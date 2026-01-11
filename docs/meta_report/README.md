# Meta Report - Attività Reporter

Sistema di generazione incrementale di report sulle attività di orientamento estratte dalle analisi PTOF.

## Panoramica

Il Meta Report Agent analizza i dati dal file `attivita.csv` e genera report markdown sulle attività di orientamento, a diversi livelli di granularità:

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

| Provider       | Configurazione                | Uso                           |
| -------------- | ----------------------------- | ----------------------------- |
| **Ollama**     | `OLLAMA_HOST`, `OLLAMA_MODEL` | **Default**, locale, no costi |
| **Gemini**     | `GEMINI_API_KEY`              | API cloud, veloce             |
| **OpenRouter** | `OPENROUTER_API_KEY`          | Multi-modello, fallback       |

### Selezione Provider

```bash
# Auto (prova in ordine: ollama > gemini > openrouter)
make meta-school CODE=RMIS001

# Provider specifico
make meta-school CODE=RMIS001 PROVIDER=gemini
make meta-regional REGION=Lazio PROVIDER=openrouter
```

### Configurazione

```bash
# Ollama (default) - modello: qwen3:32b
export OLLAMA_HOST=http://192.168.129.14:11434  # server Ollama remoto
export OLLAMA_MODEL=qwen3:32b  # opzionale, è il default

# Gemini
export GEMINI_API_KEY=your_key

# OpenRouter
export OPENROUTER_API_KEY=your_key
```

## Comandi Make

### Riepilogo Completo

| Comando                       | Descrizione                    | Opzioni             |
| ----------------------------- | ------------------------------ | ------------------- |
| `make meta-status`            | Mostra stato di tutti i report | -                   |
| `make meta-school CODE=X`     | Report singola scuola          | `PROVIDER`, `FORCE` |
| `make meta-regional REGION=X` | Report aggregato regione       | `PROVIDER`, `FORCE` |
| `make meta-national`          | Report nazionale               | `PROVIDER`, `FORCE` |
| `make meta-thematic DIM=X`    | Report tematico                | `PROVIDER`, `FORCE` |
| `make meta-next`              | Genera prossimo pendente       | `PROVIDER`          |
| `make meta-batch N=X`         | Genera N report pendenti       | `PROVIDER`          |

### Opzioni Globali

| Opzione    | Valori                           | Default                        |
| ---------- | -------------------------------- | ------------------------------ |
| `PROVIDER` | `gemini`, `openrouter`, `ollama` | `auto`                         |
| `FORCE`    | `1`                              | non impostato (skip se esiste) |

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

**Output**: `reports/meta/schools/RMIS001_attivita.md`

### Report Regionale

```bash
# Report aggregato per regione
make meta-regional REGION=Lazio
make meta-regional REGION="Emilia Romagna"
make meta-regional REGION=Lombardia PROVIDER=gemini FORCE=1
```

**Output**: `reports/meta/regional/Lazio_attivita.md`

### Report Nazionale

```bash
# Report complessivo nazionale
make meta-national
make meta-national PROVIDER=ollama FORCE=1
```

**Output**: `reports/meta/national/national_attivita.md`

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

**Output**: `reports/meta/thematic/{DIM}_attivita.md`

#### Opzioni Aggiuntive

| Variabile env                       | Descrizione                  | Default         |
| ----------------------------------- | ---------------------------- | --------------- |
| `META_REPORT_INCLUDE_REGIONS`       | Include sezioni per regione  | `0` (disattivo) |
| `META_REPORT_MIN_THEME_CASES`       | Soglia minima casi per tema  | `5`             |
| `META_REPORT_THEME_CHUNK_SIZE`      | Casi per chunk               | `30`            |
| `META_REPORT_THEME_CHUNK_THRESHOLD` | Soglia per attivare chunking | `60`            |

```bash
# Include anche le sezioni per regione
META_REPORT_INCLUDE_REGIONS=1 make meta-thematic DIM=pcto

# Soglia minima casi per tema (temi con meno casi vanno in "Altri temi emergenti")
META_REPORT_MIN_THEME_CASES=5 make meta-thematic DIM=pcto

# Chunking (bilanciamento costo/qualità)
META_REPORT_THEME_CHUNK_SIZE=80 META_REPORT_THEME_CHUNK_THRESHOLD=160 make meta-thematic DIM=pcto
```

#### Profili di Analisi

Il profilo determina il focus narrativo del report. Specificalo con `PROMPT=`:

| Profilo       | Descrizione                              |
| ------------- | ---------------------------------------- |
| `overview`    | Quadro complessivo (default)             |
| `innovative`  | Focus su pratiche innovative e originali |
| `comparative` | Confronti territoriali dettagliati       |
| `impact`      | Valutazione efficacia e impatto          |
| `operational` | Raccomandazioni operative concrete       |

```bash
make meta-thematic DIM=pcto PROMPT=overview
make meta-thematic DIM=pcto PROMPT=innovative
make meta-thematic DIM=pcto PROMPT=comparative
make meta-thematic DIM=pcto PROMPT=impact
make meta-thematic DIM=pcto PROMPT=operational
```

#### Filtri Disponibili

Puoi filtrare i dati per specifici attributi delle scuole:

| Filtro          | Parametro Make | Descrizione                 |
| --------------- | -------------- | --------------------------- |
| Regione         | `REGIONE`      | Es: Lazio, Lombardia        |
| Tipo scuola     | `TIPO`         | Es: Liceo, Istituto Tecnico |
| Ordine/grado    | `ORDINE`       | Es: ii-grado, i-grado       |
| Provincia       | `PROVINCIA`    | Es: RM, MI                  |
| Area geografica | `AREA`         | Es: Nord, Centro, Sud       |
| Stato           | `STATO`        | statale, paritaria          |
| Territorio      | `TERRITORIO`   | Es: urbano, rurale          |

```bash
# Filtro singolo
make meta-thematic DIM=pcto ORDINE=ii-grado

# Filtri multipli
make meta-thematic DIM=pcto REGIONE=Lazio TIPO=Liceo

# Combinazione filtri + profilo
make meta-thematic DIM=pcto REGIONE=Lombardia ORDINE=ii-grado PROMPT=comparative
```

#### Naming dei File Output

Il nome del file di output riflette filtri e profilo applicati:

```
{DIM}[__{filtri}][__profile={profilo}]_attivita.md
```

Esempi:

- `pcto_attivita.md` - nessun filtro, profilo default
- `pcto__ordine_grado=ii-grado_attivita.md` - filtro ordine/grado
- `pcto__ordine_grado=ii-grado__profile=overview_attivita.md` - filtro + profilo
- `pcto__regione=Lazio__tipo_scuola=Liceo_attivita.md` - filtri multipli

Per ogni report tematico viene salvato anche un file CSV con la tabella delle attività:
`reports/meta/thematic/{DIM}[__{filtri}]_attivita.activities.csv`

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

| Dimensione    | Descrizione                                         |
| ------------- | --------------------------------------------------- |
| `finalita`    | Chiarezza delle finalità orientative                |
| `obiettivi`   | Definizione obiettivi e risultati attesi            |
| `governance`  | Organizzazione, ruoli e responsabilità              |
| `didattica`   | Integrazione orientamento nelle attività didattiche |
| `partnership` | Collaborazioni con enti esterni                     |

### Dimensioni Opportunità (Granulari)

| Dimensione      | Descrizione                                         |
| --------------- | --------------------------------------------------- |
| `pcto`          | PCTO e Alternanza Scuola-Lavoro                     |
| `stage`         | Stage e Tirocini formativi                          |
| `openday`       | Open Day e Orientamento in Entrata                  |
| `visite`        | Visite Aziendali e Universitarie                    |
| `laboratori`    | Laboratori Orientativi, Simulazioni, Job Shadowing  |
| `testimonianze` | Testimonianze e Incontri con Esperti/Professionisti |
| `counseling`    | Counseling e Percorsi Individualizzati              |
| `alumni`        | Rete Alumni e Mentoring                             |

### Dimensioni Tematiche (Analisi Specifica)

Queste dimensioni permettono di analizzare temi specifici trasversalmente a tutte le scuole:

| Dimensione           | Descrizione                    | Keywords                                                |
| -------------------- | ------------------------------ | ------------------------------------------------------- |
| `valutazione`        | Valutazione e Autovalutazione  | valutazione, autovalutazione, invalsi, verifiche        |
| `formazione_docenti` | Formazione Docenti             | formazione docenti, aggiornamento professionale         |
| `cittadinanza`       | Cittadinanza e Legalità        | cittadinanza, legalità, educazione civica, costituzione |
| `digitalizzazione`   | Digitalizzazione               | digitale, coding, robotica, informatica, tecnologie     |
| `inclusione`         | Inclusione e BES               | inclusione, bes, disabilità, dsa, sostegno              |
| `continuita`         | Continuità e Accoglienza       | continuità, accoglienza, passaggio, raccordo            |
| `famiglie`           | Rapporti con Famiglie          | famiglie, genitori, patto educativo                     |
| `lettura`            | Lettura e Scrittura            | lettura, scrittura, biblioteca, letteratura             |
| `orientamento`       | Orientamento                   | orientamento, scelta scolastica, progetto di vita       |
| `arte`               | Arte e Creatività              | arte, creatività, musica, teatro                        |
| `lingue`             | Lingue Straniere               | lingue straniere, inglese, clil, certificazioni         |
| `stem`               | STEM e Ricerca                 | stem, steam, scienze, sperimentazione                   |
| `matematica`         | Matematica e Logica            | matematica, logica, problem solving, geometria          |
| `disagio`            | Prevenzione Disagio            | disagio, bullismo, cyberbullismo, dispersione           |
| `intercultura`       | Intercultura e Lingue          | intercultura, multiculturalità, integrazione stranieri  |
| `sostenibilita`      | Sostenibilità e Ambiente       | sostenibilità, ambiente, ecologia, agenda 2030          |
| `sport`              | Sport e Benessere              | sport, benessere, educazione fisica, salute             |
| `imprenditorialita`  | Imprenditorialità              | imprenditorialità, impresa, start up, business          |
| `sistema`            | Azioni di Sistema e Governance | azioni di sistema, organigramma, funzioni strumentali   |

**Esempi:**

```bash
make meta-thematic DIM=orientamento REGIONE=Lazio FORCE=1
make meta-thematic DIM=digitalizzazione FORCE=1
make meta-thematic DIM=inclusione ORDINE=ii-grado
```

Le dimensioni tematiche estraggono contenuti specifici cercando keywords nelle analisi PTOF esistenti.

## Output

I report vengono salvati in `reports/meta/`:

```
reports/meta/
├── schools/
│   ├── RMIS001_attivita.md
│   └── MIIS002_attivita.md
├── regional/
│   ├── Lazio_attivita.md
│   └── Lombardia_attivita.md
├── national/
│   └── national_attivita.md
├── thematic/
│   ├── governance_attivita.md
│   └── didattica_attivita.md
└── meta_registry.json
```

### Formato Report

Ogni report include header YAML con metadati e contenuto strutturato.

#### Report Scuola

```markdown
---
generated_at: 2024-12-28T14:30:00
provider: gemini
report_type: school
school_code: RMIS001
---

# Liceo Scientifico Roma 1

## Contesto

[Tipo scuola, territorio, caratteristiche]

## Punti di Forza

[Iniziative efficaci, metodologie innovative]

## Aree di Sviluppo

[Cosa potrebbe essere potenziato]

## Conclusioni

[Sintesi profilo orientativo]
```

#### Report Tematico (nuova struttura)

```markdown
---
dimension: orientamento
practices_analyzed: 2391
schools_involved: 263
filters: ordine_grado=ii-grado
prompt_profile: overview
---

# Orientamento

## Panoramica temi

| Tema     | Casi | Scuole | Regioni principali         |
| -------- | ---- | ------ | -------------------------- |
| PCTO     | 450  | 120    | Lombardia (80), Lazio (65) |
| Open Day | 320  | 95     | Veneto (45), Piemonte (40) |

...

## Analisi per tematiche

### PCTO

[Analisi narrativa con esempi Nome Scuola (Codice)]

### Open Day

[...]

## Altri temi emergenti

[Temi con < 5 casi elencati in modo compatto]

## Sintesi delle analisi tematiche

[Trend principali, differenze territoriali, raccomandazioni]
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

## Raccomandazioni Operative

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
