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

### 🔑 API Keys (solo per revisioni con LLM cloud)
Per usare i reviewer cloud:
- `OPENROUTER_API_KEY` per `make review-slow` / `make review-scores`
- `GEMINI_API_KEY` per `make review-gemini` / `make review-scores-gemini`

Puoi metterle in `.env` o in `data/api_config.json`.

### Download + Analisi in parallelo (opzionale)
Il workflow può restare in attesa mentre i PTOF vengono scaricati.
Apri due terminali:

```bash
# Terminale 1: download PTOF
# Strategie: Unica, Sito Web, Codice Istituto, DuckDuckGo
make download-strato N=5

# Terminale 2: analisi (resta in attesa di nuovi PDF)
make workflow
```

Il workflow aspetta se trova `ptof_inbox/.download_in_progress`.
Per cambiare il polling: `PTOF_DOWNLOAD_WAIT_SECONDS=10`.

### Strategie di Download
Il downloader utilizza 4 strategie in cascata per massimizzare il successo:
1. **Portale Unica**: Cerca sul portale ufficiale del Ministero.
2. **Sito Web Scuola**: Cerca sul sito istituzionale della scuola.
3. **Codice Istituto**: Per i plessi, prova a cercare con il codice dell'istituto principale.
4. **Ricerca Web (DuckDuckGo)**: Cerca su tutto il web "CodiceScuola PTOF filetype:pdf".

Inoltre, verifica sempre se il file è già presente in `ptof_processed` o `ptof_discarded` per evitare download inutili.

### Comandi Rapidi
- `make refresh`: Rigenera il CSV dai JSON e avvia la dashboard (utile dopo modifiche manuali).
- `make full`: Esegue tutto il ciclo (Analisi -> CSV -> Dashboard).
- `make help`: Mostra tutti i comandi disponibili.
- `make review-scores`: Revisione automatica dei punteggi estremi (solo JSON).
- `make review-scores-gemini`: Come sopra, ma con Google Gemini.
- `make review-non-ptof`: Rimuove analisi generate da documenti non-PTOF.

## 📂 Directory

- `ptof_inbox/` → PDF da analizzare
- `ptof_processed/` → PDF archiviati
- `ptof_md/` → Markdown
- `analysis_results/` → JSON analisi
- `logs/` → Log (opzionale: usa `tee` se vuoi salvare l'output)

## 🤖 Pipeline Multi-Agente

Tre ruoli complementari lavorano in sequenza: il primo propone, il secondo controlla,
il terzo rifinisce. Questo riduce errori e rende i risultati più stabili.

| Agente | Modello | Ruolo |
|--------|---------|-------|
| Analyst | gemma3:27b | Estrae dati |
| Reviewer | qwen3:32b | Verifica |
| Refiner | gemma3:27b | Corregge |

Post-processing automatico nel workflow:
- Auto-fill regione/provincia/area usando `data/comuni_italiani.json`
- Rebuild CSV (`data/analysis_summary.csv`) dai JSON

Controlli di qualità integrati:
- **Validazione PTOF pre-analisi**: i documenti non pertinenti vengono scartati.
- **Revisore non-PTOF post-analisi**: elimina output generati da documenti sbagliati.

## ✅ Qualità dell'analisi (pesi e contrappesi)

**Pesi (cosa aumenta il punteggio)**:
- Evidenze chiare nel testo (azioni concrete, obiettivi espliciti)
- Coerenza tra sezioni e attività
- Presenza di una sezione dedicata all'orientamento

**Contrappesi (cosa corregge o riduce)**:
- Validazione PTOF prima dell'analisi
- Reviewer che cerca incoerenze e allucinazioni
- Revisore dei punteggi estremi (facoltativo)
- Arricchimento metadati con anagrafica MIUR

## 📋 CLI Commands

```bash
python workflow_notebook.py    # Workflow completo
python app/agentic_pipeline.py # Solo analisi
python src/processing/autofill_region_from_comuni.py # Auto-fill regioni da comuni
python src/processing/score_reviewer.py --provider openrouter --model "meta-llama/llama-3.3-70b-instruct:free"
python src/processing/non_ptof_reviewer.py --dry-run
```

## ✅ Esempi (Review punteggi estremi)

```bash
# OpenRouter (default), batch completo
make review-scores MODEL="meta-llama/llama-3.3-70b-instruct:free" LOW=2 HIGH=6

# OpenRouter su una singola scuola
make review-scores TARGET=RMIC8GA002

# Gemini su una singola scuola
make review-scores-gemini MODEL="gemini-2.0-flash-exp" TARGET=RMIC8GA002

# CLI diretto con provider Gemini
python src/processing/score_reviewer.py --provider gemini --model "gemini-2.0-flash-exp" --low-threshold 2 --high-threshold 6 --target RMIC8GA002
```

## ✅ Esempi (Review non-PTOF)

```bash
# Dry-run per vedere cosa verrebbe rimosso
make review-non-ptof DRY=1

# Rimozione su una singola scuola
make review-non-ptof TARGET=RMIC8GA002
```

## 📓 Notebook

`docs/CLI_Examples.ipynb`

## 📜 Licenza

PRIN 2022
