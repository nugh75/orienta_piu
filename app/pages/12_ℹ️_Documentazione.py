# ℹ️ Documentazione - Metodologia e guida al sistema

from pathlib import Path

import streamlit as st
from data_utils import render_footer
from page_control import setup_page

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROMPTS_FILE = BASE_DIR / "config" / "prompts.md"

REPORT_REVIEW_PROMPT = """
SEI UN EDITOR SCOLASTICO ESPERTO E METICOLOSO.
Il tuo compito è ARRICCHIRE il report di analisi esistente (Markdown) integrando
dettagli specifici estratti dal documento originale (PTOF), SENZA stravolgere la
struttura del report.

DOCUMENTO ORIGINALE (PTOF - Fonte di verità):
[TESTO PTOF TRONCATO]

REPORT ATTUALE (Bozza da arricchire):
[REPORT ATTUALE]

ISTRUZIONI OPERATIVE:
1. Confronta il report attuale con il PTOF originale.
2. Identifica informazioni di valore presenti nel PTOF ma mancanti nel report:
   - Nomi specifici di progetti.
   - Dati quantitativi (ore, budget, percentuali).
   - Metodologie didattiche particolari.
   - Collaborazioni con enti specifici.
3. Integra le informazioni nelle sezioni esistenti, con stile narrativo.
4. Non cancellare sezioni, mantieni titoli e struttura.
5. Non inventare nulla.
6. Se il report è generico, rendilo più specifico citando il testo.
7. Se nel PTOF NON esiste un capitolo dedicato all'Orientamento, non inventarlo.

STRUTTURA OBBLIGATORIA DA PRESERVARE:
# Analisi del PTOF [CODICE]
## Report di Valutazione dell'Orientamento
### 1. Sintesi Generale
### 2. Analisi Dimensionale
#### 2.1 Sezione Dedicata all'Orientamento
#### 2.2 Partnership e Reti
#### 2.3 Finalità e Obiettivi
#### 2.4 Governance e Azioni di Sistema
#### 2.5 Didattica Orientativa
#### 2.6 Opportunità Formative
#### 2.7 Registro Dettagliato delle Attività
### 3. Punti di Forza
### 4. Aree di Debolezza
### 5. Gap Analysis
### 6. Conclusioni

OUTPUT RICHIESTO:
Restituisci il contenuto Markdown del report arricchito, senza commenti extra.
"""

SCORE_REVIEW_PROMPT = """
SEI UN REVISORE CRITICO. Devi verificare SOLO i punteggi estremi.
Conferma o modifica i punteggi usando il testo come fonte di verità.

ISTRUZIONE SPECIALE - SEZIONE ORIENTAMENTO:
Verifica con estrema attenzione se esiste un capitolo esplicito di Orientamento.
Se la sezione dedicata è alta ma nel testo non c'è un capitolo specifico,
abbassa il punteggio.

DOCUMENTO ORIGINALE (estratto):
[TESTO PTOF]

PUNTEGGI DA REVISIONARE (JSON):
[JSON PUNTEGGI]

CRITERI PUNTEGGIO (scala 1-7):
1 = Assente
2 = Generico
3 = Limitato
4 = Sufficiente
5 = Buono
6 = Ottimo
7 = Eccellente

FORMATO OUTPUT (solo JSON valido):
{
  "score_updates": [
    {
      "path": "...",
      "old_score": 2,
      "new_score": 3,
      "action": "modify",
      "reason": "Spiega in breve."
    }
  ],
  "review_notes": "Nota generale opzionale."
}

REGOLE:
- Includi un elemento per ogni path ricevuto.
- Se confermi: new_score = old_score e action = "confirm".
- Nessun testo extra, solo JSON.
"""

OLLAMA_CHUNK_PROMPT = """
SEI UN EDITOR SCOLASTICO ESPERTO.
Stai analizzando un CHUNK del documento PTOF originale.

COMPITO: Trova informazioni utili per ARRICCHIRE il report esistente.
CHUNK DEL PTOF ORIGINALE:
[TESTO CHUNK PTOF]

REPORT ATTUALE (da arricchire):
[REPORT ATTUALE - TRONCATO]

RIEPILOGO SCORE JSON:
[RIEPILOGO SCORE]

ISTRUZIONI:
1. Cerca informazioni specifiche mancanti nel report.
2. Verifica se esiste una sezione dedicata all'orientamento.
3. Segnala incongruenze tra report e PTOF.
4. Non inventare nulla.

RISPONDI con JSON:
{
  "enrichments": [
    {
      "section": "sezione report da arricchire",
      "addition": "testo narrativo da aggiungere",
      "source_quote": "citazione breve dal PTOF"
    }
  ],
  "orientamento_section_found": true/false,
  "orientamento_details": "descrizione sezione orientamento",
  "corrections": [
    {
      "issue": "cosa va corretto",
      "reason": "perché"
    }
  ]
}
"""

OLLAMA_FINAL_PROMPT = """
SEI UN EDITOR SCOLASTICO ESPERTO.
Devi produrre la versione finale ARRICCHITA del report.

REPORT ATTUALE:
[REPORT ATTUALE]

ARRICCHIMENTI DA INTEGRARE:
[JSON ARRICCHIMENTI]

CORREZIONI DA APPLICARE:
[JSON CORREZIONI]

ISTRUZIONI CRITICHE:
1. Integra gli arricchimenti nelle sezioni appropriate.
2. Usa sempre stile narrativo e discorsivo.
3. Applica le correzioni segnalate.
4. Mantieni la struttura esistente del report.
5. Non rimuovere sezioni.

OUTPUT: restituisci solo il report Markdown completo arricchito.
"""

BEST_PRACTICE_EXTRACTION_PROMPT = """
/no_think
SEI UN ESPERTO DI PRATICHE EDUCATIVE E ORIENTAMENTO SCOLASTICO.

ANALIZZA questo estratto di PTOF scolastico e IDENTIFICA le BUONE PRATICHE concrete.

SCUOLA: {school_code}
CHUNK: {chunk_num}/{total_chunks}

TESTO DA ANALIZZARE:
{chunk[:25000]}

---

CATEGORIE DISPONIBILI (usa ESATTAMENTE questi nomi):
1. "Metodologie Didattiche Innovative" - tecniche didattiche avanzate, approcci pedagogici innovativi
2. "Progetti e Attivita Esemplari" - progetti strutturati, attivita significative documentate
3. "Partnership e Collaborazioni Strategiche" - accordi con enti, universita, imprese, associazioni
4. "Azioni di Sistema e Governance" - coordinamento, monitoraggio, strutture organizzative
5. "Buone Pratiche per l'Inclusione" - BES, DSA, disabilita, integrazione stranieri
6. "Esperienze Territoriali Significative" - legame col territorio, PCTO, stage

TIPOLOGIE DI METODOLOGIA (scegli UNA o PIU tra queste, oppure "Altro"):
STEM/STEAM, Coding e Pensiero Computazionale, Flipped Classroom, Peer Education/Tutoring,
Problem Based Learning, Cooperative Learning, Gamification, Debate, Service Learning,
Outdoor Education, Didattica Laboratoriale, Didattica Digitale, CLIL, Storytelling,
Project Work, Learning by Doing, Mentoring

AMBITI DI ATTIVITA (scegli UNO o PIU tra questi, oppure "Altro"):
Orientamento, Inclusione e BES, PCTO/Alternanza, Cittadinanza e Legalita, Educazione Civica,
Sostenibilita e Ambiente, Digitalizzazione, Lingue Straniere, Arte e Creativita,
Musica e Teatro, Sport e Benessere, Scienze e Ricerca, Lettura e Scrittura,
Matematica e Logica, Imprenditorialita, Intercultura, Prevenzione Disagio,
Continuita e Accoglienza, Valutazione e Autovalutazione, Formazione Docenti,
Rapporti con Famiglie

PER OGNI BUONA PRATICA IDENTIFICATA, ESTRAI:
- "categoria": una delle 6 categorie sopra (ESATTAMENTE come scritto)
- "titolo": nome sintetico della pratica (max 100 caratteri)
- "descrizione": descrizione dettagliata di cosa consiste e come funziona (200-500 caratteri)
- "metodologia_desc": come viene implementata concretamente (testo libero)
- "tipologie_metodologia": ARRAY di tipologie metodologiche applicabili (es: ["STEM/STEAM", "Didattica Laboratoriale"])
- "ambiti_attivita": ARRAY di ambiti di attivita (es: ["Orientamento", "Digitalizzazione"])
- "target": a chi e rivolta (studenti, docenti, famiglie, classi specifiche)
- "citazione_ptof": citazione testuale rilevante dal documento (max 200 caratteri)
- "pagina_evidenza": numero di pagina se menzionato (es: "Pagina 15") o "Non specificata"
- "partnership_coinvolte": lista di partner nominati se categoria e Partnership, altrimenti array vuoto

REGOLE FONDAMENTALI:
1. Estrai SOLO pratiche CONCRETE e SPECIFICHE con un nome o una descrizione chiara
2. IGNORA dichiarazioni generiche tipo "la scuola promuove l'orientamento"
3. Ogni pratica DEVE avere evidenze testuali nel documento
4. Se non trovi pratiche significative in questo chunk, rispondi con array vuoto
5. MAX 5 pratiche per chunk (seleziona le piu significative)
6. Il titolo deve essere SPECIFICO (es: "Laboratorio di Robotica Educativa", non "Attivita di laboratorio")
7. tipologie_metodologia e ambiti_attivita devono essere ARRAY di stringhe (anche se c'e un solo elemento)

RISPONDI SOLO con JSON valido (nessun testo prima o dopo):
{
  "pratiche": [
    {
      "categoria": "Nome Categoria Esatto",
      "titolo": "Nome Specifico Pratica",
      "descrizione": "Descrizione dettagliata...",
      "metodologia_desc": "Come viene implementata...",
      "tipologie_metodologia": ["STEM/STEAM", "Didattica Laboratoriale"],
      "ambiti_attivita": ["Orientamento", "Digitalizzazione"],
      "target": "A chi e rivolta",
      "citazione_ptof": "Citazione dal documento...",
      "pagina_evidenza": "Pagina X",
      "partnership_coinvolte": []
    }
  ]
}

Se non trovi pratiche significative:
{"pratiche": []}
"""

BEST_PRACTICE_EXTRACTION_JSON = """
{
  "pratiche": [
    {
      "categoria": "Nome Categoria Esatto",
      "titolo": "Nome Specifico Pratica",
      "descrizione": "Descrizione dettagliata...",
      "metodologia_desc": "Come viene implementata...",
      "tipologie_metodologia": ["STEM/STEAM", "Didattica Laboratoriale"],
      "ambiti_attivita": ["Orientamento", "Digitalizzazione"],
      "target": "A chi e rivolta",
      "citazione_ptof": "Citazione dal documento...",
      "pagina_evidenza": "Pagina X",
      "partnership_coinvolte": []
    }
  ]
}
"""

ANALYSIS_OUTPUT_SCHEMA_JSON = """
{
  "metadata": {
    "school_id": "MIIS08900V",
    "denominazione": "...",
    "ordine_grado": "I Grado|II Grado",
    "tipo_scuola": "Liceo|Tecnico|Professionale|I Grado",
    "statale_paritaria": "Statale|Paritaria",
    "area_geografica": "Nord Ovest|Nord Est|Centro|Sud|Isole"
  },
  "ptof_section2": {
    "2_1_ptof_orientamento_sezione_dedicata": {
      "has_sezione_dedicata": 0,
      "score": 1,
      "note": "..."
    },
    "2_2_partnership": {
      "partner_nominati": ["..."],
      "partnership_count": 0
    },
    "2_3_finalita": {
      "finalita_attitudini": { "score": 1 },
      "finalita_interessi": { "score": 1 },
      "finalita_progetto_vita": { "score": 1 }
    }
  },
  "narrative": "Report markdown..."
}
"""

SCORE_REVIEW_OUTPUT_JSON = """
{
  "score_updates": [
    {
      "path": "ptof_section2.2_1_ptof_orientamento_sezione_dedicata.score",
      "old_score": 2,
      "new_score": 3,
      "action": "modify",
      "reason": "Spiega in breve."
    }
  ],
  "review_notes": "Nota generale opzionale."
}
"""

OLLAMA_CHUNK_OUTPUT_JSON = """
{
  "enrichments": [
    {
      "section": "sezione report da arricchire",
      "addition": "testo narrativo da aggiungere",
      "source_quote": "citazione breve dal PTOF"
    }
  ],
  "orientamento_section_found": true,
  "orientamento_details": "descrizione sezione orientamento",
  "corrections": [
    {
      "issue": "cosa va corretto",
      "reason": "perche"
    }
  ]
}
"""

BEST_PRACTICES_DATASET_JSON = """
{
  "version": "1.0",
  "last_updated": "2025-01-01T12:00:00",
  "extraction_model": "qwen3:32b",
  "schools_processed": 120,
  "total_practices": 560,
  "practices": [
    {
      "id": "uuid",
      "school": {
        "codice_meccanografico": "RMIS02400L",
        "nome": "Istituto ...",
        "tipo_scuola": "Liceo Scientifico",
        "ordine_grado": "Secondaria II Grado",
        "regione": "Lazio",
        "provincia": "Roma",
        "comune": "Roma",
        "area_geografica": "Centro",
        "territorio": "Metropolitano",
        "statale_paritaria": "Statale"
      },
      "pratica": {
        "categoria": "Metodologie Didattiche Innovative",
        "titolo": "Laboratorio di Robotica Educativa",
        "descrizione": "...",
        "metodologia": "...",
        "tipologie_metodologia": ["STEM/STEAM"],
        "ambiti_attivita": ["Orientamento"],
        "target": "Studenti",
        "citazione_ptof": "...",
        "pagina_evidenza": "Pagina 12"
      },
      "contesto": {
        "maturity_index": 4.6,
        "punteggi_dimensionali": {},
        "partnership_coinvolte": [],
        "attivita_correlate": []
      },
      "metadata": {}
    }
  ]
}
"""

BEST_PRACTICE_REGISTRY_JSON = """
{
  "version": "1.0",
  "last_updated": "2025-01-01T12:00:00",
  "processed_files": {
    "RMIS02400L": {
      "file_hash": "sha256:...",
      "processed_at": "2025-01-01T12:00:00",
      "practices_count": 12,
      "model_used": "qwen3:32b"
    }
  }
}
"""

COMUNI_ITALIANI_JSON = """
[
  {
    "nome": "Abano Terme",
    "codice": "028001",
    "zona": { "codice": "2", "nome": "Nord-est" },
    "regione": { "codice": "05", "nome": "Veneto" },
    "provincia": { "codice": "028", "nome": "Padova" },
    "sigla": "PD",
    "codiceCatastale": "A001",
    "cap": "35031",
    "popolazione": 0
  }
]
"""


def load_prompt_sections(path: Path):
    if not path.exists():
        return []
    content = path.read_text(encoding="utf-8")
    sections = []
    current_title = None
    buffer = []
    for line in content.splitlines():
        if line.startswith("## "):
            if current_title:
                section_text = "\n".join(buffer).strip()
                sections.append((current_title, section_text))
            current_title = line[3:].strip()
            buffer = []
        else:
            buffer.append(line)
    if current_title:
        section_text = "\n".join(buffer).strip()
        sections.append((current_title, section_text))
    return sections


def label_prompt_sections(sections):
    labeled = []
    counts = {}
    for title, content in sections:
        label = title
        if title == "Validator":
            if "2022-2025" in content:
                label = "Validator PTOF 2022-2025"
            elif "SISTEMA DI VALIDAZIONE DOCUMENTALE" in content:
                label = "Validator Documentale"
        counts[label] = counts.get(label, 0) + 1
        if counts[label] > 1:
            label = f"{label} ({counts[label]})"
        labeled.append((label, content))
    return labeled


st.set_page_config(page_title="ORIENTA+ | Documentazione", page_icon="🧭", layout="wide")
setup_page("pages/12_ℹ️_Documentazione.py")

st.title("📖 Metodologia e Guida alla Piattaforma")

st.markdown(
    """
Questa pagina spiega come funziona la piattaforma di analisi PTOF: dalla lettura dei
documenti alla produzione dei punteggi e dei report, fino alla lettura dei risultati
in dashboard. L'obiettivo è offrire una valutazione coerente, confrontabile e trasparente
della qualità dell'orientamento, senza perdere il contesto di ogni scuola.
"""
)

st.markdown("---")

st.header("Cosa fa la piattaforma")
st.markdown(
    """
Questa piattaforma analizza i PTOF e restituisce una lettura **comparabile e trasparente**
dell'orientamento scolastico. Integra punteggi strutturati, report narrativi e strumenti
di confronto per territorio e profilo di scuola, mantenendo sempre il legame con le evidenze
testuali dei documenti.
"""
)

st.subheader("Sezioni della dashboard (stato attuale)")
st.markdown(
    """
- Panoramica (Home): indicatori sintetici e distribuzioni nazionali.
- Dettaglio Scuola: profilo scuola, report MD/PDF, attività collegate, gap analysis e confronto con peer (radar per tipologia/area/nazionale).
- Confronto PTOF: analisi comparativa tra scuole.
- Analisi territoriale: mappe, confronti geografici e report regionali.

- Analytics avanzati: analisi statistiche, correlazioni e visualizzazioni esplorative.
- Ricerca / Impatto metodologie: esplorazione di approcci didattici e relativi esiti.
- Catalogo Attività: estrazione, filtri, incroci categoria e analisi statistiche (significativita ed effetto).
- Orientamento Scuola: percorso guidato per famiglie/studenti con matching scuole.
- Gestione dati (area amministrativa): qualita, filtri e allineamento metadati.
- Contribuisci: Invia PTOF, Verifica Invio, Richiedi Revisione.
- Documentazione: metodologia e guida.
"""
)

st.markdown("---")

st.header("Analisi PTOF, punteggi e report")
st.markdown(
    """
L'analisi dei PTOF è pensata come un processo unico e integrato, ma con una sequenza
chiara: prima si produce l'analisi in **punteggi** per dimensioni e sotto‑dimensioni,
poi, a partire da quei punteggi e dalle evidenze testuali, si costruisce il **report
narrativo**. La lettura mette insieme coerenza interna del documento, qualità delle
azioni descritte e solidità delle evidenze, così che numeri e testo si rinforzino
a vicenda e consentano confronti affidabili senza perdere il contesto di ciascuna scuola.

Il report non nasce “a sentimento”: segue un prompt strutturato che impone una sequenza
precise (Sintesi generale, Analisi dimensionale, Punti di forza, Aree di debolezza,
Gap analysis, Conclusioni). In questa sezione trovi come vengono definite le dimensioni,
come si assegnano i punteggi e come nasce il report finale, fino all'**Indice di Completezza**
che sintetizza la ricchezza informativa dell'orientamento.
"""
)

st.subheader("Framework di Valutazione")
st.markdown(
    """
La prima dimensione osserva se il PTOF dedica uno spazio esplicito all'orientamento,
con un capitolo riconoscibile e non solo riferimenti sparsi. Da lì si passa alle
**partnership**, cioè la presenza di reti territoriali e soggetti esterni coinvolti
in modo concreto e nominato.

La **sezione dedicata** è considerata solida quando l'**orientamento** emerge nel sommario,
ha un titolo chiaro e contiene contenuti specifici su strumenti, tempi e responsabilità.
Non basta un paragrafo occasionale: la valutazione si alza quando il PTOF mostra
una struttura riconoscibile, con **obiettivi** e **azioni** coerenti tra loro.

Le **partnership** vengono lette come indicatori di apertura e continuità verso il territorio.
Si valutano la presenza di accordi nominati con **università**, **imprese**, **enti locali**,
**ITS** o **terzo settore**, e la qualità del coinvolgimento: non solo citazioni, ma attività
congiunte, percorsi di orientamento, visite, laboratori o progetti comuni. La sotto‑categoria
dei **partner nominati** misura la precisione con cui vengono indicati soggetti e reti;
la consistenza del rapporto si vede quando il PTOF racconta **obiettivi condivisi**,
tempi di realizzazione e **ruoli reciproci**. In assenza di dettagli, la partnership
resta un segnale debole e non influenza in modo significativo il punteggio.

Le **finalità** si articolano in sotto‑categorie precise. La prima riguarda le **attitudini**:
quanto la scuola aiuta gli studenti a riconoscere punti di forza, fragilità, stili
di apprendimento e talenti individuali. La seconda è legata agli **interessi**, cioè
alla capacità di far esplorare ambiti disciplinari e professionali in modo informato.
La terza finalità è il **progetto di vita**, che non è solo un obiettivo futuro, ma una
traiettoria in cui scuola, famiglia e territorio offrono strumenti per scegliere in modo
consapevole. Le **transizioni formative** misurano quanto la scuola accompagna passaggi
chiave, come il passaggio dal primo al secondo ciclo o verso la formazione terziaria.
Infine, la **capacità orientativa** sintetizza **competenze trasversali**: saper raccogliere
informazioni, valutare alternative, prendere decisioni e rivederle nel tempo.

Gli **obiettivi** descrivono dove la scuola vuole incidere. Il contrasto alla **dispersione**
si osserva quando compaiono strategie di prevenzione e recupero, tutoraggio e monitoraggio
dei rischi. La **continuità territoriale** non è solo un raccordo formale, ma un'azione
strutturata di passaggio e dialogo tra ordini di scuola, spesso sostenuta da attività
di orientamento in uscita e in ingresso. La riduzione dei **NEET** è una finalità di sistema:
emerge quando la scuola collega l'orientamento a **competenze per il lavoro** e alla capacità
di immaginare percorsi futuri. Il **lifelong learning**, infine, valuta la prospettiva lunga
del PTOF: educare alla formazione continua e al riorientamento.

La **governance** entra nel dettaglio dell'organizzazione: chi coordina l'orientamento,
come dialogano docenti e studenti, quanto sono coinvolte le famiglie e quali strumenti
di **monitoraggio** vengono utilizzati. L'attenzione all'**inclusione** è letta come capacità
di adattare l'orientamento a bisogni diversi, evitando percorsi standardizzati.

La governance si articola in sotto‑categorie che chiariscono il livello di sistemicità.
Il **coordinamento** riguarda la presenza di figure dedicate, team o referenti stabili.
Il **dialogo** con docenti e studenti misura la capacità di integrare l'orientamento nelle
pratiche quotidiane, non solo in eventi sporadici. Il rapporto con le **famiglie** riflette
quanto l'orientamento sia condiviso e accompagnato, soprattutto nelle fasi decisive.
Il **monitoraggio** delle azioni è un indicatore di maturità: emerge quando il PTOF descrive
come si misurano risultati, feedback e ricadute. L'inclusione valuta l'adattamento a
**bisogni educativi speciali**, fragilità e differenze culturali.

La **didattica orientativa** misura il passaggio dall'intenzione all'azione. Si valuta
se l'esperienza degli studenti diventa leva di apprendimento, se ci sono attività
laboratoriali e pratiche, se spazi e tempi sono flessibili e se l'orientamento entra
in modo **interdisciplinare** nella didattica ordinaria. In questa dimensione, la sotto‑categoria
dell'**esperienza degli studenti** premia percorsi in cui lo studente sperimenta ruoli e scenari
reali; quella **laboratoriale** riconosce **metodologie attive**; la **flessibilità** valuta l'adattamento
di tempi, gruppi e setting; l'**interdisciplinarità** misura il coordinamento tra docenti
per collegare competenze e contenuti.

Infine, le **opportunità formative** osservano la varietà e l'accessibilità delle proposte.
Le **attività culturali**, **espressive**, **ludiche**, di **volontariato** e **sportive** non sono considerate
come extra a margine, ma come segnali di un **ecosistema orientativo** che offre esperienze
diverse e concrete per riconoscersi e scegliere.

Le sotto‑categorie delle opportunità aiutano a distinguere la **qualità dell'offerta**.
Le attività culturali mostrano apertura a linguaggi e competenze trasversali; quelle
espressive misurano spazi di creatività e identità; le proposte ludiche indicano
attenzione al benessere e alla motivazione; il volontariato segnala contatto con
comunità e cittadinanza attiva; lo sport evidenzia lavoro su disciplina, collaborazione
e salute. La valutazione cresce quando il PTOF descrive **accesso**, **continuità** e **ricadute**
di queste opportunità, non solo la loro presenza nominale.
"""
)

st.subheader("Scala di Completezza (1-7)")
st.markdown(
    """
Ogni dimensione è valutata rispetto alla sua **completezza informativa**. Il punteggio in scala 1-7 indica
quanto il PTOF riesce a trasformare le intenzioni in azioni concrete, documentate e coerenti.
"""
)

scale_data = {
    "Completezza": ["1.0 - 2.2", "2.3 - 3.4", "3.5 - 4.6", "4.7 - 5.8", "5.9 - 7.0"],
    "Descrizione": [
        "Nessun riferimento o accenni minimi",
        "Riferimenti generici, poco strutturati",
        "Presenza di azioni basilari ma non coordinate",
        "Sistema strutturato, buona copertura delle dimensioni",
        "Sistema eccellente, dettagliato e monitorato"
    ]
}

st.dataframe(scale_data, use_container_width=True, hide_index=True)

st.subheader("Indice Completezza PTOF")
st.markdown(
    """
L'**Indice di Completezza** (ex Indice RO) misura quanto il PTOF sia completo e informativo
rispetto alle tematiche dell'orientamento. Non è una classifica di qualità, ma un indicatore
di maturità documentale.

```
Indice RO = (Media_Finalità + Media_Obiettivi + Media_Governance + Media_Didattica + Media_Opportunità) / 5
```

### Interpretazione

| Range | Interpretazione |
|-------|-----------------|
| Range | Interpretazione |
|-------|-----------------|
| 1.0 - 2.8 | Copertura assente o marginale |
| 2.8 - 4.0 | Copertura parziale, elementi basilari |
| 4.0 - 5.5 | Buona copertura, sistema strutturato |
| 5.5 - 7.0 | Copertura eccellente, attività |
"""
)

st.subheader("Report narrativo e output")
st.markdown(
    """
Accanto ai punteggi, il sistema produce un **report narrativo** che spiega le valutazioni,
riporta le evidenze e collega le dimensioni tra loro. È il ponte tra i numeri e la lettura
qualitativa: per questo segue una struttura stabile e obbligatoria, che riflette il prompt
di produzione. La sequenza è sempre la stessa: **Sintesi generale** per fissare il quadro,
**Analisi dimensionale** per dettagliare sezione per sezione, **Punti di forza** e **Aree
di debolezza** per bilanciare la lettura, **Gap analysis** per evidenziare le mancanze
strutturali e **Conclusioni** per restituire una chiusura coerente e utile.

Il report nasce dai punteggi ma non li ripete: li interpreta, li giustifica con esempi e
spiega dove il PTOF è specifico o, al contrario, vago. In questa fase vengono richiamate
le evidenze testuali più rilevanti, così che chi legge possa collegare direttamente
valutazione e contenuto del documento.

**Esempio sintetico:** un punteggio alto sulla **didattica orientativa** diventa un
passaggio narrativo che cita laboratori, moduli interdisciplinari e attività pratiche
descritte nel PTOF; un punteggio basso si traduce invece in una nota che segnala
l'assenza di azioni strutturate e la presenza di riferimenti solo generici.

L'output finale è doppio: un **JSON strutturato** per analisi e confronti, e un **Markdown**
per la lettura umana. Questa doppia forma garantisce sia la riproducibilità tecnica sia
la comprensibilità per chi deve interpretare i risultati, e permette di aggiornare o
revisionare i report senza perdere la traccia delle scelte effettuate.
"""
)

st.markdown("---")

st.header("Flusso operativo")
st.markdown(
    """
Questa parte descrive come il sistema mette in pratica l'analisi: dal recupero dei documenti
alla gestione dei casi non pertinenti, fino alla registrazione delle attività svolte.
È qui che la pipeline organizza il lavoro e garantisce continuità tra un ciclo
di analisi e l'altro.
"""
)

st.subheader("Panoramica del Sistema")
st.markdown(
    """
Il workflow è progettato per essere ripetibile e trasparente. Prima si recuperano i PDF,
poi si valida la natura del documento, quindi si trasforma il contenuto in testo leggibile
(Markdown) e si avvia la pipeline multi‑agente. Ogni passaggio lascia traccia nei log e
nei file di stato, in modo che la pipeline possa essere ripresa senza perdere coerenza.

La sequenza, in sintesi, è questa:

```
Download -> Validazione PTOF -> Markdown -> Analisi multi-agente -> JSON + Report -> Controlli -> CSV -> Dashboard
```

Ogni passaggio è pensato per ridurre errori, evitare duplicazioni e aumentare la qualità
complessiva del risultato.
"""
)

st.subheader("Raccolta documenti")
st.markdown(
    """
Per trovare il PTOF, il sistema procede per gradi e non si ferma al primo tentativo.
Si parte dal portale Unica, poi si consultano i siti istituzionali, si risale
all'istituto di riferimento quando necessario e, se il documento non è ancora trovato,
si effettua una ricerca mirata sul web. Questo approccio evita buchi di copertura
soprattutto nei casi in cui il PTOF è pubblicato su piattaforme esterne.

Quando un file è già presente nel sistema, non viene riscaricato: la duplicazione
introduce rumore e rallenta le analisi.
"""
)

st.subheader("Validazione e gestione non-PTOF")
st.markdown(
    """
Prima di qualsiasi analisi, il documento viene verificato. Il controllo serve a evitare
che un regolamento, un curricolo o un verbale finisca per errore nel flusso dei PTOF.
Si controllano titolo, indizi testuali e coerenza temporale (triennio). Se il documento
non è un PTOF valido, viene scartato e archiviato separatamente.

La gestione dei **documenti non‑PTOF** è parte del processo principale: ciò che non supera
la validazione viene spostato in cartelle dedicate e le analisi generate per errore vengono
rimosse. In questo modo il dataset rimane pulito e affidabile.
"""
)

st.subheader("Architettura Multi-Agente")
st.markdown(
    """
### Pipeline completa

```
PDF -> Validazione PTOF -> Markdown -> Analyst -> Reviewer -> Refiner -> JSON + Report
                                                         |
                                                         v
                                            Controlli finali -> CSV -> Dashboard
```
"""
)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(
        """
### 🔍 Analyst Agent
È il primo lettore: estrae dati, assegna punteggi e costruisce una bozza
narrativa basata sulle evidenze presenti nel testo.
"""
    )

with col2:
    st.markdown(
        """
### 🧐 Reviewer Agent
È il controllo critico: verifica se il report cita elementi non presenti,
corregge punteggi troppo alti o troppo bassi e segnala incoerenze.
"""
    )

with col3:
    st.markdown(
        """
### ✨ Refiner Agent
È l'editor finale: integra le correzioni, rende il testo più chiaro e
assicura che il JSON e il report siano consistenti.
"""
    )

st.subheader("Metadati e Dataset")
st.markdown(
    """
Dopo l'analisi, il sistema arricchisce i dati con anagrafiche ufficiali. Questo
permette di standardizzare denominazioni, comune, area geografica e ordine di scuola.
Quando disponibile, l'anagrafica include anche la gestione (statale/paritaria) come
metadato descrittivo.

Il risultato è un dataset coerente che consente confronti affidabili tra territori
e tipologie di istituto. L'arricchimento è cruciale per leggere correttamente i risultati
su mappe e dashboard, evitando che differenze di formattazione generino errori.
"""
)

st.subheader("Registro dell'Analisi")
st.markdown(
    """
Ogni documento processato viene registrato in un **registro di analisi** che conserva
lo stato dei passaggi già svolti. Questo registro evita doppie elaborazioni, consente di
riprendere un lavoro interrotto e permette di sapere quali scuole sono state analizzate,
revisionate o scartate.

Il registro è utile anche per le revisioni: quando un report viene riletto o corretto,
lo stato viene aggiornato, così da mantenere una traccia coerente dell'intero ciclo di vita
di un'analisi.
"""
)

st.markdown("---")

st.header("Revisori e Controllo Qualità")
st.markdown(
    """
La qualità non dipende da un singolo controllo, ma da livelli successivi che entrano in gioco
quando necessario. Il **Reviewer Agent** è parte integrante della pipeline: agisce subito dopo
la prima bozza per correggere errori e incoerenze. A questo si aggiungono revisori dedicati che
operano a valle del workflow principale.

La **revisione del report** (con OpenRouter, Gemini o Ollama) arricchisce il testo con dettagli
mancanti, conferma la coerenza interna e rende la narrativa più precisa. La **revisione dei
punteggi estremi** si concentra sulle valutazioni troppo alte o troppo basse, per evitare distorsioni.

La **revisione Non‑PTOF** agisce quando un documento non è pertinente, eliminando output errati.
Infine, il **Background Reviewer/Fixer** controlla la coerenza tra punteggi, narrativa e metadati,
applicando correzioni prudenti quando emergono anomalie.
"""
)

st.markdown("---")

st.header("Catalogo Attività")
st.markdown(
    """
Il catalogo raccoglie pratiche concrete estratte dai PTOF e le rende esplorabili
per categoria, territorio, tipo scuola, target e metodologie.

Funzioni principali:
- Lista, vista raggruppata o tabellare con dettagli e citazioni.
- Mappa di distribuzione geografica e dettaglio per regione.
- Grafici di distribuzione (categoria, regione, tipo scuola).
- Incroci categoria x dimensione con conteggi e percentuali.
- Analisi statistiche con significativita ed effetto.
- Export dei dati filtrati in JSON e CSV.
"""
)

st.subheader("Legenda emoji (categorie)")
st.markdown(
    """
Le emoji aiutano a riconoscere subito la categoria di una pratica.

- 📚 Metodologie Didattiche Innovative
- 🎯 Progetti e Attivita Esemplari
- 🤝 Partnership e Collaborazioni Strategiche
- ⚙️ Azioni di Sistema e Governance
- 🌈 Buone Pratiche per l'Inclusione
- 🗺️ Esperienze Territoriali Significative
"""
)

st.subheader("File JSON del catalogo")
st.markdown(
    """
I file JSON del catalogo sono la base dati su cui lavora la dashboard.
Sono consultabili anche in forma tabellare:
"""
)
st.dataframe(
    [
        {
            "File": "data/attivita.json",
            "Contenuto": "Dataset pratiche estratte",
            "Chiavi principali": "version, last_updated, extraction_model, schools_processed, total_practices, practices[]",
        },
        {
            "File": "data/activity_registry.json",
            "Contenuto": "Registro avanzamento estrazione",
            "Chiavi principali": "version, last_updated, processed_files{}",
        },
    ],
    use_container_width=True,
    hide_index=True,
)

st.subheader("Struttura pratica (tabellare)")
st.dataframe(
    [
        {"Campo": "id", "Descrizione": "Identificativo pratica"},
        {"Campo": "school.*", "Descrizione": "Metadati scuola (codice, nome, tipo, area, territorio)"},
        {"Campo": "pratica.categoria", "Descrizione": "Categoria assegnata (6 macro categorie)"},
        {"Campo": "pratica.titolo", "Descrizione": "Titolo sintetico della pratica"},
        {"Campo": "pratica.descrizione", "Descrizione": "Descrizione dettagliata (200-500 caratteri)"},
        {"Campo": "pratica.metodologia", "Descrizione": "Metodologia descritta nel PTOF"},
        {"Campo": "pratica.tipologie_metodologia", "Descrizione": "Lista di tipologie metodologia"},
        {"Campo": "pratica.ambiti_attivita", "Descrizione": "Lista di ambiti di attivita"},
        {"Campo": "pratica.target", "Descrizione": "Destinatari della pratica"},
        {"Campo": "pratica.citazione_ptof", "Descrizione": "Citazione testuale dal PTOF"},
        {"Campo": "pratica.pagina_evidenza", "Descrizione": "Pagina evidenza (se presente)"},
        {"Campo": "contesto.*", "Descrizione": "Contesto (maturity_index, punteggi, partnership, attivita)"},
    ],
    use_container_width=True,
    hide_index=True,
)

st.subheader("Registro estrazione (tabellare)")
st.dataframe(
    [
        {"Campo": "processed_files{codice}.file_hash", "Descrizione": "Hash file sorgente"},
        {"Campo": "processed_files{codice}.processed_at", "Descrizione": "Timestamp elaborazione"},
        {"Campo": "processed_files{codice}.practices_count", "Descrizione": "Numero pratiche estratte"},
        {"Campo": "processed_files{codice}.model_used", "Descrizione": "Modello usato in estrazione"},
    ],
    use_container_width=True,
    hide_index=True,
)

st.markdown("---")

st.header("Trasparenza: prompt e dati")

st.subheader("Criteri catalogo buone pratiche")
st.markdown(
    """
Il catalogo e costruito da estrazioni automatiche su testi PTOF.
Le specifiche operative sono:

- Categorie obbligatorie (6): Metodologie Didattiche Innovative, Progetti e Attivita Esemplari,
  Partnership e Collaborazioni Strategiche, Azioni di Sistema e Governance,
  Buone Pratiche per l'Inclusione, Esperienze Territoriali Significative.
- Tipologie metodologia: elenco predefinito (es. STEM/STEAM, Flipped Classroom, PBL, Cooperative Learning, ecc.).
- Ambiti di attivita: elenco predefinito (es. Orientamento, Inclusione, PCTO, Cittadinanza, ecc.).
- Criterio di selezione: solo pratiche concrete e specifiche con evidenza testuale nel PTOF;
  sono escluse formulazioni generiche.
- Limite estrazione: massimo 5 pratiche per chunk di testo.
- Campi richiesti per pratica: titolo, descrizione, metodologia, target, categoria, tipologie_metodologia,
  ambiti_attivita, citazione_ptof, pagina_evidenza (se presente), partnership_coinvolte (solo per categoria partnership).
"""
)

sections = label_prompt_sections(load_prompt_sections(PROMPTS_FILE))

prompt_tabs = st.tabs(["Prompt - Codice", "Prompt - Tabella"])
with prompt_tabs[0]:
    st.markdown("Prompt base (config/prompts.md)")
    if not sections:
        st.info("Prompts non disponibili: file config/prompts.md non trovato.")
    else:
        for title, content in sections:
            with st.expander(title):
                st.code(content, language="text")

    with st.expander("Review report (OpenRouter/Gemini) - prompt"):
        st.code(REPORT_REVIEW_PROMPT.strip(), language="text")

    with st.expander("Review report Ollama - prompt chunk"):
        st.code(OLLAMA_CHUNK_PROMPT.strip(), language="text")

    with st.expander("Review report Ollama - prompt finale"):
        st.code(OLLAMA_FINAL_PROMPT.strip(), language="text")

    with st.expander("Review punteggi estremi (OpenRouter/Gemini/Ollama) - prompt"):
        st.code(SCORE_REVIEW_PROMPT.strip(), language="text")

    with st.expander("Estrazione buone pratiche - prompt"):
        st.code(BEST_PRACTICE_EXTRACTION_PROMPT.strip(), language="text")

with prompt_tabs[1]:
    prompt_rows = []
    if sections:
        prompt_rows.append(
            {
                "Prompt": f"Prompt base pipeline (config/prompts.md) - {len(sections)} sezioni",
                "Uso": "Prompt base pipeline",
                "Input": "Testo PTOF / contesto",
                "Output": "JSON o testo (vedi codice)",
            }
        )
    else:
        prompt_rows.append(
            {
                "Prompt": "Prompt base pipeline (config/prompts.md)",
                "Uso": "Prompt base pipeline",
                "Input": "Testo PTOF / contesto",
                "Output": "JSON o testo (vedi codice)",
            }
        )

    prompt_rows.extend(
        [
            {
                "Prompt": "Review report (OpenRouter/Gemini)",
                "Uso": "Arricchisce report MD con dettagli dal PTOF",
                "Input": "Testo PTOF, report MD",
                "Output": "Markdown report arricchito",
            },
            {
                "Prompt": "Review report Ollama - chunk",
                "Uso": "Estrae arricchimenti da chunk PTOF",
                "Input": "Chunk PTOF, report MD, riepilogo score",
                "Output": "JSON arricchimenti/correzioni",
            },
            {
                "Prompt": "Review report Ollama - finale",
                "Uso": "Compone report finale",
                "Input": "Report attuale, arricchimenti, correzioni",
                "Output": "Markdown finale",
            },
            {
                "Prompt": "Review punteggi estremi",
                "Uso": "Rivede punteggi troppo alti o bassi",
                "Input": "Testo PTOF, JSON punteggi",
                "Output": "JSON aggiornamenti",
            },
            {
                "Prompt": "Estrazione buone pratiche",
                "Uso": "Estrae pratiche concrete dal PTOF",
                "Input": "Chunk PTOF",
                "Output": "JSON pratiche",
            },
        ]
    )

    st.dataframe(prompt_rows, use_container_width=True, hide_index=True)

json_tabs = st.tabs(["JSON - Codice", "JSON - Tabella"])
with json_tabs[0]:
    st.markdown("Analisi PTOF - output JSON")
    st.code(ANALYSIS_OUTPUT_SCHEMA_JSON.strip(), language="json")

    st.markdown("Review punteggi estremi - output JSON")
    st.code(SCORE_REVIEW_OUTPUT_JSON.strip(), language="json")

    st.markdown("Review report Ollama - output JSON (chunk)")
    st.code(OLLAMA_CHUNK_OUTPUT_JSON.strip(), language="json")

    st.markdown("Catalogo attività - output prompt")
    st.code(BEST_PRACTICE_EXTRACTION_JSON.strip(), language="json")

    st.markdown("Catalogo attività - dataset (data/attivita.json)")
    st.code(BEST_PRACTICES_DATASET_JSON.strip(), language="json")

    st.markdown("Catalogo attività - registry (data/activity_registry.json)")
    st.code(BEST_PRACTICE_REGISTRY_JSON.strip(), language="json")

    st.markdown("Anagrafica comuni (data/comuni_italiani.json)")
    st.code(COMUNI_ITALIANI_JSON.strip(), language="json")

with json_tabs[1]:
    json_rows = [
        {
            "JSON": "analysis_results/{CODICE}_analysis.json",
            "Dove": "Output analisi PTOF",
            "Scopo": "Risultati strutturati + report",
            "Chiavi principali": "metadata, ptof_section2, narrative",
        },
        {
            "JSON": "score_review_output.json (prompt)",
            "Dove": "Review punteggi",
            "Scopo": "Correzioni punteggi estremi",
            "Chiavi principali": "score_updates[], review_notes",
        },
        {
            "JSON": "ollama_chunk_output.json (prompt)",
            "Dove": "Review report chunk",
            "Scopo": "Arricchimenti e correzioni",
            "Chiavi principali": "enrichments[], corrections[], orientamento_*",
        },
        {
            "JSON": "activity_extraction_output.json (prompt)",
            "Dove": "Estrazione attività",
            "Scopo": "Attività estratte per chunk",
            "Chiavi principali": "pratiche[]",
        },
        {
            "JSON": "data/attivita.json",
            "Dove": "Dataset catalogo",
            "Scopo": "Dataset attività estratte",
            "Chiavi principali": "version, last_updated, extraction_model, schools_processed, total_practices, practices[]",
        },
        {
            "JSON": "data/activity_registry.json",
            "Dove": "Registro estrazione",
            "Scopo": "Stato e avanzamento",
            "Chiavi principali": "version, last_updated, processed_files{}",
        },
        {
            "JSON": "data/comuni_italiani.json",
            "Dove": "Anagrafica territori",
            "Scopo": "Normalizzazione comuni/province/regioni",
            "Chiavi principali": "nome, codice, zona{}, regione{}, provincia{}, sigla, cap, popolazione",
        },
    ]

    st.dataframe(json_rows, use_container_width=True, hide_index=True)

    st.markdown("Struttura pratica (tabellare)")
    st.dataframe(
        [
            {"Campo": "id", "Descrizione": "Identificativo pratica"},
            {"Campo": "school.*", "Descrizione": "Metadati scuola (codice, nome, tipo, area, territorio)"},
            {"Campo": "pratica.categoria", "Descrizione": "Categoria assegnata (6 macro categorie)"},
            {"Campo": "pratica.titolo", "Descrizione": "Titolo sintetico della pratica"},
            {"Campo": "pratica.descrizione", "Descrizione": "Descrizione dettagliata (200-500 caratteri)"},
            {"Campo": "pratica.metodologia", "Descrizione": "Metodologia descritta nel PTOF"},
            {"Campo": "pratica.tipologie_metodologia", "Descrizione": "Lista di tipologie metodologia"},
            {"Campo": "pratica.ambiti_attivita", "Descrizione": "Lista di ambiti di attivita"},
            {"Campo": "pratica.target", "Descrizione": "Destinatari della pratica"},
            {"Campo": "pratica.citazione_ptof", "Descrizione": "Citazione testuale dal PTOF"},
            {"Campo": "pratica.pagina_evidenza", "Descrizione": "Pagina evidenza (se presente)"},
            {"Campo": "contesto.*", "Descrizione": "Contesto (maturity_index, punteggi, partnership, attivita)"},
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("Registro estrazione (tabellare)")
    st.dataframe(
        [
            {"Campo": "processed_files{codice}.file_hash", "Descrizione": "Hash file sorgente"},
            {"Campo": "processed_files{codice}.processed_at", "Descrizione": "Timestamp elaborazione"},
            {"Campo": "processed_files{codice}.practices_count", "Descrizione": "Numero pratiche estratte"},
            {"Campo": "processed_files{codice}.model_used", "Descrizione": "Modello usato in estrazione"},
        ],
        use_container_width=True,
        hide_index=True,
    )

st.markdown("---")

st.header("Avvertenze e Buone Pratiche")

st.warning(
    """
Attenzione: i punteggi sono generati da modelli di intelligenza artificiale e possono contenere errori.
"""
)

st.markdown(
    """
### Limitazioni note

La qualità dipende dai documenti di partenza. PDF scannerizzati, impaginazioni complesse
o testo poco chiaro possono ridurre la precisione. Inoltre, modelli diversi possono produrre
valutazioni leggermente differenti. Per questo i risultati vanno letti come indicatori
comparativi e non come giudizi assoluti.

### Buone pratiche

- usare i punteggi per confrontare, non per etichettare
- leggere sempre il report narrativo insieme ai numeri
- considerare il contesto specifico della scuola
"""
)

st.markdown("---")

st.header("Documenti e Fonti")

st.markdown(
    """
La base documentale è composta dai PTOF originali, dalle versioni in Markdown
utilizzate per l'analisi e dai dataset di sintesi. Queste fonti consentono sia
la lettura qualitativa sia la comparazione quantitativa tra scuole.

### 🛡️ Criteri di Esclusione e Qualità del Dato
Per garantire l'affidabilità delle analisi, il sistema applica criteri rigorosi di esclusione:
1. **Validazione PTOF**: I documenti che non superano i controlli euristici (es. numero pagine, parole chiave) vengono scartati prima dell'analisi.
2. **Soglia Minima di Rilevanza (Score <= 2.0)**: Qualsiasi analisi che produca un Indice RO (Robustezza dell'Orientamento) inferiore o uguale a 2.0 viene automaticamente scartata ed eliminata. Un punteggio così basso indica con quasi assoluta certezza che il documento non è un PTOF valido o non contiene alcuna informazione pertinente sull'orientamento, rendendo l'analisi priva di valore.
"""
)

st.markdown(
    """
| Fonte | Descrizione | Utilizzo |
|-------|-------------|----------|
| **metadata_enrichment.csv** | Anagrafica MIUR | Denominazione, Comune, Tipo scuola |
| **PTOF Documents** | Documenti scolastici | Analisi testuale |
"""
)


with st.expander("Riferimenti Normativi"):
    st.markdown(
        """
- **DM 328/2022** - Adozione delle Linee guida per l'orientamento
- **PTOF** - Piano Triennale dell'Offerta Formativa (L. 107/2015)
- **Orientamento permanente** - Accordo Stato-Regioni 2014
"""
    )

render_footer()
