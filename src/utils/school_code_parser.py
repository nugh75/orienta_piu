#!/usr/bin/env python3
"""
Parser per codici meccanografici delle scuole italiane.
Funzioni per estrarre, validare e manipolare i codici scuola.
"""

import re
from typing import Optional

# Pattern per codice meccanografico italiano
# Formato: 2 lettere (provincia) + 2 caratteri (tipo) + 6 caratteri alfanumerici
SCHOOL_CODE_PATTERN = re.compile(r'([A-Z]{2}[A-Z0-9]{2}[A-Z0-9]{6})', re.IGNORECASE)

# Pattern più permissivo per casi edge
SCHOOL_CODE_PATTERN_LOOSE = re.compile(r'([A-Z]{2,4}[A-Z0-9]{5,8}[A-Z0-9])', re.IGNORECASE)


def extract_canonical_code(filename_or_code: str) -> str:
    """
    Estrae il codice meccanografico standard da un filename o stringa.

    Gestisce casi come:
    - "BNIS01100L" → "BNIS01100L"
    - "BNIS01100L_analysis.json" → "BNIS01100L"
    - "RHO_MIPC09500C.pdf" → "MIPC09500C"
    - "ptof_RMPL355003_v2.md" → "RMPL355003"

    Args:
        filename_or_code: Nome file o stringa contenente il codice

    Returns:
        Codice meccanografico estratto in uppercase, o input originale se non trovato
    """
    if not filename_or_code:
        return ""

    # Prima prova con pattern standard (10 caratteri)
    match = SCHOOL_CODE_PATTERN.search(filename_or_code.upper())
    if match:
        return match.group(1).upper()

    # Fallback a pattern più permissivo
    match = SCHOOL_CODE_PATTERN_LOOSE.search(filename_or_code.upper())
    if match:
        return match.group(1).upper()

    # Se non trova nulla, ritorna input pulito
    return filename_or_code.strip().upper()


def validate_school_code(code: str) -> bool:
    """
    Valida se una stringa è un codice meccanografico valido.

    Args:
        code: Codice da validare

    Returns:
        True se il codice è valido, False altrimenti
    """
    if not code:
        return False

    # Deve essere esattamente 10 caratteri
    if len(code) != 10:
        return False

    # Deve matchare il pattern
    match = SCHOOL_CODE_PATTERN.match(code.upper())
    return match is not None


def get_provincia_sigla(school_code: str) -> str:
    """
    Estrae la sigla della provincia (prime 2 lettere) dal codice meccanografico.

    Args:
        school_code: Codice meccanografico (es. "BNIS01100L")

    Returns:
        Sigla provincia (es. "BN") o stringa vuota se non valido

    Example:
        >>> get_provincia_sigla("BNIS01100L")
        'BN'
        >>> get_provincia_sigla("MIPC09500C")
        'MI'
    """
    code = extract_canonical_code(school_code)
    if len(code) >= 2:
        return code[:2].upper()
    return ""


def get_tipo_scuola_from_code(school_code: str) -> Optional[str]:
    """
    Estrae il tipo di scuola dal codice meccanografico (caratteri 3-4).

    Mapping comuni:
    - IC: Istituto Comprensivo
    - PC: Liceo Classico
    - PS: Liceo Scientifico
    - PL: Liceo Linguistico
    - PM: Liceo Scienze Umane
    - IS: Istituto Superiore
    - TF: Istituto Tecnico
    - RF: Istituto Professionale
    - EE: Scuola Primaria
    - MM: Scuola Media (I Grado)
    - AA: Scuola Infanzia

    Args:
        school_code: Codice meccanografico

    Returns:
        Sigla tipo scuola (es. "PC", "IS") o None se non estratto
    """
    code = extract_canonical_code(school_code)
    if len(code) >= 4:
        return code[2:4].upper()
    return None


def parse_school_code(school_code: str) -> dict:
    """
    Analizza un codice meccanografico e restituisce le sue componenti.

    Args:
        school_code: Codice meccanografico

    Returns:
        Dict con:
        - canonical_code: codice estratto e normalizzato
        - provincia_sigla: prime 2 lettere (sigla provincia)
        - tipo_sigla: caratteri 3-4 (tipo scuola)
        - progressivo: ultimi 6 caratteri
        - is_valid: se il codice è valido

    Example:
        >>> parse_school_code("BNIS01100L")
        {
            'canonical_code': 'BNIS01100L',
            'provincia_sigla': 'BN',
            'tipo_sigla': 'IS',
            'progressivo': '01100L',
            'is_valid': True
        }
    """
    code = extract_canonical_code(school_code)

    result = {
        'canonical_code': code,
        'provincia_sigla': '',
        'tipo_sigla': '',
        'progressivo': '',
        'is_valid': False
    }

    if len(code) >= 10:
        result['provincia_sigla'] = code[:2]
        result['tipo_sigla'] = code[2:4]
        result['progressivo'] = code[4:]
        result['is_valid'] = validate_school_code(code)
    elif len(code) >= 4:
        result['provincia_sigla'] = code[:2]
        result['tipo_sigla'] = code[2:4]
        if len(code) > 4:
            result['progressivo'] = code[4:]

    return result
