#!/usr/bin/env python3
"""Post-processor per report meta-report.

Corregge:
1. Codici scuola inventati (hallucination) → sostituisce con codici reali dal CSV
2. Formattazione grassetto per scuole, province, regioni
3. Struttura sezioni mancanti

Uso:
    python -m src.agents.meta_report.postprocess REPORT_PATH [--csv CSV_PATH]
"""

import argparse
import csv
import re
from pathlib import Path
from typing import Optional


def load_school_data(csv_path: Path) -> dict:
    """Carica mappatura nome scuola → codice dal CSV attività."""
    schools = {}

    if not csv_path.exists():
        print(f"[postprocess] CSV non trovato: {csv_path}")
        return schools

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = row.get("codice_meccanografico", "").strip()
            name = row.get("nome_scuola", row.get("scuola", row.get("nome", ""))).strip()
            region = row.get("regione", "").strip()
            province = row.get("provincia", "").strip()

            if code and name:
                # Normalizza nome per matching fuzzy
                name_key = name.lower().strip()
                schools[name_key] = {
                    "codice": code,
                    "nome": name,
                    "regione": region,
                    "provincia": province,
                }
                # Aggiungi anche varianti senza articoli
                for prefix in ["l'", "la ", "il ", "lo ", "i ", "gli ", "le "]:
                    if name_key.startswith(prefix):
                        variant = name_key[len(prefix):]
                        schools[variant] = schools[name_key]

    print(f"[postprocess] Caricati {len(schools)} codici scuola dal CSV")
    return schools


def load_valid_codes(csv_path: Path) -> set:
    """Carica set di codici meccanografici validi."""
    codes = set()

    if not csv_path.exists():
        return codes

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = row.get("codice_meccanografico", "").strip()
            if code:
                codes.add(code.upper())

    return codes


def is_valid_code_format(code: str) -> bool:
    """Verifica formato codice meccanografico italiano."""
    # Pattern: 2 lettere + 2 lettere + 5-6 caratteri alfanumerici
    # Es: RMPS12345X, MIIS00900T
    pattern = r'^[A-Z]{2}[A-Z]{2}[A-Z0-9]{5,7}$'
    return bool(re.match(pattern, code.upper()))


def find_invalid_codes(content: str, valid_codes: set) -> list:
    """Trova codici nel testo che non sono nel set valido."""
    # Pattern per trovare codici nel formato (CODICE)
    pattern = r'\(([A-Z]{2}[A-Z]{2}[A-Z0-9]{5,7})\)'
    found = re.findall(pattern, content, re.IGNORECASE)

    invalid = []
    for code in found:
        code_upper = code.upper()
        if is_valid_code_format(code_upper) and code_upper not in valid_codes:
            invalid.append(code)

    return invalid


def fix_hallucinated_codes(content: str, valid_codes: set, schools: dict) -> str:
    """Sostituisce codici inventati con placeholder o rimuove."""
    invalid = find_invalid_codes(content, valid_codes)

    if not invalid:
        return content

    print(f"[postprocess] Trovati {len(invalid)} codici inventati: {invalid[:5]}...")

    for code in set(invalid):
        # Cerca il nome scuola associato nel testo
        # Pattern: Nome Scuola (CODICE)
        pattern = rf'([^(]+?)\s*\({re.escape(code)}\)'
        matches = re.findall(pattern, content, re.IGNORECASE)

        for match in matches:
            name = match.strip().strip('"\'**')
            name_key = name.lower()

            # Cerca codice corretto
            if name_key in schools:
                correct_code = schools[name_key]["codice"]
                old_pattern = f"{name} ({code})"
                new_text = f"**{schools[name_key]['nome']}** ({correct_code})"
                content = content.replace(old_pattern, new_text)
                print(f"[postprocess] Corretto: {code} → {correct_code}")
            else:
                # Rimuovi il codice falso, tieni solo il nome
                old_pattern = f"({code})"
                content = content.replace(old_pattern, "")
                print(f"[postprocess] Rimosso codice inventato: {code}")

    return content


def add_bold_formatting(content: str, schools: dict) -> str:
    """Aggiunge grassetto a nomi scuola, province, regioni."""

    # Lista regioni italiane
    regioni = [
        "Abruzzo", "Basilicata", "Calabria", "Campania", "Emilia-Romagna",
        "Emilia Romagna", "Friuli-Venezia Giulia", "Friuli Venezia Giulia",
        "Lazio", "Liguria", "Lombardia", "Marche", "Molise", "Piemonte",
        "Puglia", "Sardegna", "Sicilia", "Toscana", "Trentino-Alto Adige",
        "Trentino Alto Adige", "Umbria", "Valle d'Aosta", "Veneto"
    ]

    # Province principali (abbreviato)
    province = [
        "Roma", "Milano", "Napoli", "Torino", "Palermo", "Genova", "Bologna",
        "Firenze", "Bari", "Catania", "Venezia", "Verona", "Messina", "Padova",
        "Trieste", "Taranto", "Brescia", "Parma", "Modena", "Reggio Calabria",
        "Reggio Emilia", "Perugia", "Livorno", "Ravenna", "Cagliari", "Foggia",
        "Rimini", "Salerno", "Ferrara", "Sassari", "Latina", "Giugliano",
        "Monza", "Siracusa", "Pescara", "Bergamo", "Forlì", "Trento", "Vicenza",
        "Terni", "Bolzano", "Novara", "Piacenza", "Ancona", "Andria", "Arezzo",
        "Udine", "Cesena", "Lecce", "Pesaro", "Barletta", "Alessandria", "Pistoia",
        "Frosinone", "Rieti", "Viterbo", "Isernia", "Campobasso", "L'Aquila",
        "Teramo", "Chieti", "Avezzano"
    ]

    # Grassetto per regioni (se non già in grassetto)
    for regione in regioni:
        # Evita di doppio-grassettare
        if f"**{regione}**" not in content:
            # Solo se è una parola isolata (non parte di altra parola)
            pattern = rf'\b{re.escape(regione)}\b'
            content = re.sub(pattern, f"**{regione}**", content)

    # Grassetto per province
    for provincia in province:
        if f"**{provincia}**" not in content:
            pattern = rf'\b{re.escape(provincia)}\b'
            # Evita di grassettare dentro parentesi di codici
            content = re.sub(pattern, f"**{provincia}**", content)

    # Grassetto per nomi scuola con codice
    # Pattern: Nome Scuola (CODICE) dove CODICE è valido
    pattern = r'([A-Za-z][^(]{3,50}?)\s*\(([A-Z]{2}[A-Z]{2}[A-Z0-9]{5,7})\)'

    def bold_school(match):
        name = match.group(1).strip()
        code = match.group(2)
        # Non ri-grassettare se già grassetto
        if name.startswith("**") or name.endswith("**"):
            return match.group(0)
        return f"**{name}** ({code})"

    content = re.sub(pattern, bold_school, content)

    return content


def ensure_section_structure(content: str) -> str:
    """Assicura che il report abbia la struttura di sezioni corretta."""

    # Sezioni attese
    expected_sections = [
        ("### Nota Metodologica", True),
        ("### Panoramica Territoriale", False),
        ("### Contesto", False),
        ("### Analisi principale", False),
        ("### Raccomandazioni", False),
        ("### Sintesi", False),
    ]

    # Verifica presenza sezioni
    missing = []
    for section, required in expected_sections:
        if section not in content and required:
            missing.append(section)

    if missing:
        print(f"[postprocess] Sezioni mancanti: {missing}")

    return content


def clean_double_bold(content: str) -> str:
    """Rimuove doppio grassetto (****testo****)."""
    # Pattern per doppio grassetto
    content = re.sub(r'\*\*\*\*([^*]+)\*\*\*\*', r'**\1**', content)
    content = re.sub(r'\*\*\s*\*\*', '', content)  # Rimuovi ** vuoti
    return content


def postprocess_report(
    report_path: Path,
    csv_path: Optional[Path] = None,
    output_path: Optional[Path] = None,
    dry_run: bool = False
) -> str:
    """Applica post-processing completo a un report."""

    if not report_path.exists():
        raise FileNotFoundError(f"Report non trovato: {report_path}")

    # Determina path CSV
    if csv_path is None:
        csv_path = Path("data/attivita.csv")

    # Carica dati
    schools = load_school_data(csv_path)
    valid_codes = load_valid_codes(csv_path)

    print(f"[postprocess] Codici validi: {len(valid_codes)}")

    # Leggi report
    content = report_path.read_text(encoding="utf-8")
    original_len = len(content)

    # Applica trasformazioni
    print("[postprocess] 1. Correzione codici inventati...")
    content = fix_hallucinated_codes(content, valid_codes, schools)

    print("[postprocess] 2. Aggiunta formattazione grassetto...")
    content = add_bold_formatting(content, schools)

    print("[postprocess] 3. Pulizia doppio grassetto...")
    content = clean_double_bold(content)

    print("[postprocess] 4. Verifica struttura sezioni...")
    content = ensure_section_structure(content)

    # Report statistiche
    new_len = len(content)
    print(f"[postprocess] Lunghezza: {original_len} → {new_len} chars")

    if dry_run:
        print("[postprocess] DRY RUN - nessuna modifica salvata")
        return content

    # Salva
    if output_path is None:
        output_path = report_path

    output_path.write_text(content, encoding="utf-8")
    print(f"[postprocess] Salvato: {output_path}")

    return content


def main():
    parser = argparse.ArgumentParser(description="Post-process meta-report")
    parser.add_argument("report", type=Path, help="Path al report da processare")
    parser.add_argument("--csv", type=Path, default=Path("data/attivita.csv"),
                       help="Path al CSV attività")
    parser.add_argument("--output", "-o", type=Path, help="Path output (default: sovrascrive)")
    parser.add_argument("--dry-run", "-n", action="store_true",
                       help="Mostra modifiche senza salvare")

    args = parser.parse_args()

    postprocess_report(
        report_path=args.report,
        csv_path=args.csv,
        output_path=args.output,
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    main()
