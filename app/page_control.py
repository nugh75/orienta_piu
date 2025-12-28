import hmac
import json
import os
import re
import sys
import time
from hashlib import sha256
from pathlib import Path
from typing import Dict, List, Optional

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Load .env from project root
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except Exception:
    pass

PAGE_SETTINGS_PATH = Path("config/page_settings.json")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")
ADMIN_TOKEN_PARAM = "admin_token"
ADMIN_SESSION_TTL_SECONDS = int(os.getenv("ADMIN_SESSION_TTL_SECONDS", "43200"))
ADMIN_TOKEN_SECRET = os.getenv("ADMIN_TOKEN_SECRET") or ADMIN_PASSWORD


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
    st.session_state.pop("admin_login_at", None)
    st.session_state.pop("admin_token", None)
    _remove_query_param(ADMIN_TOKEN_PARAM)


def _normalize_query_value(value: object) -> object:
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value if v is not None]
    if value is None:
        return ""
    return str(value)


def _get_query_params() -> Dict[str, object]:
    try:
        params = dict(st.query_params)
    except Exception:
        params = st.experimental_get_query_params()
    result = {}
    for key, value in params.items():
        if key == "page":
            continue
        result[key] = _normalize_query_value(value)
    return result


def _set_query_params(params: Dict[str, object]) -> None:
    try:
        st.query_params.clear()
        for key, value in params.items():
            st.query_params[key] = value
    except Exception:
        st.experimental_set_query_params(**params)


def _set_query_param(key: str, value: str) -> None:
    params = _get_query_params()
    params[key] = value
    _set_query_params(params)


def _remove_query_param(key: str) -> None:
    params = _get_query_params()
    if key in params:
        params.pop(key, None)
        _set_query_params(params)


def _get_query_param(key: str) -> str:
    params = _get_query_params()
    value = params.get(key, "")
    if isinstance(value, list):
        return value[0] if value else ""
    return str(value or "")


def _sign_admin_token(ts: int) -> str:
    payload = str(ts).encode("utf-8")
    sig = hmac.new(ADMIN_TOKEN_SECRET.encode("utf-8"), payload, sha256).hexdigest()
    return f"{ts}:{sig}"


def _parse_admin_token(token: str) -> Optional[int]:
    try:
        ts_str, sig = token.split(":", 1)
        ts = int(ts_str)
    except Exception:
        return None
    expected = hmac.new(ADMIN_TOKEN_SECRET.encode("utf-8"), ts_str.encode("utf-8"), sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    if time.time() - ts > ADMIN_SESSION_TTL_SECONDS:
        return None
    return ts


def _remember_admin_login() -> None:
    now = int(time.time())
    token = st.session_state.get("admin_token")
    login_at = st.session_state.get("admin_login_at")
    if token and login_at and (time.time() - login_at) <= ADMIN_SESSION_TTL_SECONDS:
        if _get_query_param(ADMIN_TOKEN_PARAM) != token:
            _set_query_param(ADMIN_TOKEN_PARAM, token)
        return
    token = _sign_admin_token(now)
    st.session_state["admin_logged_in"] = True
    st.session_state["admin_login_at"] = now
    st.session_state["admin_token"] = token
    if _get_query_param(ADMIN_TOKEN_PARAM) != token:
        _set_query_param(ADMIN_TOKEN_PARAM, token)


def _restore_admin_login() -> None:
    if is_admin_logged_in():
        login_at = st.session_state.get("admin_login_at", 0)
        if login_at and (time.time() - login_at) <= ADMIN_SESSION_TTL_SECONDS:
            return
        admin_logout()
        return
    token = _get_query_param(ADMIN_TOKEN_PARAM)
    if not token:
        return
    ts = _parse_admin_token(token)
    if not ts:
        _remove_query_param(ADMIN_TOKEN_PARAM)
        return
    st.session_state["admin_logged_in"] = True
    st.session_state["admin_login_at"] = ts
    st.session_state["admin_token"] = token


def get_page_settings() -> Dict:
    settings = load_page_settings()
    discovered = discover_pages()
    pages_config = settings.get("pages", {})
    sections = settings.get("sections", [])

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
            "section": cfg.get("section", "other"),
        }

    default_page = settings.get("default_page", "Home.py")
    if default_page not in merged:
        default_page = "Home.py"

    return {
        "default_page": default_page,
        "sections": sections,
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
        # Pulsante verde tenue con testo nero per pagina corrente
        st.sidebar.markdown(
            f"""
            <div style="
                background-color: #d4edda;
                border: 1px solid #c3e6cb;
                border-radius: 0.5rem;
                padding: 0.5rem 1rem;
                margin: 0.25rem 0;
                text-align: center;
                color: #1a1a1a;
                font-weight: 500;
            ">▸ {display}</div>
            """,
            unsafe_allow_html=True
        )
        return

    if st.sidebar.button(display, key=f"nav_{page_id}", use_container_width=True):
        st.switch_page(page_id, query_params=_get_query_params())


def switch_page(page_id: str) -> None:
    """Switch page while preserving query params."""
    st.switch_page(page_id, query_params=_get_query_params())


def render_sidebar_nav(current_page: str, settings: Dict) -> None:
    st.sidebar.markdown("### Navigazione")
    pages = settings.get("pages", {})
    sections = settings.get("sections", [])
    admin_logged = is_admin_logged_in()

    # Crea mappa sezioni per ordine
    section_order = {s["id"]: i for i, s in enumerate(sections)}
    section_labels = {s["id"]: s["label"] for s in sections}

    # Filtra pagine: visibili a tutti + invisibili solo se admin
    visible_pages = []
    for pid, cfg in pages.items():
        is_visible = cfg.get("visible", True)
        if is_visible:
            visible_pages.append((pid, cfg, False))  # False = non admin-only
        elif admin_logged:
            visible_pages.append((pid, cfg, True))   # True = admin-only (mostrata perche' admin)

    # Ordina per sezione, poi per order interno
    def sort_key(item):
        pid, cfg, admin_only = item
        section = cfg.get("section", "other")
        sec_ord = section_order.get(section, 999)
        page_ord = cfg.get("order", 999)
        return (sec_ord, page_ord)

    visible_pages.sort(key=sort_key)

    # Raggruppa per sezione e renderizza
    current_section = None
    for page_id, cfg, admin_only in visible_pages:
        section = cfg.get("section", "other")

        # Se cambia sezione, mostra intestazione
        if section != current_section:
            current_section = section
            section_label = section_labels.get(section, "")
            if section_label:  # Non mostrare intestazione vuota (es. per Home)
                st.sidebar.markdown("---")
                st.sidebar.markdown(f"**{section_label}**")

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
                _remember_admin_login()
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
    _restore_admin_login()
    settings = get_page_settings()
    enforce_page_access(page_id, settings)
    if show_nav:
        render_sidebar_nav(page_id, settings)
        render_admin_login_sidebar()
    return settings
