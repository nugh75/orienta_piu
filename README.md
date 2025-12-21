# 📚 PTOF Orientation Analysis System

Sistema automatizzato per l'analisi dei documenti PTOF delle scuole italiane.

## 🚀 Quick Start

```bash
# Setup
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Workflow CLI
cp /path/to/*.pdf ptof_inbox/
python workflow_ptof.py

# Dashboard (✅ Verificata e Funzionante)
./start_dashboard.sh
# oppure: streamlit run app/Home.py
```

## 📂 Directory

- `ptof_inbox/` → PDF da analizzare
- `ptof_processed/` → PDF archiviati
- `ptof_md/` → Markdown
- `analysis_results/` → JSON analisi
- `logs/workflow_ptof.log` → Log

## 🤖 Pipeline Multi-Agente

| Agente | Modello | Ruolo |
|--------|---------|-------|
| Analyst | gemma3:27b | Estrae dati |
| Reviewer | qwen3:32b | Verifica |
| Refiner | gemma3:27b | Corregge |

## 📋 CLI Commands

```bash
python workflow_ptof.py        # Workflow completo
python app/agentic_pipeline.py # Solo analisi
python run_fixer.py            # Background fixer
```

## 📓 Notebook

`docs/CLI_Examples.ipynb`

## 📜 Licenza

PRIN 2022
