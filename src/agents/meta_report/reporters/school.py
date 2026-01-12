"""School-level report generator."""

from datetime import datetime
from ..skeleton import load_activities_from_csv
from pathlib import Path
from typing import Optional

from .base import BaseReporter


class SchoolReporter(BaseReporter):
    """Generate best practices report for a single school."""

    report_type = "school"

    def get_output_path(
        self,
        school_code: str,
        prompt_profile: Optional[str] = None,
        **kwargs
    ) -> Path:
        """Get output path for school report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        suffix = self._build_report_suffix({}, prompt_profile)
        # Format: YYYYMMDD_HHMM__Scuola_CODE__filters.md
        return self.reports_dir / "schools" / f"{timestamp}__Scuola_{school_code}{suffix}_attivita.md"

    def generate(
        self,
        school_code: str,
        force: bool = False,
        prompt_profile: str = "overview"
    ) -> Optional[Path]:
        """Generate report for a single school.

        Args:
            school_code: School code (codice meccanografico)
            force: Regenerate even if report exists

        Returns:
            Path to generated report, or None if failed
        """
        output_path = self.get_output_path(school_code, prompt_profile=prompt_profile)

        # Check if already exists
        if output_path.exists() and not force:
            return output_path

        # Load analysis
        analysis = self.load_analysis(school_code)
        if not analysis:
            print(f"[school] No analysis found for {school_code}")
            return None

        # Prepare data for LLM
        report_data = self._prepare_data(school_code, analysis)

        # Generate report
        print(f"[school] Generating report for {school_code}...")
        response = self.provider.generate_best_practices(
            report_data,
            "school",
            prompt_profile=prompt_profile
        )

        # Write report
        metadata = {
            "school_code": school_code,
            "school_name": analysis.get("metadata", {}).get("denominazione") or analysis.get("school_info", {}).get("name", "N/D"),
            "region": analysis.get("metadata", {}).get("regione") or analysis.get("school_info", {}).get("region", "N/D"),
        }
        metadata["prompt_profile"] = prompt_profile

        self.write_report(response.content, output_path, metadata)
        print(f"[school] Report saved: {output_path}")

        return output_path

    def _prepare_data(self, school_code: str, analysis: dict) -> dict:
        """Prepare analysis data for LLM prompt."""
        # Handle schema variations
        school_info = analysis.get("metadata") or analysis.get("school_info", {})
        practices = analysis.get("activities_register") or analysis.get("practices", [])
        
        # Load RAW activities from CSV (to get the full list, e.g. 47 items)
        csv_path = self.base_dir / "data/attivita.csv"
        csv_practices = []
        if csv_path.exists():
            all_activities = load_activities_from_csv(csv_path)
            for row in all_activities:
                if row.get("codice_meccanografico") == school_code:
                    # Map CSV row to practice dict
                    csv_practices.append({
                        "titolo_attivita": row.get("titolo", "N/D"),
                        "categoria_principale": row.get("categoria", "Altro"),
                        "descrizione_e_metodologia": f"{row.get('descrizione', '')} - Metodologia: {row.get('metodologia', '')}",
                        "target": row.get("target", "Tutti"),
                        "evidence_quote": row.get("citazione_ptof", ""),
                        "source": "CSV"
                    })
        
        # Combine JSON practices (richer but fewer) with CSV practices (more numerous)
        # Use a dict by title to deduplicate, preferring JSON if available (richer data)
        practices_map = {p.get("titolo_attivita", ""): p for p in practices if p.get("titolo_attivita")}
        
        for p in csv_practices:
            title = p.get("titolo_attivita", "")
            if title and title not in practices_map:
                practices_map[title] = p
                
        final_practices = list(practices_map.values())

        # Flatten scores if needed (from ptof_section2)
        scores = analysis.get("scores", {})
        qualitative_details = {}
        
        if "ptof_section2" in analysis:
            for section in analysis["ptof_section2"].values():
                for key, val in section.items():
                    if isinstance(val, dict):
                        # Extract score
                        if "score" in val:
                            scores[key] = val["score"]
                        
                        # Extract evidence/notes
                        details = []
                        if val.get("evidence_quote"):
                            details.append(f"Citazione: \"{val['evidence_quote']}\"")
                        if val.get("note"):
                            details.append(f"Nota: {val['note']}")
                        
                        if details:
                            qualitative_details[key] = " | ".join(details)

        return {
            "school_code": school_code,
            "school_info": school_info,
            "scores": scores,
            "qualitative_details": qualitative_details,
            "dimensions": analysis.get("dimensions", {}),
            "practices": final_practices,
            "citations": analysis.get("citations", []),
            "summary": analysis.get("narrative") or analysis.get("summary", ""),
        }
