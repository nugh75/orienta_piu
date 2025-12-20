# 🔬 Analisi Avanzate - Statistiche e Clustering

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import glob

st.set_page_config(page_title="Analisi Avanzate", page_icon="🔬", layout="wide")

SUMMARY_FILE = 'data/analysis_summary.csv'

LABEL_MAP = {
    'mean_finalita': 'Media Finalità',
    'mean_obiettivi': 'Media Obiettivi', 
    'mean_governance': 'Media Governance',
    'mean_didattica_orientativa': 'Media Didattica',
    'mean_opportunita': 'Media Opportunità',
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

st.markdown("---")

# 1. Clustering
st.subheader("🎯 Cluster Analysis (K-Means)")
try:
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
    from sklearn.decomposition import PCA
    
    cluster_cols = ['mean_finalita', 'mean_obiettivi', 'mean_governance', 'mean_didattica_orientativa', 'mean_opportunita']
    if all(c in df.columns for c in cluster_cols) and len(df) >= 6:
        X = df[cluster_cols].dropna()
        if len(X) >= 6:
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            n_clusters = min(3, len(X) // 2)
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            clusters = kmeans.fit_predict(X_scaled)
            
            pca = PCA(n_components=2)
            X_pca = pca.fit_transform(X_scaled)
            
            cluster_df = pd.DataFrame({
                'PC1': X_pca[:, 0], 'PC2': X_pca[:, 1],
                'Cluster': [f'Cluster {c+1}' for c in clusters],
                'Scuola': df.loc[X.index, 'denominazione'].values if 'denominazione' in df.columns else X.index
            })
            
            fig = px.scatter(cluster_df, x='PC1', y='PC2', color='Cluster', hover_data=['Scuola'],
                           title=f"Clustering ({n_clusters} gruppi)")
            st.plotly_chart(fig, use_container_width=True)
            
            # Cluster means table
            df_clust = df.loc[X.index].copy()
            df_clust['Cluster'] = [f'Cluster {c+1}' for c in clusters]
            cluster_means = df_clust.groupby('Cluster')[cluster_cols].mean()
            cluster_means.columns = [get_label(c) for c in cluster_cols]
            st.dataframe(cluster_means.round(2), use_container_width=True)
        else:
            st.info("Servono almeno 6 scuole")
    else:
        st.info("Dati insufficienti per il clustering")
except ImportError:
    st.warning("Installa scikit-learn: pip install scikit-learn")

st.markdown("---")

# 2. ANOVA
st.subheader("📊 ANOVA: Test Differenze tra Gruppi")
try:
    from scipy import stats
    
    results = []
    test_vars = [
        ('area_geografica', 'Area Geografica'),
        ('ordine_grado', 'Ordine Grado'),
        ('tipo_scuola', 'Tipo Scuola'),
        ('territorio', 'Territorio')
    ]
    
    for col, label in test_vars:
        if col in df.columns and 'ptof_orientamento_maturity_index' in df.columns:
            groups = [g['ptof_orientamento_maturity_index'].dropna().values 
                     for _, g in df.groupby(col) if len(g) >= 2]
            if len(groups) >= 2:
                f_stat, p_val = stats.f_oneway(*groups)
                sig = "✅" if p_val < 0.05 else "⚪"
                results.append({'Confronto': label, 'F': f"{f_stat:.2f}", 
                               'p-value': f"{p_val:.4f}", 'Sig.': sig})
    
    if results:
        st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)
        st.caption("ANOVA one-way. p < 0.05 = differenza significativa")
    else:
        st.info("Dati insufficienti per ANOVA")
except ImportError:
    st.warning("scipy non disponibile")

st.markdown("---")

# 3. Correlation Heatmap
st.subheader("🔥 Heatmap Correlazioni")
score_cols = [c for c in df.columns if '_score' in c and 'mean' not in c][:15]
if len(score_cols) >= 5 and len(df) >= 5:
    corr = df[score_cols].corr()
    labels = [get_label(c)[:20] for c in score_cols]
    
    fig = px.imshow(corr.values, x=labels, y=labels, color_continuous_scale='RdBu_r',
                   zmin=-1, zmax=1, text_auto='.1f', title="Correlazioni tra Dimensioni")
    fig.update_layout(height=600)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Servono almeno 5 scuole per le correlazioni")

st.markdown("---")

# 4. Violin Plot
st.subheader("🎻 Violin Plot per Tipo Scuola")
if 'tipo_scuola' in df.columns:
    fig = px.violin(df, x='tipo_scuola', y='ptof_orientamento_maturity_index',
                   color='tipo_scuola', box=True, points='all',
                   title="Distribuzione per Tipo Scuola")
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

# 6. Word Cloud
st.subheader("☁️ Word Cloud Partnership")
try:
    from wordcloud import WordCloud
    import matplotlib.pyplot as plt
    import json
    
    all_partners = []
    json_files = glob.glob('analysis_results/*_analysis.json')
    for jf in json_files[:50]:
        try:
            with open(jf, 'r') as f:
                data = json.load(f)
                partners = data.get('ptof_section2', {}).get('2_2_partnership', {}).get('partner_nominati', [])
                all_partners.extend(partners)
        except:
            pass
    
    if all_partners:
        wc = WordCloud(width=800, height=400, background_color='white', max_words=50).generate(' '.join(all_partners))
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.imshow(wc, interpolation='bilinear')
        ax.axis('off')
        st.pyplot(fig)
        st.caption(f"Basato su {len(all_partners)} partnership")
    else:
        st.info("Nessun dato partnership disponibile")
except ImportError:
    st.info("Installa wordcloud: pip install wordcloud")
except Exception as e:
    st.info(f"Word cloud non disponibile: {e}")
