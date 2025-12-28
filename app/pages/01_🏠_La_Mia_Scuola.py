# 🏠 La Mia Scuola - Dashboard Personalizzato

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import json
import glob
from data_utils import render_footer
from page_control import setup_page, switch_page

st.set_page_config(page_title="ORIENTA+ | La Mia Scuola", page_icon="🧭", layout="wide")
setup_page("pages/01_🏠_La_Mia_Scuola.py")

# CSS
st.markdown("""
<style>
    .my-school-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 30px;
        border-radius: 20px;
        color: white;
        text-align: center;
        margin-bottom: 20px;
    }
    .kpi-card {
        background: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        text-align: center;
    }
    .position-badge {
        font-size: 2em;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

SUMMARY_FILE = 'data/analysis_summary.csv'

DIMENSIONS = {
    'mean_finalita': 'Finalità',
    'mean_obiettivi': 'Obiettivi',
    'mean_governance': 'Governance',
    'mean_didattica_orientativa': 'Didattica Orientativa',
    'mean_opportunita': 'Opportunità'
}


@st.cache_data(ttl=60)
def load_data():
    if os.path.exists(SUMMARY_FILE):
        df = pd.read_csv(SUMMARY_FILE)
        num_cols = list(DIMENSIONS.keys()) + ['ptof_orientamento_maturity_index', 'partnership_count']
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        return df
    return pd.DataFrame()


def find_peer_schools_simple(target_school, df, top_n=5):
    """Trova scuole peer simili (versione semplificata)."""
    peers = []
    target_tipo = str(target_school.get('tipo_scuola', '')).split(',')[0].strip()
    target_regione = target_school.get('regione', '')

    for idx, school in df.iterrows():
        if school['school_id'] == target_school['school_id']:
            continue

        score = 0
        # Stesso tipo
        if target_tipo and target_tipo in str(school.get('tipo_scuola', '')):
            score += 40
        # Stessa regione
        if target_regione and school.get('regione') == target_regione:
            score += 30
        # Stesso territorio
        if target_school.get('territorio') == school.get('territorio'):
            score += 15
        # Stessa gestione
        if target_school.get('statale_paritaria') == school.get('statale_paritaria'):
            score += 15

        peers.append({
            'school_id': school['school_id'],
            'denominazione': school['denominazione'],
            'regione': school.get('regione', ''),
            'tipo_scuola': school.get('tipo_scuola', ''),
            'indice_ro': school.get('ptof_orientamento_maturity_index', 0),
            'similarity_score': score,
            **{col: school.get(col, 0) for col in DIMENSIONS.keys()}
        })

    return sorted(peers, key=lambda x: x['similarity_score'], reverse=True)[:top_n]


# === CARICAMENTO DATI ===
df = load_data()

st.title("🏠 La Mia Scuola")

if df.empty:
    st.warning("Nessun dato disponibile")
    st.stop()

# === SELEZIONE E PERSISTENZA SCUOLA ===
st.markdown("""
Seleziona la tua scuola per visualizzare una dashboard personalizzata.
La selezione verrà ricordata durante la sessione.
""")

# Recupera scuola salvata
saved_school_id = st.session_state.get('my_school_id', None)
saved_school_name = st.session_state.get('my_school_name', None)

# Ricerca
search_query = st.text_input("🔍 Cerca la tua scuola", placeholder="Nome, codice o comune...")

if search_query:
    search_upper = search_query.upper()
    filtered_df = df[
        df['school_id'].str.upper().str.contains(search_upper, na=False) |
        df['denominazione'].str.upper().str.contains(search_upper, na=False) |
        df['comune'].astype(str).str.upper().str.contains(search_upper, na=False)
    ]
    school_options = filtered_df['denominazione'].dropna().unique().tolist()
    st.caption(f"Trovate: {len(school_options)} scuole")
else:
    school_options = df['denominazione'].dropna().unique().tolist()

# Selectbox con valore salvato
if saved_school_name and saved_school_name in school_options:
    default_idx = school_options.index(saved_school_name)
else:
    default_idx = 0

selected_school_name = st.selectbox(
    "Seleziona la tua scuola",
    school_options,
    index=default_idx,
    key="my_school_selector"
)

# Pulsante per salvare
col_save, col_clear = st.columns([1, 1])

with col_save:
    if st.button("💾 Imposta come Mia Scuola", type="primary", use_container_width=True):
        school_row = df[df['denominazione'] == selected_school_name].iloc[0]
        st.session_state['my_school_id'] = school_row['school_id']
        st.session_state['my_school_name'] = selected_school_name
        st.success(f"✅ '{selected_school_name}' impostata come tua scuola!")
        st.rerun()

with col_clear:
    if saved_school_name:
        if st.button("🗑️ Rimuovi selezione", use_container_width=True):
            del st.session_state['my_school_id']
            del st.session_state['my_school_name']
            st.info("Selezione rimossa")
            st.rerun()

# Se non c'è una scuola salvata, mostra istruzioni
if not saved_school_name:
    st.info("👆 Cerca e seleziona la tua scuola, poi clicca 'Imposta come Mia Scuola' per salvare la selezione")
    st.stop()

# === CARICA DATI SCUOLA ===
my_school = df[df['school_id'] == saved_school_id].iloc[0]

st.markdown("---")

# === HEADER PERSONALIZZATO ===
ro_index = my_school.get('ptof_orientamento_maturity_index', 0) or 0
percentile = (df['ptof_orientamento_maturity_index'] < ro_index).mean() * 100

st.markdown(f"""
<div class="my-school-header">
    <h1 style="margin:0; font-size: 1.8em;">{my_school['denominazione']}</h1>
    <p style="margin: 10px 0; opacity: 0.9;">
        {my_school.get('comune', 'N/D')} ({my_school.get('provincia', 'N/D')}) - {my_school.get('regione', 'N/D')}
    </p>
    <p style="margin: 5px 0; opacity: 0.8;">
        {my_school.get('tipo_scuola', 'N/D')} | {my_school.get('statale_paritaria', 'N/D')}
    </p>
    <div style="margin-top: 20px;">
        <span style="font-size: 3em; font-weight: bold;">{ro_index:.2f}</span>
        <span style="font-size: 1.2em;">/7</span>
    </div>
    <p style="margin: 5px 0;">Indice di Robustezza Orientamento</p>
</div>
""", unsafe_allow_html=True)

# === KPI PRINCIPALI ===
st.subheader("📊 I Tuoi Numeri")

kpi_cols = st.columns(5)

# Posizione in classifica
df_sorted = df.sort_values('ptof_orientamento_maturity_index', ascending=False).reset_index(drop=True)
position = df_sorted[df_sorted['school_id'] == saved_school_id].index[0] + 1
total_schools = len(df)

with kpi_cols[0]:
    st.metric("🏆 Posizione", f"#{position}", f"su {total_schools}")

with kpi_cols[1]:
    st.metric("📈 Percentile", f"{percentile:.0f}°")

with kpi_cols[2]:
    mean_ro = df['ptof_orientamento_maturity_index'].mean()
    delta = ro_index - mean_ro
    st.metric("📊 vs Media", f"{mean_ro:.2f}", f"{delta:+.2f}")

with kpi_cols[3]:
    partnership_count = int(my_school.get('partnership_count', 0) or 0)
    st.metric("🤝 Partnership", partnership_count)

with kpi_cols[4]:
    # Calcola quante scuole superi nella tua regione
    region_df = df[df['regione'] == my_school.get('regione')]
    region_position = (region_df['ptof_orientamento_maturity_index'] < ro_index).sum() + 1
    st.metric("🗺️ In Regione", f"#{region_position}", f"su {len(region_df)}")

st.markdown("---")

# === PROFILO E CONFRONTO ===
col_radar, col_gaps = st.columns([1, 1])

with col_radar:
    st.subheader("🕸️ Il Tuo Profilo")

    # Dati
    my_vals = [my_school.get(d, 0) or 0 for d in DIMENSIONS.keys()]
    avg_vals = [df[d].mean() for d in DIMENSIONS.keys()]
    labels = list(DIMENSIONS.values())

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=my_vals + [my_vals[0]],
        theta=labels + [labels[0]],
        fill='toself',
        name='La Mia Scuola',
        line_color='#667eea',
        fillcolor='rgba(102, 126, 234, 0.3)'
    ))

    fig.add_trace(go.Scatterpolar(
        r=avg_vals + [avg_vals[0]],
        theta=labels + [labels[0]],
        fill='toself',
        name='Media Nazionale',
        line_color='#95a5a6',
        fillcolor='rgba(149, 165, 166, 0.2)'
    ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 7])),
        showlegend=True,
        height=400
    )
    st.plotly_chart(fig, use_container_width=True)

with col_gaps:
    st.subheader("🎯 Le Tue Priorità")

    gaps = []
    for dim_col, dim_label in DIMENSIONS.items():
        val = my_school.get(dim_col, 0) or 0
        mean_val = df[dim_col].mean()
        gap = mean_val - val
        gaps.append({
            'Dimensione': dim_label,
            'Punteggio': val,
            'Media': mean_val,
            'Gap': gap
        })

    gaps_df = pd.DataFrame(gaps)
    gaps_df = gaps_df.sort_values('Gap', ascending=False)

    # Mostra aree prioritarie
    for i, row in gaps_df.head(3).iterrows():
        if row['Gap'] > 0:
            color = "#e74c3c" if row['Gap'] > 1 else "#f39c12" if row['Gap'] > 0.5 else "#3498db"
            st.markdown(f"""
            <div style="background: {color}; padding: 15px; border-radius: 10px;
                        color: white; margin-bottom: 10px;">
                <strong>{row['Dimensione']}</strong><br>
                Tuo: {row['Punteggio']:.1f} | Media: {row['Media']:.1f} | Gap: {row['Gap']:+.1f}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="background: #27ae60; padding: 15px; border-radius: 10px;
                        color: white; margin-bottom: 10px;">
                <strong>✅ {row['Dimensione']}</strong><br>
                Tuo: {row['Punteggio']:.1f} | Media: {row['Media']:.1f} | Sopra media!
            </div>
            """, unsafe_allow_html=True)

    # Tabella completa
    with st.expander("📊 Dettaglio tutte le dimensioni"):
        for dim_col, dim_label in DIMENSIONS.items():
            val = my_school.get(dim_col, 0) or 0
            mean_val = df[dim_col].mean()
            delta = val - mean_val
            st.metric(dim_label, f"{val:.2f}/7", f"{delta:+.2f} vs media")

st.markdown("---")

# === SCUOLE PEER ===
st.subheader("👥 Le Tue Scuole Peer")

st.markdown("Scuole simili a te per tipologia, territorio e gestione:")

peers = find_peer_schools_simple(my_school, df, top_n=5)
peers_df = pd.DataFrame(peers)

if not peers_df.empty:
    # Statistiche peer
    peer_cols = st.columns(4)

    with peer_cols[0]:
        peer_mean = peers_df['indice_ro'].mean()
        st.metric("Media Peer", f"{peer_mean:.2f}")

    with peer_cols[1]:
        vs_peer = ro_index - peer_mean
        st.metric("Tu vs Peer", f"{vs_peer:+.2f}")

    with peer_cols[2]:
        rank_in_peer = (peers_df['indice_ro'] < ro_index).sum() + 1
        st.metric("Posizione Peer", f"#{rank_in_peer}/5")

    with peer_cols[3]:
        best_peer = peers_df.loc[peers_df['indice_ro'].idxmax()]
        st.metric("Best Peer", f"{best_peer['indice_ro']:.2f}")

    st.markdown("---")

    # Lista peer
    for i, peer in peers_df.iterrows():
        col_peer_info, col_peer_radar = st.columns([2, 1])

        with col_peer_info:
            delta_peer = peer['indice_ro'] - ro_index
            icon = "📈" if delta_peer > 0 else "📉" if delta_peer < 0 else "="

            st.markdown(f"""
            **{peer['denominazione']}** {icon}
            - Regione: {peer['regione']}
            - Tipo: {peer['tipo_scuola']}
            - Indice RO: **{peer['indice_ro']:.2f}** ({delta_peer:+.2f} vs te)
            - Similarità: {peer['similarity_score']}%
            """)

        with col_peer_radar:
            # Mini radar
            peer_vals = [peer.get(d, 0) or 0 for d in DIMENSIONS.keys()]

            fig_mini = go.Figure()
            fig_mini.add_trace(go.Scatterpolar(
                r=my_vals + [my_vals[0]],
                theta=labels + [labels[0]],
                fill='toself', name='Tu',
                line_color='#667eea', opacity=0.6
            ))
            fig_mini.add_trace(go.Scatterpolar(
                r=peer_vals + [peer_vals[0]],
                theta=labels + [labels[0]],
                fill='toself', name='Peer',
                line_color='#2ecc71', opacity=0.6
            ))
            fig_mini.update_layout(
                polar=dict(radialaxis=dict(range=[0, 7], showticklabels=False)),
                showlegend=False,
                height=150,
                margin=dict(l=20, r=20, t=20, b=20)
            )
            st.plotly_chart(fig_mini, use_container_width=True)

        st.markdown("---")

else:
    st.info("Nessuna scuola peer trovata")

# === QUICK ACTIONS ===
st.subheader("🚀 Azioni Rapide")

action_cols = st.columns(4)

with action_cols[0]:
    if st.button("📊 Vai a Dettaglio Scuola", use_container_width=True):
        st.session_state['selected_school_name'] = saved_school_name
        switch_page("pages/02_🏫_Dettaglio_Scuola.py")

with action_cols[1]:
    if st.button("🔍 Trova Scuole Simili", use_container_width=True):
        st.session_state['selected_school_name'] = saved_school_name
        switch_page("pages/02_🏫_Dettaglio_Scuola.py")

with action_cols[2]:
    if st.button("🔀 Confronta con altra Scuola", use_container_width=True):
        switch_page("pages/09_🔀_Confronto_PTOF.py")

with action_cols[3]:
    if st.button("💡 Cerca Best Practice", use_container_width=True):
        switch_page("pages/10_🔍_Ricerca_Metodologie.py")

st.markdown("---")

# === INSIGHTS PERSONALIZZATI ===
st.subheader("💡 Insights per Te")

insights = []

# Insight su posizione
if percentile >= 75:
    insights.append("🏆 **Eccellente!** Sei nel top 25% delle scuole italiane per Robustezza dell'Orientamento")
elif percentile >= 50:
    insights.append("✅ **Buono!** Sei sopra la mediana nazionale. Con qualche miglioramento puoi entrare nel top quartile")
elif percentile >= 25:
    insights.append("⚠️ **Attenzione:** Sei sotto la mediana nazionale. Ci sono margini di miglioramento significativi")
else:
    insights.append("🔴 **Priorità alta:** Sei nel quartile inferiore. Consigliamo un piano di miglioramento strutturato")

# Insight su dimensioni
best_dim = max(gaps, key=lambda x: x['Punteggio'])
worst_dim = min(gaps, key=lambda x: x['Punteggio'])

insights.append(f"💪 **Punto di forza:** {best_dim['Dimensione']} ({best_dim['Punteggio']:.1f}/7)")
if worst_dim['Punteggio'] < 4:
    insights.append(f"📉 **Area critica:** {worst_dim['Dimensione']} ({worst_dim['Punteggio']:.1f}/7) - richiede attenzione")

# Insight su peer
if not peers_df.empty:
    if vs_peer > 0.5:
        insights.append("📈 **Rispetto ai peer:** Sei significativamente sopra la media del tuo gruppo di riferimento")
    elif vs_peer < -0.5:
        insights.append("📊 **Rispetto ai peer:** Hai margine per raggiungere le scuole simili a te")
        best_peer_name = peers_df.loc[peers_df['indice_ro'].idxmax()]['denominazione']
        insights.append(f"🎯 **Benchmark suggerito:** {best_peer_name}")

for insight in insights:
    st.markdown(insight)

render_footer()
