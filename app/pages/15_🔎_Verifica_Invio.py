#!/usr/bin/env python3
"""
Pagina per verificare lo stato di un invio PTOF.
Le scuole possono controllare a che punto è la lavorazione.
"""

import json
from datetime import datetime
from pathlib import Path
import streamlit as st
import pandas as pd

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
SPONTANEOUS_LOG = DATA_DIR / "spontaneous_uploads.json"
ANALYSIS_SUMMARY_CSV = DATA_DIR / "analysis_summary.csv"


def load_uploads() -> list:
    """Load all uploads from the log file."""
    if not SPONTANEOUS_LOG.exists():
        return []
    try:
        return json.loads(SPONTANEOUS_LOG.read_text(encoding="utf-8"))
    except Exception:
        return []


def load_analyzed_codes() -> set:
    """Load school codes that have been analyzed (from CSV)."""
    if not ANALYSIS_SUMMARY_CSV.exists():
        return set()
    try:
        df = pd.read_csv(ANALYSIS_SUMMARY_CSV)
        return set(df['school_id'].dropna().str.upper().tolist())
    except Exception:
        return set()


def check_if_analyzed(codice: str) -> bool:
    """Check if school code is in the analyzed CSV."""
    analyzed_codes = load_analyzed_codes()
    return codice.upper() in analyzed_codes


def get_upload_by_code(codice: str) -> dict | None:
    """Find upload info by school code."""
    uploads = load_uploads()
    codice_upper = codice.strip().upper()

    for upload in uploads:
        school_data = upload.get("school_data", {})
        if school_data.get("codice_meccanografico", "").upper() == codice_upper:
            return upload
    return None


def format_date(iso_date: str) -> str:
    """Format ISO date to Italian format."""
    try:
        dt = datetime.fromisoformat(iso_date)
        return dt.strftime("%d/%m/%Y alle %H:%M")
    except Exception:
        return iso_date


def get_status_display(upload: dict) -> tuple[str, str, str]:
    """Get status display info: (label, color, description)."""
    codice = upload.get("school_data", {}).get("codice_meccanografico", "")

    # Check if analyzed (overrides stored status)
    if check_if_analyzed(codice):
        return ("Lavorato", "green", "Il PTOF è stato analizzato ed è disponibile nella dashboard.")

    stato = upload.get("stato", "inviato")

    if stato == "in_lavorazione":
        return ("In Lavorazione", "orange", "Il PTOF è stato preso in carico e l'analisi è in corso.")
    else:  # inviato
        return ("Inviato", "blue", "Il PTOF è stato ricevuto ed è in attesa di essere analizzato.")


def main():
    st.set_page_config(
        page_title="Verifica Invio PTOF",
        page_icon="🔎",
        layout="centered"
    )

    st.title("🔎 Verifica Stato Invio")
    st.write("Inserisci il codice meccanografico della tua scuola per verificare lo stato del PTOF inviato.")

    st.markdown("---")

    codice = st.text_input(
        "Codice Meccanografico",
        placeholder="Es. RMIC8GA002",
        help="Il codice identificativo della scuola usato durante l'invio"
    )

    if st.button("Verifica", type="primary", use_container_width=True):
        if not codice or len(codice.strip()) < 8:
            st.error("Inserisci un codice meccanografico valido (almeno 8 caratteri)")
            return

        upload = get_upload_by_code(codice)

        if not upload:
            st.warning("Nessun invio trovato per questo codice meccanografico.")
            st.info("Se hai appena inviato il PTOF, attendi qualche minuto e riprova.")
            return

        # Display upload info
        school_data = upload.get("school_data", {})
        status_label, status_color, status_desc = get_status_display(upload)

        st.markdown("---")
        st.subheader("Stato del tuo PTOF")

        # Status badge
        st.markdown(f"### :{status_color}[{status_label}]")
        st.write(status_desc)

        st.markdown("---")

        # School info
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Scuola**")
            st.write(school_data.get("denominazione", "N/D"))

            st.markdown("**Codice**")
            st.write(school_data.get("codice_meccanografico", "N/D"))

            st.markdown("**Tipo**")
            st.write(school_data.get("tipo_scuola", "N/D"))

        with col2:
            st.markdown("**Regione**")
            st.write(school_data.get("regione", "N/D"))

            st.markdown("**Provincia**")
            st.write(school_data.get("provincia", "N/D"))

            st.markdown("**Data invio**")
            st.write(format_date(upload.get("uploaded_at", "")))

        # If analyzed, show link to dashboard
        if status_label == "Lavorato":
            st.markdown("---")
            st.success("Il PTOF della tua scuola è stato analizzato!")
            st.info("Puoi visualizzare i risultati nella pagina 'La Mia Scuola' della dashboard.")

    # Footer
    st.markdown("---")
    st.caption("Per assistenza: orienta.piu@gmail.com")


if __name__ == "__main__":
    main()
