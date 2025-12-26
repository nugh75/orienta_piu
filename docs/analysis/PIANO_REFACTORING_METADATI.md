# Piano di Refactoring - Sistema Estrazione Metadati PTOF

## Obiettivo
Garantire che ogni JSON di analisi e il CSV della dashboard contengano metadati geografici corretti e completi:
- **provincia** (es. "Milano", "Roma", "Napoli")
- **regione** (es. "Lombardia", "Lazio", "Campania")
- **area_geografica** (es. "Nord Ovest", "Nord Est", "Centro", "Sud", "Isole")
- **territorio** ("Metropolitano" / "Non Metropolitano")

---

## Diagnosi Problemi Attuali

### Problema 1: Refiner sovrascrive i metadati arricchiti
**File:** `app/agentic_pipeline.py`
**Linee:** 462, 494-495

```
Flusso attuale (ERRATO):
1. LLM genera draft JSON (con metadati inventati/errati)
2. enrich_json_metadata() arricchisce con dati MIUR ✓
3. Refiner genera nuovo JSON → SOVRASCRIVE tutto! ✗
4. Metadati MIUR persi
```

### Problema 2: school_id nel JSON diverso dal nome file
**Esempio:** File `BNIS01100L_analysis.json` contiene `"school_id": "LEPC13000N"`
- L'LLM estrae un codice dal testo del PTOF (sbagliato)
- Il codice corretto è nel nome del file

### Problema 3: Funzione run_pipeline() duplicata
**File:** `app/agentic_pipeline.py`
**Linee:** 344-353 (incompleta) e 516-554 (completa ma sovrascritta)

### Problema 4: extract_canonical_code() duplicata in 4 file
- `app/agentic_pipeline.py:60-63`
- `src/processing/rebuild_csv_clean.py:42-47`
- `src/processing/rebuild_csv.py:83-93`
- `src/processing/enrich_json_metadata.py:27-30`

### Problema 5: Valori area_geografica inconsistenti
| Fonte | Valori usati |
|-------|--------------|
| SIGLA_PROVINCIA_MAP | "Nord Ovest", "Nord Est", "Centro", "Sud", "Isole" |
| comuni_database.py | "Nord", "Centro", "Sud e Isole" |
| CSV MIUR | "NORD OVEST", "NORD EST", "CENTRO", "SUD", "ISOLE" |

### Problema 6: Errori in region_map.json
- "BERNALDA": "Lombardia" (dovrebbe essere Basilicata)
- "TORRE ANNUNZIATA": "Calabria" (dovrebbe essere Campania)
- "TERNO D'ISOLA": "Calabria" (dovrebbe essere Lombardia)
- "CAVE": "Piemonte" (dovrebbe essere Lazio)

### Problema 7: Path hardcoded
```python
OLLAMA_URL = "http://192.168.129.14:11434/api/generate"
Path("/Users/danieledragoni/git/LIste/data/comuni_italiani.json")
```

---

## Architettura Target

```
┌─────────────────────────────────────────────────────────────────┐
│                    FLUSSO DATI CORRETTO                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  PDF (nome: BNIS01100L.pdf)                                     │
│       │                                                         │
│       ▼                                                         │
│  convert_pdfs_to_md.py → MD (nome: BNIS01100L.md)               │
│       │                                                         │
│       ▼                                                         │
│  agentic_pipeline.py                                            │
│       │                                                         │
│       ├─► Analyst Agent → draft JSON                            │
│       │                                                         │
│       ├─► Reviewer Agent → critique                             │
│       │                                                         │
│       ├─► Refiner Agent → refined JSON                          │
│       │                                                         │
│       └─► enrich_json_metadata() ◄── SPOSTATO QUI (DOPO Refiner)│
│               │                                                 │
│               ├── SchoolDatabase (CSV MIUR)                     │
│               ├── SIGLA_PROVINCIA_MAP (fallback geografico)     │
│               └── PROVINCE_METROPOLITANE (territorio)           │
│       │                                                         │
│       ▼                                                         │
│  JSON finale (analysis_results/BNIS01100L_analysis.json)        │
│       │                                                         │
│       ▼                                                         │
│  rebuild_csv_clean.py → CSV (data/analysis_summary.csv)         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Piano di Implementazione

### FASE 1: Creazione Modulo Costanti Centralizzato
**File da creare:** `src/utils/constants.py`
**Tempo stimato:** 30 min

```python
# Contenuto:
# - SIGLA_PROVINCIA_MAP (completa, 110 province)
# - PROVINCE_METROPOLITANE (14 città metropolitane ISTAT)
# - AREA_GEOGRAFICA_VALUES = ["Nord Ovest", "Nord Est", "Centro", "Sud", "Isole"]
# - TERRITORIO_VALUES = ["Metropolitano", "Non Metropolitano"]
# - Funzioni helper: get_territorio(), get_area_geografica(), normalize_area_geografica()
```

**Task:**
- [ ] 1.1 Creare file `src/utils/constants.py`
- [ ] 1.2 Definire SIGLA_PROVINCIA_MAP completa (copiare da agentic_pipeline.py e verificare)
- [ ] 1.3 Definire PROVINCE_METROPOLITANE come set
- [ ] 1.4 Creare funzione `get_territorio(provincia: str) -> str`
- [ ] 1.5 Creare funzione `normalize_area_geografica(area: str) -> str`
- [ ] 1.6 Creare funzione `get_geo_from_sigla(school_code: str) -> dict`

---

### FASE 2: Creazione Modulo Parser Codici Scuola
**File da creare:** `src/utils/school_code_parser.py`
**Tempo stimato:** 15 min

```python
# Contenuto:
# - extract_canonical_code(filename: str) -> str
# - validate_school_code(code: str) -> bool
# - get_provincia_sigla(school_code: str) -> str
```

**Task:**
- [ ] 2.1 Creare file `src/utils/school_code_parser.py`
- [ ] 2.2 Spostare `extract_canonical_code()` qui
- [ ] 2.3 Aggiungere `validate_school_code()` con regex
- [ ] 2.4 Aggiungere `get_provincia_sigla()` (prime 2 lettere)

---

### FASE 3: Fix agentic_pipeline.py
**File:** `app/agentic_pipeline.py`
**Tempo stimato:** 45 min

**Task:**
- [ ] 3.1 Rimuovere prima definizione `run_pipeline()` (linee 344-353)
- [ ] 3.2 Rimuovere `SIGLA_PROVINCIA_MAP` locale (usare da constants.py)
- [ ] 3.3 Rimuovere `extract_canonical_code()` locale (usare da school_code_parser.py)
- [ ] 3.4 **CRITICO:** Spostare chiamata `enrich_json_metadata()` DOPO il Refiner
- [ ] 3.5 Modificare `enrich_json_metadata()` per forzare school_id dal nome file
- [ ] 3.6 Aggiungere import da `src.utils.constants` e `src.utils.school_code_parser`

**Codice da modificare (linee 484-504):**
```python
# PRIMA (errato):
enrich_json_metadata(final_json_path, school_Code)  # Linea 462
# ... Refiner sovrascrive ...

# DOPO (corretto):
# ... Refiner completa ...
# Alla fine, DOPO il Refiner:
enrich_json_metadata(final_json_path, school_Code, force_school_id=True)
```

---

### FASE 4: Refactoring enrich_json_metadata()
**File:** `app/agentic_pipeline.py` (funzione interna)
**Tempo stimato:** 30 min

**Task:**
- [ ] 4.1 Aggiungere parametro `force_school_id=False`
- [ ] 4.2 Se `force_school_id=True`, sovrascrivere SEMPRE school_id con valore dal nome file
- [ ] 4.3 Usare priorità corretta per ogni campo:
  ```
  school_id:       SEMPRE dal nome file
  denominazione:   SchoolDB > LLM > "ND"
  comune:          SchoolDB > LLM > "ND"
  provincia:       SchoolDB > SIGLA_MAP > "ND"
  regione:         SchoolDB > SIGLA_MAP > "ND"
  area_geografica: SchoolDB > SIGLA_MAP > "ND"
  territorio:      Calcolato da provincia (PROVINCE_METROPOLITANE)
  ```
- [ ] 4.4 Loggare quale fonte è stata usata per ogni campo

---

### FASE 5: Aggiornare rebuild_csv_clean.py
**File:** `src/processing/rebuild_csv_clean.py`
**Tempo stimato:** 20 min

**Task:**
- [ ] 5.1 Rimuovere `extract_canonical_code()` locale
- [ ] 5.2 Importare da `src.utils.school_code_parser`
- [ ] 5.3 Aggiungere validazione che school_id nel JSON corrisponda al nome file
- [ ] 5.4 Se mismatch, usare nome file e loggare warning

---

### FASE 6: Fix region_map.json
**File:** `config/region_map.json`
**Tempo stimato:** 15 min

**Task:**
- [ ] 6.1 Correggere "BERNALDA": "Basilicata"
- [ ] 6.2 Correggere "TORRE ANNUNZIATA": "Campania"
- [ ] 6.3 Correggere "TERNO D'ISOLA": "Lombardia"
- [ ] 6.4 Correggere "CAVE": "Lazio"
- [ ] 6.5 Verificare altri comuni sospetti

---

### FASE 7: Centralizzare Configurazione
**File da creare:** `config/settings.py`
**Tempo stimato:** 20 min

**Task:**
- [ ] 7.1 Creare `config/settings.py`
- [ ] 7.2 Spostare tutti i path in variabili con fallback da `os.environ`
- [ ] 7.3 Spostare OLLAMA_URL in settings
- [ ] 7.4 Aggiornare import in tutti i file che usano path hardcoded

---

### FASE 8: Script di Re-Enrichment JSON Esistenti
**File da creare/modificare:** `src/processing/reenrich_all_json.py`
**Tempo stimato:** 20 min

**Task:**
- [ ] 8.1 Creare script che ri-arricchisce TUTTI i JSON esistenti
- [ ] 8.2 Usare nuova logica di `enrich_json_metadata()`
- [ ] 8.3 Forzare school_id dal nome file
- [ ] 8.4 Rigenerare CSV dopo re-enrichment

---

### FASE 9: Test e Validazione
**Tempo stimato:** 30 min

**Task:**
- [ ] 9.1 Testare con un nuovo PDF (workflow completo)
- [ ] 9.2 Verificare JSON generato ha metadati corretti
- [ ] 9.3 Verificare CSV ha tutti i campi compilati
- [ ] 9.4 Verificare che BNIS01100L abbia:
  - school_id: "BNIS01100L"
  - provincia: "Benevento"
  - regione: "Campania"
  - area_geografica: "Sud"
  - territorio: "Non Metropolitano"

---

## Riepilogo File da Modificare

| File | Azione | Priorità |
|------|--------|----------|
| `src/utils/constants.py` | CREARE | Alta |
| `src/utils/school_code_parser.py` | CREARE | Alta |
| `app/agentic_pipeline.py` | MODIFICARE | Critica |
| `src/processing/rebuild_csv_clean.py` | MODIFICARE | Media |
| `config/region_map.json` | CORREGGERE | Media |
| `config/settings.py` | CREARE | Bassa |
| `src/processing/reenrich_all_json.py` | CREARE | Media |

---

## Tempo Totale Stimato

| Fase | Tempo |
|------|-------|
| Fase 1: Costanti | 30 min |
| Fase 2: Parser | 15 min |
| Fase 3: Pipeline fix | 45 min |
| Fase 4: Enrich refactor | 30 min |
| Fase 5: CSV rebuild | 20 min |
| Fase 6: region_map fix | 15 min |
| Fase 7: Settings | 20 min |
| Fase 8: Re-enrichment | 20 min |
| Fase 9: Test | 30 min |
| **TOTALE** | **~4 ore** |

---

## Valori di Riferimento

### Province Metropolitane (ISTAT)
```
Roma, Milano, Napoli, Torino, Bari, Firenze, Bologna,
Genova, Venezia, Palermo, Catania, Messina, Reggio Calabria, Cagliari
```

### Area Geografica (valori standard)
```
Nord Ovest: Piemonte, Valle d'Aosta, Lombardia, Liguria
Nord Est:   Veneto, Friuli-Venezia Giulia, Trentino-Alto Adige, Emilia-Romagna
Centro:     Toscana, Umbria, Marche, Lazio
Sud:        Abruzzo, Molise, Campania, Puglia, Basilicata, Calabria
Isole:      Sicilia, Sardegna
```

### Mapping Sigla Provincia → Dati Geografici
```
Sigla = prime 2 lettere del codice meccanografico
Esempio: BNIS01100L → BN → Benevento → Campania → Sud → Non Metropolitano
```

---

## Checklist Pre-Implementazione

- [ ] Backup di tutti i file da modificare
- [ ] Verificare che tutti i JSON esistenti siano salvati
- [ ] Verificare accesso a CSV MIUR (SCUANAGRAFESTAT*.csv, SCUANAGRAFEPAR*.csv)
- [ ] Verificare che Ollama sia raggiungibile (per test pipeline)

---

## Note Importanti

1. **NON modificare i JSON manualmente** - usare sempre gli script
2. **Il CSV è DERIVATO dai JSON** - modificare prima i JSON, poi rigenerare CSV
3. **Il school_id DEVE corrispondere al nome file** - è la chiave primaria
4. **SIGLA_PROVINCIA_MAP è il fallback definitivo** - garantisce sempre un valore geografico
