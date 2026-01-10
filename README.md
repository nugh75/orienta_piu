# PTOF Orientation Analysis System

Sistema automatizzato per l'analisi dei documenti PTOF delle scuole italiane.

## Quick Start

Il progetto include un Makefile per semplificare tutte le operazioni.

```bash
# 1. Setup (solo la prima volta)
make setup

# 2. Copia i PDF nella cartella di input
cp /path/to/*.pdf ptof_inbox/

# 3. Esegui l'analisi completa (una scuola alla volta)
make run

# 4. Avvia la dashboard
make dashboard
```

## Documentazione

- [MAP](docs/MAP.md)
- [Workflow](docs/operations/WORKFLOW_README.md)
- [Makefile reference](docs/reference/MAKE_REFERENCE.md)
- [Dashboard](docs/dashboard/DASHBOARD_README.md)
- [Documentazione analisi](docs/analysis/DOCUMENTAZIONE_ANALISI.md)
- [Log & tmux (rapida)](docs/LOGS_TMUX.md)

## API keys (solo per review con LLM cloud)

Per usare i reviewer cloud:
- OPENROUTER_API_KEY per make review-report-openrouter / make review-scores-openrouter
- GEMINI_API_KEY per make review-report-gemini / make review-scores-gemini

Puoi metterle in .env o in data/api_config.json.

## Comandi make essenziali

- make setup
- make run
- make workflow
- make dashboard
- make refresh
- make full
- make help
- make wizard

Per la lista completa dei comandi make, vedi docs/reference/MAKE_REFERENCE.md.

## Download e analisi in parallelo (opzionale)

Apri due terminali:

```bash
# Terminale 1: download PTOF
make download-strato N=5

# Terminale 2: analisi (resta in attesa di nuovi PDF)
make workflow
```

### Parametri workflow

| Parametro | Descrizione | Esempio |
|-----------|-------------|---------|
| `PRESET` | ID configurazione LLM (vedi pipeline_config.json) | `PRESET=8` |
| `FORCE_CODE` | Ri-analizza SOLO una scuola specifica (skip Step 0,1) | `FORCE_CODE=BA1MD7500G` |
| `SKIP_VALIDATION` | Salta validazione PTOF (Step -1) | `SKIP_VALIDATION=1` |
| `PROVIDER` | Provider LLM (ollama, openai, openrouter) | `PROVIDER=openrouter` |
| `MODEL` | Modello da usare per tutti gli agenti | `MODEL=gemma3:27b` |

**Esempi:**
```bash
# Analisi con OpenRouter Gemini
make workflow PRESET=8

# Ri-analisi singola scuola (più veloce)
make workflow PRESET=8 FORCE_CODE=BA1MD7500G

# Skip validazione per batch veloce
make workflow PRESET=8 SKIP_VALIDATION=1
```

Il workflow aspetta se trova ptof_inbox/.download_in_progress.
Per cambiare il polling: PTOF_DOWNLOAD_WAIT_SECONDS=10.

## Strategie di download (sintesi)

Il downloader usa 4 strategie in cascata:
1. Portale Unica
2. Sito web scuola
3. Codice istituto (per plessi)
4. Ricerca web (DuckDuckGo)

Dettagli in [Downloader](src/downloaders/README.md).

## Output e directory principali

- ptof_inbox/      PDF da analizzare
- ptof_processed/  PDF archiviati
- ptof_md/         Markdown estratti
- analysis_results/ JSON analisi + report MD
- data/            Dataset, registry, config
- logs/            Log runtime
- reports/         Output legacy o manuali

## Catalogo Buone Pratiche

Comandi:

```bash
make best-practice-extract
make best-practice-extract-reset
make best-practice-extract-stats
```

Output:
- data/attivita.json
- data/activity_registry.json

## Pipeline multi agente (sintesi)

Tre ruoli lavorano in sequenza per ridurre errori e migliorare la stabilita dei risultati.

| Agente | Modello | Ruolo |
|--------|---------|-------|
| Analyst | gemma3:27b | Estrae dati |
| Reviewer | qwen3:32b | Verifica |
| Refiner | gemma3:27b | Corregge |

Post-processing automatico:
- Auto-fill regione/provincia/area usando data/comuni_italiani.json
- Rebuild CSV data/analysis_summary.csv dai JSON

## Sicurezza e integrita dei dati (sintesi)

- Scrittura atomica dei file critici (JSON, CSV, MD)
- Backup automatici .bak durante le revisioni
- Pulizia falsi positivi con make review-non-ptof

## Qualita analisi (pesi e contrappesi)

Pesi (aumenta punteggio):
- Evidenze chiare nel testo
- Coerenza tra sezioni
- Sezione dedicata all'orientamento

Contrappesi (riduce errori):
- Validazione PTOF pre-analisi
- Reviewer che cerca incoerenze
- Revisore punteggi estremi (opzionale)
- Arricchimento metadati con anagrafica MIUR

## CLI (avanzato)

```bash
python workflow_notebook.py
python app/agentic_pipeline.py
python src/processing/autofill_region_from_comuni.py
python src/processing/score_reviewer.py --provider openrouter --model "meta-llama/llama-3.3-70b-instruct:free"
python src/processing/score_reviewer.py --provider openrouter --model "meta-llama/llama-3.3-70b-instruct:free"
python src/processing/non_ptof_reviewer.py --dry-run
```

## Estrazione Attività (Avanzato)

Il comando `make activity-extract` supporta diverse opzioni avanzate per scalabilità e controllo costi:

### 1. Supporto OpenRouter
Usa modelli cloud invece di Ollama locale (richiede `OPENROUTER_API_KEY` in `.env`):
```bash
make activity-extract PROVIDER=openrouter MODEL="google/gemini-2.5-flash-lite"
```

### 2. Monitoraggio Costi
Il sistema traccia automaticamente i costi per i provider a pagamento.
Genera un report CSV/Markdown (in `data/api_costs.md`):
```bash
make report-costs
```

### 3. Limite di Budget (Safety Cap)
Ferma l'esecuzione se il costo della sessione supera un limite:
```bash
# Si ferma se spende più di 5 dollari
make activity-extract PROVIDER=openrouter MAX_COST=5.0
```

### 4. Sharding (Parallelismo)
Dividi il lavoro su più terminali/macchine:
```bash
# Terminale 1 (processa metà file)
make activity-extract SHARD="1/2"

# Terminale 2 (processa l'altra metà)
make activity-extract SHARD="2/2"
```

## Meta Report (Tematici)

Generazione report tematici sulle attivita estratte.

```bash
make meta-thematic DIM=orientamento PROVIDER=ollama
```

Opzione per includere sezioni regionali (default: disattivo):
```bash
META_REPORT_INCLUDE_REGIONS=1 make meta-thematic DIM=orientamento
```

Consiglio chunking (bilanciamento costo/qualita):
```bash
META_REPORT_THEME_CHUNK_SIZE=80 META_REPORT_THEME_CHUNK_THRESHOLD=160 make meta-thematic DIM=orientamento
```

Output: `reports/meta/thematic/{DIM}_attivita.md`

## Notebook

[docs/CLI_Examples.ipynb](docs/CLI_Examples.ipynb)

## Licenza

PRIN 2022
