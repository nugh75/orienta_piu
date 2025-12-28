"""Thematic report generator (by dimension) - reads from best_practices.json."""

import json
from collections import defaultdict
from pathlib import Path
from typing import Optional

from .base import BaseReporter


# Dimension names mapping - basato sulle categorie in best_practices.json
DIMENSIONS = {
    # Categorie principali da best_practices
    "metodologie": "Metodologie Didattiche Innovative",
    "progetti": "Progetti e Attività Esemplari",
    "inclusione": "Inclusione e Supporto",
    "orientamento": "Orientamento e Accompagnamento",
    "partnership": "Partnership e Collaborazioni",

    # Attività correlate (da contesto.attivita_correlate)
    "pcto": "PCTO e Alternanza Scuola-Lavoro",
    "openday": "Open Day e Orientamento in Entrata",
    "universita": "Orientamento Universitario",
    "visite": "Visite Guidate e Viaggi di Istruzione",
    "exalunni": "Rete Alumni e Mentoring",
    "certificazioni": "Certificazioni e Competenze",
}

# Mapping categorie -> dimension key
CATEGORY_TO_DIM = {
    "Metodologie Didattiche Innovative": "metodologie",
    "Progetti e Attività Esemplari": "progetti",
    "Inclusione e Supporto": "inclusione",
    "Orientamento e Accompagnamento": "orientamento",
    "Partnership e Collaborazioni": "partnership",
}

# Keywords per cercare nelle attività correlate
ACTIVITY_KEYWORDS = {
    "pcto": ["pcto", "alternanza", "scuola-lavoro", "scuola lavoro"],
    "openday": ["open day", "orientamento in entrata", "accoglienza"],
    "universita": ["universit", "manifestazioni universitarie", "orientamento in uscita"],
    "visite": ["visite guidate", "viaggi di istruzione", "uscite didattiche"],
    "exalunni": ["ex alunni", "ex-alunni", "alumni", "diplomati"],
    "certificazioni": ["certificazion", "cambridge", "dele", "delf", "eipass"],
}


class ThematicReporter(BaseReporter):
    """Generate thematic report for a specific dimension from best_practices.json."""

    report_type = "thematic"

    def __init__(self, provider, base_dir: Optional[Path] = None):
        super().__init__(provider, base_dir)
        self.best_practices_file = self.base_dir / "data" / "best_practices.json"

    def get_output_path(self, dimension: str, **kwargs) -> Path:
        """Get output path for thematic report."""
        return self.reports_dir / "thematic" / f"{dimension}_best_practices.md"

    def load_best_practices(self) -> list[dict]:
        """Load best practices from JSON file."""
        if not self.best_practices_file.exists():
            print(f"[thematic] File not found: {self.best_practices_file}")
            return []
        try:
            data = json.loads(self.best_practices_file.read_text(encoding="utf-8"))
            return data.get("practices", [])
        except Exception as e:
            print(f"[thematic] Error loading best practices: {e}")
            return []

    def generate(self, dimension: str, force: bool = False) -> Optional[Path]:
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

        output_path = self.get_output_path(dimension)

        if output_path.exists() and not force:
            print(f"[thematic] Report already exists: {output_path}")
            return output_path

        # Load best practices
        all_practices = self.load_best_practices()

        if not all_practices:
            print("[thematic] No best practices found")
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

        response = self.provider.generate_best_practices(report_data, "thematic")

        # Write report
        metadata = {
            "dimension": dimension,
            "dimension_name": DIMENSIONS[dimension],
            "practices_analyzed": report_data["practices_count"],
            "schools_involved": report_data["schools_count"],
        }

        self.write_report(response.content, output_path, metadata)
        print(f"[thematic] Report saved: {output_path}")

        return output_path

    def _prepare_data(self, dimension: str, practices: list[dict]) -> dict:
        """Extract dimension-specific data from best practices."""
        dimension_name = DIMENSIONS[dimension]

        # Filter practices by dimension
        filtered_practices = []

        # Check if this is a category-based dimension
        if dimension in CATEGORY_TO_DIM.values() or dimension in ["metodologie", "progetti", "inclusione", "orientamento", "partnership"]:
            # Filter by pratica.categoria
            target_category = dimension_name
            for p in practices:
                categoria = p.get("pratica", {}).get("categoria", "")
                if categoria == target_category or dimension in categoria.lower():
                    filtered_practices.append(p)
        else:
            # Filter by activity keywords (pcto, openday, etc.)
            keywords = ACTIVITY_KEYWORDS.get(dimension, [])
            for p in practices:
                # Search in attivita_correlate
                attivita = p.get("contesto", {}).get("attivita_correlate", [])
                attivita_text = " ".join(attivita).lower()

                # Also search in title and description
                titolo = p.get("pratica", {}).get("titolo", "").lower()
                descrizione = p.get("pratica", {}).get("descrizione", "").lower()
                metodologia = p.get("pratica", {}).get("metodologia", "").lower()

                search_text = f"{attivita_text} {titolo} {descrizione} {metodologia}"

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

        # Prepare sample practices (best examples)
        sample_practices = []
        for p in unique_practices[:20]:  # Top 20 examples
            sample_practices.append({
                "scuola": p.get("school", {}).get("nome", ""),
                "codice": p.get("school", {}).get("codice_meccanografico", ""),
                "regione": p.get("school", {}).get("regione", ""),
                "provincia": p.get("school", {}).get("provincia", ""),
                "tipo_scuola": p.get("school", {}).get("tipo_scuola", ""),
                "titolo": p.get("pratica", {}).get("titolo", ""),
                "categoria": p.get("pratica", {}).get("categoria", ""),
                "descrizione": p.get("pratica", {}).get("descrizione", ""),
                "metodologia": p.get("pratica", {}).get("metodologia", ""),
                "target": p.get("pratica", {}).get("target", ""),
                "citazione_ptof": p.get("pratica", {}).get("citazione_ptof", ""),
                "maturity_index": p.get("contesto", {}).get("maturity_index", 0),
                "partnership": p.get("contesto", {}).get("partnership_coinvolte", []),
                "attivita_correlate": p.get("contesto", {}).get("attivita_correlate", []),
            })

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
            "sample_practices": sample_practices,
        }
