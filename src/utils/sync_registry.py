#!/usr/bin/env python3
"""
Sync Registry - Sincronizza analysis_registry.json con i file su disco.

Fonte di verita: i file *_analysis.json presenti in analysis_results/.
Questo script:
  1. Corregge i path errati (macOS, Docker, vuoti) puntandoli al path locale
  2. Aggiunge voci per i file su disco non presenti nel registry
  3. Rimuove voci orfane (file non esistente su disco)
"""

import glob
import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))

from src.utils.analysis_registry import load_registry, save_registry

logger = logging.getLogger(__name__)

RESULTS_DIR = BASE_DIR / "analysis_results"
PTOF_MD_DIR = BASE_DIR / "ptof_md"
LOCAL_PREFIX = str(BASE_DIR) + "/"

# Path prefixes to fix (from other machines/environments)
STALE_PREFIXES = [
    "/Users/danieledragoni/git/LIste/",
    "/Users/danieledragoni/git/orienta_piu/",
    "/app/",
]


def extract_school_code(filename: str) -> str:
    """Estrae il codice meccanografico dal nome file JSON."""
    return re.sub(r"_[Pp][Tt][Oo][Ff]_analysis\.json$", "", filename)


def fix_path(old_path: str) -> tuple[str, bool]:
    """Corregge un path errato sostituendo il prefisso. Ritorna (new_path, was_fixed)."""
    if not old_path:
        return old_path, False
    for prefix in STALE_PREFIXES:
        if old_path.startswith(prefix):
            relative = old_path[len(prefix):]
            return LOCAL_PREFIX + relative, True
    return old_path, False


def sync_registry(dry_run: bool = False) -> dict:
    """
    Sincronizza il registry con i file su disco.

    Args:
        dry_run: Se True, non modifica il registry ma ritorna solo le statistiche.

    Returns:
        Dizionario con statistiche delle operazioni.
    """
    stats = {
        "paths_fixed": 0,
        "empty_paths_filled": 0,
        "entries_added": 0,
        "entries_removed": 0,
        "removed_codes": [],
        "total_before": 0,
        "total_after": 0,
    }

    registry = load_registry()
    analyzed = registry.get("analyzed_files", {})
    stats["total_before"] = len(analyzed)

    # Scan JSON files on disk
    json_files = glob.glob(str(RESULTS_DIR / "*_analysis.json"))
    disk_codes = {}
    for fp in json_files:
        fname = os.path.basename(fp)
        code = extract_school_code(fname)
        disk_codes[code] = fp

    logger.info(f"Registry entries: {len(analyzed)}, JSON files on disk: {len(disk_codes)}")

    # --- Step 1: Fix stale paths ---
    for code, entry in analyzed.items():
        for field in ("json_path", "md_path"):
            old = entry.get(field, "")
            new, was_fixed = fix_path(old)
            if was_fixed:
                if not dry_run:
                    entry[field] = new
                stats["paths_fixed"] += 1

    # --- Step 2: Fill empty json_path where file exists on disk ---
    for code, entry in analyzed.items():
        jp = entry.get("json_path", "")
        if not jp or not jp.strip():
            if code in disk_codes:
                if not dry_run:
                    entry["json_path"] = disk_codes[code]
                    # Also try to fill md_path
                    md_candidate = str(PTOF_MD_DIR / f"{code}_ptof.md")
                    if os.path.exists(md_candidate) and not entry.get("md_path"):
                        entry["md_path"] = md_candidate
                stats["empty_paths_filled"] += 1

    # --- Step 3: Add missing entries (on disk but not in registry) ---
    registry_codes = set(analyzed.keys())
    missing_codes = set(disk_codes.keys()) - registry_codes

    for code in sorted(missing_codes):
        json_path = disk_codes[code]
        md_candidate = str(PTOF_MD_DIR / f"{code}_ptof.md")
        md_path = md_candidate if os.path.exists(md_candidate) else ""
        mtime = os.path.getmtime(json_path)
        analyzed_at = datetime.fromtimestamp(mtime).isoformat()

        if not dry_run:
            analyzed[code] = {
                "pdf_hash": "reconstructed",
                "pdf_name": f"{code}_PTOF.pdf",
                "pdf_size": 0,
                "analyzed_at": analyzed_at,
                "json_path": json_path,
                "workflow_version": "1.0",
                "md_path": md_path,
            }
        stats["entries_added"] += 1

    # --- Step 4: Remove orphaned entries (in registry but not on disk) ---
    orphan_codes = set(analyzed.keys()) - set(disk_codes.keys())
    for code in sorted(orphan_codes):
        entry = analyzed[code]
        jp = entry.get("json_path", "")
        # Double check: the file truly does not exist at the (now-fixed) path
        if not jp or not os.path.exists(jp):
            stats["removed_codes"].append(code)
            if not dry_run:
                del analyzed[code]
            stats["entries_removed"] += 1

    # --- Save ---
    if not dry_run:
        registry["analyzed_files"] = analyzed
        save_registry(registry)

    stats["total_after"] = len(analyzed) if not dry_run else stats["total_before"] + stats["entries_added"] - stats["entries_removed"]

    return stats


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    import argparse
    parser = argparse.ArgumentParser(description="Sincronizza analysis_registry.json con i file su disco")
    parser.add_argument("--dry-run", action="store_true", help="Mostra cosa cambierebbe senza modificare")
    args = parser.parse_args()

    if args.dry_run:
        logger.info("DRY RUN - nessuna modifica verra applicata")

    stats = sync_registry(dry_run=args.dry_run)

    logger.info(f"Path corretti: {stats['paths_fixed']}")
    logger.info(f"Path vuoti riempiti: {stats['empty_paths_filled']}")
    logger.info(f"Voci aggiunte: {stats['entries_added']}")
    logger.info(f"Voci rimosse: {stats['entries_removed']}")
    if stats["removed_codes"]:
        logger.info(f"Codici rimossi: {stats['removed_codes']}")
    logger.info(f"Totale: {stats['total_before']} -> {stats['total_after']}")


if __name__ == "__main__":
    main()
