# 🔧 Come Aggiornare il Notebook per usare ptof_inbox/

## Problema
Il notebook attualmente usa la vecchia struttura `ptof/` invece di `ptof_inbox/`.

## ✅ Soluzione Rapida

Usa direttamente lo script `workflow_notebook.py` invece delle celle bash nel notebook!

### Da Terminale:

```bash
cd /Users/danieledragoni/git/LIste
source .venv/bin/activate

# Copia PDF da analizzare
cp /path/to/*.pdf ptof_inbox/

# Esegui workflow
python workflow_notebook.py
```

### Da Jupyter Notebook:

Aggiungi questa cella all'inizio del notebook:

```python
%%bash
cd /Users/danieledragoni/git/LIste
source .venv/bin/activate

echo "🚀 WORKFLOW PTOF"
python workflow_notebook.py 2>&1 | tee logs/workflow_notebook.log
echo "✅ Completato!"
```

## 📋 Verifica Stato

Aggiungi questa cella per vedere lo stato:

```python
%%bash
cd /Users/danieledragoni/git/LIste

echo "📊 STATO"
echo "PDF inbox: $(find ptof_inbox -name '*.pdf' | wc -l)"
echo "PDF processed: $(find ptof_processed -name '*.pdf' | wc -l)"  
echo "MD files: $(find ptof_md -name '*.md' | wc -l)"
echo "JSON files: $(find analysis_results -name '*.json' | wc -l)"
```

## 🎯 Alternativa

Usa direttamente `workflow_notebook.py` da terminale - è più semplice e affidabile!

```bash
# 1. Prepara
cp /path/to/*.pdf ptof_inbox/

# 2. Esegui
source .venv/bin/activate && python workflow_notebook.py

# 3. Verifica
tail -f logs/workflow_notebook.log
```

Il workflow automaticamente:
- ✅ Converte PDF → MD
- ✅ Anal

izza con multi-agente
- ✅ Sposta PDF in `ptof_processed/batch_TIMESTAMP/`
- ✅ Aggiorna CSV

Tutto in un comando! 🚀
