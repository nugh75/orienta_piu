import json
import re
import sys
from pathlib import Path
from typing import Dict, List

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

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


def is_admin_logged_in() -> bool:
    """Check if admin is currently logged in."""
    return st.session_state.get("admin_logged_in", False)


def admin_login() -> bool:
    """Handle admin login. Returns True if logged in."""
    if is_admin_logged_in():
        return True
    return False


def admin_logout() -> None:
    """Logout admin."""
    st.session_state.pop("admin_logged_in", None)


def get_page_settings() -> Dict:
    settings = load_page_settings()
    discovered = discover_pages()
    pages_config = settings.get("pages", {})

    merged = {}
    for page in discovered:
        page_id = page["id"]
        cfg = pages_config.get(page_id, {})
        visible = cfg.get("visible", True)

        # Amministrazione sempre visibile
        if page_id.endswith("_Amministrazione.py"):
            visible = True

        merged[page_id] = {
            "label": cfg.get("label", page["label"]),
            "visible": visible,
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


def _render_nav_button(label: str, page_id: str, current_page: str, admin_only: bool = False) -> None:
    display = label
    if admin_only:
        display = f"{label} (admin)"
    if page_id == current_page:
        st.sidebar.markdown(f"**{display}**")
        return

    if st.sidebar.button(display, key=f"nav_{page_id}", use_container_width=True):
        st.switch_page(page_id)


def render_sidebar_nav(current_page: str, settings: Dict) -> None:
    st.sidebar.markdown("### Navigazione")
    pages = settings.get("pages", {})
    admin_logged = is_admin_logged_in()

    # Filtra pagine: visibili a tutti + invisibili solo se admin
    visible_pages = []
    for pid, cfg in pages.items():
        is_visible = cfg.get("visible", True)
        if is_visible:
            visible_pages.append((pid, cfg, False))  # False = non admin-only
        elif admin_logged:
            visible_pages.append((pid, cfg, True))   # True = admin-only (mostrata perche' admin)

    visible_pages.sort(key=lambda item: item[1].get("order", 999))

    for page_id, cfg, admin_only in visible_pages:
        _render_nav_button(cfg.get("label", page_id), page_id, current_page, admin_only)

    # Mostra stato admin
    if admin_logged:
        st.sidebar.markdown("---")
        st.sidebar.success("Admin connesso")


def render_admin_login_sidebar() -> None:
    """Render admin login form in sidebar."""
    if is_admin_logged_in():
        if st.sidebar.button("Logout Admin", use_container_width=True):
            admin_logout()
            st.rerun()
    else:
        st.sidebar.markdown("---")
        st.sidebar.markdown("**Login Admin**")
        password = st.sidebar.text_input("Password", type="password", key="admin_pwd")
        if st.sidebar.button("Accedi", use_container_width=True):
            if password == ADMIN_PASSWORD:
                st.session_state["admin_logged_in"] = True
                st.rerun()
            else:
                st.sidebar.error("Password errata")


def enforce_page_access(page_id: str, settings: Dict) -> None:
    """Enforce page access. Invisible pages require admin login."""
    cfg = settings.get("pages", {}).get(page_id, {})
    is_visible = cfg.get("visible", True)

    # Se la pagina non e' visibile, solo admin puo' accedere
    if not is_visible and not is_admin_logged_in():
        st.warning("Questa pagina e' riservata all'amministratore.")
        st.info("Effettua il login come admin dalla sidebar per accedere.")
        st.stop()


def setup_page(page_id: str, show_nav: bool = True) -> Dict:
    hide_streamlit_nav()
    settings = get_page_settings()
    enforce_page_access(page_id, settings)
    if show_nav:
        render_sidebar_nav(page_id, settings)
        render_admin_login_sidebar()
    return settings
