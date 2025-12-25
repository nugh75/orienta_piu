# 🎯 Gap Analysis - Distanza dal benchmark e raccomandazioni

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import os

st.set_page_config(page_title="Gap Analysis", page_icon="🎯", layout="wide")

SUMMARY_FILE = 'data/analysis_summary.csv'

# Dimensioni da analizzare
DIMENSIONS = {
    'mean_finalita': 'Finalità',
    'mean_obiettivi': 'Obiettivi',
    'mean_governance': 'Governance',
    'mean_didattica_orientativa': 'Didattica',
    'mean_opportunita': 'Opportunità'
}

# Sotto-indicatori per dimensione (per raccomandazioni dettagliate)
SUB_INDICATORS = {
    'Finalità': {
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
    'Opportunità': {
        '2_7_opzionali_culturali_score': 'Culturali',
        '2_7_opzionali_laboratoriali_espressive_score': 'Laboratoriali Espressive',
        '2_7_opzionali_ludiche_ricreative_score': 'Ludiche Ricreative',
        '2_7_opzionali_volontariato_score': 'Volontariato',
        '2_7_opzionali_sportive_score': 'Sportive'
    }
}

# Raccomandazioni per ogni sotto-indicatore
RECOMMENDATIONS = {
    '2_3_finalita_attitudini_score': [
        "Introdurre test attitudinali standardizzati",
        "Creare portfolio delle competenze individuali",
        "Implementare colloqui orientativi personalizzati"
    ],
    '2_3_finalita_interessi_score': [
        "Organizzare giornate di esplorazione professionale",
        "Creare laboratori di scoperta interessi",
        "Attivare questionari di auto-valutazione"
    ],
    '2_3_finalita_progetto_vita_score': [
        "Sviluppare percorsi di life design",
        "Integrare educazione alla scelta nel curriculum",
        "Coinvolgere famiglie nel progetto orientativo"
    ],
    '2_3_finalita_transizioni_formative_score': [
        "Potenziare raccordo con ordini scolastici successivi",
        "Creare momenti di continuità verticale",
        "Organizzare visite presso scuole/università"
    ],
    '2_3_finalita_capacita_orientative_opportunita_score': [
        "Sviluppare competenze di decision making",
        "Formare all'analisi delle opportunità formative",
        "Creare mappe delle opportunità territoriali"
    ],
    '2_4_obiettivo_ridurre_abbandono_score': [
        "Attivare sistema di early warning",
        "Creare percorsi di ri-motivazione",
        "Potenziare tutoring individuale"
    ],
    '2_4_obiettivo_continuita_territorio_score': [
        "Stringere accordi con enti locali",
        "Creare rete con associazioni territoriali",
        "Mappare risorse del territorio"
    ],
    '2_4_obiettivo_contrastare_neet_score': [
        "Attivare percorsi di alternanza scuola-lavoro",
        "Creare connessioni con centri per l'impiego",
        "Organizzare incontri con mondo del lavoro"
    ],
    '2_4_obiettivo_lifelong_learning_score': [
        "Promuovere competenze di apprendimento permanente",
        "Sviluppare metacognizione negli studenti",
        "Creare portfolio competenze trasferibili"
    ],
    '2_5_azione_coordinamento_servizi_score': [
        "Nominare referente orientamento dedicato",
        "Creare cabina di regia per l'orientamento",
        "Definire protocolli di coordinamento"
    ],
    '2_5_azione_dialogo_docenti_studenti_score': [
        "Istituzionalizzare momenti di dialogo",
        "Formare docenti all'ascolto attivo",
        "Creare spazi di confronto informale"
    ],
    '2_5_azione_rapporto_scuola_genitori_score': [
        "Organizzare incontri orientativi con famiglie",
        "Creare canali di comunicazione dedicati",
        "Coinvolgere genitori come testimonial professionali"
    ],
    '2_5_azione_monitoraggio_azioni_score': [
        "Definire indicatori di monitoraggio",
        "Creare sistema di raccolta feedback",
        "Implementare cicli di miglioramento continuo"
    ],
    '2_5_azione_sistema_integrato_inclusione_fragilita_score': [
        "Attivare percorsi personalizzati per fragili",
        "Creare rete con servizi sociali",
        "Formare docenti su bisogni speciali orientativi"
    ],
    '2_6_didattica_da_esperienza_studenti_score': [
        "Implementare project-based learning",
        "Valorizzare esperienze extra-scolastiche",
        "Creare portfolio esperienziale"
    ],
    '2_6_didattica_laboratoriale_score': [
        "Aumentare ore di laboratorio",
        "Creare laboratori interdisciplinari",
        "Attivare learning by doing"
    ],
    '2_6_didattica_flessibilita_spazi_tempi_score': [
        "Ripensare organizzazione oraria",
        "Creare spazi flessibili di apprendimento",
        "Sperimentare moduli intensivi"
    ],
    '2_6_didattica_interdisciplinare_score': [
        "Progettare UDA interdisciplinari",
        "Creare team di docenti per aree",
        "Sviluppare competenze trasversali"
    ],
    '2_7_opzionali_culturali_score': [
        "Ampliare offerta culturale pomeridiana",
        "Creare partnership con musei/teatri",
        "Organizzare eventi culturali interni"
    ],
    '2_7_opzionali_laboratoriali_espressive_score': [
        "Attivare laboratori artistici/creativi",
        "Creare spazi maker",
        "Promuovere espressione artistica"
    ],
    '2_7_opzionali_ludiche_ricreative_score': [
        "Valorizzare momento ricreativo",
        "Creare spazi di socializzazione",
        "Organizzare eventi ludici strutturati"
    ],
    '2_7_opzionali_volontariato_score': [
        "Attivare progetti di service learning",
        "Creare partnership con associazioni",
        "Valorizzare esperienze di volontariato"
    ],
    '2_7_opzionali_sportive_score': [
        "Ampliare offerta sportiva",
        "Creare gruppi sportivi scolastici",
        "Partnership con associazioni sportive"
    ]
}

@st.cache_data(ttl=60)
def load_data():
    if os.path.exists(SUMMARY_FILE):
        df = pd.read_csv(SUMMARY_FILE)
        # Converti colonne numeriche
        num_cols = list(DIMENSIONS.keys()) + ['ptof_orientamento_maturity_index', 'partnership_count', 'activities_count']
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        return df
    return pd.DataFrame()

def get_best_in_class(df, tipo_scuola=None, ordine_grado=None):
    """Trova la scuola best-in-class per tipo/grado"""
    filtered = df.copy()
    
    if tipo_scuola and tipo_scuola != "Tutti":
        filtered = filtered[filtered['tipo_scuola'].str.contains(tipo_scuola, na=False, case=False)]
    
    if ordine_grado and ordine_grado != "Tutti":
        filtered = filtered[filtered['ordine_grado'].str.contains(ordine_grado, na=False, case=False)]
    
    if filtered.empty:
        return None
    
    return filtered.loc[filtered['ptof_orientamento_maturity_index'].idxmax()]

def calculate_gap(school, benchmark):
    """Calcola il gap per ogni dimensione"""
    gaps = {}
    for col, name in DIMENSIONS.items():
        school_val = school.get(col, 0) or 0
        bench_val = benchmark.get(col, 0) or 0
        gaps[name] = {
            'school': school_val,
            'benchmark': bench_val,
            'gap': bench_val - school_val,
            'gap_pct': ((bench_val - school_val) / bench_val * 100) if bench_val > 0 else 0
        }
    return gaps

def get_priority_areas(school, df, top_n=3):
    """Identifica le aree prioritarie di miglioramento"""
    priorities = []
    
    for dim_col, dim_name in DIMENSIONS.items():
        school_val = school.get(dim_col, 0) or 0
        mean_val = df[dim_col].mean()
        
        # Trova sotto-indicatori deboli
        if dim_name in SUB_INDICATORS:
            for sub_col, sub_name in SUB_INDICATORS[dim_name].items():
                sub_val = school.get(sub_col, 0) or 0
                sub_mean = df[sub_col].mean() if sub_col in df.columns else 4
                
                if sub_val < sub_mean:
                    priorities.append({
                        'dimension': dim_name,
                        'indicator': sub_name,
                        'column': sub_col,
                        'score': sub_val,
                        'mean': sub_mean,
                        'gap': sub_mean - sub_val,
                        'priority_score': (sub_mean - sub_val) * (7 - sub_val)  # Peso maggiore per punteggi bassi
                    })
    
    # Ordina per priority score e prendi i top N
    priorities = sorted(priorities, key=lambda x: x['priority_score'], reverse=True)
    return priorities[:top_n]

def generate_recommendations(priority_areas):
    """Genera raccomandazioni basate sulle aree prioritarie"""
    recs = []
    for area in priority_areas:
        col = area['column']
        if col in RECOMMENDATIONS:
            recs.append({
                'area': f"{area['dimension']} - {area['indicator']}",
                'score': area['score'],
                'target': min(7, area['score'] + 2),
                'recommendations': RECOMMENDATIONS[col]
            })
    return recs

df = load_data()

st.title("🎯 Gap Analysis e Raccomandazioni")

with st.expander("📖 Come leggere questa pagina", expanded=False):
    st.markdown("""
    ### 🎯 Scopo della Pagina
    Questa pagina analizza il **divario** tra una scuola e il benchmark di riferimento, 
    fornendo **raccomandazioni operative** per il miglioramento.
    
    ### 📊 Sezioni Disponibili
    
    **📏 Gap dal Benchmark**
    - Confronto visivo tra la scuola selezionata e la migliore del suo tipo
    - Barre rosse indicano aree sotto il benchmark
    - Barre verdi indicano aree sopra il benchmark
    
    **🎯 Aree Prioritarie**
    - Le 3 aree con maggior potenziale di miglioramento
    - Calcolate considerando gap dalla media e punteggio assoluto
    
    **💡 Raccomandazioni**
    - Suggerimenti operativi specifici per ogni area critica
    - Azioni concrete implementabili nel breve termine
    
    **📈 Piano di Miglioramento**
    - Target realistici per ogni dimensione
    - Timeline suggerita per il miglioramento
    """)

if df.empty:
    st.warning("⚠️ Nessun dato disponibile.")
    st.stop()

st.markdown("---")

# Selezione scuola
col1, col2 = st.columns([2, 1])

with col1:
    # Crea label per selectbox
    df['select_label'] = df['denominazione'].fillna('') + ' (' + df['school_id'].fillna('') + ') - ' + df['comune'].fillna('')
    schools = df.sort_values('denominazione')['select_label'].tolist()
    selected_label = st.selectbox("🏫 Seleziona Scuola", schools)
    
    if selected_label:
        school = df[df['select_label'] == selected_label].iloc[0]

with col2:
    benchmark_type = st.selectbox("📊 Benchmark", ["Best-in-Class Tipo", "Best-in-Class Grado", "Media Nazionale", "Top 10%"])

st.markdown("---")

if selected_label:
    # Info scuola
    st.subheader(f"📋 {school['denominazione']}")
    
    info_cols = st.columns(5)
    with info_cols[0]:
        st.metric("Indice RO", f"{school['ptof_orientamento_maturity_index']:.2f}")
    with info_cols[1]:
        st.metric("Tipo", school.get('tipo_scuola', 'N/D'))
    with info_cols[2]:
        st.metric("Regione", school.get('regione', 'N/D'))
    with info_cols[3]:
        st.metric("Partnership", int(school.get('partnership_count', 0) or 0))
    with info_cols[4]:
        # Calcola percentile
        percentile = (df['ptof_orientamento_maturity_index'] < school['ptof_orientamento_maturity_index']).mean() * 100
        st.metric("Percentile", f"{percentile:.0f}°")
    
    st.markdown("---")
    
    # Determina benchmark
    if benchmark_type == "Best-in-Class Tipo":
        tipo = school.get('tipo_scuola', '').split(',')[0].strip() if school.get('tipo_scuola') else None
        benchmark = get_best_in_class(df, tipo_scuola=tipo)
        bench_label = f"Migliore {tipo}" if tipo else "Migliore assoluta"
    elif benchmark_type == "Best-in-Class Grado":
        grado = school.get('ordine_grado', '').split(',')[0].strip() if school.get('ordine_grado') else None
        benchmark = get_best_in_class(df, ordine_grado=grado)
        bench_label = f"Migliore {grado}" if grado else "Migliore assoluta"
    elif benchmark_type == "Top 10%":
        top_10 = df.nlargest(max(1, len(df)//10), 'ptof_orientamento_maturity_index')
        benchmark = top_10.mean(numeric_only=True)
        benchmark['denominazione'] = "Media Top 10%"
        bench_label = "Media Top 10%"
    else:
        benchmark = df.mean(numeric_only=True)
        benchmark['denominazione'] = "Media Nazionale"
        bench_label = "Media Nazionale"
    
    if benchmark is None:
        st.warning("Nessun benchmark disponibile per questa categoria.")
        st.stop()
    
    # Gap Analysis
    st.subheader(f"📏 Gap rispetto a: {bench_label}")
    
    gaps = calculate_gap(school, benchmark)
    
    # Grafico gap
    gap_df = pd.DataFrame([
        {
            'Dimensione': dim,
            'Scuola': vals['school'],
            'Benchmark': vals['benchmark'],
            'Gap': vals['gap']
        }
        for dim, vals in gaps.items()
    ])
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Radar comparison
        categories = list(gaps.keys())
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatterpolar(
            r=[gaps[cat]['school'] for cat in categories],
            theta=categories,
            fill='toself',
            name=school['denominazione'][:30],
            line_color='blue',
            fillcolor='rgba(0, 100, 255, 0.3)'
        ))
        
        fig.add_trace(go.Scatterpolar(
            r=[gaps[cat]['benchmark'] for cat in categories],
            theta=categories,
            fill='toself',
            name=bench_label,
            line_color='green',
            fillcolor='rgba(0, 255, 100, 0.2)'
        ))
        
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 7])),
            showlegend=True,
            title="Confronto Profilo"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Tabella gap
        st.markdown("#### 📊 Dettaglio Gap")
        for dim, vals in gaps.items():
            gap = vals['gap']
            color = "🔴" if gap > 0.5 else "🟡" if gap > 0 else "🟢"
            st.markdown(f"{color} **{dim}**: {vals['school']:.1f} vs {vals['benchmark']:.1f} (gap: {gap:+.1f})")
    
    st.markdown("---")
    
    # Aree Prioritarie
    st.subheader("🎯 Aree Prioritarie di Miglioramento")
    
    priorities = get_priority_areas(school, df, top_n=5)
    
    if priorities:
        prio_cols = st.columns(min(3, len(priorities)))
        
        for i, prio in enumerate(priorities[:3]):
            with prio_cols[i]:
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #ff6b6b 0%, #feca57 100%); 
                            padding: 15px; border-radius: 10px; color: white; text-align: center;">
                    <h4 style="margin:0;">#{i+1} {prio['indicator']}</h4>
                    <p style="margin:5px 0; font-size: 0.9em;">{prio['dimension']}</p>
                    <p style="margin:0; font-size: 1.5em; font-weight: bold;">
                        {prio['score']:.1f} → {min(7, prio['score']+2):.1f}
                    </p>
                    <p style="margin:0; font-size: 0.8em;">Gap dalla media: {prio['gap']:.1f}</p>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Raccomandazioni
        st.subheader("💡 Raccomandazioni Operative")
        
        recommendations = generate_recommendations(priorities[:3])
        
        for rec in recommendations:
            with st.expander(f"📌 {rec['area']} (Score: {rec['score']:.1f} → Target: {rec['target']:.1f})", expanded=True):
                for i, r in enumerate(rec['recommendations'], 1):
                    st.markdown(f"{i}. {r}")
        
        st.markdown("---")
        
        # Piano di miglioramento
        st.subheader("📈 Piano di Miglioramento Suggerito")
        
        plan_data = []
        for prio in priorities[:5]:
            current = prio['score']
            target = min(7, current + 2)
            plan_data.append({
                'Area': f"{prio['dimension']} - {prio['indicator']}",
                'Attuale': current,
                'Target 6 mesi': min(7, current + 1),
                'Target 12 mesi': target,
                'Priorità': '🔴 Alta' if prio['gap'] > 1.5 else '🟡 Media' if prio['gap'] > 0.5 else '🟢 Bassa'
            })
        
        plan_df = pd.DataFrame(plan_data)
        st.dataframe(plan_df, use_container_width=True, hide_index=True)
        
        # Impatto stimato
        current_index = school['ptof_orientamento_maturity_index']
        potential_gain = sum([min(2, p['gap']) for p in priorities[:3]]) / 5  # Stima conservativa
        projected_index = min(7, current_index + potential_gain)
        
        st.markdown("---")
        st.subheader("🚀 Impatto Stimato")
        
        impact_cols = st.columns(3)
        with impact_cols[0]:
            st.metric("Indice Attuale", f"{current_index:.2f}")
        with impact_cols[1]:
            st.metric("Indice Proiettato (12 mesi)", f"{projected_index:.2f}", f"+{potential_gain:.2f}")
        with impact_cols[2]:
            new_percentile = (df['ptof_orientamento_maturity_index'] < projected_index).mean() * 100
            st.metric("Percentile Proiettato", f"{new_percentile:.0f}°", f"+{new_percentile - percentile:.0f}")
    
    else:
        st.success("✅ Questa scuola non presenta aree critiche evidenti!")

st.markdown("---")
st.caption("🎯 Gap Analysis - Sistema di analisi per il miglioramento continuo")
