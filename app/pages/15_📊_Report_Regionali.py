# 📊 Report Regionali - Sintesi per USR

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import os
from io import BytesIO
from scipy import stats

# Import tipologie standard
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from data_utils import TIPI_SCUOLA, explode_school_types

st.set_page_config(page_title="Report Regionali", page_icon="📊", layout="wide")


# === FUNZIONI STATISTICHE ===
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


def dunn_posthoc(df, group_col, score_col):
    """
    Test post-hoc di Dunn con correzione Bonferroni.
    Restituisce un DataFrame con i confronti a coppie significativi.
    """
    from itertools import combinations

    try:
        # Raggruppa i dati
        groups_data = {}
        for name, group in df.groupby(group_col):
            values = group[score_col].dropna().values
            if len(values) >= 2:
                groups_data[name] = values

        if len(groups_data) < 2:
            return None

        group_names = list(groups_data.keys())
        n_comparisons = len(list(combinations(group_names, 2)))

        results = []
        for g1, g2 in combinations(group_names, 2):
            # Mann-Whitney U test per ogni coppia
            stat, p_val = stats.mannwhitneyu(
                groups_data[g1], groups_data[g2], alternative='two-sided'
            )
            # Correzione Bonferroni
            p_adj = min(p_val * n_comparisons, 1.0)

            # Effect size: r = Z / sqrt(N)
            n1, n2 = len(groups_data[g1]), len(groups_data[g2])
            z = stats.norm.ppf(1 - p_val / 2) if p_val > 0 else 0
            r = abs(z) / np.sqrt(n1 + n2)

            # Media dei gruppi
            mean1 = np.mean(groups_data[g1])
            mean2 = np.mean(groups_data[g2])

            results.append({
                'Gruppo 1': g1,
                'Gruppo 2': g2,
                'Media 1': round(mean1, 2),
                'Media 2': round(mean2, 2),
                'Diff': round(mean1 - mean2, 2),
                'p-value': round(p_val, 4),
                'p-adj (Bonf.)': round(p_adj, 4),
                'Effect (r)': round(r, 3),
                'Significativo': '✓' if p_adj < 0.05 else ''
            })

        return pd.DataFrame(results)
    except Exception as e:
        return None


def interpret_effect_size(value):
    """Interpreta l'effect size (eta-squared)."""
    if value is None:
        return "N/D", "gray"
    if value < 0.01:
        return "Trascurabile", "gray"
    elif value < 0.06:
        return "Piccolo", "orange"
    elif value < 0.14:
        return "Medio", "blue"
    else:
        return "Grande", "green"


def interpret_r_effect(r):
    """Interpreta l'effect size r (per Mann-Whitney)."""
    if r is None:
        return "N/D"
    if r < 0.1:
        return "Trascurabile"
    elif r < 0.3:
        return "Piccolo"
    elif r < 0.5:
        return "Medio"
    else:
        return "Grande"


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

SUMMARY_FILE = 'data/analysis_summary.csv'

@st.cache_data(ttl=60)
def load_data():
    if os.path.exists(SUMMARY_FILE):
        df = pd.read_csv(SUMMARY_FILE)
        # Convert numeric columns
        numeric_cols = ['ptof_orientamento_maturity_index', 'mean_finalita', 'mean_obiettivi', 
                        'mean_governance', 'mean_didattica_orientativa', 'mean_opportunita']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        return df
    return pd.DataFrame()

df = load_data()

st.title("📊 Report Regionali per USR")

with st.expander("📖 Come usare questa pagina", expanded=False):
    st.markdown("""
    ### 🎯 Scopo della Pagina
    Genera **report sintetici regionali** per gli Uffici Scolastici Regionali (USR).
    
    ### 📊 Cosa include il report
    - Statistiche descrittive regionali
    - Confronto con la media nazionale
    - Distribuzione per tipologia di scuola
    - Scuole eccellenti e scuole da supportare
    - Dimensioni con maggiore margine di miglioramento
    
    ### 💾 Export
    - Possibilità di scaricare il report in formato Excel o CSV
    """)

if df.empty:
    st.warning("⚠️ Nessun dato disponibile.")
    st.stop()

st.markdown("---")

# Region selector
regions = sorted(df['regione'].dropna().unique().tolist())
regions = [r for r in regions if r and r not in ['', 'ND', 'Non Specificato']]

if not regions:
    st.warning("Nessuna regione disponibile nei dati.")
    st.stop()

selected_region = st.selectbox("🗺️ Seleziona Regione", regions, key="region_select")

if selected_region:
    df_region = df[df['regione'] == selected_region].copy()
    df_national = df.copy()
    
    st.markdown(f"## 📋 Report: {selected_region}")
    st.markdown("---")
    
    # === METRICHE PRINCIPALI ===
    st.subheader("📈 Statistiche Chiave")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        n_schools = len(df_region)
        st.metric("🏫 N. Scuole Analizzate", n_schools)
    
    with col2:
        mean_ro = df_region['ptof_orientamento_maturity_index'].mean()
        national_mean = df_national['ptof_orientamento_maturity_index'].mean()
        delta = mean_ro - national_mean
        st.metric("📊 Indice RO Medio", f"{mean_ro:.2f}", 
                  delta=f"{delta:+.2f} vs nazionale",
                  delta_color="normal" if delta >= 0 else "inverse")
    
    with col3:
        std_ro = df_region['ptof_orientamento_maturity_index'].std()
        st.metric("📐 Dev. Standard", f"{std_ro:.2f}")
    
    with col4:
        # Percentuale nel top 30% nazionale
        threshold_30 = df_national['ptof_orientamento_maturity_index'].quantile(0.70)
        pct_top = (df_region['ptof_orientamento_maturity_index'] >= threshold_30).mean() * 100
        st.metric("🏆 % nel Top 30%", f"{pct_top:.1f}%")
    
    st.markdown("---")
    
    # === CONFRONTO CON NAZIONALE ===
    st.subheader("🔄 Confronto con Media Nazionale")
    
    dim_cols = ['mean_finalita', 'mean_obiettivi', 'mean_governance', 
                'mean_didattica_orientativa', 'mean_opportunita']
    dim_labels = ['Finalità', 'Obiettivi', 'Governance', 'Didattica', 'Opportunità']
    
    if all(c in df.columns for c in dim_cols):
        comparison_data = []
        for col, label in zip(dim_cols, dim_labels):
            regional = df_region[col].mean()
            national = df_national[col].mean()
            diff = regional - national
            comparison_data.append({
                'Dimensione': label,
                'Regione': regional,
                'Nazionale': national,
                'Differenza': diff
            })
        
        comparison_df = pd.DataFrame(comparison_data)
        
        col_chart, col_table = st.columns([2, 1])
        
        with col_chart:
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                name=selected_region,
                x=comparison_df['Dimensione'],
                y=comparison_df['Regione'],
                marker_color='#3498db'
            ))
            
            fig.add_trace(go.Bar(
                name='Media Nazionale',
                x=comparison_df['Dimensione'],
                y=comparison_df['Nazionale'],
                marker_color='#95a5a6'
            ))
            
            fig.update_layout(
                barmode='group',
                title=f"Confronto {selected_region} vs Media Nazionale",
                yaxis_title="Punteggio",
                yaxis_range=[0, 7]
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with col_table:
            st.markdown("#### Dettaglio Differenze")
            display_df = comparison_df.copy()
            display_df['Regione'] = display_df['Regione'].round(2)
            display_df['Nazionale'] = display_df['Nazionale'].round(2)
            display_df['Differenza'] = display_df['Differenza'].apply(lambda x: f"{x:+.2f}")
            st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    # === DISTRIBUZIONE PER TIPOLOGIA ===
    st.subheader("🏫 Distribuzione per Tipologia")
    st.caption("Tipologie: Infanzia, Primaria, I Grado, Liceo, Tecnico, Professionale")

    if 'tipo_scuola' in df_region.columns:
        # Esplodi le scuole con tipologie multiple (es. "Liceo, Tecnico")
        df_region_exploded = explode_school_types(df_region.copy(), 'tipo_scuola')

        # Filtra solo le 6 tipologie standard
        df_region_exploded = df_region_exploded[
            df_region_exploded['tipo_scuola'].isin(TIPI_SCUOLA)
        ]

        if not df_region_exploded.empty:
            tipo_stats = df_region_exploded.groupby('tipo_scuola').agg({
                'ptof_orientamento_maturity_index': ['count', 'mean', 'std', 'min', 'max']
            }).round(2)
            tipo_stats.columns = ['N. Scuole', 'Media', 'Dev. Std', 'Min', 'Max']
            tipo_stats = tipo_stats.reset_index()
            tipo_stats.columns = ['Tipologia'] + list(tipo_stats.columns[1:])

            # Ordina secondo l'ordine standard delle tipologie
            tipo_order = {t: i for i, t in enumerate(TIPI_SCUOLA)}
            tipo_stats['_order'] = tipo_stats['Tipologia'].map(tipo_order)
            tipo_stats = tipo_stats.sort_values('_order').drop('_order', axis=1)

            col_pie, col_bar = st.columns([1, 2])

            with col_pie:
                fig_pie = px.pie(
                    tipo_stats,
                    values='N. Scuole',
                    names='Tipologia',
                    title="Distribuzione Scuole",
                    category_orders={'Tipologia': TIPI_SCUOLA}
                )
                st.plotly_chart(fig_pie, use_container_width=True)

            with col_bar:
                fig_tipo = px.bar(
                    tipo_stats.sort_values('Media', ascending=True),
                    x='Media',
                    y='Tipologia',
                    orientation='h',
                    color='Media',
                    color_continuous_scale='RdYlGn',
                    range_x=[0, 7],
                    title="Indice RO per Tipologia"
                )
                st.plotly_chart(fig_tipo, use_container_width=True)

            st.dataframe(tipo_stats, use_container_width=True, hide_index=True)

            # === TEST STATISTICI ===
            # Kruskal-Wallis test per differenze tra tipologie
            p_val, eta_sq = kruskal_test_scores(
                df_region_exploded, 'tipo_scuola', 'ptof_orientamento_maturity_index'
            )
            sig_text, sig_color = format_significance(p_val)
            eff_text, eff_color = interpret_effect_size(eta_sq)

            col_sig, col_eff = st.columns(2)
            with col_sig:
                st.markdown(f"**📈 Significatività (Kruskal-Wallis):** :{sig_color}[{sig_text}]")
            with col_eff:
                if eta_sq is not None:
                    st.markdown(f"**📏 Effect Size (η²):** :{eff_color}[{eta_sq:.3f} - {eff_text}]")
                else:
                    st.markdown(f"**📏 Effect Size (η²):** :gray[N/D]")

            # === POST-HOC se significativo ===
            if p_val is not None and p_val < 0.05:
                st.markdown("#### 🔍 Confronti Post-Hoc (Dunn con correzione Bonferroni)")

                posthoc_df = dunn_posthoc(
                    df_region_exploded, 'tipo_scuola', 'ptof_orientamento_maturity_index'
                )

                if posthoc_df is not None and not posthoc_df.empty:
                    # Filtra solo confronti significativi per visualizzazione compatta
                    significant_only = posthoc_df[posthoc_df['Significativo'] == '✓']

                    if not significant_only.empty:
                        st.markdown("**Confronti significativi (p-adj < 0.05):**")
                        for _, row in significant_only.iterrows():
                            diff_sign = ">" if row['Diff'] > 0 else "<"
                            r_interp = interpret_r_effect(row['Effect (r)'])
                            st.markdown(
                                f"- **{row['Gruppo 1']}** ({row['Media 1']}) {diff_sign} "
                                f"**{row['Gruppo 2']}** ({row['Media 2']}) — "
                                f"Δ = {row['Diff']:+.2f}, r = {row['Effect (r)']:.2f} ({r_interp})"
                            )
                    else:
                        st.info("Nessun confronto a coppie significativo dopo correzione Bonferroni.")

                    with st.expander("📊 Tabella completa confronti a coppie"):
                        st.dataframe(posthoc_df, use_container_width=True, hide_index=True)
                else:
                    st.info("Non è stato possibile calcolare i confronti post-hoc.")

            with st.expander("ℹ️ Interpretazione test statistici"):
                st.markdown("""
                **Test Kruskal-Wallis**: verifica se esistono differenze significative tra le tipologie scolastiche.
                - `p < 0.05`: differenze statisticamente significative
                - `p ≥ 0.05 (n.s.)`: differenze non significative

                **Effect Size (η² - Eta-squared)**: misura la dimensione dell'effetto globale.
                - < 0.01: Trascurabile
                - 0.01 - 0.06: Piccolo
                - 0.06 - 0.14: Medio
                - > 0.14: Grande

                **Test Post-Hoc (Dunn)**: se Kruskal-Wallis è significativo, identifica quali coppie di tipologie differiscono.
                - Usa correzione Bonferroni per controllare l'errore di tipo I
                - Effect size r (per coppia): < 0.1 Trascurabile, 0.1-0.3 Piccolo, 0.3-0.5 Medio, > 0.5 Grande
                """)
        else:
            st.info("Nessuna scuola con tipologia valida nella regione selezionata.")
    
    st.markdown("---")
    
    # === TOP 10 E BOTTOM 10 ===
    col_top, col_bottom = st.columns(2)
    
    with col_top:
        st.subheader("🏆 Top 10 Scuole")
        top_10 = df_region.nlargest(10, 'ptof_orientamento_maturity_index')[
            ['denominazione', 'comune', 'tipo_scuola', 'ptof_orientamento_maturity_index']
        ].copy()
        top_10.columns = ['Denominazione', 'Comune', 'Tipo', 'Indice RO']
        top_10['Indice RO'] = top_10['Indice RO'].round(2)
        st.dataframe(top_10, use_container_width=True, hide_index=True)
    
    with col_bottom:
        st.subheader("📉 Bottom 10 (da supportare)")
        bottom_10 = df_region.nsmallest(10, 'ptof_orientamento_maturity_index')[
            ['denominazione', 'comune', 'tipo_scuola', 'ptof_orientamento_maturity_index']
        ].copy()
        bottom_10.columns = ['Denominazione', 'Comune', 'Tipo', 'Indice RO']
        bottom_10['Indice RO'] = bottom_10['Indice RO'].round(2)
        st.dataframe(bottom_10, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    # === AREE DI MIGLIORAMENTO ===
    st.subheader("🎯 Aree Prioritarie di Miglioramento")
    
    if all(c in df_region.columns for c in dim_cols):
        dim_means = [(label, df_region[col].mean()) for col, label in zip(dim_cols, dim_labels)]
        dim_means_sorted = sorted(dim_means, key=lambda x: x[1])
        
        st.markdown("Le dimensioni con i punteggi più bassi a livello regionale:")
        
        for i, (dim, score) in enumerate(dim_means_sorted[:3], 1):
            color = "#e74c3c" if score < 3.5 else "#f39c12" if score < 4.5 else "#2ecc71"
            st.markdown(f"""
            <div style="padding: 10px; background-color: {color}22; border-left: 4px solid {color}; margin: 5px 0;">
                <b>{i}. {dim}</b>: Media regionale = {score:.2f}/7
            </div>
            """, unsafe_allow_html=True)
        
        st.info("""
💡 **Suggerimenti per USR**:
- Organizzare formazione mirata sulle dimensioni più deboli
- Favorire lo scambio di buone pratiche tra scuole virtuose e scuole in difficoltà
- Creare reti territoriali tematiche (es. rete per la Governance, rete per le Partnership)
""")
    
    st.markdown("---")
    
    # === EXPORT ===
    st.subheader("💾 Esporta Report")
    
    col_exp1, col_exp2, col_exp3 = st.columns(3)
    
    with col_exp1:
        # Export regione CSV
        csv_buffer = df_region.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Dati Regione (CSV)",
            data=csv_buffer,
            file_name=f"report_{selected_region.replace(' ', '_')}.csv",
            mime="text/csv"
        )
    
    with col_exp2:
        # Export regione Excel
        try:
            excel_buffer = BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                df_region.to_excel(writer, sheet_name='Dati', index=False)
                
                # Summary sheet
                summary_data = {
                    'Metrica': ['N. Scuole', 'Indice RO Medio', 'Dev. Standard', 
                                '% nel Top 30% Nazionale', 'Migliore Scuola', 'Scuola da Supportare'],
                    'Valore': [
                        len(df_region),
                        round(df_region['ptof_orientamento_maturity_index'].mean(), 2),
                        round(df_region['ptof_orientamento_maturity_index'].std(), 2),
                        f"{pct_top:.1f}%",
                        df_region.loc[df_region['ptof_orientamento_maturity_index'].idxmax(), 'denominazione'],
                        df_region.loc[df_region['ptof_orientamento_maturity_index'].idxmin(), 'denominazione']
                    ]
                }
                pd.DataFrame(summary_data).to_excel(writer, sheet_name='Sintesi', index=False)
                
                if 'comparison_df' in dir():
                    comparison_df.to_excel(writer, sheet_name='Confronto', index=False)
                
            excel_buffer.seek(0)
            st.download_button(
                label="📥 Report Excel",
                data=excel_buffer,
                file_name=f"report_{selected_region.replace(' ', '_')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except ImportError:
            st.warning("Installa openpyxl per export Excel: `pip install openpyxl`")
    
    with col_exp3:
        # Summary text
        summary_text = f"""
REPORT REGIONALE - {selected_region}
{'='*50}

STATISTICHE CHIAVE
- Scuole analizzate: {len(df_region)}
- Indice RO medio: {df_region['ptof_orientamento_maturity_index'].mean():.2f}
- Deviazione standard: {df_region['ptof_orientamento_maturity_index'].std():.2f}
- % scuole nel top 30% nazionale: {pct_top:.1f}%

CONFRONTO CON MEDIA NAZIONALE
- Differenza dall'indice nazionale: {delta:+.2f}

TOP 5 SCUOLE
"""
        for _, row in top_10.head(5).iterrows():
            summary_text += f"- {row['Denominazione']} ({row['Comune']}): {row['Indice RO']}\n"
        
        st.download_button(
            label="📥 Sintesi (TXT)",
            data=summary_text.encode('utf-8'),
            file_name=f"sintesi_{selected_region.replace(' ', '_')}.txt",
            mime="text/plain"
        )

st.markdown("---")

# === CONFRONTO TRA REGIONI ===
st.subheader("🔄 Confronto Tra Regioni")

col_compare = st.multiselect("Seleziona regioni da confrontare", regions, default=[selected_region])

if len(col_compare) >= 2:
    df_compare = df[df['regione'].isin(col_compare)].copy()
    
    # Radar comparison
    if all(c in df.columns for c in dim_cols):
        fig_radar = go.Figure()
        
        colors = px.colors.qualitative.Set2
        
        for i, region in enumerate(col_compare):
            region_data = df_compare[df_compare['regione'] == region]
            values = [region_data[col].mean() for col in dim_cols]
            values.append(values[0])
            
            labels = dim_labels + [dim_labels[0]]
            
            fig_radar.add_trace(go.Scatterpolar(
                r=values,
                theta=labels,
                fill='toself',
                name=region,
                line_color=colors[i % len(colors)],
                opacity=0.7
            ))
        
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(range=[0, 7])),
            title="Confronto Profilo Dimensionale",
            height=500
        )
        
        st.plotly_chart(fig_radar, use_container_width=True)
    
    # Box plot comparison
    fig_box = px.box(
        df_compare,
        x='regione',
        y='ptof_orientamento_maturity_index',
        color='regione',
        title="Distribuzione Indice RO per Regione"
    )
    fig_box.update_layout(showlegend=False, yaxis_range=[0, 7])
    st.plotly_chart(fig_box, use_container_width=True)
else:
    st.info("Seleziona almeno 2 regioni per il confronto.")

st.markdown("---")
st.caption("📊 Report Regionali - Dashboard PTOF | Generazione report per Uffici Scolastici Regionali")
