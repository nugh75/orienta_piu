"""Thematic report generator (by dimension) - reads from attivita.csv/json."""

import csv
import json
import os
import re
from datetime import datetime
from collections import defaultdict
from pathlib import Path
from typing import Optional

from .base import BaseReporter


# Soglia minima casi per generare sezione tema dedicata (configurabile via env)
MIN_THEME_CASES = int(os.getenv("META_REPORT_MIN_THEME_CASES", "5"))

# Nota metodologica da inserire all'inizio di ogni report tematico
METHODOLOGY_SECTION = """
## Nota Metodologica

Questo report analizza le **attività di orientamento** estratte dai PTOF delle scuole italiane e catalogate nel file `attivita.csv`. Le attività sono classificate in **sei categorie**:

| Categoria | Descrizione |
|-----------|-------------|
| 🎯 **Progetti e Attività Esemplari** | Iniziative innovative, replicabili e di impatto |
| 📚 **Metodologie Didattiche Innovative** | Approcci pedagogici originali e sperimentali |
| 🤝 **Partnership e Collaborazioni Strategiche** | Accordi con università, aziende, enti territoriali |
| ⚙️ **Azioni di Sistema e Governance** | Coordinamento, organigramma, referenti |
| 🌈 **Buone Pratiche per l'Inclusione** | Interventi per studenti con BES, DSA, disabilità |
| 🗺️ **Esperienze Territoriali Significative** | Attività radicate nel contesto locale |

### Come leggere questo report

- **Panoramica temi**: Tabella riassuntiva con conteggi per tema
- **Analisi per tematiche**: Sintesi narrativa per ogni tema principale (≥5 casi)
- **Altri temi emergenti**: Temi minori elencati in forma compatta
- **Sintesi finale**: Raccomandazioni e trend principali

I dati sono analizzati per **distribuzione geografica** (regione e provincia) quando disponibili i filtri.
"""

# Dimension names mapping - allineato con README
DIMENSIONS = {
    # Dimensioni Strutturali
    "finalita": "Finalità Orientative",
    "obiettivi": "Obiettivi e Risultati Attesi",
    "governance": "Governance e Organizzazione",
    "didattica": "Didattica Orientativa",
    "partnership": "Partnership e Reti",

    # Dimensioni Opportunità (Granulari)
    "pcto": "PCTO e Alternanza",
    "stage": "Stage e Tirocini",
    "openday": "Open Day",
    "visite": "Visite Aziendali e Universitarie",
    "laboratori": "Laboratori Orientativi e Simulazioni",
    "testimonianze": "Testimonianze e Incontri con Esperti",
    "counseling": "Counseling e Percorsi Individualizzati",
    "alumni": "Rete Alumni e Mentoring",

    # Dimensioni Tematiche (per analisi specifiche)
    "valutazione": "Valutazione e Autovalutazione",
    "formazione_docenti": "Formazione Docenti",
    "cittadinanza": "Cittadinanza e Legalità",
    "digitalizzazione": "Digitalizzazione",
    "inclusione": "Inclusione e BES",
    "continuita": "Continuità e Accoglienza",
    "famiglie": "Rapporti con Famiglie",
    "lettura": "Lettura e Scrittura",
    "orientamento": "Orientamento",
    "arte": "Arte e Creatività",
    "lingue": "Lingue Straniere",
    "stem": "STEM e Ricerca",
    "matematica": "Matematica e Logica",
    "disagio": "Prevenzione Disagio",
    "intercultura": "Intercultura e Lingue",
    "sostenibilita": "Sostenibilità e Ambiente",
    "sport": "Sport e Benessere",
    "imprenditorialita": "Imprenditorialità",
    "sistema": "Azioni di Sistema e Governance",
}

# Mapping categorie -> dimension key (per dimensioni strutturali)
CATEGORY_TO_DIM = {
    "Finalità Orientative": "finalita",
    "Obiettivi e Risultati Attesi": "obiettivi",
    "Governance e Organizzazione": "governance",
    "Didattica Orientativa": "didattica",
    "Partnership e Reti": "partnership",
    "Partnership e Collaborazioni Strategiche": "partnership",  # alias legacy
}

# Keywords per cercare nelle attività correlate
ACTIVITY_KEYWORDS = {
    # Dimensioni Strutturali
    "finalita": ["finalità", "mission", "scopo orientativo", "obiettivo formativo", "vision"],
    "obiettivi": ["obiettivi", "risultati attesi", "traguardi", "competenze in uscita", "esiti"],
    "governance": ["governance", "organizzazione", "coordinamento", "referente", "commissione", "gruppo di lavoro"],
    "didattica": ["didattica orientativa", "orientamento didattico", "competenze orientative", "modulo orientativo", "UDA orientativ"],

    # Dimensioni Opportunità (Granulari)
    "pcto": ["pcto", "alternanza", "scuola-lavoro", "scuola lavoro"],
    "stage": ["stage", "tirocinio", "tirocini", "esperienza lavorativa"],
    "openday": ["open day", "orientamento in entrata", "accoglienza", "presentazione scuola"],
    "visite": ["visite guidate", "visite aziendali", "visita universit", "viaggi di istruzione", "uscite didattiche"],
    "laboratori": ["laboratori orientativi", "simulazione", "job shadowing", "role playing", "laboratorio pratico"],
    "testimonianze": ["testimonianze", "incontri con esperti", "professionisti", "imprenditori", "testimonial"],
    "counseling": ["counseling", "orientamento individuale", "colloquio orientativo", "percorso personalizzato", "bilancio competenze"],
    "alumni": ["ex alunni", "ex-alunni", "alumni", "diplomati", "mentoring", "rete diplomati"],

    # Dimensioni Tematiche
    "valutazione": ["valutazione", "autovalutazione", "invalsi", "verifiche", "monitoraggio apprendimenti", "rubriche valutative"],
    "formazione_docenti": ["formazione docenti", "aggiornamento professionale", "formazione insegnanti", "sviluppo professionale", "corso docenti"],
    "cittadinanza": ["cittadinanza", "legalità", "educazione civica", "costituzione", "diritti", "doveri", "democrazia"],
    "digitalizzazione": ["digitale", "digitalizzazione", "competenze digitali", "coding", "robotica", "informatica", "tecnologie"],
    "inclusione": ["inclusione", "bes", "bisogni educativi speciali", "disabilità", "dsa", "sostegno", "integrazione"],
    "continuita": ["continuità", "accoglienza", "passaggio", "raccordo", "verticale", "orizzontale", "inserimento"],
    "famiglie": ["famiglie", "genitori", "rapporti scuola-famiglia", "coinvolgimento genitori", "patto educativo"],
    "lettura": ["lettura", "scrittura", "biblioteca", "letteratura", "comprensione testo", "produzione scritta"],
    "orientamento": ["orientamento", "scelta scolastica", "percorso formativo", "consapevolezza", "progetto di vita"],
    "arte": ["arte", "creatività", "musica", "teatro", "espressione artistica", "educazione estetica"],
    "lingue": ["lingue straniere", "inglese", "francese", "spagnolo", "tedesco", "certificazioni linguistiche", "clil"],
    "stem": ["stem", "steam", "scienze", "ricerca", "sperimentazione", "metodo scientifico", "laboratorio scientifico"],
    "matematica": ["matematica", "logica", "problem solving", "calcolo", "geometria", "algebra", "giochi matematici"],
    "disagio": ["disagio", "prevenzione", "bullismo", "cyberbullismo", "dispersione", "abbandono scolastico", "sportello ascolto"],
    "intercultura": ["intercultura", "multiculturalità", "integrazione stranieri", "mediazione culturale", "alfabetizzazione"],
    "sostenibilita": ["sostenibilità", "ambiente", "ecologia", "educazione ambientale", "sviluppo sostenibile", "agenda 2030"],
    "sport": ["sport", "benessere", "educazione fisica", "motoria", "salute", "alimentazione", "stili di vita"],
    "imprenditorialita": ["imprenditorialità", "impresa", "autoimprenditorialità", "start up", "business", "economia"],
    "sistema": ["azioni di sistema", "governance", "organigramma", "funzioni strumentali", "coordinamento", "piano triennale"],
}

# Mapping per raggruppare temi affini (normalizzazione)
THEME_ALIASES = {
    # Salute e benessere
    "salute": "Salute e Benessere",
    "benessere": "Salute e Benessere",
    "salute e benessere": "Salute e Benessere",
    "sport e benessere": "Sport e Benessere",
    # STEM
    "stem": "STEM e Ricerca",
    "steam": "STEM e Ricerca",
    "stem/steam": "STEM e Ricerca",
    "stem e ricerca": "STEM e Ricerca",
    "scienze e ricerca": "STEM e Ricerca",
    # Digitalizzazione
    "digitale": "Digitalizzazione",
    "digitalizzazione": "Digitalizzazione",
    "competenze digitali": "Digitalizzazione",
    # Inclusione
    "inclusione": "Inclusione e BES",
    "bes": "Inclusione e BES",
    "inclusione e bes": "Inclusione e BES",
    "buone pratiche per l'inclusione": "Inclusione e BES",
    # Cittadinanza
    "cittadinanza": "Cittadinanza e Legalità",
    "legalità": "Cittadinanza e Legalità",
    "cittadinanza e legalità": "Cittadinanza e Legalità",
    "educazione civica": "Cittadinanza e Legalità",
    # Lingue
    "lingue": "Lingue Straniere",
    "lingue straniere": "Lingue Straniere",
    "intercultura": "Intercultura e Lingue",
    # Arte
    "arte": "Arte e Creatività",
    "creatività": "Arte e Creatività",
    "arte e creatività": "Arte e Creatività",
    "musica": "Arte e Creatività",
    "teatro": "Arte e Creatività",
    "musica e teatro": "Arte e Creatività",
}


class ThematicReporter(BaseReporter):
    """Generate thematic report for a specific dimension from attivita.csv/json."""

    report_type = "thematic"

    def __init__(self, provider, base_dir: Optional[Path] = None):
        super().__init__(provider, base_dir)
        self.activities_meta_file = self.base_dir / "data" / "attivita.json"
        self.activities_csv_file = self.base_dir / "data" / "attivita.csv"

    def get_output_path(
        self,
        dimension: str,
        filters: Optional[dict] = None,
        prompt_profile: Optional[str] = None,
        **kwargs
    ) -> Path:
        """Get output path for thematic report."""
        suffix = self._build_report_suffix(filters or {}, prompt_profile)
        return self.reports_dir / "thematic" / f"{dimension}{suffix}_attivita.md"

    def load_best_practices(self) -> list[dict]:
        """Load practices from JSON (legacy) or CSV (current)."""
        if self.activities_meta_file.exists():
            try:
                data = json.loads(self.activities_meta_file.read_text(encoding="utf-8"))
                practices = data.get("practices", [])
                if isinstance(practices, list) and practices:
                    return practices
            except Exception as e:
                print(f"[thematic] Error loading attivita.json: {e}")

        if not self.activities_csv_file.exists():
            print(f"[thematic] File not found: {self.activities_csv_file}")
            return []

        def pipe_to_list(val: str) -> list[str]:
            if not val:
                return []
            return [v.strip() for v in str(val).split("|") if v.strip()]

        practices = []
        try:
            with self.activities_csv_file.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    maturity = row.get("maturity_index")
                    try:
                        maturity = float(maturity) if maturity else None
                    except (ValueError, TypeError):
                        maturity = None

                    ambiti = pipe_to_list(row.get("ambiti_attivita", ""))
                    practices.append({
                        "id": row.get("id", ""),
                        "school": {
                            "codice_meccanografico": row.get("codice_meccanografico", ""),
                            "nome": row.get("nome_scuola", ""),
                            "tipo_scuola": row.get("tipo_scuola", ""),
                            "ordine_grado": row.get("ordine_grado", ""),
                            "regione": row.get("regione", ""),
                            "provincia": row.get("provincia", ""),
                            "comune": row.get("comune", ""),
                            "area_geografica": row.get("area_geografica", ""),
                            "territorio": row.get("territorio", ""),
                            "statale_paritaria": row.get("statale_paritaria", ""),
                        },
                        "pratica": {
                            "categoria": row.get("categoria", ""),
                            "titolo": row.get("titolo", ""),
                            "descrizione": row.get("descrizione", ""),
                            "metodologia": row.get("metodologia", ""),
                            "tipologie_metodologia": pipe_to_list(row.get("tipologie_metodologia", "")),
                            "ambiti_attivita": ambiti,
                            "target": row.get("target", ""),
                            "citazione_ptof": row.get("citazione_ptof", ""),
                            "pagina_evidenza": row.get("pagina_evidenza", ""),
                        },
                        "contesto": {
                            "maturity_index": maturity,
                            "partnership_coinvolte": pipe_to_list(row.get("partnership_coinvolte", "")),
                            "attivita_correlate": ambiti,
                        },
                        "metadata": {
                            "extracted_at": row.get("extracted_at", ""),
                            "model_used": row.get("model_used", ""),
                            "source_file": row.get("source_file", ""),
                        },
                    })
        except Exception as e:
            print(f"[thematic] Error loading attivita.csv: {e}")
            return []

        return practices

    def _build_case_record(self, practice: dict) -> dict:
        """Build a lean case record for analysis prompts."""
        school = practice.get("school", {})
        pratica = practice.get("pratica", {})
        contesto = practice.get("contesto", {})

        return {
            "scuola": {
                "nome": school.get("nome", ""),
                "codice": school.get("codice_meccanografico", ""),
                "tipo_scuola": school.get("tipo_scuola", ""),
                "ordine_grado": school.get("ordine_grado", ""),
                "regione": school.get("regione", ""),
                "provincia": school.get("provincia", ""),
                "comune": school.get("comune", ""),
                "area_geografica": school.get("area_geografica", ""),
                "territorio": school.get("territorio", ""),
                "statale_paritaria": school.get("statale_paritaria", ""),
            },
            "pratica": {
                "categoria": pratica.get("categoria", ""),
                "titolo": pratica.get("titolo", ""),
                "descrizione": pratica.get("descrizione", ""),
                "metodologia": pratica.get("metodologia", ""),
                "tipologie_metodologia": pratica.get("tipologie_metodologia", []),
                "ambiti_attivita": pratica.get("ambiti_attivita", []),
                "target": pratica.get("target", ""),
                "citazione_ptof": pratica.get("citazione_ptof", ""),
                "pagina_evidenza": pratica.get("pagina_evidenza", ""),
            },
            "contesto": {
                "maturity_index": contesto.get("maturity_index"),
                "partnership_coinvolte": contesto.get("partnership_coinvolte", []),
                "attivita_correlate": contesto.get("attivita_correlate", []),
            },
        }

    def _format_case_label(self, case: dict, include_description: bool = True) -> str:
        """Build a compact label for inventory listings."""
        scuola = case.get("scuola", {})
        pratica = case.get("pratica", {})

        nome = scuola.get("nome") or "Scuola"
        codice = scuola.get("codice") or scuola.get("codice_meccanografico") or "ND"
        titolo = pratica.get("titolo") or "Attivita"
        descrizione = pratica.get("descrizione") or ""
        
        # Tronca descrizione a 150 caratteri
        if include_description and descrizione:
            descrizione_breve = descrizione[:150].strip()
            if len(descrizione) > 150:
                descrizione_breve += "..."
        else:
            descrizione_breve = ""
            
        meta_parts = [
            scuola.get("provincia"),
            scuola.get("regione"),
            scuola.get("ordine_grado"),
            scuola.get("tipo_scuola"),
            pratica.get("categoria"),
        ]
        meta = ", ".join([p for p in meta_parts if p])
        label = f"{nome} ({codice}) - {titolo}"
        if meta:
            label = f"{label} [{meta}]"
        if descrizione_breve:
            label = f"{label}: {descrizione_breve}"
        return label

    def _group_labels_by_region(self, cases: list[dict]) -> dict:
        """Group case labels by region."""
        grouped = defaultdict(list)
        for case in cases:
            region = case.get("scuola", {}).get("regione") or "Non specificata"
            grouped[region].append(self._format_case_label(case))
        return grouped

    def _group_labels_by_category(self, cases: list[dict]) -> dict:
        """Group case labels by category."""
        grouped = defaultdict(list)
        for case in cases:
            categoria = case.get("pratica", {}).get("categoria") or "Altre pratiche"
            grouped[categoria].append(self._format_case_label(case))
        return grouped

    def _case_key(self, case: dict) -> tuple[str, str]:
        scuola = case.get("scuola", {})
        pratica = case.get("pratica", {})
        return (
            scuola.get("codice") or scuola.get("codice_meccanografico") or "",
            pratica.get("titolo") or "",
        )

    def _normalize_theme(self, theme: str) -> str:
        """Normalize theme name using aliases."""
        if not theme:
            return "Altre attività"
        theme_lower = theme.strip().lower()
        return THEME_ALIASES.get(theme_lower, theme.strip())

    def _extract_themes(self, case: dict) -> list[str]:
        pratica = case.get("pratica", {})
        raw_themes = [t.strip() for t in pratica.get("ambiti_attivita", []) if t and t.strip()]
        if not raw_themes:
            categoria = pratica.get("categoria")
            if categoria:
                raw_themes = [categoria.strip()]
        if not raw_themes:
            return ["Altre attività"]
        # Normalizza e deduplica
        normalized = []
        seen = set()
        for t in raw_themes:
            norm = self._normalize_theme(t)
            if norm.lower() not in seen:
                seen.add(norm.lower())
                normalized.append(norm)
        return normalized or ["Altre attività"]

    def _group_cases_by_theme(self, cases: list[dict]) -> dict:
        grouped = defaultdict(list)
        seen = defaultdict(set)
        for case in cases:
            key = self._case_key(case)
            for theme in self._extract_themes(case):
                if key in seen[theme]:
                    continue
                seen[theme].add(key)
                grouped[theme].append(case)
        return grouped

    def _group_cases_by_region(self, cases: list[dict]) -> dict:
        grouped = defaultdict(list)
        for case in cases:
            region = case.get("scuola", {}).get("regione") or "Non specificata"
            grouped[region].append(case)
        return grouped

    def _chunk_cases(self, cases: list[dict], chunk_size: int) -> list[list[dict]]:
        """Split cases into chunks."""
        return [cases[i:i + chunk_size] for i in range(0, len(cases), chunk_size)]

    def _render_inventory(self, inventory_groups: dict) -> str:
        """Render full inventory in markdown."""
        if not inventory_groups:
            return ""

        lines = [
            "---",
            "## Inventario completo",
            "Elenco completo dei casi raggruppati per regione.",
        ]
        for region in sorted(inventory_groups.keys()):
            cases = sorted(inventory_groups[region])
            lines.append(f"### {region} ({len(cases)})")
            for item in cases:
                lines.append(f"- {item}")
        return "\n".join(lines)

    def _normalize_report_headings(self, content: str) -> str:
        """Normalize headings so only the intended hierarchy is preserved."""
        if not content:
            return ""
        allowed_h2 = {
            "Panoramica temi",
            "Analisi per tematiche",
            "Sintesi delle analisi tematiche",
            "Analisi per regione",
            "Altri temi emergenti",
        }
        lines = []
        seen_h1 = False
        prev_heading = None

        for line in content.splitlines():
            stripped = line.strip()

            # Rimuovi righe che sembrano titoli duplicati (testo in grassetto che ripete il tema)
            if stripped.startswith("**") and stripped.endswith("**"):
                # Potrebbe essere un titolo in grassetto generato dal modello
                inner = stripped[2:-2].strip()
                # Se il titolo precedente era simile, salta
                if prev_heading and inner.lower() in prev_heading.lower():
                    continue
                # Altrimenti converti in testo normale
                lines.append(inner)
                continue

            match = re.match(r"^(#{1,6})\s+(.*)$", stripped)
            if not match:
                lines.append(line)
                continue

            level = len(match.group(1))
            text = match.group(2).strip()

            # Rimuovi prefissi come "Sintesi Analitica:" o "Sintesi narrativa:"
            text = re.sub(r"^(Sintesi\s+(Analitica|narrativa|Narrativa)\s*:\s*)", "", text).strip()

            # Salta heading vuoti
            if not text:
                continue

            # Evita duplicati consecutivi
            if prev_heading and text.lower() == prev_heading.lower():
                continue

            if level == 1:
                if not seen_h1:
                    seen_h1 = True
                    lines.append(f"# {text}")
                    prev_heading = text
                else:
                    # H1 duplicato: converti in paragrafo
                    lines.append(f"\n{text}\n")
                continue

            if level == 2:
                if text in allowed_h2:
                    lines.append(f"## {text}")
                    prev_heading = text
                else:
                    # H2 non consentito: converti in paragrafo o H3
                    lines.append(f"### {text}")
                    prev_heading = text
                continue

            # Keep theme headings, demote overly deep levels
            level = min(level, 4)
            lines.append(f"{'#' * level} {text}")
            prev_heading = text

        # Post-process: rimuovi linee vuote multiple consecutive
        result = "\n".join(lines)
        result = re.sub(r"\n{3,}", "\n\n", result)
        return result.strip()

    def _sample_case_labels(
        self,
        cases: list[dict],
        per_region: int = 5,
        max_total: int = 50
    ) -> list[str]:
        """Pick a sample of case labels using systematic sampling (1 in 5)."""
        if not cases:
            return []

        # Ordina per regione e codice scuola per garantire distribuzione uniforme
        sorted_cases = sorted(cases, key=lambda x: (
            x.get("scuola", {}).get("regione", ""), 
            x.get("scuola", {}).get("codice", "")
        ))

        n = len(cases)
        if n < 10:
            # Se pochi casi, prendili tutti
            samples = sorted_cases
        else:
            # Campionamento sistematico 1 su 5 (20%)
            samples = sorted_cases[::5]

        return [self._format_case_label(c, include_description=True) for c in samples]

    def _summarize_cases(self, cases: list[dict], disable_sampling: bool = False) -> dict:
        region_counts = defaultdict(int)
        province_counts = defaultdict(int)
        category_counts = defaultdict(int)
        schools = set()

        for case in cases:
            scuola = case.get("scuola", {})
            pratica = case.get("pratica", {})
            region = scuola.get("regione") or "Non specificata"
            province = scuola.get("provincia") or "Non specificata"
            category = pratica.get("categoria") or "Altre attivita"
            region_counts[region] += 1
            province_counts[province] += 1
            category_counts[category] += 1
            code = scuola.get("codice") or scuola.get("codice_meccanografico") or ""
            if code:
                schools.add(code)

        n_cases = len(cases)
        
        if disable_sampling:
            # Analisi chunk: prendi TUUUTTI i casi
            sample_cases = [self._format_case_label(c, include_description=True) for c in cases]
            detail_level = "chunk_completo (analisi approfondita di ogni singolo caso)"
        else:
            # Logica dinamica per il sampling e livello dettaglio
            if n_cases < 10:
                per_region = 3
                max_total = 10
                detail_level = "sintetico (pochi casi)"
            elif n_cases < 50:
                per_region = 5
                max_total = 25
                detail_level = "medio (alcuni esempi rappresentativi)"
            elif n_cases < 100:
                per_region = 10
                max_total = 50
                detail_level = "approfondito (molti esempi e cluster)"
            else:
                per_region = 20
                max_total = 80
                detail_level = "molto dettagliato (ampia varieta di esempi e cluster)"

            sample_cases = self._sample_case_labels(cases, per_region=per_region, max_total=max_total)
        top_regions = sorted(region_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        top_provinces = sorted(province_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "cases_count": n_cases,
            "schools_count": len(schools),
            "region_counts": dict(region_counts),
            "province_counts": dict(province_counts),
            "category_counts": dict(category_counts),
            "top_regions": top_regions,
            "top_provinces": top_provinces,
            "sample_cases": sample_cases,
            "detail_level": detail_level,
        }

    def _build_activity_rows(self, cases: list[dict]) -> list[dict]:
        rows = []
        for case in cases:
            scuola = case.get("scuola", {})
            pratica = case.get("pratica", {})
            themes = self._extract_themes(case)
            rows.append({
                "tema": "; ".join(themes),
                "regione": scuola.get("regione") or "Non specificata",
                "provincia": scuola.get("provincia") or "",
                "scuola": scuola.get("nome") or "Scuola",
                "codice_meccanografico": scuola.get("codice") or scuola.get("codice_meccanografico") or "",
                "ordine_grado": scuola.get("ordine_grado") or "",
                "tipo_scuola": scuola.get("tipo_scuola") or "",
                "categoria": pratica.get("categoria") or "",
                "titolo": pratica.get("titolo") or "",
                "ambiti_attivita": " | ".join(pratica.get("ambiti_attivita", [])),
            })
        return rows

    def _write_activity_table(self, output_path: Path, rows: list[dict]) -> None:
        if not rows:
            return
        output_path.parent.mkdir(parents=True, exist_ok=True)
        table_path = output_path.with_suffix(".activities.csv")
        fieldnames = list(rows[0].keys())
        with table_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def _build_summary_table(
        self,
        theme_counts: dict,
        theme_groups: dict,
        min_cases: int
    ) -> str:
        """Build markdown summary table for themes."""
        lines = [
            "| Tema | Casi | Scuole | Regioni principali |",
            "|------|------|--------|-------------------|",
        ]
        for theme in sorted(theme_counts.keys(), key=lambda t: theme_counts[t], reverse=True):
            count = theme_counts[theme]
            cases = theme_groups.get(theme, [])
            schools = set()
            region_counts = defaultdict(int)
            for case in cases:
                scuola = case.get("scuola", {})
                code = scuola.get("codice") or scuola.get("codice_meccanografico") or ""
                if code:
                    schools.add(code)
                region = scuola.get("regione") or "N/D"
                region_counts[region] += 1
            top_regions = sorted(region_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            regions_str = ", ".join(f"{r} ({c})" for r, c in top_regions)
            # Marca temi sotto soglia
            marker = "" if count >= min_cases else " *"
            lines.append(f"| {theme}{marker} | {count} | {len(schools)} | {regions_str} |")
        lines.append("")
        lines.append(f"*Temi con meno di {min_cases} casi sono aggregati in 'Altri temi emergenti'*")
        return "\n".join(lines)

    def _build_minor_themes_section(
        self,
        minor_themes: dict[str, list],
        theme_counts: dict
    ) -> str:
        """Build a compact section for themes with few cases."""
        if not minor_themes:
            return ""

        lines = ["I seguenti temi emergenti presentano un numero limitato di casi ma meritano menzione:\n"]

        for theme in sorted(minor_themes.keys(), key=lambda t: theme_counts.get(t, 0), reverse=True):
            cases = minor_themes[theme]
            count = len(cases)
            # Estrai info sintetiche
            schools = set()
            regions = set()
            examples = []
            for case in cases[:3]:  # Max 3 esempi
                scuola = case.get("scuola", {})
                pratica = case.get("pratica", {})
                code = scuola.get("codice") or scuola.get("codice_meccanografico") or ""
                nome = scuola.get("nome") or "Scuola"
                if code:
                    schools.add(code)
                    examples.append(f"{nome} ({code})")
                region = scuola.get("regione")
                if region:
                    regions.add(region)

            regions_str = ", ".join(sorted(regions)[:3])
            examples_str = "; ".join(examples[:2])
            lines.append(f"- **{theme}** ({count} casi, {len(schools)} scuole): {regions_str}. Es: {examples_str}")

        return "\n".join(lines)

    def _generate_theme_summary(
        self,
        dimension: str,
        dimension_name: str,
        theme: str,
        cases: list[dict],
        prompt_profile: str,
        filters: Optional[dict] = None,
        region: Optional[str] = None
    ) -> str:
        theme_summary = self._summarize_cases(cases)
        theme_summary.update({
            "dimension": dimension,
            "dimension_name": dimension_name,
            "theme": theme,
            "scope": "region" if region else "national",
            "region": region,
        })

        chunk_size = max(8, int(os.getenv("META_REPORT_THEME_CHUNK_SIZE", "30")))
        # Abbassiamo la soglia a 35 per forzare il chunking anche su temi medi
        chunk_threshold = int(os.getenv("META_REPORT_THEME_CHUNK_THRESHOLD", "35"))
        use_chunking = len(cases) >= chunk_threshold

        if use_chunking:
            chunks = self._chunk_cases(cases, chunk_size)
            chunk_notes = []
            for idx, chunk in enumerate(chunks, 1):
                # Per i chunk, disabilitiamo il sampling: vogliamo che l'LLM veda tutto
                chunk_summary = self._summarize_cases(chunk, disable_sampling=True)
                chunk_data = {
                    "dimension": dimension,
                    "dimension_name": dimension_name,
                    "theme": theme,
                    "scope": "region" if region else "national",
                    "region": region,
                    "chunk_index": idx,
                    "chunk_total": len(chunks),
                    **chunk_summary,
                }
                if filters:
                    chunk_data["filters"] = filters
                chunk_response = self.provider.generate_best_practices(
                    chunk_data,
                    "thematic_group_chunk",
                    prompt_profile=prompt_profile
                )
                chunk_notes.append(chunk_response.content)

            merge_data = dict(theme_summary)
            merge_data["chunk_count"] = len(chunks)
            merge_data["chunk_notes"] = chunk_notes
            if filters:
                merge_data["filters"] = filters
            response = self.provider.generate_best_practices(
                merge_data,
                "thematic_group_merge",
                prompt_profile=prompt_profile
            )
            return response.content

        if filters:
            theme_summary["filters"] = filters
        response = self.provider.generate_best_practices(
            theme_summary,
            "thematic_group_merge",
            prompt_profile=prompt_profile
        )
        return response.content

    def generate(
        self,
        dimension: str,
        force: bool = False,
        filters: Optional[dict] = None,
        prompt_profile: str = "overview"
    ) -> Optional[Path]:
        """Generate thematic report for a dimension.

        Args:
            dimension: Dimension key (metodologie, progetti, pcto, etc.)
            force: Regenerate even if report exists

        Returns:
            Path to generated report, or None if failed
        """
        if dimension not in DIMENSIONS:
            print(f"[thematic] Unknown dimension: {dimension}")
            print(f"[thematic] Available: {list(DIMENSIONS.keys())}")
            return None

        filters = self._normalize_filters(filters)
        output_path = self.get_output_path(dimension, filters=filters, prompt_profile=prompt_profile)

        # Aggiungi timestamp per non sovrascrivere
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_path.with_name(f"{output_path.stem}_{timestamp}{output_path.suffix}")

        # Force diventa irrilevante per esistenza file, ma manteniamo la firma
        if output_path.exists() and not force:
             # Improbabile col timestamp, ma per sicurezza
            print(f"[thematic] Report already exists: {output_path}")
            return output_path

        # Load best practices
        all_practices = self.load_best_practices()

        if not all_practices:
            print("[thematic] No best practices found")
            return None

        if filters:
            all_practices = [p for p in all_practices if self._matches_filters(p.get("school", {}), filters)]

        if not all_practices:
            print("[thematic] No best practices found after filters")
            return None

        print(f"[thematic] Loaded {len(all_practices)} best practices")

        # Prepare thematic data
        report_data = self._prepare_data(dimension, all_practices)

        if report_data["practices_count"] == 0:
            print(f"[thematic] No practices found for dimension: {dimension}")
            return None

        # Generate report
        print(f"[thematic] Generating report for {DIMENSIONS[dimension]}...")
        print(f"[thematic] Found {report_data['practices_count']} relevant practices from {report_data['schools_count']} schools")

        cases = report_data.pop("practices", [])
        inventory_groups = report_data.pop("inventory_groups", {})

        theme_groups = self._group_cases_by_theme(cases)
        region_groups = self._group_cases_by_region(cases)
        activities_rows = self._build_activity_rows(cases)

        if filters:
            report_data["filters"] = filters

        print(f"[thematic] Themes detected: {len(theme_groups)}")
        theme_counts = {theme: len(group) for theme, group in theme_groups.items()}
        theme_order = sorted(theme_counts.keys(), key=lambda t: theme_counts[t], reverse=True)

        # Configura soglia minima (da env o default)
        min_theme_cases = int(os.getenv("META_REPORT_MIN_THEME_CASES", str(MIN_THEME_CASES)))

        # Separa temi maggiori da minori
        major_themes = [t for t in theme_order if theme_counts[t] >= min_theme_cases]
        minor_themes = {t: theme_groups[t] for t in theme_order if theme_counts[t] < min_theme_cases}

        print(f"[thematic] Major themes (>={min_theme_cases} cases): {len(major_themes)}")
        print(f"[thematic] Minor themes (<{min_theme_cases} cases): {len(minor_themes)}")

        # Genera tabella riepilogativa
        summary_table = self._build_summary_table(theme_counts, theme_groups, min_theme_cases)

        theme_summaries = {}
        print("[thematic] Avvio analisi temi maggiori")
        for theme in major_themes:
            print(f"[thematic] Analisi tema: {theme} ({theme_counts[theme]} casi)")
            theme_summaries[theme] = self._generate_theme_summary(
                dimension,
                DIMENSIONS[dimension],
                theme,
                theme_groups[theme],
                prompt_profile,
                filters=filters
            )

        # Sezione per temi minori (senza chiamata LLM, solo elencazione)
        minor_themes_section = self._build_minor_themes_section(minor_themes, theme_counts)

        print("[thematic] Sintesi temi (merge)")
        summary_data = {
            "dimension": dimension,
            "dimension_name": DIMENSIONS[dimension],
            "themes": major_themes,  # Solo temi maggiori nella sintesi
            "theme_counts": {t: theme_counts[t] for t in major_themes},
            "theme_summaries": theme_summaries,
            "minor_themes_count": len(minor_themes),
            "scope": "national",
        }
        if filters:
            summary_data["filters"] = filters
        summary_response = self.provider.generate_best_practices(
            summary_data,
            "thematic_summary_merge",
            prompt_profile=prompt_profile
        )

        include_regions = os.getenv("META_REPORT_INCLUDE_REGIONS", "0").strip().lower() in ("1", "true", "yes")
        regional_sections = {}
        if include_regions:
            print("[thematic] Avvio analisi temi per regione")
            for region in sorted(region_groups.keys()):
                region_cases = region_groups[region]
                print(f"[thematic] Analisi regione: {region} ({len(region_cases)} casi)")
                region_theme_groups = self._group_cases_by_theme(region_cases)
                region_theme_counts = {t: len(g) for t, g in region_theme_groups.items()}
                region_theme_order = sorted(region_theme_counts.keys(), key=lambda t: region_theme_counts[t], reverse=True)
                region_theme_summaries = {}
                for theme in region_theme_order:
                    print(f"[thematic] Analisi tema/regione: {region} / {theme} ({region_theme_counts[theme]} casi)")
                    region_theme_summaries[theme] = self._generate_theme_summary(
                        dimension,
                        DIMENSIONS[dimension],
                        theme,
                        region_theme_groups[theme],
                        prompt_profile,
                        filters=filters,
                        region=region
                    )
                region_summary_data = {
                    "dimension": dimension,
                    "dimension_name": DIMENSIONS[dimension],
                    "region": region,
                    "themes": region_theme_order,
                    "theme_counts": region_theme_counts,
                    "theme_summaries": region_theme_summaries,
                    "scope": "region",
                }
                if filters:
                    region_summary_data["filters"] = filters
                print(f"[thematic] Sintesi tema/regione (merge): {region}")
                region_summary_response = self.provider.generate_best_practices(
                    region_summary_data,
                    "regional_summary_merge",
                    prompt_profile=prompt_profile
                )
                regional_sections[region] = {
                    "themes": region_theme_order,
                    "theme_summaries": region_theme_summaries,
                    "summary": region_summary_response.content,
                }
            print("[thematic] Sintesi regioni completata")
        else:
            print("[thematic] Analisi per regione disattivata (META_REPORT_INCLUDE_REGIONS=0)")

        content_parts = [f"# {DIMENSIONS[dimension]}"]

        # Nota metodologica all'inizio
        content_parts.append(METHODOLOGY_SECTION)

        # Tabella riepilogativa all'inizio
        content_parts.append("## Panoramica temi")
        content_parts.append(summary_table)

        # Analisi temi maggiori
        content_parts.append("## Analisi per tematiche")
        for theme in major_themes:
            content_parts.append(f"### {theme}")
            content_parts.append(theme_summaries[theme])

        # Sezione temi minori (se presenti)
        if minor_themes_section:
            content_parts.append("## Altri temi emergenti")
            content_parts.append(minor_themes_section)

        content_parts.append("## Sintesi delle analisi tematiche")
        content_parts.append(summary_response.content)

        if include_regions:
            content_parts.append("## Analisi per regione")
            for region in sorted(regional_sections.keys()):
                section = regional_sections[region]
                content_parts.append(f"### {region}")
                for theme in section["themes"]:
                    content_parts.append(f"#### {theme}")
                    content_parts.append(section["theme_summaries"][theme])
                content_parts.append("#### Sintesi regionale")
                content_parts.append(section["summary"])

        # Appendice con riferimento al file CSV
        appendix_lines = [
            "## Appendice: Elenco completo attività",
            "",
            f"📊 **Statistiche**: {report_data['practices_count']} attività da {report_data['schools_count']} scuole",
            "",
            f"Il file CSV completo con tutte le attività è disponibile in:",
            f"`{output_path.stem}.activities.csv`",
            "",
            "Il file contiene: codice scuola, nome scuola, regione, provincia, tipo scuola, categoria, titolo, ambiti attività.",
        ]
        content_parts.append("\n".join(appendix_lines))

        content = "\n\n".join(content_parts)
        content = self._normalize_report_headings(content)

        # Write report
        metadata = {
            "dimension": dimension,
            "dimension_name": DIMENSIONS[dimension],
            "practices_analyzed": report_data["practices_count"],
            "schools_involved": report_data["schools_count"],
        }
        if filters:
            metadata["filters"] = self._format_filters(filters)
        metadata["prompt_profile"] = prompt_profile

        self.write_report(content, output_path, metadata)
        self._write_activity_table(output_path, activities_rows)
        print(f"[thematic] Report saved: {output_path}")

        return output_path

    def _prepare_data(self, dimension: str, practices: list[dict]) -> dict:
        """Extract dimension-specific data from best practices."""
        dimension_name = DIMENSIONS[dimension]

        # Filter practices by dimension using keyword matching
        # NOTE: The CSV categories (e.g., "Progetti e Attività Esemplari") differ from
        # the dimension names, so we always use keyword-based matching for all dimensions.
        filtered_practices = []
        keywords = ACTIVITY_KEYWORDS.get(dimension, [])
        
        if not keywords:
            print(f"[thematic] Warning: No keywords defined for dimension: {dimension}")
            return {
                "dimension": dimension,
                "dimension_name": dimension_name,
                "practices_count": 0,
                "schools_count": 0,
                "regional_distribution": {},
                "top_regions": [],
                "practices": [],
                "case_groups": {},
                "inventory_groups": {},
            }
        
        for p in practices:
            # Search in ambiti/attivita correlate
            ambiti = (
                p.get("pratica", {}).get("ambiti_attivita", [])
                or p.get("contesto", {}).get("attivita_correlate", [])
            )
            ambiti_text = " ".join(ambiti).lower()

            # Also search in title and description
            titolo = p.get("pratica", {}).get("titolo", "").lower()
            descrizione = p.get("pratica", {}).get("descrizione", "").lower()
            metodologia = p.get("pratica", {}).get("metodologia", "").lower()
            categoria = p.get("pratica", {}).get("categoria", "").lower()

            search_text = f"{ambiti_text} {titolo} {descrizione} {metodologia} {categoria}"

            if any(kw in search_text for kw in keywords):
                filtered_practices.append(p)

        # Deduplicate by school + title
        seen = set()
        unique_practices = []
        for p in filtered_practices:
            key = (
                p.get("school", {}).get("codice_meccanografico", ""),
                p.get("pratica", {}).get("titolo", "")
            )
            if key not in seen:
                seen.add(key)
                unique_practices.append(p)

        # Aggregate by region
        by_region = defaultdict(list)
        for p in unique_practices:
            region = p.get("school", {}).get("regione", "Non specificata")
            by_region[region].append(p)

        # Get schools involved
        schools = set()
        for p in unique_practices:
            code = p.get("school", {}).get("codice_meccanografico", "")
            if code:
                schools.add(code)

        case_records = [self._build_case_record(p) for p in unique_practices]
        case_groups = self._group_labels_by_category(case_records)
        inventory_groups = self._group_labels_by_region(case_records)

        # Regional summary
        regional_summary = {}
        for region, pracs in by_region.items():
            regional_summary[region] = {
                "count": len(pracs),
                "schools": len(set(p.get("school", {}).get("codice_meccanografico", "") for p in pracs)),
                "examples": [p.get("pratica", {}).get("titolo", "") for p in pracs[:3]]
            }

        return {
            "dimension": dimension,
            "dimension_name": dimension_name,
            "practices_count": len(unique_practices),
            "schools_count": len(schools),
            "regional_distribution": regional_summary,
            "top_regions": sorted(regional_summary.items(), key=lambda x: x[1]["count"], reverse=True)[:5],
            "practices": case_records,
            "case_groups": case_groups,
            "inventory_groups": inventory_groups,
        }
