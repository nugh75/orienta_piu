# 📖 Metodologia - Documentazione del sistema

import streamlit as st

st.set_page_config(page_title="Metodologia", page_icon="📖", layout="wide")

st.title("📖 Metodologia di Analisi")

st.markdown("""
Questa sezione documenta la metodologia utilizzata per l'analisi automatizzata dei documenti PTOF 
(Piano Triennale dell'Offerta Formativa) delle scuole italiane.
""")

st.markdown("---")

# 1. Overview
st.header("1️⃣ Panoramica del Sistema")
st.markdown("""
Il sistema utilizza un'architettura **multi-agente** basata su Large Language Models (LLM) per:

1. **Estrarre** informazioni strutturate dai documenti PTOF
2. **Valutare** la qualità delle strategie di orientamento
3. **Generare** report narrativi con evidenze testuali
4. **Aggregare** i dati per analisi comparative

### Pipeline di Elaborazione

```
PDF → Markdown → 3-Agent Analysis → JSON + Report → Dashboard
```
""")

st.markdown("---")

# 2. Agent Architecture
st.header("2️⃣ Architettura Multi-Agente")

st.markdown("""
### Pipeline Completo

```
PDF → Markdown → Analyst → Reviewer → Refiner (GPT-OSS) → JSON + Report
                                                              ↓
                                           refine_metadata.py → align_metadata.py → CSV → Dashboard
```
""")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    ### 🔍 Analyst Agent
    **Modello:** gemma3:27b
    
    **Ruolo:**
    - Legge il documento PTOF
    - Estrae dati strutturati
    - Assegna punteggi iniziali
    - Genera report narrativo
    """)

with col2:
    st.markdown("""
    ### 🧐 Reviewer Agent
    **Modello:** qwen3:32b
    
    **Ruolo:**
    - Red-team dell'analisi
    - Rileva allucinazioni
    - Verifica evidenze testuali
    - Suggerisce correzioni
    """)

with col3:
    st.markdown("""
    ### ✨ Refiner Agent
    **Modello:** gpt-oss:20b
    
    **Ruolo:**
    - Incorpora feedback del Reviewer
    - Corregge punteggi errati
    - Raffina testo del report
    - Produce JSON + MD finale
    """)

st.markdown("---")

# 2b. Metadata Pipeline
st.header("2️⃣b Pipeline Raffinamento Metadati")

st.markdown("""
Dopo l'analisi LLM, viene eseguito un processo automatico di raffinamento dei metadati:
""")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    ### 📄 refine_metadata.py
    **Scopo:** Estrarre metadati mancanti dal testo
    
    **Operazioni:**
    - Analizza il Markdown del PTOF
    - Estrae Denominazione e Comune tramite Regex
    - Deduce Ordine/Grado dal contenuto
    - Riempie i campi "ND" nel JSON
    """)

with col2:
    st.markdown("""
    ### 🔗 align_metadata.py
    **Scopo:** Allineamento e generazione Dataset
    
    **Operazioni:**
    - Standardizza i codici scuola
    - Arricchisce JSON con anagrafica MIUR (CSV)
    - Calcola medie e Indice di Robustezza
    - Genera il file `analysis_summary.csv` per la Dashboard
    - **Nota:** Disabilitata integrazione INVALSI per privacy
    """)

st.markdown("---")

# 3. Scoring Framework
st.header("3️⃣ Framework di Valutazione")

st.markdown("""
Il sistema valuta **7 dimensioni principali** dell'orientamento scolastico, basate sulle 
Linee Guida Nazionali per l'Orientamento (DM 328/2022).
""")

st.markdown("""
| Sezione | Dimensione | Sottodimensioni |
|---------|------------|-----------------|
| **2.1** | Sezione Dedicata | Presenza di una sezione specifica nel PTOF |
| **2.2** | Partnership | Partner nominati, reti territoriali |
| **2.3** | Finalità | Attitudini, Interessi, Progetto di vita, Transizioni, Capacità orientative |
| **2.4** | Obiettivi | Abbandono, Continuità territoriale, NEET, Lifelong learning |
| **2.5** | Governance | Coordinamento, Dialogo, Genitori, Monitoraggio, Inclusione |
| **2.6** | Didattica | Esperienza studenti, Laboratoriale, Flessibilità, Interdisciplinare |
| **2.7** | Opportunità | Culturali, Espressive, Ludiche, Volontariato, Sportive |
""")

st.markdown("---")

# 4. Likert Scale
st.header("4️⃣ Scala di Punteggio (Likert 1-7)")

st.markdown("""
Ogni sottodimensione è valutata su una scala Likert a 7 punti:
""")

scale_data = {
    'Punteggio': [1, 2, 3, 4, 5, 6, 7],
    'Livello': ['Assente', 'Minimo', 'Basilare', 'Sufficiente', 'Buono', 'Molto buono', 'Eccellente'],
    'Descrizione': [
        'Nessun riferimento nel documento',
        'Accenni generici o indiretti',
        'Menzione esplicita ma non sviluppata',
        'Azioni presenti ma basilari, non strutturate',
        'Azioni strutturate e descritte con dettaglio',
        'Sistema integrato con azioni interconnesse',
        'Sistema eccellente, monitorato e con evidenze di impatto'
    ]
}

st.dataframe(scale_data, width="stretch", hide_index=True)

st.markdown("---")

# 5. Indice di Robustezza
st.header("5️⃣ Indice di Robustezza")

st.markdown("""
L'**Indice di Robustezza del Sistema di Orientamento** (IRSO) è calcolato come media delle 5 medie dimensionali:

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
""")

st.markdown("---")

# 6. Data Sources
st.header("6️⃣ Fonti Dati")

st.markdown("""
Il sistema integra dati da multiple fonti per l'arricchimento dei metadati:

| Fonte | Descrizione | Utilizzo |
|-------|-------------|----------|
| **metadata_enrichment.csv** | Anagrafica ufficiale MIUR | Denominazione, Comune, Tipo scuola |
| **invalsi_unified.csv** | Dati INVALSI | Area geografica, Territorio |
| **PTOF Documents** | Documenti scolastici | Analisi testuale |
""")

st.markdown("---")

# 7. Limitations
st.header("7️⃣ Limitazioni e Considerazioni")

st.warning("""
**Attenzione:** I punteggi sono generati da modelli di intelligenza artificiale e possono contenere errori.
""")

st.markdown("""
### Limitazioni note:

1. **Qualità dei PDF**: Documenti scannerizzati o con formattazione complessa possono essere estratti in modo incompleto
2. **Variabilità LLM**: Modelli diversi possono produrre punteggi leggermente diversi
3. **Contesto limitato**: Il modello analizza solo il testo del PTOF, non altre fonti
4. **Allucinazioni**: Nonostante il processo di review, possono persistere errori interpretativi

### Best Practices:

- ✅ Usare i punteggi come indicatori comparativi, non assoluti
- ✅ Verificare le evidenze testuali nel report
- ✅ Considerare il contesto specifico della scuola
- ✅ Integrare con altri dati qualitativi
""")

st.markdown("---")

# 8. Technical Details
st.header("8️⃣ Dettagli Tecnici")

with st.expander("Schema JSON Output"):
    st.code("""
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
    """, language="json")

with st.expander("Riferimenti Normativi"):
    st.markdown("""
    - **DM 328/2022** - Adozione delle Linee guida per l'orientamento
    - **PTOF** - Piano Triennale dell'Offerta Formativa (L. 107/2015)
    - **Orientamento permanente** - Accordo Stato-Regioni 2014
    """)

st.markdown("---")

st.caption("📖 Documentazione metodologica - PRIN 2022")
