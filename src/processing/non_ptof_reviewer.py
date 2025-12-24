#!/usr/bin/env python3
"""
Non-PTOF Reviewer - remove analysis artifacts for documents classified as not PTOF.
"""

import sys
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.validation.ptof_validator import PTOFValidator, ValidationResult

ANALYSIS_DIR = BASE_DIR / "analysis_results"
MD_DIR = BASE_DIR / "ptof_md"
INBOX_DIR = BASE_DIR / "ptof_inbox"
PROCESSED_DIR = BASE_DIR / "ptof_processed"
DISCARDED_DIR = BASE_DIR / "ptof_discarded"

CSV_FILE = BASE_DIR / "data" / "analysis_summary.csv"
STATUS_FILES = [
    BASE_DIR / "data" / "review_status.json",
    BASE_DIR / "data" / "review_status_gemini.json",
    BASE_DIR / "data" / "score_review_status.json",
]
REVIEW_LOG = BASE_DIR / "data" / "non_ptof_review.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/non_ptof_review.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def _load_json_list(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _append_review_log(entry: Dict[str, Any]) -> None:
    items = _load_json_list(REVIEW_LOG)
    items.append(entry)
    REVIEW_LOG.parent.mkdir(parents=True, exist_ok=True)
    REVIEW_LOG.write_text(json.dumps(items, indent=2))


def _find_pdf_for_code(code: str) -> Optional[Path]:
    patterns = [
        INBOX_DIR.glob,
        lambda p: PROCESSED_DIR.rglob(p),
        lambda p: DISCARDED_DIR.rglob(p),
    ]
    candidates: List[Path] = []
    pattern = f"*{code}*.pdf"
    for finder in patterns:
        try:
            candidates.extend(list(finder(pattern)))
        except Exception:
            continue
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def _remove_csv_row(school_code: str) -> None:
    if not CSV_FILE.exists():
        return
    lines = CSV_FILE.read_text().splitlines()
    kept = [line for line in lines if not line.startswith(f"{school_code},")]
    if kept == lines:
        return
    content = "\n".join(kept)
    if content:
        content += "\n"
    CSV_FILE.write_text(content)


def _scrub_status_files(school_code: str) -> None:
    for path in STATUS_FILES:
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text())
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        changed = False
        for key in ("reviewed", "failed"):
            if key in data and isinstance(data[key], list):
                before = len(data[key])
                data[key] = [x for x in data[key] if x != school_code]
                changed = changed or (len(data[key]) != before)
        if changed:
            path.write_text(json.dumps(data, indent=2))


def _remove_analysis_artifacts(school_code: str) -> List[Path]:
    removed: List[Path] = []
    candidates = [
        ANALYSIS_DIR / f"{school_code}_PTOF_analysis.json",
        ANALYSIS_DIR / f"{school_code}_analysis.json",
        ANALYSIS_DIR / f"{school_code}_PTOF_analysis.md",
        ANALYSIS_DIR / f"{school_code}_analysis.md",
        MD_DIR / f"{school_code}_ptof.md",
    ]
    for path in candidates:
        if path.exists():
            path.unlink()
            removed.append(path)
    return removed


def _is_under(path: Path, parent: Path) -> bool:
    try:
        return path.resolve().is_relative_to(parent.resolve())
    except Exception:
        return False


def _should_remove(result: str) -> bool:
    return result in {
        ValidationResult.NOT_PTOF.value,
        ValidationResult.TOO_SHORT.value,
        ValidationResult.CORRUPTED.value,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Remove analysis for non-PTOF documents")
    parser.add_argument("--limit", type=int, default=200, help="Max files to process")
    parser.add_argument("--target", help="Specific school code to process")
    parser.add_argument("--dry-run", action="store_true", help="Do not delete or move files")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM for ambiguous cases")
    parser.add_argument("--no-move-pdf", action="store_true", help="Do not move PDFs to discarded")
    args = parser.parse_args()

    validator = PTOFValidator()

    analysis_files = list(ANALYSIS_DIR.glob("*_analysis.json"))
    seen: Set[str] = set()
    candidates: List[Path] = []
    for path in analysis_files:
        school_code = path.name.split("_")[0]
        if args.target and school_code != args.target:
            continue
        if school_code in seen:
            continue
        seen.add(school_code)
        candidates.append(path)

    logger.info(f"Found {len(candidates)} analyses to check")

    processed = 0
    removed_count = 0
    for path in candidates:
        if processed >= args.limit:
            break
        school_code = path.name.split("_")[0]
        processed += 1

        pdf_path = _find_pdf_for_code(school_code)
        if not pdf_path or not pdf_path.exists():
            logger.warning(f"{school_code}: PDF not found, skipping")
            continue

        report = validator.validate(pdf_path, use_llm_if_ambiguous=not args.no_llm)
        logger.info(f"{school_code}: validation result = {report.result} ({report.reason})")

        if not _should_remove(report.result):
            continue

        entry = {
            "school_code": school_code,
            "pdf_path": str(pdf_path),
            "result": report.result,
            "reason": report.reason,
            "confidence": report.confidence,
            "timestamp": datetime.now().isoformat(),
        }

        if args.dry_run:
            _append_review_log({**entry, "action": "dry_run"})
            continue

        if not args.no_move_pdf and not _is_under(pdf_path, DISCARDED_DIR):
            validator.discard(pdf_path, report)

        removed = _remove_analysis_artifacts(school_code)
        _remove_csv_row(school_code)
        _scrub_status_files(school_code)

        entry["removed_paths"] = [str(p) for p in removed]
        entry["action"] = "removed"
        _append_review_log(entry)
        removed_count += 1

    logger.info(f"Completed. Removed analyses: {removed_count}")


if __name__ == "__main__":
    main()
