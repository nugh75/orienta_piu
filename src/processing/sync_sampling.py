#!/usr/bin/env python3
"""
Sincronizza i dati del campionamento con lo stato reale dei download.

Questo script:
1. Legge download_state.json per vedere cosa è effettivamente scaricato
2. Aggiorna strata_cycle_state.json con i conteggi corretti
3. Ricalcola yield_global e yield_by_strato

Uso:
    python -m src.processing.sync_sampling [--dry-run]
"""

import json
import argparse
import logging
from pathlib import Path
from datetime import datetime
from collections import defaultdict

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DOWNLOAD_STATE = DATA_DIR / "download_state.json"
STRATA_STATE = DATA_DIR / "strata_cycle_state.json"
CAMPIONE_FILE = DATA_DIR / "campione_stratificato.json"
PTOF_INBOX = BASE_DIR / "ptof_inbox"
PTOF_DISCARDED = BASE_DIR / "ptof_discarded"
PTOF_PROCESSED = BASE_DIR / "ptof_processed"
ANALYSIS_DIR = BASE_DIR / "analysis_results"
ANALYSIS_REGISTRY = DATA_DIR / "analysis_registry.json"


def load_json(path: Path) -> dict:
    """Carica un file JSON."""
    if not path.exists():
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(path: Path, data: dict):
    """Salva un file JSON."""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_strato_from_code(code: str, campione: list) -> str:
    """Trova lo strato di una scuola dal campione."""
    for school in campione:
        if school.get('CODICESCUOLA') == code:
            return school.get('strato', 'UNKNOWN')
    return 'UNKNOWN'


def sync_sampling(dry_run: bool = False):
    """Sincronizza i dati del campionamento."""

    logger.info("=" * 60)
    logger.info("🔄 SINCRONIZZAZIONE DATI CAMPIONAMENTO")
    logger.info("=" * 60)

    # Carica dati
    download_state = load_json(DOWNLOAD_STATE)
    strata_state = load_json(STRATA_STATE)
    campione = load_json(CAMPIONE_FILE) if CAMPIONE_FILE.exists() else []

    # Estrai dati download
    downloaded = download_state.get('downloaded', {})
    failed = download_state.get('failed', {})

    # Conta PDF effettivamente presenti in inbox
    pdf_in_inbox = set()
    if PTOF_INBOX.exists():
        for f in PTOF_INBOX.glob("*.pdf"):
            code = f.stem.replace("_PTOF", "")
            pdf_in_inbox.add(code)

    # Conta analisi completate
    analyzed = set()
    if ANALYSIS_DIR.exists():
        for f in ANALYSIS_DIR.glob("*_analysis.json"):
            code = f.stem.replace("_PTOF_analysis", "")
            analyzed.add(code)

    logger.info(f"\n📊 STATO ATTUALE:")
    logger.info(f"   Download registrati:  {len(downloaded)}")
    logger.info(f"   Download falliti:     {len(failed)}")
    logger.info(f"   PDF in inbox:         {len(pdf_in_inbox)}")
    logger.info(f"   Analisi completate:   {len(analyzed)}")
    logger.info(f"   Scuole nel campione:  {len(campione)}")

    # Calcola statistiche per strato
    stats_by_strato = defaultdict(lambda: {
        'downloaded': 0,
        'failed': 0,
        'analyzed': 0,
        'total_in_campione': 0
    })

    # Conta scuole nel campione per strato
    campione_codes = set()
    for school in campione:
        code = school.get('CODICESCUOLA')
        strato = school.get('strato', 'UNKNOWN')
        if code:
            campione_codes.add(code)
            stats_by_strato[strato]['total_in_campione'] += 1

    # Conta downloaded per strato
    for code, info in downloaded.items():
        strato = info.get('strato', get_strato_from_code(code, campione))
        stats_by_strato[strato]['downloaded'] += 1
        if code in analyzed:
            stats_by_strato[strato]['analyzed'] += 1

    # Conta failed per strato
    for code, info in failed.items():
        strato = info.get('strato', get_strato_from_code(code, campione))
        stats_by_strato[strato]['failed'] += 1

    # Calcola yield globale e per strato
    total_attempts = len(downloaded) + len(failed)
    total_success = len(downloaded)
    yield_global = total_success / total_attempts if total_attempts > 0 else 0

    yield_by_strato = {}
    for strato, stats in stats_by_strato.items():
        attempts = stats['downloaded'] + stats['failed']
        if attempts > 0:
            yield_by_strato[strato] = round(stats['downloaded'] / attempts, 3)
        else:
            yield_by_strato[strato] = 0.0

    logger.info(f"\n📈 YIELD CALCOLATO:")
    logger.info(f"   Yield globale: {yield_global:.1%} ({total_success}/{total_attempts})")
    logger.info(f"   Analizzati:    {len(analyzed)} ({len(analyzed)/total_success*100:.1f}% dei downloaded)")

    # Mostra top 5 strati per download
    logger.info(f"\n📊 TOP 10 STRATI PER DOWNLOAD:")
    sorted_strata = sorted(stats_by_strato.items(), key=lambda x: x[1]['downloaded'], reverse=True)
    for strato, stats in sorted_strata[:10]:
        yield_s = yield_by_strato.get(strato, 0)
        logger.info(f"   {strato}: {stats['downloaded']} scaricati, {stats['analyzed']} analizzati (yield {yield_s:.0%})")

    # Prepara aggiornamento stato
    new_state = {
        'cycle_id': strata_state.get('cycle_id', 0),
        'target_total': strata_state.get('target_total', 6000),
        'yield_global': round(yield_global, 3),
        'yield_by_strato': yield_by_strato,
        'downloaded_total': len(downloaded),
        'failed_total': len(failed),
        'analyzed_total': len(analyzed),
        'status': 'synced',
        'synced_at': datetime.now().isoformat(),
        'note': f'Sincronizzato da sync_sampling.py - {len(downloaded)} downloaded, {len(analyzed)} analyzed'
    }

    # Confronta con stato precedente
    old_downloaded = strata_state.get('downloaded_total', 0)
    old_analyzed = strata_state.get('analyzed_total', 0)
    old_yield = strata_state.get('yield_global', 0)

    logger.info(f"\n🔄 DIFFERENZE:")
    logger.info(f"   Downloaded: {old_downloaded} → {len(downloaded)} ({len(downloaded) - old_downloaded:+d})")
    logger.info(f"   Analyzed:   {old_analyzed} → {len(analyzed)} ({len(analyzed) - old_analyzed:+d})")
    logger.info(f"   Yield:      {old_yield:.1%} → {yield_global:.1%}")

    if dry_run:
        logger.info(f"\n🔍 DRY RUN - Nessuna modifica effettuata")
        logger.info(f"   Esegui senza --dry-run per salvare le modifiche")
    else:
        save_json(STRATA_STATE, new_state)
        logger.info(f"\n✅ Stato salvato in {STRATA_STATE}")

    return new_state


def main():
    parser = argparse.ArgumentParser(description="Sincronizza dati campionamento con download effettivi")
    parser.add_argument('--dry-run', action='store_true', help='Mostra modifiche senza applicarle')
    args = parser.parse_args()

    sync_sampling(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
