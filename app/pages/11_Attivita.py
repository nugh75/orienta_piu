#!/usr/bin/env python3
"""
Attività - Esplorazione e analisi delle attività di orientamento estratte dai PTOF
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from scipy import stats
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# Aggiungi la root del progetto al path per importare src
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from src.utils.constants import REGIONE_TO_AREA
from data_utils import render_footer, scale_to_pct
from page_control import setup_page
try:
    from src.stats import activity_stats
except ImportError:
    activity_stats = None

st.set_page_config(page_title="ORIENTA+ | Attività", page_icon="🧭", layout="wide")
setup_page("pages/11_Attivita.py")

# Custom CSS
st.markdown("""
<style>
    .main .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    div[data-testid="stMetric"] {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #4e73df;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    h1, h2, h3 { color: #2c3e50; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }
    .practice-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        border-left: 4px solid #4e73df;
    }
</style>
""", unsafe_allow_html=True)

# === CONSTANTS ===
ACTIVITIES_CSV = 'data/attivita.csv'
ACTIVITIES_JSON = 'data/attivita.json'  # Solo metadata

CATEGORIE = [
    "Metodologie Didattiche Innovative",
    "Progetti e Attività Esemplari",
    "Partnership e Collaborazioni Strategiche",
    "Azioni di Sistema e Governance",
    "Buone Pratiche per l'Inclusione",
    "Esperienze Territoriali Significative"
]

CATEGORIA_ICONS = {
    "Metodologie Didattiche Innovative": "📚",
    "Progetti e Attività Esemplari": "🎯",
    "Partnership e Collaborazioni Strategiche": "🤝",
    "Azioni di Sistema e Governance": "⚙️",
    "Buone Pratiche per l'Inclusione": "🌈",
    "Esperienze Territoriali Significative": "🗺️"
}

# Tipologie di metodologia didattica
TIPOLOGIE_METODOLOGIA = [
    "STEM/STEAM",
    "Coding e Pensiero Computazionale",
    "Flipped Classroom",
    "Peer Education/Tutoring",
    "Problem Based Learning",
    "Cooperative Learning",
    "Gamification",
    "Debate",
    "Service Learning",
    "Outdoor Education",
    "Didattica Laboratoriale",
    "Didattica Digitale",
    "CLIL",
    "Storytelling",
    "Project Work",
    "Learning by Doing",
    "Mentoring",
    "Altro"
]

# Ambiti di attività
AMBITI_ATTIVITA = [
    "Orientamento",
    "Inclusione e BES",
    "PCTO/Alternanza",
    "Cittadinanza e Legalità",
    "Educazione Civica",
    "Sostenibilità e Ambiente",
    "Digitalizzazione",
    "Lingue Straniere",
    "Arte e Creatività",
    "Musica e Teatro",
    "Sport e Benessere",
    "Scienze e Ricerca",
    "Lettura e Scrittura",
    "Matematica e Logica",
    "Imprenditorialità",
    "Intercultura",
    "Prevenzione Disagio",
    "Continuità e Accoglienza",
    "Valutazione e Autovalutazione",
    "Formazione Docenti",
    "Rapporti con Famiglie",
    "Altro"
]

# Tipologie di istituto
TIPOLOGIE_ISTITUTO = [
    "Liceo Classico",
    "Liceo Scientifico",
    "Liceo Linguistico",
    "Liceo Artistico",
    "Liceo Musicale e Coreutico",
    "Liceo delle Scienze Umane",
    "Istituto Tecnico",
    "Istituto Professionale",
    "Istituto Comprensivo",
    "Circolo Didattico",
    "Scuola Secondaria I Grado",
    "Scuola Primaria",
    "Scuola dell'Infanzia",
    "CPIA",
    "Convitto/Educandato"
]

# Ordine e grado
ORDINI_GRADO = [
    "Infanzia",
    "Primaria",
    "Secondaria I Grado",
    "Licei",
    "Istituti Tecnici",
    "Istituti Professionali"
]

# Mapping normalizzazione tipo scuola
TIPO_SCUOLA_NORMALIZATION = {
    # Infanzia
    "infanzia": "Infanzia",
    "scuola dell'infanzia": "Infanzia",
    "materna": "Infanzia",
    # Primaria
    "primaria": "Primaria",
    "scuola primaria": "Primaria",
    "elementare": "Primaria",
    "elementari": "Primaria",
    # Secondaria I Grado
    "secondaria i grado": "Secondaria I Grado",
    "secondaria di i grado": "Secondaria I Grado",
    "secondaria di primo grado": "Secondaria I Grado",
    "scuola media": "Secondaria I Grado",
    "media": "Secondaria I Grado",
    "i grado": "Secondaria I Grado",
    # Licei
    "liceo": "Licei",
    "liceo classico": "Licei",
    "liceo scientifico": "Licei",
    "liceo linguistico": "Licei",
    "liceo artistico": "Licei",
    "liceo musicale": "Licei",
    "liceo coreutico": "Licei",
    "liceo delle scienze umane": "Licei",
    "liceo scienze umane": "Licei",
    "liceo economico sociale": "Licei",
    # Istituti Tecnici
    "istituto tecnico": "Istituti Tecnici",
    "tecnico": "Istituti Tecnici",
    "iti": "Istituti Tecnici",
    "its": "Istituti Tecnici",
    "tecnici": "Istituti Tecnici",
    # Istituti Professionali
    "istituto professionale": "Istituti Professionali",
    "professionale": "Istituti Professionali",
    "ipsia": "Istituti Professionali",
    "ipssar": "Istituti Professionali",
    "alberghiero": "Istituti Professionali",
    "professionali": "Istituti Professionali",
}

# Categorie di Target per raggruppamento
TARGET_CATEGORIES = {
    "Studenti": ["studenti", "alunni", "bambini", "studentesse", "alunne", "classe", "classi", "biennio", "triennio"],
    "Docenti": ["docenti", "insegnanti", "personale docente", "formazione docenti"],
    "Famiglie": ["famiglie", "genitori", "caregiver"],
    "Personale Scolastico": ["personale ata", "personale scolastico", "personale amministrativo", "dirigent", "staff", "collaboratori scolastici"],
    "Studenti BES/Inclusione": ["bes", "dsa", "disabilità", "disabili", "bisogni educativi", "bisogni speciali", "stranieri", "nai", "inclusione", "diversamente abili", "sostegno"],
    "Comunità/Territorio": ["comunità", "territorio", "enti locali", "enti esterni", "associazioni", "organizzazioni", "asl", "servizi sociali"]
}

# Ordine visualizzazione target
TARGET_ORDER = ["Studenti", "Docenti", "Famiglie", "Personale Scolastico", "Studenti BES/Inclusione", "Comunità/Territorio", "Misto/Altro"]

# Ordine di priorità per matching (BES/Inclusione prima di Studenti generico)
TARGET_PRIORITY = ["Studenti BES/Inclusione", "Personale Scolastico", "Comunità/Territorio", "Docenti", "Famiglie", "Studenti"]


def normalize_target(target_str: str) -> list:
    """Normalizza un target in categorie predefinite."""
    if not target_str or pd.isna(target_str):
        return ["N/D"]
    
    target_lower = str(target_str).lower()
    categories_found = set()
    
    # Check per ogni categoria
    for category, keywords in TARGET_CATEGORIES.items():
        for keyword in keywords:
            if keyword in target_lower:
                categories_found.add(category)
                break
    
    # Se nessuna categoria trovata, usa "Misto/Altro"
    if not categories_found:
        return ["Misto/Altro"]
    
    return list(categories_found)


def normalize_target_single(target_str: str) -> str:
    """Normalizza un target in una singola categoria principale.
    Usa priorità specifica: BES/Inclusione prima di Studenti generico."""
    if not target_str or pd.isna(target_str):
        return "N/D"
    
    target_lower = str(target_str).lower()
    
    # Usa ordine di priorità specifico (BES prima di Studenti)
    for category in TARGET_PRIORITY:
        keywords = TARGET_CATEGORIES.get(category, [])
        for keyword in keywords:
            if keyword in target_lower:
                return category
    
    return "Misto/Altro"


REGION_COORDS = {
    'Piemonte': (45.0703, 7.6869), 'Valle d\'Aosta': (45.7388, 7.4262),
    'Lombardia': (45.4668, 9.1905), 'Trentino-Alto Adige': (46.4993, 11.3548),
    'Veneto': (45.4414, 12.3155), 'Friuli Venezia Giulia': (45.6495, 13.7768),
    'Liguria': (44.4056, 8.9463), 'Emilia-Romagna': (44.4949, 11.3426),
    'Toscana': (43.7711, 11.2486), 'Umbria': (42.9384, 12.6217),
    'Marche': (43.6169, 13.5188), 'Lazio': (41.9028, 12.4964),
    'Abruzzo': (42.3498, 13.3995), 'Molise': (41.5603, 14.6684),
    'Campania': (40.8518, 14.2681), 'Puglia': (41.1258, 16.8666),
    'Basilicata': (40.6395, 15.8053), 'Calabria': (38.9059, 16.5941),
    'Sicilia': (37.6000, 14.0154), 'Sardegna': (40.1209, 9.0129)
}


# === CARICAMENTO DATI ===
@st.cache_data(ttl=30)
def load_activities():
    """Carica le attività dal CSV e metadata dal JSON."""
    result = {
        "df": pd.DataFrame(),
        "total_activities": 0,
        "schools_processed": 0,
        "last_updated": None,
        "extraction_model": None
    }

    # Carica dati da CSV
    if os.path.exists(ACTIVITIES_CSV):
        try:
            df = pd.read_csv(ACTIVITIES_CSV)
            
            # Ensure maturity_index is numeric (scala 1-7)
            if 'maturity_index' in df.columns:
                df['maturity_index'] = pd.to_numeric(df['maturity_index'], errors='coerce')

            result["df"] = df
            result["total_activities"] = len(df)
            result["schools_processed"] = df['codice_meccanografico'].nunique()
        except Exception as e:
            st.error(f"Errore caricamento CSV: {e}")

    # Carica metadata da JSON
    if os.path.exists(ACTIVITIES_JSON):
        try:
            with open(ACTIVITIES_JSON, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                result["last_updated"] = metadata.get("last_updated")
                result["extraction_model"] = metadata.get("extraction_model")
        except Exception:
            pass

    return result


def pipe_to_list(value):
    """Converte stringa separata da | in lista."""
    if pd.isna(value) or value == '':
        return []
    return [v.strip() for v in str(value).split('|') if v.strip()]


def refresh_data():
    """Forza il refresh dei dati pulendo la cache."""
    load_activities.clear()
    st.rerun()


def normalize_ordini_grado(ordine_value, tipo_value=None):
    """Restituisce un set di ordini/gradi normalizzati (Infanzia, Primaria, Sec I, Licei, Tecnici, Professionali)."""
    labels = set()

    def _parse(text):
        if text is None or pd.isna(text):
            return
        parts = re.split(r"[|,;/]+", str(text))
        for part in parts:
            p = part.strip().lower()
            if not p:
                continue
            
            # Check mapping diretto
            if p in TIPO_SCUOLA_NORMALIZATION:
                labels.add(TIPO_SCUOLA_NORMALIZATION[p])
                continue
            
            # Pattern matching per casi composti
            # Licei
            if "liceo" in p:
                labels.add("Licei")
                continue
            
            # Istituti Tecnici
            if "tecnic" in p and "istitut" in p:
                labels.add("Istituti Tecnici")
                continue
            if p in ["iti", "its", "tecnico", "tecnici"]:
                labels.add("Istituti Tecnici")
                continue
            
            # Istituti Professionali
            if "professionale" in p or "professional" in p:
                labels.add("Istituti Professionali")
                continue
            if p in ["ipsia", "ipssar", "alberghiero"]:
                labels.add("Istituti Professionali")
                continue
            
            # Secondaria II Grado generico -> prova a dedurre
            if "ii grado" in p or "secondo grado" in p or "secondaria ii" in p or "superiore" in p:
                # Se non sappiamo il tipo specifico, non aggiungiamo nulla
                # (verrà gestito dal tipo_scuola)
                continue
            
            # Secondaria I Grado
            if "i grado" in p or "primo grado" in p or "secondaria i" in p or "media" in p:
                labels.add("Secondaria I Grado")
                continue
            
            # Primaria
            if "primaria" in p or "elementar" in p:
                labels.add("Primaria")
                continue
            
            # Infanzia
            if "infanzia" in p or "materna" in p:
                labels.add("Infanzia")
                continue

    _parse(ordine_value)
    _parse(tipo_value)
    return labels


def normalize_tipo_scuola_single(text):
    """Normalizza un singolo valore di tipo scuola."""
    if not text or pd.isna(text):
        return None
    
    text_lower = str(text).strip().lower()
    
    # Check mapping diretto
    if text_lower in TIPO_SCUOLA_NORMALIZATION:
        return TIPO_SCUOLA_NORMALIZATION[text_lower]
    
    # Pattern matching
    if "liceo" in text_lower:
        return "Licei"
    if "tecnic" in text_lower:
        return "Istituti Tecnici"
    if "professionale" in text_lower or "alberghiero" in text_lower:
        return "Istituti Professionali"
    if "media" in text_lower or "i grado" in text_lower:
        return "Secondaria I Grado"
    if "primaria" in text_lower or "elementar" in text_lower:
        return "Primaria"
    if "infanzia" in text_lower or "materna" in text_lower:
        return "Infanzia"
    
    return None


def normalize_multivalue_field(
    series: pd.Series,
    separator: str = '|',
    canonical_map: dict[str, str] | None = None
) -> list[str]:
    """
    Normalizza un campo multi-valore eliminando duplicati case-insensitive.

    Args:
        series: Serie pandas con valori separati da separator
        separator: Carattere separatore (default: '|')
        canonical_map: Dizionario opzionale lowercase -> forma canonica

    Returns:
        Lista ordinata di valori unici normalizzati
    """
    if series.empty:
        return []

    values = series.dropna().astype(str).str.split(separator).explode()

    canonical = {}
    
    MANUAL_MAP = {
        "alternanza scuola-lavoro": "Alternanza Scuola Lavoro",
        "peer education": "Peer Education",
        "peer tutoring": "Peer Tutoring", 
        "problem based learning": "Problem Based Learning",
        "service learning": "Service Learning",
        "debate": "Debate",
    }
    import re

    for v in values:
        v_stripped = v.strip()
        if not v_stripped:
            continue
        # Chiave normalizzata: lowercase e rimuovi tutto ciò che non è alfanumerico
        key_clean = re.sub(r'[^a-z0-9]', '', v_stripped.lower())
        key_lower = v_stripped.lower()

        if key_clean not in canonical:
            # Step 1: Check manual map
            if key_lower in MANUAL_MAP:
                canonical[key_clean] = MANUAL_MAP[key_lower]
                continue
                
            # Step 2: Check canonical map arg
            if canonical_map and key_lower in canonical_map:
                canonical[key_clean] = canonical_map[key_lower]
                continue
            
            # Step 3: Default
            val_title = v_stripped
            if val_title.islower() or val_title.isupper():
                val_title = val_title.title()
            canonical[key_clean] = val_title
        else:
            current = canonical[key_clean]
            if "-" in current and "-" not in v_stripped:
                canonical[key_clean] = v_stripped.title()

    return sorted(canonical.values())


def build_geo_hierarchy(df: pd.DataFrame) -> dict:
    """
    Costruisce la gerarchia geografica Area → Regioni → Province dai dati effettivi.
    
    Returns:
        Dict con 'area_to_regioni' e 'regione_to_province'
    """
    hierarchy = {
        "area_to_regioni": {},    # Area → [Regioni]
        "regione_to_province": {} # Regione → [Province]
    }
    
    if df.empty:
        return hierarchy

    # --- Area -> Regioni ---
    # Raggruppa per area e raccogli regioni uniche
    if 'area_geografica' in df.columns and 'regione' in df.columns:
        # Crea df temporaneo unico per coppia area-regione
        area_reg = df[['area_geografica', 'regione']].dropna().drop_duplicates()
        
        for area in area_reg['area_geografica'].unique():
            regioni = sorted(area_reg[area_reg['area_geografica'] == area]['regione'].unique().tolist())
            hierarchy["area_to_regioni"][area] = regioni

    # --- Regione -> Province ---
    if 'regione' in df.columns and 'provincia' in df.columns:
        # Crea df temporaneo unico per coppia regione-provincia
        reg_prov = df[['regione', 'provincia']].dropna().drop_duplicates()
        
        for regione in reg_prov['regione'].unique():
            province = sorted(reg_prov[reg_prov['regione'] == regione]['provincia'].unique().tolist())
            hierarchy["regione_to_province"][regione] = province

    return hierarchy


FILTER_DEFAULTS = {
    "filter_search": "",
    "filter_categoria": "Tutte",
    "filter_ambiti": [],
    "filter_metodologie": [],
    "filter_tipologie_istituto": [],
    "filter_ordini": [],
    "filter_targets": [],
    "filter_aree": [],
    "filter_regioni": [],
    "filter_province": [],
    "filter_tipi": []
}


def reset_filters(default_maturity_range):
    for key, value in FILTER_DEFAULTS.items():
        st.session_state[key] = value

    if default_maturity_range is None:
        st.session_state.pop("filter_maturity", None)
    else:
        st.session_state["filter_maturity"] = default_maturity_range

    st.session_state["filters_signature"] = None
    st.session_state["catalog_limit"] = st.session_state.get("catalog_page_size", 50)


def filter_practices(df, categoria=None, regioni=None, tipi_scuola=None,
                     aree_geo=None, province=None, targets=None,
                     tipologie_metodologia=None, ambiti_attivita=None,
                     tipologie_istituto=None, ordini_grado=None,
                     maturity_range=None, search_text=None):
    """Filtra le pratiche usando operazioni pandas vettorizzate."""
    if df.empty:
        return df

    mask = pd.Series(True, index=df.index)

    if categoria and categoria != "Tutte":
        mask &= df['categoria'] == categoria

    if regioni and len(regioni) > 0:
        mask &= df['regione'].isin(regioni)

    if tipi_scuola and len(tipi_scuola) > 0:
        pattern = '|'.join(tipi_scuola)
        mask &= df['tipo_scuola'].str.contains(pattern, case=False, na=False)

    if aree_geo and len(aree_geo) > 0:
        mask &= df['area_geografica'].isin(aree_geo)

    if province and len(province) > 0:
        mask &= df['provincia'].isin(province)

    if targets and len(targets) > 0:
        pattern = '|'.join(targets)
        mask &= df['target'].str.contains(pattern, case=False, na=False)

    # Filtro per tipologie di metodologia (campo con |)
    if tipologie_metodologia and len(tipologie_metodologia) > 0:
        pattern = '|'.join(tipologie_metodologia)
        mask &= df['tipologie_metodologia'].str.contains(pattern, case=False, na=False)

    # Filtro per ambiti di attività (campo con |)
    if ambiti_attivita and len(ambiti_attivita) > 0:
        pattern = '|'.join(ambiti_attivita)
        mask &= df['ambiti_attivita'].str.contains(pattern, case=False, na=False)

    # Filtro per tipologia istituto
    if tipologie_istituto and len(tipologie_istituto) > 0:
        pattern = '|'.join(tipologie_istituto)
        combined = df['tipo_scuola'].fillna('') + ' ' + df['nome_scuola'].fillna('')
        mask &= combined.str.contains(pattern, case=False, na=False)

    # Filtro per ordine/grado
    if ordini_grado and len(ordini_grado) > 0:
        selected = set(ordini_grado)
        normalized = df.apply(
            lambda row: normalize_ordini_grado(row.get("ordine_grado"), row.get("tipo_scuola")),
            axis=1
        )
        mask &= normalized.apply(lambda labels: bool(labels & selected))

    if maturity_range and len(maturity_range) == 2:
        # Filter directly on percentage data
        min_pct, max_pct = maturity_range
        
        mi = pd.to_numeric(df['maturity_index'], errors='coerce')
        mask &= (mi.isna()) | ((mi >= min_pct) & (mi <= max_pct))

    if search_text:
        search_lower = search_text.lower()
        search_cols = ['titolo', 'descrizione', 'metodologia', 'target',
                       'nome_scuola', 'codice_meccanografico', 'comune',
                       'tipologie_metodologia', 'ambiti_attivita']
        search_mask = pd.Series(False, index=df.index)
        for col in search_cols:
            if col in df.columns:
                search_mask |= df[col].fillna('').str.lower().str.contains(search_lower, na=False)
        mask &= search_mask

    return df[mask]


def group_practices(df, group_by="categoria"):
    """Raggruppa le pratiche per un campo specifico usando pandas."""
    if df.empty:
        return {}

    # Mapping dei nomi dei campi
    field_map = {
        "categoria": "categoria",
        "regione": "regione",
        "scuola": "nome_scuola",
        "provincia": "provincia",
        "tipo_scuola": "tipo_scuola",
        "area_geografica": "area_geografica",
        "ordine_grado": "ordine_grado"
    }

    # Per campi con | (liste), usiamo explode
    if group_by in ["tipologia_metodologia", "ambito_attivita"]:
        col = "tipologie_metodologia" if group_by == "tipologia_metodologia" else "ambiti_attivita"
        # Crea copia e esplodi
        temp = df.copy()
        temp[col] = temp[col].fillna('N/D').apply(lambda x: x.split('|') if x else ['N/D'])
        temp = temp.explode(col)
        temp[col] = temp[col].str.strip()
        temp = temp[temp[col] != '']
        # Raggruppa
        groups = {}
        for key in temp[col].unique():
            groups[key] = temp[temp[col] == key].to_dict('records')
    else:
        col = field_map.get(group_by, "categoria")
        if col not in df.columns:
            return {"Tutte": df.to_dict('records')}
        # Raggruppa
        groups = {}
        for key in df[col].fillna('N/D').unique():
            groups[key] = df[df[col].fillna('N/D') == key].to_dict('records')

    # Ordina gruppi per numero di pratiche (decrescente)
    return dict(sorted(groups.items(), key=lambda x: -len(x[1])))


INVALID_VALUES = {"", "N/D", "ND", "NAN", "NONE"}


def _normalize_text(value):
    if value is None:
        return ""
    return str(value).strip()


def _is_valid_value(value):
    text = _normalize_text(value)
    if not text:
        return False
    return text.upper() not in INVALID_VALUES


def _listify(value):
    if isinstance(value, list):
        items = value
    elif value is None:
        items = []
    else:
        items = [value]

    cleaned = []
    for item in items:
        text = _normalize_text(item)
        if _is_valid_value(text):
            cleaned.append(text)
    return cleaned


def _split_comma(value):
    if not _is_valid_value(value):
        return []
    return [part.strip() for part in str(value).split(",") if _is_valid_value(part)]


def prepare_cross_dataframe(df, dimension):
    if df.empty or dimension not in df.columns:
        return pd.DataFrame(columns=["categoria", "dimension_value"])

    base = df[["categoria", dimension]].copy()

    if dimension in ["ambiti_attivita", "tipologie_metodologia"]:
        base[dimension] = base[dimension].apply(_listify)
        base = base.explode(dimension)
    elif dimension == "tipo_scuola":
        base[dimension] = base[dimension].apply(_split_comma)
        base = base.explode(dimension)
    else:
        base[dimension] = base[dimension].apply(_normalize_text)

    base = base[base["categoria"].apply(_is_valid_value)]
    base = base[base[dimension].apply(_is_valid_value)]
    base = base.rename(columns={dimension: "dimension_value"})
    return base


def compute_cramers_v(chi2, n, rows, cols):
    denom = n * (min(rows - 1, cols - 1))
    if denom <= 0:
        return 0.0
    return np.sqrt(chi2 / denom)


def interpret_cramers_v(value):
    if value < 0.1:
        return "trascurabile"
    if value < 0.3:
        return "piccolo"
    if value < 0.5:
        return "medio"
    return "grande"


def epsilon_squared(h_stat, k, n):
    if n <= k:
        return None
    return max(0.0, (h_stat - k + 1) / (n - k))


def interpret_epsilon_squared(value):
    if value is None:
        return "n/d"
    if value < 0.01:
        return "trascurabile"
    if value < 0.08:
        return "piccolo"
    if value < 0.26:
        return "medio"
    return "grande"


def residuals_from_table(observed, expected):
    expected = expected.replace(0, np.nan)
    return (observed - expected) / np.sqrt(expected)


# === MAIN PAGE ===
st.title("🌟 Attività")

with st.expander("Legenda emoji (categorie)", expanded=False):
    st.markdown(
        """
- 📚 Metodologie Didattiche Innovative
- 🎯 Progetti e Attività Esemplari
- 🤝 Partnership e Collaborazioni Strategiche
- ⚙️ Azioni di Sistema e Governance
- 🌈 Attività per l'Inclusione
- 🗺️ Esperienze Territoriali Significative
"""
    )

# Carica dati
data = load_activities()
df_activities = data.get("df", pd.DataFrame())

# Normalizzazione Regioni e Province (Runtime)
if not df_activities.empty:
    if 'regione' in df_activities.columns:
        # Title Case standard (es. "LOMBARDIA" -> "Lombardia")
        df_activities['regione'] = df_activities['regione'].astype(str).str.title().str.strip()
        # Fix specifici
        df_activities['regione'] = df_activities['regione'].replace({
            "Emilia Romagna": "Emilia-Romagna",
            "Friuli Venezia Giulia": "Friuli-Venezia Giulia",
            "Trentino Alto Adige": "Trentino-Alto Adige"
        })
    if 'provincia' in df_activities.columns:
        # Uppercase standard per sigle provincia (es. "mi" -> "MI")
        df_activities['provincia'] = df_activities['provincia'].astype(str).str.upper().str.strip()

if df_activities.empty:
    st.warning("Nessuna attività trovata. Esegui prima `make activity-extract` per estrarre le attività dai PDF.")
    st.info("""
    **Come estrarre le attività:**

    1. Assicurati di avere PDF PTOF in `ptof_inbox/` o `ptof_processed/`
    2. Esegui: `make activity-extract`
    3. Ricarica questa pagina

    Puoi anche specificare parametri:
    - `make activity-extract MODEL=qwen3:32b` - usa un modello specifico
    - `make activity-extract LIMIT=10` - limita a 10 PDF
    - `make activity-extract FORCE=1` - rielabora tutti i PDF
    """)
    render_footer()
    st.stop()

# === SEZIONE FILTRI NELLA PAGINA PRINCIPALE ===
# === BARRA DI RICERCA ===
search = st.text_input(
    "🔎 Cerca",
    placeholder="Cerca in titolo, descrizione, metodologia, scuola...",
    label_visibility="collapsed",
    key="filter_search"
)

# Costruzione gerarchia geografica dai dati
geo_hierarchy = build_geo_hierarchy(df_activities)

# === FILTRI PRINCIPALI (sempre visibili) ===
st.markdown("##### 🔍 Filtri")

# Prima riga: Categoria, Ambito, Metodologia
col_f1, col_f2, col_f3 = st.columns(3)

with col_f1:
    categorie_opzioni = ["Tutte"] + CATEGORIE
    sel_categoria = st.selectbox("📂 Categoria", categorie_opzioni, key="filter_categoria")

with col_f2:
    # Ambito Attività - normalizzato
    ambiti_disponibili = normalize_multivalue_field(df_activities['ambiti_attivita'])
    if not ambiti_disponibili:
        ambiti_disponibili = sorted(AMBITI_ATTIVITA)
        
    sel_ambiti = st.multiselect("🎯 Ambito Attività", ambiti_disponibili, key="filter_ambiti")

with col_f3:
    # Tipologia Metodologia - normalizzato
    metodologie_disponibili = normalize_multivalue_field(df_activities['tipologie_metodologia'])
    if not metodologie_disponibili:
        metodologie_disponibili = sorted(TIPOLOGIE_METODOLOGIA)
        
    sel_metodologie = st.multiselect(
        "📚 Tipologia Metodologia",
        metodologie_disponibili,
        key="filter_metodologie"
    )

# Seconda riga: Tipologia Istituto, Ordine/Grado, Target
col_f4, col_f5, col_f6 = st.columns(3)

with col_f4:
    sel_tipologie_istituto = st.multiselect(
        "🏫 Tipologia Istituto",
        TIPOLOGIE_ISTITUTO,
        key="filter_tipologie_istituto"
    )

with col_f5:
    sel_ordini = st.multiselect("📖 Ordine/Grado", ORDINI_GRADO, key="filter_ordini")

with col_f6:
    target_options = ["Studenti", "Docenti", "Famiglie"]
    sel_targets = st.multiselect("👥 Target", target_options, key="filter_targets")

# === FILTRI AVANZATI (expander) ===
with st.expander("➕ Più filtri (Geografia, Tipo Scuola, Indice RO)", expanded=False):
    # Riga filtri geografici - CASCADING
    col_g1, col_g2, col_g3, col_g4 = st.columns(4)

    with col_g1:
        # Area geografica - tutte le opzioni sempre disponibili
        aree_disponibili = sorted(df_activities['area_geografica'].dropna().unique().tolist()) if not df_activities.empty else []
        sel_aree = st.multiselect("📍 Area Geografica", aree_disponibili, key="filter_aree")

    with col_g2:
        # Regione - filtrata in base alle aree selezionate
        if sel_aree:
            # Solo regioni delle aree selezionate
            regioni_disponibili = []
            for area in sel_aree:
                regioni_disponibili.extend(geo_hierarchy["area_to_regioni"].get(area, []))
            regioni_disponibili = sorted(set(regioni_disponibili))
        else:
            # Tutte le regioni se nessuna area selezionata
            regioni_disponibili = sorted(df_activities['regione'].dropna().unique().tolist()) if not df_activities.empty else []

        sel_regioni = st.multiselect("🗺️ Regione", regioni_disponibili, key="filter_regioni")

    with col_g3:
        # Provincia - filtrata in base alle regioni o aree selezionate
        province_disponibili = []
        
        if sel_regioni:
            # Solo province delle regioni selezionate
            for regione in sel_regioni:
                province_disponibili.extend(geo_hierarchy["regione_to_province"].get(regione, []))
        elif sel_aree:
            # Province delle aree selezionate (indirettamente via regioni)
            regioni_in_aree = []
            for area in sel_aree:
                regioni_in_aree.extend(geo_hierarchy["area_to_regioni"].get(area, []))
            
            for regione in regioni_in_aree:
                province_disponibili.extend(geo_hierarchy["regione_to_province"].get(regione, []))
        else:
            # Tutte le province
            province_disponibili = sorted(df_activities['provincia'].dropna().unique().tolist()) if not df_activities.empty else []
        
        province_disponibili = sorted(set(province_disponibili))

        sel_province = st.multiselect("🏙️ Provincia", province_disponibili, key="filter_province")

    with col_g4:
        # Tipo scuola legacy
        tipi_disponibili = sorted(set(
            t.strip() for t in df_activities['tipo_scuola'].dropna().str.split(',').explode()
            if t.strip()
        ))
        sel_tipi = st.multiselect("🏫 Tipo Scuola (legacy)", tipi_disponibili, key="filter_tipi")

    # Riga per maturity index
    col_m1, col_m2 = st.columns([1, 3])
    with col_m1:
        st.markdown("**📊 Indice Completezza**")
    with col_m2:
        sel_maturity = None
        maturity_col = pd.to_numeric(df_activities['maturity_index'], errors='coerce')
        maturity_values = maturity_col.dropna()

        if len(maturity_values) > 0:
            min_mi_val = maturity_values.min()
            max_mi_val = maturity_values.max()

            # Slider in scala 1-7
            min_val = max(1.0, float(min_mi_val))
            max_val = min(7.0, float(max_mi_val))

            if min_val < max_val:
                default_range = (min_val, max_val)

                st.session_state["maturity_default_range"] = default_range

                sel_maturity = st.slider(
                    "Range Indice Completezza (1-7)",
                    min_value=1.0,
                    max_value=7.0,
                    value=default_range,
                    step=0.5,
                    label_visibility="collapsed",
                    key="filter_maturity"
                )
            else:
                st.session_state["maturity_default_range"] = None
                st.caption(f"Indice unico: {min_val:.1f}/7")
                sel_maturity = None
        else:
            st.session_state["maturity_default_range"] = None
            st.caption("Nessun dato disponibile")
            sel_maturity = None

# === INFO DATASET E PULSANTI ===
default_maturity_range = st.session_state.get("maturity_default_range")
col_info1, col_info2, col_info3, col_info4, col_info5 = st.columns(5)
with col_info1:
    st.caption(f"📅 Aggiornamento: {data.get('last_updated', 'N/D')[:10] if data.get('last_updated') else 'N/D'}")
with col_info2:
    models = data.get('extraction_models')
    if not models:
         models = data.get('extraction_model', 'N/D')
    elif isinstance(models, list):
         models = ", ".join(models)
    st.caption(f"🤖 Modelli: {models}")
with col_info3:
    st.caption(f"🏫 Scuole: {data.get('schools_processed', 0)}")
with col_info4:
    st.caption(f"📋 Pratiche totali: {data.get('total_activities', 0)}")
with col_info5:
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🔄", help="Aggiorna dati"):
            refresh_data()
    with col_btn2:
        if st.button("🗑️", help="Reset filtri"):
            reset_filters(default_maturity_range)
            st.rerun()

st.markdown("---")

# Aggiorna paginazione se i filtri sono cambiati (solo dopo submit)
filter_signature = (
    sel_categoria,
    tuple(sorted(sel_ambiti)),
    tuple(sorted(sel_metodologie)),
    tuple(sorted(sel_tipologie_istituto)),
    tuple(sorted(sel_ordini)),
    tuple(sorted(sel_targets)),
    tuple(sorted(sel_aree)),
    tuple(sorted(sel_regioni)),
    tuple(sorted(sel_province)),
    tuple(sorted(sel_tipi)),
    tuple(sel_maturity) if sel_maturity else None,
    search
)
prev_signature = st.session_state.get("filters_signature")
if filter_signature != prev_signature:
    st.session_state["filters_signature"] = filter_signature
    st.session_state["catalog_limit"] = st.session_state.get("catalog_page_size", 50)

# Applica filtri
# Reset filtri non validi (UX improvement)
# Se l'utente cambia Area, e aveva selezionato regioni non pertinenti, le rimuoviamo "logicamente" dal filtro applicato
# Nota: st.multiselect mantiene lo stato interno, quindi qui stiamo solo pulendo *prima* di filtrare il DF.
# Nella UI rimarranno selezionati finché l'utente non interagisce o non ricarichiamo la pagina forzatamente,
# ma almeno il risultato sarà coerente (insieme vuoto se selezione invalida, oppure filtrato correttamente).
# Tuttavia, per una UX perfetta, bisognerebbe usare callback sui widget, ma Streamlit forms lo rendono complesso.
# Procediamo a filtrare con i valori selezionati; se l'utente ha selezionato "Nord Ovest" e "Sicilia", 
# otterrà risultato vuoto (corretto poiché intersezione).

# Applica filtri
df_filtered = filter_practices(
    df_activities,
    categoria=sel_categoria,
    regioni=sel_regioni if sel_regioni else None,
    tipi_scuola=sel_tipi if sel_tipi else None,
    aree_geo=sel_aree if sel_aree else None,
    province=sel_province if sel_province else None,
    targets=sel_targets if sel_targets else None,
    tipologie_metodologia=sel_metodologie if sel_metodologie else None,
    ambiti_attivita=sel_ambiti if sel_ambiti else None,
    tipologie_istituto=sel_tipologie_istituto if sel_tipologie_istituto else None,
    ordini_grado=sel_ordini if sel_ordini else None,
    maturity_range=sel_maturity if sel_maturity else None,
    search_text=search if search else None
)

# === SEZIONE ===
section = st.radio(
    "Sezione",
    ["📋 Attività", "🗺️ Mappa", "📊 Grafici", "📈 Statistiche", "📥 Export"],
    horizontal=True,
    label_visibility="collapsed",
    key="section_select"
)

# === SEZIONE CATALOGO ===
if section == "📋 Attività":
    st.subheader(f"📋 {len(df_filtered)} Attività Trovate")

    # Metriche
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Pratiche", len(df_filtered))
    with col2:
        scuole_uniche = df_filtered['codice_meccanografico'].nunique()
        st.metric("Scuole", scuole_uniche)
    with col3:
        cat_uniche = df_filtered['categoria'].nunique()
        st.metric("Categorie", cat_uniche)
    with col4:
        regioni_uniche = df_filtered['regione'].nunique()
        st.metric("Regioni", regioni_uniche)

    st.markdown("---")

    if "catalog_page_size_prev" not in st.session_state:
        st.session_state["catalog_page_size_prev"] = st.session_state.get("catalog_page_size", 50)
    if "catalog_limit" not in st.session_state:
        st.session_state["catalog_limit"] = st.session_state.get("catalog_page_size", 50)

    # Opzioni visualizzazione
    col_view1, col_view2, col_view3, col_view4 = st.columns([1, 1, 2, 1])

    with col_view1:
        view_mode = st.radio(
            "Visualizzazione",
            ["Lista", "Raggruppata", "Tabella"],
            horizontal=True,
            label_visibility="collapsed"
        )

    with col_view2:
        if view_mode == "Raggruppata":
            group_options = {
                "Categoria": "categoria",
                "Regione": "regione",
                "Scuola": "scuola",
                "Provincia": "provincia",
                "Tipo Scuola": "tipo_scuola",
                "Area Geografica": "area_geografica"
            }
            sel_group = st.selectbox("Raggruppa per", list(group_options.keys()), key="group_by")
            group_by_field = group_options[sel_group]
        else:
            group_by_field = None

    with col_view3:
        if view_mode == "Lista":
            sort_options = ["Categoria", "Regione", "Scuola", "Titolo"]
            sort_by = st.selectbox("Ordina per", sort_options, key="sort_catalogo")
        else:
            sort_by = "Categoria"

    with col_view4:
        if view_mode == "Lista":
            page_size = st.selectbox(
                "Risultati",
                [25, 50, 100],
                index=1,
                key="catalog_page_size"
            )
            if st.session_state.get("catalog_page_size_prev") != page_size:
                st.session_state["catalog_page_size_prev"] = page_size
                st.session_state["catalog_limit"] = page_size
            elif st.session_state["catalog_limit"] < page_size:
                st.session_state["catalog_limit"] = page_size
        else:
            page_size = st.session_state.get("catalog_page_size", 50)

    st.markdown("---")

    # === VISTA LISTA ===
    if view_mode == "Lista":
        # Ordina DataFrame
        sort_col_map = {
            "Categoria": "categoria",
            "Regione": "regione",
            "Scuola": "nome_scuola",
            "Titolo": "titolo"
        }
        sort_col = sort_col_map.get(sort_by, "categoria")
        df_sorted = df_filtered.sort_values(by=sort_col, na_position='last')

        total_rows = len(df_sorted)
        limit = min(st.session_state.get("catalog_limit", page_size), total_rows)
        df_page = df_sorted.head(limit)
        st.caption(f"Mostrate {limit} di {total_rows} attività")

        # Lista pratiche con expander
        for i, row in df_page.iterrows():
            categoria = row.get("categoria", "")
            icon = CATEGORIA_ICONS.get(categoria, "📌")

            with st.expander(
                f"{icon} {row.get('titolo', 'Senza titolo')} | "
                f"{row.get('nome_scuola', 'Scuola N/D')} ({row.get('regione', 'N/D')})"
            ):
                col1, col2 = st.columns([2, 1])

                with col1:
                    st.markdown(f"**Categoria:** {categoria}")
                    st.markdown(f"**Descrizione:** {row.get('descrizione', 'N/D')}")

                    if row.get('metodologia'):
                        st.markdown(f"**Metodologia:** {row.get('metodologia')}")

                    if row.get('target'):
                        st.markdown(f"**Target:** {row.get('target')}")

                    if row.get('citazione_ptof'):
                        st.info(f"📝 *\"{row.get('citazione_ptof')}\"*")

                    if row.get('pagina_evidenza') and row.get('pagina_evidenza') != "Non specificata":
                        st.caption(f"📄 {row.get('pagina_evidenza')}")

                with col2:
                    st.markdown("**📍 Scuola:**")
                    st.markdown(f"**{row.get('nome_scuola', 'N/D')}**")
                    st.markdown(f"Codice: `{row.get('codice_meccanografico', 'N/D')}`")
                    st.markdown(f"{row.get('comune', '')}, {row.get('provincia', '')}")
                    st.markdown(f"{row.get('tipo_scuola', 'N/D')}")

                    mi = row.get('maturity_index')
                    if pd.notna(mi):
                        st.metric("Indice RO", f"{float(mi):.2f}")

                    # Partnership se presenti
                    partnership = row.get('partnership_coinvolte', '')
                    if partnership:
                        partners = [p.strip() for p in str(partnership).split('|') if p.strip()]
                        if partners:
                            st.markdown("**🤝 Partnership:**")
                            for partner in partners[:5]:
                                st.markdown(f"- {partner}")

        if limit < total_rows:
            if st.button(f"Mostra altre {page_size}", key="catalog_load_more"):
                st.session_state["catalog_limit"] = min(total_rows, limit + page_size)
                st.rerun()

    # === VISTA RAGGRUPPATA ===
    elif view_mode == "Raggruppata":
        grouped = group_practices(df_filtered, group_by_field)

        for group_name, group_practices_list in grouped.items():
            group_icon = CATEGORIA_ICONS.get(group_name, "📁") if group_by_field == "categoria" else "📁"

            with st.expander(f"{group_icon} **{group_name}** ({len(group_practices_list)} pratiche)", expanded=False):
                for pratica in group_practices_list:
                    categoria = pratica.get("categoria", "")
                    prat_icon = CATEGORIA_ICONS.get(categoria, "📌")

                    st.markdown(f"""
                    **{prat_icon} {pratica.get('titolo', 'Senza titolo')}**
                    - 🏫 {pratica.get('nome_scuola', 'N/D')} ({pratica.get('comune', '')}, {pratica.get('provincia', '')})
                    - 📂 {categoria}
                    - 📝 {pratica.get('descrizione', 'N/D')}
                    """)

                    if pratica.get('target'):
                        st.caption(f"🎯 Target: {pratica.get('target')}")

                    st.markdown("---")

    # === VISTA TABELLA ===
    else:
        if not df_filtered.empty:
            # Colonne da mostrare
            display_cols = ['titolo', 'categoria', 'nome_scuola', 'regione', 'provincia', 'tipo_scuola', 'target']
            available_cols = [c for c in display_cols if c in df_filtered.columns]

            st.dataframe(
                df_filtered[available_cols],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "titolo": st.column_config.TextColumn("Titolo", width="large"),
                    "categoria": st.column_config.TextColumn("Categoria", width="medium"),
                    "nome_scuola": st.column_config.TextColumn("Scuola", width="medium"),
                    "regione": st.column_config.TextColumn("Regione", width="small"),
                    "provincia": st.column_config.TextColumn("Prov.", width="small"),
                    "tipo_scuola": st.column_config.TextColumn("Tipo", width="small"),
                    "target": st.column_config.TextColumn("Target", width="medium"),
                }
            )
        else:
            st.info("Nessuna pratica da visualizzare.")

# === SEZIONE MAPPA ===
elif section == "🗺️ Mappa":
    st.subheader("🗺️ Distribuzione Geografica delle Attività")

    # Calcola distribuzione per regione usando DataFrame
    reg_counts = df_filtered['regione'].value_counts().to_dict()

    if reg_counts:
        # Prepara dati per la mappa
        map_data = []
        for regione, count in reg_counts.items():
            if regione in REGION_COORDS:
                lat, lon = REGION_COORDS[regione]
                map_data.append({
                    "regione": regione,
                    "lat": lat,
                    "lon": lon,
                    "pratiche": count
                })

        if map_data:
            map_df = pd.DataFrame(map_data)

            fig = px.scatter_mapbox(
                map_df,
                lat="lat",
                lon="lon",
                size="pratiche",
                color="pratiche",
                hover_name="regione",
                hover_data={"lat": False, "lon": False, "pratiche": True},
                color_continuous_scale="Viridis",
                size_max=50,
                zoom=4.5,
                center={"lat": 42.0, "lon": 12.5},
                mapbox_style="carto-positron",
                title="Distribuzione Attività per Regione"
            )

            fig.update_layout(height=600, margin={"r": 0, "t": 40, "l": 0, "b": 0})
            st.plotly_chart(fig, use_container_width=True)

        # Tabella regioni
        st.subheader("📊 Dettaglio per Regione")
        reg_df = pd.DataFrame([
            {"Regione": k, "Pratiche": v}
            for k, v in sorted(reg_counts.items(), key=lambda x: -x[1])
        ])
        st.dataframe(reg_df, use_container_width=True, hide_index=True)

    else:
        st.info("Nessun dato geografico disponibile per le pratiche filtrate.")

# === SEZIONE GRAFICI ===
elif section == "📊 Grafici":
    st.subheader("📊 Analisi Distribuzione Attività")

    if not df_filtered.empty:
        col1, col2 = st.columns(2)

        with col1:
            # Distribuzione per categoria
            cat_counts = df_filtered['categoria'].value_counts().reset_index()
            cat_counts.columns = ["Categoria", "Conteggio"]

            fig_cat = px.pie(
                cat_counts,
                names="Categoria",
                values="Conteggio",
                title="Distribuzione per Categoria",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig_cat.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_cat, use_container_width=True)

        with col2:
            # Top 10 regioni
            reg_counts = df_filtered['regione'].value_counts().head(10).reset_index()
            reg_counts.columns = ["Regione", "Conteggio"]

            fig_reg = px.bar(
                reg_counts,
                x="Conteggio",
                y="Regione",
                orientation='h',
                title="Top 10 Regioni",
                color="Conteggio",
                color_continuous_scale="Blues"
            )
            fig_reg.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig_reg, use_container_width=True)

        # Distribuzione per tipo scuola
        tipo_counts = {}
        for tipo in df_filtered['tipo_scuola']:
            for t in str(tipo).split(","):
                t = t.strip()
                if t:
                    tipo_counts[t] = tipo_counts.get(t, 0) + 1

        if tipo_counts:
            tipo_df = pd.DataFrame([
                {"Tipo": k, "Conteggio": v}
                for k, v in sorted(tipo_counts.items(), key=lambda x: -x[1])
            ])

            fig_tipo = px.bar(
                tipo_df,
                x="Tipo",
                y="Conteggio",
                title="Distribuzione per Tipo Scuola",
                color="Conteggio",
                color_continuous_scale="Greens"
            )
            st.plotly_chart(fig_tipo, use_container_width=True)

        # Heatmap categoria x regione (se dati sufficienti)
        if len(df_filtered) >= 10:
            st.subheader("🔥 Heatmap Categoria x Regione")

            pivot = df_filtered.groupby(['regione', 'categoria']).size().reset_index(name='count')
            pivot_table = pivot.pivot(index='regione', columns='categoria', values='count').fillna(0)

            if not pivot_table.empty and len(pivot_table) > 1:
                fig_heat = px.imshow(
                    pivot_table,
                    labels=dict(x="Categoria", y="Regione", color="Pratiche"),
                    aspect="auto",
                    color_continuous_scale="YlOrRd"
                )
                fig_heat.update_layout(height=max(400, len(pivot_table) * 25))
                st.plotly_chart(fig_heat, use_container_width=True)

        st.markdown("---")
        st.subheader("🧪 Analisi Incrociata Categoria x Dimensione")

        dimension_options = {
            "Area Geografica": "area_geografica",
            "Regione": "regione",
            "Provincia": "provincia",
            "Territorio": "territorio",
            "Statale/Paritaria": "statale_paritaria",
            "Ordine/Grado": "ordine_grado",
            "Tipo Scuola": "tipo_scuola",
            "Ambito Attivita": "ambiti_attivita",
            "Tipologia Metodologia": "tipologie_metodologia",
            "Target": "target"
        }

        dim_label = st.selectbox("Dimensione di confronto", list(dimension_options.keys()), index=0)
        dim_key = dimension_options[dim_label]

        col_cfg1, col_cfg2 = st.columns([2, 1])
        with col_cfg1:
            top_n = st.slider("Top tipologie per occorrenze", 5, 20, 10)
        with col_cfg2:
            alpha = st.slider("Soglia significativita", 0.01, 0.10, 0.05, step=0.01)

        cross_df = prepare_cross_dataframe(df_filtered, dim_key)

        if cross_df.empty:
            st.info("Dati insufficienti per l'incrocio selezionato.")
        else:
            if dim_key in ["ambiti_attivita", "tipologie_metodologia", "tipo_scuola"]:
                st.caption("Nota: per dimensioni multi-valore, le occorrenze contano ogni assegnazione.")

            dim_counts = cross_df["dimension_value"].value_counts()
            total_occ = int(dim_counts.sum())

            if len(dim_counts) > top_n:
                dim_counts = dim_counts.head(top_n)
                cross_df = cross_df[cross_df["dimension_value"].isin(dim_counts.index)]
                st.caption("Mostrate solo le tipologie con maggiori occorrenze.")

            occ_df = pd.DataFrame({
                "Tipologia": dim_counts.index,
                "Occorrenze": dim_counts.values,
                "Percentuale": (dim_counts.values / max(total_occ, 1) * 100).round(1)
            })
            st.subheader("📌 Occorrenze per tipologia")
            st.dataframe(occ_df, use_container_width=True, hide_index=True)

            ctab = pd.crosstab(cross_df["categoria"], cross_df["dimension_value"])
            ctab = ctab.reindex(columns=dim_counts.index, fill_value=0)

            categoria_order = [c for c in CATEGORIE if c in ctab.index]
            categoria_extra = [c for c in ctab.index if c not in categoria_order]
            ctab = ctab.reindex(categoria_order + categoria_extra, fill_value=0)

            st.subheader("📊 Tabella incrociata (occorrenze)")
            st.dataframe(ctab, use_container_width=True)

            plot_df = ctab.reset_index().melt(
                id_vars="categoria",
                var_name=dim_label,
                value_name="Occorrenze"
            )
            plot_df["Percentuale"] = plot_df.groupby("categoria")["Occorrenze"].transform(
                lambda x: (x / x.sum() * 100) if x.sum() else 0
            )

            fig_stack = px.bar(
                plot_df,
                x="categoria",
                y="Percentuale",
                color=dim_label,
                title=f"Composizione per categoria - {dim_label}",
                hover_data={"Occorrenze": True, "Percentuale": ":.1f"}
            )
            fig_stack.update_layout(
                barmode="stack",
                yaxis_title="Percentuale",
                xaxis_title="Categoria"
            )
            st.plotly_chart(fig_stack, use_container_width=True)

            if ctab.shape[0] > 1 and ctab.shape[1] > 1:
                st.subheader("🔥 Heatmap Categoria x Dimensione")
                fig_heat2 = px.imshow(
                    ctab,
                    labels=dict(x=dim_label, y="Categoria", color="Occorrenze"),
                    aspect="auto",
                    color_continuous_scale="YlGnBu",
                    text_auto=True
                )
                fig_heat2.update_layout(height=max(350, len(ctab) * 35))
                st.plotly_chart(fig_heat2, use_container_width=True)

            st.subheader("🧮 Significativita e Effetti")
            if ctab.shape[0] >= 2 and ctab.shape[1] >= 2:
                chi2, p_value, dof, expected = stats.chi2_contingency(ctab, correction=False)
                expected_df = pd.DataFrame(expected, index=ctab.index, columns=ctab.columns)
                n = int(ctab.values.sum())
                cramer_v = compute_cramers_v(chi2, n, ctab.shape[0], ctab.shape[1])
                min_expected = expected_df.min().min()

                use_fisher = ctab.shape == (2, 2) and min_expected < 5
                fisher_p = None
                odds_ratio = None
                if use_fisher:
                    odds_ratio, fisher_p = stats.fisher_exact(ctab.values)
                    p_value = fisher_p

                st.markdown(
                    f"**Test:** {'Fisher exact' if use_fisher else 'Chi-quadrato'} | p-value = {p_value:.4f} | dof = {dof}"
                )
                st.markdown(
                    f"**Effetto (Cramer's V):** {cramer_v:.2f} ({interpret_cramers_v(cramer_v)})"
                )
                if use_fisher and odds_ratio is not None:
                    st.markdown(f"**Odds ratio:** {odds_ratio:.2f}")

                if min_expected < 5:
                    st.warning("Attenzione: alcune frequenze attese sono < 5, i risultati vanno interpretati con cautela.")

                if p_value < alpha:
                    residuals = residuals_from_table(ctab.astype(float), expected_df)
                    residuals_stack = residuals.stack().sort_values(ascending=False)
                    top_cells = residuals_stack.head(3)
                    st.markdown("**A favore di (sovra-rappresentazione):**")
                    for (cat, dim), val in top_cells.items():
                        st.markdown(f"- {cat} / {dim}: residuo +{val:.2f}")
                else:
                    st.info("Nessuna associazione significativa alla soglia selezionata.")
            else:
                st.info("Tabella troppo piccola per test di significativita.")

        st.markdown("---")
        st.subheader("📈 Categoria e Indice RO")

        mi_df = df_filtered[["categoria", "maturity_index"]].copy()
        mi_df["maturity_index"] = pd.to_numeric(mi_df["maturity_index"], errors="coerce")
        mi_df = mi_df.dropna(subset=["categoria", "maturity_index"])

        if mi_df.empty:
            st.info("Nessun dato Indice RO disponibile.")
        else:
            fig_mi = px.box(
                mi_df,
                x="categoria",
                y="maturity_index",
                points="all",
                title="Distribuzione Indice RO per Categoria"
            )
            fig_mi.update_layout(xaxis_title="Categoria", yaxis_title="Indice RO")
            st.plotly_chart(fig_mi, use_container_width=True)

            med_df = (
                mi_df.groupby("categoria")["maturity_index"]
                .agg(["count", "median", "mean"])
                .reset_index()
                .sort_values("median", ascending=False)
            )
            med_df["median"] = med_df["median"].round(2)
            med_df["mean"] = med_df["mean"].round(2)
            st.subheader("📊 Statistiche per Categoria (Indice RO)")
            st.dataframe(med_df, use_container_width=True, hide_index=True)

            valid_groups = [
                grp["maturity_index"].values
                for _, grp in mi_df.groupby("categoria")
                if len(grp) >= 2
            ]

            if len(valid_groups) >= 2:
                try:
                    h_stat, p_kw = stats.kruskal(*valid_groups)
                    n_kw = sum(len(g) for g in valid_groups)
                    k_kw = len(valid_groups)
                    eps = epsilon_squared(h_stat, k_kw, n_kw)
                    eps_label = interpret_epsilon_squared(eps) if eps is not None else "n/d"

                    st.markdown(
                        f"**Test:** Kruskal-Wallis | p-value = {p_kw:.4f} | k = {k_kw}"
                    )
                    if eps is not None:
                        st.markdown(f"**Effetto (epsilon^2):** {eps:.2f} ({eps_label})")
                    else:
                        st.markdown("**Effetto (epsilon^2):** n/d")
                except ValueError:
                    p_kw = 1.0
                    st.markdown("**Test:** Kruskal-Wallis non applicabile (valori identici)")

                if p_kw < alpha and not med_df.empty:
                    top_row = med_df.iloc[0]
                    bottom_row = med_df.iloc[-1]
                    st.markdown(
                        f"**A favore di:** {top_row['categoria']} (mediana {top_row['median']:.2f})"
                    )
                    if top_row['categoria'] != bottom_row['categoria']:
                        st.markdown(
                            f"**Sotto la media:** {bottom_row['categoria']} (mediana {bottom_row['median']:.2f})"
                        )
            else:
                st.info("Servono almeno 2 categorie con >= 2 osservazioni per il test.")

    else:
        st.info("Nessun dato disponibile per i grafici.")

# === SEZIONE STATISTICHE AVANZATE ===
elif section == "📈 Statistiche":
    st.subheader("📈 Analisi Statistiche - Incroci Attività × Geografia × Istituti")

    if df_filtered.empty:
        st.warning("Nessun dato disponibile per l'analisi statistica. Modifica i filtri.")
    else:
        # Helper: prepara colonna tipo_scuola normalizzata
        def get_normalized_tipo_scuola_series(df):
            """Crea una serie con tipo scuola normalizzato."""
            result = []
            for idx, row in df.iterrows():
                ordini = normalize_ordini_grado(row.get('ordine_grado'), row.get('tipo_scuola'))
                result.append(list(ordini) if ordini else ['N/D'])
            return result
        
        # Prepara dati normalizzati una volta sola
        df_stats = df_filtered.copy()
        df_stats['_tipo_norm'] = get_normalized_tipo_scuola_series(df_stats)
        
        # Ordine logico per tipo scuola
        TIPO_ORDER = ['Infanzia', 'Primaria', 'Secondaria I Grado', 'Licei', 'Istituti Tecnici', 'Istituti Professionali']
        
        # 3 Tabs principali
        tab_geo_att, tab_ist_att, tab_confronto = st.tabs([
            "🗺️ Geografia × Attività", 
            "🏫 Istituto × Attività", 
            "🔍 Analisi Comparativa"
        ])

        # =====================================================================
        # TAB 1: GEOGRAFIA × ATTIVITÀ
        # =====================================================================
        with tab_geo_att:
            st.markdown("### 🗺️ Attività per Territorio")
            st.markdown("Cosa fanno le scuole nelle diverse regioni e aree geografiche?")
            
            # Selettore regione/area
            col_sel1, col_sel2 = st.columns([1, 2])
            with col_sel1:
                geo_level = st.radio("Livello geografico", ["Regione", "Area Geografica"], horizontal=True, key="geo_level")
            
            with col_sel2:
                if geo_level == "Regione":
                    regioni_disponibili = sorted(df_stats['regione'].dropna().unique().tolist())
                    geo_filter = st.multiselect("Seleziona Regioni (vuoto = tutte)", regioni_disponibili, key="geo_filter_reg")
                    geo_col = 'regione'
                else:
                    aree_disponibili = sorted(df_stats['area_geografica'].dropna().unique().tolist())
                    geo_filter = st.multiselect("Seleziona Aree (vuoto = tutte)", aree_disponibili, key="geo_filter_area")
                    geo_col = 'area_geografica'
            
            # Filtra se necessario
            if geo_filter:
                df_geo = df_stats[df_stats[geo_col].isin(geo_filter)]
            else:
                df_geo = df_stats
            
            if df_geo.empty:
                st.warning("Nessun dato per la selezione.")
            else:
                st.markdown(f"**{len(df_geo)} attività selezionate**")
                st.markdown("---")
                
                # === AMBITI PER TERRITORIO ===
                st.markdown("#### 📌 Ambiti Attività per Territorio")
                
                # Prepara dati esplosi
                geo_ambiti_data = []
                for idx, row in df_geo.iterrows():
                    geo_val = row.get(geo_col, 'N/D')
                    ambiti = pipe_to_list(row.get('ambiti_attivita', ''))
                    for a in ambiti:
                        geo_ambiti_data.append({geo_col: geo_val, 'ambito': a})
                
                if geo_ambiti_data:
                    ga_df = pd.DataFrame(geo_ambiti_data)
                    pivot_ga = pd.crosstab(ga_df[geo_col], ga_df['ambito'])
                    
                    # Limita colonne a top 12 ambiti
                    top_ambiti = ga_df['ambito'].value_counts().head(12).index.tolist()
                    pivot_ga = pivot_ga.reindex(columns=top_ambiti, fill_value=0)
                    
                    # Normalizza per riga (percentuali)
                    pivot_ga_pct = pivot_ga.div(pivot_ga.sum(axis=1), axis=0) * 100
                    
                    fig_ga = px.imshow(
                        pivot_ga_pct.round(1),
                        labels=dict(x="Ambito Attività", y=geo_level, color="% Attività"),
                        color_continuous_scale="Blues",
                        aspect="auto",
                        text_auto=".0f"
                    )
                    fig_ga.update_layout(height=max(300, len(pivot_ga) * 40))
                    st.plotly_chart(fig_ga, use_container_width=True)
                    
                    with st.expander("📋 Tabella valori assoluti"):
                        st.dataframe(pivot_ga, use_container_width=True)
                else:
                    st.info("Nessun dato sugli ambiti.")
                
                st.markdown("---")
                
                # === METODOLOGIE PER TERRITORIO ===
                st.markdown("#### 📚 Metodologie per Territorio")
                
                geo_met_data = []
                for idx, row in df_geo.iterrows():
                    geo_val = row.get(geo_col, 'N/D')
                    metodi = pipe_to_list(row.get('tipologie_metodologia', ''))
                    for m in metodi:
                        geo_met_data.append({geo_col: geo_val, 'metodologia': m})
                
                if geo_met_data:
                    gm_df = pd.DataFrame(geo_met_data)
                    pivot_gm = pd.crosstab(gm_df[geo_col], gm_df['metodologia'])
                    
                    # Limita colonne a top 12 metodologie
                    top_met = gm_df['metodologia'].value_counts().head(12).index.tolist()
                    pivot_gm = pivot_gm.reindex(columns=top_met, fill_value=0)
                    
                    # Normalizza per riga
                    pivot_gm_pct = pivot_gm.div(pivot_gm.sum(axis=1), axis=0) * 100
                    
                    fig_gm = px.imshow(
                        pivot_gm_pct.round(1),
                        labels=dict(x="Metodologia", y=geo_level, color="% Attività"),
                        color_continuous_scale="Greens",
                        aspect="auto",
                        text_auto=".0f"
                    )
                    fig_gm.update_layout(height=max(300, len(pivot_gm) * 40))
                    st.plotly_chart(fig_gm, use_container_width=True)
                    
                    with st.expander("📋 Tabella valori assoluti"):
                        st.dataframe(pivot_gm, use_container_width=True)
                else:
                    st.info("Nessun dato sulle metodologie.")
                
                st.markdown("---")
                
                # === TARGET PER TERRITORIO ===
                st.markdown("#### 👥 Target per Territorio")
                st.caption("I target sono raggruppati in categorie: Studenti, Docenti, Famiglie, Personale Scolastico, Studenti BES/Inclusione, Comunità/Territorio")
                
                geo_targ_data = []
                for idx, row in df_geo.iterrows():
                    geo_val = row.get(geo_col, 'N/D')
                    targets = pipe_to_list(row.get('target', ''))
                    for t in targets:
                        # Normalizza il target in categoria
                        cat = normalize_target_single(t)
                        geo_targ_data.append({geo_col: geo_val, 'target_cat': cat})
                
                if geo_targ_data:
                    gt_df = pd.DataFrame(geo_targ_data)
                    pivot_gt = pd.crosstab(gt_df[geo_col], gt_df['target_cat'])
                    
                    # Riordina le colonne secondo TARGET_ORDER
                    ordered_cols = [c for c in TARGET_ORDER if c in pivot_gt.columns]
                    extra_cols = [c for c in pivot_gt.columns if c not in TARGET_ORDER]
                    pivot_gt = pivot_gt[ordered_cols + extra_cols]
                    
                    # Normalizza per riga
                    pivot_gt_pct = pivot_gt.div(pivot_gt.sum(axis=1), axis=0) * 100
                    
                    col_t1, col_t2 = st.columns(2)
                    
                    with col_t1:
                        fig_gt = px.imshow(
                            pivot_gt_pct.round(1),
                            labels=dict(x="Categoria Target", y=geo_level, color="% Attività"),
                            color_continuous_scale="Oranges",
                            aspect="auto",
                            text_auto=".0f"
                        )
                        fig_gt.update_layout(height=max(250, len(pivot_gt) * 35))
                        st.plotly_chart(fig_gt, use_container_width=True)
                    
                    with col_t2:
                        # Bar chart comparativo
                        plot_gt = pivot_gt_pct.reset_index().melt(id_vars=geo_col, var_name='Categoria Target', value_name='Percentuale')
                        fig_bar_gt = px.bar(
                            plot_gt,
                            x=geo_col,
                            y='Percentuale',
                            color='Categoria Target',
                            barmode='group',
                            title='Confronto Target per Territorio'
                        )
                        st.plotly_chart(fig_bar_gt, use_container_width=True)
                    
                    with st.expander("📋 Tabella valori assoluti"):
                        st.dataframe(pivot_gt, use_container_width=True)
                else:
                    st.info("Nessun dato sui target.")

        # =====================================================================
        # TAB 2: ISTITUTO × ATTIVITÀ
        # =====================================================================
        with tab_ist_att:
            st.markdown("### 🏫 Attività per Tipo di Istituto")
            st.markdown("Cosa fanno le diverse tipologie di scuola? (Infanzia, Primaria, Sec. I Grado, Licei, Tecnici, Professionali)")
            
            # Selettore tipo istituto
            tipi_disponibili = []
            for tipos in df_stats['_tipo_norm']:
                tipi_disponibili.extend(tipos)
            tipi_disponibili = sorted(set(t for t in tipi_disponibili if t != 'N/D'))
            
            # Ordina secondo TIPO_ORDER
            tipi_ordinati = [t for t in TIPO_ORDER if t in tipi_disponibili]
            tipi_extra = [t for t in tipi_disponibili if t not in TIPO_ORDER]
            tipi_disponibili = tipi_ordinati + tipi_extra
            
            tipo_filter = st.multiselect(
                "Filtra per tipo di istituto (vuoto = tutti)", 
                tipi_disponibili, 
                key="tipo_filter_ist"
            )
            
            # Prepara dati esplosi per tipo
            ist_data = []
            for idx, row in df_stats.iterrows():
                tipos = row['_tipo_norm']
                if tipo_filter:
                    tipos = [t for t in tipos if t in tipo_filter]
                ambiti = pipe_to_list(row.get('ambiti_attivita', ''))
                metodi = pipe_to_list(row.get('tipologie_metodologia', ''))
                targets = pipe_to_list(row.get('target', ''))
                
                for t in tipos:
                    if t and t != 'N/D':
                        for a in ambiti:
                            ist_data.append({'tipo': t, 'ambito': a, 'field': 'ambito'})
                        for m in metodi:
                            ist_data.append({'tipo': t, 'metodologia': m, 'field': 'metodologia'})
                        for tg in targets:
                            ist_data.append({'tipo': t, 'target': tg, 'field': 'target'})
            
            if not ist_data:
                st.warning("Nessun dato per la selezione.")
            else:
                ist_df = pd.DataFrame(ist_data)
                
                # Conta attività per tipo
                tipo_counts = ist_df[ist_df['field'] == 'ambito'].groupby('tipo').size()
                st.markdown(f"**Attività per tipo di istituto:**")
                for t in tipi_disponibili:
                    if t in tipo_counts.index:
                        st.caption(f"- **{t}**: {tipo_counts[t]} occorrenze")
                
                st.markdown("---")
                
                # === AMBITI PER TIPO ISTITUTO ===
                st.markdown("#### 📌 Ambiti Attività per Tipo Istituto")
                
                ambiti_df = ist_df[ist_df['field'] == 'ambito']
                if not ambiti_df.empty:
                    pivot_ia = pd.crosstab(ambiti_df['tipo'], ambiti_df['ambito'])
                    
                    # Riordina righe
                    pivot_ia = pivot_ia.reindex(index=[t for t in TIPO_ORDER if t in pivot_ia.index])
                    
                    # Limita colonne
                    top_ambiti = ambiti_df['ambito'].value_counts().head(12).index.tolist()
                    pivot_ia = pivot_ia.reindex(columns=top_ambiti, fill_value=0)
                    
                    # Percentuali per riga
                    pivot_ia_pct = pivot_ia.div(pivot_ia.sum(axis=1), axis=0) * 100
                    
                    fig_ia = px.imshow(
                        pivot_ia_pct.round(1),
                        labels=dict(x="Ambito Attività", y="Tipo Istituto", color="% Attività"),
                        color_continuous_scale="Blues",
                        aspect="auto",
                        text_auto=".0f"
                    )
                    fig_ia.update_layout(height=max(250, len(pivot_ia) * 45))
                    st.plotly_chart(fig_ia, use_container_width=True)
                    
                    with st.expander("📋 Tabella valori assoluti"):
                        st.dataframe(pivot_ia, use_container_width=True)
                
                st.markdown("---")
                
                # === METODOLOGIE PER TIPO ISTITUTO ===
                st.markdown("#### 📚 Metodologie per Tipo Istituto")
                
                met_df = ist_df[ist_df['field'] == 'metodologia']
                if not met_df.empty:
                    pivot_im = pd.crosstab(met_df['tipo'], met_df['metodologia'])
                    
                    # Riordina righe
                    pivot_im = pivot_im.reindex(index=[t for t in TIPO_ORDER if t in pivot_im.index])
                    
                    # Limita colonne
                    top_met = met_df['metodologia'].value_counts().head(12).index.tolist()
                    pivot_im = pivot_im.reindex(columns=top_met, fill_value=0)
                    
                    # Percentuali per riga
                    pivot_im_pct = pivot_im.div(pivot_im.sum(axis=1), axis=0) * 100
                    
                    fig_im = px.imshow(
                        pivot_im_pct.round(1),
                        labels=dict(x="Metodologia", y="Tipo Istituto", color="% Attività"),
                        color_continuous_scale="Greens",
                        aspect="auto",
                        text_auto=".0f"
                    )
                    fig_im.update_layout(height=max(250, len(pivot_im) * 45))
                    st.plotly_chart(fig_im, use_container_width=True)
                    
                    with st.expander("📋 Tabella valori assoluti"):
                        st.dataframe(pivot_im, use_container_width=True)
                
                st.markdown("---")
                
                # === TARGET PER TIPO ISTITUTO ===
                st.markdown("#### 👥 Target per Tipo Istituto")
                st.caption("I target sono raggruppati in categorie")
                
                targ_df = ist_df[ist_df['field'] == 'target'].copy()
                if not targ_df.empty:
                    # Normalizza i target in categorie
                    targ_df['target_cat'] = targ_df['target'].apply(normalize_target_single)
                    
                    pivot_it = pd.crosstab(targ_df['tipo'], targ_df['target_cat'])
                    
                    # Riordina righe
                    pivot_it = pivot_it.reindex(index=[t for t in TIPO_ORDER if t in pivot_it.index])
                    
                    # Riordina colonne secondo TARGET_ORDER
                    ordered_cols = [c for c in TARGET_ORDER if c in pivot_it.columns]
                    extra_cols = [c for c in pivot_it.columns if c not in TARGET_ORDER]
                    pivot_it = pivot_it[ordered_cols + extra_cols]
                    
                    # Percentuali per riga
                    pivot_it_pct = pivot_it.div(pivot_it.sum(axis=1), axis=0) * 100
                    
                    col_it1, col_it2 = st.columns(2)
                    
                    with col_it1:
                        fig_it = px.imshow(
                            pivot_it_pct.round(1),
                            labels=dict(x="Categoria Target", y="Tipo Istituto", color="% Attività"),
                            color_continuous_scale="Purples",
                            aspect="auto",
                            text_auto=".0f"
                        )
                        fig_it.update_layout(height=max(200, len(pivot_it) * 40))
                        st.plotly_chart(fig_it, use_container_width=True)
                    
                    with col_it2:
                        # Bar chart comparativo
                        plot_it = pivot_it_pct.reset_index().melt(id_vars='tipo', var_name='Categoria Target', value_name='Percentuale')
                        fig_bar_it = px.bar(
                            plot_it,
                            x='tipo',
                            y='Percentuale',
                            color='Categoria Target',
                            barmode='group',
                            title='Confronto Target per Tipo Istituto'
                        )
                        st.plotly_chart(fig_bar_it, use_container_width=True)
                    
                    with st.expander("📋 Tabella valori assoluti"):
                        st.dataframe(pivot_it, use_container_width=True)

        # =====================================================================
        # TAB 3: ANALISI COMPARATIVA
        # =====================================================================
        with tab_confronto:
            st.markdown("### 🔍 Analisi Comparativa")
            st.markdown("Confronta territori o tipi di istituto specifici.")
            
            compare_mode = st.radio(
                "Cosa vuoi confrontare?",
                ["Confronto Regioni", "Confronto Tipi Istituto", "Incrocio Territorio × Tipo Istituto"],
                horizontal=True,
                key="compare_mode"
            )
            
            st.markdown("---")
            
            if compare_mode == "Confronto Regioni":
                st.markdown("#### 🗺️ Confronto tra Regioni")
                
                regioni_disp = sorted(df_stats['regione'].dropna().unique().tolist())
                regioni_sel = st.multiselect(
                    "Seleziona 2-5 regioni da confrontare",
                    regioni_disp,
                    default=regioni_disp[:3] if len(regioni_disp) >= 3 else regioni_disp,
                    max_selections=5,
                    key="compare_regioni"
                )
                
                if len(regioni_sel) >= 2:
                    df_cmp = df_stats[df_stats['regione'].isin(regioni_sel)]
                    
                    # Ambiti
                    st.markdown("##### Ambiti Attività")
                    cmp_amb_data = []
                    for idx, row in df_cmp.iterrows():
                        reg = row['regione']
                        for a in pipe_to_list(row.get('ambiti_attivita', '')):
                            cmp_amb_data.append({'regione': reg, 'ambito': a})
                    
                    if cmp_amb_data:
                        cmp_amb_df = pd.DataFrame(cmp_amb_data)
                        pivot_cmp = pd.crosstab(cmp_amb_df['regione'], cmp_amb_df['ambito'], normalize='index') * 100
                        
                        top_amb = cmp_amb_df['ambito'].value_counts().head(10).index.tolist()
                        pivot_cmp = pivot_cmp.reindex(columns=top_amb, fill_value=0)
                        
                        fig_cmp = px.bar(
                            pivot_cmp.reset_index().melt(id_vars='regione', var_name='Ambito', value_name='%'),
                            x='regione',
                            y='%',
                            color='Ambito',
                            barmode='group',
                            title='Distribuzione Ambiti per Regione (%)'
                        )
                        st.plotly_chart(fig_cmp, use_container_width=True)
                    
                    # Metodologie
                    st.markdown("##### Metodologie")
                    cmp_met_data = []
                    for idx, row in df_cmp.iterrows():
                        reg = row['regione']
                        for m in pipe_to_list(row.get('tipologie_metodologia', '')):
                            cmp_met_data.append({'regione': reg, 'metodologia': m})
                    
                    if cmp_met_data:
                        cmp_met_df = pd.DataFrame(cmp_met_data)
                        pivot_met = pd.crosstab(cmp_met_df['regione'], cmp_met_df['metodologia'], normalize='index') * 100
                        
                        top_met = cmp_met_df['metodologia'].value_counts().head(8).index.tolist()
                        pivot_met = pivot_met.reindex(columns=top_met, fill_value=0)
                        
                        fig_met = px.bar(
                            pivot_met.reset_index().melt(id_vars='regione', var_name='Metodologia', value_name='%'),
                            x='regione',
                            y='%',
                            color='Metodologia',
                            barmode='group',
                            title='Distribuzione Metodologie per Regione (%)'
                        )
                        st.plotly_chart(fig_met, use_container_width=True)
                else:
                    st.info("Seleziona almeno 2 regioni per il confronto.")
            
            elif compare_mode == "Confronto Tipi Istituto":
                st.markdown("#### 🏫 Confronto tra Tipi di Istituto")
                
                tipi_sel = st.multiselect(
                    "Seleziona 2-4 tipi da confrontare",
                    TIPO_ORDER,
                    default=TIPO_ORDER[:3] if len(TIPO_ORDER) >= 3 else TIPO_ORDER,
                    max_selections=4,
                    key="compare_tipi"
                )
                
                if len(tipi_sel) >= 2:
                    # Prepara dati
                    cmp_tipo_data = []
                    for idx, row in df_stats.iterrows():
                        tipos = [t for t in row['_tipo_norm'] if t in tipi_sel]
                        for t in tipos:
                            for a in pipe_to_list(row.get('ambiti_attivita', '')):
                                cmp_tipo_data.append({'tipo': t, 'ambito': a, 'field': 'ambito'})
                            for m in pipe_to_list(row.get('tipologie_metodologia', '')):
                                cmp_tipo_data.append({'tipo': t, 'metodologia': m, 'field': 'metodologia'})
                    
                    if cmp_tipo_data:
                        cmp_df = pd.DataFrame(cmp_tipo_data)
                        
                        # Ambiti
                        st.markdown("##### Ambiti Attività")
                        amb_df = cmp_df[cmp_df['field'] == 'ambito']
                        pivot_amb = pd.crosstab(amb_df['tipo'], amb_df['ambito'], normalize='index') * 100
                        pivot_amb = pivot_amb.reindex(index=[t for t in TIPO_ORDER if t in pivot_amb.index])
                        
                        top_amb = amb_df['ambito'].value_counts().head(10).index.tolist()
                        pivot_amb = pivot_amb.reindex(columns=top_amb, fill_value=0)
                        
                        fig_amb = px.bar(
                            pivot_amb.reset_index().melt(id_vars='tipo', var_name='Ambito', value_name='%'),
                            x='tipo',
                            y='%',
                            color='Ambito',
                            barmode='group',
                            title='Distribuzione Ambiti per Tipo Istituto (%)'
                        )
                        st.plotly_chart(fig_amb, use_container_width=True)
                        
                        # Metodologie
                        st.markdown("##### Metodologie")
                        met_df = cmp_df[cmp_df['field'] == 'metodologia']
                        pivot_met = pd.crosstab(met_df['tipo'], met_df['metodologia'], normalize='index') * 100
                        pivot_met = pivot_met.reindex(index=[t for t in TIPO_ORDER if t in pivot_met.index])
                        
                        top_met = met_df['metodologia'].value_counts().head(8).index.tolist()
                        pivot_met = pivot_met.reindex(columns=top_met, fill_value=0)
                        
                        fig_met = px.bar(
                            pivot_met.reset_index().melt(id_vars='tipo', var_name='Metodologia', value_name='%'),
                            x='tipo',
                            y='%',
                            color='Metodologia',
                            barmode='group',
                            title='Distribuzione Metodologie per Tipo Istituto (%)'
                        )
                        st.plotly_chart(fig_met, use_container_width=True)
                else:
                    st.info("Seleziona almeno 2 tipi per il confronto.")
            
            else:  # Incrocio Territorio × Tipo Istituto
                st.markdown("#### 🔀 Incrocio Territorio × Tipo Istituto")
                st.markdown("Esempio: *In Sicilia, cosa fanno i Licei rispetto ai Tecnici?*")
                
                col_geo, col_tipo = st.columns(2)
                
                with col_geo:
                    geo_sel = st.selectbox(
                        "Seleziona Regione o Area",
                        ["Tutte"] + sorted(df_stats['regione'].dropna().unique().tolist()),
                        key="incrocio_geo"
                    )
                
                with col_tipo:
                    tipi_incr = st.multiselect(
                        "Seleziona Tipi Istituto",
                        TIPO_ORDER,
                        default=TIPO_ORDER,
                        key="incrocio_tipi"
                    )
                
                # Filtra
                if geo_sel != "Tutte":
                    df_incr = df_stats[df_stats['regione'] == geo_sel]
                    geo_label = geo_sel
                else:
                    df_incr = df_stats
                    geo_label = "Italia"
                
                if df_incr.empty or not tipi_incr:
                    st.warning("Nessun dato per la selezione.")
                else:
                    # Prepara dati
                    incr_data = []
                    for idx, row in df_incr.iterrows():
                        tipos = [t for t in row['_tipo_norm'] if t in tipi_incr]
                        for t in tipos:
                            for a in pipe_to_list(row.get('ambiti_attivita', '')):
                                incr_data.append({'tipo': t, 'ambito': a})
                            for m in pipe_to_list(row.get('tipologie_metodologia', '')):
                                incr_data.append({'tipo': t, 'metodologia': m})
                    
                    if incr_data:
                        incr_df = pd.DataFrame(incr_data)
                        
                        st.markdown(f"##### Ambiti in **{geo_label}** per Tipo Istituto")
                        
                        # Pivot ambiti
                        amb_incr = incr_df[incr_df['ambito'].notna()].copy()
                        if not amb_incr.empty:
                            pivot_incr_amb = pd.crosstab(amb_incr['tipo'], amb_incr['ambito'], normalize='index') * 100
                            pivot_incr_amb = pivot_incr_amb.reindex(index=[t for t in TIPO_ORDER if t in pivot_incr_amb.index])
                            
                            top_amb = amb_incr['ambito'].value_counts().head(10).index.tolist()
                            pivot_incr_amb = pivot_incr_amb.reindex(columns=top_amb, fill_value=0)
                            
                            fig_incr_amb = px.imshow(
                                pivot_incr_amb.round(1),
                                labels=dict(x="Ambito", y="Tipo Istituto", color="% Attività"),
                                color_continuous_scale="YlOrRd",
                                aspect="auto",
                                text_auto=".0f",
                                title=f"Ambiti Attività in {geo_label}"
                            )
                            fig_incr_amb.update_layout(height=max(200, len(pivot_incr_amb) * 50))
                            st.plotly_chart(fig_incr_amb, use_container_width=True)
                        
                        st.markdown(f"##### Metodologie in **{geo_label}** per Tipo Istituto")
                        
                        # Pivot metodologie
                        met_incr = incr_df[incr_df['metodologia'].notna()].copy()
                        if not met_incr.empty:
                            pivot_incr_met = pd.crosstab(met_incr['tipo'], met_incr['metodologia'], normalize='index') * 100
                            pivot_incr_met = pivot_incr_met.reindex(index=[t for t in TIPO_ORDER if t in pivot_incr_met.index])
                            
                            top_met = met_incr['metodologia'].value_counts().head(10).index.tolist()
                            pivot_incr_met = pivot_incr_met.reindex(columns=top_met, fill_value=0)
                            
                            fig_incr_met = px.imshow(
                                pivot_incr_met.round(1),
                                labels=dict(x="Metodologia", y="Tipo Istituto", color="% Attività"),
                                color_continuous_scale="YlGnBu",
                                aspect="auto",
                                text_auto=".0f",
                                title=f"Metodologie in {geo_label}"
                            )
                            fig_incr_met.update_layout(height=max(200, len(pivot_incr_met) * 50))
                            st.plotly_chart(fig_incr_met, use_container_width=True)
                    else:
                        st.info("Nessun dato per l'incrocio selezionato.")

# === SEZIONE EXPORT ===
elif section == "📥 Export":
    st.subheader("📥 Esporta Dati")

    st.markdown(f"**{len(df_filtered)} pratiche** pronte per l'esportazione (filtrate)")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📄 Formato JSON")
        st.markdown("Esporta i dati completi in formato JSON.")

        # Converti DataFrame in lista di dict per JSON
        practices_list = df_filtered.to_dict('records')

        json_data = json.dumps(
            {
                "exported_at": datetime.now().isoformat(),
                "filters_applied": {
                    "categoria": sel_categoria if sel_categoria != "Tutte" else None,
                    "regioni": sel_regioni if sel_regioni else None,
                    "province": sel_province if sel_province else None,
                    "tipi_scuola": sel_tipi if sel_tipi else None,
                    "aree_geografiche": sel_aree if sel_aree else None,
                    "targets": sel_targets if sel_targets else None,
                    "maturity_range": list(sel_maturity) if sel_maturity else None,
                    "search_text": search if search else None
                },
                "total_practices": len(df_filtered),
                "practices": practices_list
            },
            ensure_ascii=False,
            indent=2
        )

        st.download_button(
            "📥 Scarica JSON",
            data=json_data.encode('utf-8'),
            file_name=f"buone_pratiche_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
            mime="application/json"
        )

    with col2:
        st.markdown("### 📊 Formato CSV")
        st.markdown("Esporta un riepilogo tabellare in formato CSV.")

        if not df_filtered.empty:
            csv_data = df_filtered.to_csv(index=False)

            st.download_button(
                "📥 Scarica CSV",
                data=csv_data.encode('utf-8'),
                file_name=f"buone_pratiche_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )
        else:
            st.info("Nessun dato da esportare.")

    # Anteprima tabella
    st.markdown("### 👁️ Anteprima Dati")
    if not df_filtered.empty:
        preview_cols = ['titolo', 'categoria', 'nome_scuola', 'regione', 'tipo_scuola']
        available_preview = [c for c in preview_cols if c in df_filtered.columns]
        st.dataframe(
            df_filtered[available_preview].head(20),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Nessun dato da visualizzare.")

render_footer()
