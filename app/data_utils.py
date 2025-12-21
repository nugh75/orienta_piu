import pandas as pd
import streamlit as st

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
    df_temp[col] = df_temp[col].astype(str).str.split(', ')
    # Explode
    df_exploded = df_temp.explode(col)
    return df_exploded

def get_unique_types(df: pd.DataFrame, col='tipo_scuola') -> list:
    """Returns sorted unique types from the column."""
    if col not in df.columns:
        return []
    
    all_types = set()
    for val in df[col].dropna().astype(str):
        if val == 'nan': continue
        for t in val.split(', '):
            if t:
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
        current = set(str(val).split(', '))
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
        keys = ["filter_area", "filter_tipo", "filter_terr", "filter_grado"]
        if extra_clear_keys:
            keys.extend(extra_clear_keys)
            
        for k in keys:
            if k in st.session_state:
                if 'chk' in k or 'checkbox' in k:
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

    # Tipo scuola filter
    if 'tipo_scuola' in df.columns:
        tipi = get_unique_types(df)
        if tipi:
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
        gradi = sorted([x for x in df['ordine_grado'].dropna().unique() if str(x) not in ['nan', 'ND', '']])
        if len(gradi) > 0:
            selected_gradi = st.sidebar.multiselect("Ordine Grado", gradi, key="filter_grado")
            if selected_gradi:
                df = df[df['ordine_grado'].isin(selected_gradi)]

    st.sidebar.info(f"📚 Scuole Filtrate: **{len(df)}**")
    return df
