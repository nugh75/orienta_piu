#!/usr/bin/env python3
"""
Converte best_practices.json esistente in best_practices.csv.

Esegue una conversione una tantum mantenendo tutti i dati.
Il JSON viene ridotto a contenere solo metadata globali.
"""
import json
import csv
import shutil
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

INPUT_JSON = DATA_DIR / "best_practices.json"
OUTPUT_CSV = DATA_DIR / "best_practices.csv"
BACKUP_JSON = DATA_DIR / "best_practices_backup.json"

# Colonne CSV in ordine
CSV_COLUMNS = [
    'id',
    'codice_meccanografico',
    'nome_scuola',
    'tipo_scuola',
    'ordine_grado',
    'regione',
    'provincia',
    'comune',
    'area_geografica',
    'territorio',
    'statale_paritaria',
    'categoria',
    'titolo',
    'descrizione',
    'metodologia',
    'tipologie_metodologia',
    'ambiti_attivita',
    'target',
    'citazione_ptof',
    'pagina_evidenza',
    'maturity_index',
    'partnership_coinvolte',
    'extracted_at',
    'model_used',
    'source_file'
]


def list_to_pipe(value):
    """Converte lista in stringa separata da |."""
    if isinstance(value, list):
        return '|'.join(str(v) for v in value if v)
    elif value:
        return str(value)
    return ''


def flatten_practice(practice: dict) -> dict:
    """Appiattisce una pratica nested in una riga flat."""
    school = practice.get('school', {})
    pratica = practice.get('pratica', {})
    contesto = practice.get('contesto', {})
    metadata = practice.get('metadata', {})

    return {
        'id': practice.get('id', ''),
        'codice_meccanografico': school.get('codice_meccanografico', ''),
        'nome_scuola': school.get('nome', ''),
        'tipo_scuola': school.get('tipo_scuola', ''),
        'ordine_grado': school.get('ordine_grado', ''),
        'regione': school.get('regione', ''),
        'provincia': school.get('provincia', ''),
        'comune': school.get('comune', ''),
        'area_geografica': school.get('area_geografica', ''),
        'territorio': school.get('territorio', ''),
        'statale_paritaria': school.get('statale_paritaria', ''),
        'categoria': pratica.get('categoria', ''),
        'titolo': pratica.get('titolo', ''),
        'descrizione': pratica.get('descrizione', ''),
        'metodologia': pratica.get('metodologia', ''),
        'tipologie_metodologia': list_to_pipe(pratica.get('tipologie_metodologia', [])),
        'ambiti_attivita': list_to_pipe(pratica.get('ambiti_attivita', [])),
        'target': pratica.get('target', ''),
        'citazione_ptof': pratica.get('citazione_ptof', ''),
        'pagina_evidenza': pratica.get('pagina_evidenza', ''),
        'maturity_index': contesto.get('maturity_index', ''),
        'partnership_coinvolte': list_to_pipe(contesto.get('partnership_coinvolte', [])),
        'extracted_at': metadata.get('extracted_at', ''),
        'model_used': metadata.get('model_used', ''),
        'source_file': metadata.get('source_file', '')
    }


def main():
    print("=" * 60)
    print("Conversione Best Practices: JSON -> CSV")
    print("=" * 60)

    if not INPUT_JSON.exists():
        print(f"ERRORE: File {INPUT_JSON} non trovato")
        return False

    # Backup del JSON originale
    print(f"\n1. Backup JSON originale -> {BACKUP_JSON}")
    shutil.copy2(INPUT_JSON, BACKUP_JSON)
    print("   OK")

    # Carica JSON
    print(f"\n2. Caricamento {INPUT_JSON}...")
    with open(INPUT_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)

    practices = data.get('practices', [])
    print(f"   Trovate {len(practices)} pratiche")

    if not practices:
        print("   ATTENZIONE: Nessuna pratica da convertire")
        return False

    # Converti in righe flat
    print(f"\n3. Conversione in formato flat...")
    rows = []
    for p in practices:
        rows.append(flatten_practice(p))
    print(f"   Convertite {len(rows)} righe")

    # Scrivi CSV
    print(f"\n4. Scrittura {OUTPUT_CSV}...")
    with open(OUTPUT_CSV, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)
    print("   OK")

    # Aggiorna JSON con solo metadata
    print(f"\n5. Aggiornamento {INPUT_JSON} (solo metadata)...")
    metadata_only = {
        'version': '2.0',
        'format': 'csv',
        'csv_file': 'best_practices.csv',
        'last_updated': data.get('last_updated', datetime.now().isoformat()),
        'extraction_model': data.get('extraction_model', ''),
        'total_practices': len(practices),
        'schools_processed': data.get('schools_processed', 0),
        'converted_at': datetime.now().isoformat(),
        'note': 'Dati pratiche migrati in best_practices.csv'
    }
    with open(INPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(metadata_only, f, ensure_ascii=False, indent=2)
    print("   OK")

    # Verifica
    print(f"\n6. Verifica...")
    csv_size = OUTPUT_CSV.stat().st_size / 1024 / 1024
    json_size = BACKUP_JSON.stat().st_size / 1024 / 1024
    print(f"   JSON originale: {json_size:.2f} MB")
    print(f"   CSV risultante: {csv_size:.2f} MB")
    print(f"   Riduzione: {((json_size - csv_size) / json_size * 100):.1f}%")

    # Test lettura CSV
    import pandas as pd
    df = pd.read_csv(OUTPUT_CSV)
    print(f"   Righe nel CSV: {len(df)}")
    print(f"   Colonne: {len(df.columns)}")

    print("\n" + "=" * 60)
    print("CONVERSIONE COMPLETATA CON SUCCESSO")
    print("=" * 60)
    print(f"\nFile creati:")
    print(f"  - {OUTPUT_CSV} (dati pratiche)")
    print(f"  - {BACKUP_JSON} (backup JSON originale)")
    print(f"  - {INPUT_JSON} (aggiornato con solo metadata)")

    return True


if __name__ == '__main__':
    main()
