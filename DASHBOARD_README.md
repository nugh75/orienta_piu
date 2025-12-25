# Dashboard Analisi PTOF - Guida Rapida

## Stato del Sistema ✅

La dashboard Streamlit è **pienamente funzionante** con tutti i componenti verificati.

### Test Eseguiti (25/12/2025)

- ✅ Moduli Python (streamlit, plotly, pandas, numpy)
- ✅ File dati (91 scuole, 43 colonne)
- ✅ Integrità CSV (indice medio: 2.99)
- ✅ Moduli custom (data_utils, data_manager)
- ✅ 11 pagine dashboard
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
2. **🗺️ Mappa Italia** - Visualizzazione geografica e analisi regionale
3. **🏆 Benchmark** - Classifiche e posizionamento relativo
4. **📈 Indicatori Statistici** - Test statistici e KPI dettagliati
5. **🔬 Clustering e Correlazioni** - Analisi cluster, correlazioni, word cloud
6. **🕸️ Visualizzazioni Avanzate** - Radar chart, Sankey, Sunburst
7. **🏫 Dettaglio Scuola** - Scheda approfondita singola scuola
8. **📋 Esplora Dati** - Dati grezzi e statistiche descrittive
9. **ℹ️ Documentazione** - Metodologia e guida al sistema
10. **✏️ Modifica Metadati** - Revisione e modifica dati scuole
11. **🛡️ Backup** - Gestione backup e ripristino

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

## Supporto

Per problemi o domande:
1. Verifica questo README
2. Esegui lo script di test: vedi sezione "Test Eseguiti"
3. Controlla i log di Streamlit

---

**Dashboard PTOF - PRIN 2022**
*Sistema di analisi automatizzata dei Piani Triennali dell'Offerta Formativa*
