# Gestione Pesi Indici - Pagina Admin ORIENTA+
# Permette di configurare i pesi per il calcolo degli indici di maturita

import streamlit as st
import sys
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Add parent for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from page_control import setup_page, is_admin_logged_in
from data_utils import render_footer

# Import weights manager
from src.utils.weights_manager import (
    load_weights_config,
    save_weights_config,
    validate_weights,
    normalize_weights,
    get_default_config,
    get_presets,
    save_as_preset,
    delete_preset,
    get_weight_summary,
    DIMENSION_LABELS,
    INDICATOR_LABELS
)

st.set_page_config(page_title="ORIENTA+ | Gestione Pesi", page_icon="⚖️", layout="wide")
setup_page("pages/22_Pesi.py")

st.title("⚖️ Gestione Pesi Indici")
st.markdown("Configura i pesi per il calcolo dell'Indice di Maturita dell'Orientamento")

# Admin check
if not is_admin_logged_in():
    st.warning("Questa pagina e riservata all'amministratore.")
    st.info("Effettua il login come admin dalla sidebar per accedere.")
    st.stop()

st.success("Connesso come amministratore")

# Load current config
config = load_weights_config()


# ==================================================
# SINCRONIZZAZIONE SLIDER <-> NUMBER_INPUT
# Usa session_state come unica sorgente di verità
# ==================================================

def init_weight_state(key: str, default_value: int):
    """Inizializza lo stato per un peso se non esiste."""
    if key not in st.session_state:
        st.session_state[key] = default_value


def sync_slider_to_num(slider_key: str, num_key: str):
    """Callback: slider cambiato -> aggiorna number_input."""
    st.session_state[num_key] = st.session_state[slider_key]


def sync_num_to_slider(num_key: str, slider_key: str):
    """Callback: number_input cambiato -> aggiorna slider."""
    # Clamp value to slider range
    val = st.session_state[num_key]
    val = max(0, min(100, val))
    st.session_state[slider_key] = val
    st.session_state[num_key] = val  # Ensure clamped value

# Tabs
tab_dims, tab_indicators, tab_presets, tab_preview = st.tabs([
    "📊 Pesi Dimensioni",
    "📋 Pesi Indicatori",
    "📁 Preset",
    "👁️ Anteprima"
])

# ===============================
# TAB 1: Pesi Dimensioni
# ===============================
with tab_dims:
    st.subheader("Pesi delle 5 Dimensioni")
    st.markdown("""
    Configura quanto ogni dimensione contribuisce all'indice finale.
    La somma deve essere uguale a **100%**.
    """)

    dim_weights = config.get("dimension_weights", get_default_config()["dimension_weights"])

    st.markdown("### Configura Pesi")

    # Inizializza session_state per tutti i pesi dimensione
    for dim_key in DIMENSION_LABELS.keys():
        current_val = dim_weights.get(dim_key, 0.20)
        init_weight_state(f"dim_weight_{dim_key}", int(current_val * 100))

    new_dim_weights = {}

    for i, (dim_key, dim_label) in enumerate(DIMENSION_LABELS.items()):
        slider_key = f"dim_slider_{dim_key}"
        num_key = f"dim_num_{dim_key}"
        state_key = f"dim_weight_{dim_key}"

        col_label, col_slider, col_num = st.columns([2, 4, 1])

        with col_label:
            st.markdown(f"**{dim_label}**")

        with col_slider:
            st.slider(
                dim_label,
                min_value=0,
                max_value=100,
                value=st.session_state[state_key],
                step=5,
                key=slider_key,
                on_change=sync_slider_to_num,
                args=(slider_key, state_key),
                label_visibility="collapsed"
            )

        with col_num:
            st.number_input(
                "%",
                min_value=0,
                max_value=100,
                value=st.session_state[state_key],
                step=1,
                key=num_key,
                on_change=sync_num_to_slider,
                args=(num_key, state_key),
                label_visibility="collapsed"
            )

        # Usa il valore dallo state (sincronizzato)
        new_dim_weights[dim_key] = st.session_state[state_key] / 100.0

    # Mostra somma
    total = sum(new_dim_weights.values())
    if abs(total - 1.0) < 0.01:
        st.success(f"✅ Somma: {total*100:.0f}%")
    else:
        st.error(f"❌ Somma: {total*100:.0f}% (deve essere 100%)")

    col_save, col_norm, col_reset = st.columns(3)

    with col_save:
        if st.button("💾 Salva Pesi Dimensioni", type="primary", key="save_dims"):
            is_valid, msg = validate_weights(new_dim_weights)
            if is_valid:
                config["dimension_weights"] = new_dim_weights
                if save_weights_config(config):
                    st.success("✅ Pesi dimensioni salvati con successo!")
                    st.rerun()
                else:
                    st.error("❌ Errore durante il salvataggio")
            else:
                st.error(f"❌ {msg}")

    with col_norm:
        if st.button("🔄 Normalizza", key="norm_dims"):
            normalized = normalize_weights(new_dim_weights)
            config["dimension_weights"] = normalized
            if save_weights_config(config):
                # Aggiorna session_state con i nuovi valori normalizzati
                for dim_key, val in normalized.items():
                    st.session_state[f"dim_weight_{dim_key}"] = int(val * 100)
                st.success("✅ Pesi normalizzati e salvati!")
                st.rerun()

    with col_reset:
        if st.button("↩️ Reset Uguali", key="reset_dims"):
            default_weights = get_default_config()["dimension_weights"]
            config["dimension_weights"] = default_weights
            if save_weights_config(config):
                # Aggiorna session_state con i valori default
                for dim_key, val in default_weights.items():
                    st.session_state[f"dim_weight_{dim_key}"] = int(val * 100)
                st.success("✅ Pesi resettati a valori uguali!")
                st.rerun()

# ===============================
# TAB 2: Pesi Indicatori
# ===============================
with tab_indicators:
    st.subheader("Pesi degli Indicatori per Dimensione")
    st.markdown("""
    Per ogni dimensione, configura quanto ogni singolo indicatore contribuisce
    alla media della dimensione. La somma per ogni dimensione deve essere **100%**.
    """)

    selected_dim = st.selectbox(
        "Seleziona Dimensione",
        options=list(DIMENSION_LABELS.keys()),
        format_func=lambda x: DIMENSION_LABELS[x],
        key="select_dim_for_indicators"
    )

    if selected_dim:
        st.markdown(f"### {DIMENSION_LABELS[selected_dim]}")

        ind_weights = config.get("indicator_weights", {}).get(selected_dim, {})
        ind_labels = INDICATOR_LABELS.get(selected_dim, {})

        # Inizializza session_state per tutti i pesi indicatore della dimensione selezionata
        n_indicators = len(ind_labels)
        for ind_key in ind_labels.keys():
            default_weight = 1.0 / n_indicators
            current_val = ind_weights.get(ind_key, default_weight)
            init_weight_state(f"ind_weight_{selected_dim}_{ind_key}", int(current_val * 100))

        new_ind_weights = {}

        for ind_key, ind_label in ind_labels.items():
            slider_key = f"ind_slider_{selected_dim}_{ind_key}"
            num_key = f"ind_num_{selected_dim}_{ind_key}"
            state_key = f"ind_weight_{selected_dim}_{ind_key}"

            col_label, col_slider, col_num = st.columns([2, 4, 1])

            with col_label:
                st.markdown(f"**{ind_label}**")

            with col_slider:
                st.slider(
                    ind_label,
                    min_value=0,
                    max_value=100,
                    value=st.session_state[state_key],
                    step=5,
                    key=slider_key,
                    on_change=sync_slider_to_num,
                    args=(slider_key, state_key),
                    label_visibility="collapsed"
                )

            with col_num:
                st.number_input(
                    "%",
                    min_value=0,
                    max_value=100,
                    value=st.session_state[state_key],
                    step=1,
                    key=num_key,
                    on_change=sync_num_to_slider,
                    args=(num_key, state_key),
                    label_visibility="collapsed"
                )

            # Usa il valore dallo state (sincronizzato)
            new_ind_weights[ind_key] = st.session_state[state_key] / 100.0

        total_ind = sum(new_ind_weights.values())
        if abs(total_ind - 1.0) < 0.01:
            st.success(f"✅ Somma: {total_ind*100:.0f}%")
        else:
            st.error(f"❌ Somma: {total_ind*100:.0f}% (deve essere 100%)")

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("💾 Salva", type="primary", key=f"save_ind_{selected_dim}"):
                is_valid, msg = validate_weights(new_ind_weights)
                if is_valid:
                    if "indicator_weights" not in config:
                        config["indicator_weights"] = {}
                    config["indicator_weights"][selected_dim] = new_ind_weights
                    if save_weights_config(config):
                        st.success(f"✅ Pesi indicatori {DIMENSION_LABELS[selected_dim]} salvati!")
                        st.rerun()
                else:
                    st.error(f"❌ {msg}")

        with col2:
            if st.button("🔄 Normalizza", key=f"norm_ind_{selected_dim}"):
                normalized = normalize_weights(new_ind_weights)
                if "indicator_weights" not in config:
                    config["indicator_weights"] = {}
                config["indicator_weights"][selected_dim] = normalized
                if save_weights_config(config):
                    # Aggiorna session_state con i nuovi valori normalizzati
                    for ind_key, val in normalized.items():
                        st.session_state[f"ind_weight_{selected_dim}_{ind_key}"] = int(val * 100)
                    st.success("✅ Pesi normalizzati e salvati!")
                    st.rerun()

        with col3:
            if st.button("↩️ Reset", key=f"reset_ind_{selected_dim}"):
                default_ind = get_default_config()["indicator_weights"].get(selected_dim, {})
                if "indicator_weights" not in config:
                    config["indicator_weights"] = {}
                config["indicator_weights"][selected_dim] = default_ind
                if save_weights_config(config):
                    # Aggiorna session_state con i valori default
                    for ind_key, val in default_ind.items():
                        st.session_state[f"ind_weight_{selected_dim}_{ind_key}"] = int(val * 100)
                    st.success("✅ Pesi indicatori resettati!")
                    st.rerun()

# ===============================
# TAB 3: Preset
# ===============================
with tab_presets:
    st.subheader("Gestione Preset")
    st.markdown("Carica configurazioni predefinite o salva la configurazione attuale come nuovo preset.")

    presets = config.get("presets", {})

    col_load, col_save_preset = st.columns(2)

    with col_load:
        st.markdown("### Carica Preset")
        if presets:
            preset_options = {k: v.get("name", k) for k, v in presets.items()}
            selected_preset = st.selectbox(
                "Seleziona Preset",
                options=list(preset_options.keys()),
                format_func=lambda x: preset_options[x],
                key="select_preset"
            )

            if selected_preset and selected_preset in presets:
                preset_info = presets[selected_preset]
                st.info(f"📝 {preset_info.get('description', 'Nessuna descrizione')}")

                col_apply, col_delete = st.columns(2)
                with col_apply:
                    if st.button("📥 Applica Preset", type="primary", key="apply_preset"):
                        if "dimension_weights" in preset_info:
                            config["dimension_weights"] = preset_info["dimension_weights"].copy()
                            # Aggiorna session_state per le dimensioni
                            for dim_key, val in preset_info["dimension_weights"].items():
                                st.session_state[f"dim_weight_{dim_key}"] = int(val * 100)
                        if "indicator_weights" in preset_info:
                            config["indicator_weights"] = preset_info["indicator_weights"].copy()
                            # Aggiorna session_state per tutti gli indicatori
                            for dim_key, ind_weights in preset_info["indicator_weights"].items():
                                for ind_key, val in ind_weights.items():
                                    st.session_state[f"ind_weight_{dim_key}_{ind_key}"] = int(val * 100)
                        if save_weights_config(config):
                            st.success(f"✅ Preset '{preset_options[selected_preset]}' applicato!")
                            st.rerun()

                with col_delete:
                    # Non permettere eliminazione preset default
                    if selected_preset not in ["equal", "didattica_focus", "transizioni"]:
                        if st.button("🗑️ Elimina", key="delete_preset"):
                            if delete_preset(selected_preset):
                                st.success("✅ Preset eliminato!")
                                st.rerun()
        else:
            st.info("Nessun preset disponibile")

    with col_save_preset:
        st.markdown("### Salva Nuovo Preset")
        with st.form("form_new_preset"):
            preset_id = st.text_input(
                "ID Preset (es: custom_2026)",
                max_chars=50,
                help="Identificativo univoco senza spazi"
            )
            preset_name = st.text_input("Nome Preset", help="Nome visualizzato")
            preset_desc = st.text_area("Descrizione", max_chars=200)

            if st.form_submit_button("💾 Salva come Preset"):
                if preset_id and preset_name:
                    # Rimuovi spazi dall'ID
                    preset_id = preset_id.replace(" ", "_").lower()
                    if save_as_preset(preset_id, preset_name, preset_desc):
                        st.success(f"✅ Preset '{preset_name}' salvato!")
                        st.rerun()
                    else:
                        st.error("❌ Errore durante il salvataggio")
                else:
                    st.error("Compila ID e Nome del preset")

# ===============================
# TAB 4: Anteprima
# ===============================
with tab_preview:
    st.subheader("Anteprima Configurazione Attuale")

    # Riepilogo visuale - Grafico pesi dimensioni
    st.markdown("### Distribuzione Pesi Dimensioni")

    dim_weights = config.get("dimension_weights", {})
    df_dims = pd.DataFrame([
        {"Dimensione": DIMENSION_LABELS.get(k, k), "Peso (%)": v*100}
        for k, v in dim_weights.items()
    ])

    fig = px.bar(
        df_dims,
        x="Dimensione",
        y="Peso (%)",
        title="Distribuzione Pesi Dimensioni",
        color="Dimensione",
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    fig.update_layout(showlegend=False, yaxis_title="Peso (%)")
    fig.add_hline(y=20, line_dash="dash", line_color="gray",
                  annotation_text="Media (20%)")
    st.plotly_chart(fig, use_container_width=True)

    # Tabella riepilogativa completa
    st.markdown("### Riepilogo Completo Pesi")

    summary_data = get_weight_summary()
    df_summary = pd.DataFrame(summary_data)

    # Rinomina colonne per visualizzazione
    df_display = df_summary[[
        "dimensione", "indicatore", "peso_dimensione", "peso_indicatore", "peso_effettivo"
    ]].copy()
    df_display.columns = ["Dimensione", "Indicatore", "Peso Dim", "Peso Ind", "Peso Effettivo"]

    # Formatta come percentuali
    df_display["Peso Dim"] = df_display["Peso Dim"].apply(lambda x: f"{x*100:.0f}%")
    df_display["Peso Ind"] = df_display["Peso Ind"].apply(lambda x: f"{x*100:.0f}%")
    df_display["Peso Effettivo"] = df_display["Peso Effettivo"].apply(lambda x: f"{x*100:.2f}%")

    st.dataframe(df_display, use_container_width=True, hide_index=True)

    # Verifica totale pesi effettivi
    total_effective = sum(item["peso_effettivo"] for item in summary_data)
    st.markdown(f"**Somma pesi effettivi:** {total_effective*100:.2f}%")

    # Info ultima modifica
    st.markdown("---")
    st.caption(f"Ultima modifica: {config.get('last_modified', 'N/D')} - da: {config.get('modified_by', 'N/D')}")

    # Export JSON
    with st.expander("📤 Esporta/Importa Configurazione"):
        st.markdown("**Configurazione JSON corrente:**")
        import json
        st.code(json.dumps(config, indent=2, ensure_ascii=False), language="json")

        st.download_button(
            "⬇️ Scarica JSON",
            data=json.dumps(config, indent=2, ensure_ascii=False),
            file_name="weights_config.json",
            mime="application/json"
        )

render_footer()
