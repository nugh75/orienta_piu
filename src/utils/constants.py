#!/usr/bin/env python3
"""
Costanti centralizzate per il sistema di analisi PTOF.
Contiene mapping geografici, province metropolitane e funzioni helper.
"""

from typing import Tuple, Optional, Dict

# ============================================================================
# SIGLA PROVINCIA MAP
# Mappa: sigla provincia (prime 2 lettere codice meccanografico) → (provincia, regione, area_geografica)
# ============================================================================

SIGLA_PROVINCIA_MAP: Dict[str, Tuple[str, str, str]] = {
    # NORD OVEST
    "TO": ("Torino", "Piemonte", "Nord Ovest"),
    "VC": ("Vercelli", "Piemonte", "Nord Ovest"),
    "NO": ("Novara", "Piemonte", "Nord Ovest"),
    "CN": ("Cuneo", "Piemonte", "Nord Ovest"),
    "AT": ("Asti", "Piemonte", "Nord Ovest"),
    "AL": ("Alessandria", "Piemonte", "Nord Ovest"),
    "BI": ("Biella", "Piemonte", "Nord Ovest"),
    "VB": ("Verbano-Cusio-Ossola", "Piemonte", "Nord Ovest"),
    "AO": ("Aosta", "Valle d'Aosta", "Nord Ovest"),
    "VA": ("Varese", "Lombardia", "Nord Ovest"),
    "CO": ("Como", "Lombardia", "Nord Ovest"),
    "SO": ("Sondrio", "Lombardia", "Nord Ovest"),
    "MI": ("Milano", "Lombardia", "Nord Ovest"),
    "BG": ("Bergamo", "Lombardia", "Nord Ovest"),
    "BS": ("Brescia", "Lombardia", "Nord Ovest"),
    "PV": ("Pavia", "Lombardia", "Nord Ovest"),
    "CR": ("Cremona", "Lombardia", "Nord Ovest"),
    "MN": ("Mantova", "Lombardia", "Nord Ovest"),
    "LC": ("Lecco", "Lombardia", "Nord Ovest"),
    "LO": ("Lodi", "Lombardia", "Nord Ovest"),
    "MB": ("Monza e Brianza", "Lombardia", "Nord Ovest"),
    "GE": ("Genova", "Liguria", "Nord Ovest"),
    "IM": ("Imperia", "Liguria", "Nord Ovest"),
    "SP": ("La Spezia", "Liguria", "Nord Ovest"),
    "SV": ("Savona", "Liguria", "Nord Ovest"),

    # NORD EST
    "VR": ("Verona", "Veneto", "Nord Est"),
    "VI": ("Vicenza", "Veneto", "Nord Est"),
    "BL": ("Belluno", "Veneto", "Nord Est"),
    "TV": ("Treviso", "Veneto", "Nord Est"),
    "VE": ("Venezia", "Veneto", "Nord Est"),
    "PD": ("Padova", "Veneto", "Nord Est"),
    "RO": ("Rovigo", "Veneto", "Nord Est"),
    "UD": ("Udine", "Friuli-Venezia Giulia", "Nord Est"),
    "GO": ("Gorizia", "Friuli-Venezia Giulia", "Nord Est"),
    "TS": ("Trieste", "Friuli-Venezia Giulia", "Nord Est"),
    "PN": ("Pordenone", "Friuli-Venezia Giulia", "Nord Est"),
    "BZ": ("Bolzano", "Trentino-Alto Adige", "Nord Est"),
    "TN": ("Trento", "Trentino-Alto Adige", "Nord Est"),
    "BO": ("Bologna", "Emilia-Romagna", "Nord Est"),
    "FE": ("Ferrara", "Emilia-Romagna", "Nord Est"),
    "FO": ("Forlì-Cesena", "Emilia-Romagna", "Nord Est"),
    "FC": ("Forlì-Cesena", "Emilia-Romagna", "Nord Est"),
    "MO": ("Modena", "Emilia-Romagna", "Nord Est"),
    "PR": ("Parma", "Emilia-Romagna", "Nord Est"),
    "PC": ("Piacenza", "Emilia-Romagna", "Nord Est"),
    "RA": ("Ravenna", "Emilia-Romagna", "Nord Est"),
    "RE": ("Reggio Emilia", "Emilia-Romagna", "Nord Est"),
    "RN": ("Rimini", "Emilia-Romagna", "Nord Est"),

    # CENTRO
    "AR": ("Arezzo", "Toscana", "Centro"),
    "FI": ("Firenze", "Toscana", "Centro"),
    "GR": ("Grosseto", "Toscana", "Centro"),
    "LI": ("Livorno", "Toscana", "Centro"),
    "LU": ("Lucca", "Toscana", "Centro"),
    "MS": ("Massa-Carrara", "Toscana", "Centro"),
    "PI": ("Pisa", "Toscana", "Centro"),
    "PT": ("Pistoia", "Toscana", "Centro"),
    "PO": ("Prato", "Toscana", "Centro"),
    "SI": ("Siena", "Toscana", "Centro"),
    "PG": ("Perugia", "Umbria", "Centro"),
    "TR": ("Terni", "Umbria", "Centro"),
    "AN": ("Ancona", "Marche", "Centro"),
    "AP": ("Ascoli Piceno", "Marche", "Centro"),
    "FM": ("Fermo", "Marche", "Centro"),
    "MC": ("Macerata", "Marche", "Centro"),
    "PU": ("Pesaro e Urbino", "Marche", "Centro"),
    "RM": ("Roma", "Lazio", "Centro"),
    "FR": ("Frosinone", "Lazio", "Centro"),
    "LT": ("Latina", "Lazio", "Centro"),
    "RI": ("Rieti", "Lazio", "Centro"),
    "VT": ("Viterbo", "Lazio", "Centro"),

    # SUD
    "AQ": ("L'Aquila", "Abruzzo", "Sud"),
    "CH": ("Chieti", "Abruzzo", "Sud"),
    "PE": ("Pescara", "Abruzzo", "Sud"),
    "TE": ("Teramo", "Abruzzo", "Sud"),
    "CB": ("Campobasso", "Molise", "Sud"),
    "IS": ("Isernia", "Molise", "Sud"),
    "AV": ("Avellino", "Campania", "Sud"),
    "BN": ("Benevento", "Campania", "Sud"),
    "CE": ("Caserta", "Campania", "Sud"),
    "NA": ("Napoli", "Campania", "Sud"),
    "SA": ("Salerno", "Campania", "Sud"),
    "BA": ("Bari", "Puglia", "Sud"),
    "BR": ("Brindisi", "Puglia", "Sud"),
    "BT": ("Barletta-Andria-Trani", "Puglia", "Sud"),
    "FG": ("Foggia", "Puglia", "Sud"),
    "LE": ("Lecce", "Puglia", "Sud"),
    "TA": ("Taranto", "Puglia", "Sud"),
    "MT": ("Matera", "Basilicata", "Sud"),
    "PZ": ("Potenza", "Basilicata", "Sud"),
    "CS": ("Cosenza", "Calabria", "Sud"),
    "CZ": ("Catanzaro", "Calabria", "Sud"),
    "KR": ("Crotone", "Calabria", "Sud"),
    "RC": ("Reggio Calabria", "Calabria", "Sud"),
    "VV": ("Vibo Valentia", "Calabria", "Sud"),

    # ISOLE
    "AG": ("Agrigento", "Sicilia", "Isole"),
    "CL": ("Caltanissetta", "Sicilia", "Isole"),
    "CT": ("Catania", "Sicilia", "Isole"),
    "EN": ("Enna", "Sicilia", "Isole"),
    "ME": ("Messina", "Sicilia", "Isole"),
    "PA": ("Palermo", "Sicilia", "Isole"),
    "RG": ("Ragusa", "Sicilia", "Isole"),
    "SR": ("Siracusa", "Sicilia", "Isole"),
    "TP": ("Trapani", "Sicilia", "Isole"),
    "CA": ("Cagliari", "Sardegna", "Isole"),
    "CI": ("Carbonia-Iglesias", "Sardegna", "Isole"),
    "NU": ("Nuoro", "Sardegna", "Isole"),
    "OG": ("Ogliastra", "Sardegna", "Isole"),
    "OT": ("Olbia-Tempio", "Sardegna", "Isole"),
    "OR": ("Oristano", "Sardegna", "Isole"),
    "SS": ("Sassari", "Sardegna", "Isole"),
    "SU": ("Sud Sardegna", "Sardegna", "Isole"),
    "VS": ("Medio Campidano", "Sardegna", "Isole"),
}

# ============================================================================
# PROVINCE METROPOLITANE (ISTAT)
# Le 14 città metropolitane italiane
# ============================================================================

PROVINCE_METROPOLITANE = {
    "Roma", "Milano", "Napoli", "Torino", "Bari", "Firenze",
    "Bologna", "Genova", "Venezia", "Palermo", "Catania",
    "Messina", "Reggio Calabria", "Cagliari"
}

# ============================================================================
# VALORI STANDARD
# ============================================================================

AREA_GEOGRAFICA_VALUES = ["Nord Ovest", "Nord Est", "Centro", "Sud", "Isole"]
TERRITORIO_VALUES = ["Metropolitano", "Non Metropolitano"]

# Mapping per normalizzazione area_geografica da varie fonti
AREA_GEOGRAFICA_NORMALIZATION = {
    "NORD OVEST": "Nord Ovest",
    "NORD-OVEST": "Nord Ovest",
    "NORDOVEST": "Nord Ovest",
    "NORD EST": "Nord Est",
    "NORD-EST": "Nord Est",
    "NORDEST": "Nord Est",
    "NORD": "Nord Ovest",  # Fallback se non specificato
    "CENTRO": "Centro",
    "SUD": "Sud",
    "ISOLE": "Isole",
    "SUD E ISOLE": "Sud",  # Fallback quando non specificato
    "SUD-ISOLE": "Sud",
}

# Mapping regione → area geografica
REGIONE_TO_AREA = {
    "Piemonte": "Nord Ovest",
    "Valle d'Aosta": "Nord Ovest",
    "Lombardia": "Nord Ovest",
    "Liguria": "Nord Ovest",
    "Veneto": "Nord Est",
    "Friuli-Venezia Giulia": "Nord Est",
    "Friuli Venezia Giulia": "Nord Est",
    "Trentino-Alto Adige": "Nord Est",
    "Emilia-Romagna": "Nord Est",
    "Toscana": "Centro",
    "Umbria": "Centro",
    "Marche": "Centro",
    "Lazio": "Centro",
    "Abruzzo": "Sud",
    "Molise": "Sud",
    "Campania": "Sud",
    "Puglia": "Sud",
    "Basilicata": "Sud",
    "Calabria": "Sud",
    "Sicilia": "Isole",
    "Sardegna": "Isole",
}


# ============================================================================
# FUNZIONI HELPER
# ============================================================================

def get_territorio(provincia: str) -> str:
    """
    Determina se una provincia è metropolitana o meno.

    Args:
        provincia: Nome della provincia (es. "Milano", "Benevento")

    Returns:
        "Metropolitano" o "Non Metropolitano"
    """
    if not provincia or provincia in ("ND", "", None):
        return "ND"

    # Normalizza per confronto case-insensitive
    provincia_normalized = provincia.strip().title()

    # Controlla anche varianti
    if provincia_normalized in PROVINCE_METROPOLITANE:
        return "Metropolitano"

    # Controlla anche senza accenti o con varianti
    for metro in PROVINCE_METROPOLITANE:
        if metro.upper() == provincia_normalized.upper():
            return "Metropolitano"

    return "Non Metropolitano"


def normalize_area_geografica(area: str, regione: Optional[str] = None, provincia_sigla: Optional[str] = None) -> str:
    """
    Normalizza il valore di area_geografica a uno dei valori standard.

    Args:
        area: Valore grezzo (es. "NORD OVEST", "Nord-Est", "SUD E ISOLE")
        regione: Regione della scuola (opzionale, per risolvere "NORD"/"SUD E ISOLE")
        provincia_sigla: Sigla provincia (opzionale, per risolvere ambiguità)

    Returns:
        Valore normalizzato (es. "Nord Ovest", "Nord Est", "Sud", "Isole")
    """
    def area_from_context(reg: Optional[str], sigla: Optional[str]) -> str:
        if sigla:
            sigla_norm = sigla.strip().upper()
            if sigla_norm in SIGLA_PROVINCIA_MAP:
                return SIGLA_PROVINCIA_MAP[sigla_norm][2]
        if reg:
            area_ctx = get_area_from_regione(reg)
            if area_ctx != "ND":
                return area_ctx
        return "ND"

    if not area or area in ("ND", "", None):
        return area_from_context(regione, provincia_sigla)

    area_upper = area.strip().upper()
    if area_upper in ("NORD", "SUD E ISOLE", "SUD-ISOLE"):
        ctx_area = area_from_context(regione, provincia_sigla)
        if ctx_area != "ND":
            return ctx_area

    normalized = AREA_GEOGRAFICA_NORMALIZATION.get(area_upper)
    if normalized:
        return normalized

    return area_from_context(regione, provincia_sigla)


def get_area_from_regione(regione: str) -> str:
    """
    Ottiene l'area geografica dalla regione.

    Args:
        regione: Nome della regione (es. "Lombardia", "Campania")

    Returns:
        Area geografica (es. "Nord Ovest", "Sud")
    """
    if not regione or regione in ("ND", "", None):
        return "ND"

    # Prova match esatto
    if regione in REGIONE_TO_AREA:
        return REGIONE_TO_AREA[regione]

    # Prova match case-insensitive
    regione_title = regione.strip().title()
    for reg, area in REGIONE_TO_AREA.items():
        if reg.upper() == regione_title.upper():
            return area

    return "ND"


def get_geo_from_sigla(school_code: str) -> Dict[str, str]:
    """
    Ottiene tutti i dati geografici dalla sigla provincia nel codice meccanografico.

    Args:
        school_code: Codice meccanografico (es. "BNIS01100L", "MIPC09500C")

    Returns:
        Dict con provincia, regione, area_geografica, territorio

    Example:
        >>> get_geo_from_sigla("BNIS01100L")
        {
            'provincia': 'Benevento',
            'regione': 'Campania',
            'area_geografica': 'Sud',
            'territorio': 'Non Metropolitano'
        }
    """
    result = {
        'provincia': 'ND',
        'regione': 'ND',
        'area_geografica': 'ND',
        'territorio': 'ND'
    }

    if not school_code or len(school_code) < 2:
        return result

    sigla = school_code[:2].upper()

    if sigla in SIGLA_PROVINCIA_MAP:
        provincia, regione, area = SIGLA_PROVINCIA_MAP[sigla]
        result['provincia'] = provincia
        result['regione'] = regione
        result['area_geografica'] = area
        result['territorio'] = get_territorio(provincia)

    return result


def get_provincia_sigla(school_code: str) -> str:
    """
    Estrae la sigla della provincia dal codice meccanografico.

    Args:
        school_code: Codice meccanografico (es. "BNIS01100L")

    Returns:
        Sigla provincia (es. "BN") o stringa vuota se non valido
    """
    if not school_code or len(school_code) < 2:
        return ""
    return school_code[:2].upper()
