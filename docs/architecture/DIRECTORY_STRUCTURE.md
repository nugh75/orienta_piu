# 📂 Struttura Directory PTOF Analysis

Questo documento spiega la struttura delle cartelle per il workflow di analisi PTOF.

## Directory Structure

```
LIste/
├── ptof_inbox/              # 📥 PDF da analizzare (INSERISCI QUI I NUOVI FILE)
│   └── .download_in_progress # ⏳ Lock file durante download automatico
├── ptof_processed/          # ✅ PDF già analizzati (archiviati per batch)
│   ├── batch_20250121_143022/
│   │   ├── README.txt       # Riepilogo batch
│   │   ├── MIIS08900V.pdf
│   │   └── MIIS08901W.pdf
│   └── batch_20250121_150055/
│       └── ...
├── ptof_md/                 # 📝 File Markdown generati
├── analysis_results/        # 📊 Risultati analisi JSON
├── data/                    # 💾 CSV e metadata
└── logs/                    # 📋 File di log
```

## Workflow Automatico

### 1. Preparazione
Copia i PDF da analizzare in `ptof_inbox/`:
```bash
cp /path/to/new/ptof/*.pdf ptof_inbox/
```

### 2. Esecuzione Workflow
```bash
# Da terminale
source .venv/bin/activate
python workflow_notebook.py
```

### 3. Cosa Succede

Il workflow automatico esegue:

1. **Conversione** 📝
   - Legge PDF da `ptof_inbox/`
   - Genera Markdown in `ptof_md/`

2. **Analisi** 🤖
   - Pipeline multi-agente su file MD
   - Salva risultati in `analysis_results/`

3. **Archiviazione** 📦
   - Sposta PDF da `ptof_inbox/` a `ptof_processed/batch_TIMESTAMP/`
   - Crea file README.txt con riepilogo batch

4. **Auto-fill regioni** 🧭
   - Completa `regione/provincia/area_geografica` usando `data/comuni_italiani.json`

5. **Aggiornamento** 📊
   - Ricostruisce `data/analysis_summary.csv`
   - Aggiorna dashboard

### 4. Risultati

Dopo l'esecuzione:
- `ptof_inbox/` è vuota (tutti i PDF processati)
- `ptof_processed/batch_TIMESTAMP/` contiene i PDF archiviati
- `analysis_results/` contiene i JSON di analisi
- Log in console (usa `tee` se vuoi salvarlo su file)

## Comandi Utili

### Verifica stato
```bash
# Conta PDF in inbox
ls -1 ptof_inbox/*.pdf | wc -l

# Conta PDF processati
find ptof_processed -name "*.pdf" | wc -l

# Conta analisi
ls -1 analysis_results/*.json | wc -l
```

### Visualizza log workflow
```bash
tail -f logs/workflow_notebook.log
```

### Cleanup inbox (svuota)
```bash
# ATTENZIONE: Rimuove tutti i PDF dalla inbox
rm ptof_inbox/*.pdf
```

### Recupera PDF da batch specifico
```bash
# Lista batch disponibili
ls -d ptof_processed/batch_*

# Copia file da batch specifico
cp ptof_processed/batch_20250121_143022/*.pdf ptof_inbox/
```

## Note Importanti

⚠️ **IMPORTANTE**:
- Metti SOLO i PDF da analizzare in `ptof_inbox/`
- NON modificare manualmente `ptof_processed/` (gestito automaticamente)
- I PDF vengono spostati (non copiati) da inbox a processed
- Ogni batch ha un README.txt con la lista dei file processati
- Se `ptof_inbox/.download_in_progress` esiste, il workflow resta in attesa di nuovi PDF

✅ **Best Practices**:
- Esegui il workflow quando hai nuovi PDF da processare
- Verifica l'output in console (oppure `logs/workflow_notebook.log` se usi `tee`)
- Backup periodico di `ptof_processed/` per sicurezza
- Usa la dashboard per verificare i risultati

## Struttura Batch

Ogni batch in `ptof_processed/` contiene:
```
batch_20250121_143022/
├── README.txt              # Riepilogo: data, ora, lista file
├── MIIS08900V.pdf         # PDF originale
├── MIIS08901W.pdf
└── ...
```

Il `README.txt` contiene:
```
Batch processato il 2025-01-21 14:30:22
File processati: 2

File:
  - MIIS08900V.pdf
  - MIIS08901W.pdf
```
