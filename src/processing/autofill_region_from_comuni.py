#!/usr/bin/env python3
"""
Auto-fill missing region/province/area metadata in analysis JSON files
using data/comuni_italiani.json (via ComuniDatabase).

Only fills missing/ND fields; existing values are preserved.
"""
import json
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.utils.comuni_database import ComuniDatabase
from src.utils.constants import SIGLA_PROVINCIA_MAP, normalize_area_geografica, get_territorio
from src.utils.school_code_parser import extract_canonical_code


RESULTS_DIR = BASE_DIR / "analysis_results"
MISSING_VALUES = {"", "nd", "n/d", "n/a", "null", "none", "nan", "non specificato"}


def is_missing(value) -> bool:
    if value is None:
        return True
    raw = str(value).strip()
    if not raw:
        return True
    return raw.lower() in MISSING_VALUES


def is_valid_school_code(value: str) -> bool:
    if not value:
        return False
    code = extract_canonical_code(str(value))
    return len(code) == 10


def apply_sigla_fallback(meta: dict, sigla: str) -> bool:
    if not sigla:
        return False
    info = SIGLA_PROVINCIA_MAP.get(sigla)
    if not info:
        return False
    provincia, regione, area = info
    changed = False
    if is_missing(meta.get("provincia")):
        meta["provincia"] = provincia
        changed = True
    if is_missing(meta.get("regione")):
        meta["regione"] = regione
        changed = True
    if is_missing(meta.get("area_geografica")):
        meta["area_geografica"] = area
        changed = True
    return changed


def main() -> int:
    json_files = sorted(RESULTS_DIR.glob("*_analysis.json"))
    if not json_files:
        print("No analysis JSON files found.")
        return 0

    comuni_db = ComuniDatabase()

    updated = 0
    updated_from_comuni = 0
    updated_from_sigla = 0
    skipped = 0
    not_found = 0

    for json_path in json_files:
        try:
            with json_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            skipped += 1
            continue

        meta = data.setdefault("metadata", {})
        school_code_raw = json_path.stem.replace("_analysis", "")
        school_code = extract_canonical_code(school_code_raw)
        sigla = school_code[:2] if is_valid_school_code(school_code) else ""

        changed = False

        if school_code and not is_valid_school_code(meta.get("school_id")):
            meta["school_id"] = school_code
            changed = True

        provincia = meta.get("provincia")
        provincia_fallback = None
        if is_missing(provincia) and sigla in SIGLA_PROVINCIA_MAP:
            provincia_fallback = SIGLA_PROVINCIA_MAP[sigla][0]

        comune = meta.get("comune")
        comune_info = None
        if not is_missing(comune):
            comune_info = comuni_db.get_comune_info(
                comune,
                provincia if not is_missing(provincia) else provincia_fallback
            )

        if comune_info:
            if is_missing(meta.get("provincia")):
                meta["provincia"] = comune_info["provincia"]
                changed = True
            if is_missing(meta.get("regione")):
                meta["regione"] = comune_info["regione"]
                changed = True
            if is_missing(meta.get("area_geografica")):
                meta["area_geografica"] = comune_info["area_geografica"]
                changed = True
            if changed:
                updated_from_comuni += 1
        else:
            if not is_missing(comune):
                not_found += 1
            if apply_sigla_fallback(meta, sigla):
                changed = True
                updated_from_sigla += 1

        if (is_missing(meta.get("area_geografica"))
                and (not is_missing(meta.get("regione")) or sigla)):
            normalized = normalize_area_geografica(
                meta.get("area_geografica"),
                regione=meta.get("regione"),
                provincia_sigla=sigla
            )
            if not is_missing(normalized):
                meta["area_geografica"] = normalized
                changed = True

        if is_missing(meta.get("territorio")) and not is_missing(meta.get("provincia")):
            meta["territorio"] = get_territorio(meta.get("provincia"))
            changed = True

        if changed:
            with json_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            updated += 1

    print(f"Processed {len(json_files)} files")
    print(f"Updated {updated} files")
    print(f"Updated from comuni: {updated_from_comuni}")
    print(f"Updated from sigla: {updated_from_sigla}")
    print(f"Not found in comuni (by name): {not_found}")
    print(f"Skipped (invalid JSON): {skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
