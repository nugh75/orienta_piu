# 🧪 Analisi Sperimentali - Radar & Flussi
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

st.set_page_config(page_title="Analisi Sperimentali", page_icon="🧪", layout="wide")

SUMMARY_FILE = 'data/analysis_summary.csv'

# Utility: Labels Mapping
LABEL_MAP = {
    'mean_finalita': 'Finalità',
    'mean_obiettivi': 'Obiettivi', 
    'mean_governance': 'Governance',
    'mean_didattica_orientativa': 'Didattica',
    'mean_opportunita': 'Opportunità',
}

def get_label(col):
    return LABEL_MAP.get(col, col)

@st.cache_data(ttl=60)
def load_data():
    if os.path.exists(SUMMARY_FILE):
        return pd.read_csv(SUMMARY_FILE)
    return pd.DataFrame()

df = load_data()

st.title("🧪 Analisi Sperimentali")
st.markdown("""
Questa pagina contiene visualizzazioni **sperimentali** per esplorare i dati in modo diverso.
1. **Radar Chart**: Confronta il profilo di una scuola con la media nazionale.
2. **Analisi dei Flussi**: Osserva come le caratteristiche geografiche influenzano la maturità dell'orientamento.
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

    else:
        st.error("Le colonne delle dimensioni (mean_finalita, etc.) mancano nel dataset.")

# --- 2. PARALLEL CATEGORIES ---
st.markdown("---")
st.subheader("🌊 Flussi: Geografica → Tipo Scuola → Maturità")
st.caption("Visualizza come si distribuiscono le scuole tra aree geografiche, tipologie e indice di maturità.")

with st.expander("ℹ️ Come leggere questo grafico (Clicca per aprire)", expanded=True):
    st.markdown("""
    Questo grafico (**Parallel Categories**) mostra i "flussi" di scuole attraverso diverse categorie:
    1.  **Sinistra (Area)**: Da dove partono le scuole (Nord, Sud).
    2.  **Centro (Tipo)**: Che tipo di scuola sono (Liceo, Tecnico, Comprensivo, ecc.).
    3.  **Destra (Maturità)**: Qual è il loro punteggio di maturità nell'orientamento (Basso, Medio, Alto).

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

    df['Livello Maturità'] = df['ptof_orientamento_maturity_index'].apply(categorize_maturity)
    
    # Prepare dataframe for plotting
    # We remove rows with critical missing values for cleaner viz
    df_flow = df[['area_geografica', 'tipo_scuola', 'Livello Maturità']].dropna()
    
    # Simplify School Types if too many unique values exist (optional, but good for display)
    # Just taking the first part if it's a comma separated list often happens
    df_flow['tipo_scuola'] = df_flow['tipo_scuola'].apply(lambda x: x.split(',')[0] if isinstance(x, str) else x)
    
    # Sort for better color flow stability
    df_flow = df_flow.sort_values(by=['area_geografica', 'Livello Maturità'])
    
    # Map area to numbers for coloring (Parcats requires numbers for color scale)
    df_flow['area_code'] = df_flow['area_geografica'].astype('category').cat.codes

    fig_flow = px.parallel_categories(
        df_flow, 
        dimensions=['area_geografica', 'tipo_scuola', 'Livello Maturità'],
        color='area_code', # Use numeric code for color
        color_continuous_scale=px.colors.sequential.Inferno,
        labels={
            'area_geografica': 'Area Geografica',
            'tipo_scuola': 'Tipo Scuola',
            'Livello Maturità': 'Livello Maturità PTOF',
            'area_code': 'Codice Area'
        }
    )
    # Hide the colorbar as it shows numbers
    fig_flow.update_layout(coloraxis_showscale=False)
    
    fig_flow.update_layout(height=600, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig_flow, use_container_width=True)

else:
    st.warning("Dati mancanti per generare il grafico dei flussi (Area, Tipo o Indice).")

# --- 3. SUNBURST CHART ---
st.markdown("---")
st.subheader("🌞 Gerarchia (Sunburst)")
st.caption("Esplora la distribuzione gerarchica: Area Geografica → Tipo Scuola → Livello Maturità.")

# Ensure 'Livello Maturità' exists if not created above
if 'Livello Maturità' not in df.columns and 'ptof_orientamento_maturity_index' in df.columns:
    def categorize_maturity(val):
        if pd.isna(val): return "ND"
        if val < 3.5: return "Bassa (<3.5)"
        elif val <= 5.5: return "Media (3.5-5.5)"
        else: return "Alta (>5.5)"
    df['Livello Maturità'] = df['ptof_orientamento_maturity_index'].apply(categorize_maturity)

if all(c in df.columns for c in ['area_geografica', 'tipo_scuola', 'Livello Maturità']):
    # Filter out ND or empty
    df_sun = df.dropna(subset=['area_geografica', 'tipo_scuola', 'Livello Maturità']).copy()
    
    # Simple normalization for Tipo Scuola
    df_sun['tipo_scuola'] = df_sun['tipo_scuola'].apply(lambda x: x.split(',')[0] if isinstance(x, str) else x)
    
    fig_sun = px.sunburst(
        df_sun,
        path=['area_geografica', 'tipo_scuola', 'Livello Maturità'],
        color='area_geografica',
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    fig_sun.update_layout(height=700, margin=dict(t=0, l=0, r=0, b=0))
    st.plotly_chart(fig_sun, use_container_width=True)
else:
    st.info("Dati insufficienti per il Sunburst Chart.")

# --- 4. 3D SCATTER PLOT ---
st.markdown("---")
st.subheader("🧊 Spazio 3D (Multidimensionale)")
st.caption("Esplora le relazioni tra 3 dimensioni contemporaneamente. Ruota il grafico per vedere i cluster!")

col_x = st.selectbox("Asse X", ['mean_finalita', 'mean_obiettivi', 'mean_governance'], index=0)
col_y = st.selectbox("Asse Y", ['mean_obiettivi', 'mean_governance', 'mean_didattica_orientativa'], index=2)
col_z = st.selectbox("Asse Z", ['mean_didattica_orientativa', 'mean_opportunita', 'ptof_orientamento_maturity_index'], index=1)
col_color = st.selectbox("Colore", ['area_geografica', 'tipo_scuola', 'Livello Maturità'], index=0)

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
else:
    st.warning("Seleziona colonne valide per generare il grafico 3D.")

# --- 5. RIDGELINE PLOT ---
st.markdown("---")
st.subheader("🌊 Distribuzioni a Onde (Ridgeline)")
st.caption("Confronta la forma delle distribuzioni dei punteggi tra diverse categorie.")

# Select Variable and Group
ridge_var = st.selectbox("Variabile (Punteggio)", ['ptof_orientamento_maturity_index', 'mean_finalita', 'mean_obiettivi', 'mean_didattica_orientativa'], index=0)
ridge_group = st.selectbox("Raggruppa per", ['area_geografica', 'tipo_scuola', 'Livello Maturità'], index=0)

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
