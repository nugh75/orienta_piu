
import os
import csv
import logging
from typing import Optional, Dict

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
        # Common fields
        data = {
            'school_id': row.get('CODICESCUOLA', '').upper(),
            'denominazione': row.get('DENOMINAZIONESCUOLA', '').strip().title(),
            'comune': row.get('DESCRIZIONECOMUNE', '').strip().title(),
            'area_geografica': row.get('REGIONE', '').strip().title(), # Will align later
            'indirizzo': row.get('INDIRIZZOSCUOLA', '').strip().title(),
            'cap': row.get('CAPSCUOLA', ''),
            'website': row.get('SITOWEBSCUOLA', '').lower() if row.get('SITOWEBSCUOLA') != 'Non Disponibile' else ''
        }
        
        # Determine Ordine/Tipo
        # State CSV has 'DESCRIZIONETIPOLOGIAGRADOISTRUZIONESCUOLA'
        # Private CSV has same field name? Checked: Yes.
        
        raw_tipo = row.get('DESCRIZIONETIPOLOGIAGRADOISTRUZIONESCUOLA', '').upper()
        
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
        elif 'SEC. DI SECONDO GRADO' in raw_tipo or 'LICEO' in raw_tipo or 'TECNICO' in raw_tipo or 'PROFESSIONALE' in raw_tipo:
            ordine = 'II Grado'
            if 'LICEO' in raw_tipo: tipo = 'Liceo'
            elif 'TECNICO' in raw_tipo: tipo = 'Tecnico'
            elif 'PROFESSIONALE' in raw_tipo: tipo = 'Professionale'
            else: tipo = 'Istituto Superiore'
            
        data['ordine_grado'] = ordine
        data['tipo_scuola'] = tipo
        data['is_paritaria'] = not is_state
        
        return data

    def get_school_data(self, school_code: str) -> Optional[Dict]:
        """Retrieve school data by code."""
        if not school_code: return None
        return self._data.get(school_code.upper())
