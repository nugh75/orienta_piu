# 📊 KPI Avanzati - Statistiche e Analisi Approfondite

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import os

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
    'ptof_orientamento_maturity_index': 'Indice Robustezza',
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
    st.warning("⚠️ Nessuna scuola con indice di robustezza valido.")
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
    st.metric("📊 Media Indice", f"{mean_idx:.2f}")

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
        title="Distribuzione Indice di Robustezza"
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

st.markdown("---")

# === 4. REGRESSION SUMMARY ===
st.subheader("📈 Analisi Regressione")
st.caption("Identificazione dei migliori predittori dell'indice di robustezza")

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

# Footer
st.markdown("---")
st.caption("📊 KPI Avanzati - Dashboard PTOF | Statistiche approfondite e analisi degli outlier")
