# 📥 PTOF Downloader

Script per il download automatico dei PTOF (Piani Triennali dell'Offerta Formativa) dalle anagrafiche MIUR con **campionamento stratificato** per garantire rappresentatività del campione.

## 🎯 Obiettivo

Scaricare PTOF autentici evitando falsi positivi, rispettando la stratificazione dei dati di origine:

- **Tipo scuola**: Statale vs Paritaria
- **Area geografica**: NORD OVEST, NORD EST, CENTRO, SUD, ISOLE
- **Tipo provincia**: Metropolitana vs Non metropolitana
- **Grado istruzione**: Infanzia, Primaria, Sec. Primo Grado, Sec. Secondo Grado

## 📂 Sorgenti Dati

| File | Descrizione | Records |
|------|-------------|---------|
| `SCUANAGRAFESTAT20252620250901.csv` | Scuole statali | ~50.000 |
| `SCUANAGRAFEPAR20252620250901.csv` | Scuole paritarie | ~11.000 |

## 🏙️ Province Metropolitane

Le 14 Città Metropolitane italiane:
- **Nord**: Milano, Torino, Genova, Venezia, Bologna
- **Centro**: Firenze, Roma
- **Sud**: Napoli, Bari, Reggio Calabria
- **Isole**: Palermo, Catania, Messina, Cagliari

## 🔒 Validazione Anti-Falsi Positivi

Lo script implementa una validazione rigorosa per assicurarsi che i PDF scaricati siano effettivamente PTOF:

1. **Verifica header PDF**: Controllo che il file inizi con `%PDF`
2. **Controllo dimensione**: 
   - Minimo 50KB (PTOF reali sono più grandi)
   - Massimo 100MB (limite ragionevole)
3. **Analisi contenuto**: Estrazione testo e ricerca keyword PTOF:
   - `ptof`, `piano triennale`, `offerta formativa`
   - `curricolo`, `competenze`, `valutazione`
   - `inclusione`, `orientamento`, `ampliamento`
4. **Score di validazione**: Solo PDF con score ≥ 0.4 vengono accettati

## 🚀 Utilizzo

### Installazione dipendenze

```bash
pip install requests pypdf  # oppure PyMuPDF per fitz
```

### Esempi di utilizzo

```bash
# Mostra stratificazione senza scaricare (dry run)
python src/downloaders/ptof_downloader.py --tutte --dry-run

# Scarica tutte le scuole statali del Lazio
python src/downloaders/ptof_downloader.py --statali --regioni LAZIO

# Campione stratificato: 5 scuole per ogni strato
python src/downloaders/ptof_downloader.py --tutte --sample-per-strato 5

# Campione proporzionale di 500 scuole totali
python src/downloaders/ptof_downloader.py --tutte --sample-total 500

# Solo licei delle province metropolitane
python src/downloaders/ptof_downloader.py --statali --gradi SEC_SECONDO --solo-metropolitane

# Solo scuole primarie NON metropolitane del Sud
python src/downloaders/ptof_downloader.py --statali --gradi PRIMARIA --solo-non-metropolitane --aree SUD

# Scuole paritarie di Milano e Roma
python src/downloaders/ptof_downloader.py --paritarie --province MILANO ROMA

# Reset dello stato e ricomincia
python src/downloaders/ptof_downloader.py --statali --reset
```

## 📊 Opzioni CLI

### Tipo scuole (obbligatorio, mutualmente esclusivi)

| Flag | Descrizione |
|------|-------------|
| `--statali` | Solo scuole statali |
| `--paritarie` | Solo scuole paritarie |
| `--tutte` | Entrambe |

### Filtri geografici

| Flag | Descrizione | Esempio |
|------|-------------|---------|
| `--regioni` | Filtra per regioni | `--regioni LAZIO LOMBARDIA` |
| `--province` | Filtra per province | `--province ROMA MILANO` |
| `--aree` | Filtra per aree geografiche | `--aree SUD ISOLE` |

### Filtri metropolitane

| Flag | Descrizione |
|------|-------------|
| `--solo-metropolitane` | Solo province metropolitane (14 città) |
| `--solo-non-metropolitane` | Solo province NON metropolitane |

### Filtri grado istruzione

| Flag | Valori | Descrizione |
|------|--------|-------------|
| `--gradi` | `INFANZIA`, `PRIMARIA`, `SEC_PRIMO`, `SEC_SECONDO`, `ALTRO` | Filtra per grado |

### Campionamento

| Flag | Descrizione |
|------|-------------|
| `--sample-per-strato N` | Estrae N scuole da ogni strato |
| `--sample-total N` | Estrae N scuole totali proporzionalmente |
| `--max N` | Limite massimo assoluto |
| `--seed N` | Seed per riproducibilità (default: 42) |

### Altre opzioni

| Flag | Descrizione |
|------|-------------|
| `--reset` | Cancella lo stato e ricomincia da zero |
| `--dry-run` | Mostra stratificazione senza scaricare |

## 📁 Output

### Directory

| Path | Descrizione |
|------|-------------|
| `ptof_inbox/` | PDF scaricati e validati |
| `logs/` | Log dettagliati delle sessioni |
| `data/download_state.json` | Stato persistente (per resume) |

### Naming convention

I file scaricati seguono la convenzione:
```
{CODICE_MECCANOGRAFICO}_PTOF.pdf
```

Esempio: `RMIS00100X_PTOF.pdf`

## 🔄 Strategie di Download

Lo script prova diverse strategie in ordine di priorità:

1. **Scuola In Chiaro - Pagina PTOF**
   ```
   https://cercalatuascuola.istruzione.it/cercalatuascuola/istituti/{codice}/ptof/
   ```

2. **Scuola In Chiaro - Pagina Documenti**
   ```
   https://cercalatuascuola.istruzione.it/cercalatuascuola/istituti/{codice}/documenti/
   ```

3. **Sito web della scuola** (se disponibile)
   - Cerca link con keyword PTOF nella homepage
   - Prova percorsi comuni: `/ptof`, `/didattica/ptof`, `/documenti/ptof`, etc.

4. **Istituto di riferimento** (solo scuole statali)
   - Per i plessi, cerca il PTOF dell'istituto comprensivo

## 📈 Stato e Resume

Lo script salva automaticamente lo stato in `data/download_state.json`:

```json
{
  "downloaded": {
    "RMIS00100X": {
      "path": "ptof_inbox/RMIS00100X_PTOF.pdf",
      "source": "scuola_in_chiaro",
      "strato": "STAT_CENTRO_METRO_SEC_SECONDO",
      "size": 2456789,
      "timestamp": "2024-12-23T10:30:00"
    }
  },
  "failed": {},
  "rejected": {},
  "stats_per_strato": {}
}
```

Questo permette di:
- **Riprendere** download interrotti
- **Evitare** di riscaricare file già presenti
- **Tracciare** statistiche per strato

## 🧪 Esempio di Stratificazione

Eseguendo `--dry-run` si ottiene un riepilogo come:

```
======================================================================
📊 RIEPILOGO STRATIFICAZIONE
======================================================================

📌 Per tipo scuola:
   PAR: 11507
   STAT: 50350

📌 Per area geografica:
   CENTRO: 12456
   ISOLE: 8923
   NORD EST: 11234
   NORD OVEST: 15678
   SUD: 13566

📌 Per tipo provincia:
   Metropolitane: 28456
   Non metropolitane: 33401

📌 Per grado istruzione:
   ALTRO: 1234
   INFANZIA: 18567
   PRIMARIA: 16789
   SEC_PRIMO: 8234
   SEC_SECONDO: 17033

📌 Totale strati: 80
📌 Totale scuole: 61857
======================================================================
```

## ⚠️ Note

- **Rate limiting**: Lo script attende 1 secondo tra le richieste per evitare blocchi
- **Timeout**: 30 secondi per richiesta
- **SSL**: Verifiche SSL disabilitate per alcuni siti scolastici con certificati non validi
- **Dimensione minima**: 50KB (esclude placeholder e documenti vuoti)

## 🔗 Integrazione con il Workflow

Dopo il download, i PTOF in `ptof_inbox/` possono essere processati dal workflow principale:

```bash
# Analizza i PTOF scaricati
make run

# Oppure esegui il notebook CLI_Examples.ipynb
```
