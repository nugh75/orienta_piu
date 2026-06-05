"""
Slot filler for cross-cutting PTOF synthesis reports.

Takes a skeleton with [SLOT:xxx] placeholders and fills each one
with LLM-generated narrative text, using section-specific prompts
and data context from SynthesisSkeleton.
"""

import json
import logging
import re
from pathlib import Path
from typing import Optional

from .providers import get_provider, BaseProvider
from .synthesis_skeleton import SynthesisSkeleton, THEMATIC_SECTIONS

logger = logging.getLogger(__name__)


# ── Section-specific prompt templates ────────────────────────────────────

SYSTEM_PROMPT = """Sei un analista esperto del sistema scolastico italiano, specializzato nell'orientamento.
Scrivi in italiano formale ma accessibile, con prosa narrativa fluida.

SCALA DI COPERTURA INFORMATIVA (Likert 1-7):
Tutti i punteggi misurano il GRADO DI COPERTURA INFORMATIVA del PTOF su una scala Likert a 7 livelli.
NON è un giudizio di qualità sulla scuola, ma una misura di quanto il documento PTOF descrive e dettaglia le pratiche di orientamento.
  1 = Assente — Nessun riferimento nel PTOF.
  2 = Traccia minima — Menzionato vagamente, copia-incolla normativo.
  3 = Copertura parziale — Intenzione dichiarata senza dettagli attuativi.
  4 = Copertura di base — Azioni descritte in modo chiaro ma essenziale.
  5 = Copertura strutturata — Azioni dettagliate, metodologie esplicitate, risorse indicate.
  6 = Copertura approfondita — Azioni integrate, con indicatori di monitoraggio documentati.
  7 = Copertura esaustiva — Documentazione sistematica, ciclica, con evidenze di miglioramento.
Quando citi punteggi, CONTESTUALIZZALI SEMPRE con il livello di copertura corrispondente.
Esempio: "il punteggio medio di 3.8 su 7 indica una copertura informativa tra 'parziale' e 'di base'".
NON usare mai termini valutativi come "eccellente", "ottimo", "buono", "sufficiente" per descrivere i punteggi.

REGOLA TASSATIVA SUI PUNTEGGI:
- Quando citi un punteggio, scrivi SEMPRE "su 7" oppure "su scala 1-7". Esempio: "un punteggio medio di 3.5 su 7".
- NON scrivere MAI "su una scala non specificata", "su una scala indefinita", "su scala presumibilmente di 5".
- NON scrivere MAI "su 5", "su scala 5", "su una scala di cinque punti" — la scala è 1-7, NON 1-5.
- NON inventare nomi di scala come "scala di coordinamento" o "scala di continuità" — esiste UNA SOLA scala: Likert 1-7.
- La prima volta che citi un punteggio in una sezione, specifica "su scala Likert 1-7 (1=Assente, 7=Copertura esaustiva)".
  Nelle citazioni successive della stessa sezione basta "su 7".

DIMENSIONI E PESI:
Ogni PTOF è valutato su 5 dimensioni principali, ciascuna con indicatori specifici (tutti su scala 1-7):
1. FINALITÀ (peso 35%): attitudini, interessi, progetto di vita, transizioni formative, capacità orientative.
2. OBIETTIVI (peso 10%): ridurre abbandono, continuità territorio, contrastare NEET, lifelong learning.
3. GOVERNANCE (peso 25%): coordinamento servizi, dialogo docenti-studenti, rapporto scuola-genitori, monitoraggio azioni, inclusione e fragilità.
4. DIDATTICA ORIENTATIVA (peso 15%): esperienza studenti, laboratoriale, flessibilità spazi/tempi, interdisciplinare.
5. OPPORTUNITÀ (peso 15%): culturali, laboratoriali/espressive, ludiche/ricreative, volontariato, sportive.

IIPO (Indice di Documentazione Pratiche Orientamento):
L'IIPO è la media ponderata delle 5 dimensioni (con i pesi sopra indicati), su scala 1-7.
- Misura la ricchezza documentale complessiva del PTOF sull'orientamento.
- Un IIPO di 4.0 indica una copertura di base; sopra 5.0 indica copertura strutturata; sotto 3.0 indica copertura carente.

GLOSSARIO CHIAVI PUNTEGGIO:
- mean_strutturale / mean_finalita / mean_obiettivi / mean_governance / mean_didattica_orientativa / mean_opportunita: medie delle 6 dimensioni del framework.
- 2_1_score: allineamento normativo (DM 328/2022).
- 2_3_finalita_*: punteggi sulle finalità (attitudini, interessi, progetto di vita, transizioni, empowerment).
- 2_4_obiettivo_*: punteggi sugli obiettivi (dispersione, NEET, continuità, lifelong learning).
- 2_5_azione_*: punteggi sulle azioni di governance (coordinamento, dialogo, monitoraggio, inclusione, famiglie).
- 2_6_didattica_*: punteggi sulla didattica orientativa (laboratoriale, esperienziale).
- 2_7_opzionali_*: punteggi sulle opportunità formative.

PRINCIPI PEDAGOGICI FONDATIVI DELL'ORIENTAMENTO:
Nell'analisi dei PTOF, tieni sempre presenti questi principi come lente interpretativa:

1. ORIENTAMENTO COME DIDATTICA CURRICOLARE: L'orientamento non è un'attività aggiuntiva o extracurricolare separata dalla didattica ordinaria. È di per sé un atto didattico e dovrebbe essere integrato nella didattica curricolare quotidiana. Quando analizzi le pratiche, valuta criticamente se le scuole trattano l'orientamento come parte integrante del curricolo o lo relegano a interventi episodici e scollegati dall'insegnamento.

2. DISTINZIONE TRA STRUMENTI DIAGNOSTICI E STRUMENTI RIFLESSIVI: Non confondere i test psicodiagnostici (che mirano a rilevare attitudini e interessi attraverso misurazioni standardizzate) con i questionari riflessivi (che spingono lo studente a interrogarsi in profondità su se stesso, sulle proprie motivazioni e aspirazioni). I primi fotografano, i secondi accompagnano un processo di crescita. Nell'analisi, segnala quale dei due approcci prevale e se le scuole documentano percorsi riflessivi autentici o si limitano alla somministrazione di test.

3. ORIENTAMENTO COME DISPOSITIVO DI AUTO-DIREZIONE: L'orientamento efficace non è un servizio che "indirizza" lo studente verso un percorso deciso da altri. È un dispositivo formativo che aiuta la persona a dirigere se stessa, a sviluppare la capacità di compiere scelte consapevoli e autonome in coerenza con i propri interessi, attitudini e aspirazioni. Valuta se i PTOF descrivono lo studente come soggetto agente della propria scelta o come destinatario passivo di consigli e informazioni.

4. RESPONSABILITÀ SOCIALE E DIGNITÀ DELLA PERSONA: Le scelte orientative non sono solo individuali. Un orientamento maturo integra la dimensione della responsabilità sociale, della sostenibilità ambientale e della dignità della persona. Verifica se i PTOF collegano l'orientamento a una visione più ampia che include il contributo del singolo alla collettività, la cura dell'ambiente e il rispetto della dignità umana nel lavoro e nella formazione.

REGOLE TASSATIVE:
- Scrivi SOLO prosa narrativa continua. NESSUN elenco puntato o numerato.
- NESSUN titolo o sottotitolo (#, ##, ###).
- NESSUNA emoji.
- Usa connettivi logici: inoltre, tuttavia, in particolare, analogamente, nondimeno, al contempo.
- Basa le osservazioni SOLO sui dati forniti. NON INVENTARE.
- TONO: Obiettivo, onesto e corretto. Evita toni trionfalistici se i dati non lo supportano. Sii rigoroso.
- TECNICISMI: Evita gergo burocratico inutile. Se usi sigle (PCTO, RAV, NIV, PTOF), assicurati che il contesto le renda comprensibili o siano di uso comune.
- DIVIETO ASSOLUTO DI IPOTESI: Non fare ipotesi, speculazioni o supposizioni su cause non esplicitate.
- Attieniti a una descrizione oggettiva dei fatti emergenti dai numeri e dai testi forniti.
- CITAZIONI: Cita SEMPRE le scuole con il formato esatto: Nome Scuola (CODICE) [REGIONE]. Esempio: "Il Liceo Volta (MIPC010001) [Lombardia] propone...". NON aggiungere MAI diciture come [CODICE DUBBIO] accanto ai codici: tutti i codici presenti nei dati sono validi (le scuole paritarie hanno formati diversi dalle statali).
- SINTESI REALE: Non fare un semplice elenco di "La scuola X fa questo, la scuola Y fa quello". Sintetizza i trend e usa gli esempi per corroborare le affermazioni generali.
- COERENZA NUMERICA: Usa il numero di scuole indicato nella sezione Campione del report. Non inventare numeri diversi nelle sezioni successive.
- Target: 400-800 parole per sezione.

REGOLA FONDAMENTALE SULL'USO DELLE EVIDENZE:
- Le "NARRATIVA CAMPIONE" forniscono il quadro interpretativo generale (riassunti delle analisi).
- Le "EVIDENZE TESTUALI DAI PTOF" sono citazioni dirette dai documenti originali delle scuole.
- Ogni affermazione chiave DEVE essere supportata da almeno una evidenza testuale dai PTOF.
- Quando riassunti e evidenze sono in contrasto, privilegia le evidenze raw dai documenti originali.
- Puoi citare brevemente il testo originale tra virgolette per ancorare l'analisi ai documenti reali.
- Se le evidenze testuali rivelano dettagli non presenti nei riassunti, integra queste informazioni nella narrazione.
"""

SLOT_PROMPTS = {
    "profili_cluster": """Scrivi una sezione che presenti i profili dei cluster identificati dall'analisi automatica.

RICORDA: I punteggi misurano la copertura informativa su scala Likert 1-7 (1=Assente, 4=Copertura di base, 7=Copertura esaustiva).

STRUTTURA ANALITICA RICHIESTA:
1. Inizia con una frase che spieghi quanti cluster sono stati individuati e quante scuole coprono complessivamente.
2. Per OGNI cluster, descrivi in un paragrafo dedicato:
   a) Usa il NOME RAPPRESENTATIVO del cluster (presente nei dati come etichetta descrittiva) come intestazione del paragrafo.
      Se non è disponibile un nome, usa "Cluster N".
   b) Dimensione (quante scuole)
   c) Tratto dominante (qual è la caratteristica che accomuna queste scuole?)
   d) Dimensioni forti e deboli (quali punteggi emergono?)
   e) Cosa lo distingue dagli altri cluster
3. Chiudi con un paragrafo comparativo: quali convergenze e divergenze emergono tra i gruppi?

DA EVITARE:
- Non inventare etichette arbitrarie per i cluster: usa i nomi rappresentativi forniti nei dati.
- Non elencare tutti i dati numerici di ogni cluster: seleziona solo quelli che marcano differenze reali.

{cluster_summaries_text}

DATI AGGREGATI:
{data_json}
""",

    "sintesi_generale": """Scrivi un commento di sintesi che offra al lettore una panoramica trasversale
sullo stato della documentazione dell'orientamento nei PTOF analizzati.

RICORDA: I punteggi misurano la copertura informativa su scala Likert 1-7 (1=Assente, 4=Copertura di base, 7=Copertura esaustiva).

STRUTTURA ANALITICA RICHIESTA:
1. Apri con il dato aggregato chiave: IIPO medio del campione, contestualizzato sulla scala 1-7.
2. Identifica le dimensioni più forti e quelle più deboli, spiegando cosa significano in concreto.
3. Descrivi la distribuzione: le scuole sono raggruppate intorno alla media o la variabilità è alta?
4. Segnala se emergono differenze macroscopiche tra tipologie di scuola o aree geografiche.
5. Chiudi anticipando i temi che verranno approfonditi nelle sezioni successive.

DOMANDE GUIDA (rispondi attraverso la narrazione, non come lista):
- L'orientamento appare come scelta strategica o come adempimento burocratico?
- L'orientamento è integrato nella didattica curricolare quotidiana o confinato in attività separate?
- Lo studente emerge come soggetto capace di dirigere se stesso o come destinatario passivo?
- C'è coerenza tra le dichiarazioni di intento e le azioni documentate?
- Emergono riferimenti alla responsabilità sociale, alla sostenibilità e alla dignità della persona nelle scelte orientative?

DA EVITARE:
- Non ripetere la spiegazione della scala Likert (il lettore l'ha già letta nella nota metodologica).
- Non entrare nel dettaglio di singole scuole qui — questa è una panoramica.

{cluster_summaries_text}

DATI AGGREGATI:
{data_json}

NARRATIVA CAMPIONE (riassunti analisi):
{narratives_text}

EVIDENZE TESTUALI DAI PTOF (citazioni dirette dai documenti originali):
{raw_evidence_text}
""",

    "allineamento_normativo": """Analizza come i PTOF recepiscono le normative recenti sull'orientamento
(Linee Guida Orientamento, D.M. 328/2022, PNRR).

RICORDA: I punteggi misurano la copertura informativa su scala Likert 1-7 (1=Assente, 4=Copertura di base, 7=Copertura esaustiva).

FATTI NORMATIVI INDEROGABILI (da trattare come verità assolute):
- I moduli di orientamento formativo di almeno 30 ore annue per studente sono OBBLIGATORI per TUTTE le scuole secondarie, sia di I grado sia di II grado (D.M. 328/2022, Linee Guida per l'orientamento, a partire dall'a.s. 2023/24).
- La figura del docente tutor e del docente orientatore è prevista per ENTRAMBI i gradi di scuola secondaria.
- Non presentare MAI i moduli da 30 ore come facoltativi, opzionali o come mera "opportunità": sono un OBBLIGO NORMATIVO.
- Non scrivere MAI che il docente orientatore è previsto "solo" per la scuola secondaria di II grado: è previsto anche per il I grado.

STRUTTURA ANALITICA RICHIESTA:
1. Apri con il punteggio medio di allineamento normativo e cosa rivela sulla distanza tra norma e pratica documentata.
2. Distingui tra recepimento formale (la norma è citata) e sostanziale (i principi sono tradotti in azioni).
   Usa le evidenze testuali per illustrare entrambi i casi.
3. Analizza le figure del Tutor e dell'Orientatore: sono descritte con ruoli operativi o solo menzionate?
4. Esamina i moduli OBBLIGATORI da 30 ore: le scuole li documentano come obbligo adempiuto con contenuti strutturati, o li riducono a un mero conteggio orario senza sostanza formativa?
5. Segnala eventuali scuole che vanno oltre il minimo normativo con approcci originali.

DA EVITARE:
- Non elencare le norme senza collegarle ai dati. Ogni riferimento normativo deve essere ancorato a un'evidenza.
- Non confondere la citazione di una norma nel PTOF con la sua applicazione.
- Non mettere in dubbio l'obbligatorietà dei moduli da 30 ore: sono un obbligo, non un'opportunità facoltativa.

{cluster_summaries_text}

DATI AGGREGATI:
{data_json}

ESTRATTI NARRATIVI RILEVANTI:
{narratives_text}

EVIDENZE TESTUALI DAI PTOF (citazioni dirette):
{raw_evidence_text}

ESEMPI DI ATTIVITÀ RAPPRESENTATIVE:
{activities_text}
""",

    "rapporto_territorio": """Analizza come le scuole documentano le relazioni con il territorio
ai fini dell'orientamento.

RICORDA: I punteggi misurano la copertura informativa su scala Likert 1-7 (1=Assente, 4=Copertura di base, 7=Copertura esaustiva).

DATI DI FREQUENZA PARTNER: Sopra trovi grafici e una tabella con i partner territoriali più citati
nel campione e la loro distribuzione per categoria. Fai ESPLICITO RIFERIMENTO a questi dati nel testo
narrativo, commentando quali tipi di partner prevalgono, quali sono sottorappresentati e cosa questo
implica per la qualità delle reti territoriali. Se disponibili:
{territory_frequencies_text}

STRUTTURA ANALITICA RICHIESTA:
1. Apri commentando i dati di frequenza dei partner: quali categorie dominano (es. Enti Locali,
   Università, Terzo Settore)? Quali sono sorprendentemente assenti o rari? Cosa rivela questo
   sulla natura delle reti territoriali?
2. Classifica le partnership documentate: con chi collaborano le scuole?
   (Università, ITS, aziende, terzo settore, enti locali, altre scuole)
   Indica quale tipo prevale e se le collaborazioni appaiono operative o solo formali.
3. Analizza i PCTO/stage: sono descritti come esperienza orientativa con obiettivi formativi,
   o come adempimento con sole ore da completare?
4. Verifica la continuità verticale: esiste un dialogo documentato con il grado precedente e successivo?
5. Cita casi concreti dalle evidenze per illustrare i diversi livelli di copertura.

DA EVITARE:
- Non elencare tutte le partnership di ogni scuola. Sintetizza i pattern e usa 2-3 esempi significativi.
- Non confondere la menzione di un ente partner con una collaborazione operativa documentata.

{cluster_summaries_text}

DATI AGGREGATI:
{data_json}

ESTRATTI NARRATIVI RILEVANTI:
{narratives_text}

EVIDENZE TESTUALI DAI PTOF (citazioni dirette):
{raw_evidence_text}

ESEMPI DI ATTIVITÀ RAPPRESENTATIVE:
{activities_text}
""",

    "metodologie_didattiche": """Analizza le metodologie didattiche documentate per l'orientamento.

RICORDA: I punteggi misurano la copertura informativa su scala Likert 1-7 (1=Assente, 4=Copertura di base, 7=Copertura esaustiva).

DATI DI FREQUENZA: Sopra trovi un grafico a barre e una tabella con le metodologie più diffuse
nel campione. Fai ESPLICITO RIFERIMENTO a questi dati nel testo narrativo, citando le metodologie
più frequenti e le percentuali di adozione. Se disponibili:
{methodology_frequencies_text}

PRINCIPIO CHIAVE: L'orientamento è di per sé un atto didattico. Non è un'aggiunta alla didattica, ma una sua dimensione costitutiva. La domanda centrale è: le scuole lo trattano come parte integrante dell'insegnamento curricolare quotidiano, o lo confinano in attività separate e aggiuntive?

STRUTTURA ANALITICA RICHIESTA:
1. Apri commentando le metodologie più diffuse nel campione (riferendoti ai dati di frequenza
   nella tabella/grafico precedente): quali dominano e perché.
2. INTEGRAZIONE CURRICOLARE (domanda chiave): l'orientamento è INTEGRATO nel curricolo quotidiano
   — cioè le discipline scolastiche stesse diventano occasione orientativa — o è RELEGATO
   a progetti speciali separati dall'insegnamento ordinario? Le evidenze cosa mostrano?
   Cerca indicatori di didattica orientativa trasversale (ogni docente orienta attraverso la propria
   disciplina) vs orientamento come "progetto a parte" affidato a referenti o esperti esterni.
3. Analizza la didattica attiva: ci sono indicatori di laboratori reali (con prodotti, risultati, valutazione)
   o si tratta di etichette generiche ("didattica laboratoriale") senza dettagli operativi?
4. Valuta il ruolo dello studente come soggetto agente: è protagonista attivo che co-progetta,
   sceglie, riflette e impara a dirigere se stesso, o destinatario passivo di attività decise da altri?
   L'orientamento lo aiuta a sviluppare la capacità di autodirezione?
5. Cerca innovazione autentica: esiste qualcosa di non convenzionale
   (orientamento narrativo, debate, compiti di realtà, peer tutoring, percorsi riflessivi profondi)
   o l'offerta è omogenea e standardizzata?

DA EVITARE:
- Non elencare tutte le attività laboratoriali citate. Identifica i pattern e usa esempi mirati.
- Non assumere che "laboratorio" significhi automaticamente didattica attiva: verifica nelle evidenze.
- Non trattare l'orientamento come se fosse necessariamente un'attività distinta dalla didattica: è didattica esso stesso.

{cluster_summaries_text}

DATI AGGREGATI:
{data_json}

ESTRATTI NARRATIVI RILEVANTI:
{narratives_text}

EVIDENZE TESTUALI DAI PTOF (citazioni dirette):
{raw_evidence_text}

ESEMPI DI ATTIVITÀ RAPPRESENTATIVE:
{activities_text}
""",

    "strumenti_supporto": """Analizza gli strumenti operativi e digitali documentati nei PTOF per l'orientamento.

RICORDA: I punteggi misurano la copertura informativa su scala Likert 1-7 (1=Assente, 4=Copertura di base, 7=Copertura esaustiva).

DISTINZIONE FONDAMENTALE TRA STRUMENTI:
- TEST PSICODIAGNOSTICI: strumenti standardizzati che misurano attitudini, interessi e tratti di personalità (es. test di Holland, questionari attitudinali strutturati). Fotografano uno stato, producono un profilo.
- QUESTIONARI RIFLESSIVI: strumenti che accompagnano lo studente in un percorso di autoesplorazione profonda, stimolando la riflessione su motivazioni, aspirazioni, valori e progetto di vita. Non misurano, ma provocano consapevolezza.
Nell'analisi, distingui SEMPRE tra questi due approcci e valuta quale prevale nei PTOF.

STRUTTURA ANALITICA RICHIESTA:
1. Panoramica: quali strumenti compaiono più frequentemente nei PTOF? (E-Portfolio, Piattaforma Unica, questionari, test attitudinali, consiglio orientativo)
2. E-Portfolio: le scuole lo descrivono come strumento di consapevolezza e riflessione,
   o come adempimento compilativo? Cerca evidenze concrete di entrambi gli approcci.
3. Piattaforma Unica MIM: è integrata nel percorso orientativo o solo menzionata?
4. Test diagnostici vs questionari riflessivi: le scuole si limitano alla somministrazione di test
   psicodiagnostici standardizzati (che fotografano attitudini e interessi) o documentano anche
   percorsi riflessivi che spingono lo studente a interrogarsi in profondità su se stesso,
   sulle proprie motivazioni e aspirazioni? I test sono somministrati una tantum o inseriti
   in un percorso con restituzione, riflessione e follow-up che trasformi il dato in consapevolezza?
5. Consiglio orientativo: è il risultato di un processo documentato (osservazioni, colloqui, portfolio,
   percorso riflessivo) o appare come un atto finale scollegato dal percorso?
6. Auto-direzione: gli strumenti documentati aiutano lo studente a dirigere se stesso e a compiere
   scelte autonome, o lo relegano a destinatario passivo di profili e consigli prodotti da altri?

DA EVITARE:
- Non fare una rassegna enciclopedica di tutti gli strumenti. Concentrati su come vengono USATI, non solo su quali esistono.
- Non confondere la menzione di uno strumento con la sua implementazione documentata.
- Non trattare test diagnostici e questionari riflessivi come sinonimi: hanno funzioni pedagogiche profondamente diverse.

{cluster_summaries_text}

DATI AGGREGATI:
{data_json}

ESTRATTI NARRATIVI RILEVANTI:
{narratives_text}

EVIDENZE TESTUALI DAI PTOF (citazioni dirette):
{raw_evidence_text}

ESEMPI DI ATTIVITÀ RAPPRESENTATIVE:
{activities_text}
""",

    "formazione_personale": """Analizza la formazione documentata per docenti e tutor sui temi dell'orientamento.

RICORDA: I punteggi misurano la copertura informativa su scala Likert 1-7 (1=Assente, 4=Copertura di base, 7=Copertura esaustiva).

STRUTTURA ANALITICA RICHIESTA:
1. Apri con il punteggio di dialogo docenti-studenti e cosa rivela sulla preparazione del personale.
2. Verifica se nei PTOF compare formazione SPECIFICA sull'orientamento o se la formazione documentata
   riguarda solo altri temi (sicurezza, digitale, inclusione, disciplinare).
3. Analizza la preparazione dei Tutor: il DM 328/2022 ha introdotto la figura del tutor e del docente orientatore
   in TUTTE le scuole secondarie (sia I sia II grado) — le scuole documentano un percorso formativo dedicato
   o la funzione è assegnata senza training?
4. Cerca gap espliciti: se la formazione sull'orientamento non compare, segnalalo chiaramente come assenza.
5. Cita eventuali eccezioni positive con evidenze concrete.

DA EVITARE:
- Non inventare formazione non documentata. Se i PTOF non ne parlano, l'assenza è il dato.
- Non confondere formazione generica dei docenti con formazione specifica sull'orientamento.

{cluster_summaries_text}

DATI AGGREGATI:
{data_json}

ESTRATTI NARRATIVI RILEVANTI:
{narratives_text}

EVIDENZE TESTUALI DAI PTOF (citazioni dirette):
{raw_evidence_text}

ESEMPI DI ATTIVITÀ RAPPRESENTATIVE:
{activities_text}
""",

    "figure_professionali": """Analizza la governance dell'orientamento documentata nei PTOF.

RICORDA: I punteggi misurano la copertura informativa su scala Likert 1-7 (1=Assente, 4=Copertura di base, 7=Copertura esaustiva).

STRUTTURA ANALITICA RICHIESTA:
1. Apri con il punteggio di coordinamento servizi e cosa rivela sull'organizzazione.
2. Analizza l'organigramma orientativo: esiste un team dedicato o la responsabilità ricade
   su un singolo referente/funzione strumentale? Come si raccorda con i Consigli di Classe?
3. Esamina il ruolo del Tutor e dell'Orientatore: sono figure operative con compiti descritti
   o solo caselle nell'organigramma?
4. Verifica se le scuole documentano lavoro in rete con altri istituti per l'orientamento
   (reti di scopo, accordi, tavoli territoriali).
5. Segnala il livello di formalizzazione: c'è un piano annuale dell'orientamento con tempi,
   azioni e responsabilità, o solo dichiarazioni generiche?

DA EVITARE:
- Non descrivere l'organigramma completo di ogni scuola. Cerca i pattern organizzativi comuni.
- Non confondere "Funzione Strumentale per l'Orientamento" con un sistema di governance strutturato.

{cluster_summaries_text}

DATI AGGREGATI:
{data_json}

ESTRATTI NARRATIVI RILEVANTI:
{narratives_text}

EVIDENZE TESTUALI DAI PTOF (citazioni dirette):
{raw_evidence_text}

ESEMPI DI ATTIVITÀ RAPPRESENTATIVE:
{activities_text}
""",

    "principali_lacune": """Analizza le criticità e i gap emersi dall'analisi dei PTOF.
Sii diretto e basato sui dati — nessuna diplomazia.

RICORDA: I punteggi misurano la copertura informativa su scala Likert 1-7 (1=Assente, 4=Copertura di base, 7=Copertura esaustiva).
Punteggi sotto 3.0 indicano copertura carente.

STRUTTURA ANALITICA RICHIESTA:
1. Identifica le 3-4 dimensioni con i punteggi più bassi e spiega cosa significa concretamente
   ciascuna lacuna (non il numero astratto, ma cosa MANCA nella pratica documentata).
2. Analizza il gap dichiarazioni/azioni: dove i PTOF dichiarano obiettivi ambiziosi
   ma non documentano azioni, risorse o indicatori corrispondenti?
3. Esamina il monitoraggio: quante scuole documentano meccanismi di verifica dell'efficacia
   delle azioni orientative? (non solo "fatto/non fatto" ma impatto sugli studenti)
4. Cerca temi sistematicamente assenti: bias di genere nelle scelte, stereotipi professionali,
   fragilità e rischio dispersione, empowerment studentesco.
5. Valuta le risorse: emergono segnali di carenza di fondi, spazi, tempo o personale dedicato?

DA EVITARE:
- Non attenuare le criticità con formule diplomatiche ("pur con alcune aree di miglioramento...").
  Se un punteggio è 2.0 su 7, la copertura è quasi assente: dillo chiaramente.
- Non ripetere criticità già emerse nelle sezioni precedenti. Aggiungi valore con analisi nuove.

{cluster_summaries_text}

DATI AGGREGATI (focus sulle dimensioni più deboli):
{data_json}

ESTRATTI NARRATIVI RILEVANTI:
{narratives_text}

EVIDENZE TESTUALI DAI PTOF (citazioni dirette):
{raw_evidence_text}

ESEMPI DI ATTIVITÀ RAPPRESENTATIVE:
{activities_text}
""",

    "temi_globali_e_scelte_consapevoli": """Analizza come i PTOF documentano la dimensione etica,
civica e di sviluppo personale dell'orientamento.

RICORDA: I punteggi misurano la copertura informativa su scala Likert 1-7 (1=Assente, 4=Copertura di base, 7=Copertura esaustiva).

PRINCIPIO CHIAVE: Le scelte orientative non sono mai solo individuali. Un orientamento maturo non si limita a indirizzare verso un percorso di studi o una professione, ma integra la dimensione della responsabilità sociale, della sostenibilità ambientale e della dignità della persona. Lo studente non sceglie solo "cosa fare da grande" ma "chi vuole essere nella comunità".

STRUTTURA ANALITICA RICHIESTA:
1. Progetto di vita e auto-direzione: le scuole documentano un accompagnamento alla costruzione
   dell'identità personale e professionale — aiutando lo studente a dirigere se stesso — o
   l'orientamento si riduce alla scelta della scuola/percorso successivo?
   Usa il punteggio sulla finalità "progetto di vita" e le evidenze concrete.
   Verifica se emerge un orientamento che sviluppa la capacità di compiere scelte autonome
   e consapevoli, in coerenza con interessi e aspirazioni proprie (non imposte).
2. Responsabilità sociale e dignità della persona: le scelte orientative sono presentate anche
   nella loro dimensione collettiva? Le scuole collegano l'orientamento alla responsabilità
   verso la comunità, al contributo che ciascuno può dare alla società? Emerge la dignità
   della persona come criterio per valutare le scelte formative e professionali (non solo
   la remunerazione o il prestigio, ma il senso, il rispetto, la realizzazione umana)?
3. Sostenibilità ambientale e Agenda 2030: compaiono come parte dell'orientamento
   (connettere le scelte formative alla cittadinanza globale e alla cura dell'ambiente)
   o sono trattati in sezioni separate senza legame con l'orientamento?
   Le scuole aiutano gli studenti a leggere le proprie scelte anche in chiave di impatto ambientale?
4. Competenze trasversali: soft skills, pensiero critico, imprenditorialità, autoregolazione —
   sono documentate come obiettivi orientativi o come generiche competenze di cittadinanza?
5. Volontariato e servizio: le esperienze di impegno sociale sono integrate
   nel percorso orientativo (come occasione per scoprire valori, attitudini e responsabilità)
   o sono completamente assenti o scollegate dall'orientamento?

DA EVITARE:
- Non sovrapporre questa sezione con "Metodologie Didattiche". Qui il focus è su COSA si orienta
  (valori, visione di futuro, cittadinanza, responsabilità sociale), non su COME si fa didattica.
- Non fare discorsi astratti sull'importanza dell'Agenda 2030 o della dignità. Resta ancorato ai dati.
- Non ridurre l'orientamento alla sola dimensione individuale: verifica se i PTOF integrano
  la dimensione sociale e collettiva delle scelte.

{cluster_summaries_text}

DATI AGGREGATI:
{data_json}

ESTRATTI NARRATIVI RILEVANTI:
{narratives_text}

EVIDENZE TESTUALI DAI PTOF (citazioni dirette):
{raw_evidence_text}

ESEMPI DI ATTIVITÀ RAPPRESENTATIVE:
{activities_text}
""",

    "bilancio_complessivo": """Scrivi le conclusioni del report.
Stile: sintetico, diretto, orientato all'azione.

RICORDA: I punteggi misurano la copertura informativa su scala Likert 1-7 (1=Assente, 4=Copertura di base, 7=Copertura esaustiva).

STRUTTURA ANALITICA RICHIESTA:
1. DATO CHIAVE: Apri con l'IIPO medio e il suo significato in una frase incisiva.
2. PUNTI DI FORZA (max 3): Solo quelli realmente supportati dai dati.
   Per ciascuno, indica il punteggio e un esempio concreto.
3. CRITICITÀ PRIORITARIE (max 3): Le lacune più gravi, con impatto reale.
   Evita di ripetere tutto ciò che è stato detto nelle sezioni precedenti: seleziona.
4. DIREZIONE DI SVILUPPO: Cosa dovrebbe cambiare nei prossimi PTOF?
   Basati su ciò che le scuole migliori già fanno (non su desideri astratti).

DA EVITARE:
- Non ripetere tutti i dati delle sezioni precedenti. Il bilancio è una SELEZIONE, non un riassunto.
- Non chiudere con frasi generiche ottimistiche ("la scuola italiana ha le risorse...").
  Chiudi con un'osservazione concreta basata sui dati analizzati.
- Non introdurre informazioni nuove non presenti nelle sezioni precedenti.

{cluster_summaries_text}

DATI AGGREGATI:
{data_json}

NARRATIVA CAMPIONE (riassunti analisi):
{narratives_text}

EVIDENZE TESTUALI DAI PTOF (citazioni dirette):
{raw_evidence_text}
""",

    "implicazioni_campionamento": """Scrivi 2-3 paragrafi che interpretino i dati campionari presentati nelle tabelle precedenti.

Non ripetere i numeri dalle tabelle — il lettore li ha già letti.
Il tuo compito è spiegare COSA SIGNIFICANO per la lettura del report.

STRUTTURA ANALITICA RICHIESTA:
1. Apri con un giudizio sintetico sulla rappresentatività complessiva del campione
   (è generalizzabile al sistema scolastico italiano o ha limiti evidenti?).
2. Per ogni bias rilevante (deviazione > 5 pp), spiega:
   a) In quale direzione il campione è sbilanciato
   b) Quali sezioni del report ne sono più influenzate (es. governance, territorio, didattica)
   c) Come il lettore dovrebbe calibrare la lettura dei risultati in quelle sezioni
3. Chiudi con un'affermazione chiara: i risultati sono generalizzabili? Con quali cautele?

DA EVITARE:
- Non ricopiare i numeri delle tabelle. Interpretali.
- Non minimizzare i bias se i numeri non lo supportano.
- Non fare ipotesi sulle cause dei bias (es. "forse le paritarie hanno risposto di più").
- Non usare tono difensivo o giustificativo.

DATI CAMPIONARI E DEVIAZIONI:
{data_json}
""",

    "panoramica_quantitativa": """Scrivi 2-3 paragrafi che offrano al lettore un commento narrativo
sui punteggi delle dimensioni appena presentati nelle tabelle precedenti.

RICORDA: I punteggi misurano la copertura informativa su scala Likert 1-7 (1=Assente, 4=Copertura di base, 7=Copertura esaustiva).

STRUTTURA ANALITICA RICHIESTA:
1. Identifica la dimensione più forte e quella più debole, spiegando cosa significano in concreto
   (non solo il numero, ma cosa implica per l'orientamento documentato nelle scuole).
2. Commenta la distribuzione interna: ci sono sotto-indicatori che si discostano molto dalla media
   della loro dimensione? Quali segnalano gap inattesi o punti di forza nascosti?
3. Anticipa le sezioni tematiche successive: quali numeri meritano un approfondimento qualitativo?

DA EVITARE:
- Non elencare tutti i numeri uno per uno. Il lettore ha le tabelle davanti.
- Non usare formule vaghe ("i punteggi sono nella media"). Specifica sempre rispetto a cosa.
- Non anticipare conclusioni che andranno nelle sezioni tematiche — qui è una panoramica quantitativa.

NOTA SUL CAMPIONE (tenerne conto nell'interpretazione):
{sampling_bias_note}

DATI AGGREGATI DELLE DIMENSIONI:
{data_json}
""",

    "conclusioni_e_limiti": """Scrivi il capitolo conclusivo del report, che deve includere sia una sintesi
dei risultati principali sia una discussione trasparente dei limiti metodologici.

RICORDA: I punteggi misurano la copertura informativa su scala Likert 1-7 (1=Assente, 4=Copertura di base, 7=Copertura esaustiva).

STRUTTURA RICHIESTA:

### Sintesi dei Risultati
1. Richiama in 3-4 frasi il messaggio centrale del report: qual è lo stato complessivo
   della documentazione dell'orientamento nei PTOF analizzati?
2. Evidenzia il risultato più significativo (positivo o negativo) emerso dall'analisi.
3. Indica la direzione evolutiva: verso dove si stanno muovendo le scuole?

### Limiti Metodologici
Discuti in modo trasparente e onesto i seguenti limiti:

1. **PTOF ≠ pratica reale**: Il report analizza documenti, non pratiche effettive.
   Una scuola con un PTOF scarno potrebbe avere ottime pratiche non documentate;
   una con un PTOF ricco potrebbe non implementare quanto scritto. I punteggi misurano
   la copertura documentale, non la qualità dell'orientamento nella realtà quotidiana.

2. **Limiti dell'analisi automatizzata**: L'analisi è condotta da modelli di linguaggio (LLM)
   che interpretano il testo. Possono verificarsi errori di classificazione, mancata
   individuazione di contenuti impliciti, o sovra-interpretazione di passaggi ambigui.
   I punteggi non sono stati validati con un panel di esperti umani.

3. **Rappresentatività del campione**: Discuti i bias campionari emersi nella sezione
   dedicata (sovra/sotto-rappresentazione di regioni, tipologie scolastiche, gestione
   statale/paritaria). Chiarisci in che misura i risultati sono generalizzabili.

4. **Scala di valutazione**: La scala Likert 1-7, pur consentendo gradualità,
   resta una riduzione di complessità. Due PTOF con lo stesso punteggio possono avere
   contenuti qualitativamente molto diversi.

5. **Snapshot temporale**: I PTOF analizzati sono documenti triennali a una data specifica.
   Le scuole possono aver aggiornato pratiche e documenti successivamente.

### Avvertenze per il Lettore
Chiudi con 2-3 raccomandazioni concrete su come leggere e utilizzare questo report
(es. incrociare con dati qualitativi, non usare come strumento di ranking, considerare
il contesto territoriale).

DA EVITARE:
- Non minimizzare i limiti con frasi rassicuranti ("nonostante questi limiti, i risultati sono solidi").
  Sii onesto e diretto.
- Non ripetere nel dettaglio i risultati delle sezioni precedenti: questa è una sintesi, non un riassunto.
- Non introdurre dati o analisi nuove non presenti nel report.

{cluster_summaries_text}

DATI AGGREGATI:
{data_json}

NOTA SUL CAMPIONE:
{sampling_bias_note}
""",
}

# ── Grade-specific normative and pedagogical context ─────────────────────
# These snippets are injected into the system prompt based on the target grade,
# so that the LLM has accurate, grade-appropriate normative knowledge.

GRADE_CONTEXT = {
    "I Grado": """
CONTESTO NORMATIVO SPECIFICO PER LA SCUOLA SECONDARIA DI I GRADO (D.M. 328/2022):

1. ETÀ E SVILUPPO: Gli studenti hanno 11-14 anni (preadolescenza). L'orientamento deve essere calibrato
   su questa fascia evolutiva: scoperta di sé, esplorazione di attitudini e interessi, costruzione
   dell'identità personale, sviluppo della capacità decisionale in modo graduale e guidato.

2. MODULI DA 30 ORE — OBBLIGATORI ma con FLESSIBILITÀ organizzativa:
   - Le Linee Guida stabiliscono che nella secondaria di I grado le 30 ore annue per studente
     possono essere gestite in modo FLESSIBILE, anche in forma EXTRACURRICULARE.
   - Questo significa che le scuole possono organizzarle sia dentro sia fuori l'orario ordinario.
   - Restano comunque un OBBLIGO, non un'opzione facoltativa.

3. PCTO — NON PERTINENTI per il I Grado:
   - I PCTO (Percorsi per le Competenze Trasversali e l'Orientamento) sono previsti
     ESCLUSIVAMENTE per la scuola secondaria di II grado.
   - Se nei dati appaiono riferimenti ai PCTO per scuole di I grado, è perché alcune
     scuole (istituti omnicomprensivi, scuole paritarie religiose, ecc.) comprendono
     sia il I sia il II grado nello stesso documento PTOF.
   - NON menzionare i PCTO nel report di I grado: ignorali silenziosamente.
     Non segnalarli come anomalia, non commentarli, non citarli nemmeno per spiegarli.
   - Analogamente, Alternanza Scuola-Lavoro NON è pertinente per il I grado: ignorala.

4. CLASSI E STRUTTURA: La scuola secondaria di I grado ha 3 anni (classi I, II, III).
   - NON scrivere MAI "classi terze, quarte e quinte" — nel I grado esistono SOLO classi I, II e III.
   - Le 30 ore sono obbligatorie per TUTTE le classi (I, II e III), a partire dall'a.s. 2023/24.

5. CONSIGLIO ORIENTATIVO: È obbligatorio in classe III (classe terminale).
   Il consiglio di classe formula un consiglio orientativo per la scelta della scuola secondaria
   di II grado, che viene comunicato alle famiglie.

6. ORIENTAMENTO IN USCITA: La transizione rilevante è dal I grado al II grado.
   - L'obiettivo principale è aiutare lo studente a scegliere consapevolmente l'indirizzo
     di scuola superiore (liceo, istituto tecnico, istituto professionale, IeFP).
   - NON si parla di orientamento verso l'università o il mondo del lavoro: è prematuro.

7. ORIENTAMENTO IN ENTRATA: La transizione dalla scuola primaria va curata come accoglienza
   e continuità verticale. Le scuole documentano spesso attività di raccordo con le primarie.

8. DISPERSIONE E NEET: Nel I grado il focus è sulla PREVENZIONE della dispersione scolastica
   e del disengagement educativo precoce, non sul contrasto diretto ai NEET (che riguarda
   prevalentemente il II grado e il post-diploma). Se i punteggi sul contrasto NEET sono bassi,
   ciò è coerente con il grado: il PTOF di una scuola media non è il luogo primario per
   strategie anti-NEET, mentre lo è per il monitoraggio del rischio di abbandono.

9. E-PORTFOLIO: Introdotto anche nel I grado dalla piattaforma UNICA.
   Gli studenti documentano il proprio percorso formativo, ma senza l'enfasi sul "Capolavoro"
   che caratterizza il II grado.

10. FIGURE PROFESSIONALI: Docente tutor e docente orientatore sono previsti anche nel I grado.
    Nel I grado il tutor ha un ruolo particolarmente importante nell'accompagnare gli studenti
    nella fase di transizione verso la scuola superiore.

11. DIDATTICA ORIENTATIVA appropriata per il I grado:
    - Didattica per competenze, apprendimento esperienziale, laboratori espressivi.
    - Orientamento narrativo: riflessione su di sé attraverso scrittura, racconto, portfolio.
    - Incontri con le scuole superiori del territorio (open day, ministage).
    - Progetti ponte e attività di continuità con le scuole di II grado.
    - NON è appropriato parlare di stage aziendali, tirocini formativi o esperienze lavorative.
""",

    "II Grado": """
CONTESTO NORMATIVO SPECIFICO PER LA SCUOLA SECONDARIA DI II GRADO (D.M. 328/2022):

1. ETÀ E SVILUPPO: Gli studenti hanno 14-19 anni (adolescenza e prima età adulta).
   L'orientamento deve accompagnare la maturazione identitaria, la costruzione di un progetto
   di vita e la preparazione a scelte formative e professionali concrete.

2. MODULI DA 30 ORE — OBBLIGATORI e prevalentemente CURRICULARI:
   - Le Linee Guida stabiliscono che nella secondaria di II grado le 30 ore annue per studente
     devono essere prevalentemente CURRICULARI, cioè integrate nell'orario scolastico ordinario.
   - Questo distingue il II grado dal I grado (dove possono essere anche extracurriculari).
   - Sono obbligatorie per TUTTE le classi (dalla I alla V), non solo per il triennio.

3. PCTO — OBBLIGATORI nel II grado (solo nel triennio: classi III, IV, V):
   - I PCTO (Percorsi per le Competenze Trasversali e l'Orientamento) sono lo strumento
     principale di orientamento esperienziale nel II grado.
   - Monte ore minimo nel triennio:
     • Licei: almeno 90 ore
     • Istituti tecnici: almeno 150 ore
     • Istituti professionali: almeno 210 ore
   - I PCTO sostituiscono la precedente "Alternanza Scuola-Lavoro" (L. 107/2015).
   - Se una scuola usa ancora il termine "Alternanza Scuola-Lavoro", si tratta di una
     denominazione obsoleta: il meccanismo normativo vigente è il PCTO.

4. CLASSI E STRUTTURA: La scuola secondaria di II grado ha 5 anni (classi I, II, III, IV, V).
   - Il biennio (classi I-II) è orientativo e propedeutico.
   - Il triennio (classi III-IV-V) prevede PCTO, orientamento in uscita e preparazione alla scelta post-diploma.
   - "Classi terze, quarte e quinte" è CORRETTO per il II grado (è il triennio finale).

5. ORIENTAMENTO IN USCITA: La transizione rilevante è dal II grado verso:
   - Università (corsi di laurea triennali e magistrali a ciclo unico)
   - ITS Academy (Istituti Tecnici Superiori — formazione terziaria professionalizzante)
   - IFTS (Istruzione e Formazione Tecnica Superiore)
   - Mondo del lavoro (inserimento diretto o apprendistato)
   - Anno di servizio civile, gap year, formazione all'estero.
   L'orientamento in uscita implica raccordi con università, aziende, enti di formazione, agenzie per il lavoro.

6. ORIENTAMENTO IN ENTRATA: La transizione dal I grado va curata come accoglienza al biennio
   e riorientamento (eventuale cambio di indirizzo nel primo anno).

7. DISPERSIONE E NEET: Nel II grado il contrasto ai NEET e alla dispersione è DIRETTAMENTE pertinente.
   - Le scuole superiori sono l'ultimo segmento formativo prima dell'ingresso nel mondo adulto.
   - Strategie attese: monitoraggio frequenze, sportelli di ascolto, raccordo con servizi sociali,
     prevenzione dell'abbandono, patti formativi, percorsi di rientro.
   - Se i punteggi sul contrasto NEET sono bassi nel II grado, è una criticità SIGNIFICATIVA.

8. E-PORTFOLIO + CAPOLAVORO:
   - L'E-Portfolio è lo strumento digitale sulla piattaforma UNICA dove lo studente documenta
     il proprio percorso formativo, le competenze acquisite, le esperienze significative.
   - Il "Capolavoro" è un elaborato/prodotto che lo studente seleziona come rappresentativo
     delle proprie competenze e della propria crescita. Ha particolare rilevanza nel II grado.

9. FIGURE PROFESSIONALI: Docente tutor e docente orientatore sono previsti nel II grado.
   - Il tutor accompagna un gruppo di studenti, cura l'E-Portfolio, supporta le scelte.
   - Il docente orientatore è la figura di raccordo con il territorio e le opportunità post-diploma.

10. TIPOLOGIE DI ISTITUTO (terminologia corretta):
    - Licei (classico, scientifico, linguistico, artistico, scienze umane, musicale e coreutico)
    - Istituti tecnici (settore economico, settore tecnologico)
    - Istituti professionali (servizi, industria e artigianato)
    - IeFP (Istruzione e Formazione Professionale regionale — percorsi triennali/quadriennali)

11. DIDATTICA ORIENTATIVA appropriata per il II grado:
    - PCTO, stage aziendali, project work, impresa formativa simulata.
    - Incontri con università, ITS, aziende, professionisti del territorio.
    - Laboratori di orientamento: bilancio di competenze, career counseling, simulazioni di colloquio.
    - Didattica per competenze trasversali (soft skills, problem solving, team working).
    - Certificazione delle competenze orientative e trasversali.
""",
}


class SynthesisFiller:
    """Fills synthesis skeleton slots with LLM-generated prose."""

    def __init__(
        self,
        skeleton: SynthesisSkeleton,
        provider_name: str = "ollama",
        model: Optional[str] = None,
    ):
        self.skeleton = skeleton
        self.provider = get_provider(provider_name, model)
        self.filled_slots: dict[str, str] = {}
        
        # Build dynamic system prompt based on filters
        target_level = self.skeleton.filters.get("ordine_grado", "tutti i gradi")
        if isinstance(target_level, list):
            target_level = ", ".join(target_level)

        # ── Grade-specific normative context ──
        # Check "II Grado" before "I Grado" to avoid substring false match
        grade_context = ""
        target_str = str(target_level)
        if "II Grado" in target_str:
            grade_context = GRADE_CONTEXT.get("II Grado", "")
        elif "I Grado" in target_str:
            grade_context = GRADE_CONTEXT.get("I Grado", "")
            
        custom_focus = f"\nFOCUS ESCLUSIVO: Questa analisi riguarda SOLO le scuole di {target_level}.\n"
        custom_focus += f"""REGOLA DI ESCLUSIONE TASSATIVA SUL GRADO SCOLASTICO:
- Il report DEVE contenere ESCLUSIVAMENTE informazioni pertinenti alle scuole di {target_level}.
- NON menzionare MAI ordini o gradi scolastici diversi da quello in focus. Esempi di contaminazioni VIETATE:
  • Se il focus è "I Grado": NON citare scuola dell'infanzia, scuola primaria, asilo nido, prima infanzia, scuola secondaria di II grado, licei, istituti tecnici, istituti professionali.
  • Se il focus è "II Grado": NON citare scuola dell'infanzia, scuola primaria, asilo nido, prima infanzia, scuola secondaria di I grado, scuola media.
- Se nei dati cluster o nelle evidenze appaiono riferimenti ad altri gradi, IGNORALI completamente: non riportarli, non commentarli, non citarli nemmeno per contrasto.
- La transizione rilevante per il I Grado è SOLO "dalla primaria al I grado" e "dal I grado al II grado". Per il II grado è SOLO "dal I grado al II grado" e "dal II grado all'università/lavoro".

DISAMBIGUAZIONE "ORIENTAMENTO":
- In questo report, "orientamento" significa SEMPRE orientamento scolastico e formativo (career guidance, educational guidance): aiutare gli studenti a comprendere attitudini, interessi, competenze e a compiere scelte consapevoli sul percorso di studi e professionale.
- NON confondere MAI con l'orientamento spaziale, cartografico o geografico (orienteering, lettura di mappe, punti cardinali). Se nei testi PTOF appaiono riferimenti all'orientamento spaziale/geografico, IGNORALI: non sono pertinenti.

FATTI NORMATIVI OBBLIGATORI (NON negoziabili, NON modificabili):
- Il D.M. 328/2022 (Linee Guida per l'orientamento) stabilisce che i moduli di orientamento formativo di almeno 30 ore annue per studente sono OBBLIGATORI per TUTTE le scuole secondarie di I grado e di II grado, a partire dall'a.s. 2023/24.
- La figura del docente tutor e del docente orientatore è prevista dal D.M. 328/2022 per ENTRAMBI i gradi della scuola secondaria (I grado E II grado).
- NON scrivere MAI che i moduli da 30 ore sono facoltativi, opzionali, o una "opportunità" che le scuole "dovrebbero" adottare: sono un OBBLIGO DI LEGGE.
- NON scrivere MAI che il docente orientatore è previsto "solo" per il II grado.
- NON usare formulazioni dubitative ("dovrebbero adottare", "sarebbe auspicabile") quando si parla di obblighi normativi: usa formulazioni assertive ("sono tenute a", "la norma impone", "l'obbligo prevede").
"""
        # Append grade-specific normative and pedagogical context
        if grade_context:
            custom_focus += grade_context

        self.system_prompt = SYSTEM_PROMPT + custom_focus

        logger.info(
            "SynthesisFiller initialized with focus=%s provider=%s model=%s",
            target_level,
            self.provider.name,
            getattr(self.provider, "model", "default"),
        )

    def fill_all_slots(self, skeleton_text: str) -> str:
        """Fill all [SLOT:xxx] placeholders in the skeleton text.

        Args:
            skeleton_text: Markdown text with [SLOT:xxx] placeholders.

        Returns:
            Complete report with all slots filled.
        """
        contexts = self.skeleton.get_slot_contexts()
        slot_pattern = re.compile(r"\[SLOT:(\w+)\]")
        slots_found = slot_pattern.findall(skeleton_text)

        logger.info("Found %d slots to fill: %s", len(slots_found), slots_found)

        for slot_key in slots_found:
            ctx = contexts.get(slot_key, {})
            logger.info("Filling slot: %s", slot_key)

            try:
                content = self._generate_slot_content(slot_key, ctx)
                self.filled_slots[slot_key] = content
                logger.info(
                    "Slot %s filled: %d chars",
                    slot_key,
                    len(content),
                )
            except Exception as e:
                logger.error("Failed to fill slot %s: %s", slot_key, e)
                try:
                    with open(f"filling_error_{slot_key}.log", "w") as f:
                        f.write(str(e))
                except Exception:
                    pass
                self.filled_slots[slot_key] = (
                    f"[Errore nella generazione di questa sezione: {e}]"
                )

        # Replace all slots in the text
        result = skeleton_text
        for slot_key, content in self.filled_slots.items():
            result = result.replace(f"[SLOT:{slot_key}]", content)

        return result

    # ── Coherence Review Pass ────────────────────────────────────────────

    REVIEW_SYSTEM_PROMPT = """Sei un editor professionista specializzato in report istituzionali sul sistema scolastico italiano.
Il tuo compito è REVISIONARE un report già scritto, correggendo SOLO i problemi elencati sotto.

COSA CORREGGERE:
1. RIPETIZIONI: Frasi, concetti o esempi ripetuti identici tra sezioni diverse. Elimina i duplicati mantenendo l'occorrenza più contestualizzata.
2. INCOERENZE NUMERICHE: Se una sezione dice "47 scuole" e un'altra "52 scuole" per lo stesso campione, uniforma al numero corretto (quello nella sezione Campione/Metodologia).
3. SCALA PUNTEGGI: Ogni punteggio DEVE essere espresso "su 7" o "su scala 1-7". Se trovi "su 5", "su 10", "scala non specificata" o simili, correggili in "su 7".
4. ETICHETTE SCALA: I livelli sono di COPERTURA INFORMATIVA (non giudizi di valore). Sostituisci eventuali "eccellente", "ottimo", "buono", "sufficiente" riferiti ai punteggi con le etichette corrette: Assente(1), Traccia minima(2), Copertura parziale(3), Copertura di base(4), Copertura strutturata(5), Copertura approfondita(6), Copertura esaustiva(7).
5. ERRORI GRAMMATICALI/ORTOGRAFICI: Correggi refusi, concordanze, punteggiatura.
6. TRANSIZIONI: Se due sezioni consecutive iniziano in modo identico o la transizione è brusca, migliora la fluidità.
7. CODICI MECCANOGRAFICI: I codici meccanografici delle scuole italiane hanno formati diversi a seconda che siano statali o paritarie. NON segnalare mai un codice come dubbio e NON inserire tag come [CODICE DUBBIO]. Se un codice appare nei dati, è corretto. Rimuovi eventuali diciture [CODICE DUBBIO] già presenti nel testo.
8. CONTAMINAZIONE DI GRADO: Se il report è dedicato a un ordine scolastico specifico (es. "I Grado" o "II Grado"), RIMUOVI ogni riferimento ad altri ordini di grado non pertinenti (es. "scuola dell'infanzia", "prima infanzia", "scuola primaria" in un report di II Grado; oppure "licei", "istituti tecnici" in un report di I Grado). Riformula il passaggio in modo coerente con il grado in focus. In particolare: se il report è di I Grado, RIMUOVI ogni menzione di PCTO, Alternanza Scuola-Lavoro o stage aziendali — questi sono previsti solo per il II grado. La loro presenza nei dati si spiega con scuole omnicomprensive o paritarie religiose che includono più ordini nello stesso PTOF, ma non sono pertinenti per il I grado. Non segnalarli come anomalia: semplicemente elimina il passaggio o riformulalo senza PCTO.
9. ORIENTAMENTO: Verifica che "orientamento" si riferisca SEMPRE all'orientamento scolastico/formativo. Se trovi riferimenti all'orientamento spaziale/cartografico (mappe, punti cardinali, orienteering), rimuovili o riformulali.
10. CORRETTEZZA NORMATIVA: I moduli da 30 ore di orientamento formativo sono OBBLIGATORI per TUTTE le scuole secondarie (I e II grado) ai sensi del D.M. 328/2022. Se trovi formulazioni che li presentano come facoltativi o opzionali, CORREGGILE. La figura del docente tutor e del docente orientatore è prevista per ENTRAMBI i gradi. Se trovi "il DM 328/2022 ha introdotto il docente orientatore nelle scuole secondarie di secondo grado" (omettendo il I grado), CORREGGI in "nelle scuole secondarie di I e II grado". Se trovi "dovrebbero adottare i moduli" o formulazioni dubitative analoghe su obblighi di legge, sostituisci con formulazioni assertive.

COSA NON FARE:
- NON aggiungere contenuti nuovi o analisi aggiuntive.
- NON cambiare la struttura (titoli, ordine sezioni).
- NON rimuovere sezioni intere.
- NON cambiare i dati o i numeri se sono coerenti.
- NON aggiungere titoli Markdown (#, ##) se non erano presenti.
- NON aggiungere emoji.
- Mantieni il tono e il registro del testo originale.

FORMATO OUTPUT: Restituisci il testo completo della sezione revisionata, NIENT'ALTRO.
Non aggiungere commenti, note editoriali o spiegazioni delle modifiche."""

    def coherence_review(self, report_text: str) -> str:
        """Run a final LLM-based coherence review on the assembled report.

        Splits the report into sections (by ## headings), reviews each section
        with full-report context, and reassembles the result.

        Args:
            report_text: The complete assembled report markdown.

        Returns:
            Revised report text.
        """
        # Split into sections by ## headings
        section_pattern = re.compile(r'^(## .+)$', re.MULTILINE)
        parts = section_pattern.split(report_text)

        # parts[0] = header/metadata before first ##
        # parts[1] = "## Title1", parts[2] = content1, parts[3] = "## Title2", ...
        if len(parts) < 3:
            logger.warning("Report too short to split into sections, reviewing as single block.")
            return self._review_single_block(report_text)

        header = parts[0]
        sections = []
        for i in range(1, len(parts), 2):
            title = parts[i]
            content = parts[i + 1] if i + 1 < len(parts) else ""
            sections.append((title, content))

        # Build a compact TOC + summary for cross-reference context
        toc = "INDICE SEZIONI DEL REPORT:\n"
        for idx, (title, _) in enumerate(sections, 1):
            toc += f"  {idx}. {title.replace('## ', '')}\n"

        logger.info("Coherence review: %d sections to review", len(sections))

        # Identify which sections are methodology/static (skip review)
        skip_keywords = {"Nota Metodologica", "Metrica di Valutazione", "Framework di Valutazione",
                         "Approccio Analitico", "Report Narrativo", "Analisi del Campione"}

        reviewed_sections = []
        for idx, (title, content) in enumerate(sections):
            section_name = title.replace("## ", "").strip()

            # Skip methodology/static sections
            if any(kw in section_name for kw in skip_keywords):
                logger.info("  Skipping static section: %s", section_name)
                reviewed_sections.append((title, content))
                continue

            # Skip very short sections (likely just a chart or table)
            if len(content.strip()) < 200:
                logger.info("  Skipping short section: %s (%d chars)", section_name, len(content.strip()))
                reviewed_sections.append((title, content))
                continue

            logger.info("  Reviewing section %d/%d: %s", idx + 1, len(sections), section_name)

            # Build context: previous section summary + next section summary
            prev_summary = ""
            if idx > 0:
                prev_title = sections[idx - 1][0].replace("## ", "")
                prev_text = sections[idx - 1][1].strip()[:500]
                prev_summary = f"\nSEZIONE PRECEDENTE ({prev_title}):\n{prev_text}...\n"

            next_summary = ""
            if idx < len(sections) - 1:
                next_title = sections[idx + 1][0].replace("## ", "")
                next_text = sections[idx + 1][1].strip()[:500]
                next_summary = f"\nSEZIONE SUCCESSIVA ({next_title}):\n{next_text}...\n"

            user_prompt = (
                f"{toc}\n"
                f"{prev_summary}"
                f"{next_summary}\n"
                f"SEZIONE DA REVISIONARE: {section_name}\n"
                f"{'=' * 60}\n"
                f"{content}\n"
                f"{'=' * 60}\n\n"
                f"Revisiona questa sezione secondo le regole indicate. "
                f"Restituisci SOLO il testo revisionato della sezione (senza il titolo ##)."
            )

            try:
                response = self.provider.generate(user_prompt, self.REVIEW_SYSTEM_PROMPT)
                reviewed_content = response.content.strip()

                # Safety: if LLM returns something wildly different in length, keep original
                original_len = len(content.strip())
                reviewed_len = len(reviewed_content)
                if reviewed_len < original_len * 0.4 or reviewed_len > original_len * 2.0:
                    logger.warning(
                        "  Review output for '%s' has suspicious length (%d vs %d), keeping original.",
                        section_name, reviewed_len, original_len,
                    )
                    reviewed_sections.append((title, content))
                else:
                    # Clean any headers the reviewer might have added
                    reviewed_content = self._clean_output(reviewed_content)
                    reviewed_sections.append((title, "\n" + reviewed_content + "\n"))
                    logger.info("  ✓ Reviewed: %s (delta: %+d chars)", section_name, reviewed_len - original_len)

            except Exception as e:
                logger.error("  Review failed for '%s': %s — keeping original.", section_name, e)
                reviewed_sections.append((title, content))

        # Reassemble
        result = header
        for title, content in reviewed_sections:
            result += title + content

        return result

    def _review_single_block(self, text: str) -> str:
        """Fallback: review the entire report as a single block (for short reports)."""
        user_prompt = (
            "REPORT COMPLETO DA REVISIONARE:\n"
            f"{'=' * 60}\n"
            f"{text}\n"
            f"{'=' * 60}\n\n"
            "Revisiona il report secondo le regole indicate. Restituisci SOLO il testo revisionato completo."
        )
        try:
            response = self.provider.generate(user_prompt, self.REVIEW_SYSTEM_PROMPT)
            reviewed = response.content.strip()
            if len(reviewed) < len(text) * 0.4:
                logger.warning("Single-block review too short, keeping original.")
                return text
            return reviewed
        except Exception as e:
            logger.error("Single-block review failed: %s", e)
            return text

    def _generate_slot_content(self, slot_key: str, context: dict) -> str:
        """Generate content for a single slot.

        Args:
            slot_key: The slot identifier (e.g. 'sintesi_generale').
            context: Data context dict from SynthesisSkeleton.get_slot_contexts().

        Returns:
            Generated prose text.
        """
        prompt_template = SLOT_PROMPTS.get(slot_key)
        if not prompt_template:
            return f"[Template mancante per slot: {slot_key}]"

        # Format data JSON (remove excerpts/activities/raw from JSON to avoid redundancy)
        exclude_keys = ("narrative_excerpts", "representative_activities", "raw_evidence")
        data_for_json = {k: v for k, v in context.items() if k not in exclude_keys}
        data_json = json.dumps(data_for_json, indent=2, ensure_ascii=False)

        # Format narrative excerpts (layer "quadro")
        narratives_text = self._format_narratives(context.get("narrative_excerpts", []))

        # Format raw PTOF evidence (layer "evidenza/booster")
        raw_evidence_text = self._format_raw_evidence(context.get("raw_evidence", []))

        # Format activities
        activities_text = self._format_activities(context.get("representative_activities", []))

        # Build the user prompt — replace all placeholders safely
        user_prompt = prompt_template
        replacements = {
            "{data_json}": data_json,
            "{narratives_text}": narratives_text,
            "{raw_evidence_text}": raw_evidence_text,
            "{activities_text}": activities_text,
            "{cluster_summaries_text}": context.get("cluster_summaries_text", ""),
            "{sampling_bias_note}": context.get("sampling_bias_note", "Nessun dato di bias disponibile."),
            "{methodology_frequencies_text}": context.get("methodology_frequencies_text", "Dati di frequenza metodologie non disponibili."),
            "{territory_frequencies_text}": context.get("territory_frequencies_text", "Dati di frequenza partner territoriali non disponibili."),
        }
        for placeholder, value in replacements.items():
            if placeholder in user_prompt:
                user_prompt = user_prompt.replace(placeholder, value)

        # Generate
        response = self.provider.generate(user_prompt, self.system_prompt)
        content = response.content.strip()

        # Post-process: remove any markdown headers the LLM may have added
        content = self._clean_output(content)

        return content

    def _format_narratives(self, excerpts: list[dict]) -> str:
        """Format narrative excerpts for the prompt."""
        if not excerpts:
            return "Nessun estratto narrativo disponibile per questa sezione."

        parts = []
        for ex in excerpts:
            parts.append(
                f"--- {ex.get('denominazione', 'N/D')} ({ex.get('code', '?')}) "
                f"[{ex.get('regione', '?')}, {ex.get('tipo_scuola', '?')}] ---\n"
                f"{ex.get('excerpt', '')}"
            )
        return "\n\n".join(parts)

    def _format_activities(self, activities: list[dict]) -> str:
        """Format representative activities for the prompt."""
        if not activities:
            return "Nessuna attività specifica disponibile per questa sezione."

        parts = []
        for act in activities:
            # Clean up newlines in description
            desc = act.get('descrizione_e_metodologia', 'N/D').replace('\n', ' ')
            parts.append(
                f"--- ATTIVITÀ: {act.get('titolo_attivita', 'N/D')}\n"
                f"SCUOLA: {act.get('school_code', '?')} ({act.get('school_region', '?')})\n"
                f"CAT: {act.get('categoria_principale', 'N/D')}\n"
                f"DESC: {desc}\n"
                f"TARGET: {act.get('target', 'N/D')}"
            )
        return "\n\n".join(parts)

    def _format_raw_evidence(self, chunks: list[dict]) -> str:
        """Format raw PTOF evidence excerpts for the prompt (layer 'evidenza')."""
        if not chunks:
            return "Nessuna evidenza testuale diretta disponibile per questa sezione."

        parts = []
        for c in chunks:
            parts.append(
                f"--- {c.get('code', '?')} [{c.get('regione', '?')}, {c.get('tipo_scuola', '?')}] ---\n"
                f"«{c.get('excerpt', '')}»"
            )
        return "\n\n".join(parts)

    def _clean_output(self, text: str) -> str:
        """Remove formatting artifacts that violate the structure (titles) but keep rich text."""
        lines = text.split("\n")
        cleaned = []
        for line in lines:
            # Remove markdown headers to prevent nesting issues
            if re.match(r"^#{1,6}\s", line):
                # Keep the text, remove the header markers
                cleaned.append(re.sub(r"^#{1,6}\s+", "", line))
            else:
                cleaned.append(line)

        result = "\n".join(cleaned)

        # Remove bold markers to keep output clean and consistent
        result = re.sub(r'\*\*(.+?)\*\*', r'\1', result)

        return result.strip()
