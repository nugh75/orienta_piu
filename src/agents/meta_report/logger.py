"""Structured logging for meta report generation.

Fase 4.3: Sistema di logging strutturato per tracciare operazioni,
metriche e problemi durante la generazione dei report.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class GenerationMetrics:
    """Metrics collected during report generation."""

    session_id: str
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())
    end_time: Optional[str] = None

    # Contatori
    reports_generated: int = 0
    reports_failed: int = 0
    llm_calls: int = 0
    cache_hits: int = 0
    cache_misses: int = 0

    # Risorse
    total_tokens: int = 0
    total_cost: float = 0.0

    # Validazione
    invalid_codes_found: int = 0
    validation_issues: list = field(default_factory=list)

    # Errori
    errors: list = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


class MetaReportLogger:
    """Structured logger for meta report operations.

    Usage:
        logger = MetaReportLogger(Path("logs"))
        logger.log_generation_start("school", "RMIS12345X")
        logger.log_llm_call("school", tokens=1500, duration_ms=2300)
        logger.log_validation_issue("invalid_code", {"code": "XXXX99999Z"})
        logger.log_generation_end("school", "RMIS12345X", success=True)
        logger.save_session_metrics()
    """

    def __init__(self, log_dir: Optional[Path] = None, session_id: Optional[str] = None):
        """Initialize the logger.

        Args:
            log_dir: Directory for log files. Defaults to project/logs/
            session_id: Optional session ID. Auto-generated if not provided.
        """
        self.log_dir = log_dir or Path(__file__).parent.parent.parent.parent / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.metrics = GenerationMetrics(session_id=self.session_id)

        # Setup Python logger
        self.logger = logging.getLogger(f"meta_report.{self.session_id}")
        self.logger.setLevel(logging.DEBUG)

        # File handler (JSON lines)
        log_file = self.log_dir / f"meta_report_{self.session_id}.jsonl"
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter("%(message)s"))
        self.logger.addHandler(fh)

        # Console handler (human readable)
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        self.logger.addHandler(ch)

        self._log_event("session_start", {"session_id": self.session_id})

    def _log_event(self, event_type: str, data: dict) -> None:
        """Log a structured event."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "session_id": self.session_id,
            "event": event_type,
            **data
        }
        self.logger.debug(json.dumps(event, ensure_ascii=False))

    def log_generation_start(self, report_type: str, identifier: str, **kwargs) -> None:
        """Log the start of a report generation.

        Args:
            report_type: Type of report (school, regional, national, thematic)
            identifier: Report identifier (school code, region name, dimension)
            **kwargs: Additional metadata
        """
        self._log_event("generation_start", {
            "report_type": report_type,
            "identifier": identifier,
            **kwargs
        })
        self.logger.info(f"Starting {report_type} report: {identifier}")

    def log_generation_end(
        self,
        report_type: str,
        identifier: str,
        success: bool,
        output_path: Optional[str] = None,
        duration_ms: Optional[int] = None,
        **kwargs
    ) -> None:
        """Log the end of a report generation.

        Args:
            report_type: Type of report
            identifier: Report identifier
            success: Whether generation succeeded
            output_path: Path to generated file
            duration_ms: Total duration in milliseconds
            **kwargs: Additional metadata
        """
        if success:
            self.metrics.reports_generated += 1
        else:
            self.metrics.reports_failed += 1

        self._log_event("generation_end", {
            "report_type": report_type,
            "identifier": identifier,
            "success": success,
            "output_path": str(output_path) if output_path else None,
            "duration_ms": duration_ms,
            **kwargs
        })

        status = "completed" if success else "FAILED"
        self.logger.info(f"Report {report_type}/{identifier} {status}")

    def log_llm_call(
        self,
        report_type: str,
        tokens: int = 0,
        duration_ms: int = 0,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        cost: float = 0.0,
        **kwargs
    ) -> None:
        """Log an LLM API call.

        Args:
            report_type: Type of report being generated
            tokens: Number of tokens used
            duration_ms: Call duration in milliseconds
            model: Model name
            provider: Provider name
            cost: Estimated cost
            **kwargs: Additional metadata
        """
        self.metrics.llm_calls += 1
        self.metrics.total_tokens += tokens
        self.metrics.total_cost += cost

        self._log_event("llm_call", {
            "report_type": report_type,
            "tokens": tokens,
            "duration_ms": duration_ms,
            "model": model,
            "provider": provider,
            "cost": cost,
            **kwargs
        })

    def log_cache_hit(self, cache_type: str, key: str) -> None:
        """Log a cache hit."""
        self.metrics.cache_hits += 1
        self._log_event("cache_hit", {"cache_type": cache_type, "key": key})

    def log_cache_miss(self, cache_type: str, key: str) -> None:
        """Log a cache miss."""
        self.metrics.cache_misses += 1
        self._log_event("cache_miss", {"cache_type": cache_type, "key": key})

    def log_validation_issue(
        self,
        issue_type: str,
        details: dict,
        severity: str = "medium"
    ) -> None:
        """Log a validation issue found during generation.

        Args:
            issue_type: Type of issue (invalid_code, missing_data, etc.)
            details: Issue details
            severity: Issue severity (low, medium, high, critical)
        """
        issue = {
            "type": issue_type,
            "details": details,
            "severity": severity,
            "timestamp": datetime.now().isoformat()
        }
        self.metrics.validation_issues.append(issue)

        if issue_type == "invalid_code":
            self.metrics.invalid_codes_found += 1

        self._log_event("validation_issue", issue)

        if severity in ("high", "critical"):
            self.logger.warning(f"Validation issue: {issue_type} - {details}")

    def log_error(
        self,
        error_type: str,
        message: str,
        exception: Optional[Exception] = None,
        **kwargs
    ) -> None:
        """Log an error.

        Args:
            error_type: Type of error
            message: Error message
            exception: Optional exception object
            **kwargs: Additional context
        """
        error = {
            "type": error_type,
            "message": message,
            "exception": str(exception) if exception else None,
            "timestamp": datetime.now().isoformat(),
            **kwargs
        }
        self.metrics.errors.append(error)

        self._log_event("error", error)
        self.logger.error(f"{error_type}: {message}")

    def log_chunk_progress(
        self,
        dimension: str,
        theme: str,
        chunk_index: int,
        chunk_total: int,
        from_cache: bool = False
    ) -> None:
        """Log chunk processing progress.

        Args:
            dimension: Dimension being processed
            theme: Theme being processed
            chunk_index: Current chunk number
            chunk_total: Total number of chunks
            from_cache: Whether this chunk came from cache
        """
        self._log_event("chunk_progress", {
            "dimension": dimension,
            "theme": theme,
            "chunk_index": chunk_index,
            "chunk_total": chunk_total,
            "from_cache": from_cache,
            "progress_pct": round(chunk_index / chunk_total * 100, 1)
        })

        source = "cache" if from_cache else "LLM"
        self.logger.info(f"Chunk {chunk_index}/{chunk_total} ({source}) - {dimension}/{theme}")

    def get_metrics(self) -> dict:
        """Get current metrics as dictionary."""
        self.metrics.end_time = datetime.now().isoformat()
        return self.metrics.to_dict()

    def save_session_metrics(self) -> Path:
        """Save session metrics to file.

        Returns:
            Path to saved metrics file
        """
        self.metrics.end_time = datetime.now().isoformat()

        metrics_file = self.log_dir / f"metrics_{self.session_id}.json"
        metrics_file.write_text(
            json.dumps(self.metrics.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        self._log_event("session_end", self.metrics.to_dict())
        self.logger.info(f"Session metrics saved: {metrics_file}")

        return metrics_file

    def print_summary(self) -> None:
        """Print a summary of the session to console."""
        m = self.metrics

        print("\n" + "=" * 50)
        print("META REPORT SESSION SUMMARY")
        print("=" * 50)
        print(f"Session ID: {m.session_id}")
        print(f"Duration: {m.start_time} -> {m.end_time or 'ongoing'}")
        print()
        print("REPORTS:")
        print(f"  Generated: {m.reports_generated}")
        print(f"  Failed: {m.reports_failed}")
        print()
        print("LLM USAGE:")
        print(f"  API Calls: {m.llm_calls}")
        print(f"  Total Tokens: {m.total_tokens:,}")
        print(f"  Estimated Cost: ${m.total_cost:.4f}")
        print()
        print("CACHING:")
        print(f"  Cache Hits: {m.cache_hits}")
        print(f"  Cache Misses: {m.cache_misses}")
        if m.cache_hits + m.cache_misses > 0:
            hit_rate = m.cache_hits / (m.cache_hits + m.cache_misses) * 100
            print(f"  Hit Rate: {hit_rate:.1f}%")
        print()
        print("VALIDATION:")
        print(f"  Invalid Codes Found: {m.invalid_codes_found}")
        print(f"  Issues: {len(m.validation_issues)}")
        print()
        if m.errors:
            print("ERRORS:")
            for err in m.errors[:5]:
                print(f"  - {err['type']}: {err['message']}")
            if len(m.errors) > 5:
                print(f"  ... and {len(m.errors) - 5} more")
        print("=" * 50)


# Singleton instance for easy access
_global_logger: Optional[MetaReportLogger] = None


def get_logger(log_dir: Optional[Path] = None) -> MetaReportLogger:
    """Get or create the global logger instance.

    Args:
        log_dir: Optional log directory

    Returns:
        MetaReportLogger instance
    """
    global _global_logger
    if _global_logger is None:
        _global_logger = MetaReportLogger(log_dir)
    return _global_logger


def reset_logger() -> None:
    """Reset the global logger (useful for tests)."""
    global _global_logger
    _global_logger = None
