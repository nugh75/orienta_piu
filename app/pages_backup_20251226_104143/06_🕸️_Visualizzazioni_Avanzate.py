# 🕸️ Visualizzazioni Avanzate - Radar, Sankey e Sunburst
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from app.data_utils import get_label, LABEL_MAP_SHORT as LABEL_MAP

st.set_page_config(page_title="Visualizzazioni Avanzate", page_icon="🕸️", layout="wide")

SUMMARY_FILE = 'data/analysis_summary.csv'

@st.cache_data(ttl=60)
def load_data():
    if os.path.exists(SUMMARY_FILE):
        return pd.read_csv(SUMMARY_FILE)
    return pd.DataFrame()

df = load_data()

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

if df.empty:
    st.warning("Nessun dato disponibile nel file summary.")
    st.stop()

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
            line_color='#FF4B4B' # Streamlit Red
        ))

        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 5] # Assuming scale 1-5
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
    # Create categories: Bassa (<3.5), Media (3.5-5.5), Alta (>5.5)
    def categorize_maturity(val):
        if pd.isna(val): return "ND"
        if val < 3.5: return "Bassa (<3.5)"
        elif val <= 5.5: return "Media (3.5-5.5)"
        else: return "Alta (>5.5)"

    df['Livello Robustezza'] = df['ptof_orientamento_maturity_index'].apply(categorize_maturity)
    
    # Prepare dataframe for plotting
    # We remove rows with critical missing values for cleaner viz
    df_flow = df[['area_geografica', 'tipo_scuola', 'Livello Robustezza']].dropna()
    
    # Simplify School Types if too many unique values exist (optional, but good for display)
    # Just taking the first part if it's a comma separated list often happens
    df_flow['tipo_scuola'] = df_flow['tipo_scuola'].apply(lambda x: x.split(',')[0] if isinstance(x, str) else x)
    
    # Sort for better color flow stability
    df_flow = df_flow.sort_values(by=['area_geografica', 'Livello Robustezza'])
    
    # Map area to numbers for coloring (Parcats requires numbers for color scale)
    df_flow['area_code'] = df_flow['area_geografica'].astype('category').cat.codes

    fig_flow = px.parallel_categories(
        df_flow, 
        dimensions=['area_geografica', 'tipo_scuola', 'Livello Robustezza'],
        color='area_code', # Use numeric code for color
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
        labelfont=dict(size=24, color="black", family="Arial Black"), # Bigger and bolder headers
        tickfont=dict(size=18, color="black"),   # Bigger category labels
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
    st.warning("Dati mancanti per generare il grafico dei flussi (Area, Tipo o Indice).")

# --- 3. SUNBURST CHART ---
st.markdown("---")
st.subheader("🌞 Gerarchia (Sunburst)")
st.caption("Esplora la distribuzione gerarchica: Area Geografica → Tipo Scuola → Livello Robustezza.")

# Ensure 'Livello Robustezza' exists if not created above
if 'Livello Robustezza' not in df.columns and 'ptof_orientamento_maturity_index' in df.columns:
    def categorize_maturity(val):
        if pd.isna(val): return "ND"
        if val < 3.5: return "Bassa (<3.5)"
        elif val <= 5.5: return "Media (3.5-5.5)"
        else: return "Alta (>5.5)"
    df['Livello Robustezza'] = df['ptof_orientamento_maturity_index'].apply(categorize_maturity)

if all(c in df.columns for c in ['area_geografica', 'tipo_scuola', 'Livello Robustezza']):
    # Filter out ND or empty
    df_sun = df.dropna(subset=['area_geografica', 'tipo_scuola', 'Livello Robustezza']).copy()
    
    # Simple normalization for Tipo Scuola
    df_sun['tipo_scuola'] = df_sun['tipo_scuola'].apply(lambda x: x.split(',')[0] if isinstance(x, str) else x)
    
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
    fig_3d = px.scatter_3d(
        df, x=col_x, y=col_y, z=col_z,
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
            points=False, # Don't show points to keep it clean "ridgeline" style
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
        violinmode='overlay', # Overlay to create the ridge effect
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
