# Guida ai Comandi Make

Questo progetto utilizza un `Makefile` per semplificare l'esecuzione degli script principali e la gestione del workflow.

## Prerequisiti

Assicurati di avere `make` installato nel tuo sistema. Su macOS e Linux è generalmente preinstallato.

## Comandi Disponibili

### 1. Installazione Dipendenze
Installa tutte le librerie Python necessarie elencate in `requirements.txt`.
```bash
make setup
```

### 2. Esecuzione Workflow Completo
Avvia lo script principale `workflow_notebook.py` che gestisce l'intero processo:
- Monitoraggio cartella `ptof_inbox`
- Conversione PDF -> Markdown
- Analisi con agenti AI
- Generazione JSON
- Auto-fill regioni/province da `data/comuni_italiani.json`
- Rebuild CSV (`data/analysis_summary.csv`)
```bash
make run
```

Alias equivalente:
```bash
make workflow
```

### 3. Avvio Dashboard
Lancia l'applicazione Streamlit per visualizzare i risultati dell'analisi.
```bash
make dashboard
```

### 4. Rigenerazione CSV
Esegue lo script `src/processing/rebuild_csv_clean.py` per ricostruire il file CSV principale (`data/analysis_summary.csv`) partendo dai file JSON. Utile se hai modificato manualmente dei JSON o se il CSV è corrotto/mancante.
```bash
make csv
```

### 5. Backfill Metadati (LLM mirato)
Esegue uno script che tenta di riempire i metadati `ND` leggendo estratti mirati dai file MD e interrogando l'LLM.
```bash
make backfill
```

### 6. Pulizia
Rimuove file temporanei come la cache di Python (`__pycache__`, `.pyc`) per mantenere pulita la directory di lavoro.
```bash
make clean
```
## Combinazioni Utili

### Refresh Rapido
Rigenera il CSV dai JSON esistenti e avvia subito la dashboard. Utile quando hai fatto modifiche manuali ai JSON o vuoi assicurarti che la dashboard legga i dati più recenti senza rieseguire l'analisi.
```bash
make refresh
```

### Workflow Completo
Esegue in sequenza: analisi dei PDF (`run`), rigenerazione del CSV (`csv`) e avvio della dashboard (`dashboard`). È il comando "fai tutto" per un aggiornamento completo.
```bash
make full
```

## Manutenzione Report

Durante le revisioni AI, può capitare che alcuni report MD vengano troncati (es. per timeout API o rate limit). I backup vengono creati automaticamente come file `.bak` nella stessa cartella.

### Controllo File Troncati
Scansiona tutti i file `*_analysis.md` e identifica quelli potenzialmente troncati (file vuoti, terminanti a metà frase, code block non chiusi).
```bash
make check-truncated
```

### Trova e Ripristina File Troncati
Comando unico che:
1. Trova tutti i file MD troncati
2. Ripristina SOLO quelli troncati usando i file `.bak` di backup
3. Non tocca i file integri

```bash
make fix-truncated
```

### Lista Backup Disponibili
Mostra quanti file `.bak` sono disponibili nella cartella analysis_results.
```bash
make list-backups
```

### Workflow di Recovery Tipico
```bash
# Trova troncati e ripristina in un solo comando
make fix-truncated

# Rigenera il CSV con i dati corretti
make csv
```

## Esempio di Workflow Tipico

1.  **Setup iniziale** (solo la prima volta):
    ```bash
    make setup
    ```
2.  **Carica i PDF** nella cartella `ptof_inbox`.
3.  **Esegui l'analisi**:
    ```bash
    make run
    ```
4.  **Controlla i risultati** sulla dashboard:
    ```bash
    make dashboard
    ```
