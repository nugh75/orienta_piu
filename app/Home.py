# 🏠 Home - Dashboard Riepilogativa

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from app.data_utils import GESTIONE_SCUOLA, normalize_statale_paritaria

st.set_page_config(page_title="ORIENTA+ | Home", page_icon="🧭", layout="wide")

# CSS
st.markdown("""
<style>
    div[data-testid="stMetric"] {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #4e73df;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .big-metric {
        font-size: 2.5rem !important;
        font-weight: bold;
        color: #2c3e50;
    }
</style>
""", unsafe_allow_html=True)

SUMMARY_FILE = 'data/analysis_summary.csv'

DIMENSIONS = {
    'mean_finalita': 'Finalita',
    'mean_obiettivi': 'Obiettivi',
    'mean_governance': 'Governance',
    'mean_didattica_orientativa': 'Didattica',
    'mean_opportunita': 'Opportunita'
}

@st.cache_data(ttl=60)
def load_data():
    if os.path.exists(SUMMARY_FILE):
        return pd.read_csv(SUMMARY_FILE)
    return pd.DataFrame()

df = load_data()

# === SIDEBAR: LA MIA SCUOLA ===
with st.sidebar:
    st.markdown("### 🏠 La Mia Scuola")

    if 'my_school_name' in st.session_state and st.session_state['my_school_name']:
        my_school_name = st.session_state['my_school_name']
        st.success(f"**{my_school_name[:30]}**")

        # Mostra mini-info se i dati sono disponibili
        if not df.empty and 'school_id' in st.session_state:
            my_school_id = st.session_state.get('my_school_id')
            my_school_data = df[df['school_id'] == my_school_id]
            if not my_school_data.empty:
                my_school = my_school_data.iloc[0]
                ro = my_school.get('ptof_orientamento_maturity_index', 0)
                if pd.notna(ro):
                    st.metric("Indice RO", f"{ro:.2f}/7")

        if st.button("📊 Vai alla Mia Scuola", use_container_width=True):
            st.switch_page("pages/01_🏠_La_Mia_Scuola.py")

        if st.button("🔄 Cambia scuola", use_container_width=True):
            st.switch_page("pages/01_🏠_La_Mia_Scuola.py")
    else:
        st.info("Nessuna scuola selezionata")
        if st.button("➕ Seleziona la tua scuola", use_container_width=True):
            st.switch_page("pages/01_🏠_La_Mia_Scuola.py")

    st.markdown("---")

st.title("🧭 ORIENTA+")
st.markdown("**Piattaforma di Analisi della Robustezza dell'Orientamento nei PTOF**")

# === PREFAZIONE ===
with st.expander("📖 **Perché ORIENTA+** — Clicca per scoprire cosa puoi fare", expanded=False):
    st.markdown("""
### Perché ORIENTA+

Questa piattaforma nasce per rispondere a una domanda concreta: **come può una scuola migliorare il proprio approccio all'orientamento?**

La risposta non sta solo nei numeri o negli indici, ma nella possibilità di guardarsi intorno, confrontarsi e imparare da chi affronta sfide simili.

---

### Cosa puoi fare con questo strumento

#### Scoprire chi ti è vicino

Ogni scuola opera in un contesto territoriale specifico, con risorse, vincoli e opportunità proprie. Questa dashboard ti permette di individuare scuole geograficamente vicine o con caratteristiche simili alla tua — per tipologia, dimensione, contesto socioeconomico.

Non si tratta solo di curiosità: conoscere le scuole affini significa poter avviare collaborazioni, costruire reti territoriali, condividere progetti. L'orientamento efficace spesso nasce dalla collaborazione tra istituti che condividono lo stesso bacino di studenti o le stesse sfide.

#### Confrontare le metodologie

Cosa fanno le altre scuole per l'orientamento? Quali progetti attivano? Come integrano la didattica orientativa nel curricolo?

Questa dashboard ti consente di esplorare le pratiche documentate nei PTOF di centinaia di scuole italiane. Puoi vedere quali approcci adottano le scuole con i punteggi più alti, quali metodologie risultano più diffuse nella tua regione, quali innovazioni stanno emergendo.

L'obiettivo non è copiare, ma lasciarsi ispirare. Ogni scuola ha la propria identità, ma le buone idee meritano di circolare.

#### Valutare la completezza del tuo PTOF

Il Piano Triennale dell'Offerta Formativa dovrebbe rappresentare in modo completo la visione della scuola sull'orientamento. Ma è davvero così?

L'Indice di Robustezza dell'Orientamento (RO) e le cinque dimensioni analizzate — Finalità, Obiettivi, Governance, Didattica Orientativa, Opportunità — ti permettono di capire se il tuo PTOF copre tutti gli aspetti fondamentali o se ci sono aree da sviluppare.

Non si tratta di un giudizio, ma di una mappa: sapere dove sei ti aiuta a decidere dove andare.
""")

st.subheader("⚡ Azioni rapide")
action_cols = st.columns(3)
with action_cols[0]:
    if st.button("🏫 Dettaglio Scuola", use_container_width=True):
        st.switch_page("pages/01_🏠_La_Mia_Scuola.py")
with action_cols[1]:
    if st.button("🗺️ Analisi Territoriale", use_container_width=True):
        st.switch_page("pages/04_🗺️_Analisi_Territoriale.py")
with action_cols[2]:
    if st.button("💡 Best Practice", use_container_width=True):
        st.switch_page("pages/09_💡_Best_Practice.py")

if df.empty:
    st.warning("Nessun dato disponibile. Esegui prima il pipeline di analisi.")
    st.stop()

# Converti colonne numeriche
numeric_cols = ['ptof_orientamento_maturity_index'] + list(DIMENSIONS.keys())
for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

st.markdown("---")

# === KPI PRINCIPALI ===
st.subheader("📊 KPI Principali")

ro_series = pd.to_numeric(df['ptof_orientamento_maturity_index'], errors='coerce').dropna()
n_scuole = len(df)
mean_ro = ro_series.mean() if not ro_series.empty else float("nan")
median_ro = ro_series.median() if not ro_series.empty else None
p25 = ro_series.quantile(0.25) if not ro_series.empty else None
p75 = ro_series.quantile(0.75) if not ro_series.empty else None
pct_ge_4 = (ro_series >= 4).mean() * 100 if not ro_series.empty else None
pct_lt_3 = (ro_series < 3).mean() * 100 if not ro_series.empty else None
excellent = int((ro_series >= 5).sum()) if not ro_series.empty else 0
pct_excellent = (excellent / n_scuole * 100) if n_scuole > 0 else 0

row1 = st.columns(4)
with row1[0]:
    st.metric("🏫 Scuole Analizzate", f"{n_scuole:,}")
with row1[1]:
    if pd.notna(mean_ro):
        st.metric("📈 Indice RO Medio", f"{mean_ro:.2f}/7")
    else:
        st.metric("📈 Indice RO Medio", "N/D")
with row1[2]:
    if median_ro is not None:
        st.metric("📌 Mediana RO", f"{median_ro:.2f}/7")
    else:
        st.metric("📌 Mediana RO", "N/D")
with row1[3]:
    if pct_ge_4 is not None:
        st.metric("✅ RO >= 4", f"{pct_ge_4:.1f}%")
    else:
        st.metric("✅ RO >= 4", "N/D")

row2 = st.columns(4)
with row2[0]:
    st.metric("🏆 Eccellenti (RO >= 5)", f"{excellent} ({pct_excellent:.1f}%)")
with row2[1]:
    if 'has_sezione_dedicata' in df.columns:
        sezione_vals = pd.to_numeric(df['has_sezione_dedicata'], errors='coerce').fillna(0)
        pct_sezione = (sezione_vals == 1).mean() * 100 if len(sezione_vals) > 0 else 0
        st.metric("🧭 Sezione Orientamento", f"{pct_sezione:.1f}%")
    else:
        st.metric("🧭 Sezione Orientamento", "N/D")
with row2[2]:
    n_regioni = df['regione'].nunique() if 'regione' in df.columns else 0
    st.metric("🗺️ Regioni Coperte", n_regioni)
with row2[3]:
    n_tipi = df['tipo_scuola'].nunique() if 'tipo_scuola' in df.columns else 0
    st.metric("📚 Tipologie Scuola", n_tipi)

st.markdown("#### 📌 Distribuzione Indice RO")
dist_cols = st.columns(2)
with dist_cols[0]:
    if p25 is not None and p75 is not None:
        st.metric("P25-P75", f"{p25:.2f}-{p75:.2f}")
    else:
        st.metric("P25-P75", "N/D")
with dist_cols[1]:
    if pct_lt_3 is not None:
        st.metric("RO < 3", f"{pct_lt_3:.1f}%")
    else:
        st.metric("RO < 3", "N/D")

with st.expander("Toplist distribuzione (P25-P75)"):
    if ro_series.empty or p25 is None or p75 is None:
        st.info("Distribuzione non disponibile.")
    else:
        bands = pd.cut(
            ro_series,
            bins=[-float("inf"), p25, p75, float("inf")],
            labels=[
                f"<= P25 ({p25:.2f})",
                f"P25-P75 ({p25:.2f}-{p75:.2f})",
                f">= P75 ({p75:.2f})"
            ],
            include_lowest=True
        )
        band_counts = bands.value_counts().reset_index()
        band_counts.columns = ['Fascia RO', 'N. Scuole']
        band_counts['%'] = (band_counts['N. Scuole'] / len(ro_series) * 100).round(1).astype(str) + "%"
        st.dataframe(band_counts, use_container_width=True, hide_index=True)

        top_quartile = df[df['ptof_orientamento_maturity_index'] >= p75][
            ['denominazione', 'regione', 'ptof_orientamento_maturity_index']
        ].copy()
        top_quartile = top_quartile.dropna(subset=['ptof_orientamento_maturity_index'])
        top_quartile = top_quartile.sort_values('ptof_orientamento_maturity_index', ascending=False)
        top_quartile = top_quartile.head(20)
        top_quartile.columns = ['Scuola', 'Regione', 'Indice RO']
        top_quartile['Indice RO'] = top_quartile['Indice RO'].round(2)

        if not top_quartile.empty:
            st.caption(f"Toplist scuole in fascia >= P75 ({p75:.2f}) - prime 20")
            st.dataframe(top_quartile, use_container_width=True, hide_index=True)
        else:
            st.info("Nessuna scuola disponibile nella fascia P75.")



st.markdown("#### 📌 Copertura e reti")
extra_cols = st.columns(4)

def _nunique_nonempty(series):
    if series is None:
        return 0
    values = series.dropna().astype(str).str.strip()
    values = values[values != ""]
    return values.nunique()

with extra_cols[0]:
    province_count = _nunique_nonempty(df['provincia']) if 'provincia' in df.columns else 0
    st.metric("Province coperte", province_count)

with extra_cols[1]:
    comuni_count = _nunique_nonempty(df['comune']) if 'comune' in df.columns else 0
    st.metric("Comuni coperti", comuni_count)

with extra_cols[2]:
    if 'partnership_count' in df.columns:
        partner_vals = pd.to_numeric(df['partnership_count'], errors='coerce').fillna(0)
        partner_count = int((partner_vals > 0).sum())
        pct_partner = (partner_vals > 0).mean() * 100 if len(partner_vals) > 0 else 0
        st.metric("Scuole con partnership", f"{partner_count} ({pct_partner:.1f}%)")
    else:
        st.metric("Scuole con partnership", "N/D")

with extra_cols[3]:
    if 'partnership_count' in df.columns:
        partner_vals = pd.to_numeric(df['partnership_count'], errors='coerce').fillna(0)
        st.metric("Partnership medie", f"{partner_vals.mean():.2f}")
    else:
        st.metric("Partnership medie", "N/D")

st.markdown("---")

# === GRAFICI PRINCIPALI ===
col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 Distribuzione Indice RO")

    fig_hist = px.histogram(
        df, x='ptof_orientamento_maturity_index',
        nbins=20,
        color_discrete_sequence=['#4e73df'],
        labels={'ptof_orientamento_maturity_index': 'Indice RO'}
    )
    fig_hist.update_layout(
        showlegend=False,
        xaxis_title="Indice RO (1-7)",
        yaxis_title="N. Scuole",
        height=350
    )
    if pd.notna(mean_ro):
        fig_hist.add_vline(x=mean_ro, line_dash="dash", line_color="red",
                           annotation_text=f"Media: {mean_ro:.2f}")
    st.plotly_chart(fig_hist, use_container_width=True)

with col2:
    st.subheader("🕸️ Profilo Medio Nazionale")

    if all(c in df.columns for c in DIMENSIONS.keys()):
        dim_means = [df[c].mean() for c in DIMENSIONS.keys()]
        dim_labels = list(DIMENSIONS.values())

        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=dim_means + [dim_means[0]],
            theta=dim_labels + [dim_labels[0]],
            fill='toself',
            name='Media Nazionale',
            line_color='#4e73df',
            fillcolor='rgba(78, 115, 223, 0.3)'
        ))
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 7])),
            showlegend=False,
            height=350
        )
        st.plotly_chart(fig_radar, use_container_width=True)

st.markdown("---")

st.subheader("🎯 Gap Analysis")
gap_cols = st.columns(len(DIMENSIONS))
for idx, (col_key, col_name) in enumerate(DIMENSIONS.items()):
    with gap_cols[idx]:
        if col_key in df.columns:
            val = df[col_key].mean()
            gap = 7 - val
            st.metric(col_name, f"{val:.2f}/7", f"Gap: {gap:.2f}")
        else:
            st.metric(col_name, "N/D")

st.markdown("---")

st.subheader("📊 Media per Tipologia")

if 'tipo_scuola' in df.columns:
    try:
        from app.data_utils import TIPI_SCUOLA, explode_school_types
        df_tipo = explode_school_types(df)
        df_tipo = df_tipo[df_tipo['tipo_scuola'].isin(TIPI_SCUOLA)]
    except Exception:
        df_tipo = df.copy()
        TIPI_SCUOLA = ['Infanzia', 'Primaria', 'I Grado', 'Liceo', 'Tecnico', 'Professionale']

    tipo_stats = df_tipo.groupby('tipo_scuola')['ptof_orientamento_maturity_index'].mean().reset_index()
    tipo_stats.columns = ['Tipologia', 'Media']
    tipo_stats = (
        tipo_stats.set_index('Tipologia')
        .reindex(TIPI_SCUOLA)
        .dropna(subset=['Media'])
        .reset_index()
    )

    tipo_cols = st.columns(2)
    with tipo_cols[0]:
        if not tipo_stats.empty:
            fig_tipo = px.bar(
                tipo_stats,
                x='Media', y='Tipologia',
                orientation='h',
                color='Media',
                color_continuous_scale='RdYlGn',
                range_color=[1, 7],
                category_orders={"Tipologia": TIPI_SCUOLA}
            )
            fig_tipo.update_layout(
                showlegend=False,
                height=300,
                xaxis_range=[0, 7]
            )
            st.plotly_chart(fig_tipo, use_container_width=True)
        else:
            st.info("Nessun dato valido per le tipologie canoniche")

    with tipo_cols[1]:
        if not df_tipo.empty:
            tipo_counts = (
                df_tipo['tipo_scuola']
                .value_counts()
                .reindex(TIPI_SCUOLA)
                .dropna()
                .reset_index()
            )
            tipo_counts.columns = ['Tipologia', 'N. Scuole']
            fig_tipo_dist = px.pie(
                tipo_counts,
                names='Tipologia',
                values='N. Scuole',
                title="Distribuzione Tipologie (canoniche)",
                hole=0.4,
                category_orders={"Tipologia": TIPI_SCUOLA}
            )
            fig_tipo_dist.update_layout(height=300, margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig_tipo_dist, use_container_width=True)
        else:
            st.info("Distribuzione tipologie non disponibile")
else:
    st.info("Colonna 'tipo_scuola' non disponibile nel dataset.")

tipologie_canoniche_md = """
**Tipologie scuola canoniche (6):**
- Infanzia
- Primaria
- I Grado
- Liceo
- Tecnico
- Professionale
"""

tipologie_note_md = (
    "_Nota: il KPI “Tipologie Scuola” può risultare >6 perché il campo `tipo_scuola` nel "
    'dataset contiene combinazioni di più ordini (es. "Infanzia, Primaria, I Grado")._'
)

if 'tipo_scuola' in df.columns:
    tipo_series = df['tipo_scuola'].dropna().astype(str)
    tipo_series = tipo_series[tipo_series.str.strip() != '']
    if not tipo_series.empty:
        tipo_counts = tipo_series.value_counts().reset_index()
        tipo_counts.columns = ['Tipologia (combinazioni)', 'N. Scuole']
        with st.expander("Toplist tipologie (combinazioni presenti nel dataset)"):
            st.markdown(tipologie_canoniche_md)
            st.markdown(tipologie_note_md)
            st.dataframe(tipo_counts, use_container_width=True, hide_index=True)
    else:
        st.markdown(tipologie_canoniche_md)
        st.markdown(tipologie_note_md)
else:
    st.markdown(tipologie_canoniche_md)
    st.markdown(tipologie_note_md)

st.markdown("---")

# === STATALE / PARITARIA ===
st.subheader("🏛️ Statali vs Paritarie")
st.caption("Distribuzione gestione scuola (normalizzata)")

if 'statale_paritaria' in df.columns:
    gestione = df['statale_paritaria'].apply(normalize_statale_paritaria)
    counts = gestione.value_counts()
    statali = int(counts.get('Statale', 0))
    paritarie = int(counts.get('Paritaria', 0))
    nd = int(counts.get('ND', 0))
    altro = int(counts.get('Altro', 0))
    total = statali + paritarie + nd + altro

    col_g1, col_g2, col_g3 = st.columns(3)
    with col_g1:
        pct_statali = (statali / total * 100) if total > 0 else 0
        st.metric("Statali", f"{statali} ({pct_statali:.1f}%)")
    with col_g2:
        pct_paritarie = (paritarie / total * 100) if total > 0 else 0
        st.metric("Paritarie", f"{paritarie} ({pct_paritarie:.1f}%)")
    with col_g3:
        st.metric("Non classificate (ND)", f"{nd}")

    if total > 0:
        chart_labels = []
        chart_values = []
        for label in GESTIONE_SCUOLA + ['ND']:
            value = counts.get(label, 0)
            if value > 0:
                chart_labels.append(label)
                chart_values.append(value)
        if altro > 0:
            chart_labels.append('Altro')
            chart_values.append(altro)

        fig_sp = px.pie(
            names=chart_labels,
            values=chart_values,
            title="Distribuzione Statale/Paritaria",
            hole=0.4
        )
        fig_sp.update_layout(height=300, margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig_sp, use_container_width=True)

    if altro > 0:
        st.warning(f"Valori non riconosciuti in 'statale_paritaria': {altro} record")
else:
    st.info("Colonna 'statale_paritaria' non disponibile nel dataset.")

st.subheader("⚖️ Confronti territoriali")
geo_cols = st.columns(1)

with geo_cols[0]:
    st.markdown("#### Nord vs Centro vs Sud")
    st.caption("Nord = Nord Ovest + Nord Est | Centro = Centro | Sud = Sud + Isole")
    if 'area_geografica' in df.columns:
        df_area = df.copy()
        df_area['ro'] = pd.to_numeric(df_area['ptof_orientamento_maturity_index'], errors='coerce')

        def _area_macro(value):
            if pd.isna(value):
                return None
            val = str(value).strip()
            if val in ("Nord Ovest", "Nord Est"):
                return "Nord"
            if val == "Centro":
                return "Centro"
            if val in ("Sud", "Isole"):
                return "Sud"
            return None

        df_area['area_macro'] = df_area['area_geografica'].apply(_area_macro)
        df_area = df_area.dropna(subset=['ro', 'area_macro'])
        area_stats = df_area.groupby('area_macro')['ro'].agg(['mean', 'count']).reset_index()
        area_stats.columns = ['Area', 'Media', 'N. Scuole']
        area_stats['Media'] = area_stats['Media'].round(2)

        metric_cols = st.columns(3)
        for idx, area in enumerate(["Nord", "Centro", "Sud"]):
            with metric_cols[idx]:
                row = area_stats[area_stats['Area'] == area]
                if not row.empty:
                    mean_val = row.iloc[0]['Media']
                    count_val = int(row.iloc[0]['N. Scuole'])
                    st.metric(area, f"{mean_val:.2f}/7", f"n={count_val}")
                else:
                    st.metric(area, "N/D")

        if not area_stats.empty:
            fig_area = px.bar(
                area_stats,
                x='Media', y='Area',
                orientation='h',
                color='Media',
                color_continuous_scale='RdYlGn',
                range_color=[1, 7]
            )
            fig_area.update_layout(
                showlegend=False,
                height=260,
                xaxis_range=[0, 7],
                yaxis=dict(categoryorder="array", categoryarray=["Nord", "Centro", "Sud"])
            )
            st.plotly_chart(fig_area, use_container_width=True)

            fig_area_pie = px.pie(
                area_stats,
                names='Area',
                values='N. Scuole',
                title="Distribuzione Nord/Centro/Sud",
                hole=0.4,
                category_orders={"Area": ["Nord", "Centro", "Sud"]}
            )
            fig_area_pie.update_layout(height=260, margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig_area_pie, use_container_width=True)
        else:
            st.info("Dati insufficienti per il confronto Nord/Centro/Sud.")
    else:
        st.info("Colonna 'area_geografica' non disponibile nel dataset.")

st.markdown("#### Metropolitano vs Non Metropolitano")
if 'territorio' in df.columns:
    df_terr = df.copy()
    df_terr['ro'] = pd.to_numeric(df_terr['ptof_orientamento_maturity_index'], errors='coerce')
    df_terr['territorio'] = df_terr['territorio'].astype(str).str.strip()
    valid_terr = ["Metropolitano", "Non Metropolitano"]
    extra = df_terr[~df_terr['territorio'].isin(valid_terr)]
    df_terr = df_terr[df_terr['territorio'].isin(valid_terr)]
    df_terr = df_terr.dropna(subset=['ro'])

    terr_stats = df_terr.groupby('territorio')['ro'].agg(['mean', 'count']).reset_index()
    terr_stats.columns = ['Territorio', 'Media', 'N. Scuole']
    terr_stats['Media'] = terr_stats['Media'].round(2)

    terr_cols = st.columns(2)
    for idx, label in enumerate(valid_terr):
        with terr_cols[idx]:
            row = terr_stats[terr_stats['Territorio'] == label]
            if not row.empty:
                mean_val = row.iloc[0]['Media']
                count_val = int(row.iloc[0]['N. Scuole'])
                st.metric(label, f"{mean_val:.2f}/7", f"n={count_val}")
            else:
                st.metric(label, "N/D")

    if not terr_stats.empty:
        fig_terr = px.bar(
            terr_stats.sort_values('Media', ascending=True),
            x='Media', y='Territorio',
            orientation='h',
            color='Media',
            color_continuous_scale='RdYlGn',
            range_color=[1, 7],
            category_orders={"Territorio": valid_terr}
        )
        fig_terr.update_layout(showlegend=False, height=260, xaxis_range=[0, 7])
        st.plotly_chart(fig_terr, use_container_width=True)

        fig_terr_pie = px.pie(
            terr_stats,
            names='Territorio',
            values='N. Scuole',
            title="Distribuzione Territorio",
            hole=0.4,
            category_orders={"Territorio": valid_terr}
        )
        fig_terr_pie.update_layout(height=260, margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig_terr_pie, use_container_width=True)
    else:
        st.info("Dati insufficienti per il confronto metropolitano.")

    if not extra.empty:
        st.caption(f"Esclusi {len(extra)} record con territorio non classificato.")
else:
    st.info("Colonna 'territorio' non disponibile nel dataset.")

st.markdown("---")

# === MAPPA RAPIDA ===
st.subheader("🗺️ Panoramica Regionale")
st.caption("Indice RO normalizzato per tipologia: ogni tipo pesa allo stesso modo")

if 'regione' in df.columns:
    try:
        from app.data_utils import TIPI_SCUOLA
    except Exception:
        TIPI_SCUOLA = ['Infanzia', 'Primaria', 'I Grado', 'Liceo', 'Tecnico', 'Professionale']

    def get_primary_type(tipo):
        if pd.isna(tipo):
            return None
        for part in str(tipo).split(','):
            t = part.strip()
            if t in TIPI_SCUOLA:
                return t
        return None

    df_norm = df.copy()
    if 'tipo_scuola' in df_norm.columns:
        df_norm['tipo_primario'] = df_norm['tipo_scuola'].apply(get_primary_type)
        df_norm = df_norm[df_norm['tipo_primario'].isin(TIPI_SCUOLA)]
    else:
        df_norm = pd.DataFrame()

    if not df_norm.empty:
        overall_mean = df_norm['ptof_orientamento_maturity_index'].mean()
        type_means = df_norm.groupby('tipo_primario')['ptof_orientamento_maturity_index'].mean()
        df_norm['score_norm'] = (
            df_norm['ptof_orientamento_maturity_index']
            - df_norm['tipo_primario'].map(type_means)
            + overall_mean
        )

        region_stats = df_norm.groupby('regione').agg({
            'score_norm': ['mean', 'count'],
            'tipo_primario': 'nunique'
        }).round(2).reset_index()
        region_stats.columns = ['Regione', 'Media Normalizzata', 'N. Scuole', 'Tipi Coperti']
        region_stats = region_stats[region_stats['Regione'] != 'Non Specificato']
        region_stats = region_stats.sort_values('Media Normalizzata', ascending=False)
    else:
        region_stats = pd.DataFrame()

    col5, col6 = st.columns([2, 1])

    with col5:
        if not region_stats.empty:
            fig_region = px.bar(
                region_stats.sort_values('Media Normalizzata', ascending=True),
                x='Media Normalizzata', y='Regione',
                orientation='h',
                color='Media Normalizzata',
                color_continuous_scale='RdYlGn',
                range_color=[1, 7],
                text='N. Scuole'
            )
            fig_region.update_traces(texttemplate='n=%{text}', textposition='outside')
            fig_region.update_layout(height=500, xaxis_range=[0, 7.5])
            st.plotly_chart(fig_region, use_container_width=True)
        else:
            st.info("Dati insufficienti per il confronto regionale normalizzato.")

    with col6:
        st.markdown("### 📈 Statistiche Normalizzate")

        if not region_stats.empty:
            mean_norm = region_stats['Media Normalizzata'].mean()
            median_types = region_stats['Tipi Coperti'].median()
            full_coverage = (region_stats['Tipi Coperti'] == len(TIPI_SCUOLA)).sum()

            st.metric("Media Normalizzata (regioni)", f"{mean_norm:.2f}/7")
            st.metric("Copertura Tipi (mediana)", f"{median_types:.0f}/6")
            st.metric("Regioni con copertura completa", f"{full_coverage}/{len(region_stats)}")
            st.caption("Normalizzazione: media per tipologia con peso uguale.")
        else:
            st.info("Statistiche normalizzate non disponibili.")

st.markdown("---")

st.subheader("🏆 Top 5 Scuole")

top5 = df.nlargest(5, 'ptof_orientamento_maturity_index')[
    ['denominazione', 'regione', 'ptof_orientamento_maturity_index']
].copy()
top5.columns = ['Scuola', 'Regione', 'Indice RO']
top5['Indice RO'] = top5['Indice RO'].round(2)
top5.insert(0, 'Pos', ['🥇', '🥈', '🥉', '4°', '5°'])
st.dataframe(top5, use_container_width=True, hide_index=True)

st.markdown("---")

# === NAVIGAZIONE RAPIDA ===
st.subheader("🧭 Navigazione Rapida")

nav_cols = st.columns(4)

with nav_cols[0]:
    st.info("""
    **🏫 Dettaglio Scuola**

    Analisi approfondita di una singola scuola con:
    - Profilo radar
    - Gap analysis
    - Confronto peer
    """)

with nav_cols[1]:
    st.info("""
    **🗺️ Analisi Territoriale**

    Confronti geografici con:
    - Mappa Italia
    - Confronti gruppi
    - Report regionali
    """)

with nav_cols[2]:
    st.info("""
    **🏆 Ranking & Benchmark**

    Classifiche e statistiche:
    - Top performers
    - Indicatori avanzati
    - Quadranti performance
    """)

with nav_cols[3]:
    st.info("""
    **💡 Best Practice**

    Analisi qualitativa:
    - Mining progetti
    - Report narrativi
    - Metodologie efficaci
    """)

st.markdown("---")
st.caption("🧭 ORIENTA+ | Piattaforma di analisi della robustezza dell'orientamento nei PTOF")
