# 🗺️ Mappa Italia - Analisi Geografica

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

st.set_page_config(page_title="Mappa Italia", page_icon="🗺️", layout="wide")

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

# Constants
SUMMARY_FILE = 'data/analysis_summary.csv'

LABEL_MAP = {
    'mean_finalita': 'Finalità',
    'mean_obiettivi': 'Obiettivi', 
    'mean_governance': 'Governance',
    'mean_didattica_orientativa': 'Didattica',
    'mean_opportunita': 'Opportunità',
    'ptof_orientamento_maturity_index': 'Indice Robustezza'
}

def get_label(col):
    return LABEL_MAP.get(col, col.replace('_', ' ').title())

# Region to ISO codes for choropleth
REGION_ISO = {
    'Piemonte': 'IT-21', 'Valle d\'Aosta': 'IT-23', 'Lombardia': 'IT-25',
    'Trentino-Alto Adige': 'IT-32', 'Veneto': 'IT-34', 'Friuli Venezia Giulia': 'IT-36',
    'Liguria': 'IT-42', 'Emilia-Romagna': 'IT-45', 'Toscana': 'IT-52',
    'Umbria': 'IT-55', 'Marche': 'IT-57', 'Lazio': 'IT-62',
    'Abruzzo': 'IT-65', 'Molise': 'IT-67', 'Campania': 'IT-72',
    'Puglia': 'IT-75', 'Basilicata': 'IT-77', 'Calabria': 'IT-78',
    'Sicilia': 'IT-82', 'Sardegna': 'IT-88'
}

# Normalizzazione nomi regioni (CSV -> ISO Map)
REGION_NORMALIZATION = {
    'Emilia Romagna': 'Emilia-Romagna',
    'Friuli-Venezia Giulia': 'Friuli Venezia Giulia',
    'Trentino Alto Adige': 'Trentino-Alto Adige',
    'Valle D\'Aosta': 'Valle d\'Aosta',
    'Valle d Aosta': 'Valle d\'Aosta',
}

# Macro-areas (solo Nord e Sud)
MACRO_AREA = {
    'Piemonte': 'Nord', 'Valle d\'Aosta': 'Nord', 'Lombardia': 'Nord',
    'Trentino-Alto Adige': 'Nord', 'Veneto': 'Nord', 'Friuli Venezia Giulia': 'Nord',
    'Liguria': 'Nord', 'Emilia-Romagna': 'Nord',
    'Toscana': 'Nord', 'Umbria': 'Nord', 'Marche': 'Nord',
    'Abruzzo': 'Nord', 'Lazio': 'Sud',
    'Molise': 'Sud', 'Campania': 'Sud', 'Puglia': 'Sud',
    'Basilicata': 'Sud', 'Calabria': 'Sud', 'Sicilia': 'Sud', 'Sardegna': 'Sud'
}

@st.cache_data(ttl=60)
def load_data():
    if os.path.exists(SUMMARY_FILE):
        df = pd.read_csv(SUMMARY_FILE)
        return df
    return pd.DataFrame()

df = load_data()

st.title("🗺️ Analisi Geografica Italia")
st.markdown("Visualizzazione della distribuzione territoriale dell'indice di robustezza dell'orientamento PTOF")

if df.empty:
    st.warning("⚠️ Nessun dato disponibile. Esegui prima il pipeline di analisi.")
    st.stop()

# Normalize region values from analysis_summary only (no external mapping)
def normalize_region(value):
    if pd.isna(value):
        return 'Non Specificato'
    value_str = str(value).strip()
    if value_str in ('', 'ND', 'N/A', 'nan'):
        return 'Non Specificato'
    
    # Applica normalizzazione specifica
    if value_str in REGION_NORMALIZATION:
        return REGION_NORMALIZATION[value_str]
        
    return value_str

if 'regione' in df.columns:
    df['regione'] = df['regione'].apply(normalize_region)
else:
    df['regione'] = 'Non Specificato'

# Standardize numeric columns
numeric_cols = ['ptof_orientamento_maturity_index', 'mean_finalita', 'mean_obiettivi', 
                'mean_governance', 'mean_didattica_orientativa', 'mean_opportunita']
for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

df['macro_area'] = df['regione'].map(MACRO_AREA).fillna('Non Specificato')

# Filter out schools with no maturity index
df_valid = df[df['ptof_orientamento_maturity_index'].notna()].copy()

# === ALERT: CHECK FOR MISSING REGION IN SUMMARY ===
missing_region_rows = df[df['regione'] == 'Non Specificato']
if not missing_region_rows.empty:
    st.error(f"⚠️ **Attenzione: {len(missing_region_rows)} scuole senza regione in analysis_summary.csv**")

    if 'comune' in df.columns:
        missing_comuni = sorted({
            str(comune).upper().strip()
            for comune in missing_region_rows['comune'].dropna().tolist()
            if str(comune).strip()
        })

        if missing_comuni:
            with st.expander(f"📋 Visualizza {len(missing_comuni)} comuni senza regione", expanded=True):
                cols = st.columns(3)
                for i, comune in enumerate(missing_comuni[:15]):
                    with cols[i % 3]:
                        st.code(comune)
                if len(missing_comuni) > 15:
                    st.caption(f"... e altri {len(missing_comuni) - 15} comuni")

    st.info("Aggiorna i metadati rigenerando `data/analysis_summary.csv` dal workflow.")
    st.markdown("---")

st.markdown("---")

# === 1. REGIONAL RANKING ===
st.subheader("🏆 Ranking Regionale")
st.caption("Classifica delle regioni per indice di robustezza medio")

regional_stats = df_valid.groupby('regione').agg({
    'ptof_orientamento_maturity_index': ['mean', 'count', 'std']
}).round(2)
regional_stats.columns = ['Media', 'N. Scuole', 'Dev. Std']
regional_stats = regional_stats.reset_index()
regional_stats.columns = ['Regione', 'Media', 'N. Scuole', 'Dev. Std']
regional_stats = regional_stats[regional_stats['Regione'] != 'Non Specificato']
regional_stats = regional_stats.sort_values('Media', ascending=False)

col1, col2 = st.columns([2, 1])

with col1:
    fig_ranking = px.bar(
        regional_stats.sort_values('Media', ascending=True),
        x='Media', y='Regione', orientation='h',
        color='Media', color_continuous_scale='RdYlGn',
        range_x=[0, 7], range_color=[1, 7],
        title="Indice di Robustezza per Regione",
        text='Media'
    )
    fig_ranking.update_traces(texttemplate='%{text:.2f}', textposition='outside')
    fig_ranking.update_layout(height=500)
    st.plotly_chart(fig_ranking, use_container_width=True)

with col2:
    st.markdown("### 📊 Statistiche Regionali")
    st.dataframe(
        regional_stats.reset_index(drop=True),
        use_container_width=True,
        hide_index=True,
        height=450
    )

# === ANOVA Test for Regional Differences ===
st.markdown("### 🔬 Test ANOVA: Differenze tra Regioni")
st.caption("Verifica statistica se esistono differenze significative nell'indice di robustezza tra le regioni")

try:
    from scipy import stats
    import numpy as np
    
    # Prepare groups for ANOVA (only regions with at least 2 schools)
    region_groups = []
    region_names = []
    for region, group in df_valid.groupby('regione'):
        vals = group['ptof_orientamento_maturity_index'].dropna().values
        if len(vals) >= 2 and region != 'Non Specificato':
            region_groups.append(vals)
            region_names.append(region)
    
    if len(region_groups) >= 2:
        # Perform one-way ANOVA
        f_stat, p_value = stats.f_oneway(*region_groups)
        
        # Calculate eta-squared (effect size)
        # eta² = SS_between / SS_total
        all_values = np.concatenate(region_groups)
        grand_mean = np.mean(all_values)
        
        # SS_between = sum of n_i * (mean_i - grand_mean)²
        ss_between = sum(len(g) * (np.mean(g) - grand_mean)**2 for g in region_groups)
        
        # SS_total = sum of (x_ij - grand_mean)²
        ss_total = sum((x - grand_mean)**2 for x in all_values)
        
        eta_squared = ss_between / ss_total if ss_total > 0 else 0
        
        # Determine significance level and effect size interpretation
        if p_value < 0.001:
            sig_stars = "***"
            sig_text = "Altamente significativo (p < 0.001)"
        elif p_value < 0.01:
            sig_stars = "**"
            sig_text = "Molto significativo (p < 0.01)"
        elif p_value < 0.05:
            sig_stars = "*"
            sig_text = "Significativo (p < 0.05)"
        else:
            sig_stars = ""
            sig_text = "Non significativo (p ≥ 0.05)"
        
        # Effect size interpretation (Cohen's guidelines for eta²)
        if eta_squared >= 0.14:
            effect_text = "Grande"
            effect_stars = "***"
        elif eta_squared >= 0.06:
            effect_text = "Medio"
            effect_stars = "**"
        elif eta_squared >= 0.01:
            effect_text = "Piccolo"
            effect_stars = "*"
        else:
            effect_text = "Trascurabile"
            effect_stars = ""
        
        # Display results in a nice table
        anova_results = {
            'Statistica': ['F-statistic', 'p-value', 'Significatività', 'η² (Eta-squared)', 'Effect Size'],
            'Valore': [
                f"{f_stat:.3f}",
                f"{p_value:.4f}",
                f"{sig_stars} {sig_text}",
                f"{eta_squared:.3f}",
                f"{effect_stars} {effect_text}"
            ]
        }
        
        col_anova1, col_anova2 = st.columns([1, 1])
        
        with col_anova1:
            st.dataframe(
                anova_results,
                use_container_width=True,
                hide_index=True
            )
        
        with col_anova2:
            st.markdown("""
            **Legenda Significatività:**
            - \\* p < 0.05
            - \\*\\* p < 0.01  
            - \\*\\*\\* p < 0.001
            
            **Legenda Effect Size (η²):**
            - \\* Piccolo (0.01 - 0.06)
            - \\*\\* Medio (0.06 - 0.14)
            - \\*\\*\\* Grande (> 0.14)
            """)
        
        # Additional context
        if p_value < 0.05:
            st.success(f"✅ Le differenze tra le {len(region_groups)} regioni sono **statisticamente significative** con un effect size **{effect_text.lower()}**.")
        else:
            st.info(f"ℹ️ Non ci sono differenze statisticamente significative tra le {len(region_groups)} regioni analizzate.")
    else:
        st.warning("Dati insufficienti per il test ANOVA (servono almeno 2 regioni con 2+ scuole ciascuna)")

except ImportError:
    st.warning("Installa scipy per il test ANOVA: `pip install scipy`")
except Exception as e:
    st.error(f"Errore nel calcolo ANOVA: {e}")

st.markdown("---")

# === 2. CHOROPLETH MAP ===
st.subheader("🗺️ Mappa Coropletica")
st.caption("Visualizzazione geografica dell'indice medio per regione")

# Prepare data for map
map_data = regional_stats.copy()
map_data['iso_code'] = map_data['Regione'].map(REGION_ISO)
map_data = map_data[map_data['iso_code'].notna()]

# Region coordinates for maps
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

if len(map_data) > 0:
    # Use scatter_geo for Italy
    
    map_data['lat'] = map_data['Regione'].map(lambda x: REGION_COORDS.get(x, (42.0, 12.5))[0])
    map_data['lon'] = map_data['Regione'].map(lambda x: REGION_COORDS.get(x, (42.0, 12.5))[1])
    
    fig_map = px.scatter_geo(
        map_data,
        lat='lat', lon='lon',
        size='N. Scuole',
        color='Media',
        hover_name='Regione',
        hover_data={'Media': ':.2f', 'N. Scuole': True, 'lat': False, 'lon': False},
        color_continuous_scale='RdYlGn',
        range_color=[1, 7],
        size_max=50,
        title="Distribuzione Geografica Indice Robustezza"
    )
    
    fig_map.update_geos(
        scope='europe',
        center=dict(lat=42.5, lon=12.5),
        projection_scale=5,
        showland=True, landcolor='rgb(243, 243, 243)',
        showocean=True, oceancolor='rgb(204, 229, 255)',
        showcountries=True, countrycolor='rgb(204, 204, 204)',
        showsubunits=True, subunitcolor='rgb(255, 255, 255)'
    )
    
    fig_map.update_layout(height=600, margin=dict(l=0, r=0, t=40, b=0))
    st.plotly_chart(fig_map, use_container_width=True)
else:
    st.info("Dati insufficienti per generare la mappa")

st.markdown("---")

# === 2bis. TOP PERFORMERS MAP ===
st.subheader("🏆 Mappa Scuole più Virtuose")
st.caption("Le scuole con gli indici di robustezza più alti, colorate per tipologia")

if len(df_valid) > 0 and 'ptof_orientamento_maturity_index' in df_valid.columns:
    # Slider to select how many top schools to show
    n_top = st.slider("Numero di scuole da visualizzare", min_value=5, max_value=min(30, len(df_valid)), value=10, step=5)
    
    # Get top N schools by maturity index
    top_schools = df_valid.nlargest(n_top, 'ptof_orientamento_maturity_index').copy()
    
    # Use real coordinates if available, otherwise fallback to region center + jitter
    if 'lat' in top_schools.columns and 'lon' in top_schools.columns:
        # Ensure numeric
        top_schools['lat'] = pd.to_numeric(top_schools['lat'], errors='coerce')
        top_schools['lon'] = pd.to_numeric(top_schools['lon'], errors='coerce')
        
        # Fill missing with region center
        for idx, row in top_schools.iterrows():
            if pd.isna(row['lat']) or pd.isna(row['lon']):
                reg = row.get('regione', '')
                coords = REGION_COORDS.get(reg, (42.0, 12.5))
                # Add jitter for fallback (reduced to 0.05)
                import numpy as np
                top_schools.at[idx, 'lat'] = coords[0] + np.random.uniform(-0.05, 0.05)
                top_schools.at[idx, 'lon'] = coords[1] + np.random.uniform(-0.05, 0.05)
    else:
        # Fallback to region center + jitter
        top_schools['lat'] = top_schools['regione'].map(lambda x: REGION_COORDS.get(x, (42.0, 12.5))[0])
        top_schools['lon'] = top_schools['regione'].map(lambda x: REGION_COORDS.get(x, (42.0, 12.5))[1])
        
        # Add slight random offset to avoid overlap (within same region)
        import numpy as np
        np.random.seed(42)
        # Reduced jitter from 0.5 to 0.1
        top_schools['lat'] = top_schools['lat'] + np.random.uniform(-0.1, 0.1, len(top_schools))
        top_schools['lon'] = top_schools['lon'] + np.random.uniform(-0.1, 0.1, len(top_schools))
    
    # Prepare tipo_scuola for color (take first type if multiple)
    if 'tipo_scuola' in top_schools.columns:
        top_schools['tipo_primario'] = top_schools['tipo_scuola'].apply(
            lambda x: str(x).split(',')[0].strip() if pd.notna(x) else 'Non Specificato'
        )
    else:
        top_schools['tipo_primario'] = 'Non Specificato'
    
    # Create the map
    fig_top = px.scatter_geo(
        top_schools,
        lat='lat', lon='lon',
        color='tipo_primario',
        hover_name='denominazione',
        hover_data={
            'ptof_orientamento_maturity_index': ':.2f',
            'comune': True,
            'regione': True,
            'tipo_primario': True,
            'lat': False, 
            'lon': False
        },
        title=f"🏆 Top {n_top} Scuole per Indice di Robustezza",
        color_discrete_sequence=px.colors.qualitative.Bold
    )
    
    # Use small fixed-size markers
    fig_top.update_traces(marker=dict(size=12, line=dict(width=1, color='white')))
    
    fig_top.update_geos(
        scope='europe',
        center=dict(lat=42.5, lon=12.5),
        projection_scale=5,
        showland=True, landcolor='rgb(243, 243, 243)',
        showocean=True, oceancolor='rgb(204, 229, 255)',
        showcountries=True, countrycolor='rgb(204, 204, 204)',
        showsubunits=True, subunitcolor='rgb(255, 255, 255)'
    )
    
    fig_top.update_layout(
        height=650, 
        margin=dict(l=0, r=0, t=50, b=0),
        legend=dict(
            title="Tipologia Scuola",
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        )
    )
    st.plotly_chart(fig_top, use_container_width=True)
    
    # Show table with top schools
    st.markdown("### 📋 Dettaglio Scuole Top Performers")
    display_cols = ['denominazione', 'comune', 'regione', 'tipo_primario', 'ptof_orientamento_maturity_index']
    display_cols = [c for c in display_cols if c in top_schools.columns]
    top_display = top_schools[display_cols].copy()
    top_display.columns = ['Scuola', 'Comune', 'Regione', 'Tipo', 'Indice']
    top_display = top_display.reset_index(drop=True)
    top_display.index = top_display.index + 1  # Start from 1
    st.dataframe(top_display, use_container_width=True)
else:
    st.info("Dati insufficienti per la mappa delle scuole virtuose")

st.markdown("---")

# === 2b. MAP BY SCHOOL TYPE ===
st.subheader("🏫 Mappa per Tipo di Istituto")
st.caption("Distribuzione geografica per tipologia scolastica")

if 'tipo_scuola' in df_valid.columns and len(map_data) > 0:
    # Get primary type
    def get_primary_type(tipo):
        if pd.isna(tipo):
            return 'Non Specificato'
        if ',' in str(tipo):
            return str(tipo).split(',')[0].strip()
        return str(tipo).strip()
    
    df_valid['tipo_primario'] = df_valid['tipo_scuola'].apply(get_primary_type)
    
    # Type selector
    tipo_options = sorted([t for t in df_valid['tipo_primario'].unique() if t != 'Non Specificato'])
    
    if tipo_options:
        col_sel1, col_sel2 = st.columns([1, 2])
        
        with col_sel1:
            view_mode = st.radio(
                "Visualizzazione",
                ["Tutti i tipi", "Singolo tipo"],
                horizontal=True
            )
        
        with col_sel2:
            if view_mode == "Singolo tipo":
                selected_tipo = st.selectbox("Seleziona Tipologia", tipo_options)
            else:
                selected_tipo = None
        
        # Filter data based on selection
        if selected_tipo:
            df_tipo_map = df_valid[df_valid['tipo_primario'] == selected_tipo].copy()
        else:
            df_tipo_map = df_valid.copy()
        
        # Group by region and type
        if view_mode == "Tutti i tipi":
            # Show all types with different colors
            tipo_region_stats = df_tipo_map.groupby(['regione', 'tipo_primario']).agg({
                'ptof_orientamento_maturity_index': 'mean',
                'school_id': 'count'
            }).reset_index()
            tipo_region_stats.columns = ['Regione', 'Tipo', 'Media', 'N. Scuole']
            tipo_region_stats = tipo_region_stats[tipo_region_stats['Regione'] != 'Non Specificato']
            
            if len(tipo_region_stats) > 0:
                # Add coordinates
                tipo_region_stats['lat'] = tipo_region_stats['Regione'].map(
                    lambda x: REGION_COORDS.get(x, (42.0, 12.5))[0]
                )
                tipo_region_stats['lon'] = tipo_region_stats['Regione'].map(
                    lambda x: REGION_COORDS.get(x, (42.0, 12.5))[1]
                )
                
                # Add slight offset to avoid overlap (reduced to keep within region)
                import numpy as np
                tipo_values = tipo_region_stats['Tipo'].unique()
                # Offset reduced from 0.3/0.2 to 0.08/0.08 (approx 8km instead of 30km)
                tipo_offsets = {t: ((i - len(tipo_values)/2) * 0.08, (i - len(tipo_values)/2) * 0.08) for i, t in enumerate(tipo_values)}
                tipo_region_stats['lat'] = tipo_region_stats.apply(
                    lambda r: r['lat'] + tipo_offsets.get(r['Tipo'], (0, 0))[0], axis=1
                )
                tipo_region_stats['lon'] = tipo_region_stats.apply(
                    lambda r: r['lon'] + tipo_offsets.get(r['Tipo'], (0, 0))[1], axis=1
                )
                
                fig_tipo_map = px.scatter_geo(
                    tipo_region_stats,
                    lat='lat', lon='lon',
                    size='N. Scuole',
                    color='Tipo',
                    hover_name='Regione',
                    hover_data={'Media': ':.2f', 'N. Scuole': True, 'Tipo': True, 'lat': False, 'lon': False},
                    size_max=20,
                    title="Distribuzione Tipologie per Regione"
                )
                
                fig_tipo_map.update_geos(
                    scope='europe',
                    center=dict(lat=42.5, lon=12.5),
                    projection_scale=5,
                    showland=True, landcolor='rgb(243, 243, 243)',
                    showocean=True, oceancolor='rgb(204, 229, 255)',
                    showcountries=True, countrycolor='rgb(204, 204, 204)'
                )
                
                fig_tipo_map.update_layout(height=550, margin=dict(l=0, r=0, t=40, b=0))
                st.plotly_chart(fig_tipo_map, use_container_width=True)
        else:
            # Show single type
            tipo_stats = df_tipo_map.groupby('regione').agg({
                'ptof_orientamento_maturity_index': ['mean', 'count']
            }).round(2)
            tipo_stats.columns = ['Media', 'N. Scuole']
            tipo_stats = tipo_stats.reset_index()
            tipo_stats.columns = ['Regione', 'Media', 'N. Scuole']
            tipo_stats = tipo_stats[tipo_stats['Regione'] != 'Non Specificato']
            
            if len(tipo_stats) > 0:
                tipo_stats['lat'] = tipo_stats['Regione'].map(
                    lambda x: REGION_COORDS.get(x, (42.0, 12.5))[0]
                )
                tipo_stats['lon'] = tipo_stats['Regione'].map(
                    lambda x: REGION_COORDS.get(x, (42.0, 12.5))[1]
                )
                
                fig_tipo_single = px.scatter_geo(
                    tipo_stats,
                    lat='lat', lon='lon',
                    size='N. Scuole',
                    color='Media',
                    hover_name='Regione',
                    hover_data={'Media': ':.2f', 'N. Scuole': True, 'lat': False, 'lon': False},
                    color_continuous_scale='RdYlGn',
                    range_color=[1, 7],
                    size_max=50,
                    title=f"Distribuzione {selected_tipo} per Regione"
                )
                
                fig_tipo_single.update_geos(
                    scope='europe',
                    center=dict(lat=42.5, lon=12.5),
                    projection_scale=5,
                    showland=True, landcolor='rgb(243, 243, 243)',
                    showocean=True, oceancolor='rgb(204, 229, 255)',
                    showcountries=True, countrycolor='rgb(204, 204, 204)'
                )
                
                fig_tipo_single.update_layout(height=550, margin=dict(l=0, r=0, t=40, b=0))
                st.plotly_chart(fig_tipo_single, use_container_width=True)
                
                # Summary stats
                st.markdown(f"**{selected_tipo}**: {df_tipo_map['school_id'].nunique()} scuole in {len(tipo_stats)} regioni | Media: {df_tipo_map['ptof_orientamento_maturity_index'].mean():.2f}")
            else:
                st.info(f"Nessun dato disponibile per {selected_tipo}")
        
        # Bar chart comparison by type
        st.markdown("### 📊 Confronto Indice per Tipologia")
        tipo_comparison = df_valid.groupby('tipo_primario').agg({
            'ptof_orientamento_maturity_index': ['mean', 'std', 'count']
        }).round(2)
        tipo_comparison.columns = ['Media', 'Dev.Std', 'N. Scuole']
        tipo_comparison = tipo_comparison.reset_index()
        tipo_comparison.columns = ['Tipologia', 'Media', 'Dev.Std', 'N. Scuole']
        tipo_comparison = tipo_comparison[tipo_comparison['Tipologia'] != 'Non Specificato']
        tipo_comparison = tipo_comparison.sort_values('Media', ascending=True)
        
        fig_tipo_bar = px.bar(
            tipo_comparison,
            x='Media', y='Tipologia', orientation='h',
            color='Media', color_continuous_scale='RdYlGn',
            range_x=[0, 7], range_color=[1, 7],
            text='N. Scuole',
            title="Indice Medio per Tipologia Scolastica"
        )
        fig_tipo_bar.update_traces(texttemplate='n=%{text}', textposition='outside')
        fig_tipo_bar.update_layout(height=350)
        st.plotly_chart(fig_tipo_bar, use_container_width=True)
    else:
        st.info("Nessuna tipologia scolastica disponibile")
else:
    st.info("Dati tipo scuola non disponibili")

st.markdown("---")

# === 3. NORD vs SUD COMPARISON ===
st.subheader("⚖️ Confronto Nord vs Sud")
st.caption("Analisi statistica delle differenze tra le due macro-aree geografiche")

df_macro = df_valid[df_valid['macro_area'] != 'Non Specificato'].copy()

if len(df_macro) > 5:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Boxplot
        fig_box = px.box(
            df_macro, x='macro_area', y='ptof_orientamento_maturity_index',
            color='macro_area',
            color_discrete_map={'Nord': '#3498db', 'Sud': '#e74c3c'},
            title="Distribuzione Indice per Macro-Area",
            labels={'macro_area': 'Macro-Area', 'ptof_orientamento_maturity_index': 'Indice Robustezza'},
            points='all'
        )
        fig_box.update_layout(showlegend=False, height=450)
        st.plotly_chart(fig_box, use_container_width=True)
    
    with col2:
        # Statistics table
        macro_stats = df_macro.groupby('macro_area')['ptof_orientamento_maturity_index'].agg([
            'count', 'mean', 'std', 'min', 'max'
        ]).round(2)
        macro_stats.columns = ['N', 'Media', 'Dev.Std', 'Min', 'Max']
        macro_stats = macro_stats.reset_index()
        macro_stats.columns = ['Area', 'N', 'Media', 'Dev.Std', 'Min', 'Max']
        
        st.markdown("### 📊 Statistiche per Area")
        st.dataframe(macro_stats, use_container_width=True, hide_index=True)
        
        # Statistical test (if scipy available)
        try:
            from scipy import stats
            # Filter groups with at least 3 samples
            valid_groups = []
            excluded_groups = []
            for name, group in df_macro.groupby('macro_area'):
                values = group['ptof_orientamento_maturity_index'].dropna().values
                if len(values) >= 3:
                    valid_groups.append(values)
                else:
                    excluded_groups.append(name)
            
            if len(valid_groups) >= 2:
                stat, p_val = stats.kruskal(*valid_groups)
                st.markdown("### 🔬 Test Kruskal-Wallis")
                if excluded_groups:
                    st.caption(f"⚠️ Esclusi per dati insufficienti (<3): {', '.join(excluded_groups)}")
                
                st.metric("H-statistic", f"{stat:.2f}")
                st.metric("p-value", f"{p_val:.4f}")
                if p_val < 0.05:
                    st.success("✅ Differenza significativa (p < 0.05)")
                else:
                    st.info("❌ Nessuna differenza significativa")
            else:
                st.info("Dati insufficienti per il test statistico (richiesti almeno 2 gruppi con n>=3)")
        except ImportError:
            st.info("Installa scipy per il test statistico")
else:
    st.info("Dati insufficienti per il confronto macro-aree")

st.markdown("---")

# === 3a. AREA GEOGRAFICA (5 AREE) COMPARISON ===
st.subheader("🌍 Confronto per Area Geografica (5 Aree)")
st.caption("Analisi statistica per Nord Ovest, Nord Est, Centro, Sud, Isole")

if 'area_geografica' in df_valid.columns:
    df_area = df_valid[df_valid['area_geografica'].notna() & (df_valid['area_geografica'] != 'ND')].copy()
    
    if len(df_area) > 5:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Boxplot
            fig_box_area = px.box(
                df_area, x='area_geografica', y='ptof_orientamento_maturity_index',
                color='area_geografica',
                title="Distribuzione Indice per Area Geografica",
                labels={'area_geografica': 'Area', 'ptof_orientamento_maturity_index': 'Indice Robustezza'},
                points='all',
                category_orders={"area_geografica": ["Nord Ovest", "Nord Est", "Centro", "Sud", "Isole"]}
            )
            fig_box_area.update_layout(showlegend=False, height=450)
            st.plotly_chart(fig_box_area, use_container_width=True)
        
        with col2:
            # Statistics table
            area_stats = df_area.groupby('area_geografica')['ptof_orientamento_maturity_index'].agg([
                'count', 'mean', 'std', 'min', 'max'
            ]).round(2)
            area_stats.columns = ['N', 'Media', 'Dev.Std', 'Min', 'Max']
            area_stats = area_stats.reset_index()
            
            st.markdown("### 📊 Statistiche per Area")
            st.dataframe(area_stats, use_container_width=True, hide_index=True)
            
            # Statistical test
            try:
                from scipy import stats
                # Filter groups with at least 3 samples
                valid_groups = []
                excluded_groups = []
                for name, group in df_area.groupby('area_geografica'):
                    values = group['ptof_orientamento_maturity_index'].dropna().values
                    if len(values) >= 3:
                        valid_groups.append(values)
                    else:
                        excluded_groups.append(name)
                
                if len(valid_groups) >= 2:
                    stat, p_val = stats.kruskal(*valid_groups)
                    st.markdown("### 🔬 Test Kruskal-Wallis")
                    if excluded_groups:
                        st.caption(f"⚠️ Esclusi per dati insufficienti (<3): {', '.join(excluded_groups)}")
                    
                    st.metric("H-statistic", f"{stat:.2f}")
                    st.metric("p-value", f"{p_val:.4f}")
                    if p_val < 0.05:
                        st.success("✅ Differenza significativa")
                    else:
                        st.info("❌ Nessuna differenza significativa")
                else:
                    st.info("Dati insufficienti per il test statistico (richiesti almeno 2 gruppi con n>=3)")
            except ImportError:
                st.info("Installa scipy per il test statistico")
    else:
        st.info("Dati insufficienti per il confronto per aree geografiche")
else:
    st.warning("Colonna 'area_geografica' non trovata nel dataset")

st.markdown("---")

# === 3b. METROPOLITANO vs NON METROPOLITANO COMPARISON ===
st.subheader("🏙️ Confronto Metropolitano vs Non Metropolitano")
st.caption("Analisi statistica delle differenze tra scuole in aree metropolitane e non metropolitane")

if 'territorio' in df_valid.columns:
    df_territorio = df_valid[df_valid['territorio'].isin(['Metropolitano', 'Non Metropolitano'])].copy()
    
    if len(df_territorio) > 5:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Boxplot
            fig_box_terr = px.box(
                df_territorio, x='territorio', y='ptof_orientamento_maturity_index',
                color='territorio',
                color_discrete_map={'Metropolitano': '#9b59b6', 'Non Metropolitano': '#27ae60'},
                title="Distribuzione Indice per Territorio",
                labels={'territorio': 'Territorio', 'ptof_orientamento_maturity_index': 'Indice Robustezza'},
                points='all'
            )
            fig_box_terr.update_layout(showlegend=False, height=450)
            st.plotly_chart(fig_box_terr, use_container_width=True)
        
        with col2:
            # Statistics table
            terr_stats = df_territorio.groupby('territorio')['ptof_orientamento_maturity_index'].agg([
                'count', 'mean', 'std', 'min', 'max'
            ]).round(2)
            terr_stats.columns = ['N', 'Media', 'Dev.Std', 'Min', 'Max']
            terr_stats = terr_stats.reset_index()
            terr_stats.columns = ['Territorio', 'N', 'Media', 'Dev.Std', 'Min', 'Max']
            
            st.markdown("### 📊 Statistiche per Territorio")
            st.dataframe(terr_stats, use_container_width=True, hide_index=True)
            
            # Mann-Whitney U Test and Cohen's d
            try:
                from scipy import stats
                import numpy as np
                
                metro = df_territorio[df_territorio['territorio'] == 'Metropolitano']['ptof_orientamento_maturity_index'].dropna().values
                non_metro = df_territorio[df_territorio['territorio'] == 'Non Metropolitano']['ptof_orientamento_maturity_index'].dropna().values
                
                if len(metro) >= 3 and len(non_metro) >= 3:
                    # Mann-Whitney U Test
                    stat_mw, p_val_mw = stats.mannwhitneyu(metro, non_metro, alternative='two-sided')
                    
                    # Cohen's d effect size
                    n1, n2 = len(metro), len(non_metro)
                    mean1, mean2 = np.mean(metro), np.mean(non_metro)
                    std1, std2 = np.std(metro, ddof=1), np.std(non_metro, ddof=1)
                    
                    # Pooled standard deviation
                    pooled_std = np.sqrt(((n1-1)*std1**2 + (n2-1)*std2**2) / (n1 + n2 - 2))
                    cohens_d = (mean1 - mean2) / pooled_std if pooled_std > 0 else 0
                    
                    # Effect size interpretation
                    abs_d = abs(cohens_d)
                    if abs_d >= 0.8:
                        effect_text = "Grande"
                        effect_stars = "***"
                    elif abs_d >= 0.5:
                        effect_text = "Medio"
                        effect_stars = "**"
                    elif abs_d >= 0.2:
                        effect_text = "Piccolo"
                        effect_stars = "*"
                    else:
                        effect_text = "Trascurabile"
                        effect_stars = ""
                    
                    # Direction of effect
                    if cohens_d > 0:
                        direction = "a favore di Metropolitano"
                    elif cohens_d < 0:
                        direction = "a favore di Non Metropolitano"
                    else:
                        direction = ""
                    
                    st.markdown("### 🔬 Test Mann-Whitney U")
                    
                    # Results table
                    test_results = {
                        'Statistica': ['U-statistic', 'p-value', 'Significatività', "Cohen's d", 'Effect Size', 'Direzione'],
                        'Valore': [
                            f"{stat_mw:.1f}",
                            f"{p_val_mw:.4f}",
                            "✅ Significativo" if p_val_mw < 0.05 else "❌ Non significativo",
                            f"{cohens_d:.3f}",
                            f"{effect_stars} {effect_text}",
                            direction if abs_d >= 0.2 else "-"
                        ]
                    }
                    st.dataframe(test_results, use_container_width=True, hide_index=True)
                    
                    # Summary message
                    if p_val_mw < 0.05 and abs_d >= 0.2:
                        st.success(f"✅ Differenza **statisticamente significativa** (p={p_val_mw:.4f}) con effect size **{effect_text.lower()}** ({cohens_d:.2f}) {direction}.")
                    elif p_val_mw < 0.05:
                        st.info(f"ℹ️ Differenza statisticamente significativa (p={p_val_mw:.4f}) ma effect size trascurabile.")
                    else:
                        st.info(f"ℹ️ Nessuna differenza statisticamente significativa tra aree metropolitane e non metropolitane.")
                else:
                    st.warning("Dati insufficienti per il test statistico (servono almeno 3 scuole per gruppo)")
            except ImportError:
                st.info("Installa scipy per il test statistico: `pip install scipy`")
            except Exception as e:
                st.error(f"Errore nel calcolo: {e}")
    else:
        st.info("Dati insufficienti per il confronto territori")
else:
    st.warning("Colonna 'territorio' non presente nei dati")

st.markdown("---")

# === 3c. ANALISI PER REGIONE E TERRITORIO ===
st.subheader("📊 Analisi per Regione e Territorio")
st.caption("Confronto dell'indice di robustezza per regione, suddiviso per area metropolitana e non metropolitana")

if 'territorio' in df_valid.columns:
    df_reg_terr = df_valid[
        (df_valid['regione'] != 'Non Specificato') & 
        (df_valid['territorio'].isin(['Metropolitano', 'Non Metropolitano']))
    ].copy()
    
    if len(df_reg_terr) > 0:
        # Grouped statistics
        reg_terr_stats = df_reg_terr.groupby(['regione', 'territorio']).agg({
            'ptof_orientamento_maturity_index': ['mean', 'count', 'std']
        }).round(2)
        reg_terr_stats.columns = ['Media', 'N', 'Dev.Std']
        reg_terr_stats = reg_terr_stats.reset_index()
        
        # Filter regions with both types
        regions_both = reg_terr_stats.groupby('regione').filter(
            lambda x: len(x['territorio'].unique()) == 2
        )['regione'].unique()
        
        if len(regions_both) > 0:
            st.markdown(f"**{len(regions_both)} regioni** hanno scuole sia metropolitane che non metropolitane:")
            
            # Grouped bar chart
            fig_grouped = px.bar(
                reg_terr_stats[reg_terr_stats['regione'].isin(regions_both)].sort_values(['regione', 'territorio']),
                x='regione', y='Media', color='territorio',
                barmode='group',
                color_discrete_map={'Metropolitano': '#9b59b6', 'Non Metropolitano': '#27ae60'},
                title="Indice Medio per Regione e Territorio",
                labels={'regione': 'Regione', 'Media': 'Indice Medio', 'territorio': 'Territorio'},
                text='N'
            )
            fig_grouped.update_traces(texttemplate='n=%{text}', textposition='outside')
            fig_grouped.update_layout(height=500, xaxis_tickangle=-45)
            st.plotly_chart(fig_grouped, use_container_width=True)
            
            # Calculate effect sizes per region
            st.markdown("### 🔬 Effect Size per Regione")
            st.caption("Cohen's d calcolato per ogni regione con almeno 2 scuole per territorio")
            
            try:
                from scipy import stats
                import numpy as np
                
                effect_data = []
                for region in regions_both:
                    metro_vals = df_reg_terr[(df_reg_terr['regione'] == region) & 
                                              (df_reg_terr['territorio'] == 'Metropolitano')]['ptof_orientamento_maturity_index'].dropna().values
                    non_metro_vals = df_reg_terr[(df_reg_terr['regione'] == region) & 
                                                   (df_reg_terr['territorio'] == 'Non Metropolitano')]['ptof_orientamento_maturity_index'].dropna().values
                    
                    if len(metro_vals) >= 2 and len(non_metro_vals) >= 2:
                        n1, n2 = len(metro_vals), len(non_metro_vals)
                        mean1, mean2 = np.mean(metro_vals), np.mean(non_metro_vals)
                        std1, std2 = np.std(metro_vals, ddof=1), np.std(non_metro_vals, ddof=1)
                        
                        pooled_std = np.sqrt(((n1-1)*std1**2 + (n2-1)*std2**2) / (n1 + n2 - 2))
                        d = (mean1 - mean2) / pooled_std if pooled_std > 0 else 0
                        
                        # Mann-Whitney test
                        try:
                            _, p_val = stats.mannwhitneyu(metro_vals, non_metro_vals, alternative='two-sided')
                        except:
                            p_val = 1.0
                        
                        abs_d = abs(d)
                        if abs_d >= 0.8:
                            effect_text = "Grande ***"
                        elif abs_d >= 0.5:
                            effect_text = "Medio **"
                        elif abs_d >= 0.2:
                            effect_text = "Piccolo *"
                        else:
                            effect_text = "Trascurabile"
                        
                        direction = "→ Metropolitano" if d > 0 else "→ Non Metropolitano" if d < 0 else "-"
                        
                        effect_data.append({
                            'Regione': region,
                            'Metro (n)': n1,
                            'Non Metro (n)': n2,
                            'Media Metro': f"{mean1:.2f}",
                            'Media Non Metro': f"{mean2:.2f}",
                            "Cohen's d": f"{d:.2f}",
                            'Effect Size': effect_text,
                            'Direzione': direction,
                            'p-value': f"{p_val:.3f}" if p_val >= 0.001 else "<0.001"
                        })
                
                if effect_data:
                    effect_df = pd.DataFrame(effect_data)
                    # Sort by absolute effect size
                    effect_df['abs_d'] = effect_df["Cohen's d"].astype(float).abs()
                    effect_df = effect_df.sort_values('abs_d', ascending=False).drop('abs_d', axis=1)
                    
                    st.dataframe(effect_df, use_container_width=True, hide_index=True)
                    
                    # Summary
                    significant_regions = [row for row in effect_data if float(row['p-value'].replace('<', '')) < 0.05]
                    if significant_regions:
                        st.success(f"✅ {len(significant_regions)} regioni mostrano differenze significative (p<0.05) tra aree metropolitane e non metropolitane.")
                    else:
                        st.info("ℹ️ Nessuna regione mostra differenze statisticamente significative.")
                else:
                    st.info("Dati insufficienti per calcolare effect size per regione")
            except Exception as e:
                st.error(f"Errore nel calcolo effect size: {e}")
        else:
            st.info("Nessuna regione ha sia scuole metropolitane che non metropolitane")
        
        # Full table
        with st.expander("📋 Tabella completa per Regione e Territorio"):
            st.dataframe(reg_terr_stats, use_container_width=True, hide_index=True)
    else:
        st.info("Dati insufficienti per l'analisi per regione e territorio")
else:
    st.warning("Colonna 'territorio' non presente nei dati")

st.markdown("---")

# === 4. GAP ANALYSIS ===
st.subheader("📉 Gap Analysis per Dimensione")
st.caption("Differenza tra punteggio massimo e minimo per ciascuna dimensione, diviso per area geografica")

dim_cols = ['mean_finalita', 'mean_obiettivi', 'mean_governance', 'mean_didattica_orientativa', 'mean_opportunita']

if all(c in df_valid.columns for c in dim_cols) and 'area_geografica' in df_valid.columns:
    gap_data = []
    
    for area in df_valid['area_geografica'].dropna().unique():
        df_area = df_valid[df_valid['area_geografica'] == area]
        for dim in dim_cols:
            vals = df_area[dim].dropna()
            if len(vals) > 0:
                gap_data.append({
                    'Area': area,
                    'Dimensione': get_label(dim),
                    'Min': vals.min(),
                    'Max': vals.max(),
                    'Gap': vals.max() - vals.min(),
                    'Media': vals.mean()
                })
    
    if gap_data:
        gap_df = pd.DataFrame(gap_data)
        
        fig_gap = px.bar(
            gap_df, x='Dimensione', y='Gap', color='Area',
            barmode='group',
            title="Gap (Max - Min) per Dimensione e Area Geografica",
            labels={'Gap': 'Ampiezza Gap'},
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig_gap.update_layout(height=450)
        st.plotly_chart(fig_gap, use_container_width=True)
        
        # Gap summary table
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 📊 Gap Maggiori")
            top_gaps = gap_df.nlargest(5, 'Gap')[['Area', 'Dimensione', 'Gap', 'Min', 'Max']]
            st.dataframe(top_gaps, use_container_width=True, hide_index=True)
        
        with col2:
            st.markdown("### 📊 Gap Minori")
            bottom_gaps = gap_df.nsmallest(5, 'Gap')[['Area', 'Dimensione', 'Gap', 'Min', 'Max']]
            st.dataframe(bottom_gaps, use_container_width=True, hide_index=True)
else:
    st.info("Dati insufficienti per l'analisi dei gap")

st.markdown("---")

# === 5. AREA GEOGRAFICA RADAR ===
st.subheader("🎯 Profilo per Area Geografica")
st.caption("Confronto del profilo medio delle 5 dimensioni per area geografica")

if all(c in df_valid.columns for c in dim_cols) and 'area_geografica' in df_valid.columns:
    area_profiles = df_valid.groupby('area_geografica')[dim_cols].mean().reset_index()
    
    if len(area_profiles) > 0:
        fig_radar = go.Figure()
        
        colors = {'Nord': '#3498db', 'Sud': '#e74c3c'}
        
        for _, row in area_profiles.iterrows():
            area = row['area_geografica']
            values = [row[c] for c in dim_cols]
            values.append(values[0])  # Close the radar
            
            labels = [get_label(c) for c in dim_cols]
            labels.append(labels[0])
            
            fig_radar.add_trace(go.Scatterpolar(
                r=values,
                theta=labels,
                fill='toself',
                name=area,
                line_color=colors.get(area, '#95a5a6'),
                opacity=0.7
            ))
        
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 7])),
            showlegend=True,
            title="Confronto Dimensioni per Area Geografica",
            height=500
        )
        
        st.plotly_chart(fig_radar, use_container_width=True)
else:
    st.info("Dati insufficienti per il radar chart")

# Footer
st.markdown("---")
st.caption("🗺️ Mappa Italia - Dashboard PTOF | Analisi geografica della robustezza dell'orientamento PTOF delle scuole italiane")
