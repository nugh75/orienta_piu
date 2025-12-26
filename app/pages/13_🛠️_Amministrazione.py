# Amministrazione - Gestione pagine e accessi

import streamlit as st

from page_control import get_page_settings, save_page_settings, setup_page

st.set_page_config(page_title="ORIENTA+ | Amministrazione", page_icon="🧭", layout="wide")
setup_page("pages/13_🛠️_Amministrazione.py")

st.title("Amministrazione Pagine")
st.markdown(
    "Gestisci quali pagine sono visibili, quali richiedono la password e quale pagina è la predefinita."
)
st.caption("Password per pagine protette: Lagom192")

settings = get_page_settings()
pages = settings.get("pages", {})

sorted_pages = sorted(pages.items(), key=lambda item: item[1].get("order", 999))

if st.button("Revoca accesso sbloccato", use_container_width=True):
    st.session_state.pop("page_access_granted", None)
    st.success("Accesso revocato per questa sessione.")

st.markdown("---")

with st.form("page_settings_form"):
    st.subheader("Pagine")
    updated_pages = {}

    for page_id, cfg in sorted_pages:
        cols = st.columns([3, 2, 1, 1])
        cols[0].markdown(f"`{page_id}`")
        label = cols[1].text_input(
            "Etichetta",
            value=cfg.get("label", page_id),
            key=f"label_{page_id}",
        )
        visible_disabled = page_id.endswith("_Amministrazione.py")
        visible = cols[2].checkbox(
            "Visibile",
            value=cfg.get("visible", True),
            key=f"visible_{page_id}",
            disabled=visible_disabled,
        )
        locked = cols[3].checkbox(
            "Protetta",
            value=cfg.get("locked", False),
            key=f"locked_{page_id}",
        )

        updated_pages[page_id] = {
            "label": label,
            "visible": visible if not visible_disabled else True,
            "locked": locked,
            "order": cfg.get("order", 999),
        }

    page_options = [page_id for page_id, _ in sorted_pages]
    default_page = st.selectbox(
        "Pagina iniziale",
        options=page_options,
        index=page_options.index(settings.get("default_page", "Home.py"))
        if settings.get("default_page", "Home.py") in page_options
        else 0,
        format_func=lambda pid: updated_pages.get(pid, {}).get("label", pid),
    )

    if st.form_submit_button("Salva configurazione"):
        new_settings = {
            "default_page": default_page,
            "pages": updated_pages,
        }
        save_page_settings(new_settings)
        st.success("Configurazione salvata con successo.")
