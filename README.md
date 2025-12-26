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
- `OPENROUTER_API_KEY` per `make review-report-openrouter` / `make review-scores-openrouter`
- `GEMINI_API_KEY` per `make review-report-gemini` / `make review-scores-gemini`

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
- `make wizard`: Avvia wizard interattivo per i comandi make.
- `make review-scores-openrouter`: Revisione automatica dei punteggi estremi con OpenRouter.
- `make review-scores-gemini`: Revisione automatica dei punteggi estremi con Gemini.
- `make review-non-ptof`: Rimuove analisi generate da documenti non-PTOF.

Per documentazione completa dei comandi make, vedi [docs/reference/MAKE_REFERENCE.md](docs/reference/MAKE_REFERENCE.md).

## �️ Sicurezza e Integrità dei Dati

Il sistema implementa meccanismi robusti per prevenire la perdita o la corruzione dei dati:

### 1. Scrittura Atomica
Tutti i file critici (JSON, CSV, Markdown) vengono scritti in modalità atomica:
- Il contenuto viene prima scritto su un file temporaneo.
- Solo se la scrittura ha successo, il file temporaneo sostituisce quello originale.
- Questo previene la creazione di file troncati o corrotti in caso di crash o interruzioni.

### 2. Backup Automatici
Durante le operazioni di revisione (es. `make review-*`), il sistema crea automaticamente copie di backup:
- Prima di modificare un file esistente, viene creata una copia con estensione `.bak`.
- Esempio: `analisi.json` -> `analisi.json.bak`.
- Questo permette di ripristinare facilmente lo stato precedente in caso di errori logici dei modelli AI.

### 3. Pulizia Falsi Positivi
Il comando `make review-non-ptof` è stato potenziato per mantenere pulito il dataset:
- Filtra le scuole con punteggi bassi (default <= 2.0), spesso indice di documenti errati.
- **Strict Mode**: Se il punteggio è <= 2.0, il documento viene eliminato a prescindere, senza ulteriore validazione. Questo perché un punteggio così basso è garanzia quasi assoluta che il documento non sia un PTOF valido o non contenga informazioni pertinenti.
- Per punteggi superiori, rivalida il PDF originale con euristiche e LLM.
- Se confermato come NON PTOF, rimuove tutti gli artefatti (JSON, MD analisi, MD conversione) e aggiorna il CSV.

## �📂 Directory

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
# OpenRouter, batch completo
make review-scores-openrouter MODEL="meta-llama/llama-3.3-70b-instruct:free" LOW=2 HIGH=6

# OpenRouter su una singola scuola
make review-scores-openrouter TARGET=RMIC8GA002

# Gemini su una singola scuola
make review-scores-gemini MODEL="gemini-2.0-flash-exp" TARGET=RMIC8GA002

# Ollama locale
make review-scores-ollama MODEL=qwen3:32b LOW=2 HIGH=6

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

## 📚 Report Best Practice con LLM

Il sistema genera report sulle best practice dell'orientamento analizzando tutti i PTOF.

### Tre tipologie di Report

| Report | Comando | Descrizione |
|--------|---------|-------------|
| **Statistico** | `make best-practice` | Dati aggregati, classifiche, tabelle (algoritmi) |
| **Narrativo** | `make best-practice-llm` | Analisi discorsiva completa (Ollama) |
| **Sintetico** | `make best-practice-llm-synth` | Versione condensata del narrativo (Gemini) |

### Architettura

| Fase | Modello | Comando |
|------|---------|---------|
| Report Narrativo | Ollama (qwen3:32b) | `make best-practice-llm` |
| Report Sintetico | Gemini 3 Flash + OpenRouter fallback | `make best-practice-llm-synth` |

### Struttura del Report Narrativo

Il report è organizzato per:
- **Sezioni principali** (##): Metodologie, Progetti, Partnership, Governance, Inclusione, Territorio
- **Sottotitoli specifici** (####): Descrivono l'attività concreta (es. "Visite ai campus universitari")
- **Tipologia scuola** (#####): Divisione per ordine e grado

Le 6 tipologie di scuola:
1. Scuole dell'Infanzia
2. Scuole Primarie
3. Scuole Secondarie di Primo Grado
4. Licei
5. Istituti Tecnici
6. Istituti Professionali

### Formattazione automatica

- **Codice meccanografico** e **Nome scuola** in neretto (es: **RMIC8GA002** - **I.C. Via Roma**)
- **Nomi dei progetti** in neretto (es: **Progetto Futuro**)
- Stile narrativo, no elenchi puntati

### Comandi

```bash
# Report statistico (algoritmi)
make best-practice

# Report narrativo con Ollama (incrementale)
make best-practice-llm

# Ricomincia report narrativo da zero
make best-practice-llm-reset

# Report sintetico (refactoring con Gemini)
make best-practice-llm-synth

# Report sintetico con modello specifico
make best-practice-llm-synth REFACTOR_MODEL=gemini-2.5-flash

# Ripristina report sintetico dal backup
make best-practice-llm-synth-restore
```

### Gestione errori

- **Rate limit Gemini (429)**: Fallback automatico a OpenRouter (GPT OSS 120B)
- **Interruzione (Ctrl+C)**: Salvataggio sicuro del progresso
- **Sezione troppo corta**: Mantiene l'originale se riduzione >80%

### Output

| Report | File |
|--------|------|
| Statistico | `reports/best_practice_orientamento.md` |
| Narrativo | `reports/best_practice_orientamento_narrativo.md` |
| Sintetico | `reports/best_practice_orientamento_sintetico.md` |

## 📓 Notebook

`docs/CLI_Examples.ipynb`

## 📜 Licenza

PRIN 2022
