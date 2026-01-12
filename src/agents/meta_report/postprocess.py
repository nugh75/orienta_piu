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
    """Aggiunge grassetto - DISABLED per semplificare.
    
    Ora restituisce il contenuto senza modifiche.
    """
    # Rimuovi TUTTI gli asterischi doppi orfani o malformati
    # per garantire un output pulito
    content = re.sub(r'\*\*\s*\)', ')', content)  # **) -> )
    content = re.sub(r'\(\s*\*\*', '(', content)  # (** -> (
    content = re.sub(r'\*\*\.\*\*', '.', content)  # **.** -> .
    content = re.sub(r'\*\*\*+', '', content)  # *** or more -> nothing
    # Rimuovi bold markers residui attorno a codici
    content = re.sub(r'\*\*([A-Z]{2}[A-Z0-9]{8})\*\*', r'\1', content)
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
    """Rimuove doppio grassetto e grassetto malformato."""
    # Standard double bold
    content = re.sub(r'\*\*\*\*([^*]+)\*\*\*\*', r'**\1**', content)
    
    # Empty bold pairs
    content = re.sub(r'\*\*\s*\*\*', '', content)
    
    # Bold with only whitespace
    content = re.sub(r'\*\*\s+\*\*', ' ', content)
    
    # Orphaned ** at end of line
    content = re.sub(r'\*\*\s*$', '', content, flags=re.MULTILINE)
    
    # Orphaned ** at start followed by space
    content = re.sub(r'^\*\*\s+', '', content, flags=re.MULTILINE)
    
    return content


def fix_bold_acronyms(content: str) -> str:
    """Fix acronyms where only the first letter is bolded."""
    # Universal fix: **X**. -> X.
    content = re.sub(r'\*\*([A-Z])\*\*\.', r'\1.', content)
    # Fix **G**. De -> G. De (matches with space if previous didn't catch)
    content = re.sub(r'\*\*([A-Z])\*\*(\s)', r'\1\2', content)
    return content


def strip_long_bolds(content: str) -> str:
    """Remove bold formatting from long text blocks (> 40 chars)."""
    def _repl(match):
        text = match.group(1)
        # If long, strip the ** wrapper.
        if len(text) > 40:
            return text
        # Keep wrapper
        return f"**{text}**"
    
    # Use non-greedy match including newlines
    return re.sub(r'\*\*(.+?)\*\*', _repl, content, flags=re.DOTALL)



def fix_word_bold(content: str) -> str:
    """Fix unclosed bold markers before punctuation to prevent bleeding."""
    # Matches: **Text followed by punctuation.
    # Limit to 30 chars to be safe (avoid bolding whole sentences).
    return re.sub(r'(\*\*[a-zA-Z0-9À-ÿ\s-]{1,30})(?=[,.:;?!])(?<!\*)', r'\1**', content)


def fix_unclosed_bold(content: str) -> str:
    """Fix unclosed bold markers by forcibly closing them if unbalanced."""
    lines = content.split('\n')
    new_lines = []
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            new_lines.append(line)
            continue

        # 1. Table Fix: Close bold in cells individually
        if stripped.startswith('|') and "**" in line:
            parts = line.split('|')
            new_parts = []
            for part in parts:
                if part.count("**") % 2 != 0:
                     part += "**" 
                new_parts.append(part)
            line = '|'.join(new_parts)

        # 2. Smart List/Header Fix
        # If line starts with bold and is unbalanced, try to close before punctuation
        if (stripped.startswith('- **') or stripped.startswith('* **') or stripped.startswith('**')) and "**" in line:
             if line.count("**") % 2 != 0:
                 # Check for colon or (
                 punctuation_match = re.search(r'([:(])', line)
                 if punctuation_match:
                     idx = punctuation_match.start()
                     # Insert ** before the punctuation
                     # But ensure we don't created nested **?
                     # Since count is odd, inserting one ** makes it even.
                     line = line[:idx] + "**" + line[idx:]
                     
        # 3. General Fallback: If line still has odd **, handle based on length
        if line.count("**") % 2 != 0:
            # If line is long (> 150 chars), it's likely a paragraph.
            # Closing at the end would bold a huge chunk.
            # safe strategy: REMOVE the last bold marker.
            if len(line) > 150:
                # Remove last occurrence of **
                # (Reverse, replace 1, reverse back)
                line = line[::-1].replace("**", "", 1)[::-1]
            else:
                # Short line (header, list item), close at end
                line = line.rstrip() + "**"

        new_lines.append(line)
        
    return '\n'.join(new_lines)

def fix_broken_bold(content: str) -> str:
    """Fix bold markers that appear in the middle of words."""
    
    # Multiple passes to catch cascading cases
    for _ in range(3):
        # Remove ** that appears inside words (letter before AND after)
        # e.g., "word**mid**word" or "word**mid"
        content = re.sub(r'(\w)\*\*(\w)', r'\1\2', content)
    
    # Remove ** before uppercase codes (likely hallucinated)
    # e.g., "F**RPC" → "FRPC"
    content = re.sub(r'\*\*(?=[A-Z]{2}[A-Z0-9])', '', content)
    
    # Remove ** between lowercase letters mid-word
    content = re.sub(r'(?<=[a-z])\*\*(?=[a-z])', '', content)
    
    # Fix patterns like "Name** (CODE)" → "Name (CODE)"
    content = re.sub(r'\*\*\s*\(([A-Z]{4}[A-Z0-9]+)\)', r' (\1)', content)
    
    # Fix patterns like "(si collega anche a: In**clusione" 
    content = re.sub(r':\s*([A-Za-z]+)\*\*([a-z]+)', r': \1\2', content)
    
    # Fix patterns like "**Anien**e" → "Aniene" (bold mid-word with ** before)
    content = re.sub(r'\*\*([A-Za-z]+)\*\*([a-z]+)', r'\1\2', content)
    
    # Fix patterns like "inclusion**e" → "inclusione" (** before last letters)
    content = re.sub(r'([a-z]+)\*\*([a-z]{1,3})\b', r'\1\2', content)
    
    # Fix orphaned ** followed immediately by lowercase
    content = re.sub(r'\*\*([a-z])', r'\1', content)
    
    # Fix orphaned ** preceded by lowercase letter
    content = re.sub(r'([a-z])\*\*(?=[\s.,;:)]|$)', r'\1', content)
    
    # Remove ** inside parentheses that shouldn't be there
    # e.g. "(FRPC02500X)** → "(FRPC02500X)"
    content = re.sub(r'\)\*\*(?=[^\*])', r')', content)
    
    return content


def remove_duplicate_headers(content: str) -> str:
    """Remove consecutive duplicate markdown headers."""
    lines = content.split('\n')
    result = []
    prev_line = None
    
    for line in lines:
        stripped = line.strip()
        # Skip if this line is identical to previous and starts with #
        if stripped.startswith('#') and stripped == (prev_line or "").strip():
            continue
        result.append(line)
        prev_line = line
    
    return '\n'.join(result)


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
    print("[postprocess] 0. Riparazione grassetti non chiusi...")
    content = fix_unclosed_bold(content)

    print("[postprocess] 1. Rimozione bold malformato...")
    content = fix_broken_bold(content)

    print("[postprocess] 2. Rimozione header duplicati...")
    content = remove_duplicate_headers(content)

    print("[postprocess] 3. Correzione codici inventati...")
    content = fix_hallucinated_codes(content, valid_codes, schools)

    print("[postprocess] 4. Aggiunta formattazione grassetto...")
    content = add_bold_formatting(content, schools)

    print("[postprocess] 5. Pulizia finale grassetto...")
    content = strip_long_bolds(content)
    content = fix_bold_acronyms(content)
    content = fix_word_bold(content)
    content = clean_double_bold(content)

    print("[postprocess] 5b. Riparazione finale grassetti non chiusi...")
    content = fix_unclosed_bold(content)

    print("[postprocess] 6. Verifica struttura sezioni...")
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
