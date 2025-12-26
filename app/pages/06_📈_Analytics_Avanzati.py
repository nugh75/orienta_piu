# 📈 Analytics Avanzati - Clustering, Correlazioni e Visualizzazioni Sperimentali
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import glob
from collections import Counter
from app.data_utils import (
    get_label,
    LABEL_MAP_SHORT as LABEL_MAP,
    TIPI_SCUOLA,
    explode_school_types,
    explode_school_grades,
    render_footer,
)
from app.page_control import setup_page

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

st.set_page_config(page_title="ORIENTA+ | Analytics Avanzati", page_icon="🧭", layout="wide")
setup_page("pages/06_📈_Analytics_Avanzati.py")

SUMMARY_FILE = 'data/analysis_summary.csv'


@st.cache_data(ttl=60)
def load_data():
    if os.path.exists(SUMMARY_FILE):
        return pd.read_csv(SUMMARY_FILE)
    return pd.DataFrame()


def categorize_maturity(val):
    if pd.isna(val):
        return "ND"
    if val < 3.5:
        return "Bassa (<3.5)"
    if val <= 5.5:
        return "Media (3.5-5.5)"
    return "Alta (>5.5)"


df = load_data()

st.title("📈 Analytics Avanzati")

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

tab_cluster, tab_visual = st.tabs(["🔬 Clustering e Correlazioni", "🕸️ Visualizzazioni Avanzate"])

with tab_cluster:
    st.title("🔬 Clustering e Correlazioni")

    with st.expander("📖 Come leggere questa pagina", expanded=False):
        st.markdown("""
        ### 🎯 Scopo della Pagina
        Questa pagina offre **analisi statistiche sofisticate** per scoprire pattern nascosti nei dati, includendo correlazioni, clustering e text mining.
        
        ### 📊 Sezioni Disponibili
        
        **🔥 Matrice di Correlazione**
        - Mostra quanto le 5 dimensioni si "muovono insieme"
        - Valori da -1 a +1:
          - **+1 (rosso)**: Correlazione positiva perfetta
          - **0 (bianco)**: Nessuna relazione
          - **-1 (blu)**: Correlazione negativa perfetta
        - Es: Se Governance correla 0.8 con Didattica, scuole forti in governance tendono a essere forti anche in didattica
        
        **🧩 Clustering K-Means**
        - Raggruppa le scuole in cluster simili automaticamente
        - Ogni cluster rappresenta un "profilo tipo" di scuola
        - La visualizzazione PCA riduce le dimensioni per mostrare i gruppi
        
        **☁️ Word Cloud**
        - Visualizza le parole più frequenti nei report
        - Dimensione maggiore = parola più ricorrente
        
        **📦 Distribuzioni**
        - Istogrammi che mostrano come si distribuiscono i punteggi
        - Utile per capire se ci sono gruppi distinti o una distribuzione normale
        
        ### 🔢 Interpretazione Test Statistici
        - **p-value < 0.05**: Risultato statisticamente significativo
        - **Correlazione r > 0.7**: Forte relazione tra variabili
        - **Silhouette Score**: Qualità del clustering (più alto = cluster più definiti)
        """)

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

    with st.expander("📘 Guida alla lettura: Matrice di Correlazione"):
        st.markdown("""
        **Cosa mostra?**
        Indica quanto due dimensioni si "muovono insieme".
        
        **Come leggere i colori:**
        - 🟥 **Rosso (+1):** Correlazione positiva forte. Se una scuola è forte in X, tende ad essere forte anche in Y.
        - 🟦 **Blu (-1):** Correlazione negativa. Se X sale, Y scende.
        - ⬜ **Bianco (0):** Nessuna relazione apparente.
        """)

    st.info("""
    💡 **A cosa serve**: Mostra quali dimensioni dell'orientamento "vanno insieme" - se una scuola è forte in una, tende a esserlo anche nell'altra?
    
    🔍 **Cosa rileva**: Valori vicini a +1 (rosso) indicano correlazione positiva forte: le dimensioni si muovono insieme. Valori vicini a 0 (bianco) indicano indipendenza.
    
    🎯 **Implicazioni**: Se due dimensioni correlano fortemente, intervenire su una potrebbe migliorare anche l'altra. Es: se Governance e Didattica correlano 0.8, migliorare l'organizzazione potrebbe riflettersi sulla didattica orientativa.
    """)

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
            if len(target_cols) > 20:
                height = 1000
            
            fig_sub = px.imshow(corr_show.values, x=sub_labels, y=sub_labels, color_continuous_scale='RdBu',
                        zmin=-1, zmax=1, title=f"Correlazioni: {selected_sub}")
            fig_sub.update_traces(text=corr_show.round(2).values, texttemplate="%{text}")
            fig_sub.update_layout(height=height)

            st.plotly_chart(fig_sub, use_container_width=True)
    else:
        st.info("Dati insufficienti per le correlazioni di dettaglio stabilite.")

    st.info("""
    💡 **A cosa serve**: Esplora le correlazioni tra i singoli indicatori all'interno di ciascuna dimensione.
    
    🔍 **Cosa rileva**: Ogni cella mostra quanto due sotto-indicatori sono correlati. Puoi filtrare per dimensione specifica e per soglia minima di correlazione. Utile per capire quali indicatori "vanno insieme".
    
    🎯 **Implicazioni**: Correlazioni forti tra sotto-dimensioni suggeriscono che migliorare un aspetto specifico potrebbe influenzare altri. Aiuta a identificare interventi mirati.
    """)

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
                    
                with st.expander("📘 Guida alla lettura: Clustering e PCA", expanded=False):
                    st.markdown("""
                    **Cosa sono i Cluster?**
                    Sono gruppi di scuole simili create automaticamente dall'algoritmo matematico.
                    - Il grafico a dispersione (**PCA**) mostra le scuole nello spazio: più sono vicine, più i loro PTOF sono simili.
                    - La **Heatmap a destra** ti dice *perché* sono simili: mostra i punteggi medi di ogni gruppo.
                    """)
                
                st.info("""
    💡 **A cosa serve**: Raggruppa automaticamente le scuole in "famiglie" con caratteristiche simili, senza pregiudizi.
    
    🔍 **Cosa rileva**: Nel grafico, scuole vicine hanno PTOF simili. I colori indicano i cluster (gruppi). La heatmap mostra il "profilo tipo" di ogni gruppo.
    
    🎯 **Implicazioni**: Identifica "tipi" di scuole non basati su etichette tradizionali (Liceo/Tecnico) ma sui contenuti reali. Utile per creare programmi di supporto mirati per ogni "famiglia".
    """)
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
        import numpy as np
        results = []
        significant_tests = []  # Per memorizzare i test significativi
        test_vars = [
            ('area_geografica', 'Area Geografica'),
            ('ordine_grado', 'Ordine Grado'),
            ('tipo_scuola', 'Tipo Scuola'),
            ('territorio', 'Territorio')
        ]
        
        if 'tipo_scuola' in df.columns:
            df_types = explode_school_types(df)
            df_types = df_types[df_types['tipo_scuola'].isin(TIPI_SCUOLA)]
            df_grades = explode_school_grades(df)
        else:
            df_types = df
            df_grades = df
        
        for col, label in test_vars:
            if col == 'tipo_scuola':
                target_df = df_types
            elif col == 'ordine_grado':
                target_df = df_grades
            else:
                target_df = df
            
            if col in target_df.columns and 'ptof_orientamento_maturity_index' in target_df.columns:
                groups = []
                group_names = []
                for name, g in target_df.groupby(col):
                    vals = g['ptof_orientamento_maturity_index'].dropna().values
                    if len(vals) >= 2:
                        groups.append(vals)
                        group_names.append(str(name))
                
                if len(groups) >= 2:
                    f_stat, p_val = stats.f_oneway(*groups)
                    sig = "✅" if p_val < 0.05 else "⚪"
                    results.append({'Confronto': label, 'F': f"{f_stat:.2f}",
                                   'p-value': f"{p_val:.4f}", 'Sig.': sig})
                    
                    # Salva info per analisi post-hoc se significativo
                    if p_val < 0.05:
                        significant_tests.append({
                            'label': label,
                            'col': col,
                            'groups': groups,
                            'group_names': group_names,
                            'f_stat': f_stat,
                            'p_val': p_val
                        })
        
        if results:
            st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)
            
            # === POST-HOC ANALYSIS per i test significativi ===
            if significant_tests:
                st.markdown("---")
                st.markdown("### 🎯 Analisi Post-Hoc: A favore di chi?")
                st.caption("Per ogni confronto significativo, il test Tukey HSD identifica quali gruppi differiscono")
                
                for test_info in significant_tests:
                    label = test_info['label']
                    groups = test_info['groups']
                    group_names = test_info['group_names']
                    
                    with st.expander(f"📊 **{label}** - Dettaglio confronti", expanded=True):
                        try:
                            from scipy.stats import tukey_hsd
                            
                            # Perform Tukey HSD test
                            tukey_result = tukey_hsd(*groups)
                            
                            # Build pairwise comparison results
                            significant_pairs = []
                            all_pairs = []
                            
                            for i in range(len(group_names)):
                                for j in range(i + 1, len(group_names)):
                                    mean_i = np.mean(groups[i])
                                    mean_j = np.mean(groups[j])
                                    diff = mean_i - mean_j
                                    p_adj = tukey_result.pvalue[i, j]
                                    
                                    # Determine which group is "better" (higher index)
                                    if diff > 0:
                                        favored = group_names[i]
                                        unfavored = group_names[j]
                                    else:
                                        favored = group_names[j]
                                        unfavored = group_names[i]
                                    
                                    pair_info = {
                                        'Gruppo 1': group_names[i],
                                        'Media 1': f"{mean_i:.2f}",
                                        'Gruppo 2': group_names[j],
                                        'Media 2': f"{mean_j:.2f}",
                                        'Differenza': f"{abs(diff):.2f}",
                                        'p-value adj.': f"{p_adj:.4f}",
                                        'Significativo': '✅' if p_adj < 0.05 else '❌',
                                        'A favore di': favored if p_adj < 0.05 else '-'
                                    }
                                    all_pairs.append(pair_info)
                                    
                                    if p_adj < 0.05:
                                        significant_pairs.append({
                                            'Confronto': f"{favored} vs {unfavored}",
                                            'Gruppo superiore': f"{favored} ({max(mean_i, mean_j):.2f})",
                                            'Gruppo inferiore': f"{unfavored} ({min(mean_i, mean_j):.2f})",
                                            'Differenza': f"{abs(diff):.2f}",
                                            'p-value': f"{p_adj:.4f}"
                                        })
                            
                            # Ranking dei gruppi
                            group_means = {group_names[i]: np.mean(groups[i]) for i in range(len(group_names))}
                            sorted_groups = sorted(group_means.items(), key=lambda x: x[1], reverse=True)
                            
                            col_rank, col_sig = st.columns([1, 2])
                            
                            with col_rank:
                                st.markdown("**🏆 Ranking Gruppi:**")
                                for i, (grp, mean) in enumerate(sorted_groups, 1):
                                    medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else f"{i}."))
                                    st.markdown(f"{medal} **{grp}**: {mean:.2f}")
                            
                            with col_sig:
                                if significant_pairs:
                                    st.markdown("**✅ Confronti Significativi (p < 0.05):**")
                                    sig_df = pd.DataFrame(significant_pairs)
                                    st.dataframe(sig_df, use_container_width=True, hide_index=True)
                                else:
                                    st.info("Nessun confronto tra coppie raggiunge la significatività nel test post-hoc.")
                            
                            # Interpretazione
                            best_group = sorted_groups[0][0]
                            worst_group = sorted_groups[-1][0]
                            st.info(f"📌 **Interpretazione**: Il gruppo con il miglior indice è **{best_group}** ({sorted_groups[0][1]:.2f}), "
                                   f"il peggiore è **{worst_group}** ({sorted_groups[-1][1]:.2f}). "
                                   f"Confronti significativi: **{len(significant_pairs)}/{len(all_pairs)}**.")
                            
                            # Tutti i confronti in dettaglio (opzionale)
                            with st.expander("📋 Tutti i confronti a coppie"):
                                all_pairs_df = pd.DataFrame(all_pairs)
                                all_pairs_df = all_pairs_df.sort_values('p-value adj.')
                                st.dataframe(all_pairs_df, use_container_width=True, hide_index=True)
                                
                        except ImportError:
                            st.warning("⚠️ Test Tukey HSD non disponibile. Aggiorna scipy: `pip install --upgrade scipy`")
                            # Fallback: mostra solo ranking
                            group_means = {group_names[i]: np.mean(groups[i]) for i in range(len(group_names))}
                            sorted_groups = sorted(group_means.items(), key=lambda x: x[1], reverse=True)
                            st.markdown("**📊 Ranking dei Gruppi:**")
                            for i, (grp, mean) in enumerate(sorted_groups, 1):
                                st.markdown(f"{i}. **{grp}**: {mean:.2f}")
                        except Exception as e:
                            st.warning(f"⚠️ Errore nel test post-hoc: {e}")
            
            # Detailed ANOVA Explanation
            with st.expander("📘 Guida alla lettura: ANOVA (Analisi delle Varianza)", expanded=False):
                st.markdown("""
                **Che cos'è questo test?**
                L'ANOVA confronta le medie di più gruppi per vedere se sono **statisticamente diverse** tra loro.
                
                **Legenda Indicatori:**
                - **F-value (F):** È il rapporto tra la varianza *tra i gruppi* e la varianza *nei gruppi*.
                    - **F alto**: I gruppi sono molto diversi/distanti tra loro.
                    - **F basso**: I gruppi sono simili o molto sovrapposti.
                - **p-value:** Indica la probabilità che le differenze osservate siano casuali.
                - **Sig. (Significatività):** 
                    - ✅ (p < 0.05): La differenza è statisticamente significativa (reale, non dovuta al caso).
                    - ⚪ (p >= 0.05): Non ci sono prove sufficienti per dire che i gruppi siano diversi.
                """)
            
            st.info("""
    💡 **A cosa serve**: Verifica scientificamente se le differenze tra gruppi (es. Nord vs Sud, Licei vs Tecnici) sono reali o dovute al caso.
    
    🔍 **Cosa rileva**: Le righe con ✅ indicano differenze statisticamente significative: quel raggruppamento crea davvero differenze nei punteggi. I test post-hoc dicono QUALI gruppi specifici differiscono.
    
    🎯 **Implicazioni**: Se il tipo di scuola è significativo ma l'area geografica no, significa che il tipo di istituto influenza la qualità dell'orientamento più della posizione geografica. Utile per decidere dove intervenire.
    """)
        else:
            st.info("Dati insufficienti per ANOVA")
    else:
        st.warning("scipy non disponibile")

    st.markdown("---")

    # 4. Violin Plot
    st.subheader("🎻 Distribuzione per Tipo Scuola")
    if 'tipo_scuola' in df.columns:
        df_violin = explode_school_types(df)
        df_violin = df_violin[df_violin['tipo_scuola'].isin(TIPI_SCUOLA)]

        if not df_violin.empty:
            fig = px.violin(
                df_violin, x='tipo_scuola', y='ptof_orientamento_maturity_index',
                color='tipo_scuola', box=True, points='all',
                title="Violin Plot Maturity Index"
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nessun dato valido per le tipologie canoniche")

        with st.expander("📘 Guida alla lettura: Violin Plot"):
            st.markdown("""
            **Che cos'è?**
            Unisce un Box Plot (la scatola nera dentro) con la distribuzione dei dati (la forma colorata).
            - **Forma Larga**: Lì si concentrano molte scuole (alta densità).
            - **Forma Stretta/Lunga**: Poche scuole hanno quei punteggi.
            - **Punto Bianco**: La mediana del gruppo.
            """)

    st.info("""
    💡 **A cosa serve**: Visualizza la distribuzione completa dei punteggi per ogni tipologia scolastica.
    
    🔍 **Cosa rileva**: La forma del "violino" indica dove si concentrano le scuole. Forme larghe = alta densità. Il box interno mostra mediana e quartili. I punti sono le singole scuole.
    
    🎯 **Implicazioni**: Permette di vedere non solo la media ma la forma della distribuzione: se è simmetrica, se ci sono outlier, se esistono sottogruppi. Tipologie con forme diverse hanno caratteristiche diverse.
    """)

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

    st.info("""
    💡 **A cosa serve**: Mostra rapidamente le 5 scuole migliori e le 5 peggiori del campione.
    
    🔍 **Cosa rileva**: Le Top 5 sono modelli di eccellenza da studiare. Le Bottom 5 potrebbero necessitare di supporto prioritario. La differenza tra i due gruppi indica l'ampiezza del gap.
    
    🎯 **Implicazioni**: Le scuole eccellenti possono essere contattate per scambi di buone pratiche. Quelle in difficoltà potrebbero beneficiare di interventi mirati.
    """)

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
            activity_titles = []  # For Word Cloud
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
                except Exception:
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
                        fig.update_layout(yaxis={'categoryorder': 'total ascending'})
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("Nessuna attività")
                
                with col2:
                    st.markdown("#### 🤝 Partner Principali")
                    if collaboration_types:
                        counts = Counter(collaboration_types)
                        df_collab = pd.DataFrame(counts.most_common(15), columns=['Partner', 'N'])
                        fig = px.bar(df_collab, x='N', y='Partner', orientation='h', title="Top Partner")
                        fig.update_layout(yaxis={'categoryorder': 'total ascending'})
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

    st.info("""
    💡 **A cosa serve**: Analizza quali attività e partner sono più frequenti nei PTOF analizzati.
    
    🔍 **Cosa rileva**: I grafici a barre mostrano le categorie di attività e i partner più citati. Le Word Cloud visualizzano le parole più frequenti nei titoli delle attività e nei nomi dei partner.
    
    🎯 **Implicazioni**: Identifica pattern comuni nelle collaborazioni e nelle attività. Partner ricorrenti potrebbero essere best practice da replicare. Categorie poco presenti potrebbero indicare aree da sviluppare.
    """)

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
                                except Exception:
                                    pass
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
                            else:
                                st.warning("No text for Top")
                        
                        with col2:
                            st.markdown("### Bottom Performers")
                            if t_bot:
                                wc = WordCloud(width=400, height=300, background_color='white', stopwords=stopwords_it).generate(t_bot)
                                fig, ax = plt.subplots()
                                ax.imshow(wc, interpolation='bilinear')
                                ax.axis('off')
                                st.pyplot(fig)
                            else:
                                st.warning("No text for Bottom")

        except Exception as e:
            st.error(f"Errore generazione Word Cloud: {e}")
    else:
        st.warning("Install wordcloud: pip install wordcloud")

    st.info("""
    💡 **A cosa serve**: Confronta il linguaggio usato nei PTOF delle scuole eccellenti rispetto a quelle in difficoltà.
    
    🔍 **Cosa rileva**: Le Word Cloud mostrano le parole più frequenti nei documenti del 20% migliore (Top Performers) vs il 20% peggiore (Bottom Performers). Parole più grandi = più frequenti.
    
    🎯 **Implicazioni**: Se le scuole eccellenti usano termini specifici (es. "competenze", "orientamento") più frequentemente, potrebbero essere indicatori di qualità. Differenze lessicali suggeriscono approcci diversi alla documentazione.
    """)

    # === NUOVA SEZIONE: DEBOLEZZE SISTEMICHE ===
    st.markdown("---")
    st.subheader("📉 Debolezze Sistemiche Nazionali")
    st.caption("Pattern di debolezza ricorrenti per tipo scuola e ordine grado")

    # Sotto-indicatori per analisi dettagliata
    SUB_INDICATORS = {
        'Finalità': {
            '2_3_finalita_attitudini_score': 'Attitudini',
            '2_3_finalita_interessi_score': 'Interessi',
            '2_3_finalita_progetto_vita_score': 'Progetto di Vita',
            '2_3_finalita_transizioni_formative_score': 'Transizioni',
            '2_3_finalita_capacita_orientative_opportunita_score': 'Capacità Orientative'
        },
        'Obiettivi': {
            '2_4_obiettivo_ridurre_abbandono_score': 'Ridurre Abbandono',
            '2_4_obiettivo_continuita_territorio_score': 'Continuità Territorio',
            '2_4_obiettivo_contrastare_neet_score': 'Contrastare NEET',
            '2_4_obiettivo_lifelong_learning_score': 'Lifelong Learning'
        },
        'Governance': {
            '2_5_azione_coordinamento_servizi_score': 'Coordinamento',
            '2_5_azione_dialogo_docenti_studenti_score': 'Dialogo Doc-Stud',
            '2_5_azione_rapporto_scuola_genitori_score': 'Rapporto Genitori',
            '2_5_azione_monitoraggio_azioni_score': 'Monitoraggio',
            '2_5_azione_sistema_integrato_inclusione_fragilita_score': 'Inclusione'
        },
        'Didattica': {
            '2_6_didattica_da_esperienza_studenti_score': 'Esperienza',
            '2_6_didattica_laboratoriale_score': 'Laboratoriale',
            '2_6_didattica_flessibilita_spazi_tempi_score': 'Flessibilità',
            '2_6_didattica_interdisciplinare_score': 'Interdisciplinare'
        },
        'Opportunità': {
            '2_7_opzionali_culturali_score': 'Culturali',
            '2_7_opzionali_laboratoriali_espressive_score': 'Espressive',
            '2_7_opzionali_ludiche_ricreative_score': 'Ludiche',
            '2_7_opzionali_volontariato_score': 'Volontariato',
            '2_7_opzionali_sportive_score': 'Sportive'
        }
    }

    # Calcola medie nazionali per ogni sotto-indicatore
    all_sub_cols = []
    for dim, subs in SUB_INDICATORS.items():
        all_sub_cols.extend(subs.keys())

    # Converti a numerico
    for col in all_sub_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Identifica le debolezze sistemiche (sotto la media nazionale)
    weaknesses = []
    national_means = {}

    for dim, subs in SUB_INDICATORS.items():
        for col, label in subs.items():
            if col in df.columns:
                mean_val = df[col].mean()
                national_means[col] = mean_val
                # Considera debole se media < 3.5 (sotto sufficienza)
                if mean_val < 3.5:
                    weaknesses.append({
                        'Dimensione': dim,
                        'Indicatore': label,
                        'Colonna': col,
                        'Media Nazionale': mean_val,
                        'Criticità': 'Alta' if mean_val < 2.5 else 'Media' if mean_val < 3.5 else 'Bassa'
                    })

    # Ordina per media
    weaknesses = sorted(weaknesses, key=lambda x: x['Media Nazionale'])

    if weaknesses:
        st.markdown("### 🔴 Aree Critiche a Livello Nazionale")
        
        # Top 5 debolezze
        top_weak = weaknesses[:5]
        
        cols = st.columns(5)
        for i, w in enumerate(top_weak):
            with cols[i]:
                color = "#dc3545" if w['Criticità'] == 'Alta' else "#ffc107"
                st.markdown(f"""
                <div style="background-color: {color}; padding: 10px; border-radius: 8px; text-align: center; color: white;">
                    <strong>{w['Indicatore']}</strong><br>
                    <span style="font-size: 1.5em;">{w['Media Nazionale']:.2f}</span><br>
                    <small>{w['Dimensione']}</small>
                </div>
                """, unsafe_allow_html=True)
        
        # Heatmap debolezze per tipo scuola
        st.markdown("### 📊 Mappa Debolezze per Tipo Scuola")
        
        tipi_scuola = ['Liceo', 'Tecnico', 'Professionale', 'Primaria', 'I Grado', 'Infanzia']
        weak_cols = [w['Colonna'] for w in weaknesses[:10]]
        weak_labels = [w['Indicatore'] for w in weaknesses[:10]]
        
        heatmap_data = []
        for tipo in tipi_scuola:
            df_tipo = df[df['tipo_scuola'].str.contains(tipo, na=False, case=False)]
            if len(df_tipo) > 0:
                row = {'Tipo': tipo}
                for col, label in zip(weak_cols, weak_labels):
                    if col in df_tipo.columns:
                        row[label] = df_tipo[col].mean()
                heatmap_data.append(row)
        
        if heatmap_data:
            hm_df = pd.DataFrame(heatmap_data).set_index('Tipo')
            
            fig_hm = px.imshow(
                hm_df.values,
                x=hm_df.columns.tolist(),
                y=hm_df.index.tolist(),
                color_continuous_scale='RdYlGn',
                aspect='auto',
                title="Media per Tipo Scuola (Verde=Alto, Rosso=Basso)"
            )
            fig_hm.update_layout(
                xaxis_title="Indicatore",
                yaxis_title="Tipo Scuola"
            )
            st.plotly_chart(fig_hm, use_container_width=True)
        
        # Analisi correlazione debolezze
        st.markdown("### 🔗 Correlazione tra Debolezze")
        st.caption("Le debolezze tendono a presentarsi insieme?")
        
        weak_col_list = [w['Colonna'] for w in weaknesses[:8]]
        weak_label_list = [w['Indicatore'] for w in weaknesses[:8]]
        
        if len(weak_col_list) >= 2:
            corr_weak = df[weak_col_list].corr()
            corr_weak.columns = weak_label_list
            corr_weak.index = weak_label_list
            
            fig_corr = px.imshow(
                corr_weak,
                color_continuous_scale='RdBu_r',
                aspect='auto',
                title="Correlazione tra Indicatori Deboli"
            )
            st.plotly_chart(fig_corr, use_container_width=True)
            
            # Trova coppie fortemente correlate
            strong_pairs = []
            for i, col1 in enumerate(weak_col_list):
                for j, col2 in enumerate(weak_col_list):
                    if i < j:
                        corr_val = df[[col1, col2]].corr().iloc[0, 1]
                        if corr_val > 0.6:
                            strong_pairs.append({
                                'Indicatore 1': weak_label_list[i],
                                'Indicatore 2': weak_label_list[j],
                                'Correlazione': corr_val
                            })
            
            if strong_pairs:
                st.markdown("**Debolezze che tendono a presentarsi insieme:**")
                for pair in sorted(strong_pairs, key=lambda x: x['Correlazione'], reverse=True)[:3]:
                    st.markdown(f"- {pair['Indicatore 1']} ↔ {pair['Indicatore 2']} (r={pair['Correlazione']:.2f})")
        
        st.info("""
        💡 **A cosa serve**: Identifica le aree di debolezza sistemica a livello nazionale, evidenziando problemi strutturali.
        
        🔍 **Cosa rileva**: Gli indicatori con media < 3.5 rappresentano aree critiche. La mappa per tipo scuola mostra se alcune tipologie sono più vulnerabili in specifiche aree. Le correlazioni rivelano se le debolezze si presentano in cluster.
        
        🎯 **Implicazioni**: Debolezze sistemiche richiedono interventi di policy a livello nazionale. Correlazioni forti tra debolezze suggeriscono cause comuni da affrontare in modo integrato.
        """)

    else:
        st.success("✅ Nessuna area critica sistemica identificata (tutte le medie ≥ 3.5)")

    st.markdown("---")
    st.caption("🔬 Clustering e Correlazioni - Analisi avanzata dei pattern")

with tab_visual:
    st.title("🧪 Analisi Sperimentali")

    with st.expander("📖 Come leggere questa pagina", expanded=False):
        st.markdown("""
        ### 🎯 Scopo della Pagina
        Questa pagina contiene visualizzazioni **sperimentali** per esplorare i dati con metodologie innovative e meno convenzionali.
        
        ### 📊 Sezioni Disponibili
        
        **🕸️ Radar Chart Comparativo**
        - Confronta il **profilo multidimensionale** di una scuola con la media nazionale
        - Ogni vertice rappresenta una delle 5 dimensioni:
          - **Finalità**: Chiarezza degli scopi dell'orientamento
          - **Obiettivi**: Concretezza e misurabilità dei target
          - **Governance**: Organizzazione e responsabilità
          - **Didattica**: Integrazione dell'orientamento nella didattica
          - **Opportunità**: Collegamenti con territorio e mondo del lavoro
        - L'area colorata della scuola (blu) si sovrappone alla media (grigio)
        - **Interpretazione**: Se l'area blu sporge oltre il grigio, la scuola eccelle in quella dimensione
        
        **🌊 Analisi dei Flussi (Sankey/Sunburst)**
        - Visualizza le **relazioni gerarchiche** tra caratteristiche
        - Mostra come regione → tipo scuola → punteggio si collegano
        - **Spessore delle bande**: Proporzionale al numero di scuole o al valore
        - Utile per identificare pattern geografici e tipologici
        
        **📊 Sunburst Chart**
        - Visualizzazione gerarchica a "raggiera"
        - Dal centro verso l'esterno: macro-categoria → sotto-categoria → dettaglio
        - Clicca su una sezione per "zoomare" su quel livello
        
        ### 🔢 Come Interpretare i Radar
        - **Forma regolare** (pentagono uniforme): Performance equilibrata su tutte le dimensioni
        - **Forma irregolare**: Punti di forza e debolezza specifici
        - **Area piccola**: Performance generale bassa
        - **Area grande**: Performance generale alta
        """)

    st.markdown("""
    Questa pagina contiene visualizzazioni **sperimentali** per esplorare i dati in modo diverso.
    1. **Radar Chart**: Confronta il profilo di una scuola con la media nazionale.
    2. **Analisi dei Flussi**: Osserva come le caratteristiche geografiche influenzano la robustezza dell'orientamento.
    """)

    # --- 1. RADAR CHART ---
    st.markdown("---")
    st.subheader("🕸️ Analisi Comparativa (Radar Chart)")
    st.caption("Confronta il posizionamento di una singola scuola rispetto alla media complessiva.")

    # Select School
    # Ensure we have a label for selection
    if 'denominazione' in df.columns and 'school_id' in df.columns:
        df['label_select'] = df['denominazione'].fillna('').astype(str) + " (" + df['school_id'].fillna('').astype(str) + ")"
    else:
        df['label_select'] = df.index.astype(str)

    school_options = sorted(df['label_select'].dropna().astype(str).unique().tolist())
    selected_school_label = st.selectbox("Seleziona una Scuola per il confronto", school_options)

    if selected_school_label:
        school_row = df[df['label_select'] == selected_school_label].iloc[0]
        
        # Dimensions to plot
        dims = ['mean_finalita', 'mean_obiettivi', 'mean_governance', 'mean_didattica_orientativa', 'mean_opportunita']
        
        # Check if dimensions exist
        if all(d in df.columns for d in dims):
            # Prepare Data
            # 1. School Values
            school_vals = [school_row.get(d, 0) for d in dims]
            
            # 2. Average Values (Global)
            avg_vals = [df[d].mean() for d in dims]
            
            # Close the loop for Radar Chart
            dims_labels = [get_label(d) for d in dims]
            
            fig = go.Figure()

            # Trace 1: Average
            fig.add_trace(go.Scatterpolar(
                r=avg_vals + [avg_vals[0]],
                theta=dims_labels + [dims_labels[0]],
                fill='toself',
                name='Media Nazionale',
                line_color='gray',
                opacity=0.4
            ))

            # Trace 2: Selected School
            fig.add_trace(go.Scatterpolar(
                r=school_vals + [school_vals[0]],
                theta=dims_labels + [dims_labels[0]],
                fill='toself',
                name=school_row['denominazione'],
                line_color='#FF4B4B'  # Streamlit Red
            ))

            fig.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, 5]  # Assuming scale 1-5
                    )
                ),
                showlegend=True,
                title=f"Profilo vs Media: {school_row['denominazione']}"
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Textual Insight
            st.markdown("##### 💡 Insight Rapido")
            diffs = []
            for d, v_school, v_avg in zip(dims_labels, school_vals, avg_vals):
                delta = v_school - v_avg
                if delta > 0.5:
                    diffs.append(f"**{d}**: +{delta:.2f} sopra la media")
                elif delta < -0.5:
                    diffs.append(f"**{d}**: {delta:.2f} sotto la media")
            
            if diffs:
                for d in diffs:
                    st.write(f"- {d}")
            else:
                st.write("La scuola è allineata alla media nazionale su tutte le dimensioni.")
            
            st.info("""
    💡 **A cosa serve**: Confronta visivamente una singola scuola con la media nazionale su tutte le dimensioni.
    
    🔍 **Cosa rileva**: L'area rossa è la scuola selezionata, quella grigia è la media. Dove il rosso "sporge", la scuola eccelle. Dove è "dentro" al grigio, c'è margine di miglioramento.
    
    🎯 **Implicazioni**: Utile per autovalutazione e comunicazione. Puoi mostrare a genitori e stakeholder dove la scuola si distingue e dove sta lavorando per migliorare.
    """)

        else:
            st.error("Le colonne delle dimensioni (mean_finalita, etc.) mancano nel dataset.")

    # --- 2. PARALLEL CATEGORIES ---
    st.markdown("---")
    st.subheader("🌊 Flussi: Geografica → Tipo Scuola → Robustezza")
    st.caption("Visualizza come si distribuiscono le scuole tra aree geografiche, tipologie e Indice RO.")

    with st.expander("ℹ️ Come leggere questo grafico (Clicca per aprire)", expanded=True):
        st.markdown("""
        Questo grafico (**Parallel Categories**) mostra i "flussi" di scuole attraverso diverse categorie:
        1.  **Sinistra (Area)**: Da dove partono le scuole (Nord, Sud).
        2.  **Centro (Tipo)**: Che tipo di scuola sono (Liceo, Tecnico, Comprensivo, ecc.).
        3.  **Destra (Robustezza)**: Qual è il loro punteggio di robustezza nell'orientamento (Basso, Medio, Alto).

        **Cosa osservare:**
        - Le **linee (nastri)** collegati mostrano quante scuole seguono quel percorso.
        - **Spessore**: Più spesso è il nastro, più scuole ci sono in quel gruppo.
        - Esempio: Se vedi un grosso nastro che va da "Sud" a "Liceo" e poi finisce in "Alta", significa che molti Licei del Sud hanno un punteggio alto.
        """)

    target_cols = ['area_geografica', 'tipo_scuola', 'ptof_orientamento_maturity_index']

    if all(c in df.columns for c in target_cols):
        # Binning Maturity Index
        df['Livello Robustezza'] = df['ptof_orientamento_maturity_index'].apply(categorize_maturity)
        
        # Prepare dataframe for plotting
        # We remove rows with critical missing values for cleaner viz
        df_flow = df[['area_geografica', 'tipo_scuola', 'Livello Robustezza']].dropna()
        
        # Simplify School Types if too many unique values exist (optional, but good for display)
        # Just taking the first part if it's a comma separated list often happens
        df_flow['tipo_scuola'] = df_flow['tipo_scuola'].apply(lambda x: x.split(',')[0] if isinstance(x, str) else x)
        df_flow = df_flow[df_flow['tipo_scuola'].isin(TIPI_SCUOLA)]
        
        if not df_flow.empty:
            # Sort for better color flow stability
            df_flow = df_flow.sort_values(by=['area_geografica', 'Livello Robustezza'])
            
            # Map area to numbers for coloring (Parcats requires numbers for color scale)
            df_flow['area_code'] = df_flow['area_geografica'].astype('category').cat.codes

            fig_flow = px.parallel_categories(
                df_flow,
                dimensions=['area_geografica', 'tipo_scuola', 'Livello Robustezza'],
                color='area_code',  # Use numeric code for color
                color_continuous_scale=px.colors.sequential.Inferno,
                labels={
                    'area_geografica': 'Area Geografica',
                    'tipo_scuola': 'Tipo Scuola',
                    'Livello Robustezza': 'Livello Robustezza PTOF',
                    'area_code': 'Codice Area'
                }
            )
            # Hide the colorbar as it shows numbers
            fig_flow.update_layout(coloraxis_showscale=False)
            
            # Improve readability
            fig_flow.update_traces(
                labelfont=dict(size=24, color="black", family="Arial Black"),  # Bigger and bolder headers
                tickfont=dict(size=18, color="black"),  # Bigger category labels
            )
            
            # Layout più largo e con margini laterali maggiori per evitare il taglio delle etichette
            fig_flow.update_layout(width=1000, height=1000, margin=dict(l=150, r=150, t=60, b=20))
            
            # Centering using columns
            col1, col2, col3 = st.columns([1, 10, 1])
            with col2:
                st.plotly_chart(fig_flow, use_container_width=False)
            
            st.info("""
    💡 **A cosa serve**: Visualizza come le scuole si distribuiscono attraverso diverse categorie (area → tipo → livello di robustezza).
    
    🔍 **Cosa rileva**: I nastri collegano le categorie. Lo spessore indica quante scuole seguono quel "percorso". Es: un nastro spesso da "Sud" a "Professionale" a "Bassa" indica molte scuole con quella combinazione.

    🎯 **Implicazioni**: Identifica combinazioni virtuose (nastri che arrivano in "Alta") e critiche (nastri verso "Bassa"). Utile per capire se certe tipologie o aree hanno sistematicamente problemi.
    """)
        else:
            st.info("Nessun dato valido per le tipologie canoniche nel grafico dei flussi.")

    else:
        st.warning("Dati mancanti per generare il grafico dei flussi (Area, Tipo o Indice).")

    # --- 3. SUNBURST CHART ---
    st.markdown("---")
    st.subheader("🌞 Gerarchia (Sunburst)")
    st.caption("Esplora la distribuzione gerarchica: Area Geografica → Tipo Scuola → Livello Robustezza.")

    # Ensure 'Livello Robustezza' exists if not created above
    if 'Livello Robustezza' not in df.columns and 'ptof_orientamento_maturity_index' in df.columns:
        df['Livello Robustezza'] = df['ptof_orientamento_maturity_index'].apply(categorize_maturity)

    if all(c in df.columns for c in ['area_geografica', 'tipo_scuola', 'Livello Robustezza']):
        # Filter out ND or empty
        df_sun = df.dropna(subset=['area_geografica', 'tipo_scuola', 'Livello Robustezza']).copy()
        
        # Simple normalization for Tipo Scuola
        df_sun['tipo_scuola'] = df_sun['tipo_scuola'].apply(lambda x: x.split(',')[0] if isinstance(x, str) else x)
        df_sun = df_sun[df_sun['tipo_scuola'].isin(TIPI_SCUOLA)]
        
        if not df_sun.empty:
            fig_sun = px.sunburst(
                df_sun,
                path=['area_geografica', 'tipo_scuola', 'Livello Robustezza'],
                color='area_geografica',
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_sun.update_layout(height=700, margin=dict(t=0, l=0, r=0, b=0))
            st.plotly_chart(fig_sun, use_container_width=True)
            
            st.info("""
    💡 **A cosa serve**: Esplora la struttura gerarchica dei dati (area → tipo → livello) in modo interattivo.
    
    🔍 **Cosa rileva**: Il centro è il totale, ogni anello esterno aggiunge dettaglio. La dimensione delle "fette" è proporzionale al numero di scuole. Clicca per "zoomare" su una sezione.
    
    🎯 **Implicazioni**: Permette di esplorare i dati in modo intuitivo, scoprendo come si compone il campione. Utile per presentazioni e per capire la struttura del sistema scolastico analizzato.
    """)
        else:
            st.info("Nessun dato valido per le tipologie canoniche nel Sunburst Chart.")
    else:
        st.info("Dati insufficienti per il Sunburst Chart.")

    # --- 4. 3D SCATTER PLOT ---
    st.markdown("---")
    st.subheader("🧊 Spazio 3D (Multidimensionale)")
    st.caption("Esplora le relazioni tra 3 dimensioni contemporaneamente. Ruota il grafico per vedere i cluster!")

    col_x = st.selectbox("Asse X", ['mean_finalita', 'mean_obiettivi', 'mean_governance'], index=0)
    col_y = st.selectbox("Asse Y", ['mean_obiettivi', 'mean_governance', 'mean_didattica_orientativa'], index=2)
    col_z = st.selectbox("Asse Z", ['mean_didattica_orientativa', 'mean_opportunita', 'ptof_orientamento_maturity_index'], index=1)
    col_color = st.selectbox("Colore", ['area_geografica', 'tipo_scuola', 'Livello Robustezza'], index=0)

    if all(c in df.columns for c in [col_x, col_y, col_z, col_color]):
        df_3d = df.copy()
        if col_color == 'tipo_scuola':
            df_3d['tipo_scuola'] = df_3d['tipo_scuola'].apply(
                lambda x: x.split(',')[0] if isinstance(x, str) else x
            )
            df_3d = df_3d[df_3d['tipo_scuola'].isin(TIPI_SCUOLA)]

        if df_3d.empty:
            st.info("Nessun dato valido per le tipologie canoniche nel grafico 3D.")
        else:
            fig_3d = px.scatter_3d(
                df_3d, x=col_x, y=col_y, z=col_z,
                color=col_color,
                hover_name='denominazione',
                opacity=0.7,
                size_max=10
            )
            fig_3d.update_layout(height=700, margin=dict(l=0, r=0, b=0, t=0))
            st.plotly_chart(fig_3d, use_container_width=True)
        
        st.info("""
    💡 **A cosa serve**: Esplora le relazioni tra 3 dimensioni contemporaneamente in uno spazio tridimensionale.
    
    🔍 **Cosa rileva**: Ogni punto è una scuola. Punti raggruppati indicano scuole simili. Ruota il grafico trascinando per vedere da diverse angolazioni. I colori mostrano la categoria selezionata.
    
    🎯 **Implicazioni**: Permette di scoprire cluster "nascosti" che non emergono guardando una dimensione alla volta. Utile per ricerche esplorative e per identificare scuole atipiche.
    """)
    else:
        st.warning("Seleziona colonne valide per generare il grafico 3D.")

    # --- 5. RIDGELINE PLOT ---
    st.markdown("---")
    st.subheader("🌊 Distribuzioni a Onde (Ridgeline)")
    st.caption("Confronta la forma delle distribuzioni dei punteggi tra diverse categorie.")

    # Select Variable and Group
    ridge_var = st.selectbox("Variabile (Punteggio)", ['ptof_orientamento_maturity_index', 'mean_finalita', 'mean_obiettivi', 'mean_didattica_orientativa'], index=0)
    ridge_group = st.selectbox("Raggruppa per", ['area_geografica', 'tipo_scuola', 'Livello Robustezza'], index=0)

    if ridge_var in df.columns and ridge_group in df.columns:
        # Filter cleanup
        df_ridge = df.dropna(subset=[ridge_var, ridge_group]).copy()
        if ridge_group == 'tipo_scuola':
            df_ridge['tipo_scuola'] = df_ridge['tipo_scuola'].apply(lambda x: x.split(',')[0] if isinstance(x, str) else x)
            df_ridge = df_ridge[df_ridge['tipo_scuola'].isin(TIPI_SCUOLA)]

        if df_ridge.empty:
            st.info("Nessun dato valido per le tipologie canoniche nel ridgeline plot.")
        else:
            # Manual Ridgeline using Violin plots
            fig_ridge = go.Figure()
            
            groups = sorted(df_ridge[ridge_group].unique())
            colors = px.colors.qualitative.Prism
            
            for i, group in enumerate(groups):
                subset = df_ridge[df_ridge[ridge_group] == group][ridge_var]
                
                fig_ridge.add_trace(go.Violin(
                    x=subset,
                    name=str(group),
                    side='positive',
                    orientation='h',
                    width=1.5,
                    points=False,  # Don't show points to keep it clean "ridgeline" style
                    line_color=colors[i % len(colors)],
                    fillcolor=colors[i % len(colors)],
                    opacity=0.6,
                    meanline_visible=True
                ))

            fig_ridge.update_layout(
                xaxis_showgrid=False,
                xaxis_zeroline=False,
                xaxis_title=get_label(ridge_var),
                yaxis_title=ridge_group.replace('_', ' ').title(),
                height=600,
                showlegend=False,
                violinmode='overlay',  # Overlay to create the ridge effect
                bargap=0,
                title=f"Distribuzione di {get_label(ridge_var)} per {ridge_group}"
            )
            st.plotly_chart(fig_ridge, use_container_width=True)
    else:
        st.warning("Dati insufficienti o colonne mancanti per il Ridgeline Plot.")

    st.info("""
    💡 **A cosa serve**: Visualizza la forma delle distribuzioni di punteggio per diverse categorie, permettendo confronti visivi immediati.

    🔍 **Cosa rileva**: Ogni "onda" rappresenta la distribuzione di una categoria. Picchi più alti indicano concentrazione di scuole in quella fascia di punteggio. La linea verticale interna mostra la media. Distribuzioni più strette indicano omogeneità.

    🎯 **Implicazioni**: Permette di vedere non solo le medie ma la forma complessiva: distribuzioni bimodali, asimmetrie, code. Utile per capire se i gruppi sono omogenei o contengono sottogruppi nascosti.
    """)

render_footer()
