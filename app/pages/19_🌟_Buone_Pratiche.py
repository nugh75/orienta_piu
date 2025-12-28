#!/usr/bin/env python3
"""
Catalogo Buone Pratiche - Esplorazione e analisi delle buone pratiche estratte dai PTOF
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os
from datetime import datetime
from data_utils import render_footer
from page_control import setup_page

st.set_page_config(page_title="ORIENTA+ | Buone Pratiche", page_icon="🧭", layout="wide")
setup_page("pages/19_🌟_Buone_Pratiche.py")

# Custom CSS
st.markdown("""
<style>
    .main .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    div[data-testid="stMetric"] {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #4e73df;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    h1, h2, h3 { color: #2c3e50; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }
    .practice-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        border-left: 4px solid #4e73df;
    }
</style>
""", unsafe_allow_html=True)

# === CONSTANTS ===
BEST_PRACTICES_FILE = 'data/best_practices.json'

CATEGORIE = [
    "Metodologie Didattiche Innovative",
    "Progetti e Attività Esemplari",
    "Partnership e Collaborazioni Strategiche",
    "Azioni di Sistema e Governance",
    "Buone Pratiche per l'Inclusione",
    "Esperienze Territoriali Significative"
]

CATEGORIA_ICONS = {
    "Metodologie Didattiche Innovative": "📚",
    "Progetti e Attività Esemplari": "🎯",
    "Partnership e Collaborazioni Strategiche": "🤝",
    "Azioni di Sistema e Governance": "⚙️",
    "Buone Pratiche per l'Inclusione": "🌈",
    "Esperienze Territoriali Significative": "🗺️"
}

REGION_COORDS = {
    'Piemonte': (45.0703, 7.6869), 'Valle d\'Aosta': (45.7388, 7.4262),
    'Lombardia': (45.4668, 9.1905), 'Trentino-Alto Adige': (46.4993, 11.3548),
    'Veneto': (45.4414, 12.3155), 'Friuli Venezia Giulia': (45.6495, 13.7768),
    'Liguria': (44.4056, 8.9463), 'Emilia-Romagna': (44.4949, 11.3426),
    'Toscana': (43.7711, 11.2486), 'Umbria': (42.9384, 12.6217),
    'Marche': (43.6169, 13.5188), 'Lazio': (41.9028, 12.4964),
    'Abruzzo': (42.3498, 13.3995), 'Molise': (41.5603, 14.6684),
    'Campania': (40.8518, 14.2681), 'Puglia': (41.1258, 16.8666),
    'Basilicata': (40.6395, 15.8053), 'Calabria': (38.9059, 16.5941),
    'Sicilia': (37.6000, 14.0154), 'Sardegna': (40.1209, 9.0129)
}


# === CARICAMENTO DATI ===
@st.cache_data(ttl=30)
def load_practices():
    """Carica le buone pratiche dal file JSON."""
    if os.path.exists(BEST_PRACTICES_FILE):
        try:
            with open(BEST_PRACTICES_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
        except Exception as e:
            st.error(f"Errore caricamento dati: {e}")
            return {"practices": [], "total_practices": 0, "schools_processed": 0}
    return {"practices": [], "total_practices": 0, "schools_processed": 0}


def refresh_data():
    """Forza il refresh dei dati pulendo la cache."""
    load_practices.clear()
    st.rerun()


def filter_practices(practices, categoria=None, regioni=None, tipi_scuola=None,
                     aree_geo=None, province=None, targets=None,
                     maturity_range=None, search_text=None):
    """Filtra le pratiche in base ai criteri selezionati."""
    filtered = practices

    if categoria and categoria != "Tutte":
        filtered = [p for p in filtered if p.get("pratica", {}).get("categoria") == categoria]

    if regioni and len(regioni) > 0:
        filtered = [p for p in filtered if p.get("school", {}).get("regione") in regioni]

    if tipi_scuola and len(tipi_scuola) > 0:
        def has_type(p):
            tipo = p.get("school", {}).get("tipo_scuola", "")
            return any(t in tipo for t in tipi_scuola)
        filtered = [p for p in filtered if has_type(p)]

    if aree_geo and len(aree_geo) > 0:
        filtered = [p for p in filtered if p.get("school", {}).get("area_geografica") in aree_geo]

    if province and len(province) > 0:
        filtered = [p for p in filtered if p.get("school", {}).get("provincia") in province]

    if targets and len(targets) > 0:
        def has_target(p):
            target_text = p.get("pratica", {}).get("target", "").lower()
            return any(t.lower() in target_text for t in targets)
        filtered = [p for p in filtered if has_target(p)]

    if maturity_range and len(maturity_range) == 2:
        min_val, max_val = maturity_range
        def in_maturity_range(p):
            mi = p.get("contesto", {}).get("maturity_index")
            if mi is None:
                return True  # Includi pratiche senza indice
            return min_val <= mi <= max_val
        filtered = [p for p in filtered if in_maturity_range(p)]

    if search_text:
        search_lower = search_text.lower()
        def matches_search(p):
            titolo = p.get("pratica", {}).get("titolo", "").lower()
            descrizione = p.get("pratica", {}).get("descrizione", "").lower()
            metodologia = p.get("pratica", {}).get("metodologia", "").lower()
            target = p.get("pratica", {}).get("target", "").lower()
            nome_scuola = p.get("school", {}).get("nome", "").lower()
            codice = p.get("school", {}).get("codice_meccanografico", "").lower()
            comune = p.get("school", {}).get("comune", "").lower()
            return (search_lower in titolo or
                    search_lower in descrizione or
                    search_lower in metodologia or
                    search_lower in target or
                    search_lower in nome_scuola or
                    search_lower in codice or
                    search_lower in comune)
        filtered = [p for p in filtered if matches_search(p)]

    return filtered


def group_practices(practices, group_by="categoria"):
    """Raggruppa le pratiche per un campo specifico."""
    groups = {}
    for p in practices:
        if group_by == "categoria":
            key = p.get("pratica", {}).get("categoria", "Altro")
        elif group_by == "regione":
            key = p.get("school", {}).get("regione", "N/D")
        elif group_by == "scuola":
            key = p.get("school", {}).get("nome", "N/D")
        elif group_by == "provincia":
            key = p.get("school", {}).get("provincia", "N/D")
        elif group_by == "tipo_scuola":
            key = p.get("school", {}).get("tipo_scuola", "N/D")
        elif group_by == "area_geografica":
            key = p.get("school", {}).get("area_geografica", "N/D")
        else:
            key = "Tutte"

        if key not in groups:
            groups[key] = []
        groups[key].append(p)

    # Ordina gruppi per numero di pratiche (decrescente)
    return dict(sorted(groups.items(), key=lambda x: -len(x[1])))


def practices_to_dataframe(practices):
    """Converte le pratiche in DataFrame per elaborazioni."""
    rows = []
    for p in practices:
        school = p.get("school", {})
        pratica = p.get("pratica", {})
        contesto = p.get("contesto", {})

        rows.append({
            "id": p.get("id", ""),
            "codice": school.get("codice_meccanografico", ""),
            "nome_scuola": school.get("nome", ""),
            "tipo_scuola": school.get("tipo_scuola", ""),
            "regione": school.get("regione", ""),
            "provincia": school.get("provincia", ""),
            "comune": school.get("comune", ""),
            "area_geografica": school.get("area_geografica", ""),
            "categoria": pratica.get("categoria", ""),
            "titolo": pratica.get("titolo", ""),
            "descrizione": pratica.get("descrizione", ""),
            "metodologia": pratica.get("metodologia", ""),
            "target": pratica.get("target", ""),
            "citazione_ptof": pratica.get("citazione_ptof", ""),
            "maturity_index": contesto.get("maturity_index")
        })

    return pd.DataFrame(rows)


# === MAIN PAGE ===
st.title("🌟 Catalogo Buone Pratiche")

# Carica dati
data = load_practices()
practices = data.get("practices", [])

if not practices:
    st.warning("Nessuna buona pratica trovata. Esegui prima `make best-practice-extract` per estrarre le pratiche dai PDF.")
    st.info("""
    **Come estrarre le buone pratiche:**

    1. Assicurati di avere PDF PTOF in `ptof_inbox/` o `ptof_processed/`
    2. Esegui: `make best-practice-extract`
    3. Ricarica questa pagina

    Puoi anche specificare parametri:
    - `make best-practice-extract MODEL=qwen3:32b` - usa un modello specifico
    - `make best-practice-extract LIMIT=10` - limita a 10 PDF
    - `make best-practice-extract FORCE=1` - rielabora tutti i PDF
    """)
    render_footer()
    st.stop()

# === SIDEBAR FILTRI ===
with st.sidebar:
    st.header("🔍 Filtri")

    # Ricerca testuale in alto per visibilita
    search = st.text_input("🔎 Ricerca testuale", placeholder="Cerca in titolo, descrizione, scuola, comune...")

    st.markdown("---")

    # Categoria
    categorie_opzioni = ["Tutte"] + CATEGORIE
    sel_categoria = st.selectbox("Categoria", categorie_opzioni)

    # Target (multiselect)
    st.markdown("**Target**")
    target_options = ["Studenti", "Docenti", "Famiglie", "Primaria", "Secondaria", "Infanzia"]
    sel_targets = st.multiselect("Destinatari", target_options, label_visibility="collapsed")

    # Expander per filtri geografici
    with st.expander("📍 Filtri Geografici", expanded=False):
        # Area geografica
        aree_disponibili = sorted(set(
            p.get("school", {}).get("area_geografica", "")
            for p in practices
            if p.get("school", {}).get("area_geografica")
        ))
        sel_aree = st.multiselect("Area Geografica", aree_disponibili)

        # Regione (multiselect)
        regioni_disponibili = sorted(set(
            p.get("school", {}).get("regione", "")
            for p in practices
            if p.get("school", {}).get("regione")
        ))
        sel_regioni = st.multiselect("Regione", regioni_disponibili)

        # Provincia (multiselect) - filtrata per regioni selezionate
        if sel_regioni:
            province_disponibili = sorted(set(
                p.get("school", {}).get("provincia", "")
                for p in practices
                if p.get("school", {}).get("provincia") and p.get("school", {}).get("regione") in sel_regioni
            ))
        else:
            province_disponibili = sorted(set(
                p.get("school", {}).get("provincia", "")
                for p in practices
                if p.get("school", {}).get("provincia")
            ))
        sel_province = st.multiselect("Provincia", province_disponibili)

    # Expander per filtri scuola
    with st.expander("🏫 Filtri Scuola", expanded=False):
        # Tipo scuola (multiselect)
        tipi_set = set()
        for p in practices:
            tipo = p.get("school", {}).get("tipo_scuola", "")
            for t in tipo.split(","):
                t = t.strip()
                if t:
                    tipi_set.add(t)
        tipi_disponibili = sorted(tipi_set)
        sel_tipi = st.multiselect("Tipo Scuola", tipi_disponibili)

        # Range Maturity Index
        st.markdown("**Indice Maturita RO**")
        maturity_values = [
            p.get("contesto", {}).get("maturity_index")
            for p in practices
            if p.get("contesto", {}).get("maturity_index") is not None
        ]
        if maturity_values:
            min_mi = min(maturity_values)
            max_mi = max(maturity_values)
            sel_maturity = st.slider(
                "Range Indice",
                min_value=float(min_mi),
                max_value=float(max_mi),
                value=(float(min_mi), float(max_mi)),
                step=0.1,
                label_visibility="collapsed"
            )
        else:
            sel_maturity = None

    st.markdown("---")

    # Info dataset
    st.caption(f"📅 Aggiornamento: {data.get('last_updated', 'N/D')[:10] if data.get('last_updated') else 'N/D'}")
    st.caption(f"🤖 Modello: {data.get('extraction_model', 'N/D')}")
    st.caption(f"🏫 Scuole: {data.get('schools_processed', 0)}")
    st.caption(f"📋 Pratiche: {data.get('total_practices', 0)}")

    # Pulsante refresh
    if st.button("🔄 Aggiorna dati", use_container_width=True):
        refresh_data()

    # Reset filtri
    if st.button("🗑️ Reset filtri", use_container_width=True):
        st.rerun()

# Applica filtri
filtered = filter_practices(
    practices,
    categoria=sel_categoria,
    regioni=sel_regioni if sel_regioni else None,
    tipi_scuola=sel_tipi if sel_tipi else None,
    aree_geo=sel_aree if sel_aree else None,
    province=sel_province if sel_province else None,
    targets=sel_targets if sel_targets else None,
    maturity_range=sel_maturity if sel_maturity else None,
    search_text=search if search else None
)

# === TAB LAYOUT ===
tab_catalogo, tab_mappa, tab_grafici, tab_export = st.tabs([
    "📋 Catalogo", "🗺️ Mappa", "📊 Grafici", "📥 Export"
])

# === TAB CATALOGO ===
with tab_catalogo:
    st.subheader(f"📋 {len(filtered)} Buone Pratiche Trovate")

    # Metriche
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Pratiche", len(filtered))
    with col2:
        scuole_uniche = len(set(p.get("school", {}).get("codice_meccanografico", "") for p in filtered))
        st.metric("Scuole", scuole_uniche)
    with col3:
        cat_uniche = len(set(p.get("pratica", {}).get("categoria", "") for p in filtered))
        st.metric("Categorie", cat_uniche)
    with col4:
        regioni_uniche = len(set(p.get("school", {}).get("regione", "") for p in filtered if p.get("school", {}).get("regione")))
        st.metric("Regioni", regioni_uniche)

    st.markdown("---")

    # Ordinamento
    sort_options = ["Categoria", "Regione", "Scuola", "Titolo"]
    sort_by = st.selectbox("Ordina per", sort_options, key="sort_catalogo")

    if sort_by == "Categoria":
        filtered_sorted = sorted(filtered, key=lambda p: p.get("pratica", {}).get("categoria", ""))
    elif sort_by == "Regione":
        filtered_sorted = sorted(filtered, key=lambda p: p.get("school", {}).get("regione", ""))
    elif sort_by == "Scuola":
        filtered_sorted = sorted(filtered, key=lambda p: p.get("school", {}).get("nome", ""))
    else:
        filtered_sorted = sorted(filtered, key=lambda p: p.get("pratica", {}).get("titolo", ""))

    # Lista pratiche con expander
    for i, pratica in enumerate(filtered_sorted):
        school = pratica.get("school", {})
        prat = pratica.get("pratica", {})
        contesto = pratica.get("contesto", {})

        categoria = prat.get("categoria", "")
        icon = CATEGORIA_ICONS.get(categoria, "📌")

        with st.expander(
            f"{icon} {prat.get('titolo', 'Senza titolo')} | "
            f"{school.get('nome', 'Scuola N/D')} ({school.get('regione', 'N/D')})"
        ):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown(f"**Categoria:** {categoria}")
                st.markdown(f"**Descrizione:** {prat.get('descrizione', 'N/D')}")

                if prat.get('metodologia'):
                    st.markdown(f"**Metodologia:** {prat.get('metodologia')}")

                if prat.get('target'):
                    st.markdown(f"**Target:** {prat.get('target')}")

                if prat.get('citazione_ptof'):
                    st.info(f"📝 *\"{prat.get('citazione_ptof')}\"*")

                if prat.get('pagina_evidenza') and prat.get('pagina_evidenza') != "Non specificata":
                    st.caption(f"📄 {prat.get('pagina_evidenza')}")

            with col2:
                st.markdown("**📍 Scuola:**")
                st.markdown(f"**{school.get('nome', 'N/D')}**")
                st.markdown(f"Codice: `{school.get('codice_meccanografico', 'N/D')}`")
                st.markdown(f"{school.get('comune', '')}, {school.get('provincia', '')}")
                st.markdown(f"{school.get('tipo_scuola', 'N/D')}")

                if contesto.get('maturity_index'):
                    st.metric("Indice RO", f"{contesto['maturity_index']:.2f}")

                # Partnership se presenti
                if contesto.get('partnership_coinvolte'):
                    st.markdown("**🤝 Partnership:**")
                    for partner in contesto['partnership_coinvolte'][:5]:
                        st.markdown(f"- {partner}")

# === TAB MAPPA ===
with tab_mappa:
    st.subheader("🗺️ Distribuzione Geografica delle Buone Pratiche")

    # Calcola distribuzione per regione
    reg_counts = {}
    for p in filtered:
        regione = p.get("school", {}).get("regione", "")
        if regione:
            reg_counts[regione] = reg_counts.get(regione, 0) + 1

    if reg_counts:
        # Prepara dati per la mappa
        map_data = []
        for regione, count in reg_counts.items():
            if regione in REGION_COORDS:
                lat, lon = REGION_COORDS[regione]
                map_data.append({
                    "regione": regione,
                    "lat": lat,
                    "lon": lon,
                    "pratiche": count
                })

        if map_data:
            map_df = pd.DataFrame(map_data)

            fig = px.scatter_mapbox(
                map_df,
                lat="lat",
                lon="lon",
                size="pratiche",
                color="pratiche",
                hover_name="regione",
                hover_data={"lat": False, "lon": False, "pratiche": True},
                color_continuous_scale="Viridis",
                size_max=50,
                zoom=4.5,
                center={"lat": 42.0, "lon": 12.5},
                mapbox_style="carto-positron",
                title="Distribuzione Buone Pratiche per Regione"
            )

            fig.update_layout(height=600, margin={"r": 0, "t": 40, "l": 0, "b": 0})
            st.plotly_chart(fig, use_container_width=True)

        # Tabella regioni
        st.subheader("📊 Dettaglio per Regione")
        reg_df = pd.DataFrame([
            {"Regione": k, "Pratiche": v}
            for k, v in sorted(reg_counts.items(), key=lambda x: -x[1])
        ])
        st.dataframe(reg_df, use_container_width=True, hide_index=True)

    else:
        st.info("Nessun dato geografico disponibile per le pratiche filtrate.")

# === TAB GRAFICI ===
with tab_grafici:
    st.subheader("📊 Analisi Distribuzione Buone Pratiche")

    df_filtered = practices_to_dataframe(filtered)

    if not df_filtered.empty:
        col1, col2 = st.columns(2)

        with col1:
            # Distribuzione per categoria
            cat_counts = df_filtered['categoria'].value_counts().reset_index()
            cat_counts.columns = ["Categoria", "Conteggio"]

            fig_cat = px.pie(
                cat_counts,
                names="Categoria",
                values="Conteggio",
                title="Distribuzione per Categoria",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig_cat.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_cat, use_container_width=True)

        with col2:
            # Top 10 regioni
            reg_counts = df_filtered['regione'].value_counts().head(10).reset_index()
            reg_counts.columns = ["Regione", "Conteggio"]

            fig_reg = px.bar(
                reg_counts,
                x="Conteggio",
                y="Regione",
                orientation='h',
                title="Top 10 Regioni",
                color="Conteggio",
                color_continuous_scale="Blues"
            )
            fig_reg.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig_reg, use_container_width=True)

        # Distribuzione per tipo scuola
        tipo_counts = {}
        for tipo in df_filtered['tipo_scuola']:
            for t in str(tipo).split(","):
                t = t.strip()
                if t:
                    tipo_counts[t] = tipo_counts.get(t, 0) + 1

        if tipo_counts:
            tipo_df = pd.DataFrame([
                {"Tipo": k, "Conteggio": v}
                for k, v in sorted(tipo_counts.items(), key=lambda x: -x[1])
            ])

            fig_tipo = px.bar(
                tipo_df,
                x="Tipo",
                y="Conteggio",
                title="Distribuzione per Tipo Scuola",
                color="Conteggio",
                color_continuous_scale="Greens"
            )
            st.plotly_chart(fig_tipo, use_container_width=True)

        # Heatmap categoria x regione (se dati sufficienti)
        if len(df_filtered) >= 10:
            st.subheader("🔥 Heatmap Categoria x Regione")

            pivot = df_filtered.groupby(['regione', 'categoria']).size().reset_index(name='count')
            pivot_table = pivot.pivot(index='regione', columns='categoria', values='count').fillna(0)

            if not pivot_table.empty and len(pivot_table) > 1:
                fig_heat = px.imshow(
                    pivot_table,
                    labels=dict(x="Categoria", y="Regione", color="Pratiche"),
                    aspect="auto",
                    color_continuous_scale="YlOrRd"
                )
                fig_heat.update_layout(height=max(400, len(pivot_table) * 25))
                st.plotly_chart(fig_heat, use_container_width=True)

    else:
        st.info("Nessun dato disponibile per i grafici.")

# === TAB EXPORT ===
with tab_export:
    st.subheader("📥 Esporta Dati")

    st.markdown(f"**{len(filtered)} pratiche** pronte per l'esportazione (filtrate)")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📄 Formato JSON")
        st.markdown("Esporta i dati completi in formato JSON.")

        json_data = json.dumps(
            {
                "exported_at": datetime.now().isoformat(),
                "filters_applied": {
                    "categoria": sel_categoria if sel_categoria != "Tutte" else None,
                    "regioni": sel_regioni if sel_regioni else None,
                    "tipi_scuola": sel_tipi if sel_tipi else None,
                    "aree_geografiche": sel_aree if sel_aree else None,
                    "search_text": search if search else None
                },
                "total_practices": len(filtered),
                "practices": filtered
            },
            ensure_ascii=False,
            indent=2
        )

        st.download_button(
            "📥 Scarica JSON",
            data=json_data.encode('utf-8'),
            file_name=f"buone_pratiche_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
            mime="application/json"
        )

    with col2:
        st.markdown("### 📊 Formato CSV")
        st.markdown("Esporta un riepilogo tabellare in formato CSV.")

        df_export = practices_to_dataframe(filtered)

        if not df_export.empty:
            csv_data = df_export.to_csv(index=False)

            st.download_button(
                "📥 Scarica CSV",
                data=csv_data.encode('utf-8'),
                file_name=f"buone_pratiche_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )
        else:
            st.info("Nessun dato da esportare.")

    # Anteprima tabella
    st.markdown("### 👁️ Anteprima Dati")
    if not df_export.empty:
        st.dataframe(
            df_export[['titolo', 'categoria', 'nome_scuola', 'regione', 'tipo_scuola']].head(20),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Nessun dato da visualizzare.")

render_footer()
