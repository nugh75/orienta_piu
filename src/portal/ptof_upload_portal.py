#!/usr/bin/env python3
"""
PTOF Upload Portal (Streamlit).
Receives PTOF PDFs and stores them locally.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PTOF_INVIATI_DIR = BASE_DIR / "ptof_inviati"
PTOF_INVIATI_BACKUP_DIR = BASE_DIR / "ptof_inviati_backup"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def save_ptof_file(data: bytes, filename: str) -> Optional[Path]:
    """Save PTOF PDF locally. Returns the saved path or None on failure."""
    try:
        ensure_dir(PTOF_INVIATI_DIR)
        target_path = PTOF_INVIATI_DIR / filename

        if target_path.exists():
            ensure_dir(PTOF_INVIATI_BACKUP_DIR)
            stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{target_path.stem}_{stamp}{target_path.suffix}"
            target_path.replace(PTOF_INVIATI_BACKUP_DIR / backup_name)

        target_path.write_bytes(data)
        return target_path
    except Exception as e:
        st.error(f"Errore salvataggio file: {e}")
        return None


def sanitize_code(code: str) -> str:
    code = (code or "").strip().upper()
    return "".join(ch for ch in code if ch.isalnum())


def main() -> None:
    st.set_page_config(page_title="PTOF Upload", layout="centered")
    st.title("Caricamento PTOF")
    st.write("Carica il PTOF in PDF usando il link ricevuto via email.")

    ensure_dir(PTOF_INVIATI_DIR)

    with st.form("ptof_upload_form"):
        school_code = st.text_input(
            "Codice Meccanografico *",
            placeholder="Es. RMIC8GA002"
        )
        uploaded = st.file_uploader("Seleziona il file PTOF (PDF) *", type=["pdf"])
        submitted = st.form_submit_button("Carica PTOF", type="primary", use_container_width=True)

        if submitted:
            if not school_code or len(school_code.strip()) < 8:
                st.error("Codice meccanografico non valido (minimo 8 caratteri).")
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

            clean_code = sanitize_code(school_code)
            with st.spinner("Caricamento in corso..."):
                filename = f"{clean_code}_PTOF.pdf"
                stored_path = save_ptof_file(bytes(data), filename)

            if stored_path:
                st.success("Caricamento completato con successo! Grazie per aver inviato il PTOF.")
                st.balloons()
            else:
                st.error("Errore durante il caricamento. Riprova o contattaci.")


if __name__ == "__main__":
    main()
