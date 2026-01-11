# Piano di Correzione: Prompt e Pipeline Meta Report

**Data**: 2026-01-11
**Versione**: 1.1
**Stato**: ✅ IMPLEMENTATO (tutte le 12 fasi completate)

---

## Executive Summary

Questo documento definisce un piano strutturato per migliorare la qualità, consistenza e manutenibilità della pipeline di generazione dei meta report. Il piano si articola in **4 fasi** con una durata stimata di implementazione progressiva.

---

## Fase 1: Quick Wins (Priorità Critica)

### 1.1 Validazione Post-Generazione dei Codici Scuola

**Problema**: L'LLM può "allucinare" codici meccanografici inesistenti.

**Soluzione**: Aggiungere un validatore post-generazione in `base.py`.

**File da modificare**: `src/agents/meta_report/providers/base.py`

```python
# Aggiungere dopo generate_best_practices()
def validate_school_codes(self, content: str, valid_codes: set[str]) -> tuple[str, list[str]]:
    """Valida e segnala codici meccanografici non validi nel report."""
    import re
    # Pattern: 2 lettere + 2 lettere + 5-6 caratteri alfanumerici
    pattern = r'\b([A-Z]{2}[A-Z]{2}[A-Z0-9]{5,6})\b'
    found_codes = set(re.findall(pattern, content))

    invalid = [code for code in found_codes if code not in valid_codes]

    if invalid:
        # Rimuovi o segnala i codici invalidi
        for code in invalid:
            content = content.replace(code, f"[CODICE NON VALIDO: {code}]")

    return content, invalid
```

**Effort**: 2 ore
**Impatto**: Elimina allucinazioni sui codici

---

### 1.2 Caching dei Risultati Intermedi per Thematic Report

**Problema**: Se la generazione fallisce a metà, si perde tutto il lavoro.

**Soluzione**: Implementare checkpoint per i chunk.

**File da modificare**: `src/agents/meta_report/reporters/thematic.py`

```python
# In _generate_theme_summary(), prima del loop sui chunk:
cache_file = self.base_dir / ".cache" / f"thematic_{dimension}_{theme}_chunks.json"
cache_file.parent.mkdir(exist_ok=True)

cached_notes = {}
if cache_file.exists():
    cached_notes = json.loads(cache_file.read_text())

for idx, chunk in enumerate(chunks, 1):
    cache_key = f"chunk_{idx}"
    if cache_key in cached_notes:
        chunk_notes.append(cached_notes[cache_key])
        continue

    # ... genera chunk ...
    chunk_notes.append(chunk_response.content)

    # Salva checkpoint
    cached_notes[cache_key] = chunk_response.content
    cache_file.write_text(json.dumps(cached_notes, ensure_ascii=False))

# Pulisci cache a fine generazione
cache_file.unlink(missing_ok=True)
```

**Effort**: 3 ore
**Impatto**: Resilienza e risparmio costi API

---

### 1.3 Correzione Istruzioni Contraddittorie nei Prompt

**Problema**: Alcuni prompt chiedono "NO titoli Markdown" ma anche "struttura obbligatoria con sezioni".

**Soluzione**: Chiarire le istruzioni per contesto.

**File da modificare**: `src/agents/meta_report/providers/base.py`

**Cambiamenti**:

| Report Type | Titoli Permessi | Note |
|-------------|-----------------|------|
| `thematic_group_chunk` | NO | Output parziale, verrà integrato |
| `thematic_group_merge` | SI (###, ####) | Report finale completo |
| `thematic_summary_merge` | NO | Sintesi discorsiva |
| `school`, `regional`, `national` | SI (#, ##, ###) | Report standalone |

**Effort**: 1 ora
**Impatto**: Output più consistente

---

## Fase 2: Miglioramento Qualità Prompt (Priorità Alta)

### 2.1 Aggiungere Few-Shot Examples ai System Prompt

**Problema**: I modelli devono "indovinare" il formato output.

**Soluzione**: Creare un modulo dedicato con esempi per ogni tipo di report.

**Nuovo file**: `src/agents/meta_report/prompts/examples.py`

```python
"""Few-shot examples for meta report prompts."""

EXAMPLES = {
    "school": {
        "good": """
## Contesto
L'**IIS Leonardo da Vinci** (RMIS09400V) è un istituto tecnico situato nel
territorio metropolitano di Roma. Con un'offerta formativa che spazia
dall'indirizzo informatico a quello meccanico, la scuola serve un bacino
d'utenza eterogeneo.

## Punti di Forza
L'istituto si distingue per un sistema di **PCTO strutturato** che coinvolge
oltre 40 aziende partner, tra cui **Accenture** e **Engineering SpA**.
Il percorso "Impresa Formativa Simulata" permette agli studenti di...
""",
        "bad": """
❌ EVITARE:
- Elenchi puntati lunghi senza contesto narrativo
- Codici inventati (es. XXXX99999Z)
- Frasi come "La scuola eccelle in tutto"
- Blocchi di codice ```
"""
    },

    "thematic": {
        "good": """
### PCTO e Partnership Aziendali

L'analisi delle 127 scuole campione evidenzia tre approcci prevalenti
nell'organizzazione dei PCTO. Il primo modello, adottato dal **Liceo Galilei**
(RMPS12000X) e dall'**IIS Marconi** (TOPS01000B), integra percorsi in azienda
con moduli di preparazione in aula. Particolarmente efficace risulta
l'esperienza del **Polo Tecnico Fermi** (NAIS00700R) che ha sviluppato un
sistema di matching studente-azienda basato sulle competenze trasversali.

Il secondo approccio privilegia le collaborazioni con il terzo settore...
""",
        "bad": """
❌ EVITARE:
- "Molte scuole fanno PCTO" (troppo generico)
- Citare scuole senza codice
- Creare cluster con nomi delle categorie amministrative
"""
    },

    "regional": {
        "good": """
## Panorama Regionale: Lombardia

La Lombardia presenta un tessuto scolastico articolato con 342 istituti
secondari di II grado analizzati. La distribuzione territoriale evidenzia
una concentrazione del 45% nell'area metropolitana milanese, seguita da
Brescia (18%) e Bergamo (12%).

### Confronto tra Province

**Milano** si distingue per l'intensità delle partnership con il settore
terziario: il **Liceo Berchet** (MIPC01000C) collabora stabilmente con
Bocconi e Politecnico, mentre l'**IIS Lagrange** (MIIS02300X) ha
formalizzato accordi con 15 studi professionali.

**Brescia** eccelle invece nei percorsi tecnico-industriali. L'**ITI Castelli**
(BSIS00300C) ha sviluppato il progetto "Fabbrica 4.0" con Beretta e Iveco...
""",
    }
}

def get_example(report_type: str, example_type: str = "good") -> str:
    """Restituisce esempio per il tipo di report."""
    return EXAMPLES.get(report_type, {}).get(example_type, "")
```

**Integrazione in base.py**:

```python
from .prompts.examples import get_example

def _get_system_prompt(self, report_type: str, prompt_profile: str) -> str:
    # ... codice esistente ...

    example = get_example(report_type)
    if example:
        specifics[report_type] += f"\n\nESEMPIO DI OUTPUT CORRETTO:\n{example}"

    return f"{base}\n\n{specifics.get(report_type, specifics['school'])}"
```

**Effort**: 4 ore
**Impatto**: Output più consistenti e di qualità

---

### 2.2 Potenziare i Prompt Profile

**Problema**: I profili (innovative, comparative, etc.) hanno effetto minimo.

**Soluzione**: Rendere i profili più prescrittivi con sezioni dedicate.

**Modifica in base.py** - `_format_analysis_prompt()`:

```python
PROFILE_STRUCTURES = {
    "overview": {
        "sections": ["Sintesi", "Analisi", "Conclusioni"],
        "focus": "bilanciato",
        "word_count": "800-1200 parole"
    },
    "innovative": {
        "sections": ["Innovazioni Chiave", "Analisi Critica", "Scalabilità"],
        "focus": "solo pratiche originali",
        "word_count": "600-900 parole",
        "required_elements": [
            "Almeno 3 pratiche innovative con spiegazione del perché sono innovative",
            "Confronto con prassi standard",
            "Valutazione replicabilità"
        ]
    },
    "comparative": {
        "sections": ["Matrice Comparativa", "Pattern Territoriali", "Gap Analysis"],
        "focus": "differenze e cluster",
        "word_count": "900-1300 parole",
        "required_elements": [
            "Almeno 1 tabella comparativa",
            "Dati quantitativi per ogni confronto",
            "Identificazione outlier"
        ]
    },
    "impact": {
        "sections": ["Evidenze di Impatto", "Analisi Costi-Benefici", "Sostenibilità"],
        "focus": "risultati misurabili",
        "word_count": "700-1000 parole",
        "required_elements": [
            "KPI o metriche citate dal PTOF",
            "Valutazione risorse impiegate",
            "Prospettive di continuità"
        ]
    },
    "operational": {
        "sections": ["Quick Wins", "Azioni a Medio Termine", "Roadmap"],
        "focus": "raccomandazioni attuabili",
        "word_count": "600-900 parole",
        "required_elements": [
            "Almeno 5 raccomandazioni concrete",
            "Prerequisiti per ogni azione",
            "Prioritizzazione per impatto/effort"
        ]
    }
}
```

**Effort**: 3 ore
**Impatto**: Report differenziati per pubblico target

---

### 2.3 Modularizzazione Prompt Comuni

**Problema**: Regole ripetute 6+ volte in diversi prompt.

**Soluzione**: Creare un sistema di composizione modulare.

**Nuovo file**: `src/agents/meta_report/prompts/components.py`

```python
"""Modular prompt components for meta reports."""

# Regole comuni a tutti i report
COMMON_RULES = """
REGOLE GENERALI:
- Scrivi in italiano accademico, registro formale
- Evita toni celebrativi e superlativi
- NON usare blocchi di codice (```)
- NON usare emoji
"""

CITATION_RULES = """
REGOLE CITAZIONI:
- Cita SOLO scuole presenti nei dati forniti
- Usa SEMPRE il formato: Nome Scuola (CODICE)
- Esempio: Liceo Galilei (RMPS12345X)
- NON inventare codici meccanografici
- Se non hai il codice, non citare la scuola
"""

NARRATIVE_STYLE = """
STILE NARRATIVO:
- Scrivi in prosa fluida e discorsiva
- Evita elenchi puntati lunghi (max 3-4 elementi)
- Usa connettivi logici (inoltre, tuttavia, in particolare)
- Metti in **grassetto** nomi di scuole, partner, progetti chiave
"""

NO_MARKDOWN_HEADERS = """
FORMATO OUTPUT (chunk parziale):
- NON usare titoli Markdown (#, ##, ###)
- NON usare righe in grassetto che fungono da titoli
- Scrivi paragrafi continui
"""

WITH_MARKDOWN_HEADERS = """
FORMATO OUTPUT (report completo):
- Usa titoli Markdown per le sezioni principali
- # per il titolo principale
- ## per sezioni maggiori
- ### per sottosezioni
"""

def compose_system_prompt(*components: str) -> str:
    """Compone un system prompt da componenti modulari."""
    return "\n\n".join(components)
```

**Refactoring in base.py**:

```python
from .prompts.components import (
    COMMON_RULES, CITATION_RULES, NARRATIVE_STYLE,
    NO_MARKDOWN_HEADERS, WITH_MARKDOWN_HEADERS, compose_system_prompt
)

def _get_system_prompt(self, report_type: str, prompt_profile: str) -> str:
    role = "Sei un esperto di orientamento scolastico italiano."

    # Componenti comuni
    base_components = [role, COMMON_RULES, CITATION_RULES, NARRATIVE_STYLE]

    # Componenti specifici per tipo
    if report_type in ("thematic_chunk", "thematic_group_chunk", "thematic_summary_merge"):
        base_components.append(NO_MARKDOWN_HEADERS)
    else:
        base_components.append(WITH_MARKDOWN_HEADERS)

    # Istruzioni specifiche
    specific = self._get_specific_instructions(report_type)
    base_components.append(specific)

    return compose_system_prompt(*base_components)
```

**Effort**: 4 ore
**Impatto**: Manutenibilità e consistenza

---

## Fase 3: Ottimizzazione Pipeline (Priorità Media)

### 3.1 Chunking Semantico per Report Tematici

**Problema**: Il chunking numerico (ogni 30 casi) può spezzare cluster tematici.

**Soluzione**: Raggruppare prima per regione/tipo, poi chunckare.

**File da modificare**: `src/agents/meta_report/reporters/thematic.py`

```python
def _semantic_chunk_cases(
    self,
    cases: list[dict],
    chunk_size: int = 30,
    strategy: str = "region"  # o "tipo_scuola", "mixed"
) -> list[list[dict]]:
    """Chunking semantico che preserva cluster significativi."""

    if strategy == "region":
        # Raggruppa per regione
        by_region = defaultdict(list)
        for case in cases:
            region = case.get("scuola", {}).get("regione", "Altro")
            by_region[region].append(case)

        chunks = []
        current_chunk = []

        for region in sorted(by_region.keys()):
            region_cases = by_region[region]

            # Se la regione intera sta nel chunk corrente, aggiungila
            if len(current_chunk) + len(region_cases) <= chunk_size:
                current_chunk.extend(region_cases)
            else:
                # Chiudi chunk corrente se non vuoto
                if current_chunk:
                    chunks.append(current_chunk)

                # Se la regione è troppo grande, spezzala
                if len(region_cases) > chunk_size:
                    for i in range(0, len(region_cases), chunk_size):
                        chunks.append(region_cases[i:i+chunk_size])
                    current_chunk = []
                else:
                    current_chunk = region_cases

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    # Fallback a chunking numerico
    return self._chunk_cases(cases, chunk_size)
```

**Effort**: 4 ore
**Impatto**: Migliore qualità analisi territoriale

---

### 3.2 Contesto Cumulativo tra Chunk

**Problema**: Ogni chunk viene analizzato senza sapere cosa è emerso prima.

**Soluzione**: Passare un riassunto dei pattern già identificati.

**Modifica in thematic.py** - `_generate_theme_summary()`:

```python
def _generate_theme_summary(self, ...):
    # ...
    if use_chunking:
        chunks = self._semantic_chunk_cases(cases, chunk_size)
        chunk_notes = []
        cumulative_patterns = []  # NUOVO: pattern cumulativi

        for idx, chunk in enumerate(chunks, 1):
            chunk_summary = self._summarize_cases(chunk, disable_sampling=True)
            chunk_data = {
                "dimension": dimension,
                "dimension_name": dimension_name,
                "theme": theme,
                "chunk_index": idx,
                "chunk_total": len(chunks),
                # NUOVO: contesto dei chunk precedenti
                "previous_patterns": cumulative_patterns[-3:] if cumulative_patterns else [],
                "instruction": "Evita di ripetere pattern già identificati. Cerca elementi nuovi.",
                **chunk_summary,
            }

            chunk_response = self.provider.generate_best_practices(
                chunk_data,
                "thematic_group_chunk",
                prompt_profile=prompt_profile
            )

            chunk_notes.append(chunk_response.content)

            # NUOVO: estrai pattern da questo chunk
            # (semplificato - in produzione usare LLM o regex)
            new_patterns = self._extract_patterns(chunk_response.content)
            cumulative_patterns.extend(new_patterns)
```

**Effort**: 5 ore
**Impatto**: Riduzione ridondanze, analisi più ricca

---

### 3.3 Sampling Stratificato

**Problema**: Il sampling 1:5 può perdere rappresentatività geografica.

**Soluzione**: Garantire almeno N casi per regione.

**Modifica in thematic.py**:

```python
def _stratified_sample(
    self,
    cases: list[dict],
    min_per_stratum: int = 2,
    max_total: int = 80,
    stratify_by: str = "regione"
) -> list[dict]:
    """Campionamento stratificato con minimo garantito per strato."""

    # Raggruppa per strato
    strata = defaultdict(list)
    for case in cases:
        key = case.get("scuola", {}).get(stratify_by, "Altro")
        strata[key].append(case)

    sampled = []
    remaining_quota = max_total

    # Prima passata: minimo garantito per strato
    for stratum, stratum_cases in sorted(strata.items()):
        take = min(min_per_stratum, len(stratum_cases), remaining_quota)
        sampled.extend(stratum_cases[:take])
        remaining_quota -= take
        if remaining_quota <= 0:
            break

    # Seconda passata: proporzionale con quota rimanente
    if remaining_quota > 0:
        all_remaining = []
        for stratum, stratum_cases in strata.items():
            all_remaining.extend(stratum_cases[min_per_stratum:])

        # Campionamento sistematico sul resto
        step = max(1, len(all_remaining) // remaining_quota)
        sampled.extend(all_remaining[::step][:remaining_quota])

    return sampled
```

**Effort**: 3 ore
**Impatto**: Rappresentatività geografica garantita

---

## Fase 4: Qualità e Manutenibilità (Priorità Bassa)

### 4.1 Output JSON Strutturato per Reviewer

**Problema**: Il `Reviewer` in `config/prompts.md` produce testo libero difficile da parsare.

**Soluzione**: Richiedere output JSON con patch specifiche.

**Modifica in config/prompts.md** - sezione Reviewer:

```markdown
## Reviewer
Sei un **REVISORE CRITICO (Red Teamer)**...

Output:
Se tutto è perfetto: `{"status": "APPROVED", "patches": []}`

Altrimenti produci un JSON con le correzioni richieste:
```json
{
  "status": "NEEDS_REVISION",
  "patches": [
    {
      "type": "score_correction",
      "field": "ptof_section2.2_6_didattica_orientativa.didattica_laboratoriale",
      "current_value": 6,
      "suggested_value": 3,
      "reason": "Nel testo si menzionano solo lezioni frontali, non laboratori."
    },
    {
      "type": "hallucination",
      "text": "progetto OrientaMente",
      "action": "remove",
      "reason": "Non presente nel documento sorgente."
    },
    {
      "type": "missing_section",
      "section": "Inclusione",
      "action": "add_analysis"
    }
  ]
}
```
```

**Effort**: 2 ore
**Impatto**: Automazione correzioni

---

### 4.2 Test Suite per Prompt

**Problema**: Nessun modo di verificare che i prompt producano output validi.

**Soluzione**: Creare test con output di riferimento.

**Nuovo file**: `tests/test_meta_report_prompts.py`

```python
"""Test suite per validare output dei prompt meta report."""

import pytest
import re
from src.agents.meta_report.providers.base import BaseProvider

class MockProvider(BaseProvider):
    """Provider mock per test."""
    name = "mock"
    def is_available(self): return True
    def generate(self, prompt, system_prompt=None):
        return LLMResponse(content="test", model="mock", provider="mock")

class TestPromptValidation:

    def test_school_code_pattern(self):
        """Verifica che il pattern di validazione codici funzioni."""
        valid_codes = {"RMPS12345X", "MIIS00900T", "TOPS01000B"}
        pattern = r'\b([A-Z]{2}[A-Z]{2}[A-Z0-9]{5,6})\b'

        for code in valid_codes:
            assert re.match(pattern, code), f"Codice valido non riconosciuto: {code}"

        invalid = ["XXXX", "rm12345", "RMPS123"]
        for code in invalid:
            match = re.match(pattern, code)
            assert not match or match.group() not in valid_codes

    def test_system_prompt_contains_citation_rules(self):
        """Verifica che tutti i system prompt contengano regole citazioni."""
        provider = MockProvider()

        for report_type in ["school", "regional", "national", "thematic"]:
            prompt = provider._get_system_prompt(report_type, "overview")
            assert "Nome Scuola (CODICE)" in prompt or "Nome (Codice)" in prompt
            assert "NON inventare" in prompt.lower() or "non inventare" in prompt.lower()

    def test_profile_focus_present(self):
        """Verifica che ogni profilo abbia un focus distinto."""
        provider = MockProvider()

        profiles = ["overview", "innovative", "comparative", "impact", "operational"]
        prompts = []

        for profile in profiles:
            data = {"dimension_name": "test", "filters": {}}
            prompt = provider._format_analysis_prompt(data, "thematic", profile)
            prompts.append(prompt)

        # Tutti i prompt devono essere diversi
        assert len(set(prompts)) == len(profiles), "I profili devono generare prompt diversi"
```

**Effort**: 4 ore
**Impatto**: Prevenzione regressioni

---

### 4.3 Logging Strutturato

**Problema**: I log attuali sono semplici print, difficili da analizzare.

**Soluzione**: Implementare logging strutturato con metriche.

**Nuovo file**: `src/agents/meta_report/logging.py`

```python
"""Structured logging for meta report generation."""

import json
import logging
from datetime import datetime
from pathlib import Path

class MetaReportLogger:
    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.log_dir.mkdir(exist_ok=True)
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.metrics = {
            "session_id": self.session_id,
            "reports_generated": 0,
            "llm_calls": 0,
            "tokens_used": 0,
            "errors": [],
            "validation_issues": [],
        }

    def log_generation_start(self, report_type: str, identifier: str):
        logging.info(json.dumps({
            "event": "generation_start",
            "report_type": report_type,
            "identifier": identifier,
            "timestamp": datetime.now().isoformat()
        }))

    def log_llm_call(self, report_type: str, tokens: int, duration_ms: int):
        self.metrics["llm_calls"] += 1
        self.metrics["tokens_used"] += tokens
        logging.info(json.dumps({
            "event": "llm_call",
            "report_type": report_type,
            "tokens": tokens,
            "duration_ms": duration_ms
        }))

    def log_validation_issue(self, issue_type: str, details: dict):
        self.metrics["validation_issues"].append({
            "type": issue_type,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })

    def save_session_metrics(self):
        metrics_file = self.log_dir / f"metrics_{self.session_id}.json"
        metrics_file.write_text(json.dumps(self.metrics, indent=2))
```

**Effort**: 3 ore
**Impatto**: Osservabilità e debugging

---

## Riepilogo Piano

| Fase | Intervento | Effort | Impatto | File Coinvolti |
|------|-----------|--------|---------|----------------|
| **1.1** | Validazione codici scuola | 2h | Critico | `base.py` |
| **1.2** | Caching risultati intermedi | 3h | Critico | `thematic.py` |
| **1.3** | Fix istruzioni contraddittorie | 1h | Alto | `base.py` |
| **2.1** | Few-shot examples | 4h | Alto | Nuovo `prompts/examples.py`, `base.py` |
| **2.2** | Potenziare prompt profile | 3h | Alto | `base.py` |
| **2.3** | Modularizzare prompt | 4h | Medio | Nuovo `prompts/components.py`, `base.py` |
| **3.1** | Chunking semantico | 4h | Medio | `thematic.py` |
| **3.2** | Contesto cumulativo chunk | 5h | Medio | `thematic.py` |
| **3.3** | Sampling stratificato | 3h | Medio | `thematic.py` |
| **4.1** | JSON output per Reviewer | 2h | Basso | `config/prompts.md` |
| **4.2** | Test suite prompt | 4h | Basso | Nuovo `tests/test_meta_report_prompts.py` |
| **4.3** | Logging strutturato | 3h | Basso | Nuovo `logging.py` |

**Effort Totale Stimato**: ~38 ore

---

## Ordine di Implementazione Consigliato

```
Settimana 1: Fase 1 (Quick Wins) - 6 ore
├── 1.1 Validazione codici
├── 1.2 Caching
└── 1.3 Fix contraddizioni

Settimana 2: Fase 2 (Qualità Prompt) - 11 ore
├── 2.1 Few-shot examples
├── 2.2 Prompt profile
└── 2.3 Modularizzazione

Settimana 3: Fase 3 (Pipeline) - 12 ore
├── 3.1 Chunking semantico
├── 3.2 Contesto cumulativo
└── 3.3 Sampling stratificato

Settimana 4: Fase 4 (Manutenibilità) - 9 ore
├── 4.1 JSON Reviewer
├── 4.2 Test suite
└── 4.3 Logging
```

---

## Metriche di Successo

| Metrica | Baseline | Target Post-Correzione |
|---------|----------|------------------------|
| Codici meccanografici invalidi per report | ~5% | 0% |
| Retry per errori mid-generation | 20% | < 5% |
| Varianza output tra profili diversi | Bassa | Alta |
| Tempo medio generazione thematic (50+ casi) | ~8 min | ~5 min (con cache) |
| Coverage test prompt | 0% | > 80% |

---

## Note per l'Implementazione

1. **Backward Compatibility**: Tutti i cambiamenti devono mantenere compatibilità con i report già generati
2. **Feature Flags**: Usare variabili d'ambiente per abilitare/disabilitare nuove feature (es. `META_REPORT_USE_SEMANTIC_CHUNKING=1`)
3. **Rollback Plan**: Ogni fase può essere annullata indipendentemente
4. **Documentazione**: Aggiornare `docs/meta_report/README.md` dopo ogni fase

---

## Appendice: Struttura File Dopo le Modifiche

```
src/agents/meta_report/
├── __init__.py
├── cli.py
├── orchestrator.py
├── registry.py
├── logging.py                    # NUOVO (Fase 4.3)
├── providers/
│   ├── __init__.py
│   ├── base.py                   # MODIFICATO (Fasi 1.1, 1.3, 2.1, 2.2, 2.3)
│   ├── gemini.py
│   ├── ollama.py
│   └── openrouter.py
├── prompts/                      # NUOVA DIRECTORY
│   ├── __init__.py
│   ├── components.py             # NUOVO (Fase 2.3)
│   └── examples.py               # NUOVO (Fase 2.1)
└── reporters/
    ├── __init__.py
    ├── base.py
    ├── school.py
    ├── regional.py
    ├── national.py
    └── thematic.py               # MODIFICATO (Fasi 1.2, 3.1, 3.2, 3.3)

tests/
└── test_meta_report_prompts.py   # NUOVO (Fase 4.2)
```

---

# Piano di Correzione: Dashboard Attività - Doppioni e Filtri Geografici

**Data**: 2026-01-11
**Versione**: 1.0
**Stato**: 📋 DA IMPLEMENTARE

---

## Executive Summary

Questo documento definisce un piano per risolvere due problemi nella pagina **Attività** della dashboard:

1. **Doppioni nei filtri** "Tipologia Metodologia" e "Ambito Attività" causati da inconsistenze di capitalizzazione
2. **Filtri geografici non collegati** - Area geografica, Regione e Provincia sono indipendenti invece di essere a cascata

---

## Problema 1: Doppioni nei Filtri Dropdown

### Analisi Root Cause

I dropdown "Tipologia Metodologia" e "Ambito Attività" mostrano valori duplicati perché:

1. **I dati vengono estratti da LLM** senza normalizzazione case-sensitive
2. **La pagina usa `.strip()` ma non `.title()` o `.lower()`** quando costruisce le opzioni
3. **`set()` non deduplica varianti di capitalizzazione**

**Esempi di duplicati trovati nel CSV:**

| Campo | Variante 1 | Variante 2 | Variante 3 |
|-------|-----------|-----------|-----------|
| Tipologia Metodologia | `Didattica Digitale` | `Didattica digitale` | - |
| Tipologia Metodologia | `Circle Time` | `Circle time` | `Circle-time` |
| Tipologia Metodologia | `Inquiry-Based Learning` | `Inquiry-based Learning` | `Inquiry-based learning` |
| Ambito Attività | `Curricolo, Progettazione e Valutazione` | `Curricolo, progettazione e valutazione` | +2 varianti |
| Ambito Attività | `Imparare ad Imparare` | `Imparare ad imparare` | - |

**Codice attuale (linee 555-575 di `19_🌟_Attivita.py`):**

```python
# Ambiti - NO normalizzazione case
ambiti_disponibili = sorted(set(
    a.strip() for a in df_activities['ambiti_attivita'].dropna().str.split('|').explode()
    if a.strip()
))

# Metodologie - NO normalizzazione case
metodologie_disponibili = sorted(set(
    m.strip() for m in df_activities['tipologie_metodologia'].dropna().str.split('|').explode()
    if m.strip()
))
```

### Soluzione Proposta

#### Approccio 1: Normalizzazione a Runtime (Quick Fix)

Normalizzare i valori al momento della costruzione delle opzioni dropdown.

**File da modificare**: `app/pages/19_🌟_Attivita.py`

```python
def normalize_multivalue_field(series: pd.Series, separator: str = '|') -> list[str]:
    """
    Normalizza un campo multi-valore con case-insensitive deduplication.
    Mantiene la forma Title Case come rappresentazione canonica.
    """
    # Esplodi i valori
    values = series.dropna().str.split(separator).explode()

    # Crea mapping: lowercase -> prima occorrenza (preserva formato originale)
    canonical = {}
    for v in values:
        v_stripped = v.strip()
        if not v_stripped:
            continue
        key = v_stripped.lower()
        if key not in canonical:
            # Usa Title Case come forma canonica
            canonical[key] = v_stripped.title()

    return sorted(canonical.values())

# Uso nel codice:
ambiti_disponibili = normalize_multivalue_field(df_activities['ambiti_attivita'])
metodologie_disponibili = normalize_multivalue_field(df_activities['tipologie_metodologia'])
```

**Pro**: Risolve immediatamente il problema nella UI
**Contro**: I dati sottostanti restano inconsistenti; i filtri potrebbero non matchare esattamente

#### Approccio 2: Normalizzazione nel CSV (Soluzione Definitiva)

Aggiungere normalizzazione durante l'estrazione delle attività.

**File da modificare**: `src/agents/activity_extractor.py`

```python
def normalize_methodology(value: str) -> str:
    """Normalizza una tipologia metodologica."""
    # Mapping esplicito per casi speciali
    CANONICAL_FORMS = {
        "circle time": "Circle Time",
        "circle-time": "Circle Time",
        "inquiry-based learning": "Inquiry-Based Learning",
        "problem solving": "Problem Solving",
        "role-play": "Role-Play",
        "role play": "Role-Play",
        "team working": "Team Working",
        "peer tutoring": "Peer Tutoring",
        # ... altri casi speciali
    }

    normalized = value.strip()
    key = normalized.lower()

    if key in CANONICAL_FORMS:
        return CANONICAL_FORMS[key]

    # Default: Title Case
    return normalized.title()

# Applicare durante l'estrazione (linea ~970)
activity['tipologie_metodologia'] = '|'.join(
    normalize_methodology(m) for m in metodologie
)
```

**Pro**: Risolve il problema alla radice; dati puliti
**Contro**: Richiede ri-estrazione o script di migrazione

### Piano di Implementazione Consigliato

1. **Fase 1 - Quick Fix** (30 min): Implementare `normalize_multivalue_field()` nella pagina
2. **Fase 2 - Canonical Forms** (2 ore): Creare dizionario di forme canoniche in `src/utils/constants.py`
3. **Fase 3 - Pipeline Fix** (1 ora): Integrare normalizzazione in `activity_extractor.py`
4. **Fase 4 - Migration Script** (1 ora): Script per normalizzare CSV esistente

---

## Problema 2: Filtri Geografici Non Collegati a Cascata

### Analisi Situazione Attuale

**Codice attuale (linee 599-612 di `19_🌟_Attivita.py`):**

```python
# Ogni filtro è INDIPENDENTE - tutte le opzioni sempre visibili
aree_disponibili = sorted(df_activities['area_geografica'].dropna().unique().tolist())
sel_aree = st.multiselect("📍 Area Geografica", aree_disponibili, key="filter_aree")

regioni_disponibili = sorted(df_activities['regione'].dropna().unique().tolist())
sel_regioni = st.multiselect("🗺️ Regione", regioni_disponibili, key="filter_regioni")

province_disponibili = sorted(df_activities['provincia'].dropna().unique().tolist())
sel_province = st.multiselect("🏙️ Provincia", province_disponibili, key="filter_province")
```

**Problema**: L'utente può selezionare combinazioni impossibili (es. "Nord Ovest" + "Sicilia") che non restituiscono risultati.

### Soluzione Proposta: Filtri a Cascata

Implementare una logica dove:
- **Area Geografica** filtra le **Regioni** disponibili
- **Regioni selezionate** filtrano le **Province** disponibili

**Diagramma Logica:**

```
Area Geografica (selezione)
        ↓
   Filtra Regioni disponibili
        ↓
Regioni (selezione)
        ↓
   Filtra Province disponibili
        ↓
Province (selezione)
```

### Implementazione

**File da modificare**: `app/pages/19_🌟_Attivita.py`

**Passo 1: Importare il mapping da constants.py**

```python
from src.utils.constants import REGIONE_TO_AREA, SIGLA_PROVINCIA_MAP
```

**Passo 2: Costruire strutture dati per lookup inverso**

```python
# All'inizio del file, dopo gli import
def build_geo_hierarchy(df: pd.DataFrame) -> dict:
    """
    Costruisce la gerarchia Area → Regioni → Province dai dati.
    """
    hierarchy = {
        "area_to_regioni": {},    # Area → [Regioni]
        "regione_to_province": {} # Regione → [Province]
    }

    # Raggruppa per area geografica
    for area in df['area_geografica'].dropna().unique():
        regioni = df[df['area_geografica'] == area]['regione'].dropna().unique().tolist()
        hierarchy["area_to_regioni"][area] = sorted(regioni)

    # Raggruppa per regione
    for regione in df['regione'].dropna().unique():
        province = df[df['regione'] == regione]['provincia'].dropna().unique().tolist()
        hierarchy["regione_to_province"][regione] = sorted(province)

    return hierarchy

# Chiamata dopo il caricamento dati
geo_hierarchy = build_geo_hierarchy(df_activities)
```

**Passo 3: Modificare la logica dei filtri (sostituire linee 599-612)**

```python
with col_g1:
    # Area geografica - tutte le opzioni sempre disponibili
    aree_disponibili = sorted(df_activities['area_geografica'].dropna().unique().tolist())
    sel_aree = st.multiselect("📍 Area Geografica", aree_disponibili, key="filter_aree")

with col_g2:
    # Regione - filtrata in base alle aree selezionate
    if sel_aree:
        # Solo regioni delle aree selezionate
        regioni_disponibili = []
        for area in sel_aree:
            regioni_disponibili.extend(geo_hierarchy["area_to_regioni"].get(area, []))
        regioni_disponibili = sorted(set(regioni_disponibili))
    else:
        # Tutte le regioni se nessuna area selezionata
        regioni_disponibili = sorted(df_activities['regione'].dropna().unique().tolist())

    sel_regioni = st.multiselect("🗺️ Regione", regioni_disponibili, key="filter_regioni")

with col_g3:
    # Provincia - filtrata in base alle regioni selezionate
    if sel_regioni:
        # Solo province delle regioni selezionate
        province_disponibili = []
        for regione in sel_regioni:
            province_disponibili.extend(geo_hierarchy["regione_to_province"].get(regione, []))
        province_disponibili = sorted(set(province_disponibili))
    elif sel_aree:
        # Province delle aree selezionate (se nessuna regione specificata)
        regioni_in_aree = []
        for area in sel_aree:
            regioni_in_aree.extend(geo_hierarchy["area_to_regioni"].get(area, []))
        province_disponibili = []
        for regione in regioni_in_aree:
            province_disponibili.extend(geo_hierarchy["regione_to_province"].get(regione, []))
        province_disponibili = sorted(set(province_disponibili))
    else:
        # Tutte le province se nessun filtro superiore
        province_disponibili = sorted(df_activities['provincia'].dropna().unique().tolist())

    sel_province = st.multiselect("🏙️ Provincia", province_disponibili, key="filter_province")
```

**Passo 4: Gestire il reset dei filtri dipendenti**

Quando l'utente cambia Area Geografica, le selezioni di Regione/Provincia potrebbero diventare invalide.

```python
# Aggiungere dopo la selezione di aree (opzionale - UX migliorata)
# Rimuovi regioni selezionate che non sono più valide
if sel_aree and sel_regioni:
    valid_regioni = set()
    for area in sel_aree:
        valid_regioni.update(geo_hierarchy["area_to_regioni"].get(area, []))
    sel_regioni = [r for r in sel_regioni if r in valid_regioni]

# Rimuovi province selezionate che non sono più valide
if sel_regioni and sel_province:
    valid_province = set()
    for regione in sel_regioni:
        valid_province.update(geo_hierarchy["regione_to_province"].get(regione, []))
    sel_province = [p for p in sel_province if p in valid_province]
```

### Comportamento Atteso

| Selezione Utente | Regioni Disponibili | Province Disponibili |
|-----------------|---------------------|---------------------|
| Nessuna area | Tutte (20) | Tutte (107) |
| Nord Ovest | Piemonte, Lombardia, Liguria, Valle d'Aosta | Province di queste 4 regioni |
| Nord Ovest + Isole | Piemonte, Lombardia, Liguria, Valle d'Aosta, Sicilia, Sardegna | Province di queste 6 regioni |
| (Area: qualsiasi) + Regione: Lombardia, Sicilia | - | Province di Lombardia + Sicilia |

---

## Riepilogo Piano

| Problema | Soluzione | Effort | Priorità | File |
|----------|-----------|--------|----------|------|
| **Doppioni Tipologia Metodologia** | Normalizzazione runtime | 30 min | Alta | `19_🌟_Attivita.py` |
| **Doppioni Ambito Attività** | Normalizzazione runtime | 30 min | Alta | `19_🌟_Attivita.py` |
| **Forme canoniche** | Dizionario in constants | 2 ore | Media | `constants.py` |
| **Fix pipeline estrazione** | Normalizzare in extractor | 1 ora | Media | `activity_extractor.py` |
| **Filtri geografici a cascata** | Logica dipendente | 1.5 ore | Alta | `19_🌟_Attivita.py` |
| **Reset filtri invalidi** | Validazione selezioni | 30 min | Bassa | `19_🌟_Attivita.py` |

**Effort Totale**: ~6 ore

---

## Codice Completo: Funzioni Helper

```python
# Da aggiungere all'inizio di 19_🌟_Attivita.py

def normalize_multivalue_field(
    series: pd.Series,
    separator: str = '|',
    canonical_map: dict[str, str] | None = None
) -> list[str]:
    """
    Normalizza un campo multi-valore eliminando duplicati case-insensitive.

    Args:
        series: Serie pandas con valori separati da separator
        separator: Carattere separatore (default: '|')
        canonical_map: Dizionario opzionale lowercase -> forma canonica

    Returns:
        Lista ordinata di valori unici normalizzati
    """
    values = series.dropna().str.split(separator).explode()

    canonical = {}
    for v in values:
        v_stripped = v.strip()
        if not v_stripped:
            continue
        key = v_stripped.lower()

        if key not in canonical:
            # Usa forma canonica se fornita, altrimenti Title Case
            if canonical_map and key in canonical_map:
                canonical[key] = canonical_map[key]
            else:
                canonical[key] = v_stripped.title()

    return sorted(canonical.values())


def build_geo_hierarchy(df: pd.DataFrame) -> dict:
    """
    Costruisce la gerarchia geografica Area → Regioni → Province.

    Returns:
        Dict con 'area_to_regioni' e 'regione_to_province'
    """
    hierarchy = {
        "area_to_regioni": {},
        "regione_to_province": {}
    }

    for area in df['area_geografica'].dropna().unique():
        regioni = df[df['area_geografica'] == area]['regione'].dropna().unique().tolist()
        hierarchy["area_to_regioni"][area] = sorted(set(regioni))

    for regione in df['regione'].dropna().unique():
        province = df[df['regione'] == regione]['provincia'].dropna().unique().tolist()
        hierarchy["regione_to_province"][regione] = sorted(set(province))

    return hierarchy


def get_cascading_options(
    hierarchy: dict,
    selected_areas: list[str],
    selected_regions: list[str]
) -> tuple[list[str], list[str]]:
    """
    Calcola le opzioni disponibili per regioni e province in base alla selezione.

    Returns:
        (regioni_disponibili, province_disponibili)
    """
    # Regioni disponibili
    if selected_areas:
        regioni_disponibili = []
        for area in selected_areas:
            regioni_disponibili.extend(hierarchy["area_to_regioni"].get(area, []))
        regioni_disponibili = sorted(set(regioni_disponibili))
    else:
        regioni_disponibili = sorted(
            r for regioni in hierarchy["area_to_regioni"].values() for r in regioni
        )

    # Province disponibili
    if selected_regions:
        province_disponibili = []
        for regione in selected_regions:
            province_disponibili.extend(hierarchy["regione_to_province"].get(regione, []))
    elif selected_areas:
        province_disponibili = []
        for area in selected_areas:
            for regione in hierarchy["area_to_regioni"].get(area, []):
                province_disponibili.extend(hierarchy["regione_to_province"].get(regione, []))
    else:
        province_disponibili = sorted(
            p for province in hierarchy["regione_to_province"].values() for p in province
        )

    return regioni_disponibili, sorted(set(province_disponibili))
```

---

## Note di Implementazione

1. **Streamlit Form Limitation**: I filtri sono dentro un `st.form()`, quindi il comportamento a cascata sarà visibile solo dopo "Applica filtri". Per cascading in tempo reale, considerare l'uso di `st.session_state` con callback.

2. **Performance**: `build_geo_hierarchy()` dovrebbe essere chiamata una sola volta e cached con `@st.cache_data`.

3. **Data Migration**: Per normalizzare il CSV esistente senza ri-estrarre:
   ```bash
   python -c "
   import pandas as pd
   df = pd.read_csv('data/attivita.csv')
   # Normalizza campi...
   df.to_csv('data/attivita.csv', index=False)
   "
   ```

4. **Backward Compatibility**: La normalizzazione runtime non modifica i dati sottostanti, quindi i filtri applicati mapperanno correttamente.
