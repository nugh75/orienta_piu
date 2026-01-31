# PTOF Code Cleanup Tool

Questo strumento (`src/agents/ptof_code_cleaner.py`) serve a identificare e correggere discrepanze tra il codice meccanografico dichiarato nel nome del file PTOF e quello effettivo contenuto nel testo del documento.

## Scopo

I file PTOF sono nominati come `CODICEMECCANOGRAFICO_PTOF.md`. Talvolta, il codice nel nome del file è errato (es. refuso, codice di una scuola diversa, o codice obsoleto). Questo tool:

1.  Analizza il testo del PTOF per identificare il codice reale (usando Regex e LLM).
2.  Confronta il codice trovato con il nome del file.
3.  Rinomina il file con il codice corretto.
4.  **Pulisce tutti i dati correlati** al vecchio codice errato per mantenere la consistenza del database.

## Funzionalità di Pulizia Dati

Quando viene rinominato un file (es. da `OLDCODE_ptof.md` a `NEWCODE_ptof.md`), il tool esegue automaticamente:

1.  **Analisi**: Elimina `analysis_results/OLDCODE_PTOF_analysis.json` e `.md`.
2.  **Processed**: Elimina `ptof_processed/OLDCODE.json`.
3.  **Registry**: Rimuove la voce relativa al vecchio file da `data/validation_registry.json`.
4.  **Activity Registry**: Rimuove la voce da `data/activity_registry.json`.
5.  **Attività**: Rimuove le righe corrispondenti al vecchio codice da `data/attivita.csv`.

## Utilizzo

### 1. Dry Run (Analisi)

Esegue l'analisi senza apportare modifiche. Genera un report in `data/ptof_mismatch_report.json`.

```bash
make clean-ptof-codes
```

Opzioni LLM (per disambifuazione):

```bash
make clean-ptof-codes MODEL=qwen2.5:7b OLLAMA_URL=http://...
```

### 2. Apply (Esecuzione)

Applica le modifiche: rinomina i file e cancella i dati obsoleti. Richiede conferma esplicita.

```bash
make clean-ptof-codes-apply
```

### Gestione Conflitti

Se il file di destinazione (con il codice corretto) esiste già, il file originale viene spostato in `ptof_md/conflicts/` per una revisione manuale, evitando sovrascritture accidentali.
