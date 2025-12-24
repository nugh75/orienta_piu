# 📖 Metodologia - Documentazione del sistema

import streamlit as st

st.set_page_config(page_title="Metodologia", page_icon="📖", layout="wide")

st.title("📖 Metodologia di Analisi")

st.markdown(
    """
Questa sezione racconta, in modo narrativo, come analizziamo i PTOF
(Piano Triennale dell'Offerta Formativa) e come manteniamo la qualità
in ogni fase, dalla raccolta dei documenti fino alla dashboard.
"""
)

st.markdown("---")

# 1. Overview
st.header("1️⃣ Panoramica del Sistema")
st.markdown(
    """
Il sistema lavora come una piccola redazione: prima si raccolgono i documenti,
poi si verifica che siano realmente PTOF, quindi si costruisce un'analisi coerente
e infine si rende tutto confrontabile nella dashboard.

La sequenza, in sintesi, è questa:

```
Download → Validazione PTOF → Markdown → Analisi multi-agente → JSON + Report → Controlli → CSV → Dashboard
```
"""
)

st.markdown("---")

# 1b. Download Strategy
st.header("1️⃣b Strategie di Download")
st.markdown(
    """
Per trovare il PTOF, il sistema procede per gradi. Si parte dal portale Unica,
poi si passa al sito istituzionale della scuola, si estende la ricerca al codice
dell'istituto di riferimento e, se serve, si cerca sul web. In questo modo
massimizziamo la copertura e riduciamo i vuoti.

In parallelo, controlliamo se il file è già stato scaricato o analizzato:
questo evita duplicazioni e mantiene il lavoro pulito.
"""
)

st.markdown("---")

# 2. Agent Architecture
st.header("2️⃣ Architettura Multi-Agente")

st.markdown(
    """
### Pipeline completa

```
PDF → Validazione PTOF → Markdown → Analyst → Reviewer → Refiner → JSON + Report
                                                        ↓
                                       Controlli finali → CSV → Dashboard
```
"""
)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(
        """
    ### 🔍 Analyst Agent
    È il primo lettore: estrae i contenuti chiave, organizza le informazioni
    e propone un primo punteggio per ogni dimensione.
    """
    )

with col2:
    st.markdown(
        """
    ### 🧐 Reviewer Agent
    È il controllo qualità interno: verifica che ciò che è scritto abbia
    riscontro nel testo e segnala punti deboli o incoerenze.
    """
    )

with col3:
    st.markdown(
        """
    ### ✨ Refiner Agent
    È l'editor finale: integra le correzioni, rafforza la chiarezza narrativa
    e produce un output consistente e confrontabile.
    """
    )

st.markdown("---")

# 2b. Metadata Pipeline
st.header("2️⃣b Metadati e Dataset")

st.markdown(
    """
Dopo l'analisi, il sistema arricchisce i dati anagrafici per rendere affidabili
confronti e mappe. È un passaggio fondamentale: i numeri sono utili solo se i
contesti sono corretti.
"""
)

col1, col2 = st.columns(2)

with col1:
    st.markdown(
        """
    ### 📌 Arricchimento contestuale
    Unisce il contenuto del PTOF con le anagrafiche ufficiali, completando
    denominazione, comune, ordine di scuola e territorio.
    """
    )

with col2:
    st.markdown(
        """
    ### 🧭 Allineamento e dataset finale
    Normalizza codici e geografie, calcola indicatori di sintesi e genera
    il dataset usato nella dashboard.
    """
    )

st.markdown("---")

# 2c. Review Layers
st.header("2️⃣c Revisione e Controllo Qualità")

st.markdown(
    """
La qualità non dipende da un unico controllo: il sistema prevede più livelli
di revisione, attivabili quando serve.

**Revisione interna (Reviewer Agent):** è sempre presente nella pipeline e serve
per correggere subito errori o interpretazioni troppo deboli.

**Revisione del report (Review Slow / Review Gemini / Review Ollama):** un secondo
passaggio narrativo che arricchisce il testo e rende più precise le evidenze.
Può essere eseguita con modelli cloud (OpenRouter o Gemini) oppure in locale con Ollama.

**Revisione dei punteggi estremi (Review Scores: OpenRouter / Gemini / Ollama):**
quando un punteggio è molto alto o molto basso, si effettua una verifica dedicata
per evitare distorsioni.

**Revisione Non-PTOF:** se un documento non è realmente un PTOF, l'analisi viene
rimossa e il file viene archiviato, mantenendo pulito il dataset.
"""
)

st.markdown("---")

# 3. Pesi e Contrappesi
st.header("3️⃣ Pesi e Contrappesi (Qualità e Affidabilità)")

st.markdown(
    """
Il punteggio cresce quando il PTOF è chiaro, articolato e ricco di azioni concrete.
Allo stesso tempo, introduciamo contrappesi per ridurre errori o illusioni.

**Cosa spinge il punteggio verso l'alto:**
- evidenze testuali chiare e specifiche
- coerenza tra obiettivi, attività e risultati attesi
- presenza di una sezione dedicata all'orientamento

**Cosa riduce il rischio di errore:**
- validazione PTOF prima dell'analisi
- revisione interna e post-analisi
- revisione degli estremi
- arricchimento con anagrafiche ufficiali
"""
)

st.markdown("---")

# 4. Scoring Framework
st.header("4️⃣ Framework di Valutazione")

st.markdown(
    """
L'orientamento viene letto in 7 dimensioni principali, ispirate alle
Linee Guida Nazionali per l'Orientamento (DM 328/2022).
"""
)

st.markdown(
    """
| Sezione | Dimensione | Sottodimensioni |
|---------|------------|-----------------|
| **2.1** | Sezione Dedicata | Presenza di una sezione specifica nel PTOF |
| **2.2** | Partnership | Partner nominati, reti territoriali |
| **2.3** | Finalità | Attitudini, Interessi, Progetto di vita, Transizioni, Capacità orientative |
| **2.4** | Obiettivi | Abbandono, Continuità territoriale, NEET, Lifelong learning |
| **2.5** | Governance | Coordinamento, Dialogo, Genitori, Monitoraggio, Inclusione |
| **2.6** | Didattica | Esperienza studenti, Laboratoriale, Flessibilità, Interdisciplinare |
| **2.7** | Opportunità | Culturali, Espressive, Ludiche, Volontariato, Sportive |
"""
)

st.markdown("---")

# 5. Likert Scale
st.header("5️⃣ Scala di Punteggio (Likert 1-7)")

st.markdown(
    """
Ogni sottodimensione è valutata su una scala Likert a 7 punti:
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

st.markdown("---")

# 6. Indice di Robustezza
st.header("6️⃣ Indice di Robustezza")

st.markdown(
    """
L'**Indice di Robustezza del Sistema di Orientamento** (IRSO) sintetizza la solidità
complessiva del sistema di orientamento della scuola, come media di 5 dimensioni.

```
IRSO = (Media_Finalità + Media_Obiettivi + Media_Governance + Media_Didattica + Media_Opportunità) / 5
```

### Interpretazione

| Range | Interpretazione |
|-------|-----------------|
| 1.0 - 2.0 | 🔴 Sistema assente o gravemente carente |
| 2.1 - 3.5 | 🟠 Sistema basilare, richiede interventi significativi |
| 3.6 - 4.5 | 🟡 Sistema sufficiente, margini di miglioramento |
| 4.6 - 5.5 | 🟢 Sistema buono, ben strutturato |
| 5.6 - 7.0 | 🟣 Sistema eccellente, benchmark di riferimento |
"""
)

st.markdown("---")

# 7. Data Sources
st.header("7️⃣ Fonti Dati")

st.markdown(
    """
Le informazioni provengono da più fonti, integrate per fornire un quadro completo.
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

st.markdown("---")

# 8. Limitations
st.header("8️⃣ Limitazioni e Considerazioni")

st.warning(
    """
**Attenzione:** I punteggi sono generati da modelli di intelligenza artificiale e possono contenere errori.
"""
)

st.markdown(
    """
### Limitazioni note

La qualità dipende dai documenti di partenza: PDF scannerizzati, impaginazioni complesse
o testo poco chiaro possono ridurre la precisione. Inoltre, modelli diversi possono dare
risultati leggermente differenti. Per questo la lettura va sempre interpretata come una
misura comparativa.

### Buone pratiche

- usare i punteggi per confrontare, non per giudizi assoluti
- leggere il report narrativo insieme ai numeri
- considerare il contesto specifico della scuola
"""
)

st.markdown("---")

# 9. Approfondimenti
st.header("9️⃣ Approfondimenti (opzionali)")

st.markdown(
    """
Se vuoi entrare nei dettagli tecnici o normativi, trovi qui le informazioni di supporto.
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

st.caption("📖 Documentazione metodologica - PRIN 2022")
