# 💡 Best Practice - Text Mining e Estrazione Progetti

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import glob
import re
from collections import Counter

st.set_page_config(page_title="Best Practice", page_icon="💡", layout="wide")

SUMMARY_FILE = 'data/analysis_summary.csv'
ANALYSIS_DIR = 'analysis_results'
PTOF_MD_DIR = 'ptof_md'

@st.cache_data(ttl=60)
def load_data():
    if os.path.exists(SUMMARY_FILE):
        df = pd.read_csv(SUMMARY_FILE)
        df['ptof_orientamento_maturity_index'] = pd.to_numeric(df['ptof_orientamento_maturity_index'], errors='coerce')
        return df
    return pd.DataFrame()

def find_report_file(school_id):
    """Trova il file report MD per una scuola"""
    patterns = [
        os.path.join(ANALYSIS_DIR, f"{school_id}_PTOF_analysis.md"),
        os.path.join(ANALYSIS_DIR, f"*{school_id}*.md"),
        os.path.join(PTOF_MD_DIR, f"{school_id}*.md"),
    ]
    
    for pattern in patterns:
        files = glob.glob(pattern)
        if files:
            return files[0]
    return None

def extract_projects(text):
    """Estrae nomi di progetti dal testo"""
    projects = []
    
    # Pattern per progetti
    patterns = [
        r'[Pp]rogetto\s+["\']?([A-Z][^"\'\.]{3,50})["\']?',
        r'[Pp]rogetto\s+([A-Z][a-zA-Z0-9\s]{3,40})',
        r'iniziativa\s+["\']?([A-Z][^"\'\.]{3,50})["\']?',
        r'attività\s+["\']?([A-Z][^"\'\.]{3,40})["\']?',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        projects.extend([m.strip() for m in matches if len(m.strip()) > 3])
    
    return list(set(projects))

def extract_partnerships(text):
    """Estrae partnership e collaborazioni"""
    partnerships = []
    
    patterns = [
        r'[Cc]ollaborazione con\s+([^\.]{5,60})',
        r'[Pp]artnership con\s+([^\.]{5,60})',
        r'[Aa]ccordo con\s+([^\.]{5,60})',
        r'[Cc]onvenzione con\s+([^\.]{5,60})',
        r'in rete con\s+([^\.]{5,60})',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        partnerships.extend([m.strip() for m in matches])
    
    return list(set(partnerships))

def extract_methodologies(text):
    """Estrae metodologie didattiche"""
    methodologies = []
    
    keywords = [
        'project based learning', 'problem based learning', 'flipped classroom',
        'cooperative learning', 'peer tutoring', 'service learning',
        'apprendimento cooperativo', 'didattica laboratoriale', 'outdoor education',
        'coding', 'STEM', 'STEAM', 'debate', 'storytelling', 'gamification',
        'learning by doing', 'role playing', 'simulazione', 'case study'
    ]
    
    text_lower = text.lower()
    for kw in keywords:
        if kw.lower() in text_lower:
            methodologies.append(kw.title())
    
    return list(set(methodologies))

def extract_key_numbers(text):
    """Estrae numeri chiave (ore, percentuali, budget)"""
    numbers = []
    
    patterns = [
        (r'(\d+)\s*ore', 'ore'),
        (r'(\d+)\s*%', 'percentuale'),
        (r'€\s*(\d+[\d\.]*)', 'budget'),
        (r'(\d+)\s*studenti', 'studenti'),
        (r'(\d+)\s*docenti', 'docenti'),
    ]
    
    for pattern, label in patterns:
        matches = re.findall(pattern, text)
        for m in matches[:3]:  # Max 3 per tipo
            numbers.append({'valore': m, 'tipo': label})
    
    return numbers

@st.cache_data(ttl=300)
def analyze_top_schools(df, top_n=10):
    """Analizza i report delle scuole top"""
    top_schools = df.nlargest(top_n, 'ptof_orientamento_maturity_index')
    
    all_projects = []
    all_partnerships = []
    all_methodologies = []
    school_details = []
    
    for _, school in top_schools.iterrows():
        school_id = school['school_id']
        report_file = find_report_file(school_id)
        
        if report_file and os.path.exists(report_file):
            try:
                with open(report_file, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
                
                projects = extract_projects(text)
                partnerships = extract_partnerships(text)
                methodologies = extract_methodologies(text)
                
                all_projects.extend(projects)
                all_partnerships.extend(partnerships)
                all_methodologies.extend(methodologies)
                
                school_details.append({
                    'school_id': school_id,
                    'denominazione': school.get('denominazione', ''),
                    'indice_ro': school['ptof_orientamento_maturity_index'],
                    'regione': school.get('regione', ''),
                    'tipo': school.get('tipo_scuola', ''),
                    'n_progetti': len(projects),
                    'n_partnership': len(partnerships),
                    'n_metodologie': len(methodologies),
                    'progetti': projects[:5],
                    'metodologie': methodologies
                })
            except Exception as e:
                pass
    
    return {
        'projects': Counter(all_projects),
        'partnerships': Counter(all_partnerships),
        'methodologies': Counter(all_methodologies),
        'school_details': school_details
    }

df = load_data()

st.title("💡 Best Practice - Estrazione e Analisi")

with st.expander("📖 Come leggere questa pagina", expanded=False):
    st.markdown("""
    ### 🎯 Scopo della Pagina
    Questa pagina analizza i **report delle scuole eccellenti** per estrarre automaticamente:
    - Nomi di progetti e iniziative
    - Partnership e collaborazioni
    - Metodologie didattiche innovative
    
    ### 📊 Sezioni Disponibili
    
    **🏆 Analisi Scuole Top**
    - Estrazione automatica dai report delle migliori scuole
    - Frequenza di progetti, metodologie, partnership
    
    **📋 Dettaglio per Scuola**
    - Lista di progetti e iniziative per ogni scuola eccellente
    - Possibilità di approfondire le best practice
    
    **☁️ Parole Chiave**
    - Word cloud delle parole più frequenti
    - Identificazione temi ricorrenti
    
    ### 💡 Come Usare
    - Usa le best practice come ispirazione per il miglioramento
    - Contatta le scuole eccellenti per approfondimenti
    - Adatta le metodologie al tuo contesto
    """)

if df.empty:
    st.warning("⚠️ Nessun dato disponibile.")
    st.stop()

st.markdown("---")

# Selezione numero scuole da analizzare
col1, col2 = st.columns([1, 3])
with col1:
    top_n = st.selectbox("📊 Analizza Top N scuole", [5, 10, 15, 20], index=1)

# Analisi
with st.spinner(f"Analisi dei report delle top {top_n} scuole..."):
    results = analyze_top_schools(df, top_n)

st.markdown("---")

# === METRICHE PRINCIPALI ===
st.subheader("📈 Sintesi Best Practice")

met_cols = st.columns(4)
with met_cols[0]:
    st.metric("📁 Progetti Trovati", len(results['projects']))
with met_cols[1]:
    st.metric("🤝 Partnership Estratte", len(results['partnerships']))
with met_cols[2]:
    st.metric("🎓 Metodologie Identificate", len(results['methodologies']))
with met_cols[3]:
    st.metric("🏫 Scuole Analizzate", len(results['school_details']))

st.markdown("---")

# === METODOLOGIE PIÙ FREQUENTI ===
st.subheader("🎓 Metodologie Didattiche più Frequenti")

if results['methodologies']:
    meth_data = [{'Metodologia': k, 'Frequenza': v} for k, v in results['methodologies'].most_common(15)]
    meth_df = pd.DataFrame(meth_data)
    
    fig_meth = px.bar(
        meth_df,
        x='Frequenza',
        y='Metodologia',
        orientation='h',
        color='Frequenza',
        color_continuous_scale='Greens',
        title="Metodologie più diffuse nelle scuole eccellenti"
    )
    fig_meth.update_layout(yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig_meth, use_container_width=True)
else:
    st.info("Nessuna metodologia specifica identificata nei report.")

st.markdown("---")

# === DETTAGLIO PER SCUOLA ===
st.subheader("🏫 Dettaglio Best Practice per Scuola")

if results['school_details']:
    for school in results['school_details']:
        with st.expander(f"🏆 {school['denominazione']} (Indice: {school['indice_ro']:.2f}) - {school['regione']}"):
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.markdown("**📁 Progetti/Iniziative:**")
                if school['progetti']:
                    for p in school['progetti']:
                        st.markdown(f"- {p}")
                else:
                    st.caption("Nessun progetto esplicito estratto")
                
            with col2:
                st.markdown("**🎓 Metodologie:**")
                if school['metodologie']:
                    for m in school['metodologie']:
                        st.markdown(f"- {m}")
                else:
                    st.caption("Nessuna metodologia specifica identificata")
            
            st.markdown(f"**📊 Stats:** {school['n_progetti']} progetti, {school['n_partnership']} partnership, {school['n_metodologie']} metodologie")
else:
    st.warning("Nessun report disponibile per l'analisi.")

st.markdown("---")

# === PAROLE CHIAVE ===
st.subheader("🔤 Parole Chiave nei Report Eccellenti")

try:
    from wordcloud import WordCloud
    import matplotlib.pyplot as plt
    
    # Combina tutto il testo
    all_text = []
    for school in results['school_details']:
        school_id = school['school_id']
        report_file = find_report_file(school_id)
        if report_file and os.path.exists(report_file):
            with open(report_file, 'r', encoding='utf-8', errors='ignore') as f:
                all_text.append(f.read())
    
    if all_text:
        combined_text = " ".join(all_text)
        
        # Stopwords italiane
        stopwords_it = set([
            'di', 'a', 'da', 'in', 'con', 'su', 'per', 'tra', 'fra', 'il', 'lo', 'la', 'i', 'gli', 'le',
            'un', 'uno', 'una', 'e', 'è', 'che', 'non', 'sono', 'come', 'anche', 'più', 'questo', 'questa',
            'del', 'della', 'delle', 'dei', 'degli', 'al', 'alla', 'alle', 'ai', 'agli', 'nel', 'nella',
            'nelle', 'nei', 'negli', 'sul', 'sulla', 'sulle', 'sui', 'sugli', 'dal', 'dalla', 'dalle',
            'dai', 'dagli', 'si', 'o', 'ma', 'se', 'perché', 'dove', 'quando', 'come', 'chi', 'cosa',
            'essere', 'avere', 'fare', 'anno', 'scuola', 'scuole', 'ptof', 'piano', 'triennale', 'offerta',
            'formativa', 'istituto', 'scolastico', 'attraverso', 'all', 'nell', 'dell', 'dall'
        ])
        
        wc = WordCloud(
            width=800, 
            height=400, 
            background_color='white',
            stopwords=stopwords_it,
            max_words=100,
            colormap='viridis'
        ).generate(combined_text)
        
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.imshow(wc, interpolation='bilinear')
        ax.axis('off')
        st.pyplot(fig)
    else:
        st.info("Nessun testo disponibile per la word cloud.")
        
except ImportError:
    st.warning("Installa wordcloud per visualizzare la nuvola di parole: `pip install wordcloud`")

st.markdown("---")

# === CONFRONTO TOP vs BOTTOM ===
st.subheader("📊 Confronto: Cosa Differenzia Top da Bottom?")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🏆 Caratteristiche Top 20%")
    top_20 = df.nlargest(len(df) // 5, 'ptof_orientamento_maturity_index')
    
    # Metriche medie
    st.metric("Media Indice RO", f"{top_20['ptof_orientamento_maturity_index'].mean():.2f}")
    if 'partnership_count' in top_20.columns:
        st.metric("Media Partnership", f"{top_20['partnership_count'].mean():.1f}")
    if 'activities_count' in top_20.columns:
        st.metric("Media Attività", f"{top_20['activities_count'].mean():.1f}")
    if 'has_sezione_dedicata' in top_20.columns:
        st.metric("% Sezione Dedicata", f"{top_20['has_sezione_dedicata'].mean()*100:.0f}%")

with col2:
    st.markdown("### 📉 Caratteristiche Bottom 20%")
    bottom_20 = df.nsmallest(len(df) // 5, 'ptof_orientamento_maturity_index')
    
    st.metric("Media Indice RO", f"{bottom_20['ptof_orientamento_maturity_index'].mean():.2f}")
    if 'partnership_count' in bottom_20.columns:
        st.metric("Media Partnership", f"{bottom_20['partnership_count'].mean():.1f}")
    if 'activities_count' in bottom_20.columns:
        st.metric("Media Attività", f"{bottom_20['activities_count'].mean():.1f}")
    if 'has_sezione_dedicata' in bottom_20.columns:
        st.metric("% Sezione Dedicata", f"{bottom_20['has_sezione_dedicata'].mean()*100:.0f}%")

st.info("""
💡 **A cosa serve**: Identifica le differenze chiave tra scuole eccellenti e scuole in difficoltà.

🔍 **Cosa rileva**: Le scuole top tendono ad avere più partnership, più attività documentate e più frequentemente una sezione dedicata all'orientamento.

🎯 **Implicazioni**: Per migliorare, le scuole potrebbero focalizzarsi su: 1) Creare sezione orientamento esplicita, 2) Sviluppare partnership, 3) Documentare le attività svolte.
""")

st.markdown("---")
st.caption("💡 Best Practice - Estrazione automatica dalle scuole eccellenti")
