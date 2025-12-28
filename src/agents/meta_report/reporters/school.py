"""School-level report generator."""

from pathlib import Path
from typing import Optional

from .base import BaseReporter


class SchoolReporter(BaseReporter):
    """Generate best practices report for a single school."""

    report_type = "school"

    def get_output_path(self, school_code: str, **kwargs) -> Path:
        """Get output path for school report."""
        return self.reports_dir / "schools" / f"{school_code}_best_practices.md"

    def generate(self, school_code: str, force: bool = False) -> Optional[Path]:
        """Generate report for a single school.

        Args:
            school_code: School code (codice meccanografico)
            force: Regenerate even if report exists

        Returns:
            Path to generated report, or None if failed
        """
        output_path = self.get_output_path(school_code)

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
        response = self.provider.generate_best_practices(report_data, "school")

        # Write report
        metadata = {
            "school_code": school_code,
            "school_name": analysis.get("school_info", {}).get("name", "N/D"),
            "region": analysis.get("school_info", {}).get("region", "N/D"),
        }

        self.write_report(response.content, output_path, metadata)
        print(f"[school] Report saved: {output_path}")

        return output_path

    def _prepare_data(self, school_code: str, analysis: dict) -> dict:
        """Prepare analysis data for LLM prompt."""
        return {
            "school_code": school_code,
            "school_info": analysis.get("school_info", {}),
            "scores": analysis.get("scores", {}),
            "dimensions": analysis.get("dimensions", {}),
            "practices": analysis.get("practices", []),
            "citations": analysis.get("citations", []),
            "summary": analysis.get("summary", ""),
        }
