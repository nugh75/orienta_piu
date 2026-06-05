# 📊 Analisi Dimensioni - Esplorazione aggregata delle dimensioni di indagine
# Filtri geografici + Visualizzazione raggruppata per dimensione

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import sys
from pathlib import Path

# Aggiungi la root del progetto al path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from src.utils.constants import REGIONE_TO_AREA
from data_utils import (
    render_footer,
    load_summary_data,
    get_index_column,
    DIMENSIONS,
    TIPI_SCUOLA,
    filter_by_type,
    get_unique_types
)
from page_control import setup_page, is_admin_logged_in

st.set_page_config(page_title="ORIENTA+ | Analisi Dimensioni", page_icon="🧭", layout="wide")
setup_page("pages/05_Dimensioni.py")

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
</style>
""", unsafe_allow_html=True)

# === CONSTANTS ===
ORDINI_CANONICI = ["Infanzia", "Primaria", "I Grado", "II Grado"]

GESTIONE_SCUOLA = [
    "Statale",
    "Paritaria"
]

# Sotto-indicatori per ogni dimensione (stessi di Dettaglio Scuola)
SUB_INDICATORS = {
    'Finalita': {
        '2_3_finalita_attitudini_score': 'Attitudini',
        '2_3_finalita_interessi_score': 'Interessi',
        '2_3_finalita_progetto_vita_score': 'Progetto di Vita',
        '2_3_finalita_transizioni_formative_score': 'Transizioni Formative',
        '2_3_finalita_capacita_orientative_opportunita_score': 'Capacità Orientative'
    },
    'Obiettivi': {
        '2_4_obiettivo_ridurre_abbandono_score': 'Ridurre Abbandono',
        '2_4_obiettivo_continuita_territorio_score': 'Continuità Territorio',
        '2_4_obiettivo_contrastare_neet_score': 'Contrastare NEET',
        '2_4_obiettivo_lifelong_learning_score': 'Lifelong Learning'
    },
    'Governance': {
        '2_5_azione_coordinamento_servizi_score': 'Coordinamento Servizi',
        '2_5_azione_dialogo_docenti_studenti_score': 'Dialogo Docenti-Studenti',
        '2_5_azione_rapporto_scuola_genitori_score': 'Rapporto Scuola-Genitori',
        '2_5_azione_monitoraggio_azioni_score': 'Monitoraggio Azioni',
        '2_5_azione_sistema_integrato_inclusione_fragilita_score': 'Inclusione Fragilità'
    },
    'Didattica': {
        '2_6_didattica_da_esperienza_studenti_score': 'Esperienza Studenti',
        '2_6_didattica_laboratoriale_score': 'Laboratoriale',
        '2_6_didattica_flessibilita_spazi_tempi_score': 'Flessibilità Spazi/Tempi',
        '2_6_didattica_interdisciplinare_score': 'Interdisciplinare'
    },
    'Opportunita': {
        '2_7_opzionali_culturali_score': 'Culturali',
        '2_7_opzionali_laboratoriali_espressive_score': 'Laboratoriali Espressive',
        '2_7_opzionali_ludiche_ricreative_score': 'Ludiche Ricreative',
        '2_7_opzionali_volontariato_score': 'Volontariato',
        '2_7_opzionali_sportive_score': 'Sportive'
    }
}

DIM_ICONS = {
    'Finalita': '🎯',
    'Obiettivi': '📌',
    'Governance': '🏛️',
    'Didattica': '📚',
    'Opportunita': '🌟'
}


# === FUNZIONI UTILITY ===

def build_geo_hierarchy(df: pd.DataFrame) -> dict:
    """
    Costruisce la gerarchia geografica Area → Regioni → Province dai dati effettivi.
    """
    hierarchy = {
        "area_to_regioni": {},
        "regione_to_province": {}
    }
    
    if df.empty:
        return hierarchy

    if 'area_geografica' in df.columns and 'regione' in df.columns:
        area_reg = df[['area_geografica', 'regione']].dropna().drop_duplicates()
        for area in area_reg['area_geografica'].unique():
            regioni = sorted(area_reg[area_reg['area_geografica'] == area]['regione'].unique().tolist())
            hierarchy["area_to_regioni"][area] = regioni

    if 'regione' in df.columns and 'provincia' in df.columns:
        reg_prov = df[['regione', 'provincia']].dropna().drop_duplicates()
        for regione in reg_prov['regione'].unique():
            province = sorted(reg_prov[reg_prov['regione'] == regione]['provincia'].unique().tolist())
            hierarchy["regione_to_province"][regione] = province

    return hierarchy


def filter_dataframe(df, aree_geo=None, regioni=None, province=None,
                     tipi_scuola=None, ordini_grado=None, gestione=None,
                     index_range=None):
    """Filtra il DataFrame in base ai criteri selezionati."""
    if df.empty:
        return df

    mask = pd.Series(True, index=df.index)

    if aree_geo and len(aree_geo) > 0:
        mask &= df['area_geografica'].isin(aree_geo)

    if regioni and len(regioni) > 0:
        mask &= df['regione'].isin(regioni)

    if province and len(province) > 0:
        mask &= df['provincia'].isin(province)

    if tipi_scuola and len(tipi_scuola) > 0:
        df = filter_by_type(df, tipi_scuola, 'tipo_scuola')
        mask = pd.Series(True, index=df.index)  # Reset mask as df is filtered

    if ordini_grado and len(ordini_grado) > 0:
        if 'ordine_grado' in df.columns:
            df = filter_by_type(df, ordini_grado, 'ordine_grado')
            mask = pd.Series(True, index=df.index) # Reset mask as df is filtered

    if gestione and len(gestione) > 0:
        mask &= df['statale_paritaria'].isin(gestione)

    if index_range and len(index_range) == 2:
        idx_col = get_index_column(df)
        if idx_col in df.columns:
            idx_vals = pd.to_numeric(df[idx_col], errors='coerce')
            mask &= (idx_vals >= index_range[0]) & (idx_vals <= index_range[1])

    return df[mask]


def get_score_color(score):
    """Restituisce il colore basato sul punteggio."""
    if score >= 5:
        return "#2ecc71"  # Verde
    elif score >= 3.5:
        return "#f39c12"  # Giallo/Arancione
    else:
        return "#e74c3c"  # Rosso


def create_gauge(value, title, show_benchmark=None):
    """Crea un gauge chart per visualizzare un punteggio."""
    if pd.isna(value):
        value = 0
    
    if value >= 5:
        bar_color = "#2ecc71"
    elif value >= 3.5:
        bar_color = "#f39c12"
    else:
        bar_color = "#e74c3c"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={'suffix': '/7', 'font': {'size': 24}},
        gauge={
            'axis': {'range': [1, 7], 'tickwidth': 1},
            'bar': {'color': bar_color},
            'bgcolor': "white",
            'steps': [
                {'range': [1, 3], 'color': '#fadbd8'},
                {'range': [3, 5], 'color': '#fef9e7'},
                {'range': [5, 7], 'color': '#d5f5e3'}
            ],
            'threshold': {
                'line': {'color': "black", 'width': 2},
                'thickness': 0.75,
                'value': value
            }
        }
    ))
    fig.update_layout(
        height=150,
        margin=dict(l=20, r=20, t=30, b=10),
        font={'size': 12}
    )
    return fig


def render_sub_indicator_bar(name, value, benchmark=None):
    """Renderizza una barra di progresso per un sotto-indicatore."""
    # Gestisci valori nulli o zero
    if pd.isna(value) or value <= 0:
        value = 0
        pct = 0
        color = "#cccccc"  # Grigio per valori non disponibili
    else:
        color = get_score_color(value)
        # Normalizza 1-7 a 0-100%, con minimo 0
        pct = max(0, (value - 1) / 6 * 100)
    
    delta_html = ""
    if benchmark is not None and value > 0:
        diff = value - benchmark
        delta_color = "#2ecc71" if diff >= 0 else "#e74c3c"
        delta_sign = "+" if diff >= 0 else ""
        delta_html = f'<span style="color: {delta_color}; font-size: 0.75em; margin-left: 5px;">({delta_sign}{diff:.2f})</span>'
    
    # Mostra "N/D" per valori nulli
    value_display = f"{value:.2f}" if value > 0 else "N/D"
    
    return f"""
    <div style="margin-bottom: 8px;">
        <div style="display: flex; justify-content: space-between; font-size: 0.85em;">
            <span>{name}</span>
            <span style="font-weight: bold; color: {color};">{value_display}{delta_html}</span>
        </div>
        <div style="background: #eee; border-radius: 4px; height: 8px; overflow: hidden;">
            <div style="background: {color}; width: {pct}%; height: 100%;"></div>
        </div>
    </div>
    """


# === CARICAMENTO DATI ===
@st.cache_data(ttl=60)
def load_data():
    df = load_summary_data(apply_weights=True)
    if df.empty:
        return pd.DataFrame()
    
    idx_col = get_index_column(df)
    
    # Converti colonne numeriche
    numeric_cols = [idx_col] + list(DIMENSIONS.keys())
    for dim_name, sub_inds in SUB_INDICATORS.items():
        numeric_cols.extend(sub_inds.keys())
    
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df


df = load_data()
INDEX_COL = get_index_column(df) if not df.empty else 'weighted_index'

# === HEADER ===
st.title("📊 Analisi Dimensioni")

with st.expander("📖 Come leggere questa pagina", expanded=False):
    st.markdown("""
    ### 🎯 Scopo della Pagina
    Questa pagina mostra le **5 dimensioni di indagine** aggregate per gruppi di scuole filtrabili.
    
    ### 📊 Come Funziona
    1. **Seleziona i filtri** per restringere l'analisi (area geografica, regione, tipo scuola, ecc.)
    2. **Visualizza le medie aggregate** per ogni dimensione e sotto-indicatore
    3. **Confronta** con il benchmark nazionale (tutte le scuole)
    
    ### 📈 Le 5 Dimensioni
    - 🎯 **Finalità**: Obiettivi formativi dell'orientamento
    - 📌 **Obiettivi**: Risultati attesi (riduzione abbandono, contrasto NEET, ecc.)
    - 🏛️ **Governance**: Organizzazione e coordinamento
    - 📚 **Didattica**: Metodologie didattiche orientative
    - 🌟 **Opportunità**: Attività ed esperienze offerte
    """)

if df.empty:
    st.warning("Nessun dato disponibile. Esegui prima il pipeline di analisi.")
    st.stop()

# Costruisci gerarchia geografica
geo_hierarchy = build_geo_hierarchy(df)

# === FILTRI ===
st.subheader("🔍 Filtri")

# Prima riga: Area geografica, Regione, Provincia
col_f1, col_f2, col_f3 = st.columns(3)

with col_f1:
    aree_disponibili = sorted(df['area_geografica'].dropna().unique().tolist())
    sel_aree = st.multiselect("📍 Area Geografica", aree_disponibili, key="filter_aree")

with col_f2:
    if sel_aree:
        regioni_disponibili = []
        for area in sel_aree:
            regioni_disponibili.extend(geo_hierarchy["area_to_regioni"].get(area, []))
        regioni_disponibili = sorted(set(regioni_disponibili))
    else:
        regioni_disponibili = sorted(df['regione'].dropna().unique().tolist())
    sel_regioni = st.multiselect("🗺️ Regione", regioni_disponibili, key="filter_regioni")

with col_f3:
    province_disponibili = []
    if sel_regioni:
        for regione in sel_regioni:
            province_disponibili.extend(geo_hierarchy["regione_to_province"].get(regione, []))
    elif sel_aree:
        regioni_in_aree = []
        for area in sel_aree:
            regioni_in_aree.extend(geo_hierarchy["area_to_regioni"].get(area, []))
        for regione in regioni_in_aree:
            province_disponibili.extend(geo_hierarchy["regione_to_province"].get(regione, []))
    else:
        province_disponibili = sorted(df['provincia'].dropna().unique().tolist())
    province_disponibili = sorted(set(province_disponibili))
    sel_province = st.multiselect("🏙️ Provincia", province_disponibili, key="filter_province")

# Seconda riga: Tipo scuola, Ordine/Grado, Gestione
col_f4, col_f5, col_f6 = st.columns(3)

with col_f4:
    # Escludiamo solo "II Grado" dai tipi, mantenendo gli altri richiesti
    all_types = get_unique_types(df)
    tipi_disponibili = [t for t in all_types if t != "II Grado"]
    sel_tipi = st.multiselect("🏫 Tipo Scuola", tipi_disponibili, key="filter_tipi")

with col_f5:
    ordini_disponibili = sorted(set(
        o.strip() for o in df['ordine_grado'].dropna().str.split(',').explode()
        if o.strip()
    ))
    # Fallback su costanti se deserto
    if not ordini_disponibili:
        ordini_disponibili = ORDINI_CANONICI
        
    sel_ordini = st.multiselect("📖 Ordine/Grado", ordini_disponibili, key="filter_ordini")

with col_f6:
    sel_gestione = st.multiselect("⚖️ Gestione", GESTIONE_SCUOLA, key="filter_gestione")

# Terza riga: Range indice
with st.expander("➕ Filtro Indice IIPO", expanded=False):
    st.caption("Indice di Informatività delle Pratiche di Orientamento (IIPO)")
    idx_vals = pd.to_numeric(df[INDEX_COL], errors='coerce').dropna()
    if len(idx_vals) > 0:
        min_idx = float(idx_vals.min())
        max_idx = float(idx_vals.max())
        sel_index_range = st.slider(
            "Range Indice IIPO (1-7)",
            min_value=1.0,
            max_value=7.0,
            value=(max(1.0, min_idx), min(7.0, max_idx)),
            step=0.5,
            key="filter_index"
        )
    else:
        sel_index_range = None

# Reset filtri
col_reset, col_info = st.columns([1, 5])
with col_reset:
    if st.button("🗑️ Reset Filtri"):
        for key in ["filter_aree", "filter_regioni", "filter_province", 
                    "filter_tipi", "filter_ordini", "filter_gestione", "filter_index"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

# Applica filtri
df_filtered = filter_dataframe(
    df,
    aree_geo=sel_aree,
    regioni=sel_regioni,
    province=sel_province,
    tipi_scuola=sel_tipi,
    ordini_grado=sel_ordini,
    gestione=sel_gestione,
    index_range=sel_index_range if sel_index_range else None
)

# Info filtri attivi
active_filters = []
if sel_aree:
    active_filters.append(f"Area: {', '.join(sel_aree)}")
if sel_regioni:
    active_filters.append(f"Regione: {', '.join(sel_regioni)}")
if sel_province:
    active_filters.append(f"Provincia: {', '.join(sel_province)}")
if sel_tipi:
    active_filters.append(f"Tipo: {', '.join(sel_tipi)}")
if sel_ordini:
    active_filters.append(f"Ordine: {', '.join(sel_ordini)}")
if sel_gestione:
    active_filters.append(f"Gestione: {', '.join(sel_gestione)}")

with col_info:
    if active_filters:
        st.info(f"🔍 **Filtri attivi:** {' | '.join(active_filters)} → **{len(df_filtered)} scuole**")
    else:
        st.caption(f"Nessun filtro attivo. Totale: {len(df_filtered)} scuole")

st.markdown("---")

# === KPI PRINCIPALI ===
st.subheader("📈 Riepilogo Selezione")

if df_filtered.empty:
    st.warning("Nessuna scuola corrisponde ai filtri selezionati.")
    st.stop()

# Calcola statistiche
n_scuole = len(df_filtered)
mean_index = df_filtered[INDEX_COL].mean()
median_index = df_filtered[INDEX_COL].median()
std_index = df_filtered[INDEX_COL].std()

# Benchmark nazionale (tutte le scuole)
national_mean = df[INDEX_COL].mean()
diff_from_national = mean_index - national_mean

kpi_cols = st.columns(5)
with kpi_cols[0]:
    st.metric("🏫 Scuole Selezionate", f"{n_scuole:,}")
with kpi_cols[1]:
    delta_color = "normal" if diff_from_national >= 0 else "inverse"
    st.metric("📈 Media Indice IIPO", f"{mean_index:.2f}/7", f"{diff_from_national:+.2f} vs naz.", delta_color=delta_color)
with kpi_cols[2]:
    st.metric("📌 Mediana", f"{median_index:.2f}/7")
with kpi_cols[3]:
    st.metric("📊 Dev. Std.", f"{std_index:.2f}")
with kpi_cols[4]:
    pct_buone = (df_filtered[INDEX_COL] >= 5).mean() * 100
    st.metric("✅ Buone (≥5/7)", f"{pct_buone:.1f}%")

st.markdown("---")

# === PUNTEGGI DETTAGLIATI PER DIMENSIONE ===
st.subheader("📊 Punteggi Medi per Dimensione")

st.caption("⚖️ I valori in parentesi indicano la differenza rispetto alla media nazionale")

# Prima riga: Finalità, Obiettivi, Governance
row1_cols = st.columns(3)
dims_row1 = ['Finalita', 'Obiettivi', 'Governance']

for col, dim_name in zip(row1_cols, dims_row1):
    with col:
        dim_col = [k for k, v in DIMENSIONS.items() if v == dim_name]
        if dim_col and dim_col[0] in df_filtered.columns:
            mean_val = df_filtered[dim_col[0]].mean()
            national_dim_mean = df[dim_col[0]].mean()
        else:
            mean_val = 0
            national_dim_mean = 0
        
        st.markdown(f"#### {DIM_ICONS.get(dim_name, '')} {dim_name}")
        st.plotly_chart(create_gauge(mean_val, dim_name), use_container_width=True, key=f"gauge_{dim_name}")
        
        # Sotto-indicatori
        if dim_name in SUB_INDICATORS:
            for sub_col, sub_name in SUB_INDICATORS[dim_name].items():
                if sub_col in df_filtered.columns:
                    sub_val = df_filtered[sub_col].mean()
                    national_sub_mean = df[sub_col].mean() if sub_col in df.columns else sub_val
                    st.markdown(render_sub_indicator_bar(sub_name, sub_val, national_sub_mean), unsafe_allow_html=True)
                else:
                    st.markdown(render_sub_indicator_bar(sub_name, 0), unsafe_allow_html=True)

# Seconda riga: Didattica, Opportunità, Legenda
row2_cols = st.columns([1, 1, 1])
dims_row2 = ['Didattica', 'Opportunita']

for idx, dim_name in enumerate(dims_row2):
    with row2_cols[idx]:
        dim_col = [k for k, v in DIMENSIONS.items() if v == dim_name]
        if dim_col and dim_col[0] in df_filtered.columns:
            mean_val = df_filtered[dim_col[0]].mean()
            national_dim_mean = df[dim_col[0]].mean()
        else:
            mean_val = 0
            national_dim_mean = 0
        
        st.markdown(f"#### {DIM_ICONS.get(dim_name, '')} {dim_name}")
        st.plotly_chart(create_gauge(mean_val, dim_name), use_container_width=True, key=f"gauge_{dim_name}")
        
        # Sotto-indicatori
        if dim_name in SUB_INDICATORS:
            for sub_col, sub_name in SUB_INDICATORS[dim_name].items():
                if sub_col in df_filtered.columns:
                    sub_val = df_filtered[sub_col].mean()
                    national_sub_mean = df[sub_col].mean() if sub_col in df.columns else sub_val
                    st.markdown(render_sub_indicator_bar(sub_name, sub_val, national_sub_mean), unsafe_allow_html=True)
                else:
                    st.markdown(render_sub_indicator_bar(sub_name, 0), unsafe_allow_html=True)

# Legenda
with row2_cols[2]:
    st.markdown("#### 📖 Legenda")
    st.markdown("""
    <div style="padding: 10px; background: #f8f9fa; border-radius: 8px; font-size: 0.85em;">
        <div style="margin-bottom: 8px;">
            <span style="display: inline-block; width: 12px; height: 12px; background: #2ecc71; border-radius: 2px; margin-right: 8px;"></span>
            <strong>5-7:</strong> Ampiamente documentato
        </div>
        <div style="margin-bottom: 8px;">
            <span style="display: inline-block; width: 12px; height: 12px; background: #f39c12; border-radius: 2px; margin-right: 8px;"></span>
            <strong>3.5-5:</strong> Parzialmente documentato
        </div>
        <div>
            <span style="display: inline-block; width: 12px; height: 12px; background: #e74c3c; border-radius: 2px; margin-right: 8px;"></span>
            <strong>1-3.5:</strong> Poco documentato
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("")
    st.info("""
**Cosa mostrano i gauge:**
- **Media aggregata** delle scuole filtrate
- Il **delta in parentesi** indica la differenza rispetto alla media nazionale
- I colori indicano il grado di documentazione della dimensione
    """)

st.markdown("---")

# === RADAR CHART COMPARATIVO ===
st.subheader("🎯 Radar Chart: Selezione vs Nazionale")

# Prepara dati per radar
dim_names = list(DIMENSIONS.values())
filtered_means = []
national_means = []

for dim_col, dim_name in DIMENSIONS.items():
    if dim_col in df_filtered.columns:
        filtered_means.append(df_filtered[dim_col].mean())
        national_means.append(df[dim_col].mean())
    else:
        filtered_means.append(0)
        national_means.append(0)

# Chiudi il radar
dim_names_radar = dim_names + [dim_names[0]]
filtered_means_radar = filtered_means + [filtered_means[0]]
national_means_radar = national_means + [national_means[0]]

fig_radar = go.Figure()

fig_radar.add_trace(go.Scatterpolar(
    r=national_means_radar,
    theta=dim_names_radar,
    fill='toself',
    name='Media Nazionale',
    line=dict(color='#95a5a6', width=2),
    fillcolor='rgba(149, 165, 166, 0.3)'
))

fig_radar.add_trace(go.Scatterpolar(
    r=filtered_means_radar,
    theta=dim_names_radar,
    fill='toself',
    name='Selezione',
    line=dict(color='#3498db', width=3),
    fillcolor='rgba(52, 152, 219, 0.3)'
))

fig_radar.update_layout(
    polar=dict(
        radialaxis=dict(
            visible=True,
            range=[0, 7]
        )
    ),
    showlegend=True,
    height=450,
    margin=dict(l=60, r=60, t=40, b=40)
)

st.plotly_chart(fig_radar, use_container_width=True)

st.markdown("---")

# === TABELLA RIEPILOGATIVA ===
st.subheader("📋 Tabella Riepilogativa Dimensioni")

table_data = []
for dim_col, dim_name in DIMENSIONS.items():
    if dim_col in df_filtered.columns:
        filtered_mean = df_filtered[dim_col].mean()
        national_mean = df[dim_col].mean()
        filtered_std = df_filtered[dim_col].std()
        diff = filtered_mean - national_mean
        
        table_data.append({
            'Dimensione': f"{DIM_ICONS.get(dim_name, '')} {dim_name}",
            'Media Selezione': f"{filtered_mean:.2f}",
            'Media Nazionale': f"{national_mean:.2f}",
            'Differenza': f"{diff:+.2f}",
            'Dev. Std.': f"{filtered_std:.2f}"
        })

df_table = pd.DataFrame(table_data)
st.dataframe(df_table, hide_index=True, use_container_width=True)

# === DISTRIBUZIONE PER DIMENSIONE ===
with st.expander("📊 Distribuzione Punteggi per Dimensione", expanded=False):
    dim_select = st.selectbox(
        "Seleziona dimensione",
        options=list(DIMENSIONS.values()),
        key="dim_distribution"
    )
    
    dim_col = [k for k, v in DIMENSIONS.items() if v == dim_select][0]
    
    if dim_col in df_filtered.columns:
        fig_hist = px.histogram(
            df_filtered,
            x=dim_col,
            nbins=20,
            title=f"Distribuzione {dim_select}",
            labels={dim_col: f"Punteggio {dim_select}"},
            color_discrete_sequence=['#3498db']
        )
        fig_hist.add_vline(
            x=df_filtered[dim_col].mean(),
            line_dash="dash",
            line_color="red",
            annotation_text=f"Media: {df_filtered[dim_col].mean():.2f}"
        )
        fig_hist.update_layout(height=400)
        st.plotly_chart(fig_hist, use_container_width=True)

# === SEZIONE ADMIN: ANALISI IMPATTO PESI ===
if is_admin_logged_in():
    st.markdown("---")
    st.markdown("### 🔐 Analisi Impatto Pesi (Admin)")
    st.info("Questa sezione è visibile solo agli amministratori")
    
    # Carica i pesi attuali
    try:
        from src.utils.weights_manager import get_dimension_weights, get_indicator_weights
        
        dim_weights = get_dimension_weights()
        
        # === TAB per organizzare i contenuti ===
        admin_tab1, admin_tab2, admin_tab3 = st.tabs([
            "📊 Pesi Configurati", 
            "📈 Impatto sui Dati",
            "🏆 Scuole Più Impattate"
        ])
        
        # === TAB 1: PESI CONFIGURATI ===
        with admin_tab1:
            st.subheader("Pesi delle Dimensioni")
            
            # Tabella pesi dimensioni
            dim_weight_data = []
            dim_labels = {
                'finalita': '🎯 Finalità',
                'obiettivi': '📌 Obiettivi',
                'governance': '🏛️ Governance',
                'didattica': '📚 Didattica',
                'opportunita': '🌟 Opportunità'
            }
            for dim_key, weight in dim_weights.items():
                dim_weight_data.append({
                    'Dimensione': dim_labels.get(dim_key, dim_key),
                    'Peso': f"{weight*100:.0f}%"
                })
            
            df_dim_weights = pd.DataFrame(dim_weight_data)
            st.dataframe(df_dim_weights, hide_index=True, use_container_width=True)
            
            st.markdown("---")
            st.subheader("Pesi degli Indicatori (Sotto-Dimensioni)")
            
            # Mapping nomi indicatori leggibili
            indicator_labels = {
                'finalita': {
                    'attitudini': 'Attitudini',
                    'interessi': 'Interessi',
                    'progetto_vita': 'Progetto di Vita',
                    'transizioni': 'Transizioni Formative',
                    'capacita_orientative': 'Capacità Orientative'
                },
                'obiettivi': {
                    'ridurre_abbandono': 'Ridurre Abbandono',
                    'continuita_territorio': 'Continuità Territorio',
                    'contrastare_neet': 'Contrastare NEET',
                    'lifelong_learning': 'Lifelong Learning'
                },
                'governance': {
                    'coordinamento': 'Coordinamento Servizi',
                    'dialogo': 'Dialogo Docenti-Studenti',
                    'rapporto_genitori': 'Rapporto Scuola-Genitori',
                    'monitoraggio': 'Monitoraggio Azioni',
                    'inclusione': 'Inclusione Fragilità'
                },
                'didattica': {
                    'esperienza_studenti': 'Esperienza Studenti',
                    'laboratoriale': 'Laboratoriale',
                    'flessibilita': 'Flessibilità Spazi/Tempi',
                    'interdisciplinare': 'Interdisciplinare'
                },
                'opportunita': {
                    'culturali': 'Culturali',
                    'laboratoriali': 'Laboratoriali Espressive',
                    'ludiche': 'Ludiche Ricreative',
                    'volontariato': 'Volontariato',
                    'sportive': 'Sportive'
                }
            }
            
            # Mostra indicatori per ogni dimensione
            ind_cols = st.columns(3)
            dims_list = list(dim_weights.keys())
            
            for idx, dim_key in enumerate(dims_list):
                col_idx = idx % 3
                with ind_cols[col_idx]:
                    dim_label = dim_labels.get(dim_key, dim_key)
                    dim_weight_pct = dim_weights.get(dim_key, 0.2) * 100
                    st.markdown(f"**{dim_label} ({dim_weight_pct:.0f}%)**")
                    
                    ind_weights = get_indicator_weights(dim_key)
                    ind_data = []
                    for ind_key, ind_weight in ind_weights.items():
                        ind_label = indicator_labels.get(dim_key, {}).get(ind_key, ind_key)
                        ind_data.append({
                            'Indicatore': ind_label,
                            'Peso': f"{ind_weight*100:.0f}%"
                        })
                    
                    if ind_data:
                        df_ind = pd.DataFrame(ind_data)
                        st.dataframe(df_ind, hide_index=True, use_container_width=True)
                    st.markdown("")
        
        # === TAB 2: IMPATTO SUI DATI ===
        with admin_tab2:
            st.subheader("Confronto Indice IIPO Originale vs Pesato")
            
            # Calcola statistiche
            if 'ptof_idpo' in df.columns and 'weighted_index' in df.columns:
                orig_mean = df['ptof_idpo'].mean()
                weighted_mean = df['weighted_index'].mean()
                diff_mean = weighted_mean - orig_mean
                
                diff_series = df['weighted_index'] - df['ptof_idpo']
                diff_min = diff_series.min()
                diff_max = diff_series.max()
                diff_std = diff_series.std()
                
                # KPI impatto
                impact_cols = st.columns(4)
                with impact_cols[0]:
                    st.metric("Media Originale", f"{orig_mean:.2f}/7")
                with impact_cols[1]:
                    st.metric("Media Pesata", f"{weighted_mean:.2f}/7", f"{diff_mean:+.3f}")
                with impact_cols[2]:
                    st.metric("Diff. Min/Max", f"{diff_min:+.2f} / {diff_max:+.2f}")
                with impact_cols[3]:
                    st.metric("Dev. Std. Diff.", f"{diff_std:.3f}")
                
                st.markdown("")
                
                # Grafico scatter Originale vs Pesato
                st.markdown("#### Scatter Plot: Originale vs Pesato")
                
                fig_scatter = px.scatter(
                    df,
                    x='ptof_idpo',
                    y='weighted_index',
                    hover_data=['denominazione', 'regione', 'tipo_scuola'],
                    labels={
                        'ptof_idpo': 'Indice IIPO Originale',
                        'weighted_index': 'Indice IIPO Pesato'
                    },
                    title="Confronto Indice IIPO Originale vs Pesato",
                    color_discrete_sequence=['#3498db']
                )
                
                # Linea di riferimento (y=x)
                min_val = min(df['ptof_idpo'].min(), df['weighted_index'].min())
                max_val = max(df['ptof_idpo'].max(), df['weighted_index'].max())
                fig_scatter.add_trace(go.Scatter(
                    x=[min_val, max_val],
                    y=[min_val, max_val],
                    mode='lines',
                    name='y=x (nessuna differenza)',
                    line=dict(color='red', dash='dash')
                ))
                
                fig_scatter.update_layout(height=500)
                st.plotly_chart(fig_scatter, use_container_width=True)
                
                st.caption("I punti sopra la linea rossa hanno indice pesato maggiore dell'originale, quelli sotto hanno indice minore.")
                
                # Istogramma delle differenze
                st.markdown("#### Distribuzione delle Differenze")
                fig_diff = px.histogram(
                    diff_series,
                    nbins=30,
                    title="Distribuzione delle differenze (Pesato - Originale)",
                    labels={'value': 'Differenza', 'count': 'N. Scuole'},
                    color_discrete_sequence=['#9b59b6']
                )
                fig_diff.add_vline(x=0, line_dash="dash", line_color="red", annotation_text="Zero")
                fig_diff.update_layout(height=350)
                st.plotly_chart(fig_diff, use_container_width=True)
            else:
                st.warning("Colonne necessarie non disponibili per il confronto")
        
        # === TAB 3: SCUOLE PIÙ IMPATTATE ===
        with admin_tab3:
            st.subheader("Scuole Più Impattate dai Pesi")
            
            if 'ptof_idpo' in df.columns and 'weighted_index' in df.columns:
                # Calcola differenza
                df_impact = df.copy()
                df_impact['diff'] = df_impact['weighted_index'] - df_impact['ptof_idpo']
                
                impact_sub_cols = st.columns(2)
                
                with impact_sub_cols[0]:
                    st.markdown("#### 📈 Top 10 - Maggior Incremento")
                    top_up = df_impact.nlargest(10, 'diff')[['denominazione', 'regione', 'ptof_idpo', 'weighted_index', 'diff']]
                    top_up.columns = ['Scuola', 'Regione', 'Originale', 'Pesato', 'Diff']
                    top_up['Originale'] = top_up['Originale'].apply(lambda x: f"{x:.2f}")
                    top_up['Pesato'] = top_up['Pesato'].apply(lambda x: f"{x:.2f}")
                    top_up['Diff'] = top_up['Diff'].apply(lambda x: f"{x:+.2f}")
                    st.dataframe(top_up, hide_index=True, use_container_width=True)
                
                with impact_sub_cols[1]:
                    st.markdown("#### 📉 Top 10 - Maggior Decremento")
                    top_down = df_impact.nsmallest(10, 'diff')[['denominazione', 'regione', 'ptof_idpo', 'weighted_index', 'diff']]
                    top_down.columns = ['Scuola', 'Regione', 'Originale', 'Pesato', 'Diff']
                    top_down['Originale'] = top_down['Originale'].apply(lambda x: f"{x:.2f}")
                    top_down['Pesato'] = top_down['Pesato'].apply(lambda x: f"{x:.2f}")
                    top_down['Diff'] = top_down['Diff'].apply(lambda x: f"{x:+.2f}")
                    st.dataframe(top_down, hide_index=True, use_container_width=True)
                
                st.markdown("")
                st.info("""
                **Interpretazione:**
                - Le scuole con **incremento positivo** hanno punteggi più alti nelle dimensioni con peso maggiore
                - Le scuole con **decremento** hanno punteggi più alti nelle dimensioni con peso minore
                - Con i pesi attuali, le scuole forti in **Finalità (35%)** e **Governance (25%)** tendono a salire
                """)
            else:
                st.warning("Colonne necessarie non disponibili")
                
    except ImportError as e:
        st.error(f"Errore nel caricamento del modulo pesi: {e}")

# Footer
render_footer()
