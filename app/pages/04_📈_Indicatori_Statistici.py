# � Indicatori Statistici - Test e KPI dettagliati

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import os
from scipy import stats
from app.data_utils import get_label, LABEL_MAP

# Funzioni per test statistici
def chi2_test_presence(df, group_col, presence_col):
    """Test Chi-quadrato per la presenza della sezione dedicata tra gruppi."""
    try:
        contingency = pd.crosstab(df[group_col], df[presence_col])
        if contingency.shape[1] < 2 or contingency.shape[0] < 2:
            return None, None, None
        chi2, p_value, dof, expected = stats.chi2_contingency(contingency)
        # Cramér's V (effect size)
        n = contingency.sum().sum()
        min_dim = min(contingency.shape[0] - 1, contingency.shape[1] - 1)
        cramers_v = np.sqrt(chi2 / (n * min_dim)) if min_dim > 0 else 0
        return p_value, cramers_v, chi2
    except:
        return None, None, None

def kruskal_test_scores(df, group_col, score_col):
    """Test Kruskal-Wallis per confrontare i punteggi tra gruppi."""
    try:
        groups = [group[score_col].dropna().values for name, group in df.groupby(group_col)]
        groups = [g for g in groups if len(g) >= 2]
        if len(groups) < 2:
            return None, None
        stat, p_value = stats.kruskal(*groups)
        # Eta-squared (effect size) approssimato
        n = sum(len(g) for g in groups)
        eta_sq = (stat - len(groups) + 1) / (n - len(groups)) if n > len(groups) else 0
        eta_sq = max(0, min(1, eta_sq))  # Clamp 0-1
        return p_value, eta_sq
    except:
        return None, None

def interpret_effect_size(value, test_type='cramers_v'):
    """Interpreta l'effect size."""
    if value is None:
        return "N/D", "gray"
    if test_type == 'cramers_v':
        if value < 0.1:
            return "Trascurabile", "gray"
        elif value < 0.3:
            return "Piccolo", "orange"
        elif value < 0.5:
            return "Medio", "blue"
        else:
            return "Grande", "green"
    else:  # eta_squared
        if value < 0.01:
            return "Trascurabile", "gray"
        elif value < 0.06:
            return "Piccolo", "orange"
        elif value < 0.14:
            return "Medio", "blue"
        else:
            return "Grande", "green"

def format_significance(p_value):
    """Formatta la significatività."""
    if p_value is None:
        return "N/D", "gray"
    if p_value < 0.001:
        return "p < 0.001 ***", "green"
    elif p_value < 0.01:
        return f"p = {p_value:.3f} **", "green"
    elif p_value < 0.05:
        return f"p = {p_value:.3f} *", "orange"
    else:
        return f"p = {p_value:.3f} (n.s.)", "gray"

st.set_page_config(page_title="KPI Avanzati", page_icon="📊", layout="wide")

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
    .kpi-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    .outlier-high { background-color: #d4edda !important; border-left-color: #28a745 !important; }
    .outlier-low { background-color: #f8d7da !important; border-left-color: #dc3545 !important; }
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
    'ptof_orientamento_maturity_index': 'Indice RO',
    'partnership_count': 'N. Partnership'
}

def get_label(col):
    return LABEL_MAP.get(col, col.replace('_', ' ').title())

@st.cache_data(ttl=60)
def load_data():
    if os.path.exists(SUMMARY_FILE):
        df = pd.read_csv(SUMMARY_FILE)
        return df
    return pd.DataFrame()

df = load_data()

st.title("📊 KPI Avanzati e Statistiche")
st.markdown("Analisi approfondita con indicatori avanzati, outliers e insight statistici")

with st.expander("ℹ️ Cosa sono i KPI?"):
    st.markdown("""
    **KPI** sta per **Key Performance Indicators** (Indicatori Chiave di Prestazione). 
    In questa dashboard, rappresentano le metriche fondamentali per valutare la qualità dell'orientamento nei PTOF analizzati.
    
    Utilizziamo questi indicatori per:
    - Monitorare l'andamento generale (es. punteggi medi).
    - Identificare eccellenze o criticità (outliers).
    - Confrontare le performance tra diverse categorie (regioni, tipi di scuola).
    """)

if df.empty:
    st.warning("⚠️ Nessun dato disponibile. Esegui prima il pipeline di analisi.")
    st.stop()

# Standardize numeric columns
numeric_cols = ['ptof_orientamento_maturity_index', 'mean_finalita', 'mean_obiettivi', 
                'mean_governance', 'mean_didattica_orientativa', 'mean_opportunita',
                'partnership_count', 'activities_count']
for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

dim_cols = ['mean_finalita', 'mean_obiettivi', 'mean_governance', 'mean_didattica_orientativa', 'mean_opportunita']

# Filter valid data
df_valid = df[df['ptof_orientamento_maturity_index'].notna()].copy()

if len(df_valid) == 0:
    st.warning("⚠️ Nessuna scuola con Indice RO valido.")
    st.stop()

st.markdown("---")

# === 1. EXTENDED KPI DASHBOARD ===
st.subheader("📈 Dashboard KPI Estesa")
st.caption("Indicatori chiave con statistiche avanzate")

# Row 1: Main metrics
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("🏫 Totale Scuole", len(df_valid))

with col2:
    mean_idx = df_valid['ptof_orientamento_maturity_index'].mean()
    st.metric("📊 Media Indice RO", f"{mean_idx:.2f}", help="Indice di Robustezza dell'Orientamento")

with col3:
    median_idx = df_valid['ptof_orientamento_maturity_index'].median()
    st.metric("📍 Mediana", f"{median_idx:.2f}")

with col4:
    std_idx = df_valid['ptof_orientamento_maturity_index'].std()
    st.metric("📐 Dev. Standard", f"{std_idx:.2f}")

with col5:
    cv = (std_idx / mean_idx * 100) if mean_idx > 0 else 0
    st.metric("📉 Coeff. Variazione", f"{cv:.1f}%")

# Row 2: Distribution metrics
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    q1 = df_valid['ptof_orientamento_maturity_index'].quantile(0.25)
    st.metric("Q1 (25°)", f"{q1:.2f}")

with col2:
    q3 = df_valid['ptof_orientamento_maturity_index'].quantile(0.75)
    st.metric("Q3 (75°)", f"{q3:.2f}")

with col3:
    iqr = q3 - q1
    st.metric("IQR", f"{iqr:.2f}")

with col4:
    min_val = df_valid['ptof_orientamento_maturity_index'].min()
    st.metric("Min", f"{min_val:.2f}")

with col5:
    max_val = df_valid['ptof_orientamento_maturity_index'].max()
    st.metric("Max", f"{max_val:.2f}")

# Row 3: Coverage and completeness
st.markdown("### 📋 Metriche di Copertura")
col1, col2, col3, col4 = st.columns(4)

with col1:
    if 'has_sezione_dedicata' in df_valid.columns:
        sez_pct = df_valid['has_sezione_dedicata'].sum() / len(df_valid) * 100
        st.metric("% Sez. Dedicata", f"{sez_pct:.0f}%")
    else:
        st.metric("% Sez. Dedicata", "N/D")

with col2:
    if 'partnership_count' in df_valid.columns:
        has_partner = (df_valid['partnership_count'] > 0).sum() / len(df_valid) * 100
        st.metric("% Con Partnership", f"{has_partner:.0f}%")
    else:
        st.metric("% Con Partnership", "N/D")

with col3:
    # Schools with score > 4 (above middle)
    above_mid = (df_valid['ptof_orientamento_maturity_index'] > 4).sum() / len(df_valid) * 100
    st.metric("% Sopra Sufficienza", f"{above_mid:.0f}%")

with col4:
    # Excellence rate (score >= 5)
    excellence = (df_valid['ptof_orientamento_maturity_index'] >= 5).sum() / len(df_valid) * 100
    st.metric("% Eccellenza (≥5)", f"{excellence:.0f}%")

st.info("""
💡 **A cosa serve**: Fornisce una panoramica sintetica delle statistiche principali sull'Indice di Robustezza dell'Orientamento (RO) delle scuole analizzate.

🔍 **Cosa rileva**: Media, mediana, deviazione standard e coefficiente di variazione descrivono la distribuzione centrale e la dispersione dei punteggi. I quartili (Q1, Q3) e l'IQR mostrano come si distribuisce il 50% centrale delle scuole. Le metriche di copertura indicano quante scuole hanno elementi chiave come sezione dedicata o partnership.

🎯 **Implicazioni**: Un coefficiente di variazione alto indica forte eterogeneità tra scuole. Una bassa percentuale di "Eccellenza" suggerisce ampio margine di miglioramento. Usa questi dati per contestualizzare le analisi successive.
""")

st.markdown("---")

# === 2. OUTLIER DETECTION ===
st.subheader("🔍 Rilevamento Outlier")
st.caption("Identificazione di scuole con punteggi anomali (eccellenti o critici)")

# Calculate IQR-based outliers
q1 = df_valid['ptof_orientamento_maturity_index'].quantile(0.25)
q3 = df_valid['ptof_orientamento_maturity_index'].quantile(0.75)
iqr = q3 - q1
lower_bound = q1 - 1.5 * iqr
upper_bound = q3 + 1.5 * iqr

df_valid['outlier_type'] = 'Normale'
df_valid.loc[df_valid['ptof_orientamento_maturity_index'] > upper_bound, 'outlier_type'] = '🌟 Eccellente'
df_valid.loc[df_valid['ptof_orientamento_maturity_index'] < lower_bound, 'outlier_type'] = '⚠️ Critico'

# Outlier statistics
outlier_stats = df_valid['outlier_type'].value_counts()

col1, col2, col3 = st.columns(3)

with col1:
    n_excellent = outlier_stats.get('🌟 Eccellente', 0)
    st.metric("🌟 Outlier Eccellenti", n_excellent, 
              help=f"Scuole con indice > {upper_bound:.2f}")

with col2:
    n_normal = outlier_stats.get('Normale', 0)
    st.metric("✅ Nella Norma", n_normal)

with col3:
    n_critical = outlier_stats.get('⚠️ Critico', 0)
    st.metric("⚠️ Outlier Critici", n_critical,
              help=f"Scuole con indice < {lower_bound:.2f}")

# Visualization
fig_outlier = px.box(
    df_valid, y='ptof_orientamento_maturity_index',
    points='all',
    color='outlier_type',
    color_discrete_map={
        '🌟 Eccellente': '#28a745',
        'Normale': '#3498db',
        '⚠️ Critico': '#dc3545'
    },
    title="Distribuzione con Outlier Evidenziati",
    hover_data=['denominazione', 'tipo_scuola']
)
fig_outlier.update_layout(height=400)
st.plotly_chart(fig_outlier, use_container_width=True)

# Show outlier details
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🌟 Scuole Eccellenti (Outlier Positivi)")
    excellent_df = df_valid[df_valid['outlier_type'] == '🌟 Eccellente'][
        ['denominazione', 'tipo_scuola', 'area_geografica', 'ptof_orientamento_maturity_index']
    ].copy()
    if len(excellent_df) > 0:
        excellent_df.columns = ['Scuola', 'Tipo', 'Area', 'Indice']
        excellent_df = excellent_df.sort_values('Indice', ascending=False)
        st.dataframe(excellent_df, use_container_width=True, hide_index=True)
    else:
        st.info("Nessun outlier eccellente rilevato")

with col2:
    st.markdown("### ⚠️ Scuole Critiche (Outlier Negativi)")
    critical_df = df_valid[df_valid['outlier_type'] == '⚠️ Critico'][
        ['denominazione', 'tipo_scuola', 'area_geografica', 'ptof_orientamento_maturity_index']
    ].copy()
    if len(critical_df) > 0:
        critical_df.columns = ['Scuola', 'Tipo', 'Area', 'Indice']
        critical_df = critical_df.sort_values('Indice', ascending=True)
        st.dataframe(critical_df, use_container_width=True, hide_index=True)
    else:
        st.info("Nessun outlier critico rilevato")

st.info("""
💡 **A cosa serve**: Identifica le scuole con punteggi "anomali" rispetto alla distribuzione generale, sia in positivo (eccellenti) che in negativo (critici).

🔍 **Cosa rileva**: Usando il metodo IQR (Interquartile Range), classifica come "outlier eccellente" chi supera Q3+1.5×IQR e come "outlier critico" chi scende sotto Q1-1.5×IQR. Il box plot visualizza la distribuzione con i punti colorati per categoria.

🎯 **Implicazioni**: Le scuole eccellenti sono potenziali modelli da studiare e replicare. Le scuole critiche potrebbero necessitare di interventi prioritari. Se non ci sono outlier, la distribuzione è omogenea.
""")

st.markdown("---")

# === 3. DISTRIBUTION ANALYSIS ===
st.subheader("📉 Analisi Distribuzione")
st.caption("Visualizzazione della distribuzione dei punteggi")

col1, col2 = st.columns(2)

with col1:
    # Histogram with KDE
    fig_hist = px.histogram(
        df_valid, x='ptof_orientamento_maturity_index',
        nbins=20, marginal='box',
        color_discrete_sequence=['#3498db'],
        title="Distribuzione Indice RO"
    )
    fig_hist.update_layout(height=400)
    st.plotly_chart(fig_hist, use_container_width=True)

with col2:
    # Dimension distribution
    if all(c in df_valid.columns for c in dim_cols):
        dim_data = []
        for c in dim_cols:
            for val in df_valid[c].dropna():
                dim_data.append({'Dimensione': get_label(c), 'Punteggio': val})
        
        dim_df = pd.DataFrame(dim_data)
        
        fig_violin = px.violin(
            dim_df, x='Dimensione', y='Punteggio',
            box=True, points='outliers',
            color='Dimensione',
            title="Distribuzione per Dimensione"
        )
        fig_violin.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig_violin, use_container_width=True)

st.info("""
💡 **A cosa serve**: Mostra la forma della distribuzione dei punteggi, evidenziando concentrazioni e code.

🔍 **Cosa rileva**: L'istogramma a sinistra mostra quante scuole cadono in ogni fascia di punteggio. Il violin plot a destra confronta la distribuzione di ciascuna delle 5 dimensioni: la larghezza indica la densità, il box interno mostra mediana e quartili.

🎯 **Implicazioni**: Una distribuzione bimodale (due picchi) suggerisce gruppi distinti di scuole. Dimensioni con distribuzioni più strette indicano omogeneità; quelle più ampie indicano forte variabilità.
""")

st.markdown("---")

# === 4. REGRESSION SUMMARY ===
st.subheader("📈 Analisi Regressione")
st.caption("Identificazione dei migliori predittori dell'Indice RO (Robustezza Orientamento)")

try:
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import StandardScaler
    
    if all(c in df_valid.columns for c in dim_cols):
        # Prepare data
        X = df_valid[dim_cols].dropna()
        y = df_valid.loc[X.index, 'ptof_orientamento_maturity_index']
        
        if len(X) >= 10:
            # Fit model
            model = LinearRegression()
            model.fit(X, y)
            
            # Feature importance
            coef_df = pd.DataFrame({
                'Dimensione': [get_label(c) for c in dim_cols],
                'Coefficiente': model.coef_,
                'Importanza Relativa': np.abs(model.coef_) / np.abs(model.coef_).sum() * 100
            }).sort_values('Importanza Relativa', ascending=False)
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                fig_coef = px.bar(
                    coef_df.sort_values('Importanza Relativa', ascending=True),
                    x='Importanza Relativa', y='Dimensione',
                    orientation='h',
                    color='Importanza Relativa',
                    color_continuous_scale='Blues',
                    title="Importanza Relativa delle Dimensioni",
                    text='Importanza Relativa'
                )
                fig_coef.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig_coef.update_layout(height=350)
                st.plotly_chart(fig_coef, use_container_width=True)
            
            with col2:
                st.markdown("### 📊 Coefficienti")
                st.dataframe(
                    coef_df[['Dimensione', 'Coefficiente']].round(3),
                    use_container_width=True,
                    hide_index=True
                )
                
                r2 = model.score(X, y)
                st.metric("R² Score", f"{r2:.3f}", 
                         help="Quota di varianza spiegata dal modello")
        else:
            st.info("Servono almeno 10 scuole per l'analisi di regressione")
    else:
        st.warning("Colonne dimensioni non disponibili")
        
except ImportError:
    st.warning("Installa scikit-learn per l'analisi di regressione: pip install scikit-learn")

st.info("""
💡 **A cosa serve**: Identifica quali delle 5 dimensioni contribuiscono maggiormente all'Indice RO complessivo.

🔍 **Cosa rileva**: Un modello di regressione lineare calcola l'importanza relativa di ciascuna dimensione. I coefficienti indicano l'impatto: valori alti significano che quella dimensione "pesa" di più. L'R² indica quanto il modello spiega la variabilità totale.

🎯 **Implicazioni**: Se una dimensione ha alta importanza, migliorarla avrà forte impatto sull'indice complessivo. Dimensioni con bassa importanza potrebbero essere meno prioritarie negli interventi di miglioramento.
""")

st.markdown("---")

# === 5. SWOT PER TIPOLOGIA ===
st.subheader("💡 Analisi SWOT per Tipologia")
st.caption("Punti di forza e debolezza per ciascuna tipologia scolastica")

if 'tipo_scuola' in df_valid.columns and all(c in df_valid.columns for c in dim_cols):
    # Get primary type
    def get_primary_type(tipo):
        if pd.isna(tipo):
            return 'Non Specificato'
        if ',' in str(tipo):
            return str(tipo).split(',')[0].strip()
        return str(tipo).strip()
    
    df_valid['tipo_primario'] = df_valid['tipo_scuola'].apply(get_primary_type)
    
    # Calculate means by type
    tipo_means = df_valid.groupby('tipo_primario')[dim_cols].mean()
    
    # Overall means
    overall_means = df_valid[dim_cols].mean()
    
    # SWOT analysis
    tipi = [t for t in tipo_means.index if t != 'Non Specificato']
    
    if len(tipi) > 0:
        selected_tipo = st.selectbox("Seleziona Tipologia", tipi)
        
        if selected_tipo:
            tipo_vals = tipo_means.loc[selected_tipo]
            
            strengths = []
            weaknesses = []
            
            for dim in dim_cols:
                diff = tipo_vals[dim] - overall_means[dim]
                label = get_label(dim)
                
                if diff > 0.3:
                    strengths.append((label, diff, tipo_vals[dim]))
                elif diff < -0.3:
                    weaknesses.append((label, diff, tipo_vals[dim]))
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### 💪 Punti di Forza")
                if strengths:
                    for label, diff, val in sorted(strengths, key=lambda x: -x[1]):
                        st.success(f"**{label}**: {val:.2f} (+{diff:.2f} vs media)")
                else:
                    st.info("Nessun punto di forza significativo rispetto alla media")
            
            with col2:
                st.markdown("### ⚠️ Aree di Miglioramento")
                if weaknesses:
                    for label, diff, val in sorted(weaknesses, key=lambda x: x[1]):
                        st.error(f"**{label}**: {val:.2f} ({diff:.2f} vs media)")
                else:
                    st.info("Nessuna debolezza significativa rispetto alla media")
            
            # Radar comparison
            fig_swot = go.Figure()
            
            # Overall average
            avg_vals = [overall_means[c] for c in dim_cols]
            avg_vals.append(avg_vals[0])
            labels = [get_label(c) for c in dim_cols]
            labels.append(labels[0])
            
            fig_swot.add_trace(go.Scatterpolar(
                r=avg_vals, theta=labels,
                fill='toself', name='Media Generale',
                line_color='gray', opacity=0.5
            ))
            
            # Selected type
            tipo_vls = [tipo_vals[c] for c in dim_cols]
            tipo_vls.append(tipo_vls[0])
            
            fig_swot.add_trace(go.Scatterpolar(
                r=tipo_vls, theta=labels,
                fill='toself', name=selected_tipo,
                line_color='#3498db', opacity=0.7
            ))
            
            fig_swot.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 7])),
                title=f"Profilo {selected_tipo} vs Media Generale",
                height=450
            )
            
            st.plotly_chart(fig_swot, use_container_width=True)
    else:
        st.info("Dati insufficienti per l'analisi SWOT")
else:
    st.warning("Dati tipologia scuola non disponibili")

st.info("""
💡 **A cosa serve**: Analizza punti di forza e debolezza di ciascuna tipologia scolastica (Licei, Tecnici, ecc.) rispetto alla media generale.

🔍 **Cosa rileva**: Per la tipologia selezionata, confronta ogni dimensione con la media nazionale. Differenze >+0.3 sono "Punti di Forza", <-0.3 sono "Aree di Miglioramento". Il radar sovrappone il profilo della tipologia (blu) alla media generale (grigio).

🎯 **Implicazioni**: Ogni tipologia ha caratteristiche distintive. I Licei potrebbero eccellere in una dimensione dove i Tecnici sono più deboli, e viceversa. Usa queste informazioni per interventi mirati per tipologia.
""")

st.markdown("---")

# === 5.5 SEZIONE DEDICATA ANALYSIS ===
st.subheader("📑 Analisi Sezione Dedicata")
st.caption("Approfondimento sulla presenza e qualità della sezione dedicata all'orientamento")

if 'has_sezione_dedicata' in df_valid.columns and '2_1_score' in df_valid.columns:
    # Ensure numeric
    df_valid['has_sezione_dedicata'] = pd.to_numeric(df_valid['has_sezione_dedicata'], errors='coerce').fillna(0)
    df_valid['2_1_score'] = pd.to_numeric(df_valid['2_1_score'], errors='coerce').fillna(0)

    # === SEZIONE 1: PER REGIONE ===
    st.markdown("### 🌍 Analisi per Regione")
    
    if 'regione' in df_valid.columns:
        col_reg1, col_reg2 = st.columns(2)
        
        with col_reg1:
            st.markdown("#### 📊 Presenza Sezione")
            reg_stats = df_valid.groupby('regione')['has_sezione_dedicata'].agg(['count', 'sum', 'mean']).reset_index()
            reg_stats.columns = ['Regione', 'Totale', 'Con Sezione', 'Percentuale']
            reg_stats['Percentuale'] = reg_stats['Percentuale'] * 100
            reg_stats = reg_stats.sort_values('Percentuale', ascending=False)

            fig_reg_pres = px.bar(
                reg_stats, x='Regione', y='Percentuale',
                text=reg_stats['Percentuale'].apply(lambda x: f'{x:.1f}%'),
                title="Percentuale Scuole con Sezione Dedicata per Regione",
                color='Percentuale', color_continuous_scale='Greens'
            )
            fig_reg_pres.update_layout(yaxis_title="% con Sezione", xaxis_title="")
            st.plotly_chart(fig_reg_pres, use_container_width=True)
            
            # Test statistico per presenza
            p_val_reg_pres, cramers_v_reg, _ = chi2_test_presence(df_valid, 'regione', 'has_sezione_dedicata')
            sig_text, sig_color = format_significance(p_val_reg_pres)
            eff_text, eff_color = interpret_effect_size(cramers_v_reg, 'cramers_v')
            st.markdown(f"**📈 Significatività (χ²):** :{sig_color}[{sig_text}]")
            if cramers_v_reg is not None:
                st.markdown(f"**📏 Effect Size (Cramér's V):** :{eff_color}[{cramers_v_reg:.3f} - {eff_text}]")
        
        with col_reg2:
            st.markdown("#### ⭐ Punteggio Medio")
            df_with_sec = df_valid[df_valid['has_sezione_dedicata'] == 1]
            
            if not df_with_sec.empty:
                score_reg = df_with_sec.groupby('regione')['2_1_score'].mean().reset_index()
                score_reg = score_reg.sort_values('2_1_score', ascending=False)
                
                fig_score_reg = px.bar(
                    score_reg, x='regione', y='2_1_score',
                    text=score_reg['2_1_score'].apply(lambda x: f'{x:.2f}'),
                    title="Punteggio Medio per Regione (solo scuole con sezione)",
                    color='2_1_score', color_continuous_scale='Viridis',
                    range_y=[0, 7]
                )
                fig_score_reg.update_layout(yaxis_title="Punteggio Medio (1-7)", xaxis_title="")
                st.plotly_chart(fig_score_reg, use_container_width=True)
                
                # Test statistico per punteggi
                p_val_reg_score, eta_sq_reg = kruskal_test_scores(df_with_sec, 'regione', '2_1_score')
                sig_text, sig_color = format_significance(p_val_reg_score)
                eff_text, eff_color = interpret_effect_size(eta_sq_reg, 'eta_squared')
                st.markdown(f"**📈 Significatività (Kruskal-Wallis):** :{sig_color}[{sig_text}]")
                if eta_sq_reg is not None:
                    st.markdown(f"**📏 Effect Size (η²):** :{eff_color}[{eta_sq_reg:.3f} - {eff_text}]")
            else:
                st.info("Nessuna scuola con sezione dedicata trovata")
    else:
        st.info("Dati 'regione' non disponibili")

    # === SEZIONE 2: PER TIPO SCUOLA ===
    st.markdown("---")
    st.markdown("### 🏫 Analisi per Tipo Scuola")
    st.caption("Tipologie singole: Infanzia, Primaria, I Grado, Liceo, Tecnico, Professionale")
    
    if 'tipo_scuola' in df_valid.columns:
        # Expand rows that contain multiple types (separated by comma)
        rows = []
        for idx, row in df_valid.iterrows():
            tipo = str(row['tipo_scuola'])
            tipi_singoli = [t.strip() for t in tipo.split(',')]
            for t in tipi_singoli:
                new_row = row.copy()
                new_row['tipo_singolo'] = t
                rows.append(new_row)
        
        df_exploded = pd.DataFrame(rows)
        target_types = ['Infanzia', 'Primaria', 'I Grado', 'Liceo', 'Tecnico', 'Professionale']
        df_target = df_exploded[df_exploded['tipo_singolo'].isin(target_types)].copy()
        
        if not df_target.empty:
            col_tipo1, col_tipo2 = st.columns(2)
            
            with col_tipo1:
                st.markdown("#### 📊 Presenza Sezione")
                tipo_stats = df_target.groupby('tipo_singolo')['has_sezione_dedicata'].agg(['count', 'sum', 'mean']).reset_index()
                tipo_stats.columns = ['Tipo', 'Totale', 'Con Sezione', 'Percentuale']
                tipo_stats['Percentuale'] = tipo_stats['Percentuale'] * 100
                tipo_stats = tipo_stats.sort_values('Percentuale', ascending=False)

                fig_tipo_pres = px.bar(
                    tipo_stats, x='Tipo', y='Percentuale',
                    text=tipo_stats['Percentuale'].apply(lambda x: f'{x:.1f}%'),
                    title="Percentuale Scuole con Sezione Dedicata per Tipo",
                    color='Percentuale', color_continuous_scale='Blues'
                )
                fig_tipo_pres.update_layout(yaxis_title="% con Sezione", xaxis_title="")
                st.plotly_chart(fig_tipo_pres, use_container_width=True)
                
                # Test statistico per presenza
                p_val_tipo_pres, cramers_v_tipo, _ = chi2_test_presence(df_target, 'tipo_singolo', 'has_sezione_dedicata')
                sig_text, sig_color = format_significance(p_val_tipo_pres)
                eff_text, eff_color = interpret_effect_size(cramers_v_tipo, 'cramers_v')
                st.markdown(f"**📈 Significatività (χ²):** :{sig_color}[{sig_text}]")
                if cramers_v_tipo is not None:
                    st.markdown(f"**📏 Effect Size (Cramér's V):** :{eff_color}[{cramers_v_tipo:.3f} - {eff_text}]")
            
            with col_tipo2:
                st.markdown("#### ⭐ Punteggio Medio")
                df_with_sec_tipo = df_target[df_target['has_sezione_dedicata'] == 1]
                
                if not df_with_sec_tipo.empty:
                    score_tipo = df_with_sec_tipo.groupby('tipo_singolo')['2_1_score'].mean().reset_index()
                    score_tipo = score_tipo.sort_values('2_1_score', ascending=False)
                    
                    fig_score_tipo = px.bar(
                        score_tipo, x='tipo_singolo', y='2_1_score',
                        text=score_tipo['2_1_score'].apply(lambda x: f'{x:.2f}'),
                        title="Punteggio Medio per Tipo (solo scuole con sezione)",
                        color='2_1_score', color_continuous_scale='Magma',
                        range_y=[0, 7]
                    )
                    fig_score_tipo.update_layout(yaxis_title="Punteggio Medio (1-7)", xaxis_title="")
                    st.plotly_chart(fig_score_tipo, use_container_width=True)
                    
                    # Test statistico per punteggi
                    p_val_tipo_score, eta_sq_tipo = kruskal_test_scores(df_with_sec_tipo, 'tipo_singolo', '2_1_score')
                    sig_text, sig_color = format_significance(p_val_tipo_score)
                    eff_text, eff_color = interpret_effect_size(eta_sq_tipo, 'eta_squared')
                    st.markdown(f"**📈 Significatività (Kruskal-Wallis):** :{sig_color}[{sig_text}]")
                    if eta_sq_tipo is not None:
                        st.markdown(f"**📏 Effect Size (η²):** :{eff_color}[{eta_sq_tipo:.3f} - {eff_text}]")
                else:
                    st.info("Nessuna scuola con sezione dedicata trovata")
        else:
            st.info("Nessuna scuola trovata per le tipologie specificate")
    else:
        st.info("Dati 'tipo_scuola' non disponibili")

    # === SEZIONE 3: PER ORDINE E GRADO ===
    st.markdown("---")
    st.markdown("### 🎓 Analisi per Ordine e Grado")
    st.caption("Ordini singoli: Infanzia, Primaria, I Grado, II Grado")
    
    if 'ordine_grado' in df_valid.columns:
        # Expand rows that contain multiple ordini (separated by comma)
        rows_ord = []
        for idx, row in df_valid.iterrows():
            ordine = str(row['ordine_grado'])
            ordini_singoli = [o.strip() for o in ordine.split(',')]
            for o in ordini_singoli:
                new_row = row.copy()
                new_row['ordine_singolo'] = o
                rows_ord.append(new_row)
        
        df_exploded_ord = pd.DataFrame(rows_ord)
        target_ordini = ['Infanzia', 'Primaria', 'I Grado', 'II Grado']
        df_target_ord = df_exploded_ord[df_exploded_ord['ordine_singolo'].isin(target_ordini)].copy()
        
        if not df_target_ord.empty:
            col_ord1, col_ord2 = st.columns(2)
            
            with col_ord1:
                st.markdown("#### 📊 Presenza Sezione")
                ord_stats = df_target_ord.groupby('ordine_singolo')['has_sezione_dedicata'].agg(['count', 'sum', 'mean']).reset_index()
                ord_stats.columns = ['Ordine', 'Totale', 'Con Sezione', 'Percentuale']
                ord_stats['Percentuale'] = ord_stats['Percentuale'] * 100
                ord_stats = ord_stats.sort_values('Percentuale', ascending=False)

                fig_ord_pres = px.bar(
                    ord_stats, x='Ordine', y='Percentuale',
                    text=ord_stats['Percentuale'].apply(lambda x: f'{x:.1f}%'),
                    title="Percentuale Scuole con Sezione Dedicata per Ordine",
                    color='Percentuale', color_continuous_scale='Purples'
                )
                fig_ord_pres.update_layout(yaxis_title="% con Sezione", xaxis_title="")
                st.plotly_chart(fig_ord_pres, use_container_width=True)
                
                # Test statistico per presenza
                p_val_ord_pres, cramers_v_ord, _ = chi2_test_presence(df_target_ord, 'ordine_singolo', 'has_sezione_dedicata')
                sig_text, sig_color = format_significance(p_val_ord_pres)
                eff_text, eff_color = interpret_effect_size(cramers_v_ord, 'cramers_v')
                st.markdown(f"**📈 Significatività (χ²):** :{sig_color}[{sig_text}]")
                if cramers_v_ord is not None:
                    st.markdown(f"**📏 Effect Size (Cramér's V):** :{eff_color}[{cramers_v_ord:.3f} - {eff_text}]")

            with col_ord2:
                st.markdown("#### ⭐ Punteggio Medio")
                df_with_sec_ord = df_target_ord[df_target_ord['has_sezione_dedicata'] == 1]
                
                if not df_with_sec_ord.empty:
                    score_ord = df_with_sec_ord.groupby('ordine_singolo')['2_1_score'].mean().reset_index()
                    score_ord = score_ord.sort_values('2_1_score', ascending=False)
                    
                    fig_score_ord = px.bar(
                        score_ord, x='ordine_singolo', y='2_1_score',
                        text=score_ord['2_1_score'].apply(lambda x: f'{x:.2f}'),
                        title="Punteggio Medio per Ordine (solo scuole con sezione)",
                        color='2_1_score', color_continuous_scale='Oranges',
                        range_y=[0, 7]
                    )
                    fig_score_ord.update_layout(yaxis_title="Punteggio Medio (1-7)", xaxis_title="")
                    st.plotly_chart(fig_score_ord, use_container_width=True)
                    
                    # Test statistico per punteggi
                    p_val_ord_score, eta_sq_ord = kruskal_test_scores(df_with_sec_ord, 'ordine_singolo', '2_1_score')
                    sig_text, sig_color = format_significance(p_val_ord_score)
                    eff_text, eff_color = interpret_effect_size(eta_sq_ord, 'eta_squared')
                    st.markdown(f"**📈 Significatività (Kruskal-Wallis):** :{sig_color}[{sig_text}]")
                    if eta_sq_ord is not None:
                        st.markdown(f"**📏 Effect Size (η²):** :{eff_color}[{eta_sq_ord:.3f} - {eff_text}]")
                else:
                    st.info("Nessuna scuola con sezione dedicata trovata")
        else:
            st.info("Nessun ordine trovato tra quelli specificati")
    else:
        st.info("Dati 'ordine_grado' non disponibili")

    # === SEZIONE 4: CONFRONTO RO INDEX - CON VS SENZA SEZIONE ===
    st.markdown("---")
    st.markdown("### 📊 Impatto della Sezione Dedicata sull'Indice RO")
    st.caption("Confronto tra scuole con e senza sezione dedicata all'orientamento")
    
    if 'ptof_orientamento_maturity_index' in df_valid.columns:
        # Prepare data
        df_valid['has_sezione_label'] = df_valid['has_sezione_dedicata'].apply(
            lambda x: '✅ Con Sezione' if x == 1 else '❌ Senza Sezione'
        )
        
        col_ro1, col_ro2 = st.columns(2)
        
        with col_ro1:
            st.markdown("#### 📈 Distribuzione Indice RO")
            
            # Box plot comparison
            fig_ro_box = px.box(
                df_valid, x='has_sezione_label', y='ptof_orientamento_maturity_index',
                color='has_sezione_label',
                color_discrete_map={'✅ Con Sezione': '#28a745', '❌ Senza Sezione': '#dc3545'},
                title="Distribuzione Indice RO: Con vs Senza Sezione",
                points='all'
            )
            fig_ro_box.update_layout(
                yaxis_title="Indice RO", 
                xaxis_title="",
                showlegend=False
            )
            st.plotly_chart(fig_ro_box, use_container_width=True)
            
        with col_ro2:
            st.markdown("#### 📊 Confronto Medie")
            
            # Calculate means
            mean_with = df_valid[df_valid['has_sezione_dedicata'] == 1]['ptof_orientamento_maturity_index'].mean()
            mean_without = df_valid[df_valid['has_sezione_dedicata'] == 0]['ptof_orientamento_maturity_index'].mean()
            n_with = (df_valid['has_sezione_dedicata'] == 1).sum()
            n_without = (df_valid['has_sezione_dedicata'] == 0).sum()
            
            # Bar chart
            comparison_df = pd.DataFrame({
                'Gruppo': ['✅ Con Sezione', '❌ Senza Sezione'],
                'Media RO': [mean_with, mean_without],
                'N': [n_with, n_without]
            })
            
            fig_ro_bar = px.bar(
                comparison_df, x='Gruppo', y='Media RO',
                text=comparison_df['Media RO'].apply(lambda x: f'{x:.2f}'),
                color='Gruppo',
                color_discrete_map={'✅ Con Sezione': '#28a745', '❌ Senza Sezione': '#dc3545'},
                title="Media Indice RO: Con vs Senza Sezione"
            )
            fig_ro_bar.update_layout(
                yaxis_title="Media Indice RO", 
                xaxis_title="",
                showlegend=False,
                yaxis_range=[0, max(mean_with, mean_without) * 1.2]
            )
            st.plotly_chart(fig_ro_bar, use_container_width=True)
        
        # Statistical test
        st.markdown("#### 🔬 Test Statistico")
        
        group_with = df_valid[df_valid['has_sezione_dedicata'] == 1]['ptof_orientamento_maturity_index'].dropna()
        group_without = df_valid[df_valid['has_sezione_dedicata'] == 0]['ptof_orientamento_maturity_index'].dropna()
        
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        
        with col_stat1:
            diff = mean_with - mean_without
            diff_pct = (diff / mean_without * 100) if mean_without > 0 else 0
            color = "green" if diff > 0 else "red"
            st.metric(
                "Differenza Media", 
                f"{diff:+.2f}",
                delta=f"{diff_pct:+.1f}%",
                delta_color="normal" if diff > 0 else "inverse"
            )
        
        with col_stat2:
            # Mann-Whitney U test (non-parametric)
            if len(group_with) >= 2 and len(group_without) >= 2:
                stat, p_value = stats.mannwhitneyu(group_with, group_without, alternative='two-sided')
                sig_text, sig_color = format_significance(p_value)
                st.markdown(f"**Mann-Whitney U:**")
                st.markdown(f":{sig_color}[{sig_text}]")
            else:
                st.info("Dati insufficienti per il test")
        
        with col_stat3:
            # Effect size (Cohen's d)
            if len(group_with) >= 2 and len(group_without) >= 2:
                pooled_std = np.sqrt(((len(group_with)-1)*group_with.std()**2 + 
                                      (len(group_without)-1)*group_without.std()**2) / 
                                     (len(group_with) + len(group_without) - 2))
                cohens_d = (mean_with - mean_without) / pooled_std if pooled_std > 0 else 0
                
                # Interpret Cohen's d
                if abs(cohens_d) < 0.2:
                    eff_text, eff_color = "Trascurabile", "gray"
                elif abs(cohens_d) < 0.5:
                    eff_text, eff_color = "Piccolo", "orange"
                elif abs(cohens_d) < 0.8:
                    eff_text, eff_color = "Medio", "blue"
                else:
                    eff_text, eff_color = "Grande", "green"
                
                st.markdown(f"**Cohen's d:**")
                st.markdown(f":{eff_color}[{cohens_d:.3f} - {eff_text}]")
            else:
                st.info("Dati insufficienti")
        
        # Interpretation
        if mean_with > mean_without and p_value < 0.05:
            st.success(f"🎯 **Le scuole CON sezione dedicata hanno un Indice RO significativamente più alto** (+{diff:.2f} punti, +{diff_pct:.1f}%)")
        elif mean_with > mean_without:
            st.info(f"📊 Le scuole con sezione dedicata hanno un Indice RO più alto (+{diff:.2f}), ma la differenza non è statisticamente significativa.")
        elif mean_without > mean_with and p_value < 0.05:
            st.warning(f"⚠️ Le scuole SENZA sezione dedicata hanno un Indice RO più alto ({-diff:.2f} punti)")
        else:
            st.info("📊 Non c'è una differenza significativa tra i due gruppi.")

    # === SEZIONE 5: CONFRONTO GRANULARE PER TIPO SCUOLA ===
    st.markdown("---")
    st.markdown("### 🏫 Confronto RO per Tipo Scuola (Con vs Senza Sezione)")
    
    if 'tipo_scuola' in df_valid.columns and 'ptof_orientamento_maturity_index' in df_valid.columns:
        # Expand types
        rows_tipo = []
        for idx, row in df_valid.iterrows():
            tipo = str(row['tipo_scuola'])
            tipi_singoli = [t.strip() for t in tipo.split(',')]
            for t in tipi_singoli:
                new_row = row.copy()
                new_row['tipo_singolo'] = t
                rows_tipo.append(new_row)
        
        df_tipo_exp = pd.DataFrame(rows_tipo)
        target_types = ['Infanzia', 'Primaria', 'I Grado', 'Liceo', 'Tecnico', 'Professionale']
        df_tipo_exp = df_tipo_exp[df_tipo_exp['tipo_singolo'].isin(target_types)].copy()
        
        if not df_tipo_exp.empty:
            # Calculate means for each type, split by has_sezione
            tipo_comparison = df_tipo_exp.groupby(['tipo_singolo', 'has_sezione_dedicata'])['ptof_orientamento_maturity_index'].mean().reset_index()
            tipo_comparison['Sezione'] = tipo_comparison['has_sezione_dedicata'].apply(lambda x: '✅ Con' if x == 1 else '❌ Senza')
            
            fig_tipo_comp = px.bar(
                tipo_comparison, x='tipo_singolo', y='ptof_orientamento_maturity_index',
                color='Sezione', barmode='group',
                color_discrete_map={'✅ Con': '#28a745', '❌ Senza': '#dc3545'},
                text=tipo_comparison['ptof_orientamento_maturity_index'].apply(lambda x: f'{x:.2f}'),
                title="Media Indice RO per Tipo Scuola: Con vs Senza Sezione"
            )
            fig_tipo_comp.update_layout(yaxis_title="Media Indice RO", xaxis_title="", legend_title="Sezione Dedicata")
            st.plotly_chart(fig_tipo_comp, use_container_width=True)
            
            # Summary table with stats
            summary_tipo = []
            for tipo in target_types:
                df_t = df_tipo_exp[df_tipo_exp['tipo_singolo'] == tipo]
                group_con = df_t[df_t['has_sezione_dedicata'] == 1]['ptof_orientamento_maturity_index'].dropna()
                group_senza = df_t[df_t['has_sezione_dedicata'] == 0]['ptof_orientamento_maturity_index'].dropna()
                mean_con = group_con.mean() if len(group_con) > 0 else None
                mean_senza = group_senza.mean() if len(group_senza) > 0 else None
                n_con = len(group_con)
                n_senza = len(group_senza)
                diff = mean_con - mean_senza if pd.notna(mean_con) and pd.notna(mean_senza) else None
                
                # Statistical test
                p_val, cohens_d = None, None
                if n_con >= 2 and n_senza >= 2:
                    try:
                        _, p_val = stats.mannwhitneyu(group_con, group_senza, alternative='two-sided')
                        pooled_std = np.sqrt(((n_con-1)*group_con.std()**2 + (n_senza-1)*group_senza.std()**2) / (n_con + n_senza - 2))
                        cohens_d = (mean_con - mean_senza) / pooled_std if pooled_std > 0 else 0
                    except:
                        pass
                
                sig_text, _ = format_significance(p_val) if p_val else ("N/D", "gray")
                eff_text = f"{cohens_d:.2f}" if cohens_d is not None else "N/D"
                
                summary_tipo.append({
                    'Tipo': tipo,
                    'Media Con': f"{mean_con:.2f}" if pd.notna(mean_con) else "N/D",
                    'N Con': n_con,
                    'Media Senza': f"{mean_senza:.2f}" if pd.notna(mean_senza) else "N/D",
                    'N Senza': n_senza,
                    'Diff.': f"{diff:+.2f}" if diff else "N/D",
                    'p-value': sig_text,
                    "Cohen's d": eff_text,
                    'Vantaggio': "✅ Con" if diff and diff > 0 else ("❌ Senza" if diff and diff < 0 else "=")
                })
            st.dataframe(pd.DataFrame(summary_tipo), use_container_width=True, hide_index=True)
    
    # === SEZIONE 6: CONFRONTO GRANULARE PER REGIONE ===
    st.markdown("---")
    st.markdown("### 🌍 Confronto RO per Regione (Con vs Senza Sezione)")
    
    if 'regione' in df_valid.columns and 'ptof_orientamento_maturity_index' in df_valid.columns:
        # Calculate means for each region, split by has_sezione
        reg_comparison = df_valid.groupby(['regione', 'has_sezione_dedicata'])['ptof_orientamento_maturity_index'].mean().reset_index()
        reg_comparison['Sezione'] = reg_comparison['has_sezione_dedicata'].apply(lambda x: '✅ Con' if x == 1 else '❌ Senza')
        
        fig_reg_comp = px.bar(
            reg_comparison, x='regione', y='ptof_orientamento_maturity_index',
            color='Sezione', barmode='group',
            color_discrete_map={'✅ Con': '#28a745', '❌ Senza': '#dc3545'},
            text=reg_comparison['ptof_orientamento_maturity_index'].apply(lambda x: f'{x:.2f}'),
            title="Media Indice RO per Regione: Con vs Senza Sezione"
        )
        fig_reg_comp.update_layout(yaxis_title="Media Indice RO", xaxis_title="", legend_title="Sezione Dedicata")
        st.plotly_chart(fig_reg_comp, use_container_width=True)
        
        # Summary table with stats
        summary_reg = []
        for regione in df_valid['regione'].dropna().unique():
            df_r = df_valid[df_valid['regione'] == regione]
            group_con = df_r[df_r['has_sezione_dedicata'] == 1]['ptof_orientamento_maturity_index'].dropna()
            group_senza = df_r[df_r['has_sezione_dedicata'] == 0]['ptof_orientamento_maturity_index'].dropna()
            mean_con = group_con.mean() if len(group_con) > 0 else None
            mean_senza = group_senza.mean() if len(group_senza) > 0 else None
            n_con = len(group_con)
            n_senza = len(group_senza)
            diff = mean_con - mean_senza if pd.notna(mean_con) and pd.notna(mean_senza) else None
            
            # Statistical test
            p_val, cohens_d = None, None
            if n_con >= 2 and n_senza >= 2:
                try:
                    _, p_val = stats.mannwhitneyu(group_con, group_senza, alternative='two-sided')
                    pooled_std = np.sqrt(((n_con-1)*group_con.std()**2 + (n_senza-1)*group_senza.std()**2) / (n_con + n_senza - 2))
                    cohens_d = (mean_con - mean_senza) / pooled_std if pooled_std > 0 else 0
                except:
                    pass
            
            sig_text, _ = format_significance(p_val) if p_val else ("N/D", "gray")
            eff_text = f"{cohens_d:.2f}" if cohens_d is not None else "N/D"
            
            summary_reg.append({
                'Regione': regione,
                'Media Con': f"{mean_con:.2f}" if pd.notna(mean_con) else "N/D",
                'N Con': n_con,
                'Media Senza': f"{mean_senza:.2f}" if pd.notna(mean_senza) else "N/D",
                'N Senza': n_senza,
                'Diff.': f"{diff:+.2f}" if diff else "N/D",
                'p-value': sig_text,
                "Cohen's d": eff_text,
                'Vantaggio': "✅ Con" if diff and diff > 0 else ("❌ Senza" if diff and diff < 0 else "=")
            })
        summary_reg_df = pd.DataFrame(summary_reg).sort_values('Regione')
        st.dataframe(summary_reg_df, use_container_width=True, hide_index=True)
    
    # === SEZIONE 7: CONFRONTO GRANULARE PER ORDINE E GRADO ===
    st.markdown("---")
    st.markdown("### 🎓 Confronto RO per Ordine e Grado (Con vs Senza Sezione)")
    
    if 'ordine_grado' in df_valid.columns and 'ptof_orientamento_maturity_index' in df_valid.columns:
        # Expand ordini
        rows_ord = []
        for idx, row in df_valid.iterrows():
            ordine = str(row['ordine_grado'])
            ordini_singoli = [o.strip() for o in ordine.split(',')]
            for o in ordini_singoli:
                new_row = row.copy()
                new_row['ordine_singolo'] = o
                rows_ord.append(new_row)
        
        df_ord_exp = pd.DataFrame(rows_ord)
        target_ordini = ['Infanzia', 'Primaria', 'I Grado', 'II Grado']
        df_ord_exp = df_ord_exp[df_ord_exp['ordine_singolo'].isin(target_ordini)].copy()
        
        if not df_ord_exp.empty:
            # Calculate means for each ordine, split by has_sezione
            ord_comparison = df_ord_exp.groupby(['ordine_singolo', 'has_sezione_dedicata'])['ptof_orientamento_maturity_index'].mean().reset_index()
            ord_comparison['Sezione'] = ord_comparison['has_sezione_dedicata'].apply(lambda x: '✅ Con' if x == 1 else '❌ Senza')
            
            fig_ord_comp = px.bar(
                ord_comparison, x='ordine_singolo', y='ptof_orientamento_maturity_index',
                color='Sezione', barmode='group',
                color_discrete_map={'✅ Con': '#28a745', '❌ Senza': '#dc3545'},
                text=ord_comparison['ptof_orientamento_maturity_index'].apply(lambda x: f'{x:.2f}'),
                title="Media Indice RO per Ordine: Con vs Senza Sezione"
            )
            fig_ord_comp.update_layout(yaxis_title="Media Indice RO", xaxis_title="", legend_title="Sezione Dedicata")
            st.plotly_chart(fig_ord_comp, use_container_width=True)
            
            # Summary table with stats
            summary_ord = []
            for ordine in target_ordini:
                df_o = df_ord_exp[df_ord_exp['ordine_singolo'] == ordine]
                group_con = df_o[df_o['has_sezione_dedicata'] == 1]['ptof_orientamento_maturity_index'].dropna()
                group_senza = df_o[df_o['has_sezione_dedicata'] == 0]['ptof_orientamento_maturity_index'].dropna()
                mean_con = group_con.mean() if len(group_con) > 0 else None
                mean_senza = group_senza.mean() if len(group_senza) > 0 else None
                n_con = len(group_con)
                n_senza = len(group_senza)
                diff = mean_con - mean_senza if pd.notna(mean_con) and pd.notna(mean_senza) else None
                
                # Statistical test
                p_val, cohens_d = None, None
                if n_con >= 2 and n_senza >= 2:
                    try:
                        _, p_val = stats.mannwhitneyu(group_con, group_senza, alternative='two-sided')
                        pooled_std = np.sqrt(((n_con-1)*group_con.std()**2 + (n_senza-1)*group_senza.std()**2) / (n_con + n_senza - 2))
                        cohens_d = (mean_con - mean_senza) / pooled_std if pooled_std > 0 else 0
                    except:
                        pass
                
                sig_text, _ = format_significance(p_val) if p_val else ("N/D", "gray")
                eff_text = f"{cohens_d:.2f}" if cohens_d is not None else "N/D"
                
                summary_ord.append({
                    'Ordine': ordine,
                    'Media Con': f"{mean_con:.2f}" if pd.notna(mean_con) else "N/D",
                    'N Con': n_con,
                    'Media Senza': f"{mean_senza:.2f}" if pd.notna(mean_senza) else "N/D",
                    'N Senza': n_senza,
                    'Diff.': f"{diff:+.2f}" if diff else "N/D",
                    'p-value': sig_text,
                    "Cohen's d": eff_text,
                    'Vantaggio': "✅ Con" if diff and diff > 0 else ("❌ Senza" if diff and diff < 0 else "=")
                })
            st.dataframe(pd.DataFrame(summary_ord), use_container_width=True, hide_index=True)

    # === LEGENDA TEST STATISTICI ===
    st.markdown("---")
    with st.expander("ℹ️ Come interpretare i test statistici"):
        st.markdown("""
        **Test utilizzati:**
        - **Chi-quadrato (χ²)**: Verifica se la presenza della sezione dedicata varia significativamente tra gruppi (regioni, tipi, ordini).
        - **Kruskal-Wallis**: Verifica se i punteggi medi differiscono significativamente tra gruppi (test non parametrico).
        
        **Significatività (p-value):**
        - `***` p < 0.001: Differenza molto significativa
        - `**` p < 0.01: Differenza significativa
        - `*` p < 0.05: Differenza marginalmente significativa
        - `n.s.`: Non significativo (p ≥ 0.05)
        
        **Effect Size (dimensione dell'effetto):**
        - **Cramér's V** (per presenza): Trascurabile (<0.1), Piccolo (0.1-0.3), Medio (0.3-0.5), Grande (>0.5)
        - **η² (Eta-squared)** (per punteggi): Trascurabile (<0.01), Piccolo (0.01-0.06), Medio (0.06-0.14), Grande (>0.14)
        
        Un risultato significativo con effect size piccolo indica che, pur essendoci una differenza reale, questa ha un impatto pratico limitato.
        """)

else:
    st.warning("Dati 'has_sezione_dedicata' o '2_1_score' non disponibili nel dataset")

st.info("""
💡 **A cosa serve**: Analizza in profondità la presenza e qualità della "Sezione Dedicata all'Orientamento" nei PTOF, confrontando regioni, tipologie e ordini scolastici.

🔍 **Cosa rileva**: Per ogni categoria (regione, tipo scuola, ordine) mostra: percentuale di scuole con sezione dedicata, punteggio medio della sezione. I test statistici (Chi-quadrato, Kruskal-Wallis) verificano se le differenze sono significative. L'effect size indica l'impatto pratico.

🎯 **Implicazioni**: Una sezione dedicata all'orientamento è indicatore di attenzione specifica al tema. Regioni o tipologie con bassa presenza potrebbero necessitare di sensibilizzazione. Differenze nei punteggi suggeriscono dove la qualità è migliore.
""")

st.markdown("---")

# === 6. CORRELATION QUICK INSIGHTS ===
st.subheader("🔗 Correlazioni Chiave")
st.caption("Relazioni tra dimensioni e metriche")

if all(c in df_valid.columns for c in dim_cols):
    corr_cols = dim_cols + ['ptof_orientamento_maturity_index']
    if 'partnership_count' in df_valid.columns:
        corr_cols.append('partnership_count')
    
    corr_matrix = df_valid[corr_cols].corr()
    
    # Rename for display
    corr_matrix.index = [get_label(c) for c in corr_matrix.index]
    corr_matrix.columns = [get_label(c) for c in corr_matrix.columns]
    
    fig_corr = px.imshow(
        corr_matrix,
        text_auto='.2f',
        color_continuous_scale='RdBu_r',
        range_color=[-1, 1],
        title="Matrice di Correlazione"
    )
    fig_corr.update_layout(height=500)
    st.plotly_chart(fig_corr, use_container_width=True)
    
    # Top correlations
    st.markdown("### 📊 Correlazioni più Forti")
    
    # Get top correlations
    corr_pairs = []
    for i in range(len(corr_cols)):
        for j in range(i+1, len(corr_cols)):
            corr_pairs.append({
                'Variabile 1': get_label(corr_cols[i]),
                'Variabile 2': get_label(corr_cols[j]),
                'Correlazione': corr_matrix.iloc[i, j]
            })
    
    corr_pairs_df = pd.DataFrame(corr_pairs)
    corr_pairs_df = corr_pairs_df.reindex(
        corr_pairs_df['Correlazione'].abs().sort_values(ascending=False).index
    ).head(5)
    
    st.dataframe(corr_pairs_df.round(3), use_container_width=True, hide_index=True)

st.info("""
💡 **A cosa serve**: Mostra quali dimensioni e metriche sono correlate tra loro, rivelando relazioni sistematiche.

🔍 **Cosa rileva**: La heatmap visualizza le correlazioni: rosso=positiva (crescono insieme), blu=negativa (una cresce, l'altra cala). Valori vicini a ±1 indicano forte correlazione, vicini a 0 indicano indipendenza. La tabella elenca le 5 correlazioni più forti.

🎯 **Implicazioni**: Dimensioni fortemente correlate potrebbero avere cause comuni. Se vuoi migliorare una dimensione, potresti beneficiare anche in quelle correlate. Correlazioni deboli suggeriscono aspetti indipendenti da affrontare separatamente.
""")

# Footer
st.markdown("---")
st.caption("📊 KPI Avanzati - Dashboard PTOF | Statistiche approfondite e analisi degli outlier")
