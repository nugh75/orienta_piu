#!/usr/bin/env python3
"""
PTOF Upload Portal (Streamlit).
Receives PTOF PDFs and drops them into ptof_inbox.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
TOKENS_FILE = DATA_DIR / "ptof_upload_tokens.json"
INBOX_DIR = BASE_DIR / "ptof_inbox"
BACKUP_DIR = BASE_DIR / "ptof_inbox_backup"


def load_tokens() -> Dict:
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
    TOKENS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = TOKENS_FILE.with_suffix(TOKENS_FILE.suffix + ".tmp")
    tmp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp_path.replace(TOKENS_FILE)


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


def backup_existing(path: Path) -> Optional[Path]:
    if not path.exists():
        return None
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"{path.stem}_{stamp}{path.suffix}"
    path.replace(backup_path)
    return backup_path


def save_upload(data: bytes, school_code: str) -> Tuple[Path, Optional[Path]]:
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    dest_path = INBOX_DIR / f"{school_code}_PTOF.pdf"
    backup_path = backup_existing(dest_path)
    dest_path.write_bytes(data)
    return dest_path, backup_path


def update_token_entry(tokens: Dict, token: str, upload_name: str, size: int, dest_path: Path) -> None:
    entry = tokens["by_token"].get(token, {})
    entry.setdefault("uploads", [])
    now = datetime.utcnow().isoformat()
    entry["used_at"] = now
    entry["uploads"].append(
        {
            "uploaded_at": now,
            "source_name": upload_name,
            "stored_path": str(dest_path),
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
    st.title("PTOF Upload")
    st.write("Carica il PTOF in PDF usando il link ricevuto via email.")

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

    uploaded = st.file_uploader("PTOF (PDF)", type=["pdf"])
    submit = st.button("Carica")
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

    dest_path, backup_path = save_upload(data, school_code)
    update_token_entry(tokens, token, uploaded.name, len(data), dest_path)

    st.success("Caricamento completato. Grazie.")
    if backup_path:
        st.info("Un file precedente era gia presente ed e stato archiviato.")


if __name__ == "__main__":
    main()

