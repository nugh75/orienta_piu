"""Main orchestrator for meta report generation."""

import time
from pathlib import Path
from typing import Optional

from .providers import get_provider, BaseProvider
from .registry import MetaReportRegistry
from .reporters import SchoolReporter
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

        # Create report directories if they don't exist
        self._ensure_report_directories()

    def _ensure_report_directories(self) -> None:
        """Create report directories if they don't exist."""
        reports_dir = self.base_dir / "reports" / "meta"
        for subdir in ["schools"]:
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



        # Thematic (legacy removed)
        # t = status["thematic"]
        # print(f"\\nTHEMATIC ({t['total']} dimensions)")
        # print(f"  ✓ Current:  {t['current']}")
        # print(f"  ⚠ Stale:    {t['stale']}")

        # Next action
        pending = self.registry.get_next_pending()
        if pending:
            print(f"\nNEXT: make meta-{pending[0]}", end="")
            if pending[1]:
                key = "CODE"
                print(f" {key}={pending[1]}")
            else:
                print()
        else:
            print("\nAll reports up to date!")

        print()


