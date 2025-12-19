import streamlit as st

st.set_page_config(page_title="Metodologia", layout="wide")
st.title("📐 Metodologia di Analisi")

st.markdown("""
Questa pagina descrive come vengono costruiti gli indici e i punteggi mostrati nella dashboard.

---

## 🔄 Processo di Analisi

L'analisi di ogni PTOF segue queste fasi:

```mermaid
graph LR
    A[PDF PTOF] --> B[Estrazione Testo]
    B --> C[Divisione in Chunk]
    C --> D[Analisi per Chunk]
    D --> E[Aggregazione Evidenze]
    E --> F[Analisi Finale]
    F --> G[JSON + Report]
```

### 1. Estrazione e Chunking
- Il PDF viene letto e convertito in testo
- Il testo viene diviso in **chunk da 8.000 caratteri**
- Ogni chunk mantiene il riferimento alla pagina originale

### 2. Analisi per Chunk
Per ogni chunk, il modello AI identifica:
- **Categoria** (Finalità, Obiettivi, Partnership, ecc.)
- **Evidenza testuale** (citazione dal documento)
- **Pagina di riferimento**
- **Punteggio preliminare** (1-7)

### 3. Aggregazione Finale
Le evidenze di tutti i chunk vengono combinate per produrre:
- Un **JSON strutturato** con tutti i punteggi
- Un **report narrativo** di 800-1200 parole

---

## 📊 Costruzione degli Indici

### Punteggi Singoli (1-7)
Ogni dimensione riceve un punteggio basato sulla **qualità e completezza** delle evidenze trovate:

| Punteggio | Criterio |
|:---------:|:---------|
| **1** | Nessun riferimento trovato nel documento |
| **2** | Menzionato genericamente senza dettagli |
| **3** | Accenni indiretti o frammentari |
| **4** | Descritto con alcune azioni concrete |
| **5** | Ben descritto con strumenti specifici |
| **6** | Strutturato con responsabilità chiare |
| **7** | Sistema integrato, monitorato e innovativo |

---

### Indici Aggregati (Medie)

Gli indici sintetici sono calcolati come **media aritmetica** dei punteggi delle sottodimensioni:

#### Media Finalità
```
mean_finalita = (
    finalita_attitudini + 
    finalita_interessi + 
    finalita_progetto_vita + 
    finalita_transizioni_formative + 
    finalita_capacita_orientative
) / 5
```

#### Media Obiettivi
```
mean_obiettivi = (
    obiettivo_ridurre_abbandono + 
    obiettivo_continuita_territorio + 
    obiettivo_contrastare_neet + 
    obiettivo_lifelong_learning
) / 4
```

#### Media Governance
```
mean_governance = (
    azione_coordinamento_servizi + 
    azione_dialogo_docenti_studenti + 
    azione_rapporto_scuola_genitori + 
    azione_monitoraggio_azioni + 
    azione_sistema_integrato_inclusione
) / 5
```

#### Media Didattica Orientativa
```
mean_didattica = (
    didattica_da_esperienza + 
    didattica_laboratoriale + 
    didattica_flessibilita_spazi_tempi + 
    didattica_interdisciplinare
) / 4
```

#### Media Opportunità
```
mean_opportunita = (
    opzionali_culturali + 
    opzionali_laboratoriali + 
    opzionali_ludiche + 
    opzionali_volontariato + 
    opzionali_sportive
) / 5
```

---

### Indice di Maturità Globale

L'**Indice di Maturità Orientamento** è la media delle medie:

```
ptof_orientamento_maturity_index = (
    mean_finalita + 
    mean_obiettivi + 
    mean_governance + 
    mean_didattica + 
    mean_opportunita
) / 5
```

---

## 📋 Conteggi

### Partnership Count (0-11)
Conta quante tipologie di partner sono attive:
- Interni, Scuole Primarie, Licei, Tecnici, Professionali
- IeFP, Università, Aziende, Enti Pubblici, Terzo Settore, Altro

### Activities Count
Numero totale di attività specifiche censite nel documento.

---

## ⚠️ Limitazioni

- L'analisi dipende dalla **qualità del testo estratto** dal PDF
- Documenti mal formattati possono produrre risultati incompleti
- Il modello AI può occasionalmente interpretare erroneamente il contesto
- I punteggi riflettono **cosa è scritto nel PTOF**, non necessariamente cosa viene effettivamente realizzato
""")
