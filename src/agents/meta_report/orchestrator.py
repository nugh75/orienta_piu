"""Main orchestrator for meta report generation."""

import time
from pathlib import Path
from typing import Optional

from .providers import get_provider, BaseProvider
from .registry import MetaReportRegistry
from .reporters import SchoolReporter, RegionalReporter, NationalReporter, ThematicReporter
from .logger import MetaReportLogger


class MetaReportOrchestrator:
    """Orchestrates incremental meta report generation."""

    def __init__(self, provider_name: str = "auto", base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent.parent.parent
        self.provider = get_provider(provider_name)
        self.registry = MetaReportRegistry(self.base_dir)
        self.logger = MetaReportLogger(self.base_dir / "logs")

        # Initialize reporters
        self.school_reporter = SchoolReporter(self.provider, self.base_dir)
        self.regional_reporter = RegionalReporter(self.provider, self.base_dir)
        self.national_reporter = NationalReporter(self.provider, self.base_dir)
        self.thematic_reporter = ThematicReporter(self.provider, self.base_dir)

        # Create report directories if they don't exist
        self._ensure_report_directories()

    def _ensure_report_directories(self) -> None:
        """Create report directories if they don't exist."""
        reports_dir = self.base_dir / "reports" / "meta"
        for subdir in ["schools", "regional", "national", "thematic"]:
            (reports_dir / subdir).mkdir(parents=True, exist_ok=True)

    def generate_school(
        self,
        school_code: str,
        force: bool = False,
        prompt_profile: str = "overview"
    ) -> Optional[Path]:
        """Generate report for a single school."""
        self.logger.log_generation_start("school", school_code, profile=prompt_profile)
        start = time.time()

        result = self.school_reporter.generate(
            school_code,
            force=force,
            prompt_profile=prompt_profile
        )

        duration_ms = int((time.time() - start) * 1000)
        self.logger.log_generation_end(
            "school", school_code,
            success=result is not None,
            output_path=str(result) if result else None,
            duration_ms=duration_ms
        )

        if result:
            self.registry.mark_school_generated(school_code)
            # Mark regional as stale
            self._mark_region_stale_for_school(school_code)
        return result

    def generate_regional(
        self,
        region: str,
        force: bool = False,
        filters: Optional[dict] = None,
        prompt_profile: str = "overview"
    ) -> Optional[Path]:
        """Generate report for a region."""
        self.logger.log_generation_start("regional", region, profile=prompt_profile, filters=filters)
        start = time.time()

        result = self.regional_reporter.generate(
            region,
            force=force,
            filters=filters,
            prompt_profile=prompt_profile
        )

        duration_ms = int((time.time() - start) * 1000)
        self.logger.log_generation_end(
            "regional", region,
            success=result is not None,
            output_path=str(result) if result else None,
            duration_ms=duration_ms
        )

        if result and not filters:
            # Count schools in region
            all_analyses = self.regional_reporter.load_all_analyses()
            count = sum(1 for a in all_analyses
                       if a.get("school_info", {}).get("region", "").lower() == region.lower())
            self.registry.mark_regional_generated(region, count)
            # Mark national as stale
            self.registry.mark_national_stale(f"region updated: {region}")
        return result

    def generate_national(
        self,
        force: bool = False,
        filters: Optional[dict] = None,
        prompt_profile: str = "overview"
    ) -> Optional[Path]:
        """Generate national report."""
        self.logger.log_generation_start("national", "italia", profile=prompt_profile, filters=filters)
        start = time.time()

        result = self.national_reporter.generate(
            force=force,
            filters=filters,
            prompt_profile=prompt_profile
        )

        duration_ms = int((time.time() - start) * 1000)
        self.logger.log_generation_end(
            "national", "italia",
            success=result is not None,
            output_path=str(result) if result else None,
            duration_ms=duration_ms
        )

        if result and not filters:
            all_analyses = self.national_reporter.load_all_analyses()
            self.registry.mark_national_generated(len(all_analyses))
        return result

    def generate_thematic(
        self,
        dimension: str,
        force: bool = False,
        filters: Optional[dict] = None,
        prompt_profile: str = "overview"
    ) -> Optional[Path]:
        """Generate thematic report for a dimension."""
        self.logger.log_generation_start("thematic", dimension, profile=prompt_profile, filters=filters)
        start = time.time()

        result = self.thematic_reporter.generate(
            dimension,
            force=force,
            filters=filters,
            prompt_profile=prompt_profile
        )

        duration_ms = int((time.time() - start) * 1000)
        self.logger.log_generation_end(
            "thematic", dimension,
            success=result is not None,
            output_path=str(result) if result else None,
            duration_ms=duration_ms
        )

        if result and not filters:
            self.registry.mark_thematic_generated(dimension)
        return result

    def generate_next(self) -> Optional[tuple[str, str, Path]]:
        """Generate next pending report. Returns (type, id, path) or None."""
        pending = self.registry.get_next_pending()
        if not pending:
            print("[meta] No pending reports")
            return None

        report_type, identifier = pending

        if report_type == "school":
            path = self.generate_school(identifier, force=True)
        elif report_type == "regional":
            path = self.generate_regional(identifier, force=True)
        elif report_type == "national":
            path = self.generate_national(force=True)
        elif report_type == "thematic":
            path = self.generate_thematic(identifier, force=True)
        else:
            return None

        if path:
            return (report_type, identifier, path)
        return None

    def generate_batch(self, count: int = 5) -> list[tuple[str, str, Path]]:
        """Generate up to N pending reports."""
        results = []
        for _ in range(count):
            result = self.generate_next()
            if result:
                results.append(result)
            else:
                break
        return results

    def get_status(self) -> dict:
        """Get status summary."""
        return self.registry.get_status()

    def print_status(self) -> None:
        """Print status summary."""
        status = self.get_status()

        print("\n=== META REPORT STATUS ===\n")

        # Schools
        s = status["schools"]
        print(f"SCHOOLS ({s['total']} total)")
        print(f"  ✓ Current:  {s['current']}")
        print(f"  ⚠ Pending:  {s['stale']}")

        # Regional
        r = status["regional"]
        print(f"\nREGIONAL ({r['total']} regions)")
        print(f"  ✓ Current:  {r['current']}")
        print(f"  ⚠ Stale:    {r['stale']}")

        # National
        n = status["national"]
        status_icon = "✓" if n["status"] == "current" else "⚠"
        print(f"\nNATIONAL")
        print(f"  {status_icon} Status: {n['status']}")
        if n.get("generated_at"):
            print(f"    Last: {n['generated_at'][:10]}")

        # Thematic
        t = status["thematic"]
        print(f"\nTHEMATIC ({t['total']} dimensions)")
        print(f"  ✓ Current:  {t['current']}")
        print(f"  ⚠ Stale:    {t['stale']}")

        # Next action
        pending = self.registry.get_next_pending()
        if pending:
            print(f"\nNEXT: make meta-{pending[0]}", end="")
            if pending[1]:
                key = "CODE" if pending[0] == "school" else ("REGION" if pending[0] == "regional" else "DIM")
                print(f" {key}={pending[1]}")
            else:
                print()
        else:
            print("\nAll reports up to date!")

        print()

    def _mark_region_stale_for_school(self, school_code: str) -> None:
        """Mark the region of a school as stale."""
        analysis = self.school_reporter.load_analysis(school_code)
        if analysis:
            region = analysis.get("school_info", {}).get("region")
            if region:
                self.registry.mark_regional_stale(region, f"school updated: {school_code}")
