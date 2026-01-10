import pandas as pd
import streamlit as st
import os

TIPI_SCUOLA = [
    "Infanzia",
    "Primaria",
    "I Grado",
    "Liceo",
    "Tecnico",
    "Professionale"
]

GESTIONE_SCUOLA = [
    "Statale",
    "Paritaria"
]

SUMMARY_FILE = 'data/analysis_summary.csv'

DIMENSIONS = {
    'mean_finalita': 'Finalita',
    'mean_obiettivi': 'Obiettivi',
    'mean_governance': 'Governance',
    'mean_didattica_orientativa': 'Didattica',
    'mean_opportunita': 'Opportunita'
}

# Mapping centralizzato per etichette colonne (evita duplicazione nelle pagine)
LABEL_MAP = {
    'mean_finalita': 'Media Finalità',
    'mean_obiettivi': 'Media Obiettivi', 
    'mean_governance': 'Media Governance',
    'mean_didattica_orientativa': 'Media Didattica',
    'mean_opportunita': 'Media Opportunità',
    'ptof_orientamento_maturity_index': 'Indice RO',
    'partnership_count': 'N. Partnership',
    'activities_count': 'N. Attività',
    '2_1_score': 'Sezione Dedicata',
    'has_sezione_dedicata': 'Sezione Dedicata'
}

# Versione compatta per grafici
LABEL_MAP_SHORT = {
    'mean_finalita': 'Finalità',
    'mean_obiettivi': 'Obiettivi', 
    'mean_governance': 'Governance',
    'mean_didattica_orientativa': 'Didattica',
    'mean_opportunita': 'Opportunità',
    'ptof_orientamento_maturity_index': 'Indice RO'
}

def get_label(col: str, short: bool = False) -> str:
    """Restituisce l'etichetta leggibile per una colonna."""
    label_dict = LABEL_MAP_SHORT if short else LABEL_MAP
    return label_dict.get(col, col.replace('_', ' ').title())

def normalize_statale_paritaria(value: object) -> str:
    """Normalizza il campo statale_paritaria in Statale/Paritaria/ND/Altro."""
    if pd.isna(value):
        return "ND"
    raw = str(value).strip()
    if not raw or raw.lower() in ("nd", "n/d", "nan"):
        return "ND"
    lower = raw.lower()
    if "paritaria" in lower or "non statale" in lower:
        return "Paritaria"
    if "statale" in lower:
        return "Statale"
    if raw in GESTIONE_SCUOLA:
        return raw
    return "Altro"

def scale_to_pct(score: float) -> float:
    """
    Restituisce il punteggio nella scala originale 1-7.
    Funzione identità per retrocompatibilità.
    """
    if pd.isna(score):
        return 0.0
    return float(score)

def format_pct(score: float, decimals: int = 1) -> str:
    """
    Formatta punteggio in scala 1-7 (es: '5.0/7').
    """
    if pd.isna(score):
        return "N/D"
    return f"{float(score):.{decimals}f}/7"

def split_multi_value(value):
    if pd.isna(value):
        return []
    return [part.strip() for part in str(value).split(',') if part.strip()]



def load_summary_data():
    if os.path.exists(SUMMARY_FILE):
        return pd.read_csv(SUMMARY_FILE)
    return pd.DataFrame()

def find_pdf_for_school(school_id, base_dirs=None):
    import glob
    import os

    if not school_id:
        return None

    base_dirs = base_dirs or ["ptof_processed", "ptof_inbox", "ptof_inviati"]
    patterns = []
    for base in base_dirs:
        patterns.extend([
            os.path.join(base, f"*{school_id}*.pdf"),
            os.path.join(base, f"{school_id}*.pdf"),
            os.path.join(base, f"*_{school_id}_*.pdf"),
            os.path.join(base, "**", f"*{school_id}*.pdf"),
        ])

    pdf_files = []
    for pattern in patterns:
        pdf_files.extend(glob.glob(pattern, recursive=True))

    if not pdf_files:
        for base in base_dirs:
            for pdf in glob.glob(os.path.join(base, "**", "*.pdf"), recursive=True):
                if school_id.upper() in os.path.basename(pdf).upper():
                    pdf_files.append(pdf)
                    break
            if pdf_files:
                break

    if not pdf_files:
        return None

    return sorted(set(pdf_files))[0]

def explode_school_types(df: pd.DataFrame, col='tipo_scuola') -> pd.DataFrame:
    """
    Explodes the dataframe so that rows with multiple school types (comma separated)
    are duplicated, one for each type. 
    Useful for aggregation charts by type.
    """
    if col not in df.columns:
        return df
    
    # Check if we have any comma separated values
    if not df[col].astype(str).str.contains(',').any():
        return df
        
    df_temp = df.copy()
    # Split by comma and stack involves index manipulation
    df_temp[col] = df_temp[col].apply(split_multi_value)
    # Explode
    df_exploded = df_temp.explode(col)
    return df_exploded

def explode_school_grades(df: pd.DataFrame, col='ordine_grado') -> pd.DataFrame:
    """
    Explodes the dataframe so that rows with multiple grades (comma separated)
    are duplicated, one for each grade. 
    Useful for aggregation charts by grade.
    """
    if col not in df.columns:
        return df
    
    # Check if we have any comma separated values
    if not df[col].astype(str).str.contains(',').any():
        return df
        
    df_temp = df.copy()
    # Split by comma and stack involves index manipulation
    df_temp[col] = df_temp[col].apply(split_multi_value)
    # Explode
    df_exploded = df_temp.explode(col)
    return df_exploded

def get_unique_types(df: pd.DataFrame, col='tipo_scuola') -> list:
    """Returns sorted unique types from the column."""
    if col not in df.columns:
        return sorted(TIPI_SCUOLA)
    
    all_types = set(TIPI_SCUOLA)
    for val in df[col].dropna():
        for t in split_multi_value(val):
            if t.lower() == 'nan':
                continue
            all_types.add(t)
    return sorted(list(all_types))

def filter_by_type(df: pd.DataFrame, selected_types: list, col='tipo_scuola') -> pd.DataFrame:
    """
    Filters df to keep rows where 'tipo_scuola' contains ANY of the selected types.
    """
    if not selected_types:
        return df
        
    if col not in df.columns:
        return df
    
    def has_overlap(val):
        if pd.isna(val): return False
        current = set(split_multi_value(val))
        return not set(selected_types).isdisjoint(current)
        
    return df[df[col].apply(has_overlap)]

def apply_sidebar_filters(df: pd.DataFrame, extra_clear_keys: list = None) -> pd.DataFrame:
    """
    Applies standard sidebar filters (Area, Tipo, Territorio, Ordine) to the dataframe.
    Returns the filtered dataframe.
    """
    st.sidebar.header("🔍 Filtri Globali")
    
    # Reset Button
    if st.sidebar.button("🗑️ Rimuovi Filtri", use_container_width=True):
        keys = ["filter_area", "filter_regione", "filter_provincia", "filter_tipo", "filter_terr", "filter_grado", "home_score_range"]
        if extra_clear_keys:
            keys.extend(extra_clear_keys)
            
        for k in keys:
            if k in st.session_state:
                if k == 'home_score_range':
                    # Delete slider key so it reinitializes with data defaults
                    del st.session_state[k]
                elif 'chk' in k or 'checkbox' in k:
                    st.session_state[k] = False
                elif 'multiselect' in k or 'list' in k or k.startswith('filter_'):
                    # Sidebar filters are lists usually, but sometimes boolean if custom
                    if isinstance(st.session_state[k], bool): st.session_state[k] = False
                    else: st.session_state[k] = []
                else:
                    st.session_state[k] = ""  # Default for text inputs
        st.rerun()
    
    # Area filter
    if 'area_geografica' in df.columns:
        areas = sorted([x for x in df['area_geografica'].dropna().unique() if str(x) not in ['nan', 'ND', '']])
        if areas:
            selected_areas = st.sidebar.multiselect("Area Geografica", areas, key="filter_area")
            if selected_areas:
                df = df[df['area_geografica'].isin(selected_areas)]

    # Regione filter
    if 'regione' in df.columns:
        regioni = sorted([x for x in df['regione'].dropna().unique() if str(x) not in ['nan', 'ND', '']])
        if regioni:
            selected_regioni = st.sidebar.multiselect("Regione", regioni, key="filter_regione")
            if selected_regioni:
                df = df[df['regione'].isin(selected_regioni)]
    
    # Provincia filter
    if 'provincia' in df.columns:
        province = sorted([x for x in df['provincia'].dropna().unique() if str(x) not in ['nan', 'ND', '']])
        if province:
            selected_province = st.sidebar.multiselect("Provincia", province, key="filter_provincia")
            if selected_province:
                df = df[df['provincia'].isin(selected_province)]

    # Tipo scuola filter
    if 'tipo_scuola' in df.columns:
        tipi = get_unique_types(df)
        if tipi:
            # Clean invalid values from session_state (combinations like "Liceo, Tecnico")
            if 'filter_tipo' in st.session_state:
                current = st.session_state['filter_tipo']
                if isinstance(current, list):
                    # Remove any value that contains comma (combinations)
                    valid = [t for t in current if t in tipi]
                    if valid != current:
                        st.session_state['filter_tipo'] = valid

            selected_tipi = st.sidebar.multiselect("Tipo Scuola", tipi, key="filter_tipo")
            if selected_tipi:
                df = filter_by_type(df, selected_tipi)

    # Territorio filter
    if 'territorio' in df.columns:
        # Normalize text
        df['territorio'] = df['territorio'].fillna('ND')
        territori = sorted([x for x in df['territorio'].unique() if str(x) not in ['nan', 'ND', '']])
        if territori:
            selected_territori = st.sidebar.multiselect("Territorio", territori, key="filter_terr")
            if selected_territori:
                df = df[df['territorio'].isin(selected_territori)]

    # Ordine grado filter
    if 'ordine_grado' in df.columns:
        # Get existing unique values (exploding commas if any)
        existing_gradi = set()
        for x in df['ordine_grado'].dropna().unique():
            if str(x) not in ['nan', 'ND', '']:
                for g in split_multi_value(x):
                    if g:
                        existing_gradi.add(g)
        # ensure "Infanzia" and "Primaria" are always available options
        for forced_option in ["Infanzia", "Primaria"]:
            existing_gradi.add(forced_option)
        
        gradi = sorted(list(existing_gradi))

        if len(gradi) > 0:
            # Clean invalid values from session_state
            if 'filter_grado' in st.session_state:
                current = st.session_state['filter_grado']
                if isinstance(current, list):
                    valid = [g for g in current if g in gradi]
                    if valid != current:
                        st.session_state['filter_grado'] = valid

            selected_gradi = st.sidebar.multiselect("Ordine Grado", gradi, key="filter_grado")
            if selected_gradi:
                 # Use same logic as filters by type to partial match "I Grado, II Grado"
                 def has_grade_overlap(val):
                     if pd.isna(val): return False
                     # Split cell value by comma
                     current = set(split_multi_value(val))
                     # Check if any selected grade is in current cell's grades
                     return not set(selected_gradi).isdisjoint(current)
                 
                 df = df[df['ordine_grado'].apply(has_grade_overlap)]

    st.sidebar.info(f"📚 Scuole Filtrate: **{len(df)}**")
    return df


def render_footer():
    """
    Renderizza il footer standard ORIENTA+ con branding, contatti e licenza.
    Licenza: CC BY-NC-ND 4.0 (Attribution-NonCommercial-NoDerivatives)
    """
    st.markdown("---")
    st.markdown("""
<div style="text-align: center; padding: 18px 0; color: #666; font-size: 0.85rem;">
    <div style="font-size: 1.2rem; font-weight: bold; margin-bottom: 6px;">
        🧭 ORIENTA+
    </div>
    <div style="margin: 4px 0;">
        Piattaforma di Analisi della Robustezza dell'Orientamento nei PTOF •
        Sviluppato da <strong>Daniele Dragoni</strong> — Dottorando, Università Roma Tre •
        📧 <a href="mailto:daniele.dragoni@uniroma3.it">daniele.dragoni@uniroma3.it</a>
    </div>
    <div style="margin: 8px 0 4px; font-size: 0.75rem; color: #888;">
        <a href="https://creativecommons.org/licenses/by-nc-nd/4.0/" target="_blank" style="color: #888;">
            <img src="https://licensebuttons.net/l/by-nc-nd/4.0/88x31.png" alt="CC BY-NC-ND 4.0" style="vertical-align: middle;">
        </a>
    </div>
    <div style="margin: 4px 0; font-size: 0.75rem; color: #888;">
        Quest'opera è distribuita con Licenza
        <a href="https://creativecommons.org/licenses/by-nc-nd/4.0/deed.it" target="_blank" style="color: #666;">Creative Commons Attribuzione - Non commerciale - Non opere derivate 4.0 Internazionale</a> •
        <strong>ORIENTA+</strong> è un marchio registrato.
    </div>
</div>
    """, unsafe_allow_html=True)
