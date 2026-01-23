# Make - Quick Start

Elenco rapido dei comandi principali. Per la guida completa vedi
[MAKE_REFERENCE](MAKE_REFERENCE.md).

## Core commands

- make setup
- make run
- make workflow
- make dashboard
- make refresh
- make help
- make wizard

## Workflow tipici

### Analisi standard
```bash
make run
make dashboard
```

### Refresh dati
```bash
make csv
make dashboard
```

### Download + analisi
```bash
make download-sample
make workflow
```

### Ciclo stratificato con Ollama remoto
```bash
# Usa .env per OLLAMA_HOST (raccomandato)
make strata-cycle MAX_DOWNLOADS=50

# Con modelli specifici per ogni ruolo
make strata-cycle \
  PROVIDER_WORKFLOW=ollama \
  ANALYST_WORKFLOW=gemma3:27b \
  REVIEWER_WORKFLOW=gemma3:27b \
  REFINER_WORKFLOW=gemma3:27b \
  SYNTHESIZER_WORKFLOW=gemma3:27b \
  MAX_DOWNLOADS=50
```

## Catalogo buone pratiche
```bash
make activity-extract
make activity-extract-reset
make activity-extract-stats
```

## Configurazione ambiente (.env)

```bash
# Server Ollama
OLLAMA_HOST=http://192.168.129.14:11434
OLLAMA_MODEL=qwen3:latest

# API per ricerca PTOF (opzionali - fallback)
TAVILY_API_KEY=tvly-xxxxx
BRAVE_API_KEY=BSAxxxxx
PERPLEXITY_API_KEY=pplx-xxxxx
```

## Note
- Per configurazioni modelli usa make config / make config-show.
- Per revisioni e manutenzione vedi MAKE_REFERENCE.
- `OLLAMA_HOST` viene letto automaticamente dal file `.env`.
