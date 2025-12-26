# 👥 Confronto Peer - Match con scuole simili

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import os

st.set_page_config(page_title="Confronto Peer", page_icon="👥", layout="wide")

SUMMARY_FILE = 'data/analysis_summary.csv'

DIMENSIONS = {
    'mean_finalita': 'Finalità',
    'mean_obiettivi': 'Obiettivi',
    'mean_governance': 'Governance',
    'mean_didattica_orientativa': 'Didattica',
    'mean_opportunita': 'Opportunità'
}

@st.cache_data(ttl=60)
def load_data():
    if os.path.exists(SUMMARY_FILE):
        df = pd.read_csv(SUMMARY_FILE)
        num_cols = list(DIMENSIONS.keys()) + ['ptof_orientamento_maturity_index', 'partnership_count', 'activities_count']
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        return df
    return pd.DataFrame()

def calculate_similarity_score(school1, school2, weights=None):
    """Calcola un punteggio di similarità tra due scuole"""
    if weights is None:
        weights = {
            'tipo_match': 30,
            'grado_match': 25,
            'territorio_match': 15,
            'regione_match': 10,
            'statale_match': 10,
            'size_similarity': 10
        }
    
    score = 0
    
    # Match tipo scuola
    tipo1 = set(str(school1.get('tipo_scuola', '')).split(','))
    tipo2 = set(str(school2.get('tipo_scuola', '')).split(','))
    if tipo1 & tipo2:
        score += weights['tipo_match']
    
    # Match ordine grado
    grado1 = set(str(school1.get('ordine_grado', '')).split(','))
    grado2 = set(str(school2.get('ordine_grado', '')).split(','))
    if grado1 & grado2:
        score += weights['grado_match']
    
    # Match territorio
    if school1.get('territorio') == school2.get('territorio'):
        score += weights['territorio_match']
    
    # Match regione (bonus se stessa regione)
    if school1.get('regione') == school2.get('regione'):
        score += weights['regione_match']
    
    # Match statale/paritaria
    if school1.get('statale_paritaria') == school2.get('statale_paritaria'):
        score += weights['statale_match']
    
    # Similarità dimensionale (partnership + activities)
    p1 = school1.get('partnership_count', 0) or 0
    p2 = school2.get('partnership_count', 0) or 0
    a1 = school1.get('activities_count', 0) or 0
    a2 = school2.get('activities_count', 0) or 0
    
    if p1 + p2 > 0:
        size_sim = 1 - abs(p1 - p2) / max(p1 + p2, 1)
        score += weights['size_similarity'] * size_sim
    
    return score

def find_peer_schools(target_school, df, top_n=10, exclude_self=True):
    """Trova le scuole peer più simili"""
    peers = []
    
    for idx, school in df.iterrows():
        if exclude_self and school['school_id'] == target_school['school_id']:
            continue
        
        similarity = calculate_similarity_score(target_school, school)
        peers.append({
            'school_id': school['school_id'],
            'denominazione': school['denominazione'],
            'comune': school.get('comune', ''),
            'regione': school.get('regione', ''),
            'tipo_scuola': school.get('tipo_scuola', ''),
            'ordine_grado': school.get('ordine_grado', ''),
            'territorio': school.get('territorio', ''),
            'statale_paritaria': school.get('statale_paritaria', ''),
            'indice_ro': school.get('ptof_orientamento_maturity_index', 0),
            'similarity_score': similarity,
            **{col: school.get(col, 0) for col in DIMENSIONS.keys()}
        })
    
    peers = sorted(peers, key=lambda x: x['similarity_score'], reverse=True)
    return peers[:top_n]

def get_peer_statistics(target_school, peers_df):
    """Calcola statistiche comparative con i peer"""
    stats = {}
    target_index = target_school.get('ptof_orientamento_maturity_index', 0)
    
    peer_indices = peers_df['indice_ro'].values
    
    stats['peer_mean'] = np.mean(peer_indices)
    stats['peer_std'] = np.std(peer_indices)
    stats['peer_min'] = np.min(peer_indices)
    stats['peer_max'] = np.max(peer_indices)
    stats['target_vs_mean'] = target_index - stats['peer_mean']
    stats['rank_in_peers'] = (peer_indices < target_index).sum() + 1
    stats['total_peers'] = len(peer_indices)
    stats['percentile_in_peers'] = stats['rank_in_peers'] / stats['total_peers'] * 100
    
    # Stats per dimensione
    for col, name in DIMENSIONS.items():
        target_val = target_school.get(col, 0) or 0
        peer_vals = peers_df[col].values
        stats[f'{name}_target'] = target_val
        stats[f'{name}_peer_mean'] = np.mean(peer_vals)
        stats[f'{name}_diff'] = target_val - np.mean(peer_vals)
    
    return stats

df = load_data()

st.title("👥 Confronto Peer - Scuole Simili")

with st.expander("📖 Come leggere questa pagina", expanded=False):
    st.markdown("""
    ### 🎯 Scopo della Pagina
    Questa pagina confronta una scuola con le sue **peer** - scuole con caratteristiche simili -
    per un benchmark più equo e significativo.
    
    ### 📊 Criteri di Matching
    Le scuole peer sono selezionate in base a:
    - **Tipo scuola** (30%): Liceo, Tecnico, Professionale, etc.
    - **Ordine/Grado** (25%): Infanzia, Primaria, I/II Grado
    - **Territorio** (15%): Metropolitano vs Non Metropolitano
    - **Regione** (10%): Bonus per stessa regione
    - **Statale/Paritaria** (10%): Match tipologia gestionale
    - **Dimensione** (10%): Similarità in partnership/attività
    
    ### 📈 Interpretazione
    - **Posizione nel Gruppo Peer**: Dove si colloca la scuola tra le simili
    - **Δ dalla Media Peer**: Quanto è sopra/sotto la media del gruppo
    - **Punti di Forza/Debolezza Relativi**: Rispetto a scuole comparabili
    """)

if df.empty:
    st.warning("⚠️ Nessun dato disponibile.")
    st.stop()

st.markdown("---")

# Selezione scuola
df['select_label'] = df['denominazione'].fillna('') + ' (' + df['school_id'].fillna('') + ')'
schools = df.sort_values('denominazione')['select_label'].tolist()
selected_label = st.selectbox("🏫 Seleziona Scuola da Analizzare", schools)

if selected_label:
    target_school = df[df['select_label'] == selected_label].iloc[0]
    
    # Parametri peer matching
    with st.expander("⚙️ Configura Criteri di Matching", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            n_peers = st.slider("Numero di Peer", 5, 20, 10)
        with col2:
            same_region_only = st.checkbox("Solo stessa regione", False)
        with col3:
            same_type_only = st.checkbox("Solo stesso tipo", False)
    
    # Filtra se richiesto
    filtered_df = df.copy()
    if same_region_only:
        filtered_df = filtered_df[filtered_df['regione'] == target_school['regione']]
    if same_type_only:
        tipo = str(target_school.get('tipo_scuola', '')).split(',')[0].strip()
        filtered_df = filtered_df[filtered_df['tipo_scuola'].str.contains(tipo, na=False, case=False)]
    
    # Trova peer
    peers = find_peer_schools(target_school, filtered_df, top_n=n_peers)
    peers_df = pd.DataFrame(peers)
    
    if peers_df.empty:
        st.warning("Nessuna scuola peer trovata con i criteri selezionati.")
        st.stop()
    
    # Info scuola target
    st.subheader(f"📋 {target_school['denominazione']}")
    
    info_cols = st.columns(5)
    with info_cols[0]:
        st.metric("Indice RO", f"{target_school['ptof_orientamento_maturity_index']:.2f}")
    with info_cols[1]:
        st.metric("Tipo", str(target_school.get('tipo_scuola', 'N/D'))[:20])
    with info_cols[2]:
        st.metric("Regione", target_school.get('regione', 'N/D'))
    with info_cols[3]:
        st.metric("Territorio", target_school.get('territorio', 'N/D'))
    with info_cols[4]:
        st.metric("Gestione", target_school.get('statale_paritaria', 'N/D'))
    
    st.markdown("---")
    
    # Statistiche peer
    stats = get_peer_statistics(target_school, peers_df)
    
    st.subheader("📊 Posizionamento nel Gruppo Peer")
    
    stat_cols = st.columns(4)
    with stat_cols[0]:
        st.metric(
            "Posizione", 
            f"{stats['rank_in_peers']}/{stats['total_peers']}",
            help="Posizione nel ranking del gruppo peer"
        )
    with stat_cols[1]:
        st.metric(
            "Percentile Peer", 
            f"{stats['percentile_in_peers']:.0f}°",
            help="Percentuale di peer superati"
        )
    with stat_cols[2]:
        delta = stats['target_vs_mean']
        st.metric(
            "vs Media Peer", 
            f"{target_school['ptof_orientamento_maturity_index']:.2f}",
            f"{delta:+.2f}",
            delta_color="normal"
        )
    with stat_cols[3]:
        st.metric(
            "Range Peer", 
            f"{stats['peer_min']:.1f} - {stats['peer_max']:.1f}",
            help="Range indici delle scuole peer"
        )
    
    st.markdown("---")
    
    # Confronto visivo
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.subheader("📈 Confronto Dimensionale")
        
        # Radar chart
        categories = list(DIMENSIONS.values())
        
        target_values = [target_school.get(col, 0) or 0 for col in DIMENSIONS.keys()]
        peer_mean_values = [peers_df[col].mean() for col in DIMENSIONS.keys()]
        peer_max_values = [peers_df[col].max() for col in DIMENSIONS.keys()]
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatterpolar(
            r=target_values,
            theta=categories,
            fill='toself',
            name='Scuola Selezionata',
            line_color='blue',
            fillcolor='rgba(0, 100, 255, 0.3)'
        ))
        
        fig.add_trace(go.Scatterpolar(
            r=peer_mean_values,
            theta=categories,
            fill='toself',
            name='Media Peer',
            line_color='orange',
            fillcolor='rgba(255, 165, 0, 0.2)'
        ))
        
        fig.add_trace(go.Scatterpolar(
            r=peer_max_values,
            theta=categories,
            fill='none',
            name='Best Peer',
            line_color='green',
            line_dash='dash'
        ))
        
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 7])),
            showlegend=True,
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("📊 Δ per Dimensione")
        
        diff_data = []
        for col, name in DIMENSIONS.items():
            target_val = target_school.get(col, 0) or 0
            peer_mean = peers_df[col].mean()
            diff = target_val - peer_mean
            diff_data.append({
                'Dimensione': name,
                'Differenza': diff,
                'Colore': 'green' if diff > 0 else 'red'
            })
        
        diff_df = pd.DataFrame(diff_data)
        
        fig_bar = px.bar(
            diff_df,
            x='Differenza',
            y='Dimensione',
            orientation='h',
            color='Differenza',
            color_continuous_scale=['red', 'yellow', 'green'],
            range_color=[-2, 2]
        )
        fig_bar.update_layout(
            showlegend=False,
            height=300,
            xaxis_title="Δ vs Media Peer",
            yaxis_title=""
        )
        fig_bar.add_vline(x=0, line_dash="dash", line_color="gray")
        
        st.plotly_chart(fig_bar, use_container_width=True)
        
        # Interpretazione
        strengths = [d['Dimensione'] for d in diff_data if d['Differenza'] > 0.3]
        weaknesses = [d['Dimensione'] for d in diff_data if d['Differenza'] < -0.3]
        
        if strengths:
            st.success(f"**Punti di forza relativi:** {', '.join(strengths)}")
        if weaknesses:
            st.warning(f"**Aree di miglioramento:** {', '.join(weaknesses)}")
    
    st.markdown("---")
    
    # Lista peer
    st.subheader(f"🏫 Le {n_peers} Scuole Peer Più Simili")
    
    # Prepara tabella
    display_df = peers_df[[
        'denominazione', 'comune', 'regione', 'tipo_scuola', 
        'indice_ro', 'similarity_score'
    ]].copy()
    display_df.columns = ['Scuola', 'Comune', 'Regione', 'Tipo', 'Indice RO', 'Similarità %']
    display_df['Similarità %'] = display_df['Similarità %'].round(0).astype(int)
    display_df['Indice RO'] = display_df['Indice RO'].round(2)
    
    # Colora in base all'indice
    def color_index(val):
        target = target_school['ptof_orientamento_maturity_index']
        if val > target + 0.3:
            return 'background-color: rgba(0, 255, 0, 0.2)'
        elif val < target - 0.3:
            return 'background-color: rgba(255, 0, 0, 0.2)'
        return ''
    
    st.dataframe(
        display_df.style.applymap(color_index, subset=['Indice RO']),
        use_container_width=True,
        hide_index=True
    )
    
    st.markdown("---")
    
    # Distribuzione peer
    st.subheader("📊 Distribuzione Indici nel Gruppo Peer")
    
    fig_dist = go.Figure()
    
    # Histogram
    fig_dist.add_trace(go.Histogram(
        x=peers_df['indice_ro'],
        nbinsx=10,
        name='Distribuzione Peer',
        marker_color='lightblue'
    ))
    
    # Linea target
    fig_dist.add_vline(
        x=target_school['ptof_orientamento_maturity_index'],
        line_dash="dash",
        line_color="red",
        annotation_text="Tu",
        annotation_position="top"
    )
    
    # Linea media
    fig_dist.add_vline(
        x=peers_df['indice_ro'].mean(),
        line_dash="dot",
        line_color="orange",
        annotation_text="Media",
        annotation_position="bottom"
    )
    
    fig_dist.update_layout(
        xaxis_title="Indice RO",
        yaxis_title="N. Scuole",
        showlegend=False,
        height=300
    )
    
    st.plotly_chart(fig_dist, use_container_width=True)
    
    # Insights
    st.subheader("💡 Insights dal Confronto Peer")
    
    insights = []
    
    if stats['percentile_in_peers'] >= 75:
        insights.append("🏆 **Eccellente!** Ti posizioni nel quartile superiore del tuo gruppo peer.")
    elif stats['percentile_in_peers'] >= 50:
        insights.append("✅ **Buono!** Sei sopra la mediana del gruppo peer.")
    elif stats['percentile_in_peers'] >= 25:
        insights.append("⚠️ **Attenzione:** Sei sotto la mediana del gruppo peer.")
    else:
        insights.append("🔴 **Critico:** Sei nel quartile inferiore del gruppo peer.")
    
    # Analisi punti di forza/debolezza
    max_strength = max(diff_data, key=lambda x: x['Differenza'])
    max_weakness = min(diff_data, key=lambda x: x['Differenza'])
    
    if max_strength['Differenza'] > 0.5:
        insights.append(f"💪 **Punto di forza distintivo:** {max_strength['Dimensione']} (+{max_strength['Differenza']:.1f} vs peer)")
    
    if max_weakness['Differenza'] < -0.5:
        insights.append(f"📉 **Area critica rispetto ai peer:** {max_weakness['Dimensione']} ({max_weakness['Differenza']:.1f} vs peer)")
    
    # Best practice dai peer migliori
    best_peer = peers_df.loc[peers_df['indice_ro'].idxmax()]
    if best_peer['indice_ro'] > target_school['ptof_orientamento_maturity_index'] + 0.5:
        insights.append(f"🎯 **Benchmark suggerito:** {best_peer['denominazione']} (Indice: {best_peer['indice_ro']:.2f})")
    
    for insight in insights:
        st.markdown(insight)

st.markdown("---")
st.caption("👥 Confronto Peer - Benchmark equo con scuole simili")
