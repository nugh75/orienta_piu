# 🏆 Benchmark - Rankings e Confronti

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import os

st.set_page_config(page_title="Benchmark", page_icon="🏆", layout="wide")

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
    .top-performer { background-color: #d4edda !important; border-left-color: #28a745 !important; }
    .bottom-performer { background-color: #f8d7da !important; border-left-color: #dc3545 !important; }
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

@st.cache_data(ttl=60)
def load_data():
    if os.path.exists(SUMMARY_FILE):
        df = pd.read_csv(SUMMARY_FILE)
        return df
    return pd.DataFrame()

df = load_data()

st.title("🏆 Benchmark e Confronti")
st.markdown("Analisi comparativa delle performance delle scuole")

if df.empty:
    st.warning("⚠️ Nessun dato disponibile. Esegui prima il pipeline di analisi.")
    st.stop()

# Standardize numeric columns
numeric_cols = ['ptof_orientamento_maturity_index', 'mean_finalita', 'mean_obiettivi', 
                'mean_governance', 'mean_didattica_orientativa', 'mean_opportunita',
                'partnership_count']
for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

# Filter valid data
df_valid = df[df['ptof_orientamento_maturity_index'].notna() & (df['ptof_orientamento_maturity_index'] > 0)].copy()

if len(df_valid) == 0:
    st.warning("⚠️ Nessuna scuola con indice di robustezza valido.")
    st.stop()

st.markdown("---")

# === 1. BEST IN CLASS PER TIPO SCUOLA ===
st.subheader("🥇 Best-in-Class per Tipologia")
st.caption("Le migliori scuole per ciascuna tipologia scolastica")

if 'tipo_scuola' in df_valid.columns:
    # Explode tipo_scuola if contains multiple types
    def get_primary_type(tipo):
        if pd.isna(tipo):
            return 'Non Specificato'
        if ',' in str(tipo):
            return str(tipo).split(',')[0].strip()
        return str(tipo).strip()
    
    df_valid['tipo_primario'] = df_valid['tipo_scuola'].apply(get_primary_type)
    
    tipi = df_valid['tipo_primario'].unique()
    tipi = [t for t in tipi if t != 'Non Specificato']
    
    # Create tabs for each type
    if len(tipi) > 0:
        tabs = st.tabs(tipi)
        
        for i, tipo in enumerate(tipi):
            with tabs[i]:
                df_tipo = df_valid[df_valid['tipo_primario'] == tipo].copy()
                df_tipo = df_tipo.sort_values('ptof_orientamento_maturity_index', ascending=False)
                
                top3 = df_tipo.head(3)
                
                if len(top3) > 0:
                    cols = st.columns(min(3, len(top3)))
                    medals = ['🥇', '🥈', '🥉']
                    
                    for j, (_, row) in enumerate(top3.iterrows()):
                        with cols[j]:
                            st.markdown(f"### {medals[j]} #{j+1}")
                            st.metric(
                                label=row.get('denominazione', 'N/D')[:40],
                                value=f"{row['ptof_orientamento_maturity_index']:.2f}/7"
                            )
                            st.caption(f"📍 {row.get('comune', 'N/D')} | {row.get('area_geografica', 'N/D')}")
                else:
                    st.info(f"Nessuna scuola di tipo {tipo}")
else:
    st.info("Colonna 'tipo_scuola' non disponibile")

st.markdown("---")

# === 2. TOP vs BOTTOM PERFORMERS ===
st.subheader("📊 Top 10 vs Bottom 10")
st.caption("Confronto tra le scuole con i punteggi più alti e più bassi")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🔝 Top 10 Performers")
    top10 = df_valid.nlargest(10, 'ptof_orientamento_maturity_index')[
        ['denominazione', 'tipo_scuola', 'area_geografica', 'ptof_orientamento_maturity_index']
    ].copy()
    top10.columns = ['Scuola', 'Tipo', 'Area', 'Indice']
    top10.insert(0, '#', range(1, len(top10) + 1))
    top10['Indice'] = top10['Indice'].round(2)
    st.dataframe(top10, use_container_width=True, hide_index=True)

with col2:
    st.markdown("### 🔻 Bottom 10 Performers")
    bottom10 = df_valid.nsmallest(10, 'ptof_orientamento_maturity_index')[
        ['denominazione', 'tipo_scuola', 'area_geografica', 'ptof_orientamento_maturity_index']
    ].copy()
    bottom10.columns = ['Scuola', 'Tipo', 'Area', 'Indice']
    bottom10.insert(0, '#', range(1, len(bottom10) + 1))
    bottom10['Indice'] = bottom10['Indice'].round(2)
    st.dataframe(bottom10, use_container_width=True, hide_index=True)

# Comparison chart
st.markdown("### 📈 Visualizzazione Comparativa")
comparison_df = pd.concat([
    top10.assign(Gruppo='Top 10'),
    bottom10.assign(Gruppo='Bottom 10')
])

fig_compare = px.bar(
    comparison_df, x='Scuola', y='Indice', color='Gruppo',
    color_discrete_map={'Top 10': '#28a745', 'Bottom 10': '#dc3545'},
    title="Top 10 vs Bottom 10 - Indice di Robustezza",
    barmode='group'
)
fig_compare.update_layout(xaxis_tickangle=45, height=400)
fig_compare.update_xaxes(tickfont_size=8)
st.plotly_chart(fig_compare, use_container_width=True)

st.markdown("---")

# === 2b. CLASSIFICA COMPLETA ===
st.subheader("📋 Classifica Completa")
st.caption("Tutte le scuole ordinate per indice di robustezza con le medie per dimensione")

# Prepare complete ranking with all means
ranking_cols = ['denominazione', 'tipo_scuola', 'regione', 'area_geografica', 'ptof_orientamento_maturity_index']
dim_cols_ranking = ['mean_finalita', 'mean_obiettivi', 'mean_governance', 'mean_didattica_orientativa', 'mean_opportunita']

# Add dimension columns if they exist
for col in dim_cols_ranking:
    if col in df_valid.columns:
        ranking_cols.append(col)

df_ranking = df_valid[ranking_cols].copy()
df_ranking = df_ranking.sort_values('ptof_orientamento_maturity_index', ascending=False)
df_ranking.insert(0, 'Pos.', range(1, len(df_ranking) + 1))

# Rename columns for display
rename_map = {
    'denominazione': 'Scuola',
    'tipo_scuola': 'Tipo',
    'regione': 'Regione',
    'area_geografica': 'Area',
    'ptof_orientamento_maturity_index': 'Indice',
    'mean_finalita': 'Finalità',
    'mean_obiettivi': 'Obiettivi',
    'mean_governance': 'Governance',
    'mean_didattica_orientativa': 'Didattica',
    'mean_opportunita': 'Opportunità'
}
df_ranking = df_ranking.rename(columns=rename_map)

# Round numeric columns
numeric_display_cols = ['Indice', 'Finalità', 'Obiettivi', 'Governance', 'Didattica', 'Opportunità']
for col in numeric_display_cols:
    if col in df_ranking.columns:
        df_ranking[col] = df_ranking[col].round(2)

# Add filter options
col_filter1, col_filter2, col_filter3 = st.columns(3)

with col_filter1:
    if 'Tipo' in df_ranking.columns:
        tipi_filtro = ['Tutti'] + sorted(df_ranking['Tipo'].dropna().unique().tolist())
        tipo_sel = st.selectbox("Filtra per Tipo", tipi_filtro, key='ranking_tipo')
    else:
        tipo_sel = 'Tutti'

with col_filter2:
    if 'Regione' in df_ranking.columns:
        regioni_filtro = ['Tutte'] + sorted(df_ranking['Regione'].dropna().unique().tolist())
        regione_sel = st.selectbox("Filtra per Regione", regioni_filtro, key='ranking_regione')
    else:
        regione_sel = 'Tutte'

with col_filter3:
    if 'Area' in df_ranking.columns:
        aree_filtro = ['Tutte'] + sorted(df_ranking['Area'].dropna().unique().tolist())
        area_sel = st.selectbox("Filtra per Area", aree_filtro, key='ranking_area')
    else:
        area_sel = 'Tutte'

# Apply filters
df_ranking_filtered = df_ranking.copy()
if tipo_sel != 'Tutti' and 'Tipo' in df_ranking_filtered.columns:
    df_ranking_filtered = df_ranking_filtered[df_ranking_filtered['Tipo'].str.contains(tipo_sel, na=False)]
if regione_sel != 'Tutte' and 'Regione' in df_ranking_filtered.columns:
    df_ranking_filtered = df_ranking_filtered[df_ranking_filtered['Regione'] == regione_sel]
if area_sel != 'Tutte' and 'Area' in df_ranking_filtered.columns:
    df_ranking_filtered = df_ranking_filtered[df_ranking_filtered['Area'] == area_sel]

# Recalculate positions after filtering
df_ranking_filtered = df_ranking_filtered.copy()
df_ranking_filtered['Pos.'] = range(1, len(df_ranking_filtered) + 1)

# Display stats
st.markdown(f"**{len(df_ranking_filtered)}** scuole nella selezione (su {len(df_ranking)} totali)")

# Display with progress bars
st.dataframe(
    df_ranking_filtered,
    use_container_width=True,
    hide_index=True,
    height=500,
    column_config={
        'Pos.': st.column_config.NumberColumn('Pos.', width='small'),
        'Scuola': st.column_config.TextColumn('Scuola', width='large'),
        'Indice': st.column_config.ProgressColumn('Indice', min_value=0, max_value=7, format='%.2f'),
        'Finalità': st.column_config.ProgressColumn('Finalità', min_value=0, max_value=7, format='%.2f'),
        'Obiettivi': st.column_config.ProgressColumn('Obiettivi', min_value=0, max_value=7, format='%.2f'),
        'Governance': st.column_config.ProgressColumn('Governance', min_value=0, max_value=7, format='%.2f'),
        'Didattica': st.column_config.ProgressColumn('Didattica', min_value=0, max_value=7, format='%.2f'),
        'Opportunità': st.column_config.ProgressColumn('Opportunità', min_value=0, max_value=7, format='%.2f'),
    }
)

# Summary statistics for filtered selection
if len(df_ranking_filtered) > 0:
    with st.expander("📊 Statistiche della selezione"):
        stat_cols = ['Indice', 'Finalità', 'Obiettivi', 'Governance', 'Didattica', 'Opportunità']
        stat_cols = [c for c in stat_cols if c in df_ranking_filtered.columns]
        
        stats_summary = df_ranking_filtered[stat_cols].describe().round(2)
        st.dataframe(stats_summary, use_container_width=True)
        
        # Best and worst in selection
        col_best, col_worst = st.columns(2)
        with col_best:
            best = df_ranking_filtered.iloc[0]
            st.success(f"🥇 **Migliore**: {best['Scuola'][:40]} (Indice: {best['Indice']:.2f})")
        with col_worst:
            worst = df_ranking_filtered.iloc[-1]
            st.warning(f"🔻 **Ultimo**: {worst['Scuola'][:40]} (Indice: {worst['Indice']:.2f})")

# Download button
csv_data = df_ranking_filtered.to_csv(index=False)
st.download_button(
    label="📥 Scarica Classifica (CSV)",
    data=csv_data,
    file_name="classifica_scuole.csv",
    mime="text/csv"
)

st.markdown("---")

# === 3. PERCENTILE POSITIONING ===
st.subheader("📍 Posizionamento Percentile")
st.caption("Scopri dove si posiziona una scuola rispetto alla distribuzione nazionale")

# School selector
if 'denominazione' in df_valid.columns:
    school_options = sorted(df_valid['denominazione'].dropna().unique().tolist())
    selected_school = st.selectbox("Seleziona una scuola", school_options)
    
    if selected_school:
        school_row = df_valid[df_valid['denominazione'] == selected_school].iloc[0]
        school_score = school_row['ptof_orientamento_maturity_index']
        
        # Calculate percentile
        all_scores = df_valid['ptof_orientamento_maturity_index'].dropna()
        percentile = (all_scores < school_score).sum() / len(all_scores) * 100
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Indice Robustezza", f"{school_score:.2f}/7")
        
        with col2:
            st.metric("Percentile", f"{percentile:.0f}°")
            if percentile >= 75:
                st.success("🌟 Eccellente! Top 25%")
            elif percentile >= 50:
                st.info("👍 Sopra la media")
            elif percentile >= 25:
                st.warning("⚠️ Sotto la media")
            else:
                st.error("❌ Bottom 25%")
        
        with col3:
            rank = int((all_scores >= school_score).sum())
            st.metric("Posizione in Classifica", f"{rank}/{len(all_scores)}")
        
        # Distribution chart with marker
        fig_dist = go.Figure()
        
        # Histogram
        fig_dist.add_trace(go.Histogram(
            x=all_scores, nbinsx=20,
            name='Distribuzione',
            marker_color='#3498db',
            opacity=0.7
        ))
        
        # Marker for selected school
        fig_dist.add_vline(x=school_score, line_dash="dash", line_color="red", line_width=3)
        fig_dist.add_annotation(
            x=school_score, y=0,
            text=f"{selected_school[:20]}...",
            showarrow=True, arrowhead=2,
            yshift=100, xshift=20
        )
        
        fig_dist.update_layout(
            title="Posizione nella Distribuzione Nazionale",
            xaxis_title="Indice di Robustezza",
            yaxis_title="Frequenza",
            height=400
        )
        
        st.plotly_chart(fig_dist, use_container_width=True)

st.markdown("---")

# === 4. MULTI-SCHOOL RADAR COMPARISON ===
st.subheader("🎯 Confronto Multi-Scuola (Radar)")
st.caption("Confronta fino a 5 scuole su tutte le dimensioni")

dim_cols = ['mean_finalita', 'mean_obiettivi', 'mean_governance', 'mean_didattica_orientativa', 'mean_opportunita']

if all(c in df_valid.columns for c in dim_cols):
    selected_schools = st.multiselect(
        "Seleziona fino a 5 scuole da confrontare",
        options=sorted(df_valid['denominazione'].dropna().unique().tolist()),
        max_selections=5
    )
    
    if selected_schools:
        fig_radar = go.Figure()
        
        colors = px.colors.qualitative.Set1
        
        # Add average line
        avg_values = [df_valid[c].mean() for c in dim_cols]
        avg_values.append(avg_values[0])  # Close
        labels = [get_label(c) for c in dim_cols]
        labels.append(labels[0])
        
        fig_radar.add_trace(go.Scatterpolar(
            r=avg_values,
            theta=labels,
            fill='toself',
            name='Media Nazionale',
            line_color='gray',
            opacity=0.3
        ))
        
        # Add selected schools
        for i, school in enumerate(selected_schools):
            row = df_valid[df_valid['denominazione'] == school].iloc[0]
            values = [row[c] for c in dim_cols]
            values.append(values[0])
            
            fig_radar.add_trace(go.Scatterpolar(
                r=values,
                theta=labels,
                fill='toself',
                name=school[:30],
                line_color=colors[i % len(colors)],
                opacity=0.7
            ))
        
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 7])),
            showlegend=True,
            title="Confronto Profili Scuole",
            height=550
        )
        
        st.plotly_chart(fig_radar, use_container_width=True)
        
        # Comparison table
        comparison_data = []
        for school in selected_schools:
            row = df_valid[df_valid['denominazione'] == school].iloc[0]
            comparison_data.append({
                'Scuola': school[:40],
                **{get_label(c): f"{row[c]:.2f}" for c in dim_cols},
                'Indice': f"{row['ptof_orientamento_maturity_index']:.2f}"
            })
        
        st.dataframe(pd.DataFrame(comparison_data), use_container_width=True, hide_index=True)
    else:
        st.info("Seleziona almeno una scuola per il confronto")
else:
    st.warning("Dati delle dimensioni non disponibili")

st.markdown("---")

# === 5. PERFORMANCE QUADRANT ===
st.subheader("📐 Quadrante Performance")
st.caption("Visualizzazione bidimensionale per classificare le scuole in 4 categorie strategiche")

col1, col2 = st.columns(2)

with col1:
    x_metric = st.selectbox(
        "Asse X",
        options=dim_cols + ['ptof_orientamento_maturity_index', 'partnership_count'],
        format_func=get_label,
        index=0
    )

with col2:
    y_metric = st.selectbox(
        "Asse Y",
        options=dim_cols + ['ptof_orientamento_maturity_index', 'partnership_count'],
        format_func=get_label,
        index=2
    )

if x_metric in df_valid.columns and y_metric in df_valid.columns:
    df_quad = df_valid[[x_metric, y_metric, 'denominazione', 'tipo_scuola', 'area_geografica']].dropna().copy()
    
    if len(df_quad) > 0:
        x_median = df_quad[x_metric].median()
        y_median = df_quad[y_metric].median()
        
        # Assign quadrants
        def get_quadrant(row):
            if row[x_metric] >= x_median and row[y_metric] >= y_median:
                return '⭐ Eccellenti (Alto-Alto)'
            elif row[x_metric] < x_median and row[y_metric] >= y_median:
                return '🎯 Focalizzati su Y'
            elif row[x_metric] >= x_median and row[y_metric] < y_median:
                return '📈 Focalizzati su X'
            else:
                return '⚠️ Da Migliorare'
        
        df_quad['Quadrante'] = df_quad.apply(get_quadrant, axis=1)
        
        # Scatter plot
        fig_quad = px.scatter(
            df_quad, x=x_metric, y=y_metric,
            color='Quadrante',
            hover_name='denominazione',
            hover_data={'tipo_scuola': True, 'area_geografica': True},
            color_discrete_map={
                '⭐ Eccellenti (Alto-Alto)': '#28a745',
                '🎯 Focalizzati su Y': '#ffc107',
                '📈 Focalizzati su X': '#17a2b8',
                '⚠️ Da Migliorare': '#dc3545'
            },
            title=f"Quadrante: {get_label(x_metric)} vs {get_label(y_metric)}"
        )
        
        # Add median lines
        fig_quad.add_hline(y=y_median, line_dash="dash", line_color="gray", opacity=0.5)
        fig_quad.add_vline(x=x_median, line_dash="dash", line_color="gray", opacity=0.5)
        
        # Add quadrant labels
        fig_quad.add_annotation(x=df_quad[x_metric].max(), y=df_quad[y_metric].max(), 
                               text="⭐ Eccellenti", showarrow=False, font=dict(size=12))
        fig_quad.add_annotation(x=df_quad[x_metric].min(), y=df_quad[y_metric].min(), 
                               text="⚠️ Da Migliorare", showarrow=False, font=dict(size=12))
        
        fig_quad.update_layout(height=550)
        st.plotly_chart(fig_quad, use_container_width=True)
        
        # Quadrant summary
        quad_counts = df_quad['Quadrante'].value_counts()
        col1, col2, col3, col4 = st.columns(4)
        
        quadrants = ['⭐ Eccellenti (Alto-Alto)', '🎯 Focalizzati su Y', '📈 Focalizzati su X', '⚠️ Da Migliorare']
        cols = [col1, col2, col3, col4]
        
        for q, c in zip(quadrants, cols):
            with c:
                count = quad_counts.get(q, 0)
                pct = count / len(df_quad) * 100
                st.metric(q.split(' ')[0], f"{count} ({pct:.0f}%)")
else:
    st.warning("Metriche selezionate non disponibili")

st.markdown("---")

# === 6. BENCHMARK PER TIPO SCUOLA ===
st.subheader("📊 Benchmark per Tipologia")
st.caption("Confronto delle medie per ciascuna tipologia scolastica")

if 'tipo_primario' in df_valid.columns:
    tipo_stats = df_valid.groupby('tipo_primario').agg({
        'ptof_orientamento_maturity_index': ['mean', 'std', 'count'],
        **{c: 'mean' for c in dim_cols if c in df_valid.columns}
    }).round(2)
    
    tipo_stats.columns = ['_'.join(col).strip() for col in tipo_stats.columns.values]
    tipo_stats = tipo_stats.reset_index()
    
    # Bar chart comparison
    fig_tipo = px.bar(
        tipo_stats, x='tipo_primario', 
        y='ptof_orientamento_maturity_index_mean',
        error_y='ptof_orientamento_maturity_index_std',
        color='ptof_orientamento_maturity_index_mean',
        color_continuous_scale='RdYlGn',
        range_color=[1, 7],
        title="Indice Medio per Tipologia Scolastica",
        labels={'tipo_primario': 'Tipologia', 'ptof_orientamento_maturity_index_mean': 'Indice Medio'},
        text='ptof_orientamento_maturity_index_mean'
    )
    fig_tipo.update_traces(texttemplate='%{text:.2f}', textposition='outside')
    fig_tipo.update_layout(height=400)
    st.plotly_chart(fig_tipo, use_container_width=True)

# Footer
st.markdown("---")
st.caption("🏆 Benchmark - Dashboard PTOF | Analisi comparativa delle performance scolastiche")
