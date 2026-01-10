"""Thematic report generator (by dimension) - reads from attivita.csv/json."""

import csv
import json
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Optional

from .base import BaseReporter


# Dimension names mapping - basato sulle categorie/ambiti in attivita.csv
DIMENSIONS = {
    # Categorie principali da attivita
    "metodologie": "Metodologie Didattiche Innovative",
    "progetti": "Progetti e Attività Esemplari",
    "inclusione": "Buone Pratiche per l'Inclusione",
    "partnership": "Partnership e Collaborazioni Strategiche",

    # Ambiti/attività correlate
    "orientamento": "Orientamento",
    "pcto": "PCTO/Alternanza",
    "openday": "Open Day",
    "universita": "Orientamento Universitario",
    "visite": "Visite Guidate e Viaggi di Istruzione",
    "exalunni": "Rete Alumni e Mentoring",
    "certificazioni": "Certificazioni e Competenze",
}

# Mapping categorie -> dimension key
CATEGORY_TO_DIM = {
    "Metodologie Didattiche Innovative": "metodologie",
    "Progetti e Attività Esemplari": "progetti",
    "Buone Pratiche per l'Inclusione": "inclusione",
    "Partnership e Collaborazioni Strategiche": "partnership",
}

# Keywords per cercare nelle attività correlate
ACTIVITY_KEYWORDS = {
    "orientamento": ["orientamento"],
    "pcto": ["pcto", "alternanza", "scuola-lavoro", "scuola lavoro"],
    "openday": ["open day", "orientamento in entrata", "accoglienza"],
    "universita": ["universit", "manifestazioni universitarie", "orientamento in uscita"],
    "visite": ["visite guidate", "viaggi di istruzione", "uscite didattiche"],
    "exalunni": ["ex alunni", "ex-alunni", "alumni", "diplomati"],
    "certificazioni": ["certificazion", "cambridge", "dele", "delf", "eipass"],
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

    def _format_case_label(self, case: dict) -> str:
        """Build a compact label for inventory listings."""
        scuola = case.get("scuola", {})
        pratica = case.get("pratica", {})

        nome = scuola.get("nome") or "Scuola"
        codice = scuola.get("codice") or scuola.get("codice_meccanografico") or "ND"
        titolo = pratica.get("titolo") or "Attivita"
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
            return f"{label} ({meta})"
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

    def _extract_themes(self, case: dict) -> list[str]:
        pratica = case.get("pratica", {})
        themes = [t.strip() for t in pratica.get("ambiti_attivita", []) if t and t.strip()]
        if not themes:
            categoria = pratica.get("categoria")
            if categoria:
                themes = [categoria.strip()]
        return themes or ["Altre attivita"]

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
            "Analisi per tematiche",
            "Sintesi delle analisi tematiche",
            "Analisi per regione",
        }
        lines = []
        seen_h1 = False
        for line in content.splitlines():
            match = re.match(r"^(#{1,6})\s+(.*)$", line.strip())
            if not match:
                lines.append(line)
                continue
            level = len(match.group(1))
            text = match.group(2).strip()
            if level == 1:
                if not seen_h1:
                    seen_h1 = True
                    lines.append(f"# {text}")
                else:
                    lines.append(text)
                continue
            if level == 2:
                if text in allowed_h2:
                    lines.append(f"## {text}")
                else:
                    lines.append(text)
                continue
            # Keep theme headings, demote overly deep levels
            level = min(level, 4)
            lines.append(f"{'#' * level} {text}")
        return "\n".join(lines).strip()

    def _sample_case_labels(
        self,
        cases: list[dict],
        per_region: int = 2,
        max_total: int = 20
    ) -> list[str]:
        """Pick a small sample of case labels for narrative anchoring."""
        if not cases:
            return []

        grouped = self._group_cases_by_region(cases)
        samples: list[str] = []
        for region in sorted(grouped.keys()):
            for case in grouped[region][:per_region]:
                samples.append(self._format_case_label(case))
                if len(samples) >= max_total:
                    return samples
        return samples

    def _summarize_cases(self, cases: list[dict]) -> dict:
        region_counts = defaultdict(int)
        category_counts = defaultdict(int)
        schools = set()

        for case in cases:
            scuola = case.get("scuola", {})
            pratica = case.get("pratica", {})
            region = scuola.get("regione") or "Non specificata"
            category = pratica.get("categoria") or "Altre attivita"
            region_counts[region] += 1
            category_counts[category] += 1
            code = scuola.get("codice") or scuola.get("codice_meccanografico") or ""
            if code:
                schools.add(code)

        sample_cases = self._sample_case_labels(cases)
        top_regions = sorted(region_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "cases_count": len(cases),
            "schools_count": len(schools),
            "region_counts": dict(region_counts),
            "category_counts": dict(category_counts),
            "top_regions": top_regions,
            "sample_cases": sample_cases,
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
        chunk_threshold = int(os.getenv("META_REPORT_THEME_CHUNK_THRESHOLD", str(chunk_size * 2)))
        use_chunking = len(cases) >= chunk_threshold

        if use_chunking:
            chunks = self._chunk_cases(cases, chunk_size)
            chunk_notes = []
            for idx, chunk in enumerate(chunks, 1):
                chunk_summary = self._summarize_cases(chunk)
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

        if output_path.exists() and not force:
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

        theme_summaries = {}
        print("[thematic] Avvio analisi temi")
        for theme in theme_order:
            print(f"[thematic] Analisi tema: {theme} ({theme_counts[theme]} casi)")
            theme_summaries[theme] = self._generate_theme_summary(
                dimension,
                DIMENSIONS[dimension],
                theme,
                theme_groups[theme],
                prompt_profile,
                filters=filters
            )

        print("[thematic] Sintesi temi (merge)")
        summary_data = {
            "dimension": dimension,
            "dimension_name": DIMENSIONS[dimension],
            "themes": theme_order,
            "theme_counts": theme_counts,
            "theme_summaries": theme_summaries,
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
        content_parts.append("## Analisi per tematiche")
        for theme in theme_order:
            content_parts.append(f"### {theme}")
            content_parts.append(theme_summaries[theme])

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

        # Filter practices by dimension
        filtered_practices = []

        # Check if this is a category-based dimension
        dim_to_category = {v: k for k, v in CATEGORY_TO_DIM.items()}
        if dimension in dim_to_category:
            # Filter by pratica.categoria
            target_category = dim_to_category[dimension]
            for p in practices:
                categoria = p.get("pratica", {}).get("categoria", "")
                if categoria == target_category:
                    filtered_practices.append(p)
        else:
            # Filter by activity keywords (pcto, openday, etc.)
            keywords = ACTIVITY_KEYWORDS.get(dimension, [])
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
