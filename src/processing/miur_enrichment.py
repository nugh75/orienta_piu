# MIUR Enrichment - Arricchimento dati con database MIUR
# Fase 1, 2, 3 del piano di risoluzione incongruenze

import os
import re
import json
import requests
from typing import Dict, Optional, Tuple, List
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.school_database import SchoolDatabase
from src.utils.constants import get_area_from_regione, normalize_area_geografica

# Import del database dei comuni (fallback per area_geografica)
try:
    from src.utils.comuni_database import ComuniDatabase
    _comuni_db = None
    def get_comuni_db():
        global _comuni_db
        if _comuni_db is None:
            _comuni_db = ComuniDatabase()
        return _comuni_db
except ImportError:
    get_comuni_db = None
    print("⚠️ ComuniDatabase non disponibile - usa fallback statico")

# Singleton per il database
_school_db = None

def get_school_db() -> SchoolDatabase:
    """Get or create SchoolDatabase singleton"""
    global _school_db
    if _school_db is None:
        _school_db = SchoolDatabase()
    return _school_db


# =============================================================================
# FASE 4: Ricerca web per scuole non trovate in MIUR
# =============================================================================

def search_school_online(school_name: str) -> Optional[Dict]:
    """
    Cerca informazioni sulla scuola online usando DuckDuckGo.
    Estrae comune, provincia, regione dalla ricerca.
    
    Returns: dict con 'comune', 'provincia', 'regione' o None
    """
    if not school_name or school_name in ['ND', '']:
        return None
    
    try:
        # Usa DuckDuckGo instant answer API
        query = f"{school_name} scuola codice meccanografico comune"
        url = f"https://api.duckduckgo.com/?q={requests.utils.quote(query)}&format=json&no_html=1"
        
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            abstract = data.get('Abstract', '') or data.get('AbstractText', '')
            
            if abstract:
                # Cerca pattern di località italiane
                result = extract_location_from_text(abstract)
                if result:
                    return result
        
        # Fallback: cerca su Google (solo parsing, no API)
        # Usa ricerca testuale nel nome stesso
        return extract_location_from_school_name(school_name)
        
    except Exception as e:
        print(f"   ⚠️ Errore ricerca web: {e}")
        return None


def extract_location_from_text(text: str) -> Optional[Dict]:
    """Estrae comune/provincia/regione da un testo."""
    db = get_school_db()
    
    # Cerca comuni italiani nel testo
    text_upper = text.upper()
    
    # Lista di comuni comuni da cercare
    for code, school_data in db._data.items():
        comune = school_data.get('comune', '')
        if comune and len(comune) > 3 and comune.upper() in text_upper:
            return {
                'comune': comune,
                'provincia': school_data.get('provincia', ''),
                'regione': school_data.get('regione', ''),
                'source': 'web_search'
            }
    
    return None


def extract_location_from_school_name(school_name: str) -> Optional[Dict]:
    """
    Estrae località dal nome della scuola.
    Cerca nel database MIUR scuole con nome simile.
    """
    db = get_school_db()
    
    if not school_name or school_name in ['ND', '']:
        return None
    
    # Pulisci il nome
    name_lower = school_name.lower()
    
    # Parole comuni da ignorare (non distintive)
    stopwords = {'istituto', 'scuola', 'superiore', 'istruzione', 'liceo', 
                 'tecnico', 'professionale', 'statale', 'paritaria', 'primaria',
                 'secondaria', 'grado', 'comprensivo', 'dell', 'della', 'delle', 
                 'degli', 'del', 'con', 'per', 'san', 'santa', 'santo'}
    
    # Estrai parole chiave significative (>2 caratteri, no stopwords)
    keywords = [w for w in re.split(r'\W+', name_lower) 
                if len(w) > 2 and w not in stopwords]
    
    if not keywords:
        return None
    
    # Cerca corrispondenza con priorità a match multipli
    best_match = None
    best_score = 0
    
    for code, school_data in db._data.items():
        denom = school_data.get('denominazione', '').lower()
        if not denom:
            continue
        
        # Estrai parole dal nome della scuola nel database
        denom_words = set(re.split(r'\W+', denom))
        
        # Conta quante keyword sono presenti come PAROLE INTERE
        matched_kw = [kw for kw in keywords if kw in denom_words]
        
        # Salta se meno di 2 match
        if len(matched_kw) < 2:
            continue
        
        # Calcola score base
        score = len(matched_kw)
        
        # Bonus per combinazioni specifiche di nomi propri
        # Se match contiene cognomi rari, bonus alto
        has_bonghi = 'bonghi' in matched_kw
        has_polo = 'polo' in matched_kw
        has_marco = 'marco' in matched_kw
        
        if has_bonghi and (has_polo or has_marco):
            score += 10  # Match molto forte
        elif has_bonghi:
            score += 5
        
        if score > best_score:
            best_score = score
            best_match = school_data
    
    if best_match:
        return {
            'comune': best_match.get('comune', ''),
            'provincia': best_match.get('provincia', ''),
            'regione': best_match.get('regione', ''),
            'source': f'database_match (score={best_score})',
            'matched_school': best_match.get('denominazione', ''),
            'matched_code': best_match.get('school_id', '')
        }
    
    # Fallback: cerca comuni nel nome della scuola
    for code, school_data in db._data.items():
        comune = school_data.get('comune', '')
        if comune and len(comune) > 3 and comune.lower() in name_lower:
            return {
                'comune': comune,
                'provincia': school_data.get('provincia', ''),
                'regione': school_data.get('regione', ''),
                'source': 'comune_in_name'
            }
    
    return None

def enrich_json_with_miur(json_path: str, school_code: str = None) -> Dict:
    """
    Arricchisce un JSON di analisi con i dati MIUR ufficiali.
    
    - Sovrascrive: regione, provincia, comune (se diversi da MIUR)
    - Aggiunge: nome_scuola, codice_meccanografico, tipologia
    - Mantiene: tutti gli altri campi estratti dall'LLM
    
    Returns: dict con 'success', 'changes', 'warnings'
    """
    result = {'success': False, 'changes': [], 'warnings': []}
    
    # Leggi JSON esistente
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
    except Exception as e:
        result['warnings'].append(f"Errore lettura JSON: {e}")
        return result
    
    # Estrai codice dal nome file se non fornito
    if not school_code:
        school_code = Path(json_path).stem.replace('_analysis', '')
    
    # Cerca nel database MIUR
    db = get_school_db()
    miur = db.get_school_data(school_code)
    
    if not miur:
        result['warnings'].append(f"Codice {school_code} non trovato in database MIUR")
        
        if 'metadata' not in data:
            data['metadata'] = {}
        
        # Aggiorna comunque il codice meccanografico dal nome file
        data['metadata']['codice_meccanografico'] = school_code
        data['metadata']['school_id'] = school_code
        result['changes'].append(f"codice_meccanografico = {school_code} (da nome file)")
        
        # FALLBACK: Deriva provincia/regione dal comune estratto dall'LLM
        comune_llm = data['metadata'].get('comune', '')
        if comune_llm and comune_llm not in ['ND', '', None]:
            location = db.get_location_by_comune(comune_llm)
            if location:
                # Aggiorna provincia e regione dal comune
                if data['metadata'].get('provincia') in ['ND', '', None]:
                    data['metadata']['provincia'] = location['provincia']
                    result['changes'].append(f"provincia = '{location['provincia']}' (da comune '{comune_llm}')")
                if data['metadata'].get('regione') in ['ND', '', None]:
                    data['metadata']['regione'] = location['regione']
                    result['changes'].append(f"regione = '{location['regione']}' (da comune '{comune_llm}')")
                if location.get('area_geografica') and data['metadata'].get('area_geografica') in ['ND', '', None]:
                    data['metadata']['area_geografica'] = location['area_geografica']
            else:
                # FALLBACK 1.5: Usa database comuni italiani
                if get_comuni_db:
                    comuni_db = get_comuni_db()
                    comuni_info = comuni_db.get_comune_info(comune_llm)
                    if comuni_info:
                        # Aggiorna con dati dal database comuni
                        if data['metadata'].get('provincia') in ['ND', '', None]:
                            data['metadata']['provincia'] = comuni_info['provincia']
                            result['changes'].append(f"provincia = '{comuni_info['provincia']}' (da ComuniDB)")
                        if data['metadata'].get('regione') in ['ND', '', None]:
                            data['metadata']['regione'] = comuni_info['regione']
                            result['changes'].append(f"regione = '{comuni_info['regione']}' (da ComuniDB)")
                        if data['metadata'].get('area_geografica') in ['ND', '', None]:
                            data['metadata']['area_geografica'] = comuni_info['area_geografica']
                            result['changes'].append(f"area_geografica = '{comuni_info['area_geografica']}' (da ComuniDB)")
                    else:
                        result['warnings'].append(f"Comune '{comune_llm}' non trovato neanche in ComuniDB")
                else:
                    result['warnings'].append(f"Comune '{comune_llm}' non trovato in database MIUR")
        else:
            # FALLBACK 2: Ricerca web usando il nome della scuola
            denominazione = data['metadata'].get('denominazione', '')
            if denominazione and denominazione not in ['ND', '', None]:
                print(f"   🔍 Ricerca web per: {denominazione[:50]}...")
                web_location = search_school_online(denominazione)
                if web_location:
                    source = web_location.get('source', 'web')
                    if data['metadata'].get('comune') in ['ND', '', None] and web_location.get('comune'):
                        data['metadata']['comune'] = web_location['comune']
                        result['changes'].append(f"comune = '{web_location['comune']}' (da {source})")
                    if data['metadata'].get('provincia') in ['ND', '', None] and web_location.get('provincia'):
                        data['metadata']['provincia'] = web_location['provincia']
                        result['changes'].append(f"provincia = '{web_location['provincia']}' (da {source})")
                    if data['metadata'].get('regione') in ['ND', '', None] and web_location.get('regione'):
                        data['metadata']['regione'] = web_location['regione']
                        result['changes'].append(f"regione = '{web_location['regione']}' (da {source})")
                else:
                    result['warnings'].append(f"Nessun dato trovato online per '{denominazione[:40]}'")
    else:
        # Mappa campi MIUR → JSON
        miur_mapping = {
            'denominazione': ('nome_scuola', miur.get('denominazione', miur.get('DENOMINAZIONESCUOLA', ''))),
            'comune': ('comune', miur.get('comune', miur.get('DESCRIZIONECOMUNESCUOLA', ''))),
            'regione': ('regione', miur.get('regione', miur.get('REGIONE', ''))),
            'provincia': ('provincia', miur.get('provincia', miur.get('SIGLAPROVINCIA', ''))),
            'tipologia': ('tipologia', miur.get('tipo_scuola', miur.get('DESCRIZIONETIPOLOGIASCUOLA', 'ND'))),
        }
        
        if 'metadata' not in data:
            data['metadata'] = {}
        
        # Aggiorna sempre codice meccanografico
        data['metadata']['codice_meccanografico'] = school_code
        data['metadata']['school_id'] = school_code
        result['changes'].append(f"codice_meccanografico = {school_code}")
        
        # Aggiorna altri campi
        for miur_key, (json_key, miur_value) in miur_mapping.items():
            if miur_value and miur_value not in ['ND', '', None]:
                old_value = data['metadata'].get(json_key, 'ND')
                
                # Sovrascrive se mancante o diverso
                if old_value in ['ND', '', None] or (old_value.lower() != str(miur_value).lower()):
                    data['metadata'][json_key] = miur_value
                    if old_value not in ['ND', '', None]:
                        result['changes'].append(f"{json_key}: '{old_value}' → '{miur_value}' (MIUR)")
                    else:
                        result['changes'].append(f"{json_key} = '{miur_value}' (MIUR)")
    
    # CALCOLO AUTOMATICO area_geografica e territorio dalla regione/provincia
    def get_area_geografica(regione: str) -> str:
        """Ritorna area geografica standard dalla regione (case-insensitive)."""
        return get_area_from_regione(regione)
    
    PROVINCE_METRO = ['Roma', 'Milano', 'Napoli', 'Torino', 'Bari', 'Firenze', 
                      'Bologna', 'Genova', 'Venezia', 'Palermo', 'Catania', 
                      'Messina', 'Reggio Calabria', 'Cagliari']
    
    regione = data['metadata'].get('regione', '')
    provincia = data['metadata'].get('provincia', '')
    
    if regione and regione not in ['ND', '', None]:
        area_geo = get_area_geografica(regione)
        if area_geo != 'ND':
            old_area = data['metadata'].get('area_geografica', 'ND')
            if old_area in ['ND', '', None, 'Metropolitano', 'Non Metropolitano'] or old_area != area_geo:
                data['metadata']['area_geografica'] = area_geo
                result['changes'].append(f"area_geografica = '{area_geo}' (da regione)")
    
    if provincia and provincia not in ['ND', '', None]:
        prov_upper = provincia.upper().strip()
        is_metro = any(p.upper() == prov_upper for p in PROVINCE_METRO)
        territorio = 'Metropolitano' if is_metro else 'Non Metropolitano'
        old_terr = data['metadata'].get('territorio', 'ND')
        if old_terr in ['ND', '', None, 'Nord', 'Centro', 'Sud', 'Isole'] or old_terr != territorio:
            data['metadata']['territorio'] = territorio
            result['changes'].append(f"territorio = '{territorio}' (da provincia)")
    
    # FALLBACK FINALE: Se area_geografica è ancora ND, usa database comuni
    if data['metadata'].get('area_geografica') in ['ND', '', None]:
        comune = data['metadata'].get('comune', '')
        if comune and comune not in ['ND', '', None] and get_comuni_db:
            comuni_db = get_comuni_db()
            comuni_info = comuni_db.get_comune_info(comune)
            if comuni_info and comuni_info.get('area_geografica'):
                data['metadata']['area_geografica'] = comuni_info['area_geografica']
                result['changes'].append(f"area_geografica = '{comuni_info['area_geografica']}' (da ComuniDB fallback)")
                # Aggiorna anche provincia e regione se mancanti
                if data['metadata'].get('provincia') in ['ND', '', None]:
                    data['metadata']['provincia'] = comuni_info['provincia']
                    result['changes'].append(f"provincia = '{comuni_info['provincia']}' (da ComuniDB)")
                if data['metadata'].get('regione') in ['ND', '', None]:
                    data['metadata']['regione'] = comuni_info['regione']
                    result['changes'].append(f"regione = '{comuni_info['regione']}' (da ComuniDB)")
    
    area_norm = normalize_area_geografica(
        data['metadata'].get('area_geografica'),
        regione=data['metadata'].get('regione'),
        provincia_sigla=school_code[:2] if school_code else None
    )
    if area_norm != 'ND':
        data['metadata']['area_geografica'] = area_norm

    # Salva JSON aggiornato
    try:
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        result['success'] = True
    except Exception as e:
        result['warnings'].append(f"Errore salvataggio JSON: {e}")
    
    return result


def enrich_all_json_files(analysis_dir: str = 'analysis_results') -> Dict:
    """
    Arricchisce tutti i JSON nella directory con dati MIUR.
    
    Returns: dict con statistiche
    """
    stats = {'total': 0, 'enriched': 0, 'warnings': 0, 'details': []}
    
    for json_file in sorted(os.listdir(analysis_dir)):
        if not json_file.endswith('.json'):
            continue
        
        stats['total'] += 1
        json_path = os.path.join(analysis_dir, json_file)
        code = json_file.replace('_analysis.json', '')
        
        result = enrich_json_with_miur(json_path, code)
        
        if result['success'] and result['changes']:
            stats['enriched'] += 1
        if result['warnings']:
            stats['warnings'] += 1
        
        stats['details'].append({
            'file': json_file,
            'changes': result['changes'],
            'warnings': result['warnings']
        })
    
    return stats


# =============================================================================
# FASE 2: Validazione codici pre-analisi
# =============================================================================

def validate_school_code(school_code: str) -> Dict:
    """
    Valida un codice meccanografico prima dell'analisi.
    
    Returns: dict con 'valid', 'miur_data', 'warnings'
    """
    result = {
        'valid': False,
        'miur_data': None,
        'warnings': []
    }
    
    # Check formato codice (2 lettere regione + 2 alfanumerici tipo + 6 alfanumerici)
    # Es: MIPC09500C, BS1M004009, UD1M00600L
    pattern = r'^[A-Z]{2}[A-Z0-9]{2}[A-Z0-9]{6}$'
    if not re.match(pattern, school_code.upper()):
        result['warnings'].append(f"Formato codice non valido: {school_code}")
        return result
    
    # Cerca nel database MIUR
    db = get_school_db()
    miur = db.get_school_data(school_code.upper())
    
    if miur:
        result['valid'] = True
        result['miur_data'] = {
            'denominazione': miur.get('denominazione', miur.get('DENOMINAZIONESCUOLA', '')),
            'comune': miur.get('comune', miur.get('DESCRIZIONECOMUNESCUOLA', '')),
            'regione': miur.get('regione', miur.get('REGIONE', '')),
            'provincia': miur.get('provincia', miur.get('SIGLAPROVINCIA', '')),
        }
    else:
        result['warnings'].append(f"Codice {school_code} non trovato in database MIUR")
    
    return result


def validate_pdf_before_analysis(pdf_path: str) -> Dict:
    """
    Valida un PDF prima di analizzarlo.
    Estrae il codice dal nome file e verifica in MIUR.
    
    Returns: dict con 'valid', 'school_code', 'miur_data', 'warnings'
    """
    result = {
        'valid': False,
        'school_code': None,
        'miur_data': None,
        'warnings': []
    }
    
    # Estrai codice dal nome file
    basename = Path(pdf_path).stem
    
    # Pattern: cerca codice meccanografico nel nome
    # Formato: 2 lettere regione + 2 alfanumerici tipo + 6 alfanumerici
    match = re.search(r'([A-Z]{2}[A-Z0-9]{2}[A-Z0-9]{6})', basename.upper())
    
    if not match:
        result['warnings'].append(f"Nessun codice meccanografico trovato nel nome: {basename}")
        return result
    
    school_code = match.group(1)
    result['school_code'] = school_code
    
    # Valida il codice
    validation = validate_school_code(school_code)
    result['valid'] = validation['valid']
    result['miur_data'] = validation['miur_data']
    result['warnings'].extend(validation['warnings'])
    
    return result


# =============================================================================
# FASE 3: Cross-check contenuto PDF
# =============================================================================

def extract_codes_from_text(text: str) -> List[str]:
    """
    Estrae tutti i possibili codici meccanografici da un testo.
    Formato: 2 lettere regione + 2 alfanumerici tipo + 6 alfanumerici
    """
    pattern = r'\b([A-Z]{2}[A-Z0-9]{2}[A-Z0-9]{6})\b'
    matches = re.findall(pattern, text.upper())
    return list(set(matches))  # Rimuovi duplicati


def crosscheck_pdf_content(md_path: str, expected_code: str) -> Dict:
    """
    Verifica che il contenuto del PDF (convertito in MD) contenga
    il codice meccanografico atteso.
    
    Returns: dict con 'match', 'found_codes', 'warnings'
    """
    result = {
        'match': False,
        'found_codes': [],
        'expected_code': expected_code,
        'warnings': []
    }
    
    try:
        with open(md_path, 'r') as f:
            content = f.read()
    except Exception as e:
        result['warnings'].append(f"Errore lettura file: {e}")
        return result
    
    # Estrai codici dal testo
    found_codes = extract_codes_from_text(content)
    result['found_codes'] = found_codes
    
    # Verifica match
    if expected_code.upper() in [c.upper() for c in found_codes]:
        result['match'] = True
    elif found_codes:
        # Trovati altri codici ma non quello atteso
        result['warnings'].append(
            f"Codice atteso {expected_code} non trovato. "
            f"Trovati invece: {', '.join(found_codes[:3])}"
        )
        
        # Verifica se uno dei codici trovati esiste in MIUR
        db = get_school_db()
        for code in found_codes:
            miur = db.get_school_data(code)
            if miur:
                result['warnings'].append(
                    f"⚠️ Il codice {code} trovato nel testo corrisponde a: "
                    f"{miur.get('denominazione', 'ND')} ({miur.get('comune', 'ND')})"
                )
    else:
        result['warnings'].append("Nessun codice meccanografico trovato nel testo del PDF")
    
    return result


def full_validation_pipeline(pdf_path: str, md_path: str = None) -> Dict:
    """
    Pipeline completa di validazione:
    1. Valida codice dal nome file
    2. Cross-check con contenuto (se md_path fornito)
    
    Returns: dict completo con tutti i check
    """
    result = {
        'pdf_path': pdf_path,
        'school_code': None,
        'valid_code': False,
        'content_match': None,
        'miur_data': None,
        'proceed': False,  # True se si può procedere con l'analisi
        'warnings': []
    }
    
    # Step 1: Valida codice
    validation = validate_pdf_before_analysis(pdf_path)
    result['school_code'] = validation['school_code']
    result['valid_code'] = validation['valid']
    result['miur_data'] = validation['miur_data']
    result['warnings'].extend(validation['warnings'])
    
    # Step 2: Cross-check contenuto (opzionale)
    if md_path and os.path.exists(md_path) and result['school_code']:
        crosscheck = crosscheck_pdf_content(md_path, result['school_code'])
        result['content_match'] = crosscheck['match']
        result['found_codes'] = crosscheck.get('found_codes', [])
        result['warnings'].extend(crosscheck['warnings'])
    
    # Decisione finale
    if result['valid_code']:
        result['proceed'] = True
    elif result['school_code']:
        # Codice estratto ma non in MIUR - procedi con warning
        result['proceed'] = True
        result['warnings'].append("Procedo comunque ma il codice non è verificato in MIUR")
    
    return result


# =============================================================================
# Utility per il workflow
# =============================================================================

def print_validation_result(result: Dict):
    """Stampa risultato validazione in modo leggibile"""
    code = result.get('school_code', 'ND')
    
    if result.get('valid_code'):
        print(f"✅ {code}: Valido in MIUR")
        if result.get('miur_data'):
            miur = result['miur_data']
            print(f"   📍 {miur.get('denominazione', 'ND')} - {miur.get('comune', 'ND')}")
    else:
        print(f"⚠️ {code}: Non trovato in MIUR")
    
    if result.get('content_match') is not None:
        if result['content_match']:
            print(f"   ✅ Codice trovato nel contenuto PDF")
        else:
            print(f"   ⚠️ Codice NON trovato nel contenuto PDF")
    
    for w in result.get('warnings', []):
        print(f"   ⚠️ {w}")


if __name__ == "__main__":
    # Test rapido
    import sys
    
    print("=" * 60)
    print("🧪 TEST MIUR ENRICHMENT")
    print("=" * 60)
    
    # Test arricchimento
    print("\n📋 Test arricchimento JSON...")
    stats = enrich_all_json_files()
    print(f"   Totale: {stats['total']}, Arricchiti: {stats['enriched']}, Warning: {stats['warnings']}")
    
    for detail in stats['details'][:3]:
        print(f"\n   📄 {detail['file']}:")
        for change in detail['changes']:
            print(f"      ✏️ {change}")
        for warn in detail['warnings']:
            print(f"      ⚠️ {warn}")
