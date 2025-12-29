#!/usr/bin/env python3
"""
Script di pulizia file obsoleti - ORIENTA+
==========================================

Questo script identifica e rimuove file non più utilizzati nel progetto.
Esegui con --dry-run per vedere cosa verrebbe eliminato senza eliminare nulla.
Esegui senza flag per eliminare effettivamente i file.

Uso:
    python cleanup_obsolete.py --dry-run    # Mostra cosa verrebbe eliminato
    python cleanup_obsolete.py              # Elimina i file (chiede conferma)
    python cleanup_obsolete.py --force      # Elimina senza conferma
    python cleanup_obsolete.py --include-bak                    # Includi file .bak
    python cleanup_obsolete.py --include-bak --older-than 7     # Solo .bak più vecchi di 7 giorni
    python cleanup_obsolete.py --bak-only --older-than 1        # Solo .bak più vecchi di 1 giorno
"""

import os
import shutil
import argparse
import logging
from pathlib import Path
from datetime import datetime, timedelta

# Directory base del progetto
BASE_DIR = Path(__file__).parent

# Setup logging
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / 'cleanup.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# =============================================================================
# DEFINIZIONE FILE/DIRECTORY DA ELIMINARE
# =============================================================================

# 1. Directory di backup pre-review (snapshot obsoleti)
PRE_REVIEW_BACKUPS = [
    "analysis_results/pre_review_backup",
    "analysis_results/pre_score_review_backup",
    "analysis_results/pre_review_backup_gemini",
    "analysis_results/pre_ollama_score_backup",
    "analysis_results/pre_ollama_report_backup",
]

# 2. Backup manuali datati (20-21 dicembre)
MANUAL_BACKUPS = [
    "backups/backup_20251220_223105_manual_user",
    "backups/backup_20251220_233845_manual_user",
    "backups/backup_20251220_235229_manual_user",
    "backups/backup_20251221_000225_manual_user",
    "backups/backup_20251221_001404_manual_user",
]

# 3. Directory legacy
LEGACY_DIRS = [
    "legacy",  # 11 script Python obsoleti
    "ptof_inbox_backup",  # Backup PTOF non utilizzato
]

# 4. File singoli obsoleti
OBSOLETE_FILES = [
    "pages/1_Metodologia.py",  # Pagina Streamlit legacy (sostituita da app/pages/)
    "extract_ref_pdf.py",  # Script test non documentato
    "reproduce_issue.py",  # Script debug non più necessario
    "update_notebook.py",  # Script utilità non documentato
]

# 5. Backup pagine Streamlit (creato il 26/12)
PAGES_BACKUP = "app/pages_backup_20251226_104143"

# 6. File .bak in analysis_results (opzionale - chiedere conferma separata)
BAK_PATTERN = "analysis_results/*.bak"


def get_size(path: Path) -> int:
    """Calcola la dimensione di un file o directory in bytes."""
    if path.is_file():
        return path.stat().st_size
    elif path.is_dir():
        total = 0
        for f in path.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
        return total
    return 0


def format_size(bytes_size: int) -> str:
    """Formatta la dimensione in formato leggibile."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f} TB"


def count_files(path: Path) -> int:
    """Conta i file in una directory."""
    if path.is_file():
        return 1
    elif path.is_dir():
        return sum(1 for f in path.rglob("*") if f.is_file())
    return 0


def get_file_age_days(path: Path) -> float:
    """Restituisce l'età del file in giorni."""
    if not path.exists():
        return 0
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    age = datetime.now() - mtime
    return age.total_seconds() / 86400  # secondi in un giorno


def list_bak_files(older_than_days: int = None) -> list:
    """Lista i file .bak in analysis_results, opzionalmente filtrati per età."""
    bak_dir = BASE_DIR / "analysis_results"
    if not bak_dir.exists():
        return []

    all_bak = list(bak_dir.glob("*.bak"))

    if older_than_days is None:
        return all_bak

    # Filtra per età
    cutoff = datetime.now() - timedelta(days=older_than_days)
    filtered = []
    for f in all_bak:
        mtime = datetime.fromtimestamp(f.stat().st_mtime)
        if mtime < cutoff:
            filtered.append(f)

    return filtered


def print_section(title: str, items: list, show_age: bool = False):
    """Stampa una sezione del report."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print('='*60)

    total_size = 0
    total_files = 0

    for item in items:
        path = BASE_DIR / item if isinstance(item, str) else item
        if path.exists():
            size = get_size(path)
            files = count_files(path)
            total_size += size
            total_files += files
            status = "DIR" if path.is_dir() else "FILE"

            # Mostra età se richiesto
            age_str = ""
            if show_age and path.is_file():
                age_days = get_file_age_days(path)
                if age_days < 1:
                    age_str = f" ({age_days*24:.1f}h fa)"
                else:
                    age_str = f" ({age_days:.1f}d fa)"

            print(f"  [{status}] {path.relative_to(BASE_DIR)}{age_str}")
            print(f"         {format_size(size)} - {files} file(s)")
        else:
            print(f"  [SKIP] {item} (non esiste)")

    print(f"\n  TOTALE: {format_size(total_size)} - {total_files} file(s)")
    return total_size, total_files


def delete_items(items: list, dry_run: bool = True) -> tuple:
    """Elimina gli elementi specificati."""
    deleted_size = 0
    deleted_files = 0
    errors = []

    for item in items:
        path = BASE_DIR / item if isinstance(item, str) else item
        if path.exists():
            try:
                size = get_size(path)
                files = count_files(path)

                if not dry_run:
                    if path.is_dir():
                        shutil.rmtree(path)
                    else:
                        path.unlink()

                deleted_size += size
                deleted_files += files

            except Exception as e:
                errors.append((item, str(e)))

    return deleted_size, deleted_files, errors


def main():
    parser = argparse.ArgumentParser(
        description="Pulizia file obsoleti - ORIENTA+",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='Mostra cosa verrebbe eliminato senza eliminare')
    parser.add_argument('--force', action='store_true',
                        help='Elimina senza chiedere conferma')
    parser.add_argument('--include-bak', action='store_true',
                        help='Includi anche i file .bak (backup analysis)')
    parser.add_argument('--include-pages-backup', action='store_true',
                        help='Includi anche il backup pagine Streamlit recente')
    parser.add_argument('--older-than', type=int, metavar='DAYS',
                        help='Filtra file .bak più vecchi di N giorni (richiede --include-bak o --bak-only)')
    parser.add_argument('--bak-only', action='store_true',
                        help='Elimina SOLO i file .bak (ignora tutto il resto)')

    args = parser.parse_args()

    # Validazione argomenti
    if args.older_than is not None and not (args.include_bak or args.bak_only):
        print("ERRORE: --older-than richiede --include-bak o --bak-only")
        return

    print("\n" + "="*60)
    print(" PULIZIA FILE OBSOLETI - ORIENTA+")
    print(" " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*60)

    if args.dry_run:
        print("\n [DRY-RUN] Nessun file verra' eliminato\n")

    # Raccogli tutti gli elementi da eliminare
    all_items = []

    # Modalità solo .bak
    if args.bak_only:
        bak_files = list_bak_files(older_than_days=args.older_than)

        if args.older_than:
            title = f"FILE .BAK più vecchi di {args.older_than} giorni"
        else:
            title = "TUTTI I FILE .BAK"

        if bak_files:
            print_section(title, bak_files, show_age=True)
            all_items.extend(bak_files)
        else:
            print(f"\n{'='*60}")
            print(f" {title}")
            print("="*60)
            if args.older_than:
                print(f"  Nessun file .bak più vecchio di {args.older_than} giorni trovato")
            else:
                print("  Nessun file .bak trovato")
            return
    else:
        # Modalità normale (tutti i file obsoleti)

        # 1. Pre-review backups
        print_section("1. BACKUP PRE-REVIEW (snapshot obsoleti)", PRE_REVIEW_BACKUPS)
        all_items.extend(PRE_REVIEW_BACKUPS)

        # 2. Manual backups
        print_section("2. BACKUP MANUALI (20-21 dicembre)", MANUAL_BACKUPS)
        all_items.extend(MANUAL_BACKUPS)

        # 3. Legacy directories
        print_section("3. DIRECTORY LEGACY", LEGACY_DIRS)
        all_items.extend(LEGACY_DIRS)

        # 4. Obsolete files
        print_section("4. FILE SINGOLI OBSOLETI", OBSOLETE_FILES)
        all_items.extend(OBSOLETE_FILES)

        # 5. Pages backup (opzionale)
        if args.include_pages_backup:
            print_section("5. BACKUP PAGINE STREAMLIT (26/12)", [PAGES_BACKUP])
            all_items.append(PAGES_BACKUP)
        else:
            print(f"\n{'='*60}")
            print(" 5. BACKUP PAGINE STREAMLIT (26/12) - ESCLUSO")
            print("="*60)
            print(f"  [SKIP] {PAGES_BACKUP}")
            print("         Usa --include-pages-backup per includerlo")

        # 6. BAK files (opzionale)
        if args.include_bak:
            bak_files = list_bak_files(older_than_days=args.older_than)
            if bak_files:
                if args.older_than:
                    title = f"6. FILE .BAK più vecchi di {args.older_than} giorni"
                else:
                    title = "6. FILE .BAK (backup analysis)"
                print_section(title, bak_files, show_age=True)
                all_items.extend(bak_files)
            else:
                print(f"\n{'='*60}")
                print(" 6. FILE .BAK (backup analysis)")
                print("="*60)
                if args.older_than:
                    print(f"  Nessun file .bak più vecchio di {args.older_than} giorni")
                else:
                    print("  Nessun file .bak trovato")
        else:
            all_bak = list_bak_files()
            print(f"\n{'='*60}")
            print(" 6. FILE .BAK (backup analysis) - ESCLUSI")
            print("="*60)
            print(f"  [SKIP] {len(all_bak)} file .bak in analysis_results/")
            print("         Usa --include-bak per includerli")
            print("         Usa --include-bak --older-than N per filtrare per età")
            print("         NOTA: Questi file servono per restore_from_backup.py")

    # Calcola totali
    print("\n" + "="*60)
    print(" RIEPILOGO")
    print("="*60)

    total_size = 0
    total_files = 0
    for item in all_items:
        path = BASE_DIR / item if isinstance(item, str) else item
        if path.exists():
            total_size += get_size(path)
            total_files += count_files(path)

    print(f"\n  Elementi da eliminare: {len(all_items)}")
    print(f"  File totali: {total_files}")
    print(f"  Spazio da liberare: {format_size(total_size)}")

    if total_files == 0:
        print("\n Nessun file da eliminare.")
        return

    # Conferma ed esecuzione
    if args.dry_run:
        print("\n [DRY-RUN] Esegui senza --dry-run per eliminare")
        return

    if not args.force:
        print("\n" + "-"*60)
        response = input(" Vuoi procedere con l'eliminazione? [y/N]: ")
        if response.lower() not in ['y', 'yes', 's', 'si']:
            print(" Operazione annullata.")
            return

    # Esegui eliminazione
    print("\n Eliminazione in corso...")
    deleted_size, deleted_files, errors = delete_items(all_items, dry_run=False)

    print(f"\n COMPLETATO!")
    print(f"  File eliminati: {deleted_files}")
    print(f"  Spazio liberato: {format_size(deleted_size)}")

    if errors:
        print(f"\n ERRORI ({len(errors)}):")
        for item, error in errors:
            print(f"  - {item}: {error}")


if __name__ == "__main__":
    main()
