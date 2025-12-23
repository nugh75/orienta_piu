# 📚 PTOF Orientation Analysis System

Sistema automatizzato per l'analisi dei documenti PTOF delle scuole italiane.

## 🚀 Quick Start

Il progetto include un `Makefile` per semplificare tutte le operazioni.

```bash
# 1. Setup (solo la prima volta)
make setup

# 2. Copia i PDF nella cartella di input
cp /path/to/*.pdf ptof_inbox/

# 3. Esegui l'analisi completa
make run

# 4. Avvia la Dashboard
make dashboard
```

### Comandi Rapidi
- `make refresh`: Rigenera il CSV dai JSON e avvia la dashboard (utile dopo modifiche manuali).
- `make full`: Esegue tutto il ciclo (Analisi -> CSV -> Dashboard).
- `make help`: Mostra tutti i comandi disponibili.

## 📂 Directory

- `ptof_inbox/` → PDF da analizzare
- `ptof_processed/` → PDF archiviati
- `ptof_md/` → Markdown
- `analysis_results/` → JSON analisi
- `logs/` → Log (opzionale: usa `tee` se vuoi salvare l'output)

## 🤖 Pipeline Multi-Agente

| Agente | Modello | Ruolo |
|--------|---------|-------|
| Analyst | gemma3:27b | Estrae dati |
| Reviewer | qwen3:32b | Verifica |
| Refiner | gemma3:27b | Corregge |

## 📋 CLI Commands

```bash
python workflow_notebook.py    # Workflow completo
python app/agentic_pipeline.py # Solo analisi
```

## 📓 Notebook

`docs/CLI_Examples.ipynb`

## 📜 Licenza

PRIN 2022
