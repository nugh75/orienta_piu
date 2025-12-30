#!/usr/bin/env python3
"""
Stratified incremental cycle for PTOF downloads and analysis.

Goal: keep a representative sample (MIUR-proportional) and grow it
incrementally by a fixed number of valid PTOF per stratum.
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import math
import random
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.downloaders import ptof_downloader as dl


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"
LOG_DIR = BASE_DIR / "logs"
ANALYSIS_CSV = DATA_DIR / "analysis_summary.csv"

STATE_FILE = DATA_DIR / "strata_cycle_state.json"
REGISTRY_FILE = DATA_DIR / "strata_cycle_registry.jsonl"
FAIL_REPORT = REPORTS_DIR / "strata_failures.csv"


DEFAULT_TARGET_TOTAL = 6000
DEFAULT_TARGET_STEP = 300
DEFAULT_PER_STRATO_STEP = 3
DEFAULT_YIELD_GLOBAL = 0.6
RETRY_INTERVAL = 2


class RetryAwareState:
    """Download state wrapper that allows forced retries for specific codes."""

    def __init__(self, base_state: dl.DownloadState, force_codes: Optional[set[str]] = None):
        self._base = base_state
        self._force_codes = set(force_codes or [])

    def is_downloaded(self, code: str) -> bool:
        if code in self._force_codes:
            return False
        return self._base.is_downloaded(code)

    def is_rejected(self, code: str) -> bool:
        if code in self._force_codes:
            return False
        return self._base.is_rejected(code)

    def __getattr__(self, name: str):
        return getattr(self._base, name)


def setup_logging(log_dir: Path) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = log_dir / f"strata_cycle_{timestamp}.log"

    logger = logging.getLogger("strata_cycle")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

    logger.addHandler(console)
    logger.addHandler(file_handler)
    return logger


def load_cycle_state() -> Dict:
    if STATE_FILE.exists():
        with STATE_FILE.open(encoding="utf-8") as f:
            return json.load(f)
    return {
        "cycle_id": 0,
        "target_total": DEFAULT_TARGET_TOTAL,
        "yield_global": DEFAULT_YIELD_GLOBAL,
        "yield_by_strato": {},
        "failures": {},
    }


def save_cycle_state(state: Dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with STATE_FILE.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=True)


def append_registry(entry: Dict) -> None:
    REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with REGISTRY_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=True) + "\n")


def append_failures(rows: List[Dict[str, str]]) -> None:
    if not rows:
        return
    FAIL_REPORT.parent.mkdir(parents=True, exist_ok=True)
    file_exists = FAIL_REPORT.exists()
    with FAIL_REPORT.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["cycle_id", "school_code", "strato", "reason", "attempt", "last_seen"],
        )
        if not file_exists:
            writer.writeheader()
        for row in rows:
            writer.writerow(row)


def normalize_area(value: str) -> Optional[str]:
    if not value:
        return None
    v = value.strip().upper()
    v = v.replace("-", " ").replace("_", " ")
    v = " ".join(v.split())
    mapping = {
        "NORD OVEST": "NORD OVEST",
        "NORD EST": "NORD EST",
        "CENTRO": "CENTRO",
        "SUD": "SUD",
        "ISOLE": "ISOLE",
        "ISOLA": "ISOLE",
    }
    return mapping.get(v)


def normalize_tipo(value: str) -> Optional[str]:
    if not value:
        return None
    v = value.strip().lower()
    if v.startswith("stat"):
        return "STAT"
    if v.startswith("par"):
        return "PAR"
    return None


def normalize_territorio(value: str) -> Optional[str]:
    if not value:
        return None
    v = value.strip().lower()
    if "non" in v:
        return "NON_METRO"
    if "metro" in v or "metropolit" in v:
        return "METRO"
    return None


def normalize_grado(value: str) -> Optional[str]:
    if not value:
        return None
    v = value.strip().upper()
    if "INFANZIA" in v or "MATERNA" in v:
        return "INFANZIA"
    if "PRIMARIA" in v or "ELEMENTARE" in v:
        return "PRIMARIA"
    if "PRIMO" in v or "I GRADO" in v or "1" in v:
        return "SEC_PRIMO"
    if "SECONDO" in v or "II GRADO" in v or "2" in v or "SUPERIORE" in v:
        return "SEC_SECONDO"
    return "ALTRO"


def row_to_strato(row: Dict[str, str]) -> Optional[str]:
    tipo = normalize_tipo(row.get("statale_paritaria", ""))
    area = normalize_area(row.get("area_geografica", ""))
    territorio = normalize_territorio(row.get("territorio", ""))
    grado = normalize_grado(row.get("ordine_grado", "") or row.get("tipo_scuola", ""))
    if not tipo or not area or not territorio or not grado:
        return None
    return f"{tipo}_{area}_{territorio}_{grado}"


def load_analysis_counts() -> Tuple[Dict[str, int], set[str], int]:
    counts: Dict[str, int] = defaultdict(int)
    codes: set[str] = set()
    missing = 0
    if not ANALYSIS_CSV.exists():
        return counts, codes, 0
    with ANALYSIS_CSV.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = (row.get("school_id") or "").strip()
            if code:
                codes.add(code)
            strato = row_to_strato(row)
            if not strato:
                missing += 1
                continue
            counts[strato] += 1
    return counts, codes, missing


def compute_targets(miur_counts: Dict[str, int], target_total: int) -> Dict[str, int]:
    total = sum(miur_counts.values())
    if total == 0:
        return {k: 0 for k in miur_counts}
    target_total = min(target_total, total)
    raw = {k: (target_total * v) / total for k, v in miur_counts.items()}
    base = {k: min(int(math.floor(raw[k])), miur_counts[k]) for k in miur_counts}
    remainder = target_total - sum(base.values())
    if remainder > 0:
        ranked = sorted(
            miur_counts.keys(),
            key=lambda k: (raw[k] - base[k]),
            reverse=True,
        )
        for key in ranked:
            if remainder == 0:
                break
            if base[key] < miur_counts[key]:
                base[key] += 1
                remainder -= 1
    if remainder > 0:
        ranked = sorted(
            miur_counts.keys(),
            key=lambda k: (miur_counts[k] - base[k]),
            reverse=True,
        )
        for key in ranked:
            if remainder == 0:
                break
            capacity = miur_counts[key] - base[key]
            if capacity <= 0:
                continue
            add = min(capacity, remainder)
            base[key] += add
            remainder -= add
    return base


def smooth_yield(prev: float, new: float, alpha: float = 0.4) -> float:
    value = (alpha * new) + ((1 - alpha) * prev)
    return max(0.2, min(0.95, round(value, 3)))


def classify_result(result: dl.DownloadResult) -> str:
    msg = (result.message or "").lower()
    msg = (
        msg.replace("\u00e0", "a")
        .replace("\u00e8", "e")
        .replace("\u00ec", "i")
        .replace("\u00f2", "o")
        .replace("\u00f9", "u")
    )
    if result.success:
        if "gia scaricato" in msg or "file gia presente" in msg:
            return "already_done"
        return "downloaded"
    if "non ptof" in msg:
        return "rejected"
    if "gia rifiutato" in msg:
        return "skipped_rejected"
    return "failed"


def call_workflow(logger: logging.Logger) -> None:
    logger.info("RUN workflow_notebook.py")
    subprocess.run([sys.executable, "workflow_notebook.py"], cwd=BASE_DIR, check=False)


def rebuild_csv(logger: logging.Logger) -> None:
    logger.info("REBUILD analysis_summary.csv (rebuild_csv_clean)")
    subprocess.run(
        [sys.executable, "-m", "src.processing.rebuild_csv_clean"],
        cwd=BASE_DIR,
        check=False,
    )


def cap_selected_by_strato(
    selected_by_strato: Dict[str, List[str]],
    max_total: int,
) -> Tuple[Dict[str, List[str]], List[str]]:
    if max_total <= 0:
        return {}, []
    strata = [s for s in sorted(selected_by_strato.keys()) if selected_by_strato.get(s)]
    if not strata:
        return {}, []
    indexes = {s: 0 for s in strata}
    final_codes: List[str] = []
    while len(final_codes) < max_total:
        progressed = False
        for strato in strata:
            codes = selected_by_strato[strato]
            idx = indexes[strato]
            if idx < len(codes):
                final_codes.append(codes[idx])
                indexes[strato] += 1
                progressed = True
                if len(final_codes) >= max_total:
                    break
        if not progressed:
            break
    final_set = set(final_codes)
    capped_by_strato: Dict[str, List[str]] = {}
    for strato, codes in selected_by_strato.items():
        kept = [code for code in codes if code in final_set]
        if kept:
            capped_by_strato[strato] = kept
    return capped_by_strato, final_codes


def main() -> int:
    parser = argparse.ArgumentParser(description="Ciclo incrementale stratificato PTOF")
    parser.add_argument("--target-total", type=int, default=DEFAULT_TARGET_TOTAL)
    parser.add_argument("--target-step", type=int, default=DEFAULT_TARGET_STEP)
    parser.add_argument("--per-strato-step", type=int, default=DEFAULT_PER_STRATO_STEP)
    parser.add_argument("--yield-global", type=float, default=DEFAULT_YIELD_GLOBAL)
    parser.add_argument("--max-cycles", type=int, default=1)
    parser.add_argument("--max-downloads", type=int, default=0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--skip-analysis", action="store_true", help="Salta workflow e rebuild CSV")
    args = parser.parse_args()

    logger = setup_logging(LOG_DIR)
    logger.info("START ciclo stratificato incrementale")

    state = load_cycle_state()
    rng = random.Random(args.seed)

    # Load MIUR schools
    schools: List[dl.SchoolRecord] = []
    if dl.ANAGRAFE_STAT.exists():
        logger.info(f"LOAD MIUR statali: {dl.ANAGRAFE_STAT.name}")
        schools.extend(dl.load_schools_statali(dl.ANAGRAFE_STAT))
    else:
        logger.error(f"ERROR file mancante: {dl.ANAGRAFE_STAT}")
    if dl.ANAGRAFE_PAR.exists():
        logger.info(f"LOAD MIUR paritarie: {dl.ANAGRAFE_PAR.name}")
        schools.extend(dl.load_schools_paritarie(dl.ANAGRAFE_PAR))
    else:
        logger.error(f"ERROR file mancante: {dl.ANAGRAFE_PAR}")
    if not schools:
        logger.error("ERROR nessuna scuola MIUR caricata.")
        return 1

    strata_all = dl.stratify_schools(schools)
    miur_counts = {k: len(v) for k, v in strata_all.items()}
    miur_total = sum(miur_counts.values())
    logger.info(f"MIUR totale scuole: {miur_total} | strati: {len(miur_counts)}")

    cycle_id = state.get("cycle_id", 0)
    target_total = int(state.get("target_total", args.target_total))
    if target_total < args.target_total:
        target_total = args.target_total

    yield_global = float(state.get("yield_global", args.yield_global))
    if yield_global <= 0:
        yield_global = args.yield_global

    for _ in range(args.max_cycles):
        cycle_id += 1
        logger.info("=" * 80)
        logger.info(f"CICLO {cycle_id} | target_totale={target_total}")

        targets = compute_targets(miur_counts, target_total)
        current_counts, valid_codes, missing_rows = load_analysis_counts()
        if missing_rows:
            logger.info(f"WARN righe senza strato valido in CSV: {missing_rows}")

        deficits = {k: max(0, targets.get(k, 0) - current_counts.get(k, 0)) for k in targets}
        total_deficit = sum(deficits.values())
        logger.info(f"Deficit totale: {total_deficit}")

        if total_deficit == 0:
            if target_total < miur_total:
                target_total = min(miur_total, target_total + args.target_step)
                logger.info(f"OK target raggiunto, incremento target_totale -> {target_total}")
                targets = compute_targets(miur_counts, target_total)
                deficits = {k: max(0, targets.get(k, 0) - current_counts.get(k, 0)) for k in targets}
                total_deficit = sum(deficits.values())
            else:
                logger.info("OK target totale gia raggiunto sull'universo MIUR. Stop.")
                state["cycle_id"] = cycle_id - 1
                save_cycle_state(state)
                return 0

        request_valid = {
            k: min(args.per_strato_step, deficit) for k, deficit in deficits.items() if deficit > 0
        }
        logger.info(f"Strati in deficit: {len(request_valid)}")

        # Failures and retry logic
        failure_state = state.get("failures", {})
        retry_codes = {
            code for code, info in failure_state.items()
            if (cycle_id - int(info.get("last_cycle", 0))) >= RETRY_INTERVAL
        }

        # Build candidate pools
        downloaded_state = dl.DownloadState(dl.STATE_FILE)
        downloaded_codes = set(downloaded_state.state.get("downloaded", {}).keys())
        rejected_codes = set(downloaded_state.state.get("rejected", {}).keys())

        excluded_due_to_fail = 0
        excluded_downloaded = 0
        excluded_valid = 0

        candidates_by_strato: Dict[str, List[dl.SchoolRecord]] = defaultdict(list)
        seen_codes: set[str] = set()
        for school in schools:
            code = school.codice
            if code in seen_codes:
                continue
            seen_codes.add(code)

            if code in valid_codes:
                excluded_valid += 1
                continue
            if code in failure_state and code not in retry_codes:
                excluded_due_to_fail += 1
                continue
            if code in downloaded_codes and code not in retry_codes:
                excluded_downloaded += 1
                continue
            if code in rejected_codes and code not in retry_codes:
                excluded_downloaded += 1
                continue

            candidates_by_strato[school.strato].append(school)

        logger.info(
            f"Esclusi: validi={excluded_valid} "
            f"downloaded/rejected={excluded_downloaded} "
            f"fail_pending={excluded_due_to_fail}"
        )

        # Compute quotas per strato
        yield_by_strato = state.get("yield_by_strato", {})
        quota_per_strato: Dict[str, int] = {}
        for strato, needed_valid in request_valid.items():
            yield_value = float(yield_by_strato.get(strato, yield_global))
            if yield_value <= 0:
                yield_value = yield_global
            quota = int(math.ceil(needed_valid / yield_value))
            quota_per_strato[strato] = max(0, quota)

        # Select schools per strato
        selected: List[dl.SchoolRecord] = []
        selected_by_strato: Dict[str, List[str]] = defaultdict(list)
        for strato, quota in quota_per_strato.items():
            if quota <= 0:
                continue
            pool = candidates_by_strato.get(strato, [])
            if not pool:
                logger.info(f"WARN nessun candidato per {strato}")
                continue

            retry_pool = [s for s in pool if s.codice in retry_codes]
            remaining_pool = [s for s in pool if s.codice not in retry_codes]
            picked: List[dl.SchoolRecord] = []

            if retry_pool:
                retry_pool_sorted = sorted(retry_pool, key=lambda s: s.codice)
                picked.extend(retry_pool_sorted[:quota])

            remaining = quota - len(picked)
            if remaining > 0:
                if len(remaining_pool) <= remaining:
                    picked.extend(remaining_pool)
                else:
                    picked.extend(rng.sample(remaining_pool, remaining))

            for school in picked:
                selected.append(school)
                selected_by_strato[strato].append(school.codice)

            if len(picked) < quota:
                logger.info(
                    f"WARN {strato}: quota {quota} ma candidati {len(pool)} -> selezionati {len(picked)}"
                )

        total_selected = len(selected)
        capped_total = 0
        max_attempts = 0
        if args.max_downloads:
            max_attempts = int(math.ceil(args.max_downloads / max(yield_global, 0.1)))
            if total_selected > max_attempts:
                before_cap = total_selected
                capped_by_strato, capped_codes = cap_selected_by_strato(
                    selected_by_strato,
                    max_attempts,
                )
                capped_total = len(capped_codes)
                if capped_total:
                    code_to_school = {s.codice: s for s in selected}
                    selected = [code_to_school[c] for c in capped_codes if c in code_to_school]
                    selected_by_strato = capped_by_strato
                    total_selected = len(selected)
                logger.info(
                    "Cap attempts: %s -> %s (max_downloads=%s max_attempts=%s)",
                    before_cap,
                    total_selected,
                    args.max_downloads,
                    max_attempts,
                )
        logger.info(f"Scuole selezionate per download: {total_selected}")

        for strato in sorted(selected_by_strato):
            logger.debug(
                f"{strato}: selezionati {len(selected_by_strato[strato])} | "
                f"codes={','.join(selected_by_strato[strato])}"
            )

        if total_selected == 0:
            logger.info("INFO nessuna scuola selezionata. Registro ciclo e stop.")
            entry = {
                "status": "no-op",
                "cycle_id": cycle_id,
                "timestamp": datetime.now().isoformat(),
                "target_total": target_total,
                "per_strato_step": args.per_strato_step,
                "target_per_strato": targets,
                "current_per_strato": current_counts,
                "deficit_per_strato": deficits,
                "selected_total": 0,
                "selected_per_strato": selected_by_strato,
            }
            append_registry(entry)
            state["cycle_id"] = cycle_id
            state["target_total"] = target_total
            save_cycle_state(state)
            return 0

        start_entry = {
            "status": "started",
            "cycle_id": cycle_id,
            "timestamp": datetime.now().isoformat(),
            "target_total": target_total,
            "target_step": args.target_step,
            "per_strato_step": args.per_strato_step,
            "max_downloads": args.max_downloads,
            "max_attempts": max_attempts,
            "miur_total": miur_total,
            "miur_strata": len(miur_counts),
            "yield_global": yield_global,
            "yield_by_strato": yield_by_strato,
            "target_per_strato": targets,
            "current_per_strato": current_counts,
            "deficit_per_strato": deficits,
            "request_valid_per_strato": request_valid,
            "quota_download_per_strato": quota_per_strato,
            "selected_total": total_selected,
            "selected_total_before_cap": capped_total or total_selected,
            "selected_per_strato": selected_by_strato,
        }
        append_registry(start_entry)

        # Download phase
        failure_rows: List[Dict[str, str]] = []
        download_attempts = 0
        download_attempts_by_strato: Dict[str, int] = defaultdict(int)
        download_results_by_strato: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"downloaded": 0, "failed": 0, "rejected": 0, "already_done": 0}
        )
        downloaded_success = 0
        cap_reached = False

        retry_state = RetryAwareState(downloaded_state, force_codes=retry_codes)
        downloader = dl.PTOFDownloader(retry_state, dl.DOWNLOAD_DIR)

        for idx, school in enumerate(selected, 1):
            result = downloader.download_ptof(school)
            status = classify_result(result)

            if status != "already_done":
                download_attempts += 1
                download_attempts_by_strato[school.strato] += 1

            if status == "downloaded":
                download_results_by_strato[school.strato]["downloaded"] += 1
                downloaded_success += 1
                failure_state.pop(school.codice, None)
            elif status == "already_done":
                download_results_by_strato[school.strato]["already_done"] += 1
            elif status == "rejected":
                download_results_by_strato[school.strato]["rejected"] += 1
                info = failure_state.get(school.codice, {"attempts": 0})
                info["attempts"] = int(info.get("attempts", 0)) + 1
                info["last_cycle"] = cycle_id
                info["last_reason"] = result.message
                info["strato"] = school.strato
                failure_state[school.codice] = info
                failure_rows.append({
                    "cycle_id": str(cycle_id),
                    "school_code": school.codice,
                    "strato": school.strato,
                    "reason": result.message,
                    "attempt": str(info["attempts"]),
                    "last_seen": datetime.now().isoformat(),
                })
            elif status == "failed":
                download_results_by_strato[school.strato]["failed"] += 1
                info = failure_state.get(school.codice, {"attempts": 0})
                info["attempts"] = int(info.get("attempts", 0)) + 1
                info["last_cycle"] = cycle_id
                info["last_reason"] = result.message
                info["strato"] = school.strato
                failure_state[school.codice] = info
                failure_rows.append({
                    "cycle_id": str(cycle_id),
                    "school_code": school.codice,
                    "strato": school.strato,
                    "reason": result.message,
                    "attempt": str(info["attempts"]),
                    "last_seen": datetime.now().isoformat(),
                })

            if idx % 25 == 0 or idx == total_selected:
                downloaded_state.save()
                logger.info(
                    f"Download progress {idx}/{total_selected} | "
                    f"OK {downloader.stats['downloaded']} | "
                    f"REJECT {downloader.stats['rejected']} | "
                    f"FAIL {downloader.stats['failed']} | "
                    f"SKIP {downloader.stats['already_done']}"
                )

            if args.max_downloads and downloaded_success >= args.max_downloads:
                cap_reached = True
                logger.info(
                    "Download cap reached: %s successful downloads (limit=%s)",
                    downloaded_success,
                    args.max_downloads,
                )
                break

        downloaded_state.save()
        append_failures(failure_rows)

        # Analysis phase
        if not args.skip_analysis:
            call_workflow(logger)
            rebuild_csv(logger)

        post_counts, _, missing_rows_post = load_analysis_counts()
        if missing_rows_post:
            logger.info(f"WARN righe senza strato valido dopo workflow: {missing_rows_post}")

        delta_per_strato: Dict[str, int] = {}
        for strato in targets:
            delta_per_strato[strato] = max(0, post_counts.get(strato, 0) - current_counts.get(strato, 0))

        total_delta = sum(delta_per_strato.values())
        logger.info(f"OK nuovi PTOF validi (delta): {total_delta}")

        # Update yield estimates
        yield_updates: Dict[str, float] = {}
        total_attempts = sum(download_attempts_by_strato.values())
        if total_attempts > 0:
            cycle_yield_global = total_delta / total_attempts
            yield_global = smooth_yield(yield_global, cycle_yield_global)
        for strato, attempts in download_attempts_by_strato.items():
            if attempts < 5:
                continue
            strato_yield = delta_per_strato.get(strato, 0) / attempts if attempts else 0
            prev = float(yield_by_strato.get(strato, yield_global))
            yield_updates[strato] = smooth_yield(prev, strato_yield)
        yield_by_strato.update(yield_updates)

        # Registry entry
        entry = {
            "status": "completed",
            "cycle_id": cycle_id,
            "timestamp": datetime.now().isoformat(),
            "target_total": target_total,
            "target_step": args.target_step,
            "per_strato_step": args.per_strato_step,
            "max_downloads": args.max_downloads,
            "max_attempts": max_attempts,
            "miur_total": miur_total,
            "miur_strata": len(miur_counts),
            "yield_global": yield_global,
            "yield_by_strato": yield_by_strato,
            "target_per_strato": targets,
            "current_per_strato": current_counts,
            "deficit_per_strato": deficits,
            "request_valid_per_strato": request_valid,
            "quota_download_per_strato": quota_per_strato,
            "selected_total": total_selected,
            "selected_total_before_cap": capped_total or total_selected,
            "selected_per_strato": selected_by_strato,
            "download_attempts": download_attempts,
            "download_attempts_per_strato": dict(download_attempts_by_strato),
            "download_results_per_strato": download_results_by_strato,
            "downloaded_success": downloaded_success,
            "download_cap_reached": cap_reached,
            "valid_delta_total": total_delta,
            "valid_delta_per_strato": delta_per_strato,
        }
        append_registry(entry)

        state["cycle_id"] = cycle_id
        state["target_total"] = target_total
        state["yield_global"] = yield_global
        state["yield_by_strato"] = yield_by_strato
        state["failures"] = failure_state
        save_cycle_state(state)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
