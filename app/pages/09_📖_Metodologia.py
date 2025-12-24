# 📖 Metodologia - Documentazione del sistema

from pathlib import Path

import streamlit as st

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

CRITERI PUNTEGGIO (1-7):
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


st.set_page_config(page_title="Metodologia", page_icon="📖", layout="wide")

st.title("📖 Metodologia di Analisi")

st.markdown(
    """
Questa sezione racconta, in modo narrativo e trasparente, come analizziamo i PTOF
(Piano Triennale dell'Offerta Formativa) e come manteniamo la qualità dei risultati.
L'obiettivo non è soltanto estrarre informazioni, ma costruire una lettura coerente
e confrontabile tra scuole, capace di restituire un quadro chiaro dell'orientamento.
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
precisa (Sintesi generale, Analisi dimensionale, Punti di forza, Aree di debolezza,
Gap analysis, Conclusioni). In questa sezione trovi come vengono definite le dimensioni,
come si assegnano i punteggi e come nasce il report finale, fino all'**Indice di Robustezza**
che sintetizza la qualità complessiva dell'orientamento.
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

st.subheader("Scala di Punteggio (Likert 1-7)")
st.markdown(
    """
Ogni sottodimensione è valutata su una scala Likert a 7 punti. La scala non è un giudizio
morale, ma una misura di quanto il PTOF riesce a trasformare le intenzioni in azioni
concrete, documentate e coerenti.
"""
)

scale_data = {
    "Punteggio": [1, 2, 3, 4, 5, 6, 7],
    "Livello": [
        "Assente",
        "Minimo",
        "Basilare",
        "Sufficiente",
        "Buono",
        "Molto buono",
        "Eccellente",
    ],
    "Descrizione": [
        "Nessun riferimento nel documento",
        "Accenni generici o indiretti",
        "Menzione esplicita ma non sviluppata",
        "Azioni presenti ma basilari, non strutturate",
        "Azioni strutturate e descritte con dettaglio",
        "Sistema integrato con azioni interconnesse",
        "Sistema eccellente, monitorato e con evidenze di impatto",
    ],
}

st.dataframe(scale_data, use_container_width=True, hide_index=True)

st.subheader("Indice di Robustezza")
st.markdown(
    """
L'**Indice di Robustezza del Sistema di Orientamento** (IRSO) sintetizza la solidità
complessiva del sistema di orientamento della scuola. Non sostituisce i punteggi
analitici, ma offre una misura sintetica utile per confronti rapidi tra istituti.

```
IRSO = (Media_Finalità + Media_Obiettivi + Media_Governance + Media_Didattica + Media_Opportunità) / 5
```

### Interpretazione

| Range | Interpretazione |
|-------|-----------------|
| 1.0 - 2.0 | Sistema assente o gravemente carente |
| 2.1 - 3.5 | Sistema basilare, richiede interventi significativi |
| 3.6 - 4.5 | Sistema sufficiente, margini di miglioramento |
| 4.6 - 5.5 | Sistema buono, ben strutturato |
| 5.6 - 7.0 | Sistema eccellente, benchmark di riferimento |
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

st.header("Workflow operativo e agente principale")
st.markdown(
    """
Questa parte descrive come il sistema mette in pratica l'analisi: dal recupero dei documenti
alla gestione dei casi non pertinenti, fino alla registrazione delle attività svolte.
È qui che l'agente principale organizza il lavoro e garantisce continuità tra un ciclo
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

st.subheader("Strategie di Download")
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

st.header("Prompt degli Agenti e delle Revisioni")

st.markdown(
    """
Per trasparenza, riportiamo i prompt utilizzati nelle diverse fasi. Sono mostrati
integralmente, con segnaposto dove viene inserito il testo del PTOF o del report.
"""
)

sections = label_prompt_sections(load_prompt_sections(PROMPTS_FILE))
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
"""
)

st.markdown(
    """
| Fonte | Descrizione | Utilizzo |
|-------|-------------|----------|
| **metadata_enrichment.csv** | Anagrafica MIUR | Denominazione, Comune, Tipo scuola |
| **comuni_italiani.json** | Elenco comuni/province | Normalizzazione geografica |
| **PTOF Documents** | Documenti scolastici | Analisi testuale |
"""
)

with st.expander("Schema JSON Output"):
    st.code(
        """
{
  "metadata": {
    "school_id": "MIIS08900V",
    "denominazione": "...",
    "ordine_grado": "I Grado|II Grado",
    "tipo_scuola": "Liceo|Tecnico|Professionale|I Grado",
    "area_geografica": "Nord Ovest|Nord Est|Centro|Sud|Isole"
  },
  "ptof_section2": {
    "2_1_ptof_orientamento_sezione_dedicata": {
      "has_sezione_dedicata": 0|1,
      "score": 1-7,
      "note": "..."
    },
    "2_2_partnership": {
      "partner_nominati": ["..."],
      "partnership_count": N
    },
    "2_3_finalita": {
      "finalita_attitudini": { "score": 1-7 },
      ...
    },
    ...
  },
  "narrative": "Report markdown..."
}
        """,
        language="json",
    )

with st.expander("Riferimenti Normativi"):
    st.markdown(
        """
- **DM 328/2022** - Adozione delle Linee guida per l'orientamento
- **PTOF** - Piano Triennale dell'Offerta Formativa (L. 107/2015)
- **Orientamento permanente** - Accordo Stato-Regioni 2014
"""
    )

st.markdown("---")

st.caption("Documentazione metodologica - PRIN 2022")
