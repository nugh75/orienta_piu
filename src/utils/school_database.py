
import os
import csv
import logging
from typing import Optional, Dict

from src.utils.constants import normalize_area_geografica

logger = logging.getLogger(__name__)

class SchoolDatabase:
    """
    Database to key-value store school metadata from local CSVs.
    Supported files: SCUANAGRAFESTAT... (State) and SCUANAGRAFEPAR... (Private/Paritarie).
    """

    # Update these filenames if they change
    # Paths relative to project root usually
    STATALE_CSV = "data/SCUANAGRAFESTAT20252620250901.csv"
    PARITARIA_CSV = "data/SCUANAGRAFEPAR20252620250901.csv"

    _instance = None
    _data = {}      # Map[school_code] -> dict
    _loaded = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SchoolDatabase, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._loaded:
            self._load_data()
            SchoolDatabase._loaded = True

    def _load_data(self):
        """Load data from CSVs into memory."""
        self._data = {}
        
        # Load Statale
        self._load_csv(self.STATALE_CSV, is_state=True)
        # Load Paritaria
        self._load_csv(self.PARITARIA_CSV, is_state=False)
        
        logger.info(f"[SchoolDatabase] Loaded {len(self._data)} schools.")
        print(f"[SchoolDatabase] Loaded {len(self._data)} schools from CSVs.")

    def _load_csv(self, path: str, is_state: bool):
        if not os.path.exists(path):
            logger.warning(f"CSV not found: {path}")
            return
            
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    code = row.get('CODICESCUOLA')
                    if code:
                        self._data[code.upper()] = self._map_row(row, is_state)
        except Exception as e:
            logger.error(f"Error loading {path}: {e}")

    def _map_row(self, row: dict, is_state: bool) -> dict:
        """Map CSV row to internal schema."""
        # Normalize 'Non Disponibile' values
        def clean_value(val, to_title=False):
            if not val or val.strip().lower() in ['non disponibile', 'nd', 'n/a', '']:
                return ''
            val = val.strip()
            return val.title() if to_title else val
        
        raw_area = row.get('AREAGEOGRAFICA', '')
        raw_regione = row.get('REGIONE', '')
        provincia_sigla = row.get('PROVINCIA', '')
        provincia_sigla = provincia_sigla.strip() if provincia_sigla else ''
        if provincia_sigla and len(provincia_sigla) != 2:
            provincia_sigla = ''

        try:
            area_geografica = normalize_area_geografica(
                raw_area,
                regione=raw_regione,
                provincia_sigla=provincia_sigla
            )
        except TypeError:
            area_geografica = normalize_area_geografica(raw_area)
        except Exception:
            area_geografica = clean_value(raw_area, to_title=True)

        # Common fields - extract all available metadata
        data = {
            'school_id': row.get('CODICESCUOLA', '').upper().strip(),
            'denominazione': clean_value(row.get('DENOMINAZIONESCUOLA', ''), to_title=True),
            'comune': clean_value(row.get('DESCRIZIONECOMUNE', ''), to_title=True),
            'provincia': clean_value(row.get('PROVINCIA', ''), to_title=True),
            'regione': clean_value(row.get('REGIONE', ''), to_title=True),
            'area_geografica': area_geografica,
            'indirizzo': clean_value(row.get('INDIRIZZOSCUOLA', ''), to_title=True),
            'cap': clean_value(row.get('CAPSCUOLA', '')),
            'codice_comune': clean_value(row.get('CODICECOMUNESCUOLA', '')),
            'email': clean_value(row.get('INDIRIZZOEMAILSCUOLA', '')).lower() if clean_value(row.get('INDIRIZZOEMAILSCUOLA', '')) else '',
            'pec': clean_value(row.get('INDIRIZZOPECSCUOLA', '')).lower() if clean_value(row.get('INDIRIZZOPECSCUOLA', '')) else '',
            'website': clean_value(row.get('SITOWEBSCUOLA', '')).lower() if clean_value(row.get('SITOWEBSCUOLA', '')) else '',
            'anno_scolastico': clean_value(row.get('ANNOSCOLASTICO', '')),
        }
        
        # Determine Ordine/Tipo
        # State CSV has 'DESCRIZIONETIPOLOGIAGRADOISTRUZIONESCUOLA'
        # Private CSV has same field name? Checked: Yes.
        
        raw_tipo = row.get('DESCRIZIONETIPOLOGIAGRADOISTRUZIONESCUOLA', '').upper()
        data['tipo_istruzione_raw'] = clean_value(row.get('DESCRIZIONETIPOLOGIAGRADOISTRUZIONESCUOLA', ''), to_title=True)
        
        # Map Type
        ordine = 'ND'
        tipo = 'ND'
        
        if 'INFANZIA' in raw_tipo:
            ordine = 'Infanzia'
            tipo = 'Infanzia'
        elif 'PRIMARIA' in raw_tipo or 'ELEMENTARE' in raw_tipo:
            ordine = 'Primaria'
            tipo = 'Primaria'
        elif 'PRIMO GRADO' in raw_tipo or 'MEDIA' in raw_tipo:
            ordine = 'I Grado'
            tipo = 'I Grado'
        elif 'SECONDO GRADO' in raw_tipo or 'LICEO' in raw_tipo or 'TECNICO' in raw_tipo or 'PROFESSIONALE' in raw_tipo or 'SUPERIORE' in raw_tipo:
            ordine = 'II Grado'
            if 'LICEO' in raw_tipo: tipo = 'Liceo'
            elif 'TECNICO' in raw_tipo: tipo = 'Tecnico'
            elif 'PROFESSIONALE' in raw_tipo: tipo = 'Professionale'
            else: tipo = 'ND'
            
        data['ordine_grado'] = ordine
        data['tipo_scuola'] = tipo
        data['is_paritaria'] = not is_state
        data['statale_paritaria'] = 'Paritaria' if not is_state else 'Statale'
        
        return data

    def get_school_data(self, school_code: str) -> Optional[Dict]:
        """Retrieve school data by code."""
        if not school_code: return None
        return self._data.get(school_code.upper())

    def get_location_by_comune(self, comune: str) -> Optional[Dict]:
        """
        Trova provincia e regione dato il nome di un comune.
        Cerca nel database una scuola qualsiasi in quel comune.
        
        Returns: dict con 'comune', 'provincia', 'regione' o None se non trovato
        """
        if not comune:
            return None
        
        comune_upper = comune.upper().strip()
        
        for code, data in self._data.items():
            com = data.get('comune', '')
            if com and com.upper().strip() == comune_upper:
                return {
                    'comune': data.get('comune', ''),
                    'provincia': data.get('provincia', ''),
                    'regione': data.get('regione', ''),
                    'area_geografica': data.get('area_geografica', '')
                }
        
        return None
