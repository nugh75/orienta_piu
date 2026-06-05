#!/usr/bin/env python3
"""
Post-processing: arricchisce i codici meccanografici nei report di sintesi
aggiungendo il nome della scuola dove manca.

Esempio:
  "la scuola RMTAPV5005 nel Lazio"
  → "la scuola I.C. Roma Tre (RMTAPV5005) nel Lazio"

Fonti dati (in ordine di priorità):
  1. data/analysis_summary.csv        → school_id, denominazione
  2. data/SCUANAGRAFESTAT*.csv         → CODICESCUOLA, DENOMINAZIONESCUOLA
  3. data/SCUANAGRAFEPAR*.csv          → CODICESCUOLA, DENOMINAZIONESCUOLA

Uso:
  python scripts/enrich_school_names.py reports/synthesis/report.md
  python scripts/enrich_school_names.py reports/synthesis/*.md --dry-run
"""

import argparse
import csv
import glob
import os
import re
import sys
from pathlib import Path

# ── Pattern codice meccanografico ─────────────────────────────────
# 2 lettere maiuscole (provincia) + 8 alfanumerici maiuscoli
CODE_RE = re.compile(r'\b([A-Z]{2}[A-Z0-9]{8})\b')


# ── Costruzione dizionario codice → nome ─────────────────────────

def _load_csv(path: str, mapping: dict, code_col: str, name_col: str) -> None:
    """Carica un CSV e aggiunge le coppie codice→nome al mapping."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = (row.get(code_col) or "").strip().upper()
                name = (row.get(name_col) or "").strip()
                if code and name and CODE_RE.fullmatch(code):
                    # Pulisci virgolette doppie residue
                    name = name.replace('""', '"').strip('"').strip()
                    mapping[code] = name
    except Exception as e:
        print(f"  ⚠️  Errore leggendo {path}: {e}", file=sys.stderr)


def build_school_map(data_dir: str) -> dict[str, str]:
    """Costruisce dizionario codice_meccanografico → denominazione."""
    mapping: dict[str, str] = {}

    # 1. Anagrafe MIUR statali (base ampia)
    for csv_path in sorted(glob.glob(os.path.join(data_dir, "SCUANAGRAFESTAT*.csv"))):
        _load_csv(csv_path, mapping, code_col="CODICESCUOLA", name_col="DENOMINAZIONESCUOLA")

    # 2. Anagrafe MIUR paritarie
    for csv_path in sorted(glob.glob(os.path.join(data_dir, "SCUANAGRAFEPAR*.csv"))):
        _load_csv(csv_path, mapping, code_col="CODICESCUOLA", name_col="DENOMINAZIONESCUOLA")

    # 3. analysis_summary.csv (priorità massima: denominazioni curate)
    summary_path = os.path.join(data_dir, "analysis_summary.csv")
    if os.path.isfile(summary_path):
        _load_csv(summary_path, mapping, code_col="school_id", name_col="denominazione")

    return mapping


# ── Logica di arricchimento ───────────────────────────────────────

def _name_already_nearby(text: str, start: int, end: int, name: str) -> bool:
    """
    Controlla se il nome della scuola compare già nelle vicinanze del codice
    (finestra ±150 caratteri).
    """
    window = 150
    ctx_start = max(0, start - window)
    ctx_end = min(len(text), end + window)
    context = text[ctx_start:ctx_end].lower()

    name_lower = name.lower()

    # Match esatto
    if name_lower in context:
        return True

    # Match parziale: almeno 2 parole significative (>2 char) del nome
    words = [w for w in name_lower.split() if len(w) > 2]
    if words:
        hits = sum(1 for w in words if w in context)
        if hits >= min(2, len(words)):
            return True

    return False


def _is_in_table_or_heading(text: str, pos: int) -> bool:
    """Il codice si trova in una riga di tabella markdown o heading?"""
    line_start = text.rfind('\n', 0, pos) + 1
    line_end = text.find('\n', pos)
    if line_end == -1:
        line_end = len(text)
    line = text[line_start:line_end].lstrip()
    return line.startswith('|') or line.startswith('#')


def _is_already_parenthesized(text: str, start: int, end: int) -> bool:
    """Il codice è già tra parentesi, es. (CODICE)?"""
    return (start > 0 and text[start - 1] == '('
            and end < len(text) and text[end] == ')')


def enrich_report(text: str, mapping: dict[str, str]) -> tuple[str, int]:
    """
    Trova i codici meccanografici senza nome nelle vicinanze e li arricchisce.
    Rimuove anche la doppia numerazione dagli heading markdown (es. "## 3. Titolo" → "## Titolo").
    Restituisce (testo_arricchito, numero_sostituzioni).
    """
    # Pre-processing: rimuovi numerazione manuale dagli heading markdown
    # es. "## 3. Metodologie" → "## Metodologie"
    text = re.sub(r'^(#{1,6})\s+\d+\.\s+', r'\1 ', text, flags=re.MULTILINE)

    substitutions: list[tuple[int, int, str]] = []

    for m in CODE_RE.finditer(text):
        code = m.group(1)
        start, end = m.start(), m.end()

        # Salta se il codice non è nel dizionario
        if code not in mapping:
            continue

        name = mapping[code]

        # Salta tabelle/heading
        if _is_in_table_or_heading(text, start):
            continue

        # Salta se già tra parentesi: Nome (CODICE)
        if _is_already_parenthesized(text, start, end):
            continue

        # Salta se il nome compare già nelle vicinanze
        if _name_already_nearby(text, start, end, name):
            continue

        # Sostituzione: CODICE → Nome Scuola (CODICE)
        substitutions.append((start, end, f"{name} ({code})"))

    # Applica dal fondo per preservare gli indici
    result = text
    for start, end, replacement in reversed(substitutions):
        result = result[:start] + replacement + result[end:]

    return result, len(substitutions)


# ── CLI ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Arricchisce i codici meccanografici nei report con il nome della scuola"
    )
    parser.add_argument("files", nargs="+", help="File markdown da processare")
    parser.add_argument(
        "--data-dir", default=None,
        help="Directory con i CSV (default: <project_root>/data)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Mostra le modifiche senza applicarle"
    )
    args = parser.parse_args()

    # Risolvi data_dir
    project_root = Path(__file__).resolve().parent.parent
    data_dir = Path(args.data_dir) if args.data_dir else project_root / "data"
    data_dir = data_dir.resolve()

    if not data_dir.is_dir():
        print(f"❌ Directory dati non trovata: {data_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"📂 Caricamento mapping scuole da {data_dir}...")
    mapping = build_school_map(str(data_dir))
    print(f"   ✅ {len(mapping)} scuole nel dizionario")

    total_enriched = 0

    for filepath in args.files:
        if not os.path.isfile(filepath):
            print(f"  ⚠️  File non trovato: {filepath}", file=sys.stderr)
            continue

        # Salta skeleton e backup
        basename = os.path.basename(filepath)
        if "SKELETON" in basename or basename.endswith(".bak"):
            continue

        print(f"\n📄 Processamento: {filepath}")

        with open(filepath, encoding="utf-8") as f:
            original = f.read()

        enriched, count = enrich_report(original, mapping)

        if count == 0:
            print("   ✅ Nessun codice meccanografico isolato trovato")
            continue

        total_enriched += count

        if args.dry_run:
            print(f"   🔍 {count} codici da arricchire (dry-run, nessuna modifica)")
            for orig_line, new_line in zip(
                original.splitlines(), enriched.splitlines()
            ):
                if orig_line != new_line:
                    print(f"   - {orig_line[:140]}")
                    print(f"   + {new_line[:140]}")
        else:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(enriched)
            print(f"   ✅ {count} codici arricchiti con nome scuola")

    print(f"\n{'🔍 Dry-run:' if args.dry_run else '✅'} "
          f"Totale codici arricchiti: {total_enriched}")


if __name__ == "__main__":
    main()
