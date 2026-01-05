# Makefile Reference - PTOF Analysis System

Guida completa a tutti i comandi `make` disponibili nel progetto.

Per una lista rapida dei comandi vedi [MAKE_COMMANDS](MAKE_COMMANDS.md).
Per la mappa documentazione vedi [MAP](../MAP.md).

## Indice

- [Quick Start](#quick-start)
- [Download PTOF](#-download-ptof)
- [Analisi & Revisione](#-analisi--revisione)
  - [Revisione Report (MD)](#-revisione-report-arricchimento-md)
  - [Revisione Scores (JSON)](#-revisione-scores-punteggi-estremi-json)
  - [Validazione](#-validazione)
- [Workflow](#-workflow-analisi)
- [Catalogo Buone Pratiche](#-catalogo-buone-pratiche)
- [Outreach](#-outreach-ptof)
- [Registro Analisi](#-registro-analisi)
- [Manutenzione](#-manutenzione-report)
- [Modelli AI](#-modelli-ai)
- [Troubleshooting](#-troubleshooting)

---

## Quick Start

```bash
# Setup iniziale
make setup

# Wizard interattivo (consigliato per iniziare)
make wizard

# Mostra tutti i comandi
make help
```

---

## 📥 Download PTOF

### Comandi base

| Comando | Descrizione |
|---------|-------------|
| `make download` | Dry-run: mostra stratificazione senza scaricare |
| `make download-sample` | Scarica 5 scuole per ogni strato |
| `make download-strato N=X` | Scarica X scuole per ogni strato |
| `make download-reset` | Reset stato download e ricomincia |

### Filtri specifici

| Comando | Descrizione |
|---------|-------------|
| `make download-statali` | Solo scuole statali |
| `make download-paritarie` | Solo scuole paritarie |
| `make download-regione R=LAZIO` | Scuole di una regione |
| `make download-metro` | Solo province metropolitane |
| `make download-non-metro` | Solo province NON metropolitane |
| `make download-grado G=SEC_SECONDO` | Per grado scolastico |
| `make download-area A=SUD` | Per area geografica |

### Esempi d'uso

```bash
# Campione stratificato con 10 scuole per strato
make download-strato N=10

# Tutte le scuole del Lazio
make download-regione R=LAZIO

# Solo licei e istituti tecnici
make download-grado G=SEC_SECONDO

# Solo scuole del Sud e Isole
make download-area A=SUD
make download-area A=ISOLE
```

### Valori ammessi

**Gradi (G=)**:
- `INFANZIA`, `PRIMARIA`, `SEC_PRIMO`, `SEC_SECONDO`, `ALTRO`

**Aree (A=)**:
- `NORD OVEST`, `NORD EST`, `CENTRO`, `SUD`, `ISOLE`

**Regioni (R=)**:
- `ABRUZZO`, `BASILICATA`, `CALABRIA`, `CAMPANIA`, `EMILIA ROMAGNA`
- `FRIULI-VENEZIA G.`, `LAZIO`, `LIGURIA`, `LOMBARDIA`, `MARCHE`
- `MOLISE`, `PIEMONTE`, `PUGLIA`, `SARDEGNA`, `SICILIA`
- `TOSCANA`, `TRENTINO-ALTO ADIGE`, `UMBRIA`, `VALLE D'AOSTA`, `VENETO`

---

## 🤖 Analisi & Revisione

### Workflow principale

| Comando | Descrizione |
|---------|-------------|
| `make run` | Esegue analisi sui PDF in `ptof_inbox/` |
| `make run-force` | Forza ri-analisi di tutti i file |
| `make run-force-code CODE=X` | Forza ri-analisi di un codice specifico |

---

### 📝 Revisione Report (arricchimento MD)

Arricchisce i report Markdown con dettagli estratti dal PTOF originale.

| Comando | Provider | API Key |
|---------|----------|---------|
| `make review-report-openrouter` | OpenRouter | `OPENROUTER_API_KEY` |
| `make review-report-gemini` | Google Gemini | `GEMINI_API_KEY` |
| `make review-report-ollama` | Ollama locale | Nessuna |

#### Parametri comuni

| Parametro | Descrizione | Default |
|-----------|-------------|---------|
| `MODEL=X` | Nome del modello | Varia per provider |
| `TARGET=X` | Codice scuola specifico | Tutti |
| `LIMIT=X` | Numero max di file | 100 |
| `WAIT=X` | Secondi tra chiamate | 120 |

#### Parametri Ollama aggiuntivi

| Parametro | Descrizione | Default |
|-----------|-------------|---------|
| `OLLAMA_URL=X` | URL server Ollama | `http://192.168.129.14:11434` |
| `CHUNK_SIZE=X` | Dimensione chunk | 30000 |

#### Esempi

```bash
# OpenRouter con modello free
make review-report-openrouter MODEL="google/gemini-2.0-flash-exp:free"

# Gemini su una scuola specifica
make review-report-gemini TARGET=RMIC8GA002 MODEL=gemini-2.5-flash

# Ollama locale con qwen3
make review-report-ollama MODEL=qwen3:32b OLLAMA_URL=http://localhost:11434
```

---

### 🎯 Revisione Scores (punteggi estremi JSON)

Rivede e corregge i punteggi estremi (troppo alti o troppo bassi) nei file JSON.

| Comando | Provider | API Key |
|---------|----------|---------|
| `make review-scores-openrouter` | OpenRouter | `OPENROUTER_API_KEY` |
| `make review-scores-gemini` | Google Gemini | `GEMINI_API_KEY` |
| `make review-scores-ollama` | Ollama locale | Nessuna |

#### Parametri specifici

| Parametro | Descrizione | Default |
|-----------|-------------|---------|
| `LOW=X` | Soglia bassa (<=) | 2 |
| `HIGH=X` | Soglia alta (>=) | 6 |
| `MAX_CHARS=X` | Max caratteri nel prompt | 60000 |

#### Come funziona

1. Estrae tutti i punteggi dal JSON
2. Filtra quelli <= LOW o >= HIGH
3. Chiede al modello di confermare o correggere
4. Aggiorna il JSON con le correzioni

#### Esempi

```bash
# Revisione standard con OpenRouter
make review-scores-openrouter

# Solo punteggi molto estremi (1 o 7)
make review-scores-openrouter LOW=1 HIGH=7

# Gemini su scuola specifica
make review-scores-gemini TARGET=RMIC8GA002

# Ollama con soglie personalizzate
make review-scores-ollama MODEL=qwen3:32b LOW=2 HIGH=6
```

---

### 🔍 Validazione

| Comando | Descrizione |
|---------|-------------|
| `make review-non-ptof` | Rimuove analisi per documenti non-PTOF |

#### Parametri

| Parametro | Descrizione | Default |
|-----------|-------------|---------|
| `TARGET=X` | Codice scuola specifico | Tutti |
| `DRY=1` | Dry-run (mostra senza eseguire) | No |
| `NO_LLM=1` | Non usare LLM per validazione | No |
| `NO_MOVE=1` | Non spostare PDF | No |
| `LIMIT=X` | Numero max di file | Tutti |
| `MAX_SCORE=X` | Soglia massima punteggio | 2.0 |

#### Esempi

```bash
# Dry-run per vedere cosa verrebbe rimosso
make review-non-ptof DRY=1

# Rimozione su una singola scuola
make review-non-ptof TARGET=RMIC8GA002

# Solo documenti con score <= 1.5
make review-non-ptof MAX_SCORE=1.5
```

---

## 🔄 Workflow Analisi

| Comando | Descrizione |
|---------|-------------|
| `make setup` | Installa le dipendenze |
| `make run` | Esegue il workflow completo |
| `make dashboard` | Avvia la dashboard Streamlit |
| `make csv` | Rigenera il CSV dai file JSON |
| `make backfill` | Backfill metadati mancanti con LLM |
| `make clean` | Pulisce file temporanei e cache |

### Combinazioni

| Comando | Descrizione |
|---------|-------------|
| `make refresh` | csv + dashboard |
| `make full` | run + csv + dashboard |
| `make pipeline` | download-sample + run + csv + dashboard |

### Watch mode

```bash
# Rigenera CSV ogni 5 minuti
make csv-watch

# Rigenera CSV ogni 60 secondi
make csv-watch INTERVAL=60
```

---

## 🌟 Catalogo Buone Pratiche

**Legenda emoji (categorie):**
- 📚 Metodologie Didattiche Innovative
- 🎯 Progetti e Attività Esemplari
- 🤝 Partnership e Collaborazioni Strategiche
- ⚙️ Azioni di Sistema e Governance
- 🌈 Buone Pratiche per l'Inclusione
- 🗺️ Esperienze Territoriali Significative

### Estrazione buone pratiche

| Comando | Descrizione |
|---------|-------------|
| `make activity-extract` | Estrae e aggiorna il dataset dal PTOF |
| `make activity-extract-reset` | Reset e rielaborazione completa |
| `make activity-extract-stats` | Statistiche rapide sul dataset |

#### Parametri

```bash
# Estrazione con modello specifico
make activity-extract MODEL=qwen3:32b

# Limita il numero di PDF
make activity-extract LIMIT=10

# Gestione rate limit avanzata (Batch Wait)
# Esegue 10 richieste poi si ferma per 300 secondi (5 minuti)
make activity-extract BATCH_SIZE=10 BATCH_WAIT=300

# Pausa tra ogni singola richiesta (es. 10 secondi)
make activity-extract WAIT=10

# Forza rielaborazione completa
make activity-extract FORCE=1
```

---

## 📬 Outreach PTOF

| Comando | Descrizione |
|---------|-------------|
| `make outreach-portal` | Avvia portale upload PTOF |
| `make outreach-email` | Invia email PTOF |

#### Parametri outreach-portal

| Parametro | Default |
|-----------|---------|
| `PORT=X` | 8502 |

#### Parametri outreach-email

| Parametro | Descrizione |
|-----------|-------------|
| `BASE_URL=X` | URL base del portale |
| `LIMIT=X` | Limite invii |
| `SEND=1` | Invio reale (senza: dry-run) |
| `USE_PEC=1` | Usa PEC se email assente |
| `TEMPLATE=X` | Template email |
| `SUBJECT=X` | Oggetto email |
| `CSV="file1.csv file2.csv"` | File CSV con liste scuole |

---

## 📋 Registro Analisi

| Comando | Descrizione |
|---------|-------------|
| `make registry-status` | Mostra statistiche del registro |
| `make registry-list` | Lista tutti i file registrati |
| `make registry-clear` | Pulisce il registro (forza ri-analisi) |
| `make registry-remove CODE=X` | Rimuove una entry specifica |

---

## 🔧 Manutenzione Report

| Comando | Descrizione |
|---------|-------------|
| `make check-truncated` | Trova report MD troncati |
| `make fix-truncated` | Ripristina troncati dai backup |
| `make list-backups` | Elenca file di backup disponibili |
| `make recover-not-ptof` | Recupera PDF con suffisso `_ok` da `ptof_discarded/not_ptof` |

---

## 🤖 Modelli AI

| Comando | Descrizione |
|---------|-------------|
| `make models` | Mostra TUTTI i modelli disponibili |
| `make list-models` | Lista modelli dai preset |
| `make list-models-openrouter` | Lista modelli OpenRouter |
| `make list-models-gemini` | Lista modelli Gemini |

```bash
# Solo modelli free di OpenRouter
make list-models-openrouter FREE_ONLY=1
```

### Modelli consigliati

#### OpenRouter (free tier)

- `z-ai/glm-4.5-air:free` (default)
- `google/gemini-2.0-flash-exp:free`
- `meta-llama/llama-3.3-70b-instruct:free`

#### Gemini

- `gemini-3-flash-preview` (default, latest)
- `gemini-2.5-flash` (stabile)
- `gemini-2.5-pro` (2M token context)

#### Ollama

- `qwen3:32b` (default, bilanciato)
- `qwen3:14b` (veloce)
- `llama3.3:70b` (alta qualità)
- `deepseek-r1:32b` (reasoning)

---

## 🔥 Troubleshooting

### Errore: `Expecting value: line 1 column 1 (char 0)`

**Causa**: L'API ha restituito una risposta vuota o non-JSON.

**Soluzioni**:
1. Controlla i log per vedere la risposta raw
2. Verifica lo stato dell'account API (quota/crediti)
3. Aumenta il tempo di attesa: `WAIT=180`
4. Prova un modello diverso

### Errore: Rate limit (429)

**Causa**: Troppe richieste in poco tempo.

**Soluzioni**:
1. Il sistema riprova automaticamente con backoff esponenziale
2. Aumenta `WAIT=180` o più
3. Usa un modello diverso
4. Controlla i limiti del tuo account

### Errore: API Key non trovata

**Soluzioni**:
1. Crea file `.env` nella root del progetto:
   ```
   OPENROUTER_API_KEY=sk-or-...
   GEMINI_API_KEY=AIza...
   ```
2. Oppure aggiungi in `data/api_config.json`:
   ```json
   {
     "openrouter_api_key": "sk-or-...",
     "gemini_api_key": "AIza..."
   }
   ```

### Report troncati o corrotti

```bash
# Trova report troncati
make check-truncated

# Ripristina dai backup
make fix-truncated

# Lista backup disponibili
make list-backups
```

### Ollama non risponde

1. Verifica che il server sia attivo:
   ```bash
   curl http://localhost:11434/api/tags
   ```
2. Specifica l'URL corretto:
   ```bash
   make review-scores-ollama OLLAMA_URL=http://192.168.129.14:11434
   ```

### Debugging e Log
Visualizza i log di sistema in tempo reale per diagnosticare problemi.

```bash
# Apri visualizzatore interattivo
make logs

# Visualizza ultime 100 righe di un log specifico (selezionandolo dal menu)
make logs LINES=100
```


### Analisi bloccata su un file

```bash
# Forza ri-analisi di un codice specifico
make run-force-code CODE=RMIC8GA002

# Rimuovi dal registro e riprova
make registry-remove CODE=RMIC8GA002
make run
```

---

## 📁 Struttura Directory

```
ptof_inbox/          # PDF da analizzare
ptof_processed/      # PDF archiviati dopo analisi
ptof_discarded/      # PDF scartati (non-PTOF, duplicati)
ptof_md/             # Markdown estratti dai PDF
analysis_results/    # JSON con risultati analisi
reports/             # Output legacy o manuali
logs/                # File di log
data/                # Configurazioni e dati (analysis_summary.csv, attivita.json)
```

---

## 🔗 Link Utili

- [README principale](../../README.md)
- [Mappa documentazione](../MAP.md)
- [Dashboard Streamlit](http://localhost:8501) (dopo `make dashboard`)
- [Portale Upload](http://localhost:8502) (dopo `make outreach-portal`)
