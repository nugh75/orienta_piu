# Scegli la Tua Scuola - Percorso guidato per famiglie e studenti

import os
from typing import Dict, List

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from match_engine import FAMILY_PREFERENCE_WEIGHTS, match_for_families
from page_control import setup_page
from data_utils import (
    render_footer,
    TIPI_SCUOLA,
    load_summary_data,
    scale_to_pct,
    format_pct
)

st.set_page_config(page_title="ORIENTA+ | Scegli la Tua Scuola", page_icon="🎓", layout="wide")
setup_page("pages/11_🎓_Scegli_la_Tua_Scuola.py")

st.markdown(
    """
<style>
    .family-tag {
        display: inline-block;
        background: #eef2ff;
        color: #1f2a6b;
        border-radius: 999px;
        padding: 4px 10px;
        font-size: 0.75rem;
        margin-right: 6px;
        margin-bottom: 6px;
    }
    .family-step {
        font-size: 0.9rem;
        color: #444;
        margin-bottom: 10px;
    }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data(ttl=60)
def load_data() -> pd.DataFrame:
    df = load_summary_data()
    for col in [
        "mean_finalita",
        "mean_obiettivi",
        "mean_governance",
        "mean_didattica_orientativa",
        "mean_opportunita",
        "ptof_orientamento_maturity_index",
        "partnership_count",
        "activities_count",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def to_stars(score: float) -> str:
    if pd.isna(score):
        return "N/D"
    scaled = 1 + (float(score) - 1) * 4 / 6
    stars = int(round(max(1, min(5, scaled))))
    return "★" * stars + "☆" * (5 - stars)


def init_state() -> None:
    if "family_step" not in st.session_state:
        st.session_state.family_step = 1
    if "family_filters" not in st.session_state:
        st.session_state.family_filters = {}
    if "family_compare" not in st.session_state:
        st.session_state.family_compare = []


def format_location(row: pd.Series) -> str:
    comune = row.get("comune", "")
    provincia = row.get("provincia", "")
    regione = row.get("regione", "")
    return f"{comune} ({provincia}) - {regione}".strip(" -")


def build_summary(row: pd.Series) -> str:
    ro = float(row.get("ptof_orientamento_maturity_index", 0) or 0)
    did = float(row.get("mean_didattica_orientativa", 0) or 0)
    opp = float(row.get("mean_opportunita", 0) or 0)

    if ro >= 5.0:
        base = "Profilo molto solido"
    elif ro >= 4.0:
        base = "Profilo equilibrato"
    else:
        base = "Profilo da rafforzare"

    focus = []
    if did >= 5.0:
        focus.append("didattica orientativa forte")
    if opp >= 5.0:
        focus.append("buone collaborazioni esterne")

    if focus:
        return f"{base}, con {', '.join(focus)}."
    return f"{base}, con margini di crescita nelle opportunità offerte."


def render_tags(tags: List[str]) -> None:
    if not tags:
        return
    html = "".join([f"<span class='family-tag'>{tag}</span>" for tag in tags])
    st.markdown(html, unsafe_allow_html=True)


def update_compare_list(school_id: str, add: bool) -> None:
    current = list(st.session_state.family_compare)
    if add and school_id not in current and len(current) < 3:
        current.append(school_id)
    if not add and school_id in current:
        current.remove(school_id)
    st.session_state.family_compare = current


def render_step_indicator(step: int) -> None:
    steps = {
        1: "1. Dimmi cosa cerchi",
        2: "2. Ecco le scuole per te",
        3: "3. Confronta le tue scuole",
    }
    st.markdown(f"<div class='family-step'><strong>Step {steps.get(step)}</strong></div>", unsafe_allow_html=True)


def step_one(df: pd.DataFrame) -> None:
    render_step_indicator(1)
    st.header("Dimmi cosa cerchi")
    st.write("Rispondi a poche domande: ti guideremo verso le scuole più adatte.")

    regioni = sorted([r for r in df.get("regione", pd.Series(dtype=str)).dropna().unique() if str(r) not in ("", "ND")])
    tipo_scuola_options = list(TIPI_SCUOLA)
    preferenze = list(FAMILY_PREFERENCE_WEIGHTS.keys())

    with st.form("family_step_one"):
        regione = st.selectbox("Dove abiti? (Regione)", ["Tutte"] + regioni)
        province_source = df if regione == "Tutte" else df[df.get("regione") == regione]
        province = sorted([p for p in province_source.get("provincia", pd.Series(dtype=str)).dropna().unique() if str(p) not in ("", "ND")])
        provincia = st.selectbox("Provincia", ["Tutte"] + province)

        tipi = st.multiselect("Che tipo di scuola cerchi?", tipo_scuola_options)
        scelte = st.multiselect("Cosa ti interessa di più?", preferenze)

        submitted = st.form_submit_button("Continua")

    if submitted:
        st.session_state.family_filters = {
            "regione": None if regione == "Tutte" else regione,
            "provincia": None if provincia == "Tutte" else provincia,
            "tipi": tipi,
            "preferenze": scelte,
        }
        st.session_state.family_compare = []
        st.session_state.family_step = 2
        st.rerun()


def step_two(df: pd.DataFrame) -> None:
    render_step_indicator(2)
    st.header("Ecco le scuole per te")

    filters: Dict = st.session_state.family_filters or {}
    matches = match_for_families(
        df,
        regione=filters.get("regione"),
        provincia=filters.get("provincia"),
        school_types=filters.get("tipi"),
        preferences=filters.get("preferenze"),
        top_n=100,
    )

    if matches.empty:
        st.warning("Nessuna scuola trovata con questi criteri. Prova ad ampliare i filtri.")
        if st.button("Torna indietro"):
            st.session_state.family_step = 1
            st.rerun()
        return

    if "school_id" not in matches.columns:
        st.error("Dati incompleti: manca l'identificativo scuola.")
        return

    compare_ids = st.session_state.family_compare
    selected_names = matches[matches["school_id"].isin(compare_ids)]["denominazione"].tolist()

    if compare_ids:
        st.info(f"Scuole selezionate per il confronto: {', '.join(selected_names)}")

    max_results = st.slider("Numero di scuole da mostrare", min_value=5, max_value=30, value=12)

    for _, row in matches.head(max_results).iterrows():
        school_id = row.get("school_id")
        with st.container():
            st.subheader(row.get("denominazione", "Scuola"))
            st.caption(format_location(row))
            st.write(f"Compatibilità: **{row.get('compatibility_score', 0)} / 100**")
            ro_val = row.get('ptof_orientamento_maturity_index')
            st.write(f"Indice Completezza: **{format_pct(ro_val)} {to_stars(ro_val)}**")
            render_tags(row.get("strength_tags", []))

            col1, col2 = st.columns(2)
            with col1:
                add_disabled = school_id not in compare_ids and len(compare_ids) >= 3
                if st.button(
                    "Aggiungi al confronto" if school_id not in compare_ids else "Rimuovi dal confronto",
                    key=f"compare_{school_id}",
                    disabled=add_disabled,
                ):
                    update_compare_list(school_id, add=school_id not in compare_ids)
                    st.rerun()
            with col2:
                if st.button("Vai al confronto", key=f"goto_compare_{school_id}"):
                    if school_id not in compare_ids:
                        update_compare_list(school_id, add=True)
                    st.session_state.family_step = 3
                    st.rerun()
        st.markdown("---")

    nav_cols = st.columns(2)
    with nav_cols[0]:
        if st.button("Indietro"):
            st.session_state.family_step = 1
            st.rerun()
    with nav_cols[1]:
        if st.button("Confronta le selezionate"):
            if len(st.session_state.family_compare) >= 2:
                st.session_state.family_step = 3
                st.rerun()
            else:
                st.warning("Seleziona almeno 2 scuole per il confronto.")


def step_three(df: pd.DataFrame) -> None:
    render_step_indicator(3)
    st.header("Confronta le tue scuole preferite")

    if "school_id" not in df.columns:
        st.error("Dati incompleti: manca l'identificativo scuola.")
        return

    compare_ids = st.session_state.family_compare
    if len(compare_ids) < 2:
        st.warning("Seleziona almeno 2 scuole per attivare il confronto.")
        if st.button("Torna alla lista"):
            st.session_state.family_step = 2
            st.rerun()
        return

    selected = df[df.get("school_id").isin(compare_ids)].copy()
    if selected.empty:
        st.warning("Non riesco a caricare i dati per le scuole selezionate.")
        return

    table = selected[
        [
            "denominazione",
            "mean_didattica_orientativa",
            "mean_opportunita",
            "mean_governance",
            "ptof_orientamento_maturity_index",
        ]
    ].copy()
    table.columns = [
        "Scuola",
        "Preparazione al futuro (1-7)",
        "Collaborazioni esterne (1-7)",
        "Organizzazione e progetti (1-7)",
        "Indice Completezza (1-7)",
    ]

    # Format numeric columns for display
    for col in table.columns[1:]:
        table[col] = table[col].apply(lambda x: format_pct(x) if pd.notna(x) else "N/D")
    
    st.dataframe(table, use_container_width=True)

    st.subheader("Radar semplificato")
    categories = [
        "Finalità",
        "Obiettivi",
        "Preparazione al futuro",
        "Collaborazioni",
        "Organizzazione",
    ]

    fig = go.Figure()
    for _, row in selected.iterrows():
        values = [
            float(row.get("mean_finalita", 0) or 0),
            float(row.get("mean_obiettivi", 0) or 0),
            float(row.get("mean_didattica_orientativa", 0) or 0),
            float(row.get("mean_opportunita", 0) or 0),
            float(row.get("mean_governance", 0) or 0),
        ]
        values.append(values[0])
        fig.add_trace(
            go.Scatterpolar(
                r=values,
                theta=categories + [categories[0]],
                fill="toself",
                name=row.get("denominazione", "Scuola"),
            )
        )

    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[1, 7])), showlegend=True)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Pro e contro")
    label_map = {
        "mean_finalita": "Orientamento universitario",
        "mean_obiettivi": "Obiettivi chiari",
        "mean_didattica_orientativa": "Preparazione al futuro",
        "mean_opportunita": "Collaborazioni esterne",
        "mean_governance": "Organizzazione",
    }

    for _, row in selected.iterrows():
        st.markdown(f"**{row.get('denominazione')}**")
        scores = {k: float(row.get(k, 0) or 0) for k in label_map}
        sorted_dims = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        top = [label_map[k] for k, _ in sorted_dims[:2]]
        bottom = label_map[sorted_dims[-1][0]] if sorted_dims else ""
        st.write(f"Punti di forza: {', '.join(top)}")
        st.write(f"Da rafforzare: {bottom}")
        st.write(f"Cosa dicono i dati: {build_summary(row)}")
        st.markdown("---")

    nav_cols = st.columns(2)
    with nav_cols[0]:
        if st.button("Torna alla lista"):
            st.session_state.family_step = 2
            st.rerun()
    with nav_cols[1]:
        if st.button("Ricomincia il percorso"):
            st.session_state.family_step = 1
            st.session_state.family_compare = []
            st.rerun()


def main() -> None:
    df = load_data()
    init_state()

    if df.empty:
        st.warning("Nessun dato disponibile. Esegui prima il pipeline di analisi.")
        return

    if st.session_state.family_step == 1:
        step_one(df)
    elif st.session_state.family_step == 2:
        step_two(df)
    else:
        step_three(df)

    render_footer()


main()
