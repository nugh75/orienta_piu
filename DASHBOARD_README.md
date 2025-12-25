# Dashboard Analisi PTOF - Guida Rapida

## Stato del Sistema ✅

La dashboard Streamlit è **pienamente funzionante** con tutti i componenti verificati.

### Test Eseguiti (25/12/2025)

- ✅ Moduli Python (streamlit, plotly, pandas, numpy)
- ✅ File dati (91 scuole, 43 colonne)
- ✅ Integrità CSV (indice medio: 2.99)
- ✅ Moduli custom (data_utils, data_manager)
- ✅ 15 pagine dashboard
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
- **reports/best_practice_orientamento_narrativo.md** - Report best practice generato con LLM

## Metodologia Report Best Practice LLM

Il report narrativo sulle best practice viene generato con un'architettura a due livelli:

### Fase 1: Incremento (Ollama)
Per ogni scuola analizzata:
1. Estrae punti di forza, didattica orientativa, opportunità formative
2. Identifica progetti, partnership e azioni di sistema
3. Arricchisce il report esistente con le nuove informazioni
4. Formatta automaticamente **codice** e **nome scuola** in neretto

### Fase 2: Refactoring (Gemini 3)
Ogni N scuole (default: 10), Gemini riorganizza il report:
- Elimina ridondanze e ripetizioni
- Unifica sottotitoli simili sotto categorie più ampie
- Migliora la fluidità narrativa con connettivi
- Preserva tutti i riferimenti specifici alle scuole

### Gestione Rate Limit
Se Gemini risponde con errore 429 (rate limit), il sistema:
1. Salta il refactoring corrente
2. Continua con le prossime N scuole
3. Riprova automaticamente al prossimo ciclo

### Comandi
```bash
make best-practice-llm                    # Default (refactoring ogni 10 scuole)
make best-practice-llm REFACTOR_EVERY=5   # Refactoring ogni 5 scuole
make best-practice-llm-reset              # Ricomincia da zero
```

## Supporto

Per problemi o domande:
1. Verifica questo README
2. Esegui lo script di test: vedi sezione "Test Eseguiti"
3. Controlla i log di Streamlit

---

**Dashboard PTOF - PRIN 2022**
*Sistema di analisi automatizzata dei Piani Triennali dell'Offerta Formativa*
