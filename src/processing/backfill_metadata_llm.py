#!/usr/bin/env python3
"""
Backfill missing metadata in analysis JSONs using MIUR + targeted LLM scan.
"""
import os
import sys
import glob
import logging
from pathlib import Path

# Ensure project root on path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, BASE_DIR)

# Setup logging
LOG_DIR = Path(BASE_DIR) / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / 'backfill.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

from app.agentic_pipeline import enrich_json_metadata, fill_missing_metadata_with_llm
from src.utils.school_code_parser import extract_canonical_code

RESULTS_DIR = "analysis_results"
MD_DIR = "ptof_md"


def find_md_path(school_code):
    candidates = [
        os.path.join(MD_DIR, f"{school_code}_ptof.md"),
        os.path.join(MD_DIR, f"{school_code}_PTOF.md"),
        os.path.join(MD_DIR, f"{school_code}.md"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def select_json_files(json_files):
    selected = {}
    for path in json_files:
        filename = os.path.basename(path)
        code = extract_canonical_code(filename.replace('_analysis.json', ''))
        prefer = 2 if filename.endswith('_PTOF_analysis.json') else 1
        mtime = os.path.getmtime(path)
        current = selected.get(code)
        if not current or prefer > current['prefer'] or (prefer == current['prefer'] and mtime > current['mtime']):
            selected[code] = {'path': path, 'code': code, 'prefer': prefer, 'mtime': mtime}
    return [item for item in selected.values()]


def main():
    json_files = glob.glob(os.path.join(RESULTS_DIR, '*_analysis.json'))
    if not json_files:
        print(f"No analysis JSON files found in {RESULTS_DIR}")
        return

    targets = select_json_files(json_files)
    print(f"Backfill targets: {len(targets)} files")

    updated = 0
    for item in targets:
        json_path = item['path']
        school_code = item['code']
        md_path = find_md_path(school_code)

        enrich_json_metadata(json_path, school_code, force_school_id=True, md_path=md_path)
        if fill_missing_metadata_with_llm(json_path, md_path, school_code):
            updated += 1

    print(f"Backfill complete. Files updated by LLM scan: {updated}")


if __name__ == "__main__":
    main()
