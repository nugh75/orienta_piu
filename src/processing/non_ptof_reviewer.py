#!/usr/bin/env python3
"""
Non-PTOF Reviewer - remove analysis artifacts for documents classified as not PTOF.
"""

import sys
import json
import csv
import logging
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.utils.file_utils import atomic_write
from src.validation.ptof_validator import PTOFValidator, ValidationResult, ValidationReport

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
    atomic_write(REVIEW_LOG, json.dumps(items, indent=2))


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
    atomic_write(CSV_FILE, content)


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
            atomic_write(path, json.dumps(data, indent=2))


def _remove_analysis_artifacts(school_code: str) -> List[Path]:
    removed: List[Path] = []
    base_candidates = [
        ANALYSIS_DIR / f"{school_code}_PTOF_analysis.json",
        ANALYSIS_DIR / f"{school_code}_analysis.json",
        ANALYSIS_DIR / f"{school_code}_PTOF_analysis.md",
        ANALYSIS_DIR / f"{school_code}_analysis.md",
        MD_DIR / f"{school_code}_ptof.md",
    ]
    
    candidates = []
    for p in base_candidates:
        candidates.append(p)
        candidates.append(p.with_suffix(p.suffix + ".bak"))

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


def _get_sorted_candidates(limit: int, target: Optional[str] = None, max_score: float = 2.0) -> List[Tuple[Path, float]]:
    """
    Returns a list of (path, score) tuples to check, sorted by score (ascending).
    Only includes schools with score <= max_score (default 2.0).
    Low scores are prioritized as they are more likely to be false positives or poor documents.
    """
    # 1. Get all available analysis files
    all_analyses = {
        f.name.split("_")[0]: f 
        for f in ANALYSIS_DIR.glob("*_analysis.json")
    }
    
    if target:
        if target in all_analyses:
            # If target is specified, try to find its score, otherwise default to 0
            score = 0.0
            if CSV_FILE.exists():
                try:
                    with open(CSV_FILE, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            if row.get('school_id') == target:
                                try:
                                    score = float(row.get('ptof_orientamento_maturity_index', '0'))
                                except ValueError:
                                    pass
                                break
                except Exception:
                    pass
            return [(all_analyses[target], score)]
        return []

    # 2. Read CSV to get scores
    scored_schools: List[Tuple[str, float]] = []
    if CSV_FILE.exists():
        try:
            with open(CSV_FILE, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    code = row.get('school_id', '')
                    score_str = row.get('ptof_orientamento_maturity_index', '0')
                    try:
                        score = float(score_str)
                    except ValueError:
                        score = 0.0
                    
                    # Filter by max_score
                    if score <= max_score and code in all_analyses:
                        scored_schools.append((code, score))
        except Exception as e:
            logger.error(f"Error reading CSV: {e}")

    # 3. Sort by score ascending
    scored_schools.sort(key=lambda x: x[1])
    
    # 4. Build final list
    candidates: List[Tuple[Path, float]] = []
    seen_codes: Set[str] = set()
    
    # Add sorted schools first
    for code, score in scored_schools:
        if code in all_analyses:
            candidates.append((all_analyses[code], score))
            seen_codes.add(code)
            
    return candidates


def main() -> None:
    parser = argparse.ArgumentParser(description="Remove analysis for non-PTOF documents")
    parser.add_argument("--limit", type=int, default=200, help="Max files to process")
    parser.add_argument("--target", help="Specific school code to process")
    parser.add_argument("--dry-run", action="store_true", help="Do not delete or move files")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM for ambiguous cases")
    parser.add_argument("--no-move-pdf", action="store_true", help="Do not move PDFs to discarded")
    parser.add_argument("--max-score", type=float, default=2.0, help="Max score to consider (default 2.0)")
    args = parser.parse_args()

    validator = PTOFValidator()

    candidates = _get_sorted_candidates(args.limit, args.target, args.max_score)
    logger.info(f"Found {len(candidates)} analyses to check (score <= {args.max_score})")

    processed = 0
    removed_count = 0
    for path, score in candidates:
        if processed >= args.limit:
            break
        school_code = path.name.split("_")[0]
        processed += 1

        pdf_path = _find_pdf_for_code(school_code)
        if not pdf_path or not pdf_path.exists():
            logger.warning(f"{school_code}: PDF not found, skipping")
            continue

        logger.info(f"Checking {school_code} (Score: {score}, PDF: {pdf_path.name})...")
        
        # FORCE DELETE for low scores (<= 2.0)
        # If score is <= 2.0, we delete it regardless of validation result.
        if score <= 2.0:
            logger.info(f"🚫 Force removing {school_code}: Score {score} <= 2.0")
            # Create a dummy report to trigger removal
            report = ValidationReport(
                file_path=str(pdf_path),
                file_name=pdf_path.name,
                result=ValidationResult.NOT_PTOF.value,
                confidence=1.0,
                phase="score_check",
                reason=f"Score {score} too low (<= 2.0)"
            )
        else:
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

    if removed_count > 0 and not args.dry_run:
        logger.info("🔄 Refreshing CSV...")
        try:
            subprocess.run([sys.executable, "-m", "src.processing.rebuild_csv_clean"], check=True)
            logger.info("✅ CSV refreshed successfully")
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Error refreshing CSV: {e}")


if __name__ == "__main__":
    main()
