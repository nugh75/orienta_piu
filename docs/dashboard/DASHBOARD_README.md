# Dashboard Analisi PTOF - Guida Rapida

## Stato del Sistema ✅

La dashboard Streamlit è **pienamente funzionante** con tutti i componenti verificati.

### Test Eseguiti (25/12/2025)

- ✅ Moduli Python (streamlit, plotly, pandas, numpy)
- ✅ File dati (91 scuole, 43 colonne)
- ✅ Integrità CSV (indice medio: 2.99)
- ✅ Moduli custom (data_utils, data_manager)
- ✅ 16 pagine dashboard
- ✅ Sintassi corretta in tutti i file

## Avvio Rapido

### Metodo 1: Script di Avvio (Consigliato)

```bash
./start_dashboard.sh
```

### Metodo 2: Comando Diretto

```bash
streamlit run app/Home.py
```

### Metodo 3: Modulo Python

```bash
python -m streamlit run app/Home.py
```

## Accesso alla Dashboard

Una volta avviata, la dashboard sarà disponibile su:

- **Locale**: http://localhost:8501
- **Rete**: http://192.168.4.117:8501 (se accessibile da rete locale)

## Struttura Dashboard

### Homepage (Home.py)
- 📈 Indicatori chiave (scuole, indice medio, sezioni dedicate, partnership)
- 📊 Distribuzione per territorio, grado e area
- 🧩 Medie per dimensione (Finalità, Obiettivi, Governance, Didattica, Opportunità)
- 📋 Classifica completa

### Pagine Disponibili

1. **📊 Confronti Gruppi** - Comparazioni statistiche tra gruppi di scuole
2. **🗺️ Mappa Italia** - Visualizzazione geografica, analisi regionale e **hotspot geografici**
3. **🏆 Benchmark** - Classifiche e posizionamento relativo
4. **📈 Indicatori Statistici** - Test statistici, KPI e **confronto Statale vs Paritaria**
5. **🔬 Clustering e Correlazioni** - Cluster, correlazioni, word cloud e **debolezze sistemiche**
6. **🕸️ Visualizzazioni Avanzate** - Radar chart, Sankey, Sunburst
7. **🏫 Dettaglio Scuola** - Scheda approfondita singola scuola + **export PDF**
8. **📋 Esplora Dati** - Dati grezzi, statistiche descrittive e **filtri con export avanzato**
9. **ℹ️ Documentazione** - Metodologia e guida al sistema
10. **✏️ Modifica Metadati** - Revisione e modifica dati scuole
11. **🛡️ Backup** - Gestione backup e ripristino
12. **🎯 Gap Analysis** - Distanza da best-in-class e raccomandazioni automatiche
13. **👥 Confronto Peer** - Matching e confronto con scuole simili
14. **💡 Best Practice** - Text mining dai report delle scuole eccellenti
15. **📊 Report Regionali** - Sintesi per USR con export Excel/CSV
16. **📚 Report Best Practice LLM** - Report narrativo generato con AI (Ollama + Gemini)

## Filtri Globali

La sidebar offre filtri per:
- 🌍 Area Geografica (Nord Ovest, Nord Est, Centro, Sud, Isole)
- 🏫 Tipo Scuola (Liceo, Tecnico, Professionale, ecc.)
- 🗺️ Territorio (Metropolitano, Non Metropolitano)
- 📚 Ordine Grado (Infanzia, Primaria, I Grado, II Grado)
- 📊 Range Indice Robustezza (1.0 - 7.0)

## Indicatori Principali

### Indice di Robustezza (1-7)
Media delle 5 dimensioni di orientamento:
- **Finalità**: Attitudini, Interessi, Progetto di vita
- **Obiettivi**: Abbandono, NEET, Lifelong learning
- **Governance**: Coordinamento, Monitoraggio
- **Didattica**: Laboratoriale, Interdisciplinare
- **Opportunità**: Culturali, Espressive, Sportive

### Scala Likert
- 1: Assente
- 4: Sufficiente
- 7: Eccellente

## Risoluzione Problemi

### La dashboard non si avvia

1. Verifica le dipendenze:
```bash
pip install streamlit plotly pandas numpy
```

2. Verifica i file:
```bash
python3 -c "from src.data.data_manager import update_index_safe; update_index_safe()"
```

3. Controlla i log:
```bash
streamlit run app/Home.py --logger.level=debug
```

### Dati non aggiornati

Usa il pulsante "🔄 Aggiorna Dati" nella sidebar oppure:

```bash
python3 -c "from src.data.data_manager import update_index_safe; update_index_safe()"
```

### Porta 8501 già in uso

```bash
streamlit run app/Home.py --server.port=8502
```

## Performance

Per migliorare le performance, installa Watchdog:

```bash
pip install watchdog
```

## Configurazione

La configurazione si trova in [.streamlit/config.toml](.streamlit/config.toml):

```toml
[theme]
base = "light"
```

## File Dati

- **data/analysis_summary.csv** - Dataset principale (91 scuole)
- **analysis_results/*.json** - File analisi JSON per scuola
- **analysis_results/*.md** - Report analisi in markdown
- **reports/best_practice_orientamento.md** - Report statistico (algoritmi)
- **reports/best_practice_orientamento_narrativo.md** - Report narrativo (Ollama LLM)
- **reports/best_practice_orientamento_sintetico.md** - Report sintetico (Gemini refactoring)

## Metodologia Report Best Practice LLM

Il sistema genera tre tipologie di report sulle best practice dell'orientamento:

| Report | Comando | Descrizione |
|--------|---------|-------------|
| **Statistico** | `make best-practice` | Dati aggregati, classifiche, tabelle (algoritmi) |
| **Narrativo** | `make best-practice-llm` | Analisi discorsiva completa (Ollama) |
| **Sintetico** | `make best-practice-llm-synth` | Versione condensata del narrativo (Gemini) |

### Fase 1: Report Narrativo (Ollama)

Per ogni scuola analizzata, il modello qwen3:32b:
1. Estrae punti di forza, didattica orientativa, opportunità formative
2. Identifica progetti, partnership e azioni di sistema
3. Arricchisce il report esistente con le nuove informazioni
4. Divide il contenuto per **tipologia di scuola** (da CSV)
5. Formatta automaticamente **codice** e **nome scuola** in neretto

#### Struttura del Report Narrativo

Il report è organizzato per:
- **Sezioni principali** (##): Metodologie, Progetti, Partnership, Governance, Inclusione, Territorio
- **Sottotitoli specifici** (####): Descrivono l'attività concreta (es. "Visite ai campus universitari")
- **Tipologia scuola** (#####): Divisione per ordine e grado

Le 6 tipologie di scuola (dal campo `tipo_scuola` del CSV):
1. Scuole dell'Infanzia
2. Scuole Primarie
3. Scuole Secondarie di Primo Grado
4. Licei
5. Istituti Tecnici
6. Istituti Professionali

### Fase 2: Report Sintetico (Gemini)

Comando separato che processa il report narrativo **sezione per sezione**:
- Estrae ogni sezione `##` dal report narrativo
- Invia ogni sezione a Gemini per il refactoring
- Elimina ridondanze mantenendo tutti i riferimenti alle scuole
- Unifica contenuti simili sotto categorie più ampie
- Riduce la lunghezza del 30-50%

#### Gestione Rate Limit
- **Errore 429 Gemini**: Fallback automatico a OpenRouter (GPT OSS 120B)
- **Backup automatico**: Creazione di `.bak` prima di sovrascrivere
- **Sezione troppo corta**: Mantiene l'originale se riduzione >80%

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

## Supporto

Per problemi o domande:
1. Verifica questo README
2. Esegui lo script di test: vedi sezione "Test Eseguiti"
3. Controlla i log di Streamlit

---

**Dashboard PTOF - PRIN 2022**
*Sistema di analisi automatizzata dei Piani Triennali dell'Offerta Formativa*
