# Meta Report - Best Practices Reporter

Sistema di generazione incrementale di report sulle buone pratiche di orientamento estratte dalle analisi PTOF.

## Panoramica

Il Meta Report Agent analizza i JSON delle analisi PTOF e genera report markdown sulle buone pratiche, a diversi livelli di granularità:

- **School**: Report per singola scuola
- **Regional**: Report aggregato per regione
- **National**: Report nazionale con trend e confronti
- **Thematic**: Report per dimensione (governance, didattica, etc.)

## Quick Start

```bash
# Verifica stato report
make meta-status

# Genera report per una scuola
make meta-school CODE=RMIS001

# Genera prossimo report pendente
make meta-next

# Genera batch di 5 report
make meta-batch N=5
```

## Provider LLM

Il sistema supporta tre provider LLM:

| Provider | Configurazione | Uso |
|----------|---------------|-----|
| **Gemini** | `GEMINI_API_KEY` | Default API, veloce, gratuito |
| **OpenRouter** | `OPENROUTER_API_KEY` | Multi-modello, fallback |
| **Ollama** | `OLLAMA_HOST` | Locale, no costi, batch grandi |

### Selezione Provider

```bash
# Auto (prova in ordine: gemini > openrouter > ollama)
make meta-school CODE=RMIS001

# Provider specifico
make meta-school CODE=RMIS001 PROVIDER=ollama
make meta-regional REGION=Lazio PROVIDER=gemini
```

### Configurazione

```bash
# Gemini (default)
export GEMINI_API_KEY=your_key

# OpenRouter
export OPENROUTER_API_KEY=your_key

# Ollama (locale)
export OLLAMA_HOST=http://localhost:11434
```

## Comandi Make

### Riepilogo Completo

| Comando | Descrizione | Opzioni |
|---------|-------------|---------|
| `make meta-status` | Mostra stato di tutti i report | - |
| `make meta-school CODE=X` | Report singola scuola | `PROVIDER`, `FORCE` |
| `make meta-regional REGION=X` | Report aggregato regione | `PROVIDER`, `FORCE` |
| `make meta-national` | Report nazionale | `PROVIDER`, `FORCE` |
| `make meta-thematic DIM=X` | Report tematico | `PROVIDER`, `FORCE` |
| `make meta-next` | Genera prossimo pendente | `PROVIDER` |
| `make meta-batch N=X` | Genera N report pendenti | `PROVIDER` |

### Opzioni Globali

| Opzione | Valori | Default |
|---------|--------|---------|
| `PROVIDER` | `gemini`, `openrouter`, `ollama` | `auto` |
| `FORCE` | `1` | non impostato (skip se esiste) |

### Stato e Monitoraggio

```bash
make meta-status
```

Output esempio:
```
=== META REPORT STATUS ===

SCHOOLS (234 total)
  ✓ Current:  220
  ⚠ Pending:  14

REGIONAL (20 regions)
  ✓ Current:  12
  ⚠ Stale:    8

NATIONAL
  ⚠ Status: stale

THEMATIC (13 dimensions)
  ✓ Current:  5
  ⚠ Stale:    8

NEXT: make meta-school CODE=RMIS005
```

### Report per Scuola

```bash
# Genera report per una scuola specifica
make meta-school CODE=RMIS001

# Con provider specifico
make meta-school CODE=RMIS001 PROVIDER=ollama

# Forza rigenerazione
make meta-school CODE=RMIS001 FORCE=1
```

**Output**: `reports/meta/schools/RMIS001_best_practices.md`

### Report Regionale

```bash
# Report aggregato per regione
make meta-regional REGION=Lazio
make meta-regional REGION="Emilia Romagna"
make meta-regional REGION=Lombardia PROVIDER=gemini FORCE=1
```

**Output**: `reports/meta/regional/Lazio_best_practices.md`

### Report Nazionale

```bash
# Report complessivo nazionale
make meta-national
make meta-national PROVIDER=ollama FORCE=1
```

**Output**: `reports/meta/national/national_best_practices.md`

### Report Tematici

#### Dimensioni Strutturali

```bash
make meta-thematic DIM=finalita      # Finalità orientative
make meta-thematic DIM=obiettivi     # Obiettivi e risultati attesi
make meta-thematic DIM=governance    # Governance e organizzazione
make meta-thematic DIM=didattica     # Didattica orientativa
make meta-thematic DIM=partnership   # Partnership e reti
```

#### Dimensioni Opportunità (Granulari)

```bash
make meta-thematic DIM=pcto          # PCTO e Alternanza
make meta-thematic DIM=stage         # Stage e Tirocini
make meta-thematic DIM=openday       # Open Day
make meta-thematic DIM=visite        # Visite aziendali/universitarie
make meta-thematic DIM=laboratori    # Laboratori e simulazioni
make meta-thematic DIM=testimonianze # Incontri con esperti
make meta-thematic DIM=counseling    # Counseling individuale
make meta-thematic DIM=alumni        # Rete alumni e mentoring
```

**Output**: `reports/meta/thematic/{DIM}_best_practices.md`

### Elaborazione Automatica

```bash
# Genera il prossimo report pendente
# Priorità: school > regional > national > thematic
make meta-next

# Genera N report pendenti in sequenza
make meta-batch N=5
make meta-batch N=20 PROVIDER=ollama
```

## Dimensioni Tematiche

### Dimensioni Strutturali

| Dimensione | Descrizione |
|------------|-------------|
| `finalita` | Chiarezza delle finalità orientative |
| `obiettivi` | Definizione obiettivi e risultati attesi |
| `governance` | Organizzazione, ruoli e responsabilità |
| `didattica` | Integrazione orientamento nelle attività didattiche |
| `partnership` | Collaborazioni con enti esterni |

### Dimensioni Opportunità (Granulari)

| Dimensione | Descrizione |
|------------|-------------|
| `pcto` | PCTO e Alternanza Scuola-Lavoro |
| `stage` | Stage e Tirocini formativi |
| `openday` | Open Day e Orientamento in Entrata |
| `visite` | Visite Aziendali e Universitarie |
| `laboratori` | Laboratori Orientativi, Simulazioni, Job Shadowing |
| `testimonianze` | Testimonianze e Incontri con Esperti/Professionisti |
| `counseling` | Counseling e Percorsi Individualizzati |
| `alumni` | Rete Alumni e Mentoring |

Le dimensioni granulari estraggono contenuti specifici cercando keywords nelle analisi PTOF esistenti.

## Output

I report vengono salvati in `reports/meta/`:

```
reports/meta/
├── schools/
│   ├── RMIS001_best_practices.md
│   └── MIIS002_best_practices.md
├── regional/
│   ├── Lazio_best_practices.md
│   └── Lombardia_best_practices.md
├── national/
│   └── national_best_practices.md
├── thematic/
│   ├── governance_best_practices.md
│   └── didattica_best_practices.md
└── meta_registry.json
```

### Formato Report

Ogni report include:

```markdown
---
generated_at: 2024-12-28T14:30:00
provider: gemini
report_type: school
school_code: RMIS001
---

# Best Practices - Liceo Scientifico Roma 1

## Executive Summary
[Sintesi 2-3 frasi]

## Pratiche di Eccellenza
[Con citazioni dal PTOF]

## Punti di Forza per Dimensione
[Analisi per area]

## Raccomandazioni
[Suggerimenti]
```

## Flusso Incrementale

Il sistema traccia automaticamente quali report devono essere aggiornati:

```
Nuova analisi JSON
       │
       ▼
┌──────────────────┐
│ Report scuola    │ ◄── Generato/aggiornato
│ diventa "stale"  │
└──────────────────┘
       │
       ▼
┌──────────────────┐
│ Report regionale │ ◄── Marcato come "stale"
│ della scuola     │
└──────────────────┘
       │
       ▼
┌──────────────────┐
│ Report nazionale │ ◄── Marcato come "stale"
└──────────────────┘
```

### Priorità Elaborazione

`make meta-next` elabora in questo ordine:

1. **Scuole nuove** - Analisi senza report
2. **Scuole aggiornate** - Analisi più recente del report
3. **Regioni stale** - Con nuove scuole
4. **Nazionale** - Se regioni aggiornate
5. **Tematici** - Se dati cambiati

## Integrazione Workflow

### Con Analisi PTOF

```bash
# Dopo analisi, genera automaticamente report scuola
make run-force-code CODE=RMIS001 && make meta-school CODE=RMIS001
```

### Batch Notturno

```bash
# Cron job per aggiornare report pendenti
0 2 * * * cd /path/to/project && make meta-batch N=20 PROVIDER=ollama
```

### Monitoraggio Continuo

```bash
# Script per elaborare tutto il pendente
while make meta-next; do
  sleep 5
done
```

## Best Practices

### 1. Usa Ollama per Batch Grandi

```bash
# Ollama è locale, no rate limits, no costi
make meta-batch N=50 PROVIDER=ollama
```

### 2. Rigenera Report Regionali dopo Batch Scuole

```bash
# Prima le scuole
make meta-batch N=20 PROVIDER=ollama

# Poi le regioni
make meta-regional REGION=Lazio FORCE=1
make meta-regional REGION=Lombardia FORCE=1
```

### 3. Controlla Status Regolarmente

```bash
# Verifica cosa c'è da fare
make meta-status

# Elabora il pendente
make meta-next
```

### 4. Forza Rigenerazione Solo se Necessario

```bash
# FORCE rigenera anche se esiste
make meta-school CODE=RMIS001 FORCE=1

# Senza FORCE, salta se già generato
make meta-school CODE=RMIS001
```

## Troubleshooting

### Provider Non Disponibile

```
Error: No LLM provider available
```

**Soluzione**: Configura almeno un provider:
```bash
export GEMINI_API_KEY=your_key
# oppure
export OPENROUTER_API_KEY=your_key
# oppure
export OLLAMA_HOST=http://localhost:11434
```

### Analisi Non Trovata

```
[school] No analysis found for RMIS001
```

**Soluzione**: Verifica che esista `analysis_results/RMIS001_PTOF_analysis.json`

### Ollama Non Raggiungibile

```
[ollama] Connection refused
```

**Soluzione**:
```bash
# Verifica che Ollama sia attivo
curl http://localhost:11434/api/tags

# Avvia Ollama se necessario
ollama serve
```

## API Programmatica

```python
from src.agents.meta_report import MetaReportOrchestrator

# Inizializza con provider specifico
orchestrator = MetaReportOrchestrator(provider_name="gemini")

# Genera report
orchestrator.generate_school("RMIS001")
orchestrator.generate_regional("Lazio")
orchestrator.generate_national()
orchestrator.generate_thematic("governance")

# Elabora pendenti
orchestrator.generate_next()
orchestrator.generate_batch(count=10)

# Stato
orchestrator.print_status()
```

## Struttura Codice

```
src/agents/meta_report/
├── __init__.py
├── cli.py              # CLI per comandi make
├── orchestrator.py     # Coordinatore principale
├── registry.py         # Tracking stato report
├── providers/
│   ├── __init__.py
│   ├── base.py         # Interfaccia base provider
│   ├── gemini.py       # Google Gemini
│   ├── openrouter.py   # OpenRouter API
│   └── ollama.py       # Ollama locale
└── reporters/
    ├── __init__.py
    ├── base.py         # Classe base reporter
    ├── school.py       # Report singola scuola
    ├── regional.py     # Report regionale
    ├── national.py     # Report nazionale
    └── thematic.py     # Report tematico
```
