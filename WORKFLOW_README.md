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

### 3. Visualizza Risultati
```bash
make dashboard
```

### Altri Comandi Utili
- **`make csv`**: Rigenera il file CSV (`data/analysis_summary.csv`) partendo dai JSON in `analysis_results/`. Utile se hai modificato manualmente i JSON o se il CSV è disallineato.
- **`make refresh`**: Esegue `make csv` e poi avvia la dashboard.
- **`make full`**: Esegue l'intero ciclo (`run` + `csv` + `dashboard`).

### 4. Risultati (Output)
- `ptof_inbox/` svuotata (PDF spostati)
- `ptof_processed/batch_TIMESTAMP/` contiene PDF archiviati
- `analysis_results/` contiene analisi JSON
- Log in console (oppure `logs/workflow_notebook.log` se usi `tee`)

## 📚 Documentazione

- **Script workflow**: [`workflow_notebook.py`](workflow_notebook.py)
- **Guida completa**: [`docs/DIRECTORY_STRUCTURE.md`](docs/DIRECTORY_STRUCTURE.md)
- **Esempi Jupyter**: [`docs/CLI_Examples.ipynb`](docs/CLI_Examples.ipynb)

## 🔧 File Creati

1. ✅ `workflow_notebook.py` - Script workflow automatico
2. ✅ `docs/DIRECTORY_STRUCTURE.md` - Dok mentazione directory
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
