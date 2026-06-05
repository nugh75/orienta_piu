#!/usr/bin/env python3
"""
Allinea i metadati delle scuole ai file ufficiali MIUR (SCUANAGRAFESTAT/PAR).

Sovrascrive i campi anagrafici in:
  - data/analysis_summary.csv
  - analysis_results/*_analysis.json

Usage:
    python scripts/align_miur_metadata.py              # Applica tutto
    python scripts/align_miur_metadata.py --dry-run    # Mostra solo le differenze
    python scripts/align_miur_metadata.py --csv-only   # Solo CSV
    python scripts/align_miur_metadata.py --json-only  # Solo JSON
    python scripts/align_miur_metadata.py --verify      # Verifica allineamento post-fix
"""
import os
import sys
import csv
import json
import shutil
import argparse
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, PROJECT_ROOT)

from src.utils.constants import normalize_area_geografica, get_territorio, normalize_regione

# ─── File paths ───────────────────────────────────────────────────────────
STAT_CSV = os.path.join(PROJECT_ROOT, "data/SCUANAGRAFESTAT20252620250901.csv")
PAR_CSV = os.path.join(PROJECT_ROOT, "data/SCUANAGRAFEPAR20252620250901.csv")
SUMMARY_CSV = os.path.join(PROJECT_ROOT, "data/analysis_summary.csv")
RESULTS_DIR = os.path.join(PROJECT_ROOT, "analysis_results")


# ─── Mappatura tipo MIUR → (ordine_grado, tipo_scuola) ──────────────────
# Ordine logico per ordinamento ordine_grado
ORDINE_GRADO_ORDER = ['Infanzia', 'Primaria', 'I Grado', 'Comprensivo', 'II Grado', 'Altro']

def sort_ordine_grado(ordine: str) -> str:
    """Ordina le parti di ordine_grado in ordine logico."""
    if not ordine or ordine == 'ND':
        return ordine
    parts = [p.strip() for p in ordine.split(',') if p.strip()]
    parts = sorted(set(parts), key=lambda x: ORDINE_GRADO_ORDER.index(x) if x in ORDINE_GRADO_ORDER else 99)
    return ', '.join(parts)

def sort_tipo_scuola(tipo: str) -> str:
    """Ordina le parti di tipo_scuola in ordine logico."""
    TIPO_ORDER = ['Infanzia', 'Primaria', 'I Grado', 'Comprensivo', 'Liceo', 'Tecnico', 'Professionale', 'Convitto', 'II Grado', 'CPIA']
    if not tipo or tipo == 'ND':
        return tipo
    parts = [p.strip() for p in tipo.split(',') if p.strip()]
    parts = sorted(set(parts), key=lambda x: TIPO_ORDER.index(x) if x in TIPO_ORDER else 99)
    return ', '.join(parts)


def map_tipo_miur(raw_tipo: str) -> tuple:
    """
    Mappa il campo DESCRIZIONETIPOLOGIAGRADOISTRUZIONESCUOLA a (ordine_grado, tipo_scuola).
    Returns: (ordine_grado, tipo_scuola, tipo_scuola_dettaglio)
    """
    t = raw_tipo.strip().upper()

    # Infanzia
    if 'INFANZIA' in t:
        return ('Infanzia', 'Infanzia', raw_tipo.strip().title())

    # Primaria
    if 'PRIMARIA' in t or 'ELEMENTARE' in t:
        return ('Primaria', 'Primaria', raw_tipo.strip().title())

    # I Grado (scuola media / primo grado)
    if 'PRIMO GRADO' in t or 'MEDIA' in t:
        return ('I Grado', 'I Grado', raw_tipo.strip().title())

    # Scuola Magistrale (vecchio ordinamento, II grado)
    if t == 'SCUOLA MAGISTRALE':
        return ('II Grado', 'Liceo', 'Scuola Magistrale')

    # Istituto Comprensivo → tipo canonico 'Comprensivo'
    if 'COMPRENSIVO' in t:
        return ('Comprensivo', 'Comprensivo', raw_tipo.strip().title())

    # II Grado - Licei
    if 'LICEO' in t:
        return ('II Grado', 'Liceo', raw_tipo.strip().title())

    # II Grado - Istituto Magistrale (equivalente liceo)
    if 'MAGISTRALE' in t:
        return ('II Grado', 'Liceo', raw_tipo.strip().title())

    # II Grado - Tecnici
    if 'TECNICO' in t or 'IST TEC' in t:
        return ('II Grado', 'Tecnico', raw_tipo.strip().title())

    # II Grado - Professionali
    if 'PROF' in t:
        return ('II Grado', 'Professionale', raw_tipo.strip().title())

    # II Grado - Istituto Superiore (generico, sarà risolto dai plessi)
    if 'SUPERIORE' in t:
        return ('II Grado', 'Istituto Superiore', raw_tipo.strip().title())

    # II Grado - Convitto / Educandato → tipo canonico 'Convitto'
    if 'CONVITTO' in t or 'EDUCANDATO' in t:
        return ('II Grado', 'Convitto', raw_tipo.strip().title())

    # II Grado - Istituto d'Arte
    if "D'ARTE" in t or 'ARTE' in t:
        return ('II Grado', 'Liceo', raw_tipo.strip().title())

    # Secondo grado generico (paritarie)
    if 'SECONDO GRADO' in t:
        return ('II Grado', 'II Grado', raw_tipo.strip().title())

    # Centro territoriale (CPIA / educazione adulti)
    if 'CENTRO' in t:
        return ('Altro', 'CPIA', raw_tipo.strip().title())

    return ('ND', 'ND', raw_tipo.strip().title())


def clean_value(val: str, to_title: bool = False) -> str:
    """Pulisce un valore MIUR. Rimuove anche doppi apici residui."""
    if not val or val.strip().lower() in ['non disponibile', 'nd', 'n/a', '']:
        return ''
    val = val.strip().strip('"')
    return val.title() if to_title else val


# ─── Caricamento dati MIUR ───────────────────────────────────────────────
def load_miur_data() -> dict:
    """
    Carica entrambi i file MIUR e restituisce un dict code → metadata.
    Per le scuole STAT con più record (es. IS), usa il record principale
    (CODICESCUOLA == CODICEISTITUTORIFERIMENTO) e risolve il tipo
    'Istituto Superiore' esaminando i plessi associati.
    """
    miur = {}
    # Raccoglie i plessi per ogni istituto di riferimento (per risolvere IS)
    plessi_per_istituto = defaultdict(list)

    # --- Scuole statali ---
    if os.path.exists(STAT_CSV):
        print(f"📂 Caricamento {os.path.basename(STAT_CSV)}...")
        all_stat_rows = []
        with open(STAT_CSV, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f)
            all_stat_rows = list(reader)

        # Prima passata: raccogli tutti i plessi per istituto
        for row in all_stat_rows:
            code = row.get('CODICESCUOLA', '').strip().upper()
            ref_code = row.get('CODICEISTITUTORIFERIMENTO', '').strip().upper()
            if code != ref_code and ref_code:
                raw_tipo = row.get('DESCRIZIONETIPOLOGIAGRADOISTRUZIONESCUOLA', '')
                _, plesso_tipo, plesso_dettaglio = map_tipo_miur(raw_tipo)
                plessi_per_istituto[ref_code].append({
                    'tipo_scuola': plesso_tipo,
                    'dettaglio': plesso_dettaglio,
                })

        # Seconda passata: carica i record principali
        for row in all_stat_rows:
            code = row.get('CODICESCUOLA', '').strip().upper()
            ref_code = row.get('CODICEISTITUTORIFERIMENTO', '').strip().upper()

            # REMOVED: if code != ref_code filter to include ALL plessi
            # if code != ref_code:
            #     continue

            raw_tipo = row.get('DESCRIZIONETIPOLOGIAGRADOISTRUZIONESCUOLA', '')
            ordine, tipo, dettaglio = map_tipo_miur(raw_tipo)

            # Risolvi 'Istituto Superiore' dai plessi
            if tipo == 'Istituto Superiore' and code in plessi_per_istituto:
                plesso_types = set()
                for p in plessi_per_istituto[code]:
                    pt = p['tipo_scuola']
                    # Ignora i sotto-plessi generici
                    if pt not in ('Istituto Superiore', 'ND', 'CPIA'):
                        plesso_types.add(pt)
                if plesso_types:
                    tipo = sort_tipo_scuola(', '.join(plesso_types))
                    dettaglio = 'Istituto Superiore'  # Mantieni il dettaglio originale

            raw_area = row.get('AREAGEOGRAFICA', '')
            regione_raw = clean_value(row.get('REGIONE', ''), to_title=True)
            regione = normalize_regione(regione_raw)
            provincia = clean_value(row.get('PROVINCIA', ''), to_title=True)

            try:
                area = normalize_area_geografica(
                    raw_area,
                    regione=regione,
                    provincia_sigla=code[:2] if len(code) >= 2 else None
                )
            except Exception:
                area = clean_value(raw_area, to_title=True)

            miur[code] = {
                'denominazione': clean_value(row.get('DENOMINAZIONEISTITUTORIFERIMENTO', '') or row.get('DENOMINAZIONESCUOLA', ''), to_title=True),
                'comune': clean_value(row.get('DESCRIZIONECOMUNE', ''), to_title=True),
                'provincia': provincia,
                'regione': regione,
                'area_geografica': area,
                'indirizzo': clean_value(row.get('INDIRIZZOSCUOLA', ''), to_title=True),
                'cap': clean_value(row.get('CAPSCUOLA', '')),
                'email': clean_value(row.get('INDIRIZZOEMAILSCUOLA', '')).lower() if clean_value(row.get('INDIRIZZOEMAILSCUOLA', '')) else '',
                'pec': clean_value(row.get('INDIRIZZOPECSCUOLA', '')).lower() if clean_value(row.get('INDIRIZZOPECSCUOLA', '')) else '',
                'website': clean_value(row.get('SITOWEBSCUOLA', '')).lower() if clean_value(row.get('SITOWEBSCUOLA', '')) else '',
                'tipo_scuola': tipo,
                'tipo_scuola_dettaglio': dettaglio,
                'ordine_grado': sort_ordine_grado(ordine),
                'statale_paritaria': 'Statale',
                'territorio': get_territorio(provincia),
            }
        print(f"   ✅ {len(miur)} scuole statali (record principali)")
        # Report IS risolti
        is_resolved = sum(1 for v in miur.values() if v['tipo_scuola_dettaglio'] == 'Istituto Superiore' and v['tipo_scuola'] != 'Istituto Superiore')
        is_unresolved = sum(1 for v in miur.values() if v['tipo_scuola'] == 'Istituto Superiore')
        print(f"   📋 IS risolti dai plessi: {is_resolved}, IS non risolti: {is_unresolved}")
    else:
        print(f"   ⚠️ File non trovato: {STAT_CSV}")

    # --- Scuole paritarie ---
    par_count = 0
    if os.path.exists(PAR_CSV):
        print(f"📂 Caricamento {os.path.basename(PAR_CSV)}...")
        with open(PAR_CSV, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = row.get('CODICESCUOLA', '').strip().upper()
                if not code or code in miur:
                    continue

                raw_tipo = row.get('DESCRIZIONETIPOLOGIAGRADOISTRUZIONESCUOLA', '')
                ordine, tipo, dettaglio = map_tipo_miur(raw_tipo)

                raw_area = row.get('AREAGEOGRAFICA', '')
                regione_raw = clean_value(row.get('REGIONE', ''), to_title=True)
                regione = normalize_regione(regione_raw)
                provincia = clean_value(row.get('PROVINCIA', ''), to_title=True)

                try:
                    area = normalize_area_geografica(
                        raw_area,
                        regione=regione,
                        provincia_sigla=code[:2] if len(code) >= 2 else None
                    )
                except Exception:
                    area = clean_value(raw_area, to_title=True)

                miur[code] = {
                    'denominazione': clean_value(row.get('DENOMINAZIONESCUOLA', ''), to_title=True),
                    'comune': clean_value(row.get('DESCRIZIONECOMUNE', ''), to_title=True),
                    'provincia': provincia,
                    'regione': regione,
                    'area_geografica': area,
                    'indirizzo': clean_value(row.get('INDIRIZZOSCUOLA', ''), to_title=True),
                    'cap': clean_value(row.get('CAPSCUOLA', '')),
                    'email': clean_value(row.get('INDIRIZZOEMAILSCUOLA', '')).lower() if clean_value(row.get('INDIRIZZOEMAILSCUOLA', '')) else '',
                    'pec': clean_value(row.get('INDIRIZZOPECSCUOLA', '')).lower() if clean_value(row.get('INDIRIZZOPECSCUOLA', '')) else '',
                    'website': clean_value(row.get('SITOWEBSCUOLA', '')).lower() if clean_value(row.get('SITOWEBSCUOLA', '')) else '',
                    'tipo_scuola': tipo,
                    'tipo_scuola_dettaglio': dettaglio,
                    'ordine_grado': sort_ordine_grado(ordine),
                    'statale_paritaria': 'Paritaria',
                    'territorio': get_territorio(provincia),
                }
                par_count += 1
        print(f"   ✅ {par_count} scuole paritarie")
    else:
        print(f"   ⚠️ File non trovato: {PAR_CSV}")

    print(f"\n📊 Totale scuole MIUR caricate: {len(miur)}")
    return miur


# ─── Campi da allineare ──────────────────────────────────────────────────
ALIGN_FIELDS = [
    'denominazione', 'comune', 'provincia', 'regione', 'area_geografica',
    'tipo_scuola', 'tipo_scuola_dettaglio', 'ordine_grado',
    'indirizzo', 'cap', 'email', 'pec', 'website',
    'statale_paritaria', 'territorio',
]


# ─── Allineamento CSV ────────────────────────────────────────────────────
def align_csv(miur: dict, dry_run: bool = False) -> dict:
    """Allinea analysis_summary.csv ai dati MIUR."""
    if not os.path.exists(SUMMARY_CSV):
        print(f"❌ File non trovato: {SUMMARY_CSV}")
        return {}

    print(f"\n{'🔍 DRY RUN - ' if dry_run else ''}📋 Allineamento {os.path.basename(SUMMARY_CSV)}...")

    with open(SUMMARY_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    stats = {
        'total': len(rows),
        'matched': 0,
        'not_in_miur': 0,
        'updated': 0,
        'field_changes': defaultdict(int),
        'changes_detail': [],
    }

    updated_rows = []
    for row in rows:
        sid = row.get('school_id', '').strip().upper()
        miur_data = miur.get(sid)

        if not miur_data:
            stats['not_in_miur'] += 1
            updated_rows.append(row)
            continue

        stats['matched'] += 1
        changes = {}

        for field in ALIGN_FIELDS:
            if field not in fieldnames and field != 'tipo_scuola_dettaglio':
                continue

            miur_val = miur_data.get(field, '')
            csv_val = row.get(field, '')

            # Non sovrascrivere con valori vuoti
            if not miur_val:
                continue

            if csv_val != miur_val:
                changes[field] = {'old': csv_val, 'new': miur_val}
                stats['field_changes'][field] += 1
                row[field] = miur_val

        if changes:
            stats['updated'] += 1
            stats['changes_detail'].append({
                'school_id': sid,
                'denominazione': miur_data.get('denominazione', ''),
                'changes': changes,
            })

        updated_rows.append(row)

    # Report
    print(f"   Scuole totali: {stats['total']}")
    print(f"   Trovate in MIUR: {stats['matched']}")
    print(f"   Non in MIUR: {stats['not_in_miur']}")
    print(f"   Con modifiche: {stats['updated']}")

    if stats['field_changes']:
        print(f"\n   Modifiche per campo:")
        for field, count in sorted(stats['field_changes'].items(), key=lambda x: -x[1]):
            print(f"     {field}: {count} modifiche")

    # Mostra le prime N modifiche dettagliate
    detail_limit = 30 if dry_run else 10
    if stats['changes_detail']:
        print(f"\n   Dettaglio (prime {min(detail_limit, len(stats['changes_detail']))}):")
        for d in stats['changes_detail'][:detail_limit]:
            print(f"   📌 {d['school_id']} ({d['denominazione'][:40]})")
            for field, change in d['changes'].items():
                print(f"      {field}: '{change['old']}' → '{change['new']}'")

    # Scrittura
    if not dry_run and stats['updated'] > 0:
        # Backup
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup = f"{SUMMARY_CSV}.bak.miur_align.{ts}"
        shutil.copy2(SUMMARY_CSV, backup)
        print(f"\n   💾 Backup: {os.path.basename(backup)}")

        # Assicurati che tipo_scuola_dettaglio sia nei fieldnames se necessario
        if 'tipo_scuola_dettaglio' not in fieldnames:
            # Inseriscilo dopo tipo_scuola
            idx = fieldnames.index('tipo_scuola') + 1 if 'tipo_scuola' in fieldnames else len(fieldnames)
            fieldnames = list(fieldnames)
            fieldnames.insert(idx, 'tipo_scuola_dettaglio')

        with open(SUMMARY_CSV, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(updated_rows)
        print(f"   ✅ CSV aggiornato con {stats['updated']} modifiche")

    return stats


# ─── Allineamento JSON ───────────────────────────────────────────────────
def align_json_files(miur: dict, dry_run: bool = False) -> dict:
    """Allinea i file JSON di analisi ai dati MIUR."""
    if not os.path.exists(RESULTS_DIR):
        print(f"❌ Directory non trovata: {RESULTS_DIR}")
        return {}

    json_files = list(Path(RESULTS_DIR).glob('*_analysis.json'))
    print(f"\n{'🔍 DRY RUN - ' if dry_run else ''}📋 Allineamento {len(json_files)} file JSON...")

    import re

    stats = {
        'total': len(json_files),
        'matched': 0,
        'not_in_miur': 0,
        'updated': 0,
        'errors': 0,
        'field_changes': defaultdict(int),
    }

    for jf in json_files:
        # Estrai codice dal nome file
        code_raw = jf.stem.replace('_PTOF_analysis', '').replace('_analysis', '')
        # Estrai codice canonico
        match = re.search(r'([A-Z]{2}[A-Z0-9]{8,10})', code_raw.upper())
        if match:
            code = match.group(1)
        else:
            code = code_raw.upper()

        miur_data = miur.get(code)
        if not miur_data:
            stats['not_in_miur'] += 1
            continue

        stats['matched'] += 1

        try:
            with open(jf, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if 'metadata' not in data:
                data['metadata'] = {}

            changed = False
            for field in ALIGN_FIELDS:
                miur_val = miur_data.get(field, '')
                if not miur_val:
                    continue
                current = data['metadata'].get(field, '')
                if current != miur_val:
                    data['metadata'][field] = miur_val
                    stats['field_changes'][field] += 1
                    changed = True

            # Assicura school_id
            data['metadata']['school_id'] = code

            if changed:
                stats['updated'] += 1
                if not dry_run:
                    with open(jf, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            stats['errors'] += 1
            print(f"   ❌ Errore {jf.name}: {e}")

    print(f"   File totali: {stats['total']}")
    print(f"   Trovati in MIUR: {stats['matched']}")
    print(f"   Non in MIUR: {stats['not_in_miur']}")
    print(f"   Aggiornati: {stats['updated']}")
    if stats['errors']:
        print(f"   Errori: {stats['errors']}")

    if stats['field_changes']:
        print(f"\n   Modifiche per campo:")
        for field, count in sorted(stats['field_changes'].items(), key=lambda x: -x[1]):
            print(f"     {field}: {count}")

    return stats


# ─── Verifica ─────────────────────────────────────────────────────────────
def verify_alignment(miur: dict) -> bool:
    """Verifica che analysis_summary.csv sia allineato con MIUR."""
    if not os.path.exists(SUMMARY_CSV):
        print(f"❌ File non trovato: {SUMMARY_CSV}")
        return False

    print(f"\n🔎 Verifica allineamento {os.path.basename(SUMMARY_CSV)}...")

    mismatches = []
    matched = 0
    total = 0

    with open(SUMMARY_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            sid = row.get('school_id', '').strip().upper()
            miur_data = miur.get(sid)
            if not miur_data:
                continue
            matched += 1

            diffs = {}
            for field in ALIGN_FIELDS:
                miur_val = miur_data.get(field, '')
                csv_val = row.get(field, '')
                if miur_val and csv_val != miur_val:
                    diffs[field] = {'csv': csv_val, 'miur': miur_val}

            if diffs:
                mismatches.append({'school_id': sid, 'diffs': diffs})

    print(f"   Scuole totali: {total}")
    print(f"   Con dati MIUR: {matched}")
    print(f"   Disallineamenti: {len(mismatches)}")

    if mismatches:
        print(f"\n   Prime {min(20, len(mismatches))} discrepanze:")
        for m in mismatches[:20]:
            print(f"   📌 {m['school_id']}")
            for field, d in m['diffs'].items():
                print(f"      {field}: CSV='{d['csv']}' ≠ MIUR='{d['miur']}'")
        return False

    print("   ✅ Tutti i dati sono allineati con MIUR!")
    return True


# ─── Main ─────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description='Allinea metadati scuole ai file MIUR')
    parser.add_argument('--dry-run', action='store_true', help='Mostra modifiche senza applicarle')
    parser.add_argument('--csv-only', action='store_true', help='Aggiorna solo il CSV')
    parser.add_argument('--json-only', action='store_true', help='Aggiorna solo i JSON')
    parser.add_argument('--verify', action='store_true', help='Verifica allineamento')
    args = parser.parse_args()

    print("=" * 60)
    print("🏫 Allineamento Metadati MIUR")
    print("=" * 60)

    miur = load_miur_data()

    if args.verify:
        ok = verify_alignment(miur)
        sys.exit(0 if ok else 1)

    do_csv = not args.json_only
    do_json = not args.csv_only

    csv_stats = {}
    json_stats = {}

    if do_csv:
        csv_stats = align_csv(miur, dry_run=args.dry_run)

    if do_json:
        json_stats = align_json_files(miur, dry_run=args.dry_run)

    # Riepilogo finale
    print("\n" + "=" * 60)
    print("📊 RIEPILOGO")
    print("=" * 60)
    if csv_stats:
        print(f"   CSV: {csv_stats.get('updated', 0)}/{csv_stats.get('total', 0)} scuole aggiornate")
    if json_stats:
        print(f"   JSON: {json_stats.get('updated', 0)}/{json_stats.get('total', 0)} file aggiornati")

    if args.dry_run:
        print("\n   ⚠️  DRY RUN: nessuna modifica effettuata")
        print("   Per applicare, eseguire senza --dry-run")


if __name__ == '__main__':
    main()
