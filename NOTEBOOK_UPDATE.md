✅ **AGGIORNAMENTO NOTEBOOK**

Ho aggiornato il notebook `docs/CLI_Examples.ipynb` per usare il nuovo sistema con cartelle separate!

## 📝 Modifiche

1. **Aggiunta sezione "Workflow Automatico Inbox → Processed"** all'inizio
   - Priorità massima ⭐
   - Usa `workflow_ptof.py` invece degli script separati
   - Gestisce automaticamente `ptof_inbox/` → `ptof_processed/`

2. **Cella di verifica stato**
   - Mostra quanti PDF ci sono in inbox/processed
   - Conta file MD e JSON
   - Indica se ci sono file da processare

## 🚀 Come Usare

### Nel Notebook:

1. **Copia PDF da analizzare**:
   ```bash
   cp /path/to/*.pdf ptof_inbox/
   ```

2. **Esegui la prima cella del notebook** (sezione "Workflow Automatico")
   - Automaticamente converte, analizza e archivia PDF
   - Log salvato in `logs/workflow_ptof.log`

3. **Verifica stato** con la seconda cella
   - Vedi PDF rimanenti in inbox
   - Conta totale processed

## ⚙️ Workflow Script

Se preferisci da terminale invece del notebook:
```bash
source .venv/bin/activate
python workflow_ptof.py
```

## 📂 Risultati

Dopo l'esecuzione:
- `ptof_inbox/` - Vuota (PDF spostati)
- `ptof_processed/batch_TIMESTAMP/` - PDF archiviati con README
- `analysis_results/` - JSON analisi
- `logs/workflow_ptof.log` - Log completo

Il notebook è pronto! Ricaricalo e prova la nuova sezione in cima. 🎯
