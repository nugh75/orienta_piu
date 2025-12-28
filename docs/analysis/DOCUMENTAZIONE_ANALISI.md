# Documentazione Analisi PTOF - Orientamento Scolastico

## Introduzione

Questo documento descrive in dettaglio il sistema di analisi automatica dei Piani Triennali dell'Offerta Formativa (PTOF) per la valutazione delle pratiche di orientamento scolastico. L'obiettivo è fotografare oggettivamente come le scuole italiane integrano l'orientamento nei loro documenti programmatici.

Per la mappa documentazione vedi [MAP](../MAP.md).

---

## 1. Processo di Analisi

### 1.1 Flusso Operativo

```
PDF PTOF → Estrazione Testo → Chunking (8000 car.) → Analisi per Chunk → Aggregazione → Output Finale
```

### 1.2 Fasi Dettagliate

| Fase | Descrizione | Output |
|:-----|:------------|:-------|
| **Estrazione** | Il PDF viene convertito in testo puro | Testo con riferimenti pagina |
| **Validazione** | Verifica presenza keyword PTOF | Skip se non valido |
| **Chunking** | Divisione in blocchi da 8.000 caratteri | N chunk per documento |
| **Analisi Chunk** | LLM identifica evidenze orientamento | JSON con findings |
| **Aggregazione** | Combinazione evidenze + scoring finale | JSON strutturato + Report MD |

### 1.3 Modello di Analisi

- **Modello:** Ollama `gemma3:27b` (locale)
- **Dimensione Chunk:** 8.000 caratteri
- **Temperatura:** 0.3 (output deterministico)
- **Contesto:** 16.384 token

---

## 2. Struttura dell'Output

### 2.1 File Generati per Ogni Scuola

| File | Contenuto |
|:-----|:----------|
| `{CODICE}_analysis.json` | Dati strutturati con punteggi e evidenze |
| `{CODICE}_analysis.md` | Report narrativo (800-1200 parole) |

### 2.2 CSV Riepilogativo

Il file `data/analysis_summary.csv` contiene tutti i punteggi aggregati per analisi comparative.

---

## 3. Sistema di Scoring

### 3.1 Scala di Valutazione (Likert 1-7)

| Punteggio | Significato | Criterio |
|:---------:|:------------|:---------|
| **1** | Assente | Nessun riferimento nel documento |
| **2** | Minimo | Menzionato genericamente senza dettagli |
| **3** | Limitato | Accenni indiretti o frammentari |
| **4** | Sufficiente | Azioni presenti ma basilari |
| **5** | Buono | Azioni descritte con strumenti specifici |
| **6** | Strutturato | Sistema con responsabilità chiare |
| **7** | Eccellente | Integrato, monitorato e innovativo |

### 3.2 Aree di Valutazione

#### FINALITÀ (Sezione 2.3)
Rispondono alla domanda: *Perché la scuola fa orientamento?*

- **Attitudini Personali**: Scoperta inclinazioni e talenti
- **Interessi**: Esplorazione e sviluppo interessi
- **Progetto di Vita**: Costruzione progetto personale/professionale
- **Transizioni Formative**: Accompagnamento passaggi tra cicli
- **Capacità Orientative**: Sviluppo competenze per scelte consapevoli

#### OBIETTIVI (Sezione 2.4)
Rispondono alla domanda: *Cosa vuole raggiungere la scuola?*

- **Riduzione Abbandono**: Prevenzione dispersione scolastica
- **Continuità Territoriale**: Collegamento scuola-territorio
- **Contrasto NEET**: Prevenzione inattività post-diploma
- **Apprendimento Permanente**: Promozione lifelong learning

#### GOVERNANCE (Sezione 2.5)
- Coordinamento servizi
- Dialogo docenti-studenti
- Rapporto scuola-genitori
- Monitoraggio azioni
- Sistema inclusione fragilità

#### DIDATTICA ORIENTATIVA (Sezione 2.6)
- Apprendimento esperienziale
- Didattica laboratoriale
- Flessibilità spazi/tempi
- Interdisciplinarità

#### OPPORTUNITÀ (Sezione 2.7)
- Attività culturali
- Laboratori espressivi
- Attività ludico-ricreative
- Volontariato
- Sport

---

## 4. Indici Aggregati

### 4.1 Formule di Calcolo

**Media Finalità:**
```
mean_finalita = (attitudini + interessi + progetto_vita + transizioni + capacità_orientative) / 5
```

**Media Obiettivi:**
```
mean_obiettivi = (abbandono + continuità + neet + lifelong) / 4
```

**Indice di Maturità Globale:**
```
maturity_index = (mean_finalita + mean_obiettivi + mean_governance + mean_didattica + mean_opportunita) / 5
```

### 4.2 Interpretazione Indice di Maturità

| Range | Interpretazione |
|:-----:|:----------------|
| 1.0 - 2.5 | Orientamento assente o episodico |
| 2.6 - 4.0 | Orientamento presente ma frammentato |
| 4.1 - 5.5 | Orientamento strutturato |
| 5.6 - 7.0 | Orientamento sistemico e integrato |

---

## 5. Primi Risultati (Esempio)

### 5.1 Riepilogo Scuole Analizzate

| Scuola | Comune | Indice Maturità | Media Finalità | Media Obiettivi |
|:-------|:-------|:---------------:|:--------------:|:---------------:|
| SAN MARCELLINO CENTRO | San Marcellino | **5.4** | 5.4 | 5.5 |
| IC2 RAVARINO | Ravarino | **5.1** | 5.4 | 4.5 |
| Istituto Comprensivo Capranica | Capranica | **5.2** | 5.4 | 5.0 |

### 5.2 Esempio Report Narrativo

**Scuola:** SAN MARCELLINO CENTRO (CEIC87400L)

> **Collocazione dell'orientamento nel documento**
> 
> L'orientamento, pur non essendo esplicitamente trattato come un'area tematica autonoma nel PTOF, è intrinsecamente presente in tutta la sua struttura. Il documento pone una forte enfasi sulla formazione integrale del bambino (Pagina 1, 4, 10), sullo sviluppo della sua autonomia, identità e competenze (Pagina 9), e sulla preparazione per la vita in società.
>
> **Gap Analysis**
> 
> Nonostante la ricchezza di contenuti e l'impegno dimostrato, il PTOF presenta alcune lacune in termini di orientamento esplicito. In particolare, manca una sezione dedicata all'orientamento scolastico e professionale, con obiettivi specifici e azioni mirate. L'orientamento verso la scuola primaria è presente, ma in modo frammentario.

### 5.3 Dettaglio Punteggi - SAN MARCELLINO CENTRO

| Dimensione | Punteggio |
|:-----------|:---------:|
| Sezione Orientamento Dedicata | 5 |
| Finalità: Attitudini | 6 |
| Finalità: Interessi | 5 |
| Finalità: Progetto di Vita | 5 |
| Finalità: Transizioni | 3 |
| Obiettivo: Riduzione Abbandono | 6 |
| Obiettivo: Continuità Territorio | 4 |
| Obiettivo: Contrasto NEET | 1 |
| Obiettivo: Lifelong Learning | 6 |
| **N. Partnership** | 5 |
| **N. Attività Censite** | 1 |

---

## 6. Dashboard Interattiva

La dashboard Streamlit permette di:

1. **Visualizzare KPI globali** (scuole analizzate, indice medio, % sezione orientamento)
2. **Filtrare per grado scolastico** (I Grado, II Grado, Infanzia)
3. **Confrontare punteggi** tramite grafici a barre orizzontali
4. **Esplorare singole scuole** con radar chart comparativo
5. **Leggere report completi** direttamente nell'interfaccia

### Accesso Dashboard
```bash
streamlit run dashboard.py
```

---

## 7. Limitazioni

- L'analisi dipende dalla qualità del testo estratto dal PDF
- Documenti mal formattati possono produrre risultati incompleti
- I punteggi riflettono cosa è **scritto** nel PTOF, non cosa viene effettivamente realizzato
- Il modello AI può occasionalmente interpretare erroneamente il contesto

---

## 8. Pipeline e Automazione

### 8.1 Pipeline Completa con Ollama

Esegui analisi e revisione in parallelo:

```bash
make pipeline-ollama MODEL=qwen3:32b
```

Avvia contemporaneamente:
- Analisi PTOF
- Revisione scores (punteggi estremi)
- Revisione report MD (arricchimento)

Parametri:
| Parametro | Default | Descrizione |
|:----------|:--------|:------------|
| `MODEL` | qwen3:32b | Modello Ollama |
| `OLLAMA_URL` | http://192.168.129.14:11434 | URL server |
| `LOW` | 2 | Soglia minima revisione scores |
| `HIGH` | 6 | Soglia massima revisione scores |

### 8.2 Catalogo Buone Pratiche

**Legenda emoji (categorie):**
- 📚 Metodologie Didattiche Innovative
- 🎯 Progetti e Attività Esemplari
- 🤝 Partnership e Collaborazioni Strategiche
- ⚙️ Azioni di Sistema e Governance
- 🌈 Buone Pratiche per l'Inclusione
- 🗺️ Esperienze Territoriali Significative

**Estrazione dataset (Catalogo Pratiche):**
```bash
make best-practice-extract MODEL=qwen3:32b
```

**Reset e rielaborazione completa:**
```bash
make best-practice-extract-reset
```

**Statistiche rapide:**
```bash
make best-practice-extract-stats
```

### 8.3 Comandi Makefile Principali

| Comando | Descrizione |
|:--------|:------------|
| `make run` | Esegue analisi PTOF |
| `make csv` | Rigenera CSV dai JSON |
| `make dashboard` | Avvia dashboard Streamlit |
| `make pipeline-ollama` | Analisi + revisione parallela |
| `make best-practice-extract` | Estrazione buone pratiche (catalogo) |
| `make help` | Mostra tutti i comandi disponibili |

---

## 9. Contatti e Riferimenti

- **Repository:** `/Users/danieledragoni/git/LIste`
- **Script Principale:** `workflow_notebook.py`
- **Dashboard:** `app/Home.py`
- **Documentazione Workflow:** `docs/operations/WORKFLOW_README.md`
