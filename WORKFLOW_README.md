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

## 🚀 Utilizzo Rapido

### 1. Prepara i PDF
```bash
# Copia i PDF da analizzare
cp /path/to/new/*.pdf ptof_inbox/
```

### 2. Esegui Workflow
```bash
source .venv/bin/activate
python workflow_ptof.py
```

### 3. Risultati
- `ptof_inbox/` svuotata (PDF spostati)
- `ptof_processed/batch_TIMESTAMP/` contiene PDF archiviati
- `analysis_results/` contiene analisi JSON
- `logs/workflow_ptof.log` contiene log completo

## 📚 Documentazione

- **Script workflow**: [`workflow_ptof.py`](workflow_ptof.py)
- **Guida completa**: [`docs/DIRECTORY_STRUCTURE.md`](docs/DIRECTORY_STRUCTURE.md)
- **Esempi Jupyter**: [`docs/CLI_Examples.ipynb`](docs/CLI_Examples.ipynb)

## 🔧 File Creati

1. ✅ `workflow_ptof.py` - Script workflow automatico
2. ✅ `docs/DIRECTORY_STRUCTURE.md` - Dok mentazione directory
3. ✅ `ptof_inbox/` - Directory inbox (creata)
4.  ✅ `ptof_processed/` - Directory processed (creata)

## 💡 Prossimi Passi

1. Copia PDF da analizzare in `ptof_inbox/`
2. Esegui `python workflow_ptof.py`
3. Verifica risultati su dashboard Streamlit

## Note
- I PDF vengono **spostati** (non copiati) da inbox a processed
- Ogni batch ha timestamp e README con lista file
- Log salvato in `logs/workflow_ptof.log`
