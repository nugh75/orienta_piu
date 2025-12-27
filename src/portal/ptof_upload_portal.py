#!/usr/bin/env python3
"""
PTOF Upload Portal (Streamlit).
Receives PTOF PDFs and stores them locally.
Supports both local mode and Streamlit Cloud with secrets.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
TOKENS_FILE = DATA_DIR / "ptof_upload_tokens.json"
PTOF_INBOX_DIR = BASE_DIR / "ptof_inbox"
PTOF_INBOX_BACKUP_DIR = BASE_DIR / "ptof_inbox_backup"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def relative_path(path: Path) -> str:
    try:
        return str(path.relative_to(BASE_DIR))
    except ValueError:
        return str(path)


def save_ptof_file(data: bytes, filename: str) -> Optional[Path]:
    """Save PTOF PDF locally. Returns the saved path or None on failure."""
    try:
        ensure_dir(PTOF_INBOX_DIR)
        target_path = PTOF_INBOX_DIR / filename

        if target_path.exists():
            ensure_dir(PTOF_INBOX_BACKUP_DIR)
            stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{target_path.stem}_{stamp}{target_path.suffix}"
            target_path.replace(PTOF_INBOX_BACKUP_DIR / backup_name)

        target_path.write_bytes(data)
        return target_path
    except Exception as e:
        st.error(f"Errore salvataggio file: {e}")
        return None


def load_tokens() -> Dict:
    """Load tokens from local file or Streamlit secrets."""
    # Try Streamlit secrets first
    try:
        if hasattr(st, 'secrets') and 'ptof_tokens' in st.secrets:
            data = dict(st.secrets['ptof_tokens'])
            data.setdefault("by_token", {})
            data.setdefault("by_code", {})
            return data
    except Exception:
        pass

    # Fallback to local file
    if TOKENS_FILE.exists():
        try:
            data = json.loads(TOKENS_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    else:
        data = {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault("by_token", {})
    data.setdefault("by_code", {})
    return data


def save_tokens(data: Dict) -> None:
    """Save tokens to local file (only works in local mode)."""
    try:
        TOKENS_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = TOKENS_FILE.with_suffix(TOKENS_FILE.suffix + ".tmp")
        tmp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp_path.replace(TOKENS_FILE)
    except Exception:
        # In cloud mode, we can't write to filesystem
        pass


def get_query_param(name: str) -> str:
    if hasattr(st, "query_params"):
        value = st.query_params.get(name, "")
        if isinstance(value, list):
            value = value[0] if value else ""
        return str(value).strip()
    params = st.experimental_get_query_params()
    value = params.get(name, [""])
    return value[0].strip() if value else ""


def sanitize_code(code: str) -> str:
    code = (code or "").strip().upper()
    return "".join(ch for ch in code if ch.isalnum())


def update_token_entry(tokens: Dict, token: str, upload_name: str, size: int, stored_path: str) -> None:
    entry = tokens["by_token"].get(token, {})
    entry.setdefault("uploads", [])
    now = datetime.utcnow().isoformat()
    entry["used_at"] = now
    entry["uploads"].append(
        {
            "uploaded_at": now,
            "source_name": upload_name,
            "stored_path": stored_path,
            "size": size,
        }
    )
    tokens["by_token"][token] = entry
    save_tokens(tokens)


def render_school_info(entry: Dict, school_code: str) -> None:
    name = entry.get("denominazione") or ""
    comune = entry.get("comune") or ""
    st.markdown(f"**Scuola:** {name} ({school_code})")
    if comune:
        st.markdown(f"**Comune:** {comune}")


def main() -> None:
    st.set_page_config(page_title="PTOF Upload", layout="centered")
    st.title("Caricamento PTOF")
    st.write("Carica il PTOF in PDF usando il link ricevuto via email.")

    ensure_dir(PTOF_INBOX_DIR)

    tokens = load_tokens()
    token = get_query_param("token")
    if not token:
        st.error("Link non valido. Usa il link ricevuto via email.")
        return

    entry = tokens.get("by_token", {}).get(token)
    if not entry:
        st.error("Token non valido o scaduto.")
        return

    school_code = sanitize_code(entry.get("school_code", ""))
    if not school_code:
        st.error("Token non valido.")
        return

    render_school_info(entry, school_code)

    st.markdown("---")

    uploaded = st.file_uploader("Seleziona il file PTOF (PDF)", type=["pdf"])
    submit = st.button("Carica PTOF", type="primary")

    if not submit:
        return

    if not uploaded:
        st.error("Seleziona un file PDF.")
        return

    data = uploaded.getbuffer()
    if not data:
        st.error("File vuoto.")
        return

    if not bytes(data[:4]) == b"%PDF":
        st.error("Il file non sembra un PDF valido.")
        return

    with st.spinner("Caricamento in corso..."):
        filename = f"{school_code}_PTOF.pdf"
        stored_path = save_ptof_file(bytes(data), filename)

    if stored_path:
        update_token_entry(tokens, token, uploaded.name, len(data), relative_path(stored_path))
        st.success("Caricamento completato con successo! Grazie per aver inviato il PTOF.")
        st.balloons()
    else:
        st.error("Errore durante il caricamento. Riprova o contattaci.")


if __name__ == "__main__":
    main()
