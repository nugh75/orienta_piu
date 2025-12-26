README - Workflow PTOF con Cartelle Separate
==========================================

## ✅ Implementato!

Il sistema ora usa due cartelle separate:

### 📂 Struttura Directory

```
LIste/
├── ptof_inbox/              # 📥 PDF da analizzare (INSERISCI QUI I NUOVI FILE)
├── ptof_processed/          # ✅ PDF già analizzati (archiviati per batch)  
│   ├── batch_20250121_143022/
│   │   ├── README.txt
│   │   └── *.pdf
│   └── batch_20250121_150055/
├── ptof_md/                 # 📝 Markdown generati
└── analysis_results/        # 📊 Risultati JSON
```

## 🚀 Utilizzo Rapido con Make

### 1. Prepara i PDF
```bash
# Copia i PDF da analizzare
cp /path/to/new/*.pdf ptof_inbox/
```

### 2. Esegui Workflow
```bash
make run
```

Alias equivalente:
```bash
make workflow
```

### 3. Visualizza Risultati
```bash
make dashboard
```

### Altri Comandi Utili
- **`make csv`**: Rigenera il file CSV (`data/analysis_summary.csv`) partendo dai JSON in `analysis_results/`. Utile se hai modificato manualmente i JSON o se il CSV è disallineato.
- **`make refresh`**: Esegue `make csv` e poi avvia la dashboard.
- **`make full`**: Esegue l'intero ciclo (`run` + `csv` + `dashboard`).

---

## 🚀 Pipeline Ollama (Analisi + Revisione Parallela)

Per eseguire analisi e revisione in parallelo con solo Ollama:

```bash
make pipeline-ollama MODEL=qwen3:32b
```

Questo comando avvia in parallelo:
- **Analisi PTOF** (`workflow_notebook.py`)
- **Revisione scores** (`ollama_score_reviewer`)
- **Revisione report MD** (`ollama_report_reviewer`)

Parametri opzionali:
- `MODEL=qwen3:32b` - Modello Ollama (default: qwen3:32b)
- `OLLAMA_URL=http://localhost:11434` - URL server Ollama
- `LOW=2` - Soglia minima per revisione scores
- `HIGH=6` - Soglia massima per revisione scores

Per aggiornare il CSV mentre i processi girano:
```bash
make csv
```

---

## 📚 Report Best Practice

### Generazione Report Narrativo (solo Ollama)

```bash
make best-practice-llm MODEL=qwen3:32b
```

Genera un report incrementale analizzando tutte le scuole e arricchendo progressivamente il documento.

**Rilevamento automatico modifiche:** L'agente rileva automaticamente se i file JSON/MD sono stati modificati (es. dopo una revisione con `ollama_score_reviewer` o `ollama_report_reviewer`) e ri-analizza solo le scuole i cui file sono cambiati. Nel log vedrai:
- `🆕` per scuole nuove
- `🔄 RECHECK` per scuole ri-analizzate

### Generazione Report Sintetico

**Con solo Ollama (consigliato per uso locale):**
```bash
make best-practice-llm-synth-ollama MODEL=qwen3:32b
```

**Con Gemini/OpenRouter (richiede API key):**
```bash
make best-practice-llm-synth REFACTOR_MODEL=gemini-3-flash-preview
```

**Rilevamento automatico modifiche:** Anche la sintesi rileva automaticamente se il report narrativo è stato modificato e ri-sintetizza tutto da zero. Nel log vedrai:
- `🔄 Report narrativo modificato dall'ultima sintesi - ri-sintetizzo`

### Flusso Completo Solo Ollama
```bash
# 1. Genera report narrativo
make best-practice-llm MODEL=qwen3:32b

# 2. Genera report sintetico
make best-practice-llm-synth-ollama MODEL=qwen3:32b
```

### Altri Comandi Best Practice
- `make best-practice-llm-reset` - Rigenera da zero il report narrativo
- `make best-practice-llm-synth-restore` - Ripristina report sintetico da backup

## 🔁 Cosa Succede nel Workflow

1. **Conversione** -> PDF in `ptof_md/`
2. **Analisi** -> JSON in `analysis_results/`
3. **Auto-fill regioni** -> completa `regione/provincia/area_geografica` usando `data/comuni_italiani.json`
4. **CSV** -> rigenera `data/analysis_summary.csv`
5. **Archiviazione** -> PDF spostati in `ptof_processed/batch_TIMESTAMP/`

### 4. Risultati (Output)
- `ptof_inbox/` svuotata (PDF spostati)
- `ptof_processed/batch_TIMESTAMP/` contiene PDF archiviati
- `analysis_results/` contiene analisi JSON
- Log in console (oppure `logs/workflow_notebook.log` se usi `tee`)

## 📚 Documentazione

- **Script workflow**: [`workflow_notebook.py`](../../workflow_notebook.py)
- **Guida completa**: [`docs/architecture/DIRECTORY_STRUCTURE.md`](../architecture/DIRECTORY_STRUCTURE.md)
- **Esempi Jupyter**: [`docs/CLI_Examples.ipynb`](../CLI_Examples.ipynb)

## 🔧 File Creati

1. ✅ `workflow_notebook.py` - Script workflow automatico
2. ✅ `docs/architecture/DIRECTORY_STRUCTURE.md` - Dok mentazione directory
3. ✅ `ptof_inbox/` - Directory inbox (creata)
4.  ✅ `ptof_processed/` - Directory processed (creata)

## 💡 Prossimi Passi

1. Copia PDF da analizzare in `ptof_inbox/`
2. Esegui `python workflow_notebook.py`
3. Verifica risultati su dashboard Streamlit

## Note
- I PDF vengono **spostati** (non copiati) da inbox a processed
- Ogni batch ha timestamp e README con lista file
- Log in console (oppure `logs/workflow_notebook.log` se usi `tee`)
- Se `ptof_inbox/.download_in_progress` esiste, il workflow resta in attesa di nuovi PDF
  (polling configurabile con `PTOF_DOWNLOAD_WAIT_SECONDS`)
