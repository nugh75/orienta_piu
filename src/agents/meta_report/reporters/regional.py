"""Regional-level report generator."""

from collections import defaultdict
from pathlib import Path
from typing import Optional

from .base import BaseReporter


class RegionalReporter(BaseReporter):
    """Generate best practices report for a region."""

    report_type = "regional"

    def get_output_path(self, region: str, **kwargs) -> Path:
        """Get output path for regional report."""
        safe_region = region.replace(" ", "_").replace("'", "")
        return self.reports_dir / "regional" / f"{safe_region}_best_practices.md"

    def generate(self, region: str, force: bool = False) -> Optional[Path]:
        """Generate report for a region.

        Args:
            region: Region name
            force: Regenerate even if report exists

        Returns:
            Path to generated report, or None if failed
        """
        output_path = self.get_output_path(region)

        if output_path.exists() and not force:
            return output_path

        # Load all analyses for region
        all_analyses = self.load_all_analyses()
        regional_analyses = [
            a for a in all_analyses
            if a.get("school_info", {}).get("region", "").lower() == region.lower()
        ]

        if not regional_analyses:
            print(f"[regional] No analyses found for region: {region}")
            return None

        # Prepare aggregated data
        report_data = self._prepare_data(region, regional_analyses)

        # Generate report
        print(f"[regional] Generating report for {region} ({len(regional_analyses)} schools)...")
        response = self.provider.generate_best_practices(report_data, "regional")

        # Write report
        metadata = {
            "region": region,
            "schools_count": len(regional_analyses),
        }

        self.write_report(response.content, output_path, metadata)
        print(f"[regional] Report saved: {output_path}")

        return output_path

    def _prepare_data(self, region: str, analyses: list[dict]) -> dict:
        """Aggregate analyses for regional report."""
        # Aggregate scores
        scores_sum = defaultdict(float)
        scores_count = defaultdict(int)

        # Collect practices
        all_practices = []
        province_data = defaultdict(list)

        for analysis in analyses:
            school_code = analysis.get("_school_code", "")
            school_info = analysis.get("school_info", {})
            province = school_info.get("province", "N/D")

            # Aggregate scores
            for dim, score in analysis.get("scores", {}).items():
                if isinstance(score, (int, float)):
                    scores_sum[dim] += score
                    scores_count[dim] += 1

            # Collect practices
            for practice in analysis.get("practices", []):
                all_practices.append({
                    "practice": practice,
                    "school": school_code,
                    "province": province,
                })

            # Group by province
            province_data[province].append({
                "code": school_code,
                "name": school_info.get("name", ""),
                "ro_score": analysis.get("scores", {}).get("ro_index", 0),
            })

        # Calculate averages
        avg_scores = {
            dim: scores_sum[dim] / scores_count[dim]
            for dim in scores_sum
            if scores_count[dim] > 0
        }

        # Find top schools per province
        top_schools = {}
        for province, schools in province_data.items():
            sorted_schools = sorted(schools, key=lambda x: x.get("ro_score", 0), reverse=True)
            top_schools[province] = sorted_schools[:3]

        return {
            "region": region,
            "total_schools": len(analyses),
            "average_scores": avg_scores,
            "top_schools_by_province": top_schools,
            "sample_practices": all_practices[:20],  # Limit for prompt size
        }
