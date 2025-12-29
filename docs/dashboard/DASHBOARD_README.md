# Dashboard Analisi PTOF - Guida Rapida

Per la mappa documentazione vedi [MAP](../MAP.md).
Per lo stato e i test vedi [DASHBOARD_STATUS](DASHBOARD_STATUS.md).

## Avvio rapido

### Metodo 1: Makefile (consigliato)
```bash
make dashboard
```

### Metodo 2: Script di avvio
```bash
./start_dashboard.sh
```

### Metodo 3: Comando diretto
```bash
streamlit run app/Home.py
```

### Metodo 4: Modulo Python
```bash
python -m streamlit run app/Home.py
```

## Accesso alla dashboard

- Locale: http://localhost:8501
- Rete: http://192.168.4.117:8501 (se accessibile da rete locale)

## Sezioni della dashboard (stato attuale)

- Panoramica (Home): indicatori sintetici e distribuzioni nazionali.
- Dettaglio Scuola: profilo scuola, report MD/PDF, best practice collegate, gap analysis e confronto con peer (radar per tipologia/area/nazionale).
- Confronto PTOF: analisi comparativa tra scuole.
- Analisi territoriale: mappe, confronti geografici e report regionali.
- Ranking e Benchmark: classifiche, posizionamento e confronti multidimensionali.
- Analytics avanzati: analisi statistiche, correlazioni e visualizzazioni esplorative.
- Ricerca / Impatto metodologie: esplorazione di approcci didattici e relativi esiti.
- Catalogo Buone Pratiche: estrazione, filtri, incroci categoria e analisi statistiche (significativita ed effetto).
- Orientamento Scuola: percorso guidato per famiglie/studenti con matching scuole.
- Gestione dati (area amministrativa): qualita, filtri e allineamento metadati.
- Contribuisci: Invia PTOF, Verifica Invio, Richiedi Revisione.
- Documentazione: metodologia e guida.

## Filtri globali

La sidebar offre filtri per:
- Area Geografica (Nord Ovest, Nord Est, Centro, Sud, Isole)
- Tipo Scuola (Liceo, Tecnico, Professionale, ecc.)
- Territorio (Metropolitano, Non metropolitano)
- Ordine Grado (Infanzia, Primaria, I Grado, II Grado)
- Range Indice Robustezza (1.0 - 7.0)

## Framework Metodologico

Il framework traduce la qualità dell'orientamento in criteri osservabili. La valutazione
si basa su evidenze testuali: ciò che è scritto nel PTOF conta più delle intenzioni
dichiarate a parole. Ogni dimensione è composta da sotto‑indicatori che alimentano
un indice sintetico, l'Indice RO.

### Principi di lettura
- Evidenza testuale: ogni valutazione deve essere riconducibile al testo del PTOF.
- Specificità: contano nomi di progetti, tempi, ruoli e responsabilità esplicite.
- Coerenza: obiettivi, azioni e governance devono parlare la stessa lingua.
- Sistemicità: si premiano percorsi strutturati, non iniziative isolate.
- Inclusione: l'orientamento deve adattarsi a bisogni diversi e contesti reali.

### Struttura di valutazione

#### Indicatori strutturali
- **Sezione dedicata**: presenza nel sommario con titolo esplicito, strumenti e responsabilità dichiarati.
- **Partnership**: partner nominati, attività concrete, ruoli chiari e ricadute formative.

#### Macro‑dimensioni (Indice RO)
- **Finalità**: attitudini, interessi, progetto di vita, transizioni formative.
- **Obiettivi**: contrasto dispersione e NEET, continuità territoriale, lifelong learning.
- **Governance**: coordinamento, monitoraggio, coinvolgimento famiglie e inclusione.
- **Didattica orientativa**: laboratori, interdisciplinarità, esperienze sul campo.
- **Opportunità formative**: attività culturali, sportive, espressive e di volontariato.

### Indice RO (Robustezza Orientamento)
L'Indice RO sintetizza la solidità complessiva dell'orientamento.

```
Indice RO = (Finalita + Obiettivi + Governance + Didattica + Opportunita) / 5
```

| Range | Interpretazione |
|-------|-----------------|
| **1.0 - 2.0** | Sistema assente o gravemente carente |
| **2.1 - 3.5** | Sistema basilare, interventi necessari |
| **3.6 - 4.5** | Sistema sufficiente, in evoluzione |
| **4.6 - 5.5** | **Buono**, ben strutturato |
| **5.6 - 7.0** | **Eccellente**, benchmark di riferimento |

### Scala di Valutazione (Likert 1-7)
Ogni sottodimensione viene valutata con una scala a 7 livelli.
- 1: Assente
- 2: Generico
- 3: Limitato
- 4: Sufficiente
- 5: Buono
- 6: Ottimo
- 7: Eccellente

## Dati usati

- data/analysis_summary.csv
- analysis_results/*.json
- analysis_results/*.md
- data/attivita.json
- data/activity_registry.json

## Agenti automatici (panoramica narrativa)

Qui la pipeline viene raccontata come una redazione: ogni agente ha un ruolo chiaro,
così anche chi non è tecnico capisce cosa succede e perché.

### Analisi PTOF (flusso principale)
Flow: PDF → Validazione PTOF → Markdown → Lettore → Sintetizzatore → Critico → Editor → Report + JSON → Registro

Il **Lettore** entra nel documento e costruisce la prima bozza con punteggi ed evidenze.
Se il PTOF è lungo, il **Sintetizzatore** unisce le parti in una visione coerente.
Il **Critico** controlla incoerenze e passaggi deboli, l'**Editor** stabilizza i risultati.
Quando serve, il **Narratore** completa la parte testuale del report.

### Revisione narrativa (arricchimento report)
Flow: PTOF + Report → Arricchitore Narrativo → Report arricchito → Registro

L'**Arricchitore Narrativo** rilegge il PTOF e inserisce dettagli concreti nel report,
così la narrazione resta aderente alle evidenze.

### Revisione punteggi estremi
Flow: PTOF + JSON punteggi → Revisore dei Punteggi → Aggiornamenti → JSON aggiornato → Status

Il **Revisore dei Punteggi** controlla solo i valori troppo alti o troppo bassi per
ridurre distorsioni e mantenere coerenza tra numeri e testo.

### Filtro documenti non-PTOF
Flow: Documento → Filtro Non‑PTOF → Scarto e pulizia → Log

Il **Filtro Non‑PTOF** scarta i documenti non pertinenti o troppo deboli, mantenendo
il dataset pulito.

### Catalogo Buone Pratiche
Flow: PTOF in Markdown → Estrattore Pratiche → Dataset + Registro

L'**Estrattore Pratiche** individua attività concrete, le classifica e costruisce
il catalogo per esplorazioni e confronti.

### Metadati e orchestrazione
Flow: JSON incompleti → Completa Metadati → JSON completi

Il **Completa Metadati** aggiunge informazioni mancanti utili per confronti affidabili.

Flow: Analisi principale + Revisione report + Revisione punteggi → Orchestratore → Dataset allineati

L'**Orchestratore** coordina i passaggi e sincronizza le revisioni quando necessario.

## Catalogo Buone Pratiche

Il catalogo raccoglie pratiche concrete estratte dai PTOF e le rende esplorabili
per categoria, territorio, tipo scuola, target e metodologie.

Funzioni principali:
- Lista, vista raggruppata o tabellare con dettagli e citazioni.
- Mappa di distribuzione geografica e dettaglio per regione.
- Grafici di distribuzione (categoria, regione, tipo scuola).
- Incroci categoria x dimensione con conteggi e percentuali.
- Analisi statistiche con significativita ed effetto.
- Export dei dati filtrati in JSON e CSV.

### Legenda emoji (categorie)

Le emoji aiutano a riconoscere subito la categoria di una pratica.

- 📚 Metodologie Didattiche Innovative
- 🎯 Progetti e Attivita Esemplari
- 🤝 Partnership e Collaborazioni Strategiche
- ⚙️ Azioni di Sistema e Governance
- 🌈 Buone Pratiche per l'Inclusione
- 🗺️ Esperienze Territoriali Significative

## Trasparenza: prompt e dati

### Criteri catalogo buone pratiche

Il catalogo e costruito da estrazioni automatiche su testi PTOF.
Le specifiche operative sono:

- Categorie obbligatorie (6): Metodologie Didattiche Innovative, Progetti e Attivita Esemplari,
  Partnership e Collaborazioni Strategiche, Azioni di Sistema e Governance,
  Buone Pratiche per l'Inclusione, Esperienze Territoriali Significative.
- Tipologie metodologia: elenco predefinito (es. STEM/STEAM, Flipped Classroom, PBL, Cooperative Learning, ecc.).
- Ambiti di attivita: elenco predefinito (es. Orientamento, Inclusione, PCTO, Cittadinanza, ecc.).
- Criterio di selezione: solo pratiche concrete e specifiche con evidenza testuale nel PTOF;
  sono escluse formulazioni generiche.
- Limite estrazione: massimo 5 pratiche per chunk di testo.
- Campi richiesti per pratica: titolo, descrizione, metodologia, target, categoria, tipologie_metodologia,
  ambiti_attivita, citazione_ptof, pagina_evidenza (se presente), partnership_coinvolte (solo per categoria partnership).

### Prompt - Codice

Prompt base (config/prompts.md): vedi file per il dettaglio completo.

#### Review report (OpenRouter/Gemini) - prompt
```text
SEI UN EDITOR SCOLASTICO ESPERTO E METICOLOSO.
Il tuo compito e ARRICCHIRE il report di analisi esistente (Markdown) integrando
dettagli specifici estratti dal documento originale (PTOF), SENZA stravolgere la
struttura del report.

DOCUMENTO ORIGINALE (PTOF - Fonte di verita):
[TESTO PTOF TRONCATO]

REPORT ATTUALE (Bozza da arricchire):
[REPORT ATTUALE]

ISTRUZIONI OPERATIVE:
1. Confronta il report attuale con il PTOF originale.
2. Identifica informazioni di valore presenti nel PTOF ma mancanti nel report:
   - Nomi specifici di progetti.
   - Dati quantitativi (ore, budget, percentuali).
   - Metodologie didattiche particolari.
   - Collaborazioni con enti specifici.
3. Integra le informazioni nelle sezioni esistenti, con stile narrativo.
4. Non cancellare sezioni, mantieni titoli e struttura.
5. Non inventare nulla.
6. Se il report e generico, rendilo piu specifico citando il testo.
7. Se nel PTOF NON esiste un capitolo dedicato all'Orientamento, non inventarlo.

STRUTTURA OBBLIGATORIA DA PRESERVARE:
# Analisi del PTOF [CODICE]
## Report di Valutazione dell'Orientamento
### 1. Sintesi Generale
### 2. Analisi Dimensionale
#### 2.1 Sezione Dedicata all'Orientamento
#### 2.2 Partnership e Reti
#### 2.3 Finalita e Obiettivi
#### 2.4 Governance e Azioni di Sistema
#### 2.5 Didattica Orientativa
#### 2.6 Opportunita Formative
#### 2.7 Registro Dettagliato delle Attivita
### 3. Punti di Forza
### 4. Aree di Debolezza
### 5. Gap Analysis
### 6. Conclusioni

OUTPUT RICHIESTO:
Restituisci il contenuto Markdown del report arricchito, senza commenti extra.
```

#### Review report Ollama - prompt chunk
```text
SEI UN EDITOR SCOLASTICO ESPERTO.
Stai analizzando un CHUNK del documento PTOF originale.

COMPITO: Trova informazioni utili per ARRICCHIRE il report esistente.
CHUNK DEL PTOF ORIGINALE:
[TESTO CHUNK PTOF]

REPORT ATTUALE (da arricchire):
[REPORT ATTUALE - TRONCATO]

RIEPILOGO SCORE JSON:
[RIEPILOGO SCORE]

ISTRUZIONI:
1. Cerca informazioni specifiche mancanti nel report.
2. Verifica se esiste una sezione dedicata all'orientamento.
3. Segnala incongruenze tra report e PTOF.
4. Non inventare nulla.

RISPONDI con JSON:
{
  "enrichments": [
    {
      "section": "sezione report da arricchire",
      "addition": "testo narrativo da aggiungere",
      "source_quote": "citazione breve dal PTOF"
    }
  ],
  "orientamento_section_found": true/false,
  "orientamento_details": "descrizione sezione orientamento",
  "corrections": [
    {
      "issue": "cosa va corretto",
      "reason": "perche"
    }
  ]
}
```

#### Review report Ollama - prompt finale
```text
SEI UN EDITOR SCOLASTICO ESPERTO.
Devi produrre la versione finale ARRICCHITA del report.

REPORT ATTUALE:
[REPORT ATTUALE]

ARRICCHIMENTI DA INTEGRARE:
[JSON ARRICCHIMENTI]

CORREZIONI DA APPLICARE:
[JSON CORREZIONI]

ISTRUZIONI CRITICHE:
1. Integra gli arricchimenti nelle sezioni appropriate.
2. Usa sempre stile narrativo e discorsivo.
3. Applica le correzioni segnalate.
4. Mantieni la struttura esistente del report.
5. Non rimuovere sezioni.

OUTPUT: restituisci solo il report Markdown completo arricchito.
```

#### Review punteggi estremi - prompt
```text
SEI UN REVISORE CRITICO. Devi verificare SOLO i punteggi estremi.
Conferma o modifica i punteggi usando il testo come fonte di verita.

ISTRUZIONE SPECIALE - SEZIONE ORIENTAMENTO:
Verifica con estrema attenzione se esiste un capitolo esplicito di Orientamento.
Se la sezione dedicata e alta ma nel testo non c'e un capitolo specifico,
abbassa il punteggio.

DOCUMENTO ORIGINALE (estratto):
[TESTO PTOF]

PUNTEGGI DA REVISIONARE (JSON):
[JSON PUNTEGGI]

CRITERI PUNTEGGIO (1-7):
1 = Assente
2 = Generico
3 = Limitato
4 = Sufficiente
5 = Buono
6 = Ottimo
7 = Eccellente

FORMATO OUTPUT (solo JSON valido):
{
  "score_updates": [
    {
      "path": "...",
      "old_score": 2,
      "new_score": 3,
      "action": "modify",
      "reason": "Spiega in breve."
    }
  ],
  "review_notes": "Nota generale opzionale."
}

REGOLE:
- Includi un elemento per ogni path ricevuto.
- Se confermi: new_score = old_score e action = "confirm".
- Nessun testo extra, solo JSON.
```

#### Estrazione buone pratiche - prompt
```text
/no_think
SEI UN ESPERTO DI PRATICHE EDUCATIVE E ORIENTAMENTO SCOLASTICO.

ANALIZZA questo estratto di PTOF scolastico e IDENTIFICA le BUONE PRATICHE concrete.

SCUOLA: {school_code}
CHUNK: {chunk_num}/{total_chunks}

TESTO DA ANALIZZARE:
{chunk[:25000]}

---

CATEGORIE DISPONIBILI (usa ESATTAMENTE questi nomi):
1. "Metodologie Didattiche Innovative" - tecniche didattiche avanzate, approcci pedagogici innovativi
2. "Progetti e Attivita Esemplari" - progetti strutturati, attivita significative documentate
3. "Partnership e Collaborazioni Strategiche" - accordi con enti, universita, imprese, associazioni
4. "Azioni di Sistema e Governance" - coordinamento, monitoraggio, strutture organizzative
5. "Buone Pratiche per l'Inclusione" - BES, DSA, disabilita, integrazione stranieri
6. "Esperienze Territoriali Significative" - legame col territorio, PCTO, stage

TIPOLOGIE DI METODOLOGIA (scegli UNA o PIU tra queste, oppure "Altro"):
STEM/STEAM, Coding e Pensiero Computazionale, Flipped Classroom, Peer Education/Tutoring,
Problem Based Learning, Cooperative Learning, Gamification, Debate, Service Learning,
Outdoor Education, Didattica Laboratoriale, Didattica Digitale, CLIL, Storytelling,
Project Work, Learning by Doing, Mentoring

AMBITI DI ATTIVITA (scegli UNO o PIU tra queste, oppure "Altro"):
Orientamento, Inclusione e BES, PCTO/Alternanza, Cittadinanza e Legalita, Educazione Civica,
Sostenibilita e Ambiente, Digitalizzazione, Lingue Straniere, Arte e Creativita,
Musica e Teatro, Sport e Benessere, Scienze e Ricerca, Lettura e Scrittura,
Matematica e Logica, Imprenditorialita, Intercultura, Prevenzione Disagio,
Continuita e Accoglienza, Valutazione e Autovalutazione, Formazione Docenti,
Rapporti con Famiglie

PER OGNI BUONA PRATICA IDENTIFICATA, ESTRAI:
- "categoria": una delle 6 categorie sopra (ESATTAMENTE come scritto)
- "titolo": nome sintetico della pratica (max 100 caratteri)
- "descrizione": descrizione dettagliata di cosa consiste e come funziona (200-500 caratteri)
- "metodologia_desc": come viene implementata concretamente (testo libero)
- "tipologie_metodologia": ARRAY di tipologie metodologiche applicabili (es: ["STEM/STEAM", "Didattica Laboratoriale"])
- "ambiti_attivita": ARRAY di ambiti di attivita (es: ["Orientamento", "Digitalizzazione"])
- "target": a chi e rivolta (studenti, docenti, famiglie, classi specifiche)
- "citazione_ptof": citazione testuale rilevante dal documento (max 200 caratteri)
- "pagina_evidenza": numero di pagina se menzionato (es: "Pagina 15") o "Non specificata"
- "partnership_coinvolte": lista di partner nominati se categoria e Partnership, altrimenti array vuoto

REGOLE FONDAMENTALI:
1. Estrai SOLO pratiche CONCRETE e SPECIFICHE con un nome o una descrizione chiara
2. IGNORA dichiarazioni generiche tipo "la scuola promuove l'orientamento"
3. Ogni pratica DEVE avere evidenze testuali nel documento
4. Se non trovi pratiche significative in questo chunk, rispondi con array vuoto
5. MAX 5 pratiche per chunk (seleziona le piu significative)
6. Il titolo deve essere SPECIFICO (es: "Laboratorio di Robotica Educativa", non "Attivita di laboratorio")
7. tipologie_metodologia e ambiti_attivita devono essere ARRAY di stringhe (anche se c'e un solo elemento)

RISPONDI SOLO con JSON valido (nessun testo prima o dopo):
{
  "pratiche": [
    {
      "categoria": "Nome Categoria Esatto",
      "titolo": "Nome Specifico Pratica",
      "descrizione": "Descrizione dettagliata...",
      "metodologia_desc": "Come viene implementata...",
      "tipologie_metodologia": ["STEM/STEAM", "Didattica Laboratoriale"],
      "ambiti_attivita": ["Orientamento", "Digitalizzazione"],
      "target": "A chi e rivolta",
      "citazione_ptof": "Citazione dal documento...",
      "pagina_evidenza": "Pagina X",
      "partnership_coinvolte": []
    }
  ]
}

Se non trovi pratiche significative:
{"pratiche": []}
```

### Prompt - Tabella

| Prompt | Uso | Input | Output |
|-------|-----|-------|--------|
| Prompt base pipeline (config/prompts.md) | Prompt base pipeline | Testo PTOF / contesto | JSON o testo (vedi codice) |
| Review report (OpenRouter/Gemini) | Arricchisce report MD con dettagli dal PTOF | Testo PTOF, report MD | Markdown report arricchito |
| Review report Ollama - chunk | Estrae arricchimenti da chunk PTOF | Chunk PTOF, report MD, riepilogo score | JSON arricchimenti/correzioni |
| Review report Ollama - finale | Compone report finale | Report attuale, arricchimenti, correzioni | Markdown finale |
| Review punteggi estremi | Rivede punteggi troppo alti o bassi | Testo PTOF, JSON punteggi | JSON aggiornamenti |
| Estrazione buone pratiche | Estrae pratiche concrete dal PTOF | Chunk PTOF | JSON pratiche |

### JSON - Codice

#### Analisi PTOF - output JSON
```json
{
  "metadata": {
    "school_id": "MIIS08900V",
    "denominazione": "...",
    "ordine_grado": "I Grado|II Grado",
    "tipo_scuola": "Liceo|Tecnico|Professionale|I Grado",
    "statale_paritaria": "Statale|Paritaria",
    "area_geografica": "Nord Ovest|Nord Est|Centro|Sud|Isole"
  },
  "ptof_section2": {
    "2_1_ptof_orientamento_sezione_dedicata": {
      "has_sezione_dedicata": 0,
      "score": 1,
      "note": "..."
    },
    "2_2_partnership": {
      "partner_nominati": ["..."],
      "partnership_count": 0
    },
    "2_3_finalita": {
      "finalita_attitudini": { "score": 1 },
      "finalita_interessi": { "score": 1 },
      "finalita_progetto_vita": { "score": 1 }
    }
  },
  "narrative": "Report markdown..."
}
```

#### Review punteggi estremi - output JSON
```json
{
  "score_updates": [
    {
      "path": "ptof_section2.2_1_ptof_orientamento_sezione_dedicata.score",
      "old_score": 2,
      "new_score": 3,
      "action": "modify",
      "reason": "Spiega in breve."
    }
  ],
  "review_notes": "Nota generale opzionale."
}
```

#### Review report Ollama - output JSON (chunk)
```json
{
  "enrichments": [
    {
      "section": "sezione report da arricchire",
      "addition": "testo narrativo da aggiungere",
      "source_quote": "citazione breve dal PTOF"
    }
  ],
  "orientamento_section_found": true,
  "orientamento_details": "descrizione sezione orientamento",
  "corrections": [
    {
      "issue": "cosa va corretto",
      "reason": "perche"
    }
  ]
}
```

#### Catalogo buone pratiche - output prompt
```json
{
  "pratiche": [
    {
      "categoria": "Nome Categoria Esatto",
      "titolo": "Nome Specifico Pratica",
      "descrizione": "Descrizione dettagliata...",
      "metodologia_desc": "Come viene implementata...",
      "tipologie_metodologia": ["STEM/STEAM", "Didattica Laboratoriale"],
      "ambiti_attivita": ["Orientamento", "Digitalizzazione"],
      "target": "A chi e rivolta",
      "citazione_ptof": "Citazione dal documento...",
      "pagina_evidenza": "Pagina X",
      "partnership_coinvolte": []
    }
  ]
}
```

#### Catalogo attività - dataset (data/attivita.json)
```json
{
  "version": "1.0",
  "last_updated": "2025-01-01T12:00:00",
  "extraction_model": "qwen3:32b",
  "schools_processed": 120,
  "total_practices": 560,
  "practices": [
    {
      "id": "uuid",
      "school": {
        "codice_meccanografico": "RMIS02400L",
        "nome": "Istituto ...",
        "tipo_scuola": "Liceo Scientifico",
        "ordine_grado": "Secondaria II Grado",
        "regione": "Lazio",
        "provincia": "Roma",
        "comune": "Roma",
        "area_geografica": "Centro",
        "territorio": "Metropolitano",
        "statale_paritaria": "Statale"
      },
      "pratica": {
        "categoria": "Metodologie Didattiche Innovative",
        "titolo": "Laboratorio di Robotica Educativa",
        "descrizione": "...",
        "metodologia": "...",
        "tipologie_metodologia": ["STEM/STEAM"],
        "ambiti_attivita": ["Orientamento"],
        "target": "Studenti",
        "citazione_ptof": "...",
        "pagina_evidenza": "Pagina 12"
      },
      "contesto": {
        "maturity_index": 4.6,
        "punteggi_dimensionali": {},
        "partnership_coinvolte": [],
        "attivita_correlate": []
      },
      "metadata": {}
    }
  ]
}
```

#### Catalogo attività - registry (data/activity_registry.json)
```json
{
  "version": "1.0",
  "last_updated": "2025-01-01T12:00:00",
  "processed_files": {
    "RMIS02400L": {
      "file_hash": "sha256:...",
      "processed_at": "2025-01-01T12:00:00",
      "practices_count": 12,
      "model_used": "qwen3:32b"
    }
  }
}
```

#### Anagrafica comuni (data/comuni_italiani.json)
```json
[
  {
    "nome": "Abano Terme",
    "codice": "028001",
    "zona": { "codice": "2", "nome": "Nord-est" },
    "regione": { "codice": "05", "nome": "Veneto" },
    "provincia": { "codice": "028", "nome": "Padova" },
    "sigla": "PD",
    "codiceCatastale": "A001",
    "cap": "35031",
    "popolazione": 0
  }
]
```

### JSON - Tabella

| JSON | Dove | Scopo | Chiavi principali |
|------|------|-------|------------------|
| analysis_results/{CODICE}_analysis.json | Output analisi PTOF | Risultati strutturati + report | metadata, ptof_section2, narrative |
| score_review_output.json (prompt) | Review punteggi | Correzioni punteggi estremi | score_updates[], review_notes |
| ollama_chunk_output.json (prompt) | Review report chunk | Arricchimenti e correzioni | enrichments[], corrections[], orientamento_* |
| activity_extraction_output.json (prompt) | Estrazione attività | Pratiche/attività estratte per chunk | pratiche[] |
| data/attivita.json | Dataset catalogo | Dataset attività estratte | version, last_updated, extraction_model, schools_processed, total_practices, practices[] |
| data/activity_registry.json | Registro estrazione | Stato e avanzamento | version, last_updated, processed_files{} |
| data/comuni_italiani.json | Anagrafica territori | Normalizzazione comuni/province/regioni | nome, codice, zona{}, regione{}, provincia{}, sigla, cap, popolazione |

#### Struttura pratica (tabellare)

| Campo | Descrizione |
|------|-------------|
| id | Identificativo pratica |
| school.* | Metadati scuola (codice, nome, tipo, area, territorio) |
| pratica.categoria | Categoria assegnata (6 macro categorie) |
| pratica.titolo | Titolo sintetico della pratica |
| pratica.descrizione | Descrizione dettagliata (200-500 caratteri) |
| pratica.metodologia | Metodologia descritta nel PTOF |
| pratica.tipologie_metodologia | Lista di tipologie metodologia |
| pratica.ambiti_attivita | Lista di ambiti di attivita |
| pratica.target | Destinatari della pratica |
| pratica.citazione_ptof | Citazione testuale dal PTOF |
| pratica.pagina_evidenza | Pagina evidenza (se presente) |
| contesto.* | Contesto (maturity_index, punteggi, partnership, attivita) |

#### Registro estrazione (tabellare)

| Campo | Descrizione |
|------|-------------|
| processed_files{codice}.file_hash | Hash file sorgente |
| processed_files{codice}.processed_at | Timestamp elaborazione |
| processed_files{codice}.practices_count | Numero pratiche estratte |
| processed_files{codice}.model_used | Modello usato in estrazione |

## Troubleshooting

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

Usa il pulsante "Aggiorna Dati" nella sidebar oppure:

```bash
python3 -c "from src.data.data_manager import update_index_safe; update_index_safe()"
```

### Porta 8501 gia in uso

```bash
streamlit run app/Home.py --server.port=8502
```

## Performance

Per migliorare le performance, installa Watchdog:

```bash
pip install watchdog
```

## Configurazione

La configurazione si trova in .streamlit/config.toml:

```toml
[theme]
base = "light"
```

## Supporto

Per problemi o domande:
1. Verifica questa guida
2. Consulta docs/operations/TROUBLESHOOTING.md
3. Controlla i log di Streamlit
