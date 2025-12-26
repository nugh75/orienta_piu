import json
import re
from pathlib import Path
from typing import Dict, List

import streamlit as st

PAGE_SETTINGS_PATH = Path("config/page_settings.json")
ADMIN_PASSWORD = "Lagom192"


def _order_from_filename(name: str) -> int:
    match = re.match(r"^(\d+)_", name)
    if match:
        return int(match.group(1))
    return 999


def _label_from_stem(stem: str) -> str:
    parts = stem.split("_")
    if parts and parts[0].isdigit():
        parts = parts[1:]
    label = " ".join(parts).replace("  ", " ").strip()
    return label or stem


def discover_pages() -> List[Dict[str, str]]:
    base_dir = Path(__file__).resolve().parent
    pages_dir = base_dir / "pages"
    pages = []

    pages.append({
        "id": "Home.py",
        "label": "Home",
        "order": 0,
    })

    if pages_dir.exists():
        for path in sorted(pages_dir.glob("*.py")):
            if path.name.startswith("__"):
                continue
            pages.append({
                "id": f"pages/{path.name}",
                "label": _label_from_stem(path.stem),
                "order": _order_from_filename(path.name),
            })

    return pages


def load_page_settings() -> Dict:
    if PAGE_SETTINGS_PATH.exists():
        try:
            return json.loads(PAGE_SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {"default_page": "Home.py", "pages": {}}
    return {"default_page": "Home.py", "pages": {}}


def get_page_settings() -> Dict:
    settings = load_page_settings()
    discovered = discover_pages()
    pages_config = settings.get("pages", {})

    merged = {}
    for page in discovered:
        page_id = page["id"]
        cfg = pages_config.get(page_id, {})
        visible = cfg.get("visible", True)
        locked = cfg.get("locked", False)

        if page_id.endswith("_Amministrazione.py"):
            visible = True

        merged[page_id] = {
            "label": cfg.get("label", page["label"]),
            "visible": visible,
            "locked": locked,
            "order": cfg.get("order", page["order"]),
        }

    default_page = settings.get("default_page", "Home.py")
    if default_page not in merged:
        default_page = "Home.py"

    return {
        "default_page": default_page,
        "pages": merged,
    }


def save_page_settings(settings: Dict) -> None:
    PAGE_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    PAGE_SETTINGS_PATH.write_text(
        json.dumps(settings, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def hide_streamlit_nav() -> None:
    st.markdown(
        """
<style>
    [data-testid="stSidebarNav"] { display: none; }
</style>
""",
        unsafe_allow_html=True,
    )


def _render_nav_button(label: str, page_id: str, current_page: str, locked: bool) -> None:
    display = label
    if locked:
        display = f"{label} (locked)"
    if page_id == current_page:
        st.sidebar.markdown(f"**{display}**")
        return

    if st.sidebar.button(display, key=f"nav_{page_id}", use_container_width=True):
        st.switch_page(page_id)


def render_sidebar_nav(current_page: str, settings: Dict) -> None:
    st.sidebar.markdown("### Navigazione")
    pages = settings.get("pages", {})
    visible_pages = [
        (pid, cfg) for pid, cfg in pages.items() if cfg.get("visible", True)
    ]
    visible_pages.sort(key=lambda item: item[1].get("order", 999))

    for page_id, cfg in visible_pages:
        _render_nav_button(cfg.get("label", page_id), page_id, current_page, cfg.get("locked", False))

    if st.session_state.get("page_access_granted"):
        st.sidebar.caption("Accesso sbloccato per questa sessione")


def _require_password() -> bool:
    st.info("Pagina protetta. Inserisci la password per continuare.")
    password = st.text_input("Password", type="password", key="page_password")
    if st.button("Sblocca", use_container_width=True):
        if password == ADMIN_PASSWORD:
            st.session_state["page_access_granted"] = True
            st.success("Accesso sbloccato.")
            st.rerun()
        else:
            st.error("Password errata.")
    return False


def enforce_page_access(page_id: str, settings: Dict) -> None:
    cfg = settings.get("pages", {}).get(page_id, {})
    if not cfg.get("visible", True):
        st.warning("Questa pagina non e' attiva.")
        st.stop()

    if cfg.get("locked", False) and not st.session_state.get("page_access_granted"):
        _require_password()
        st.stop()


def setup_page(page_id: str, show_nav: bool = True) -> Dict:
    hide_streamlit_nav()
    settings = get_page_settings()
    enforce_page_access(page_id, settings)
    if show_nav:
        render_sidebar_nav(page_id, settings)
    return settings
