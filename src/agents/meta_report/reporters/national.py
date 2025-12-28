"""National-level report generator."""

from collections import defaultdict
from pathlib import Path
from typing import Optional

from .base import BaseReporter


class NationalReporter(BaseReporter):
    """Generate best practices report at national level."""

    report_type = "national"

    def get_output_path(self, **kwargs) -> Path:
        """Get output path for national report."""
        return self.reports_dir / "national" / "national_best_practices.md"

    def generate(self, force: bool = False) -> Optional[Path]:
        """Generate national report.

        Args:
            force: Regenerate even if report exists

        Returns:
            Path to generated report, or None if failed
        """
        output_path = self.get_output_path()

        if output_path.exists() and not force:
            return output_path

        # Load all analyses
        all_analyses = self.load_all_analyses()

        if not all_analyses:
            print("[national] No analyses found")
            return None

        # Prepare aggregated data
        report_data = self._prepare_data(all_analyses)

        # Generate report
        print(f"[national] Generating national report ({len(all_analyses)} schools)...")
        response = self.provider.generate_best_practices(report_data, "national")

        # Write report
        metadata = {
            "total_schools": len(all_analyses),
            "regions_count": len(report_data["by_region"]),
        }

        self.write_report(response.content, output_path, metadata)
        print(f"[national] Report saved: {output_path}")

        return output_path

    def _prepare_data(self, analyses: list[dict]) -> dict:
        """Aggregate analyses for national report."""
        # Group by region
        by_region = defaultdict(list)
        scores_sum = defaultdict(float)
        scores_count = defaultdict(int)

        # Macro areas
        macro_areas = {
            "Nord": ["Piemonte", "Valle d'Aosta", "Lombardia", "Liguria",
                     "Trentino-Alto Adige", "Veneto", "Friuli-Venezia Giulia", "Emilia-Romagna"],
            "Centro": ["Toscana", "Umbria", "Marche", "Lazio"],
            "Sud e Isole": ["Abruzzo", "Molise", "Campania", "Puglia",
                           "Basilicata", "Calabria", "Sicilia", "Sardegna"],
        }

        by_macro = defaultdict(list)

        for analysis in analyses:
            school_info = analysis.get("school_info", {})
            region = school_info.get("region", "N/D")

            by_region[region].append(analysis)

            # Aggregate scores
            for dim, score in analysis.get("scores", {}).items():
                if isinstance(score, (int, float)):
                    scores_sum[dim] += score
                    scores_count[dim] += 1

            # Assign to macro area
            for macro, regions in macro_areas.items():
                if region in regions:
                    by_macro[macro].append(analysis)
                    break

        # Calculate averages
        avg_scores = {
            dim: round(scores_sum[dim] / scores_count[dim], 2)
            for dim in scores_sum
            if scores_count[dim] > 0
        }

        # Regional summary
        regional_summary = {}
        for region, region_analyses in by_region.items():
            ro_scores = [
                a.get("scores", {}).get("ro_index", 0)
                for a in region_analyses
            ]
            regional_summary[region] = {
                "count": len(region_analyses),
                "avg_ro": round(sum(ro_scores) / len(ro_scores), 2) if ro_scores else 0,
            }

        # Macro area summary
        macro_summary = {}
        for macro, macro_analyses in by_macro.items():
            ro_scores = [
                a.get("scores", {}).get("ro_index", 0)
                for a in macro_analyses
            ]
            macro_summary[macro] = {
                "count": len(macro_analyses),
                "avg_ro": round(sum(ro_scores) / len(ro_scores), 2) if ro_scores else 0,
            }

        # Top schools nationally
        sorted_analyses = sorted(
            analyses,
            key=lambda x: x.get("scores", {}).get("ro_index", 0),
            reverse=True
        )
        top_schools = [
            {
                "code": a.get("_school_code", ""),
                "name": a.get("school_info", {}).get("name", ""),
                "region": a.get("school_info", {}).get("region", ""),
                "ro_score": a.get("scores", {}).get("ro_index", 0),
            }
            for a in sorted_analyses[:10]
        ]

        return {
            "total_schools": len(analyses),
            "average_scores": avg_scores,
            "by_region": regional_summary,
            "by_macro_area": macro_summary,
            "top_10_schools": top_schools,
        }
