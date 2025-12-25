# 📊 Comparazioni - Confronti tra gruppi

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import numpy as np
from scipy import stats

st.set_page_config(page_title="Comparazioni", page_icon="📊", layout="wide")

SUMMARY_FILE = 'data/analysis_summary.csv'

LABEL_MAP = {
    'mean_finalita': 'Media Finalità',
    'mean_obiettivi': 'Media Obiettivi', 
    'mean_governance': 'Media Governance',
    'mean_didattica_orientativa': 'Media Didattica',
    'mean_opportunita': 'Media Opportunità',
    'ptof_orientamento_maturity_index': 'Indice RO',
}

def get_label(col):
    return LABEL_MAP.get(col, col.replace('_', ' ').title())

def split_multi_value(value):
    if pd.isna(value):
        return []
    return [part.strip() for part in str(value).split(',') if part.strip()]

def explode_multi_value(df: pd.DataFrame, col: str) -> pd.DataFrame:
    if col not in df.columns:
        return df
    if not df[col].astype(str).str.contains(',').any():
        return df
    df_temp = df.copy()
    df_temp[col] = df_temp[col].apply(split_multi_value)
    return df_temp.explode(col)

@st.cache_data(ttl=60)
def load_data():
    if os.path.exists(SUMMARY_FILE):
        return pd.read_csv(SUMMARY_FILE)
    return pd.DataFrame()

df = load_data()

st.title("📊 Comparazioni tra Gruppi")

with st.expander("📖 Come leggere questa pagina", expanded=False):
    st.markdown("""
    ### 🎯 Scopo della Pagina
    Questa pagina permette di **confrontare le performance** tra diversi gruppi di scuole, evidenziando pattern e differenze significative.
    
    ### 📊 Sezioni Disponibili
    
    **🔥 Matrice Performance (Heatmap)**
    - Incrocio tra **Area geografica** (Nord, Centro, Sud) e **Tipo scuola** (Liceo, Tecnico, ecc.)
    - I colori indicano il punteggio medio:
      - 🟢 **Verde scuro**: Punteggio alto (> 5)
      - 🟡 **Giallo**: Punteggio medio (3-5)
      - 🔴 **Rosso**: Punteggio basso (< 3)
    - Le celle vuote indicano assenza di dati per quella combinazione
    
    **📊 Box Plot Comparativi**
    - Mostrano la **distribuzione** dei punteggi per ogni gruppo
    - La **linea centrale** indica la mediana
    - La **scatola** contiene il 50% centrale dei dati (dal 25° al 75° percentile)
    - I **baffi** mostrano il range dei valori tipici
    - I **punti isolati** sono valori anomali (outlier)
    
    **📊 Grafico a Barre per Tipologia**
    - Confronto diretto delle medie per tipo di scuola
    - Più la barra è alta, migliore è la performance media
    
    ### 🔢 Come Interpretare le Heatmap
    - **Righe**: Tipi di scuola
    - **Colonne**: Aree geografiche o altre categorie
    - **Intensità colore**: Livello del punteggio
    - **Valori numerici**: Valore esatto della cella
    """)

if df.empty:
    st.warning("Nessun dato disponibile")
    st.stop()

# Convert to numeric
numeric_cols = [
    'ptof_orientamento_maturity_index', 
    'mean_finalita', 'mean_obiettivi', 
    'mean_governance', 'mean_didattica_orientativa', 'mean_opportunita'
]
for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

st.markdown("---")

# 1. Heatmap Area x Tipo
st.subheader("🔥 Matrice Performance: Area x Tipo Scuola")
st.caption("Confronto del punteggio medio per area geografica e tipo di scuola.")

if 'tipo_scuola' in df.columns and 'area_geografica' in df.columns:
    try:
        from app.data_utils import explode_school_types
        df_pivot = explode_school_types(df)
    except Exception:
        df_pivot = df
    df_pivot = explode_multi_value(df_pivot, 'tipo_scuola')
        
    # Pivot calculation
    pivot = df_pivot.pivot_table(
        index='tipo_scuola', 
        columns='area_geografica', 
        values='ptof_orientamento_maturity_index', 
        aggfunc='mean'
    )
    
    if not pivot.empty:
        fig = px.imshow(
            pivot, text_auto='.2f', color_continuous_scale='RdBu',
            zmin=1, zmax=7, title="Indice RO Medio per Tipo e Area"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        with st.expander("📘 Guida alla lettura: Heatmap"):
            st.markdown("""
            **Cosa mostra?**
            Incrocia il **Tipo di Scuola** con l'**Area Geografica** per vedere chi performa meglio.
            - **Blu/Rosso scuro:** Punteggi alti/bassi (a seconda della scala).
            - **Numeri:** Il punteggio medio del gruppo (1-7).
            """)
        
        st.info("""
💡 **A cosa serve**: Incrocia tipologia scolastica e area geografica per identificare le combinazioni migliori e peggiori.

🔍 **Cosa rileva**: Ogni cella mostra il punteggio medio di quel gruppo. Colori scuri = punteggi estremi (alti o bassi). Celle vuote = nessun dato per quella combinazione.

🎯 **Implicazioni**: Se i Licei del Nord hanno punteggi alti ma quelli del Sud bassi, potrebbe indicare disparità territoriali da affrontare. Utile per politiche educative mirate.
""")
        
        # === ANALISI STATISTICA HEATMAP ===
        with st.expander("📈 Analisi Statistica: Effetti Tipo Scuola e Area Geografica", expanded=False):
            st.markdown("""
            Analisi degli effetti principali e dell'interazione tra **Tipo Scuola** e **Area Geografica** 
            sull'Indice RO.
            """)
            
            # Effetto Tipo Scuola (ANOVA one-way)
            tipo_groups = df_pivot.groupby('tipo_scuola')['ptof_orientamento_maturity_index'].apply(list).to_dict()
            valid_tipo = {k: pd.Series(v).dropna() for k, v in tipo_groups.items() if len(pd.Series(v).dropna()) >= 3}
            
            col_stat1, col_stat2 = st.columns(2)
            
            with col_stat1:
                st.markdown("#### 📚 Effetto Tipo Scuola")
                if len(valid_tipo) >= 2:
                    f_tipo, p_tipo = stats.f_oneway(*[v for v in valid_tipo.values()])
                    p_interp, p_emoji = interpret_pvalue(p_tipo)
                    st.markdown(f"- F = {f_tipo:.2f}, p = {p_tipo:.4f} {p_emoji} {p_interp}")
                    
                    if p_tipo < 0.05:
                        st.success("✅ Il tipo di scuola ha un effetto significativo")
                    else:
                        st.info("Il tipo di scuola non ha un effetto significativo")
                else:
                    st.info("Dati insufficienti")
            
            with col_stat2:
                st.markdown("#### 🗺️ Effetto Area Geografica")
                if 'area_geografica' in df_pivot.columns:
                    area_groups = df_pivot.groupby('area_geografica')['ptof_orientamento_maturity_index'].apply(list).to_dict()
                    valid_area = {k: pd.Series(v).dropna() for k, v in area_groups.items() if len(pd.Series(v).dropna()) >= 3}
                    
                    if len(valid_area) >= 2:
                        f_area, p_area = stats.f_oneway(*[v for v in valid_area.values()])
                        p_interp, p_emoji = interpret_pvalue(p_area)
                        st.markdown(f"- F = {f_area:.2f}, p = {p_area:.4f} {p_emoji} {p_interp}")
                        
                        if p_area < 0.05:
                            st.success("✅ L'area geografica ha un effetto significativo")
                        else:
                            st.info("L'area geografica non ha un effetto significativo")
                    else:
                        st.info("Dati insufficienti")
                else:
                    st.info("Dati area non disponibili")
            
            # Tabella riassuntiva combinazioni
            st.markdown("---")
            st.markdown("#### 🏆 Migliori e Peggiori Combinazioni")
            
            if not pivot.empty:
                # Trova max e min
                flat_data = []
                for tipo in pivot.index:
                    for area in pivot.columns:
                        val = pivot.loc[tipo, area]
                        if pd.notna(val):
                            flat_data.append({'Tipo': tipo, 'Area': area, 'Media': val})
                
                if flat_data:
                    flat_df = pd.DataFrame(flat_data).sort_values('Media', ascending=False)
                    
                    col_best, col_worst = st.columns(2)
                    with col_best:
                        st.markdown("**🥇 Top 3:**")
                        for _, row in flat_df.head(3).iterrows():
                            st.markdown(f"- {row['Tipo']} ({row['Area']}): **{row['Media']:.2f}**")
                    
                    with col_worst:
                        st.markdown("**⚠️ Bottom 3:**")
                        for _, row in flat_df.tail(3).iterrows():
                            st.markdown(f"- {row['Tipo']} ({row['Area']}): **{row['Media']:.2f}**")
    else:
        st.info("Dati insufficienti per la Heatmap")
else:
    st.warning("Colonne 'tipo_scuola' o 'area_geografica' mancanti.")

st.markdown("---")

# 2. Radar Chart (NEW)
st.subheader("🕸️ Radar Chart: Profili a Confronto")
st.caption("Confronto delle 5 dimensioni di robustezza tra diversi gruppi.")

radar_cols = ['mean_finalita', 'mean_obiettivi', 'mean_governance', 'mean_didattica_orientativa', 'mean_opportunita']
if all(c in df.columns for c in radar_cols):
    radar_group = st.selectbox("Raggruppa per:", ["tipo_scuola", "area_geografica", "ordine_grado"], index=0) # Index 0 is tipo_scuola
    
    if radar_group in df.columns:
        # Explode if grouping by multi-value column
        df_radar = df
        if radar_group == 'tipo_scuola':
             try:
                 from app.data_utils import explode_school_types
                 df_radar = explode_school_types(df)
             except Exception:
                 df_radar = df
             df_radar = explode_multi_value(df_radar, 'tipo_scuola')
        elif radar_group == 'ordine_grado':
             try:
                 from app.data_utils import explode_school_grades
                 df_radar = explode_school_grades(df)
             except Exception:
                 df_radar = df
             df_radar = explode_multi_value(df_radar, 'ordine_grado')
             
        # Calculate means
        radar_df = df_radar.groupby(radar_group)[radar_cols].mean().reset_index()
        
        fig = go.Figure()
        
        # Add trace for each group
        for i, row in radar_df.iterrows():
            group_name = str(row[radar_group])
            values = row[radar_cols].values.tolist()
            # Close the loop
            values += values[:1]
            
            fig.add_trace(go.Scatterpolar(
                r=values,
                theta=[get_label(c) for c in radar_cols] + [get_label(radar_cols[0])],
                fill='toself',
                name=group_name
            ))
            
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 7]
                )
            ),
            showlegend=True,
            title=f"Confronto Profili per {radar_group.replace('_', ' ').title()}",
            height=600
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.info("""
💡 **A cosa serve**: Confronta il "profilo" di diversi gruppi (es. Licei vs Tecnici) sulle 5 dimensioni dell'orientamento.

🔍 **Cosa rileva**: Ogni "petalo" del radar è una dimensione. Più un gruppo si espande verso l'esterno, migliore è in quella area. Gruppi con profili sovrapposti hanno performance simili.

🎯 **Implicazioni**: Se un tipo di scuola ha un profilo "schiacciato" su una dimensione, quella è un'area critica su cui lavorare a livello di sistema per quel tipo di istituto.
""")
else:
    st.info("Dati insufficienti per il Radar Chart")

st.markdown("---")

# 3. Box plots Territorio e Grado
st.subheader("🏙️ Confronti: Territorio e Grado Scolastico")
col1, col2 = st.columns(2)

with col1:
    if 'territorio' in df.columns:
        fig = px.box(df, x='territorio', y='ptof_orientamento_maturity_index',
                     points="all", color='territorio',
                     title="Distribuzione per Territorio")
        st.plotly_chart(fig, use_container_width=True)

with col2:
    if 'ordine_grado' in df.columns:
        # Explode for box plot
        try:
             from app.data_utils import explode_school_grades
             df_box = explode_school_grades(df)
        except Exception:
             df_box = df
        df_box = explode_multi_value(df_box, 'ordine_grado')
             
        fig = px.box(df_box, x='ordine_grado', y='ptof_orientamento_maturity_index',
                     points="all", color='ordine_grado',
                     title="Distribuzione per Grado")
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("📘 Guida alla lettura: Box Plot"):
        st.markdown("""
        **Come si legge?**
        Confronta la distribuzione dei punteggi tra gruppi.
        - **Linea centrale:** Mediana (il valore che divide a metà il gruppo).
        - **Scatola (Box):** Contiene il 50% centrale delle scuole.
        - **Baffi (Linee):** Indicano il range dei valori (esclusi gli outlier).
        """)

st.info("""
💡 **A cosa serve**: Mostra come si distribuiscono i punteggi all'interno di ogni gruppo, non solo la media.

🔍 **Cosa rileva**: La linea centrale è la mediana (metà delle scuole sta sopra, metà sotto). La "scatola" contiene il 50% centrale. I punti isolati sono scuole eccezionali (positive o negative).

🎯 **Implicazioni**: Scatole "alte" indicano gruppi migliori. Scatole "lunghe" indicano alta variabilità (alcune scuole eccellenti, altre no). I punti isolati meritano attenzione speciale.
""")

st.markdown("---")

# === NUOVA SEZIONE: SIGNIFICATIVITÀ STATISTICA E EFFECT SIZE ===
st.subheader("📈 Significatività Statistica ed Effect Size")
st.caption("Analisi della significatività delle differenze tra gruppi e della dimensione dell'effetto.")

def cohens_d(group1, group2):
    """Calcola Cohen's d per due gruppi"""
    n1, n2 = len(group1), len(group2)
    if n1 < 2 or n2 < 2:
        return np.nan
    var1, var2 = group1.var(), group2.var()
    pooled_std = np.sqrt(((n1-1)*var1 + (n2-1)*var2) / (n1+n2-2))
    if pooled_std == 0:
        return np.nan
    return (group1.mean() - group2.mean()) / pooled_std

def interpret_cohens_d(d):
    """Interpreta il valore di Cohen's d"""
    if pd.isna(d):
        return "N/D", "⚪"
    d_abs = abs(d)
    if d_abs < 0.2:
        return "Trascurabile", "⚪"
    elif d_abs < 0.5:
        return "Piccolo", "🟡"
    elif d_abs < 0.8:
        return "Medio", "🟠"
    else:
        return "Grande", "🔴"

def interpret_pvalue(p):
    """Interpreta il p-value"""
    if pd.isna(p):
        return "N/D", "⚪"
    if p < 0.001:
        return "***", "🟢"
    elif p < 0.01:
        return "**", "🟢"
    elif p < 0.05:
        return "*", "🟡"
    else:
        return "n.s.", "⚪"

# Tab per diverse analisi statistiche
stat_tab1, stat_tab2, stat_tab3 = st.tabs(["🏙️ Territorio", "📚 Grado Scolastico", "🗺️ Area Geografica"])

with stat_tab1:
    st.markdown("#### Confronto Metropolitano vs Non Metropolitano")
    if 'territorio' in df.columns and 'ptof_orientamento_maturity_index' in df.columns:
        terr_groups = df.groupby('territorio')['ptof_orientamento_maturity_index'].apply(list).to_dict()
        
        if len(terr_groups) >= 2:
            terr_names = list(terr_groups.keys())
            results_terr = []
            
            for i, t1 in enumerate(terr_names):
                for t2 in terr_names[i+1:]:
                    g1 = pd.Series(terr_groups[t1]).dropna()
                    g2 = pd.Series(terr_groups[t2]).dropna()
                    
                    if len(g1) >= 3 and len(g2) >= 3:
                        # T-test
                        t_stat, p_value = stats.ttest_ind(g1, g2)
                        # Cohen's d
                        d = cohens_d(g1, g2)
                        d_interp, d_emoji = interpret_cohens_d(d)
                        p_interp, p_emoji = interpret_pvalue(p_value)
                        
                        results_terr.append({
                            'Confronto': f"{t1} vs {t2}",
                            'N₁': len(g1),
                            'Media₁': f"{g1.mean():.2f}",
                            'N₂': len(g2),
                            'Media₂': f"{g2.mean():.2f}",
                            'Differenza': f"{g1.mean() - g2.mean():.2f}",
                            't': f"{t_stat:.2f}",
                            'p-value': f"{p_value:.4f}",
                            'Sig.': f"{p_emoji} {p_interp}",
                            "Cohen's d": f"{d:.2f}" if not pd.isna(d) else "N/D",
                            'Effetto': f"{d_emoji} {d_interp}"
                        })
            
            if results_terr:
                st.dataframe(pd.DataFrame(results_terr), use_container_width=True, hide_index=True)
            else:
                st.info("Dati insufficienti per l'analisi statistica (servono almeno 3 scuole per gruppo)")
        else:
            st.info("Servono almeno 2 gruppi territoriali per il confronto")
    else:
        st.warning("Colonna 'territorio' non disponibile")

with stat_tab2:
    st.markdown("#### Confronto I Grado vs II Grado")
    if 'ordine_grado' in df.columns and 'ptof_orientamento_maturity_index' in df.columns:
        # Explode multi-value
        try:
            from app.data_utils import explode_school_grades
            df_stat = explode_school_grades(df)
        except Exception:
            df_stat = df
        df_stat = explode_multi_value(df_stat, 'ordine_grado')
        
        grado_groups = df_stat.groupby('ordine_grado')['ptof_orientamento_maturity_index'].apply(list).to_dict()
        
        if len(grado_groups) >= 2:
            grado_names = list(grado_groups.keys())
            results_grado = []
            
            for i, g1_name in enumerate(grado_names):
                for g2_name in grado_names[i+1:]:
                    g1 = pd.Series(grado_groups[g1_name]).dropna()
                    g2 = pd.Series(grado_groups[g2_name]).dropna()
                    
                    if len(g1) >= 3 and len(g2) >= 3:
                        t_stat, p_value = stats.ttest_ind(g1, g2)
                        d = cohens_d(g1, g2)
                        d_interp, d_emoji = interpret_cohens_d(d)
                        p_interp, p_emoji = interpret_pvalue(p_value)
                        
                        results_grado.append({
                            'Confronto': f"{g1_name} vs {g2_name}",
                            'N₁': len(g1),
                            'Media₁': f"{g1.mean():.2f}",
                            'N₂': len(g2),
                            'Media₂': f"{g2.mean():.2f}",
                            'Differenza': f"{g1.mean() - g2.mean():.2f}",
                            't': f"{t_stat:.2f}",
                            'p-value': f"{p_value:.4f}",
                            'Sig.': f"{p_emoji} {p_interp}",
                            "Cohen's d": f"{d:.2f}" if not pd.isna(d) else "N/D",
                            'Effetto': f"{d_emoji} {d_interp}"
                        })
            
            if results_grado:
                st.dataframe(pd.DataFrame(results_grado), use_container_width=True, hide_index=True)
            else:
                st.info("Dati insufficienti per l'analisi statistica")
        else:
            st.info("Servono almeno 2 gradi scolastici per il confronto")
    else:
        st.warning("Colonna 'ordine_grado' non disponibile")

with stat_tab3:
    st.markdown("#### Confronto tra Aree Geografiche (Nord, Centro, Sud)")
    if 'area_geografica' in df.columns and 'ptof_orientamento_maturity_index' in df.columns:
        area_groups = df.groupby('area_geografica')['ptof_orientamento_maturity_index'].apply(list).to_dict()
        
        if len(area_groups) >= 2:
            area_names = list(area_groups.keys())
            results_area = []
            
            for i, a1 in enumerate(area_names):
                for a2 in area_names[i+1:]:
                    g1 = pd.Series(area_groups[a1]).dropna()
                    g2 = pd.Series(area_groups[a2]).dropna()
                    
                    if len(g1) >= 3 and len(g2) >= 3:
                        t_stat, p_value = stats.ttest_ind(g1, g2)
                        d = cohens_d(g1, g2)
                        d_interp, d_emoji = interpret_cohens_d(d)
                        p_interp, p_emoji = interpret_pvalue(p_value)
                        
                        results_area.append({
                            'Confronto': f"{a1} vs {a2}",
                            'N₁': len(g1),
                            'Media₁': f"{g1.mean():.2f}",
                            'N₂': len(g2),
                            'Media₂': f"{g2.mean():.2f}",
                            'Differenza': f"{g1.mean() - g2.mean():.2f}",
                            't': f"{t_stat:.2f}",
                            'p-value': f"{p_value:.4f}",
                            'Sig.': f"{p_emoji} {p_interp}",
                            "Cohen's d": f"{d:.2f}" if not pd.isna(d) else "N/D",
                            'Effetto': f"{d_emoji} {d_interp}"
                        })
            
            if results_area:
                st.dataframe(pd.DataFrame(results_area), use_container_width=True, hide_index=True)
                
                # ANOVA se ci sono 3+ gruppi
                if len(area_groups) >= 3:
                    valid_groups = [pd.Series(v).dropna() for v in area_groups.values() if len(pd.Series(v).dropna()) >= 3]
                    if len(valid_groups) >= 3:
                        f_stat, p_anova = stats.f_oneway(*valid_groups)
                        p_interp, p_emoji = interpret_pvalue(p_anova)
                        st.markdown(f"""
                        **ANOVA (confronto globale)**: F = {f_stat:.2f}, p = {p_anova:.4f} {p_emoji} {p_interp}
                        """)
            else:
                st.info("Dati insufficienti per l'analisi statistica")
        else:
            st.info("Servono almeno 2 aree geografiche per il confronto")
    else:
        st.warning("Colonna 'area_geografica' non disponibile")

with st.expander("📘 Guida alla lettura: Significatività e Effect Size"):
    st.markdown("""
    ### 📊 Come interpretare i risultati
    
    **P-value (Significatività statistica)**
    - `*** (p < 0.001)`: Differenza altamente significativa
    - `** (p < 0.01)`: Differenza molto significativa
    - `* (p < 0.05)`: Differenza significativa
    - `n.s.`: Non significativa (la differenza potrebbe essere casuale)
    
    **Cohen's d (Dimensione dell'effetto)**
    - `< 0.2` ⚪ **Trascurabile**: Differenza praticamente inesistente
    - `0.2-0.5` 🟡 **Piccolo**: Differenza reale ma modesta
    - `0.5-0.8` 🟠 **Medio**: Differenza sostanziale e rilevante
    - `> 0.8` 🔴 **Grande**: Differenza molto marcata
    
    ### ⚠️ Nota importante
    Un p-value significativo indica che la differenza è *reale* (non casuale), ma non dice quanto sia *importante*.
    Il Cohen's d invece quantifica l'*entità* della differenza. Una differenza può essere statisticamente significativa ma praticamente irrilevante (d piccolo), o viceversa.
    
    **Per decisioni pratiche, guarda il Cohen's d!**
    """)

st.info("""
💡 **A cosa serve**: Quantifica se le differenze osservate tra i gruppi sono statisticamente significative e quanto sono rilevanti nella pratica.

🔍 **Cosa rileva**: Il **p-value** indica se la differenza è reale o casuale. Il **Cohen's d** misura l'entità della differenza: valori > 0.5 indicano differenze sostanziali meritevoli di attenzione.

🎯 **Implicazioni**: Differenze con p < 0.05 E Cohen's d > 0.5 sono quelle su cui vale la pena intervenire. Evita di basare decisioni su differenze statisticamente significative ma con effetto trascurabile.
""")

st.markdown("---")

# 4. Grouped Bar I Grado vs II Grado
st.subheader("📊 Confronto I Grado vs II Grado")

if 'ordine_grado' in df.columns:
    dim_cols = ['mean_finalita', 'mean_obiettivi', 'mean_governance', 'mean_didattica_orientativa', 'mean_opportunita']
    if all(c in df.columns for c in dim_cols):
        # Explode for grouped bar
        try:
             from app.data_utils import explode_school_grades
             df_bar = explode_school_grades(df)
        except Exception:
             df_bar = df
        df_bar = explode_multi_value(df_bar, 'ordine_grado')
             
        grado_df = df_bar.groupby('ordine_grado')[dim_cols].mean().reset_index()
        grado_melted = grado_df.melt(id_vars='ordine_grado', var_name='Dimensione', value_name='Media')
        grado_melted['Dimensione'] = grado_melted['Dimensione'].apply(get_label)
        
        fig = px.bar(grado_melted, x='Dimensione', y='Media', color='ordine_grado',
                     barmode='group', title="Media per Dimensione: I Grado vs II Grado")
        fig.update_layout(xaxis_tickangle=-30)
        st.plotly_chart(fig, use_container_width=True)
        
        # === ANALISI STATISTICA PER DIMENSIONE ===
        with st.expander("📈 Analisi Statistica per Dimensione (I Grado vs II Grado)", expanded=False):
            grado_groups = df_bar.groupby('ordine_grado')
            grado_names = list(grado_groups.groups.keys())
            
            if len(grado_names) >= 2:
                results_dim = []
                for dim_col in dim_cols:
                    g1_name, g2_name = grado_names[0], grado_names[1]
                    g1 = grado_groups.get_group(g1_name)[dim_col].dropna()
                    g2 = grado_groups.get_group(g2_name)[dim_col].dropna()
                    
                    if len(g1) >= 3 and len(g2) >= 3:
                        t_stat, p_value = stats.ttest_ind(g1, g2)
                        d = cohens_d(g1, g2)
                        d_interp, d_emoji = interpret_cohens_d(d)
                        p_interp, p_emoji = interpret_pvalue(p_value)
                        
                        results_dim.append({
                            'Dimensione': get_label(dim_col),
                            f'Media {g1_name}': f"{g1.mean():.2f}",
                            f'Media {g2_name}': f"{g2.mean():.2f}",
                            'Diff.': f"{g1.mean() - g2.mean():.2f}",
                            'p-value': f"{p_value:.4f}",
                            'Sig.': f"{p_emoji} {p_interp}",
                            "Cohen's d": f"{d:.2f}" if not pd.isna(d) else "N/D",
                            'Effetto': f"{d_emoji} {d_interp}"
                        })
                
                if results_dim:
                    st.dataframe(pd.DataFrame(results_dim), use_container_width=True, hide_index=True)
                    
                    # Evidenzia le differenze significative
                    sig_dims = [r for r in results_dim if '🟢' in r['Sig.'] or '🟡' in r['Sig.']]
                    if sig_dims:
                        st.markdown("**🔍 Differenze significative trovate in:**")
                        for r in sig_dims:
                            effect = r['Effetto'].split()[1] if len(r['Effetto'].split()) > 1 else r['Effetto']
                            st.markdown(f"- **{r['Dimensione']}**: differenza di {r['Diff.']} punti (effetto {effect.lower()})")
        
        st.info("""
💡 **A cosa serve**: Confronta direttamente le scuole di I grado (medie) con quelle di II grado (superiori) su ogni dimensione.

🔍 **Cosa rileva**: Le barre affiancate mostrano le medie per grado. Differenze evidenti tra i colori indicano che un grado performa sistematicamente meglio dell'altro in quella dimensione.

🎯 **Implicazioni**: Se il II grado eccelle in "Opportunità" ma il I grado no, potrebbe indicare che i collegamenti con il mondo del lavoro sono più sviluppati alle superiori. Utile per interventi specifici per fascia d'età.
""")

st.markdown("---")

# 5. Gap Analysis
st.subheader("🎯 Gap Analysis: Distanza dal Ottimo (7)")
gap_cols = ['mean_finalita', 'mean_obiettivi', 'mean_governance', 'mean_didattica_orientativa', 'mean_opportunita']
if all(c in df.columns for c in gap_cols):
    gap_means = df[gap_cols].mean()
    gap_values = 7 - gap_means
    
    gap_df = pd.DataFrame({
        'Dimensione': [get_label(c) for c in gap_cols],
        'Punteggio Attuale': gap_means.values,
        'Gap da 7': gap_values.values
    })
    
    fig = go.Figure()
    fig.add_trace(go.Bar(x=gap_df['Dimensione'], y=gap_df['Punteggio Attuale'], 
                         name='Attuale', marker_color='#00CC96'))
    fig.add_trace(go.Bar(x=gap_df['Dimensione'], y=gap_df['Gap da 7'], 
                         name='Gap', marker_color='#EF553B'))
    fig.update_layout(barmode='stack', yaxis=dict(range=[0, 7]))
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("📘 Guida alla lettura: Gap Analysis"):
        st.markdown("""
        **Cosa significa?**
        Visualizza quanto manca per raggiungere l'eccellenza (punteggio 7).
        - **Verde/Blu:** Il punteggio attuale raggiunto.
        - **Rosso/Grigio:** Il gap (distanza) mancante per arrivare a 7.
        """)
    
    # === ANALISI STATISTICA GAP ===
    with st.expander("📈 Analisi Statistica: Quanto siamo lontani dall'eccellenza?", expanded=False):
        st.markdown("""
        Verifica se i punteggi medi sono significativamente diversi dal valore teorico ottimo (7).
        Utilizziamo un **t-test one-sample** per ogni dimensione.
        """)
        
        results_gap = []
        for gap_col in gap_cols:
            values = df[gap_col].dropna()
            if len(values) >= 3:
                t_stat, p_value = stats.ttest_1samp(values, 7)  # Test vs valore teorico 7
                mean_val = values.mean()
                std_val = values.std()
                gap = 7 - mean_val
                
                # Effect size (Cohen's d one-sample)
                d_one = (mean_val - 7) / std_val if std_val > 0 else np.nan
                d_interp, d_emoji = interpret_cohens_d(d_one)
                p_interp, p_emoji = interpret_pvalue(p_value)
                
                results_gap.append({
                    'Dimensione': get_label(gap_col),
                    'Media': f"{mean_val:.2f}",
                    'Gap da 7': f"{gap:.2f}",
                    'DS': f"{std_val:.2f}",
                    't': f"{t_stat:.2f}",
                    'p-value': f"{p_value:.4f}",
                    'Sig.': f"{p_emoji} {p_interp}",
                    'Distanza (d)': f"{abs(d_one):.2f}" if not pd.isna(d_one) else "N/D",
                    'Entità Gap': f"{d_emoji} {d_interp}"
                })
        
        if results_gap:
            st.dataframe(pd.DataFrame(results_gap), use_container_width=True, hide_index=True)
            
            # Ranking delle priorità
            st.markdown("### 🎯 Priorità di Intervento")
            sorted_gaps = sorted(results_gap, key=lambda x: float(x['Gap da 7']), reverse=True)
            for i, r in enumerate(sorted_gaps, 1):
                emoji = "🔴" if float(r['Gap da 7']) > 2 else "🟠" if float(r['Gap da 7']) > 1 else "🟡"
                st.markdown(f"{i}. {emoji} **{r['Dimensione']}**: gap di {r['Gap da 7']} punti ({r['Entità Gap'].split()[1] if len(r['Entità Gap'].split()) > 1 else 'N/D'})")

st.info("""
💡 **A cosa serve**: Visualizza quanto manca a ciascuna dimensione per raggiungere l'eccellenza (punteggio massimo 7).

🔍 **Cosa rileva**: La parte verde è il punteggio medio attuale, quella rossa è il "gap" da colmare. Dimensioni con più rosso sono quelle dove c'è maggior margine di miglioramento.

🎯 **Implicazioni**: Concentra gli sforzi sulle dimensioni con gap maggiori. Queste sono le priorità di intervento per migliorare la qualità complessiva dell'orientamento nel sistema.
""")

# 6. Regional comparison
st.subheader("🗺️ Confronto Regionale")

def normalize_region(value):
    if pd.isna(value):
        return None
    value_str = str(value).strip()
    if value_str in ('', 'ND', 'N/A', 'nan'):
        return None
    return value_str

if 'regione' in df.columns:
    df_region = df.copy()
    df_region['regione'] = df_region['regione'].apply(normalize_region)
    region_counts = df_region['regione'].dropna().value_counts()

    if len(region_counts) >= 3:
        region_avg = df_region[df_region['regione'].notna()].groupby('regione')[
            'ptof_orientamento_maturity_index'
        ].agg(['mean', 'count']).reset_index()
        region_avg.columns = ['Regione', 'Indice RO Medio', 'N. Scuole']

        if len(region_avg) >= 3:
            fig = px.bar(
                region_avg.sort_values('Indice RO Medio'),
                x='Indice RO Medio',
                y='Regione',
                orientation='h',
                color='Indice RO Medio',
                color_continuous_scale='RdYlGn',
                range_color=[1, 7],
                text='N. Scuole',
                title="Indice RO per Regione",
            )
            fig.update_traces(texttemplate='n=%{text}', textposition='outside')
            st.plotly_chart(fig, use_container_width=True)
            
            # === ANALISI STATISTICA REGIONALE ===
            with st.expander("📈 Analisi Statistica Regionale (ANOVA + Confronti)", expanded=False):
                # ANOVA globale
                region_groups = df_region[df_region['regione'].notna()].groupby('regione')['ptof_orientamento_maturity_index'].apply(list).to_dict()
                valid_regions = {k: pd.Series(v).dropna() for k, v in region_groups.items() if len(pd.Series(v).dropna()) >= 3}
                
                if len(valid_regions) >= 3:
                    f_stat, p_anova = stats.f_oneway(*[v for v in valid_regions.values()])
                    p_interp, p_emoji = interpret_pvalue(p_anova)
                    
                    st.markdown(f"""
                    ### ANOVA (Confronto Globale tra Regioni)
                    - **F-statistic**: {f_stat:.2f}
                    - **p-value**: {p_anova:.4f} {p_emoji} {p_interp}
                    """)
                    
                    if p_anova < 0.05:
                        st.success("✅ Esistono differenze significative tra le regioni!")
                        
                        # Top 3 e Bottom 3 regioni
                        sorted_regions = sorted(valid_regions.items(), key=lambda x: x[1].mean(), reverse=True)
                        top3 = sorted_regions[:3]
                        bottom3 = sorted_regions[-3:]
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("#### 🏆 Top 3 Regioni")
                            for reg, vals in top3:
                                st.markdown(f"- **{reg}**: {vals.mean():.2f} (n={len(vals)})")
                        
                        with col2:
                            st.markdown("#### ⚠️ Bottom 3 Regioni")
                            for reg, vals in bottom3:
                                st.markdown(f"- **{reg}**: {vals.mean():.2f} (n={len(vals)})")
                        
                        # Confronti Post-hoc (Top vs Bottom)
                        st.markdown("---")
                        st.markdown("#### Confronti Post-hoc (Migliore vs Peggiore)")
                        
                        if len(sorted_regions) >= 2:
                            best_name, best_vals = sorted_regions[0]
                            worst_name, worst_vals = sorted_regions[-1]
                            
                            t_stat, p_value = stats.ttest_ind(best_vals, worst_vals)
                            d = cohens_d(best_vals, worst_vals)
                            d_interp, d_emoji = interpret_cohens_d(d)
                            p_interp, p_emoji = interpret_pvalue(p_value)
                            
                            st.markdown(f"""
                            **{best_name}** vs **{worst_name}**:
                            - Differenza medie: {best_vals.mean() - worst_vals.mean():.2f}
                            - t = {t_stat:.2f}, p = {p_value:.4f} {p_emoji} {p_interp}
                            - Cohen's d = {d:.2f} → Effetto {d_emoji} {d_interp}
                            """)
                    else:
                        st.info("Le differenze tra regioni non sono statisticamente significative (p > 0.05)")
                else:
                    st.info("Servono almeno 3 regioni con dati sufficienti per l'ANOVA")
            
            st.info("""
💡 **A cosa serve**: Ordina le regioni per punteggio medio, permettendo confronti territoriali immediati.

🔍 **Cosa rileva**: Le regioni in alto hanno punteggi migliori. Il numero "n=" indica quante scuole sono state analizzate. Regioni con n basso hanno dati meno affidabili.

🎯 **Implicazioni**: Le regioni con punteggi bassi potrebbero necessitare di programmi formativi specifici. Confronta la tua regione con le altre per capire il posizionamento.
""")
        else:
            st.info("Dati regionali insufficienti (servono almeno 3 regioni)")
    else:
        st.info("Dati regionali insufficienti")
else:
    st.info("Colonna 'regione' non disponibile nel CSV")
