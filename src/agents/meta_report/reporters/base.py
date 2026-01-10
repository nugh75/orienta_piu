"""Base reporter class."""

import csv
import json
import re
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..providers import BaseProvider


class BaseReporter(ABC):
    """Abstract base class for report generators."""

    report_type: str = "base"
    FILTER_FIELDS = {
        "tipo_scuola": "contains",
        "ordine_grado": "contains",
        "regione": "exact",
        "provincia": "exact",
        "area_geografica": "exact",
        "statale_paritaria": "exact",
        "territorio": "exact",
    }

    def __init__(self, provider: BaseProvider, base_dir: Optional[Path] = None):
        self.provider = provider
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent.parent.parent.parent
        self.reports_dir = self.base_dir / "reports" / "meta"
        self.analysis_dir = self.base_dir / "analysis_results"
        self.summary_file = self.base_dir / "data" / "analysis_summary.csv"
        self._summary_map = None

    @abstractmethod
    def generate(self, **kwargs) -> Path:
        """Generate report and return path to output file."""
        pass

    @abstractmethod
    def get_output_path(self, **kwargs) -> Path:
        """Get the output path for the report."""
        pass

    def load_analysis(self, school_code: str) -> Optional[dict]:
        """Load analysis JSON for a school."""
        analysis_file = self.analysis_dir / f"{school_code}_PTOF_analysis.json"
        if not analysis_file.exists():
            return None
        try:
            return json.loads(analysis_file.read_text(encoding="utf-8"))
        except Exception:
            return None

    def load_all_analyses(self) -> list[dict]:
        """Load all analysis JSON files."""
        analyses = []
        for f in self.analysis_dir.glob("*_PTOF_analysis.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                data["_source_file"] = f.name
                data["_school_code"] = f.stem.replace("_PTOF_analysis", "")
                analyses.append(data)
            except Exception:
                continue
        return analyses

    def load_summary_map(self) -> dict:
        """Load analysis_summary.csv into a map keyed by school_id."""
        if self._summary_map is not None:
            return self._summary_map

        summary_map = {}
        if not self.summary_file.exists():
            self._summary_map = summary_map
            return summary_map

        try:
            with self.summary_file.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    code = row.get("school_id") or row.get("codice_meccanografico")
                    if code:
                        summary_map[code] = row
        except Exception:
            summary_map = {}

        self._summary_map = summary_map
        return summary_map

    def _normalize_filters(self, filters: Optional[dict]) -> dict:
        """Normalize filters to lowercase lists."""
        if not filters:
            return {}

        normalized = {}
        for key, value in filters.items():
            if key not in self.FILTER_FIELDS or value is None:
                continue

            values = []
            raw_values = value if isinstance(value, (list, tuple, set)) else [value]
            for raw in raw_values:
                if raw is None:
                    continue
                if isinstance(raw, str):
                    parts = [p.strip() for p in raw.split(",") if p.strip()]
                else:
                    parts = [str(raw).strip()]
                values.extend([p.lower() for p in parts if p])

            if values:
                normalized[key] = values

        return normalized

    def _matches_filters(self, data: dict, filters: dict) -> bool:
        """Check if a data dict matches normalized filters."""
        if not filters:
            return True

        for key, values in filters.items():
            if key not in self.FILTER_FIELDS or not values:
                continue

            field_value = data.get(key)
            if field_value is None or field_value == "":
                return False

            field_text = str(field_value).lower()
            mode = self.FILTER_FIELDS[key]
            if mode == "contains":
                if not any(v in field_text for v in values):
                    return False
            else:
                if field_text not in values:
                    return False

        return True

    def _build_filter_suffix(self, filters: dict) -> str:
        """Build a filename-safe suffix from normalized filters."""
        if not filters:
            return ""

        parts = []
        for key in sorted(filters.keys()):
            values = filters[key]
            if not values:
                continue
            value = "+".join(values)
            slug = re.sub(r"[^a-z0-9+]+", "-", value.lower()).strip("-")
            parts.append(f"{key}={slug}")

        return f"__{'__'.join(parts)}" if parts else ""

    def _build_report_suffix(self, filters: dict, prompt_profile: Optional[str] = None) -> str:
        """Build a filename-safe suffix from filters and prompt profile."""
        suffix = self._build_filter_suffix(filters)
        if prompt_profile:
            profile_slug = re.sub(r"[^a-z0-9]+", "-", prompt_profile.lower()).strip("-")
            profile_part = f"profile={profile_slug}"
            if suffix:
                suffix = f"{suffix}__{profile_part}"
            else:
                suffix = f"__{profile_part}"
        return suffix

    def _format_filters(self, filters: dict) -> str:
        """Format normalized filters for metadata."""
        if not filters:
            return ""
        return "; ".join(f"{key}={','.join(values)}" for key, values in filters.items() if values)

    def _get_school_filters_row(self, analysis: dict) -> dict:
        """Return a normalized school info row for filtering."""
        summary_map = self.load_summary_map()
        school_code = analysis.get("_school_code") or analysis.get("school_code")
        if school_code and school_code in summary_map:
            return summary_map[school_code]

        school_info = analysis.get("school_info", {}) or {}
        return {
            "regione": school_info.get("region") or school_info.get("regione"),
            "provincia": school_info.get("province") or school_info.get("provincia"),
            "area_geografica": school_info.get("area_geografica") or school_info.get("area"),
            "tipo_scuola": school_info.get("tipo_scuola") or school_info.get("school_type"),
            "ordine_grado": school_info.get("ordine_grado") or school_info.get("order_grade"),
            "statale_paritaria": school_info.get("statale_paritaria"),
            "territorio": school_info.get("territorio"),
        }

    def write_report(self, content: str, output_path: Path, metadata: dict) -> Path:
        """Write report to file with metadata header."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        header = f"""---
generated_at: {datetime.now().isoformat()}
provider: {self.provider.name}
report_type: {self.report_type}
"""
        for key, value in metadata.items():
            header += f"{key}: {value}\n"
        header += "---\n\n"

        output_path.write_text(header + content, encoding="utf-8")
        return output_path
