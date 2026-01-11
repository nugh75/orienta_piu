"""
Configurazione Temi Canonici - Fonte Unica di Verità

Questo modulo definisce i temi ufficiali per le attività di orientamento.
Tutte le altre parti del sistema dovrebbero importare da qui.

Uso:
    from src.config.themes import CANONICAL_THEMES, normalize_theme, DIMENSIONS
"""

from typing import Optional

# =============================================================================
# TEMI CANONICI (22 temi principali)
# =============================================================================

CANONICAL_THEMES = [
    "Orientamento",
    "PCTO/Alternanza",
    "Inclusione e BES",
    "Digitalizzazione",
    "Cittadinanza e Legalità",
    "Valutazione e Autovalutazione",
    "STEM e Ricerca",
    "Lingue Straniere",
    "Arte e Creatività",
    "Sostenibilità e Ambiente",
    "Rapporti con Famiglie",
    "Intercultura",
    "Matematica e Logica",
    "Lettura e Scrittura",
    "Continuità e Accoglienza",
    "Sport e Benessere",
    "Prevenzione Disagio",
    "Imprenditorialità",
    "Formazione Docenti",
    "Musica e Teatro",
    "Azioni di Sistema e Governance",
    "Altro",  # fallback
]

# =============================================================================
# ALIAS PER NORMALIZZAZIONE
# Mappa varianti sporche ai temi canonici
# =============================================================================

THEME_ALIASES = {
    # STEM variants
    "STEM/STEAM": "STEM e Ricerca",
    "Scienze e Ricerca": "STEM e Ricerca",
    "STEAM": "STEM e Ricerca",
    "Scienze": "STEM e Ricerca",
    
    # Benessere variants
    "Benessere": "Sport e Benessere",
    "Salute e Benessere": "Sport e Benessere",
    "Benessere e Salute": "Sport e Benessere",
    "Salute": "Sport e Benessere",
    "Educazione alla Salute": "Sport e Benessere",
    
    # Cittadinanza variants
    "Educazione Civica": "Cittadinanza e Legalità",
    "Cittadinanza": "Cittadinanza e Legalità",
    "Legalità": "Cittadinanza e Legalità",
    
    # Intercultura variants
    "Intercultura e Lingue": "Intercultura",
    "Multiculturalità": "Intercultura",
    
    # Didattica/Sistema variants
    "Governance": "Azioni di Sistema e Governance",
    "Organizzazione": "Azioni di Sistema e Governance",
    "Didattica": "Azioni di Sistema e Governance",
    "Metodologie Didattiche Innovative": "Azioni di Sistema e Governance",
    
    # Arte variants
    "Creatività": "Arte e Creatività",
    
    # Prevenzione variants
    "Bullismo e Cyberbullismo": "Prevenzione Disagio",
    "Dispersione Scolastica": "Prevenzione Disagio",
    
    # Storia/Geografia -> Altro
    "Storia": "Altro",
    "Geografia": "Altro",
    "Filosofia": "Altro",
    "Storia e Geografia": "Altro",
    
    # Esperienze territoriali -> mapping basato su contesto
    "Esperienze Territoriali Significative": "Altro",
    "Esperienze Territoriali": "Altro",
    
    # Partnership
    "Partnership e Collaborazioni Strategiche": "Azioni di Sistema e Governance",
    "Partnership": "Azioni di Sistema e Governance",
    
    # Progetti
    "Progetti e Attività Esemplari": "Altro",
}

# Set per lookup veloce
_CANONICAL_SET = set(CANONICAL_THEMES)
_CANONICAL_LOWER = {t.lower(): t for t in CANONICAL_THEMES}


def normalize_theme(raw: str) -> str:
    """
    Normalizza un tema al suo valore canonico.
    
    Args:
        raw: Tema grezzo (potenzialmente sporco o alias)
    
    Returns:
        Tema canonico corrispondente, o "Altro" se non riconosciuto
    
    Examples:
        >>> normalize_theme("STEM/STEAM")
        'STEM e Ricerca'
        >>> normalize_theme("Orientamento")
        'Orientamento'
        >>> normalize_theme("Random stuff")
        'Altro'
    """
    if not raw or not raw.strip():
        return "Altro"
    
    raw = raw.strip()
    
    # Già canonico?
    if raw in _CANONICAL_SET:
        return raw
    
    # È un alias noto?
    if raw in THEME_ALIASES:
        return THEME_ALIASES[raw]
    
    # Match case-insensitive
    raw_lower = raw.lower()
    if raw_lower in _CANONICAL_LOWER:
        return _CANONICAL_LOWER[raw_lower]
    
    # Match parziale (es. "Orientamento scolastico" -> "Orientamento")
    for canonical in CANONICAL_THEMES:
        if canonical.lower() in raw_lower or raw_lower in canonical.lower():
            return canonical
    
    # Fallback
    return "Altro"


def normalize_themes_string(raw: str, separator: str = "|") -> str:
    """
    Normalizza una stringa con temi multipli separati.
    
    Args:
        raw: Stringa tipo "STEM/STEAM|Orientamento|Random"
        separator: Separatore tra temi (default: "|")
    
    Returns:
        Stringa normalizzata con temi unici
    
    Examples:
        >>> normalize_themes_string("STEM/STEAM|Orientamento")
        'STEM e Ricerca|Orientamento'
    """
    if not raw or not raw.strip():
        return "Altro"
    
    themes = [t.strip() for t in raw.split(separator) if t.strip()]
    normalized = list(dict.fromkeys(normalize_theme(t) for t in themes))  # preserva ordine, rimuove duplicati
    return separator.join(normalized) if normalized else "Altro"


# =============================================================================
# DIMENSIONS - Dizionario per CLI e report tematici
# =============================================================================

def _theme_to_key(theme: str) -> str:
    """Converte nome tema in chiave CLI-friendly."""
    return (theme.lower()
            .replace("/", "_")
            .replace(" e ", "_")
            .replace(" ", "_")
            .replace("'", ""))

# Genera automaticamente da CANONICAL_THEMES
DIMENSIONS = {
    _theme_to_key(theme): theme 
    for theme in CANONICAL_THEMES 
    if theme != "Altro"  # "Altro" non è una dimensione selezionabile
}

# Alias per retrocompatibilità (nomi vecchi -> nuovi)
DIMENSIONS.update({
    "pcto": "PCTO/Alternanza",
    "stem": "STEM e Ricerca",
    "inclusione": "Inclusione e BES",
    "cittadinanza": "Cittadinanza e Legalità",
    "famiglie": "Rapporti con Famiglie",
    "disagio": "Prevenzione Disagio",
    "sistema": "Azioni di Sistema e Governance",
    "arte": "Arte e Creatività",
    "lingue": "Lingue Straniere",
    "sport": "Sport e Benessere",
    "continuita": "Continuità e Accoglienza",
    "valutazione": "Valutazione e Autovalutazione",
    "formazione_docenti": "Formazione Docenti",
    "musica": "Musica e Teatro",
    "lettura": "Lettura e Scrittura",
    "matematica": "Matematica e Logica",
})
