"""Registry for tracking meta report status."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional


class MetaReportRegistry:
    """Track status of generated reports."""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent.parent.parent
        self.registry_path = self.base_dir / "reports" / "meta" / "meta_registry.json"
        self.analysis_dir = self.base_dir / "analysis_results"
        self._data = None

    def _load(self) -> dict:
        """Load registry from disk."""
        if self._data is not None:
            return self._data

        if self.registry_path.exists():
            try:
                self._data = json.loads(self.registry_path.read_text(encoding="utf-8"))
            except Exception:
                self._data = self._empty_registry()
        else:
            self._data = self._empty_registry()

        return self._data

    def _save(self) -> None:
        """Save registry to disk."""
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self.registry_path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    def _empty_registry(self) -> dict:
        """Create empty registry structure."""
        return {
            "schools": {},
            "regional": {},
            "national": {"status": "missing"},
            "thematic": {},
        }

    def get_analysis_timestamp(self, school_code: str) -> Optional[str]:
        """Get modification time of analysis file."""
        analysis_file = self.analysis_dir / f"{school_code}_PTOF_analysis.json"
        if not analysis_file.exists():
            return None
        return datetime.fromtimestamp(analysis_file.stat().st_mtime).isoformat()

    def get_all_analyzed_schools(self) -> list[str]:
        """Get list of all schools with analysis."""
        schools = []
        for f in self.analysis_dir.glob("*_PTOF_analysis.json"):
            code = f.stem.replace("_PTOF_analysis", "")
            schools.append(code)
        return schools

    def get_all_regions(self) -> list[str]:
        """Get list of all regions from analyses."""
        regions = set()
        for f in self.analysis_dir.glob("*_PTOF_analysis.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                region = data.get("school_info", {}).get("region")
                if region:
                    regions.add(region)
            except Exception:
                continue
        return sorted(regions)

    # === School reports ===

    def mark_school_generated(self, school_code: str) -> None:
        """Mark school report as generated."""
        data = self._load()
        data["schools"][school_code] = {
            "generated_at": datetime.now().isoformat(),
            "source_analysis": self.get_analysis_timestamp(school_code),
            "status": "current",
        }
        self._save()

    def is_school_stale(self, school_code: str) -> bool:
        """Check if school report needs regeneration."""
        data = self._load()
        school = data["schools"].get(school_code)

        if not school:
            return True

        # Check if analysis is newer than report
        current_analysis = self.get_analysis_timestamp(school_code)
        if current_analysis and current_analysis > school.get("source_analysis", ""):
            return True

        return school.get("status") == "stale"

    def get_schools_needing_report(self) -> list[str]:
        """Get schools that need report generation."""
        data = self._load()
        all_schools = self.get_all_analyzed_schools()

        needs_report = []
        for code in all_schools:
            if code not in data["schools"]:
                needs_report.append(code)
            elif self.is_school_stale(code):
                needs_report.append(code)

        return needs_report

    # === Regional reports ===

    def mark_regional_generated(self, region: str, schools_count: int) -> None:
        """Mark regional report as generated."""
        data = self._load()
        data["regional"][region] = {
            "generated_at": datetime.now().isoformat(),
            "schools_count": schools_count,
            "status": "current",
        }
        self._save()

    def mark_regional_stale(self, region: str, reason: str = "") -> None:
        """Mark regional report as stale."""
        data = self._load()
        if region in data["regional"]:
            data["regional"][region]["status"] = "stale"
            data["regional"][region]["stale_reason"] = reason
            self._save()

    def get_stale_regions(self) -> list[str]:
        """Get regions with stale reports."""
        data = self._load()
        all_regions = self.get_all_regions()

        stale = []
        for region in all_regions:
            if region not in data["regional"]:
                stale.append(region)
            elif data["regional"][region].get("status") == "stale":
                stale.append(region)

        return stale

    # === National report ===

    def mark_national_generated(self, schools_count: int) -> None:
        """Mark national report as generated."""
        data = self._load()
        data["national"] = {
            "generated_at": datetime.now().isoformat(),
            "schools_count": schools_count,
            "status": "current",
        }
        self._save()

    def mark_national_stale(self, reason: str = "") -> None:
        """Mark national report as stale."""
        data = self._load()
        data["national"]["status"] = "stale"
        data["national"]["stale_reason"] = reason
        self._save()

    def is_national_stale(self) -> bool:
        """Check if national report needs regeneration."""
        data = self._load()
        return data["national"].get("status") in ("stale", "missing")

    # === Thematic reports ===

    def mark_thematic_generated(self, dimension: str) -> None:
        """Mark thematic report as generated."""
        data = self._load()
        data["thematic"][dimension] = {
            "generated_at": datetime.now().isoformat(),
            "status": "current",
        }
        self._save()

    def mark_thematic_stale(self, dimension: str) -> None:
        """Mark thematic report as stale."""
        data = self._load()
        if dimension in data["thematic"]:
            data["thematic"][dimension]["status"] = "stale"
            self._save()

    def get_stale_thematic(self) -> list[str]:
        """Get thematic dimensions with stale reports."""
        data = self._load()
        # Core dimensions + granular opportunity dimensions
        dimensions = [
            # Core
            "finalita", "obiettivi", "governance", "didattica", "partnership",
            # Granular opportunity dimensions
            "pcto", "stage", "openday", "visite", "laboratori", "testimonianze", "counseling", "alumni",
        ]

        stale = []
        for dim in dimensions:
            if dim not in data["thematic"]:
                stale.append(dim)
            elif data["thematic"][dim].get("status") == "stale":
                stale.append(dim)

        return stale

    # === Status summary ===

    def get_status(self) -> dict:
        """Get overall status summary."""
        data = self._load()
        all_schools = self.get_all_analyzed_schools()
        all_regions = self.get_all_regions()
        dimensions = [
            # Core
            "finalita", "obiettivi", "governance", "didattica", "partnership",
            # Granular opportunity dimensions
            "pcto", "stage", "openday", "visite", "laboratori", "testimonianze", "counseling", "alumni",
        ]

        schools_current = sum(1 for c in all_schools if c in data["schools"] and data["schools"][c].get("status") == "current")
        schools_stale = len(self.get_schools_needing_report())

        regions_current = sum(1 for r in all_regions if r in data["regional"] and data["regional"][r].get("status") == "current")
        regions_stale = len(self.get_stale_regions())

        thematic_current = sum(1 for d in dimensions if d in data["thematic"] and data["thematic"][d].get("status") == "current")
        thematic_stale = len(self.get_stale_thematic())

        return {
            "schools": {
                "total": len(all_schools),
                "current": schools_current,
                "stale": schools_stale,
            },
            "regional": {
                "total": len(all_regions),
                "current": regions_current,
                "stale": regions_stale,
            },
            "national": {
                "status": data["national"].get("status", "missing"),
                "generated_at": data["national"].get("generated_at"),
            },
            "thematic": {
                "total": len(dimensions),
                "current": thematic_current,
                "stale": thematic_stale,
            },
        }

    def get_next_pending(self) -> Optional[tuple[str, str]]:
        """Get next item to process. Returns (type, identifier) or None."""
        # Priority: schools > regions > national > thematic

        # 1. New schools first
        schools = self.get_schools_needing_report()
        if schools:
            return ("school", schools[0])

        # 2. Stale regions
        regions = self.get_stale_regions()
        if regions:
            return ("regional", regions[0])

        # 3. National
        if self.is_national_stale():
            return ("national", "")

        # 4. Thematic
        thematic = self.get_stale_thematic()
        if thematic:
            return ("thematic", thematic[0])

        return None
