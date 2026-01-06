# 🔀 Confronto PTOF - Confronto Side-by-Side tra due scuole

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
import json
import glob
import glob
from data_utils import (
    render_footer,
    load_summary_data,
    DIMENSIONS,
    scale_to_pct,
    format_pct
)
from page_control import setup_page

st.set_page_config(page_title="ORIENTA+ | Confronto PTOF", page_icon="🧭", layout="wide")
setup_page("pages/03_🔀_Confronto_PTOF.py")

# CSS
st.markdown("""
<style>
    .comparison-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 10px;
    }
    .school-header {
        font-size: 1.2em;
        font-weight: bold;
        margin-bottom: 10px;
    }
    .winner-badge {
        background: #2ecc71;
        padding: 3px 10px;
        border-radius: 15px;
        font-size: 0.8em;
    }
    .loser-badge {
        background: #e74c3c;
        padding: 3px 10px;
        border-radius: 15px;
        font-size: 0.8em;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=60)
def load_data():
    df = load_summary_data()
    num_cols = list(DIMENSIONS.keys()) + ['ptof_orientamento_maturity_index']
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return df


def load_school_json(school_id):
    """Carica il JSON di analisi di una scuola."""
    json_files = glob.glob(f'analysis_results/*{school_id}*_analysis.json')
    if json_files:
        try:
            with open(json_files[0], 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return None


def load_school_markdown(school_id):
    """Carica il report markdown di una scuola."""
    md_files = glob.glob(f'analysis_results/*{school_id}*_analysis.md')
    if md_files:
        try:
            with open(md_files[0], 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            pass
    return None


def extract_partnerships(json_data):
    """Estrae le partnership dal JSON."""
    if not json_data:
        return []
    try:
        sec2 = json_data.get('ptof_section2', {})
        partnerships = sec2.get('2_2_partnership', {})
        return partnerships.get('partner_nominati', [])
    except Exception:
        return []


def extract_methodologies(text):
    """Estrae metodologie dal testo del report."""
    if not text:
        return []

    methodologies_keywords = [
        'PBL', 'Project Based Learning', 'STEM', 'STEAM',
        'Debate', 'Cooperative Learning', 'Flipped Classroom',
        'Service Learning', 'Peer Education', 'Tutoring',
        'Laboratorio', 'Alternanza', 'PCTO', 'Stage',
        'Mentoring', 'Orientamento narrativo', 'Portfolio'
    ]

    found = []
    text_upper = text.upper()
    for method in methodologies_keywords:
        if method.upper() in text_upper:
            found.append(method)

    return found


# === CARICAMENTO DATI ===
df = load_data()

st.title("🔀 Confronto PTOF")
st.markdown("Confronta due scuole fianco a fianco per analizzare differenze e somiglianze")

if df.empty:
    st.warning("Nessun dato disponibile")
    st.stop()

# === SELEZIONE SCUOLE ===
st.subheader("📋 Seleziona le Scuole da Confrontare")

col_search1, col_search2 = st.columns(2)

with col_search1:
    search1 = st.text_input("🔍 Cerca Scuola 1", key="search1", placeholder="Nome, codice o comune...")
    if search1:
        search_upper = search1.upper()
        filtered1 = df[
            df['school_id'].str.upper().str.contains(search_upper, na=False) |
            df['denominazione'].str.upper().str.contains(search_upper, na=False) |
            df['comune'].astype(str).str.upper().str.contains(search_upper, na=False)
        ]
        options1 = filtered1['denominazione'].dropna().unique().tolist()
    else:
        options1 = df['denominazione'].dropna().unique().tolist()

with col_search2:
    search2 = st.text_input("🔍 Cerca Scuola 2", key="search2", placeholder="Nome, codice o comune...")
    if search2:
        search_upper = search2.upper()
        filtered2 = df[
            df['school_id'].str.upper().str.contains(search_upper, na=False) |
            df['denominazione'].str.upper().str.contains(search_upper, na=False) |
            df['comune'].astype(str).str.upper().str.contains(search_upper, na=False)
        ]
        options2 = filtered2['denominazione'].dropna().unique().tolist()
    else:
        options2 = df['denominazione'].dropna().unique().tolist()

col_sel1, col_sel2 = st.columns(2)

with col_sel1:
    if options1:
        school1_name = st.selectbox("Scuola 1 (blu)", options1, key="school1_select")
    else:
        st.warning("Nessuna scuola trovata")
        st.stop()

with col_sel2:
    if options2:
        # Rimuovi la scuola 1 dalle opzioni se presente
        options2_filtered = [s for s in options2 if s != school1_name]
        if options2_filtered:
            school2_name = st.selectbox("Scuola 2 (verde)", options2_filtered, key="school2_select")
        else:
            st.warning("Seleziona una scuola diversa")
            st.stop()
    else:
        st.warning("Nessuna scuola trovata")
        st.stop()

# Carica dati delle scuole
school1 = df[df['denominazione'] == school1_name].iloc[0]
school2 = df[df['denominazione'] == school2_name].iloc[0]

st.markdown("---")

# === HEADER CONFRONTO ===
st.subheader("📊 Panoramica")

col_h1, col_vs, col_h2 = st.columns([5, 1, 5])

with col_h1:
    ro1 = school1.get('ptof_orientamento_maturity_index', 0) or 0
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
                padding: 20px; border-radius: 15px; color: white; text-align: center;">
        <div style="font-size: 1.3em; font-weight: bold; margin-bottom: 10px;">
            {school1['denominazione'][:40]}
        </div>
        <div style="font-size: 0.9em; opacity: 0.9;">
            {school1.get('regione', 'N/D')} | {school1.get('tipo_scuola', 'N/D')[:25]}
        </div>
        <div style="font-size: 2.5em; font-weight: bold; margin: 15px 0;">
            {format_pct(ro1)}
        </div>
        <div style="font-size: 0.9em;">Indice Completezza</div>
    </div>
    """, unsafe_allow_html=True)

with col_vs:
    st.markdown("""
    <div style="display: flex; justify-content: center; align-items: center; height: 200px;">
        <span style="font-size: 2em; font-weight: bold; color: #7f8c8d;">VS</span>
    </div>
    """, unsafe_allow_html=True)

with col_h2:
    ro2 = school2.get('ptof_orientamento_maturity_index', 0) or 0
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #2ecc71 0%, #27ae60 100%);
                padding: 20px; border-radius: 15px; color: white; text-align: center;">
        <div style="font-size: 1.3em; font-weight: bold; margin-bottom: 10px;">
            {school2['denominazione'][:40]}
        </div>
        <div style="font-size: 0.9em; opacity: 0.9;">
            {school2.get('regione', 'N/D')} | {school2.get('tipo_scuola', 'N/D')[:25]}
        </div>
        <div style="font-size: 2.5em; font-weight: bold; margin: 15px 0;">
            {format_pct(ro2)}
        </div>
        <div style="font-size: 0.9em;">Indice Completezza</div>
    </div>
    """, unsafe_allow_html=True)

# Differenza RO
pct1 = scale_to_pct(ro1)
pct2 = scale_to_pct(ro2)
diff_pct = pct1 - pct2

if abs(diff_pct) < 5.0:
    st.info(f"📊 Le due scuole hanno un Indice di Completezza molto simile (differenza: {abs(diff_pct):.1f}%)")
elif diff_pct > 0:
    st.success(f"📈 **{school1['denominazione'][:30]}** ha un Indice di Completezza superiore di **{diff_pct:.1f}%**")
else:
    st.success(f"📈 **{school2['denominazione'][:30]}** ha un Indice di Completezza superiore di **{abs(diff_pct):.1f}%**")

st.markdown("---")

# === RADAR COMPARATIVO ===
st.subheader("🕸️ Confronto Dimensionale")

col_radar, col_table = st.columns([2, 1])

with col_radar:
    # Prepara dati (percentuali)
    vals1 = [scale_to_pct(school1.get(d, 0) or 0) for d in DIMENSIONS.keys()]
    vals2 = [scale_to_pct(school2.get(d, 0) or 0) for d in DIMENSIONS.keys()]
    labels = list(DIMENSIONS.values())

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=vals1 + [vals1[0]],
        theta=labels + [labels[0]],
        fill='toself',
        name=school1['denominazione'][:25],
        line_color='#3498db',
        fillcolor='rgba(52, 152, 219, 0.3)'
    ))

    fig.add_trace(go.Scatterpolar(
        r=vals2 + [vals2[0]],
        theta=labels + [labels[0]],
        fill='toself',
        name=school2['denominazione'][:25],
        line_color='#2ecc71',
        fillcolor='rgba(46, 204, 113, 0.3)'
    ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=True,
        height=450,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2)
    )
    st.plotly_chart(fig, use_container_width=True)

with col_table:
    st.markdown("### 📊 Dettaglio per Dimensione")

    comparison_data = []
    for dim_col, dim_label in DIMENSIONS.items():
        v1 = scale_to_pct(school1.get(dim_col, 0) or 0)
        v2 = scale_to_pct(school2.get(dim_col, 0) or 0)
        diff = v1 - v2

        if diff > 5.0:
            winner = "🔵"
        elif diff < -5.0:
            winner = "🟢"
        else:
            winner = "="

        comparison_data.append({
            'Dimensione': dim_label,
            'Scuola 1': f"{v1:.1f}%",
            'Scuola 2': f"{v2:.1f}%",
            'Δ': f"{diff:+.1f}%",
            'Migliore': winner
        })

    comp_df = pd.DataFrame(comparison_data)
    st.dataframe(comp_df, use_container_width=True, hide_index=True)

    # Riepilogo
    wins1 = sum(1 for d in comparison_data if d['Migliore'] == '🔵')
    wins2 = sum(1 for d in comparison_data if d['Migliore'] == '🟢')
    ties = sum(1 for d in comparison_data if d['Migliore'] == '=')

    st.markdown(f"""
    **Riepilogo:**
    - 🔵 Scuola 1 migliore: {wins1} dimensioni
    - 🟢 Scuola 2 migliore: {wins2} dimensioni
    - = Parità: {ties} dimensioni
    """)

st.markdown("---")

# === DETTAGLI ANAGRAFICI ===
st.subheader("📋 Confronto Dati Anagrafici")

col_info1, col_info2 = st.columns(2)

with col_info1:
    st.markdown(f"### 🔵 {school1['denominazione'][:35]}")
    st.markdown(f"""
    | Campo | Valore |
    |-------|--------|
    | **Codice** | {school1.get('school_id', 'N/D')} |
    | **Tipo** | {school1.get('tipo_scuola', 'N/D')} |
    | **Regione** | {school1.get('regione', 'N/D')} |
    | **Provincia** | {school1.get('provincia', 'N/D')} |
    | **Comune** | {school1.get('comune', 'N/D')} |
    | **Area** | {school1.get('area_geografica', 'N/D')} |
    | **Territorio** | {school1.get('territorio', 'N/D')} |
    | **Gestione** | {school1.get('statale_paritaria', 'N/D')} |
    | **Partnership** | {int(school1.get('partnership_count', 0) or 0)} |
    """)

with col_info2:
    st.markdown(f"### 🟢 {school2['denominazione'][:35]}")
    st.markdown(f"""
    | Campo | Valore |
    |-------|--------|
    | **Codice** | {school2.get('school_id', 'N/D')} |
    | **Tipo** | {school2.get('tipo_scuola', 'N/D')} |
    | **Regione** | {school2.get('regione', 'N/D')} |
    | **Provincia** | {school2.get('provincia', 'N/D')} |
    | **Comune** | {school2.get('comune', 'N/D')} |
    | **Area** | {school2.get('area_geografica', 'N/D')} |
    | **Territorio** | {school2.get('territorio', 'N/D')} |
    | **Gestione** | {school2.get('statale_paritaria', 'N/D')} |
    | **Partnership** | {int(school2.get('partnership_count', 0) or 0)} |
    """)

st.markdown("---")

# === PARTNERSHIP E METODOLOGIE ===
st.subheader("🤝 Partnership e Metodologie")

# Carica JSON e MD
json1 = load_school_json(school1.get('school_id', ''))
json2 = load_school_json(school2.get('school_id', ''))
md1 = load_school_markdown(school1.get('school_id', ''))
md2 = load_school_markdown(school2.get('school_id', ''))

col_pm1, col_pm2 = st.columns(2)

with col_pm1:
    st.markdown("#### 🔵 Partnership Scuola 1")
    partners1 = extract_partnerships(json1)
    if partners1:
        for p in partners1[:10]:
            st.markdown(f"- {p}")
        if len(partners1) > 10:
            st.caption(f"... e altre {len(partners1) - 10} partnership")
    else:
        st.info("Nessuna partnership estratta dal PTOF")

    st.markdown("#### 🔵 Metodologie Scuola 1")
    methods1 = extract_methodologies(md1)
    if methods1:
        st.markdown(" | ".join([f"`{m}`" for m in methods1]))
    else:
        st.info("Nessuna metodologia specifica identificata")

with col_pm2:
    st.markdown("#### 🟢 Partnership Scuola 2")
    partners2 = extract_partnerships(json2)
    if partners2:
        for p in partners2[:10]:
            st.markdown(f"- {p}")
        if len(partners2) > 10:
            st.caption(f"... e altre {len(partners2) - 10} partnership")
    else:
        st.info("Nessuna partnership estratta dal PTOF")

    st.markdown("#### 🟢 Metodologie Scuola 2")
    methods2 = extract_methodologies(md2)
    if methods2:
        st.markdown(" | ".join([f"`{m}`" for m in methods2]))
    else:
        st.info("Nessuna metodologia specifica identificata")

# Metodologie in comune
common_methods = set(methods1) & set(methods2)
if common_methods:
    st.success(f"🤝 **Metodologie in comune:** {', '.join(common_methods)}")

st.markdown("---")

# === BAR CHART COMPARATIVO ===
st.subheader("📊 Confronto Visivo per Dimensione")

bar_data = []
for dim_col, dim_label in DIMENSIONS.items():
    v1 = scale_to_pct(school1.get(dim_col, 0) or 0)
    v2 = scale_to_pct(school2.get(dim_col, 0) or 0)
    bar_data.append({'Dimensione': dim_label, 'Scuola 1': v1, 'Scuola 2': v2})

bar_df = pd.DataFrame(bar_data)

fig_bar = go.Figure()
fig_bar.add_trace(go.Bar(
    name=school1['denominazione'][:20],
    x=bar_df['Dimensione'],
    y=bar_df['Scuola 1'],
    marker_color='#3498db'
))
fig_bar.add_trace(go.Bar(
    name=school2['denominazione'][:20],
    x=bar_df['Dimensione'],
    y=bar_df['Scuola 2'],
    marker_color='#2ecc71'
))

fig_bar.update_layout(
    barmode='group',
    yaxis_range=[0, 100],
    height=400,
    legend=dict(orientation="h", yanchor="bottom", y=-0.2)
)
st.plotly_chart(fig_bar, use_container_width=True)

st.markdown("---")

# === INSIGHTS ===
st.subheader("💡 Insights dal Confronto")

insights = []

# Insight su RO
if abs(diff_pct) >= 10.0:
    if diff_pct > 0:
        insights.append(f"📈 **Differenza significativa:** {school1['denominazione'][:25]} supera {school2['denominazione'][:25]} di {diff_pct:.1f}% nell'Indice di Completezza")
    else:
        insights.append(f"📈 **Differenza significativa:** {school2['denominazione'][:25]} supera {school1['denominazione'][:25]} di {abs(diff_pct):.1f}% nell'Indice di Completezza")

# Insight sulle dimensioni
for dim_col, dim_label in DIMENSIONS.items():
    v1 = scale_to_pct(school1.get(dim_col, 0) or 0)
    v2 = scale_to_pct(school2.get(dim_col, 0) or 0)
    diff = abs(v1 - v2)
    if diff >= 15.0:
        better = school1['denominazione'][:25] if v1 > v2 else school2['denominazione'][:25]
        insights.append(f"🎯 **{dim_label}:** Differenza marcata ({diff:.1f}%). {better} eccelle in questa dimensione")

# Insight su partnership
p1 = int(school1.get('partnership_count', 0) or 0)
p2 = int(school2.get('partnership_count', 0) or 0)
if abs(p1 - p2) >= 3:
    more = school1['denominazione'][:25] if p1 > p2 else school2['denominazione'][:25]
    insights.append(f"🤝 **Partnership:** {more} ha significativamente più partnership ({max(p1, p2)} vs {min(p1, p2)})")

# Insight su regione
if school1.get('regione') == school2.get('regione'):
    insights.append(f"📍 **Stessa regione:** Entrambe le scuole sono in {school1.get('regione')} - potenziale per collaborazione territoriale")

# Insight su tipo scuola
if school1.get('tipo_scuola') == school2.get('tipo_scuola'):
    insights.append(f"🏫 **Stesso tipo:** Entrambe sono {school1.get('tipo_scuola')} - confronto particolarmente significativo")

if insights:
    for insight in insights:
        st.markdown(insight)
else:
    st.info("Le due scuole hanno profili abbastanza simili senza differenze marcate.")

st.markdown("---")

# === REPORT COMPLETI ===
st.subheader("📝 Report Completi")

report_tab1, report_tab2 = st.tabs([
    f"🔵 {school1['denominazione'][:35]}",
    f"🟢 {school2['denominazione'][:35]}"
])

with report_tab1:
    if md1:
        st.markdown(md1)
    else:
        st.info("Report non disponibile per questa scuola")

with report_tab2:
    if md2:
        st.markdown(md2)
    else:
        st.info("Report non disponibile per questa scuola")

render_footer()
