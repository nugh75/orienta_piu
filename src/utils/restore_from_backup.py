#!/usr/bin/env python3
"""
Trova file MD troncati e li ripristina dai backup .bak
Usa SOLO i file .bak creati da atomic_write() nella stessa directory.
"""
import shutil
from pathlib import Path

ANALYSIS_DIR = Path("analysis_results")

def is_truncated(file_path):
    """Controlla se un file MD è troncato."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return True
            if content.startswith("```") and not content.endswith("```"):
                return True
            last_char = content[-1]
            if last_char not in ['.', '!', '?', '>', '`', '\n', '}', ']']: 
                return True
            return False
    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}")
        return False

def find_backup(file_path):
    """Cerca il backup .bak nella stessa directory."""
    bak_path = file_path.with_suffix(file_path.suffix + ".bak")
    if bak_path.exists():
        return bak_path
    return None

def restore_files():
    """Trova file troncati e ripristina SOLO quelli dai .bak."""
    truncated_count = 0
    restored_count = 0
    no_backup_count = 0
    
    files = sorted(list(ANALYSIS_DIR.glob("*_PTOF_analysis.md")))
    print(f"🔍 Scanning {len(files)} file MD in {ANALYSIS_DIR}...")

    for file_path in files:
        if is_truncated(file_path):
            truncated_count += 1
            print(f"⚠️  Troncato: {file_path.name}")
            
            backup = find_backup(file_path)
            if backup:
                try:
                    shutil.copy2(backup, file_path)
                    print(f"   ✅ Ripristinato da {backup.name}")
                    restored_count += 1
                except Exception as e:
                    print(f"   ❌ Errore ripristino: {e}")
            else:
                print(f"   ⚠️  Nessun backup .bak trovato")
                no_backup_count += 1

    print(f"\n📊 Riepilogo:")
    print(f"   File troncati trovati: {truncated_count}")
    print(f"   File ripristinati: {restored_count}")
    if no_backup_count > 0:
        print(f"   ⚠️  Senza backup: {no_backup_count}")
    
    if truncated_count == 0:
        print("✅ Nessun file troncato trovato!")

if __name__ == "__main__":
    restore_files()
