# 🔬 Analisi Avanzate - Statistiche e Clustering

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import glob
from collections import Counter

# Safe optional imports
try:
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
    from sklearn.decomposition import PCA
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

try:
    from scipy import stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

try:
    from wordcloud import WordCloud
    import matplotlib.pyplot as plt
    HAS_WORDCLOUD = True
except ImportError:
    HAS_WORDCLOUD = False

st.set_page_config(page_title="Analisi Avanzate", page_icon="🔬", layout="wide")

SUMMARY_FILE = 'data/analysis_summary.csv'

LABEL_MAP = {
    'mean_finalita': 'Finalità',
    'mean_obiettivi': 'Obiettivi', 
    'mean_governance': 'Governance',
    'mean_didattica_orientativa': 'Didattica',
    'mean_opportunita': 'Opportunità',
}

def get_label(col):
    return LABEL_MAP.get(col, col.replace('_', ' ').title())

@st.cache_data(ttl=60)
def load_data():
    if os.path.exists(SUMMARY_FILE):
        return pd.read_csv(SUMMARY_FILE)
    return pd.DataFrame()

df = load_data()

st.title("🔬 Analisi Statistiche Avanzate")

if df.empty:
    st.warning("Nessun dato disponibile")
    st.stop()

# Standardize numeric columns (handle 'ND')
numeric_cols = [
    'ptof_orientamento_maturity_index', 
    'mean_finalita', 'mean_obiettivi', 
    'mean_governance', 'mean_didattica_orientativa', 'mean_opportunita'
]
for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

st.markdown("---")

# 1. Correlation Heatmap (Refined)
st.subheader("🔥 Matrice di Correlazione (Dimensioni Chiave)")
st.caption("Correlazione di Pearson tra le 5 dimensioni. Valori alti (rosso/blu scuro) indicano forte legame.")

corr_cols = ['mean_finalita', 'mean_obiettivi', 'mean_governance', 'mean_didattica_orientativa', 'mean_opportunita']
if all(c in df.columns for c in corr_cols) and len(df) >= 5:
    corr = df[corr_cols].corr()
    labels = [get_label(c) for c in corr_cols]
    
    fig = px.imshow(corr.values, x=labels, y=labels, color_continuous_scale='RdBu',
                   zmin=-1, zmax=1, text_auto='.2f', title="Correlazioni tra Dimensioni")
    fig.update_layout(height=600)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Dati insufficienti per le correlazioni (servono le 5 dimensioni e almeno 5 scuole)")

# 1.1 Correlation Heatmap (Sub-dimensions)
st.markdown("---")
st.subheader("🔍 Analisi di Dettaglio (Sotto-dimensioni)")
st.caption("Correlazioni tra gli indicatori specifici che compongono le dimensioni principali.")

# Define groups
sub_dim_groups = {
    'Finalità (2.3)': [c for c in df.columns if c.startswith('2_3_')],
    'Obiettivi (2.4)': [c for c in df.columns if c.startswith('2_4_')],
    'Governance (2.5)': [c for c in df.columns if c.startswith('2_5_')],
    'Didattica (2.6)': [c for c in df.columns if c.startswith('2_6_')],
    'Opportunità (2.7)': [c for c in df.columns if c.startswith('2_7_')]
}

# Clean naming for display
def clean_sub_label(col):
    if col.startswith('2_'):
        parts = col.split('_')
        if len(parts) > 3:
            return " ".join(parts[3:]).title()
    return col

col_ctrl1, col_ctrl2 = st.columns([2, 1])
with col_ctrl1:
    sub_options = ["Tutte"] + list(sub_dim_groups.keys())
    selected_sub = st.selectbox("Seleziona Dimensione per Dettaglio", sub_options)

with col_ctrl2:
    min_corr = st.slider("Filtra per correlazione minima (valore assoluto)", 0.0, 1.0, 0.5, 0.05)

target_cols = []
if selected_sub == "Tutte":
    for cols in sub_dim_groups.values():
        target_cols.extend(cols)
else:
    target_cols = sub_dim_groups[selected_sub]

# Filter columns that actually exist in df and have numeric data
target_cols = [c for c in target_cols if c in df.columns]

if len(target_cols) >= 2 and len(df) >= 5:
    # Cleanup labels
    sub_labels = [clean_sub_label(c) for c in target_cols]
    
    # Calculate Custom Correlation Matrix
    df_target = df[target_cols].dropna()
    
    if len(df_target) < 5:
         st.warning("Dati insufficienti dopo la rimozione dei valori mancanti.")
    else:
        corr_matrix = df_target.corr()
        
        # Apply magnitude filter
        mask = corr_matrix.abs() < min_corr
        # Keep diagonal visible (always 1.0)
        for i in range(len(corr_matrix)):
            mask.iloc[i, i] = False
            
        corr_show = corr_matrix.mask(mask)

        height = 600 if len(target_cols) < 10 else 800
        if len(target_cols) > 20: height = 1000
        
        fig_sub = px.imshow(corr_show.values, x=sub_labels, y=sub_labels, color_continuous_scale='RdBu',
                    zmin=-1, zmax=1, title=f"Correlazioni: {selected_sub}")
        fig_sub.update_traces(text=corr_show.round(2).values, texttemplate="%{text}")
        fig_sub.update_layout(height=height)


        st.plotly_chart(fig_sub, use_container_width=True)
else:
    st.info("Dati insufficienti per le correlazioni di dettaglio stabilite.")

st.markdown("---")

# 2. Clustering (Refined)
st.subheader("🎯 Cluster Analysis (Identificazione Gruppi)")
st.caption("Raggruppamento automatico (K-Means) basato sulle 5 dimensioni.")

if HAS_SKLEARN:
    cluster_cols = ['mean_finalita', 'mean_obiettivi', 'mean_governance', 'mean_didattica_orientativa', 'mean_opportunita']
    if all(c in df.columns for c in cluster_cols) and len(df) >= 6:
        X = df[cluster_cols].dropna()
        if len(X) >= 6:
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            n_clusters = st.slider("Numero di Gruppi", 2, 5, 3)
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            clusters = kmeans.fit_predict(X_scaled)
            
            pca = PCA(n_components=2)
            X_pca = pca.fit_transform(X_scaled)
            
            cluster_df = pd.DataFrame({
                'PC1': X_pca[:, 0], 'PC2': X_pca[:, 1],
                'Cluster': [f'Cluster {c+1}' for c in clusters],
                'Scuola': df.loc[X.index, 'denominazione'].values if 'denominazione' in df.columns else X.index
            })
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                fig = px.scatter(cluster_df, x='PC1', y='PC2', color='Cluster', hover_data=['Scuola'],
                               title=f"Mappa dei Cluster (PCA)")
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("### 📊 Profilo Gruppi")
                # Cluster means heatmap
                df_clust = df.loc[X.index].copy()
                df_clust['Cluster'] = [f'Cluster {c+1}' for c in clusters]
                cluster_means = df_clust.groupby('Cluster')[cluster_cols].mean()
                cluster_means.columns = [get_label(c) for c in cluster_cols]
                
                fig_heat = px.imshow(cluster_means, text_auto='.1f', color_continuous_scale='Viridis',
                                   title="Punteggi Medi", aspect="auto")
                st.plotly_chart(fig_heat, use_container_width=True)
        else:
            st.info("Servono almeno 6 scuole con dati completi")
    else:
        st.info("Dati insufficienti per il clustering")
else:
    st.warning("Installa scikit-learn: pip install scikit-learn")

st.markdown("---")

# 3. ANOVA
st.subheader("📊 ANOVA: Test Differenze per Gruppo")
if HAS_SCIPY:
    results = []
    test_vars = [
        ('area_geografica', 'Area Geografica'),
        ('ordine_grado', 'Ordine Grado'),
        ('tipo_scuola', 'Tipo Scuola'),
        ('territorio', 'Territorio')
    ]
    
    if 'tipo_scuola' in df.columns:
        try:
            from app.data_utils import explode_school_types
            df_types = explode_school_types(df)
        except ImportError:
            df_types = df
    else:
        df_types = df
    
    for col, label in test_vars:
        target_df = df_types if col == 'tipo_scuola' else df
        
        if col in target_df.columns and 'ptof_orientamento_maturity_index' in target_df.columns:
            groups = [g['ptof_orientamento_maturity_index'].dropna().values 
                     for _, g in target_df.groupby(col) if len(g) >= 2]
            if len(groups) >= 2:
                f_stat, p_val = stats.f_oneway(*groups)
                sig = "✅" if p_val < 0.05 else "⚪"
                results.append({'Confronto': label, 'F': f"{f_stat:.2f}", 
                               'p-value': f"{p_val:.4f}", 'Sig.': sig})
    
    if results:
        st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)
    else:
        st.info("Dati insufficienti per ANOVA")
else:
    st.warning("scipy non disponibile")

st.markdown("---")

# 4. Violin Plot
st.subheader("🎻 Distribuzione per Tipo Scuola")
if 'tipo_scuola' in df.columns:
    try:
        from app.data_utils import explode_school_types
        df_violin = explode_school_types(df)
    except ImportError:
        df_violin = df

    fig = px.violin(df_violin, x='tipo_scuola', y='ptof_orientamento_maturity_index',
                   color='tipo_scuola', box=True, points='all',
                   title="Violin Plot Maturity Index")
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# 5. Top/Bottom Performers
st.subheader("🏅 Top 5 e Bottom 5")
if 'ptof_orientamento_maturity_index' in df.columns:
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🥇 Top 5")
        top5 = df.nlargest(5, 'ptof_orientamento_maturity_index')[['denominazione', 'tipo_scuola', 'ptof_orientamento_maturity_index']]
        top5.columns = ['Scuola', 'Tipo', 'Indice']
        st.dataframe(top5.reset_index(drop=True), use_container_width=True)
    with col2:
        st.markdown("### 🔻 Bottom 5")
        bottom5 = df.nsmallest(5, 'ptof_orientamento_maturity_index')[['denominazione', 'tipo_scuola', 'ptof_orientamento_maturity_index']]
        bottom5.columns = ['Scuola', 'Tipo', 'Indice']
        st.dataframe(bottom5.reset_index(drop=True), use_container_width=True)

st.markdown("---")

# 6. JSON Analysis (Bar Charts + Word Clouds)
st.subheader("📊 Analisi Attività e Partnership (da JSON)")
st.caption("Aggregazione dai file JSON: Grafici a barre e Word Cloud di Attività e Partner.")

try:
    import json
    
    # Use absolute path
    base_path = os.getcwd()
    json_path = os.path.join(base_path, 'analysis_results', '*_analysis.json')
    json_files = glob.glob(json_path)
    
    if not json_files:
        st.warning(f"Nessun file JSON trovato in {json_path}")
    else:
        activity_categories = []
        activity_titles = [] # For Word Cloud
        collaboration_types = []
        
        # Limit processing
        MAX_FILES = 200
        for jf in json_files[:MAX_FILES]:
            try:
                with open(jf, 'r') as f:
                    data = json.load(f)
                    
                    # 1. Activities
                    activities = data.get('activities_register', [])
                    for act in activities:
                        # Category
                        cat = act.get('categoria_principale')
                        if cat and cat not in ['ND', '']:
                            activity_categories.append(cat)
                        # Title for Word Cloud
                        title = act.get('titolo_attivita')
                        if title and title not in ['ND', '']:
                            activity_titles.append(title)
                            
                    # 2. Partners
                    partners = []
                    p_scores = data.get('ptof_section2', {})
                    if p_scores:
                         p_partners = p_scores.get('2_2_partnership', {})
                         if p_partners:
                             partners = p_partners.get('partner_nominati', [])
                    
                    for p in partners:
                        if p and p not in ['ND', '']:
                            collaboration_types.append(p)
            except Exception as e:
                pass
        
        # --- Section 6a: Bar Charts ---
        if activity_categories or collaboration_types:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 📌 Categorie Attività")
                if activity_categories:
                    counts = Counter(activity_categories)
                    df_act = pd.DataFrame(counts.most_common(15), columns=['Categoria', 'N'])
                    fig = px.bar(df_act, x='N', y='Categoria', orientation='h', title="Top Categorie")
                    fig.update_layout(yaxis={'categoryorder':'total ascending'})
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Nessuna attività")
            
            with col2:
                st.markdown("#### 🤝 Partner Principali")
                if collaboration_types:
                    counts = Counter(collaboration_types)
                    df_collab = pd.DataFrame(counts.most_common(15), columns=['Partner', 'N'])
                    fig = px.bar(df_collab, x='N', y='Partner', orientation='h', title="Top Partner")
                    fig.update_layout(yaxis={'categoryorder':'total ascending'})
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Nessun partner")
        
        # --- Section 6b: Word Clouds (Activity Titles & Partners) ---
        if HAS_WORDCLOUD and (activity_titles or collaboration_types):
            st.markdown("---")
            st.subheader("☁️ Word Cloud: Attività e Partner")
            
            stopwords_it = {
                'il', 'lo', 'la', 'i', 'gli', 'le', 'un', 'uno', 'una', 'un\'', 
                'di', 'a', 'da', 'in', 'con', 'su', 'per', 'tra', 'fra', 
                'e', 'o', 'ma', 'se', 'perché', 'come', 'dove', 'che', 'chi', 'cui',
                'non', 'sì', 'no', 'anche', 'ancora', 'già', 'più', 'meno',
                'mio', 'tuo', 'suo', 'nostro', 'vostro', 'loro',
                'mia', 'tua', 'sua', 'nostra', 'vostra',
                'miei', 'tuoi', 'suoi', 'nostri', 'vostri',
                'mie', 'tue', 'sue', 'nostre', 'vostre',
                'questo', 'quello', 'questa', 'quella', 'questi', 'quelli', 'queste', 'quelle',
                'io', 'tu', 'lui', 'lei', 'noi', 'voi', 'essi', 'esse',
                'mi', 'ti', 'si', 'ci', 'vi', 'li', 'le', 'lo', 'la', 'ne',
                'è', 'era', 'fu', 'sarà', 'sono', 'erano', 'furono', 'saranno',
                'sia', 'siano', 'fosse', 'fossero', 'stato', 'stata', 'stati', 'state',
                'ha', 'hanno', 'aveva', 'avevano', 'ebbe', 'ebbero', 'avrà', 'avranno',
                'abbia', 'abbiano', 'avesse', 'avessero', 'avuto', 'avuta', 'avuti', 'avute',
                'fare', 'fatto', 'fa', 'fanno', 'faceva', 'facevano',
                'stare', 'stai', 'sta', 'stiamo', 'state', 'stanno',
                'del', 'dello', 'della', 'dei', 'degli', 'delle',
                'al', 'allo', 'alla', 'ai', 'agli', 'alle',
                'dal', 'dallo', 'dalla', 'dai', 'dagli', 'dalle',
                'nel', 'nello', 'nella', 'nei', 'negli', 'nelle',
                'col', 'coi', 'sul', 'sullo', 'sulla', 'sui', 'sugli', 'sulle',
                'ed', 'od', 'ad',
                'progetto', 'corso', 'attività', 'scuola'
            }
            
            wc_col1, wc_col2 = st.columns(2)
            
            with wc_col1:
                st.markdown("#### Parole chiave nelle Attività")
                if activity_titles:
                    text_act = " ".join(activity_titles)
                    wc_act = WordCloud(width=400, height=300, background_color='white', stopwords=stopwords_it, colormap='Blues').generate(text_act)
                    fig, ax = plt.subplots()
                    ax.imshow(wc_act, interpolation='bilinear')
                    ax.axis('off')
                    st.pyplot(fig)
                else:
                    st.info("Nessun titolo attività disponibile")
                    
            with wc_col2:
                st.markdown("#### Parole chiave nei Partner")
                if collaboration_types:
                    text_part = " ".join(collaboration_types)
                    wc_part = WordCloud(width=400, height=300, background_color='white', stopwords=stopwords_it, colormap='Dark2').generate(text_part)
                    fig, ax = plt.subplots()
                    ax.imshow(wc_part, interpolation='bilinear')
                    ax.axis('off')
                    st.pyplot(fig)
                else:
                    st.info("Nessun partner disponibile")

except Exception as e:
    st.error(f"Errore JSON Analysis: {e}")

st.markdown("---")

# 7. Word Cloud (Markdown - Top/Bottom)
st.subheader("📚 Analisi Lessicale dai Report (Top vs Bottom Performers)")
st.caption("Confronto delle parole più frequenti nei PTOF delle scuole con punteggi alti vs bassi.")

if HAS_WORDCLOUD:
    try:
        if 'ptof_orientamento_maturity_index' in df.columns and 'school_id' in df.columns:
            q_high = df['ptof_orientamento_maturity_index'].quantile(0.80)
            q_low = df['ptof_orientamento_maturity_index'].quantile(0.20)
            
            # Use school_id instead of analysis_file
            top_ids = df[df['ptof_orientamento_maturity_index'] >= q_high]['school_id'].dropna().tolist()
            bottom_ids = df[df['ptof_orientamento_maturity_index'] <= q_low]['school_id'].dropna().tolist()
            
            st.write(f"Confronto: {len(top_ids)} Top vs {len(bottom_ids)} Bottom files.")
            
            if st.button("Genera Word Cloud (Report)", key="gen_wc_md"):
                stopwords_it = {
                    'il', 'lo', 'la', 'i', 'gli', 'le', 'un', 'uno', 'una', 'un\'', 
                    'di', 'a', 'da', 'in', 'con', 'su', 'per', 'tra', 'fra', 
                    'e', 'o', 'ma', 'se', 'perché', 'come', 'dove', 'che', 'chi', 'cui',
                    'non', 'sì', 'no', 'anche', 'ancora', 'già', 'più', 'meno',
                    'mio', 'tuo', 'suo', 'nostro', 'vostro', 'loro',
                    'mia', 'tua', 'sua', 'nostra', 'vostra',
                    'miei', 'tuoi', 'suoi', 'nostri', 'vostri',
                    'mie', 'tue', 'sue', 'nostre', 'vostre',
                    'questo', 'quello', 'questa', 'quella', 'questi', 'quelli', 'queste', 'quelle',
                    'io', 'tu', 'lui', 'lei', 'noi', 'voi', 'essi', 'esse',
                    'mi', 'ti', 'si', 'ci', 'vi', 'li', 'le', 'lo', 'la', 'ne',
                    'è', 'era', 'fu', 'sarà', 'sono', 'erano', 'furono', 'saranno',
                    'sia', 'siano', 'fosse', 'fossero', 'stato', 'stata', 'stati', 'state',
                    'ha', 'hanno', 'aveva', 'avevano', 'ebbe', 'ebbero', 'avrà', 'avranno',
                    'abbia', 'abbiano', 'avesse', 'avessero', 'avuto', 'avuta', 'avuti', 'avute',
                    'fare', 'fatto', 'fa', 'fanno', 'faceva', 'facevano',
                    'stare', 'stai', 'sta', 'stiamo', 'state', 'stanno',
                    'del', 'dello', 'della', 'dei', 'degli', 'delle',
                    'al', 'allo', 'alla', 'ai', 'agli', 'alle',
                    'dal', 'dallo', 'dalla', 'dai', 'dagli', 'dalle',
                    'nel', 'nello', 'nella', 'nei', 'negli', 'nelle',
                    'col', 'coi', 'sul', 'sullo', 'sulla', 'sui', 'sugli', 'sulle',
                    'ed', 'od', 'ad',
                    'scuola', 'studenti', 'alunni', 'classe', 'classi', 'docenti', 'istituto', 
                    'anno', 'scolastico', 'attività', 'progetto', 'percorso', 'corso', 'ptof', 
                    'obiettivi', 'didattica', 'valutazione', 'competenze', 'formazione', 
                    'apprendimento', 'orientamento', 'tempi', 'spazi', 'figure', 'professionali'
                }
                
                def read_ptof_md(school_ids):
                    txt = []
                    # Pre-scan ptof_md directory to map school_ids to filenames
                    md_dir = os.path.join(os.getcwd(), 'ptof_md')
                    if not os.path.exists(md_dir):
                        return ""
                    
                    all_md_files = os.listdir(md_dir)
                    
                    for sid in school_ids:
                        # Find matching file for this school_id
                        found_file = None
                        for fname in all_md_files:
                            if sid in fname and fname.endswith('.md'):
                                found_file = os.path.join(md_dir, fname)
                                break
                        
                        if found_file:
                            try:
                                with open(found_file, 'r', encoding='utf-8', errors='ignore') as f:
                                    txt.append(f.read())
                            except: pass
                    return " ".join(txt)
                
                with st.spinner("Elaborazione (ricerca file PTOF)..."):
                    t_top = read_ptof_md(top_ids)
                    t_bot = read_ptof_md(bottom_ids)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("### Top Performers")
                        if t_top:
                            wc = WordCloud(width=400, height=300, background_color='white', stopwords=stopwords_it).generate(t_top)
                            fig, ax = plt.subplots()
                            ax.imshow(wc, interpolation='bilinear')
                            ax.axis('off')
                            st.pyplot(fig)
                        else: st.warning("No text for Top")
                    
                    with col2:
                        st.markdown("### Bottom Performers")
                        if t_bot:
                            wc = WordCloud(width=400, height=300, background_color='white', stopwords=stopwords_it).generate(t_bot)
                            fig, ax = plt.subplots()
                            ax.imshow(wc, interpolation='bilinear')
                            ax.axis('off')
                            st.pyplot(fig)
                        else: st.warning("No text for Bottom")
    except Exception as e:
        st.error(f"Errore generazione Word Cloud: {e}")
else:
    st.warning("Install wordcloud: pip install wordcloud")
