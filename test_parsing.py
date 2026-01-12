
import re

REPORT_SUFFIXES = ("_best_practices", "_attivita", "_skeleton")

def strip_report_suffix(stem: str) -> str:
    # Remove common suffixes first
    for suffix in REPORT_SUFFIXES:
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
    return stem

def split_report_filters(identifier: str) -> tuple[str, dict, str]:
    clean_id = strip_report_suffix(identifier)
    
    # Check for timestamp prefix (YYYYMMDD_HHMM__)
    # Regex: optional timestamp group, then the rest
    match = re.match(r"^(?P<ts>\d{8}_\d{4}__)?(?P<rest>.*)$", clean_id)
    if not match:
        base = clean_id
    else:
        rest = match.group("rest")
        # Ensure we strip known prefixes if present in new format
        if rest.startswith("Tema_"):
            rest = rest[5:]
        elif rest.startswith("Scuola_"):
            rest = rest[7:]
        base = rest

    # Now parse standard parts
    parts = base.split("__")
    core_id = parts[0]
    
    filters = {}
    profile = ""
    for part in parts[1:]:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        if key == "profile":
            profile = value.replace("-", " ")
            continue
        label = value.replace("+", ", ").replace("-", " ")
        filters[key] = label
        
    return core_id, filters, profile

# Test cases
files = [
    "20260113_0016__Scuola_RMIS01600N__profile=overview_attivita",
    "20260112_2320__Tema_orientamento__ordine_grado=ii-grado__regione=marche_skeleton"
]

for f in files:
    print(f"Testing: {f}")
    core_id, filters, profile = split_report_filters(f)
    print(f"  Core ID: {core_id}")
    print(f"  Filters: {filters}")
    print(f"  Profile: {profile}")
