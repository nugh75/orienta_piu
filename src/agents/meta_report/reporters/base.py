"""Base reporter class."""

import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..providers import BaseProvider


class BaseReporter(ABC):
    """Abstract base class for report generators."""

    report_type: str = "base"

    def __init__(self, provider: BaseProvider, base_dir: Optional[Path] = None):
        self.provider = provider
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent.parent.parent.parent
        self.reports_dir = self.base_dir / "reports" / "meta"
        self.analysis_dir = self.base_dir / "analysis_results"

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
