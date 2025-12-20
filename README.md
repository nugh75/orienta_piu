# 📚 PTOF Orientation Analysis System

Sistema automatizzato per l'analisi dei documenti PTOF (Piano Triennale dell'Offerta Formativa) delle scuole italiane, valutando le strategie di orientamento attraverso un'architettura multi-agente LLM.

## 🏗️ Architettura

```
PDF → Markdown → 3-Agent Analysis → JSON + Report → Dashboard
         ↓             ↓                  ↓
    ptof_md/     LLM Pipeline     analysis_results/
                      ↓
              refine_metadata.py → align_metadata.py → CSV
```

### Pipeline Multi-Agente
| Agente | Modello | Ruolo |
|--------|---------|-------|
| **Analyst** | gemma3:27b | Estrae dati strutturati + scrive report narrativo |
| **Reviewer** | qwen3:32b | Red-team dell'analisi, rileva allucinazioni |
| **Refiner** | gemma3:27b | Corregge punteggi e raffina il report |

### Pipeline di Metadati (integrato)
Dopo ogni analisi, vengono eseguiti automaticamente:
1. `refine_metadata.py` - Estrae metadati ND dai file MD
2. `align_metadata.py` - Sincronizza JSON e ricostruisce CSV

## 📁 Struttura Directory

```
├── app/                        # Entry point applicazioni
│   ├── agentic_pipeline.py     # Pipeline 3-agenti principale
│   └── dashboard.py            # Visualizzazione Streamlit
├── src/
│   ├── processing/
│   │   ├── align_metadata.py   # Allineamento metadati JSON ↔ CSV
│   │   ├── refine_metadata.py  # Estrazione ND da file MD
│   │   ├── rebuild_csv.py      # Ricostruzione CSV (legacy)
│   │   └── convert_pdf.py      # Conversione PDF → Markdown
│   ├── validation/             # Script validazione PTOF
│   └── utils/                  # Config loaders
├── config/
│   ├── prompts.md              # Tutti i prompt LLM (centralizzati)
│   └── models.json             # Configurazione modelli Ollama
├── data/
│   ├── analysis_summary.csv    # Dashboard data source
│   ├── metadata_enrichment.csv # Anagrafica scuole (50k+)
│   └── invalsi_unified.csv     # Dati valutazione INVALSI
├── ptof/                       # Documenti PDF sorgente
├── ptof_md/                    # File Markdown convertiti
├── analysis_results/           # Output JSON + MD reports
└── logs/                       # Log esecuzione pipeline
```

## 🚀 Quick Start

### 1. Installa Dipendenze
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Avvia Pipeline di Analisi
```bash
nohup python -u app/agentic_pipeline.py > logs/pipeline.log 2>&1 &
```

### 3. Avvia Dashboard
```bash
streamlit run app/dashboard.py --server.port 8501
```

### 4. Monitoraggio
```bash
tail -f logs/pipeline.log
```

## 📊 Schema Output JSON

Ogni scuola genera `{code}_PTOF_analysis.json` con questa struttura:

```json
{
  "metadata": {
    "school_id": "MIIS08900V",
    "denominazione": "...",
    "comune": "...",
    "area_geografica": "Nord|Centro|Sud",
    "ordine_grado": "I Grado|II Grado",
    "tipo_scuola": "Liceo|Tecnico|Professionale|I Grado",
    "territorio": "Metropolitano|Non Metropolitano"
  },
  "ptof_section2": {
    "2_1_ptof_orientamento_sezione_dedicata": {
      "has_sezione_dedicata": 0|1,
      "score": 1-7,
      "note": "..."
    },
    "2_2_partnership": {
      "partner_nominati": ["..."],
      "partnership_count": N,
      "score": 1-7
    },
    "2_3_finalita": {
      "finalita_attitudini": { "score": 1-7 },
      "finalita_interessi": { "score": 1-7 },
      "finalita_progetto_vita": { "score": 1-7 },
      "finalita_transizioni_formative": { "score": 1-7 },
      "finalita_capacita_orientative_opportunita": { "score": 1-7 }
    },
    "2_4_obiettivi": {
      "obiettivo_ridurre_abbandono": { "score": 1-7 },
      "obiettivo_continuita_territorio": { "score": 1-7 },
      "obiettivo_contrastare_neet": { "score": 1-7 },
      "obiettivo_lifelong_learning": { "score": 1-7 }
    },
    "2_5_azioni_sistema": {
      "azione_coordinamento_servizi": { "score": 1-7 },
      "azione_dialogo_docenti_studenti": { "score": 1-7 },
      "azione_rapporto_scuola_genitori": { "score": 1-7 },
      "azione_monitoraggio_azioni": { "score": 1-7 },
      "azione_sistema_integrato_inclusione_fragilita": { "score": 1-7 }
    },
    "2_6_didattica_orientativa": {
      "didattica_da_esperienza_studenti": { "score": 1-7 },
      "didattica_laboratoriale": { "score": 1-7 },
      "didattica_flessibilita_spazi_tempi": { "score": 1-7 },
      "didattica_interdisciplinare": { "score": 1-7 }
    },
    "2_7_opzionali_facoltative": {
      "opzionali_culturali": { "score": 1-7 },
      "opzionali_laboratoriali_espressive": { "score": 1-7 },
      "opzionali_ludiche_ricreative": { "score": 1-7 },
      "opzionali_volontariato": { "score": 1-7 },
      "opzionali_sportive": { "score": 1-7 }
    }
  },
  "narrative": "..."
}
```

## 📈 Dimensioni di Scoring (Likert 1-7)

| Sezione | Descrizione |
|---------|-------------|
| **2.1** | Sezione Dedicata all'Orientamento |
| **2.2** | Partnership e Reti |
| **2.3** | Finalità dell'Orientamento (5 sottodimensioni) |
| **2.4** | Obiettivi (4 sottodimensioni) |
| **2.5** | Governance e Azioni di Sistema (5 sottodimensioni) |
| **2.6** | Didattica Orientativa (4 sottodimensioni) |
| **2.7** | Opportunità Formative (5 sottodimensioni) |

### Scala Punteggi
| Valore | Interpretazione |
|:------:|-----------------|
| **1** | Assente: nessun riferimento |
| **2-3** | Minimo: accenni generici |
| **4** | Sufficiente: azioni presenti ma basilari |
| **5-6** | Buono: azioni strutturate |
| **7** | Eccellente: sistema integrato e monitorato |

## 🔧 Script Principali

### `app/agentic_pipeline.py`
Pipeline principale che:
1. Legge file MD da `ptof_md/`
2. Esegue analisi 3-agenti (Analyst → Reviewer → Refiner)
3. Salva JSON + MD in `analysis_results/`
4. Chiama `refine_metadata.py` e `align_metadata.py` dopo ogni scuola

### `src/processing/align_metadata.py`
Allineamento metadati:
- **Fase 1**: Carica cache da `metadata_enrichment.csv` e `invalsi_unified.csv`
- **Fase 2**: Arricchisce JSON con metadati (ordine_grado, tipo_scuola, area_geografica)
- **Fase 3**: Ricostruisce `data/analysis_summary.csv` per la dashboard

### `src/processing/refine_metadata.py`
Estrae metadati ND:
- Cerca pattern nel testo MD (denominazione, comune, ordine_grado)
- Sincronizza bidirezionalmente ordine_grado ↔ tipo_scuola

## 📝 Fonti Dati

| File | Descrizione | Records |
|------|-------------|---------|
| `metadata_enrichment.csv` | Anagrafica ufficiale scuole | ~50.000 |
| `invalsi_unified.csv` | Dati valutazione INVALSI | ~250 |
| `candidati_ptof.csv` | Lista candidati download PTOF | variabile |

## 📜 Licenza

Progetto di ricerca interno - PRIN 2022.
