#!/usr/bin/env python3
"""
Pagina admin per gestire le richieste di revisione analisi PTOF.
"""

import json
from datetime import datetime
from pathlib import Path
import streamlit as st
import pandas as pd

from page_control import setup_page

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
REVISION_REQUESTS_FILE = DATA_DIR / "revision_requests.json"
ANALYSIS_SUMMARY_CSV = DATA_DIR / "analysis_summary.csv"


def load_revision_requests() -> list:
    """Load all revision requests."""
    if not REVISION_REQUESTS_FILE.exists():
        return []
    try:
        return json.loads(REVISION_REQUESTS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_revision_requests(requests: list) -> None:
    """Save revision requests to file."""
    REVISION_REQUESTS_FILE.write_text(
        json.dumps(requests, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def update_request_status(codice: str, submitted_at: str, new_status: str, note: str = None) -> bool:
    """Update the status of a revision request."""
    requests = load_revision_requests()
    codice_upper = codice.strip().upper()

    for req in requests:
        if (req.get("codice_meccanografico", "").upper() == codice_upper and
            req.get("submitted_at") == submitted_at):
            req["stato"] = new_status
            if note:
                req["note_admin"] = note
            if new_status in ["completed", "rejected"]:
                req["completed_at"] = datetime.now().isoformat()
            save_revision_requests(requests)
            return True
    return False


def format_date(iso_date: str) -> str:
    """Format ISO date to Italian format."""
    try:
        dt = datetime.fromisoformat(iso_date)
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return iso_date or "N/D"


def main():
    st.set_page_config(
        page_title="Gestione Revisioni",
        page_icon="📋",
        layout="wide"
    )

    # Setup page with admin protection
    setup_page("pages/18_📋_Gestione_Revisioni.py")

    st.title("📋 Gestione Richieste di Revisione")
    st.write("Gestisci le richieste di revisione delle analisi PTOF.")

    requests = load_revision_requests()

    if not requests:
        st.info("Nessuna richiesta di revisione ricevuta.")
        return

    # Stats
    stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)
    statuses = [r.get("stato", "pending") for r in requests]

    with stats_col1:
        st.metric("Totale", len(requests))
    with stats_col2:
        st.metric("In Attesa", statuses.count("pending"))
    with stats_col3:
        st.metric("In Revisione", statuses.count("in_review"))
    with stats_col4:
        completed = statuses.count("completed") + statuses.count("rejected")
        st.metric("Completate", completed)

    st.markdown("---")

    # Filters
    col_filter1, col_filter2 = st.columns([2, 2])

    with col_filter1:
        status_filter = st.selectbox(
            "Filtra per stato",
            options=["Tutti", "pending", "in_review", "completed", "rejected"]
        )

    with col_filter2:
        search_code = st.text_input("Cerca codice", placeholder="RMIC...")

    # Filter requests
    filtered = []
    for req in requests:
        stato = req.get("stato", "pending")

        if status_filter != "Tutti" and stato != status_filter:
            continue

        codice = req.get("codice_meccanografico", "")
        if search_code and search_code.upper() not in codice.upper():
            continue

        filtered.append(req)

    # Sort by date (newest first)
    filtered.sort(key=lambda x: x.get("submitted_at", ""), reverse=True)

    st.markdown("---")
    st.subheader(f"Richieste ({len(filtered)} risultati)")

    if not filtered:
        st.warning("Nessuna richiesta corrisponde ai filtri.")
        return

    for i, req in enumerate(filtered):
        codice = req.get("codice_meccanografico", "N/D")
        denominazione = req.get("denominazione", "N/D")
        stato = req.get("stato", "pending")
        submitted_at = req.get("submitted_at", "")

        # Status color and icon
        status_map = {
            "pending": ("🟡", "orange", "In Attesa"),
            "in_review": ("🔵", "blue", "In Revisione"),
            "completed": ("🟢", "green", "Completata"),
            "rejected": ("🔴", "red", "Respinta")
        }
        icon, color, label = status_map.get(stato, ("⚪", "gray", stato))

        with st.expander(
            f"{icon} **{codice}** - {denominazione} | :{color}[{label}] | {format_date(submitted_at)[:10]}",
            expanded=(stato == "pending")
        ):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown("**Dettagli Richiesta**")
                st.write(f"**Codice:** {codice}")
                st.write(f"**Scuola:** {denominazione}")
                st.write(f"**Email:** {req.get('email_contatto', 'N/D')}")
                st.write(f"**Data richiesta:** {format_date(submitted_at)}")
                st.write(f"**Motivo:** {req.get('motivo', 'N/D')}")

                st.markdown("**Descrizione:**")
                st.text_area(
                    "Dettagli forniti",
                    value=req.get("dettagli", ""),
                    height=100,
                    disabled=True,
                    key=f"details_{i}",
                    label_visibility="collapsed"
                )

                if req.get("note_admin"):
                    st.markdown("**Note admin:**")
                    st.info(req.get("note_admin"))

                if req.get("completed_at"):
                    st.caption(f"Completata il: {format_date(req.get('completed_at'))}")

            with col2:
                st.markdown("**Azioni**")

                # Link to school detail
                st.page_link(
                    "pages/02_🏫_Dettaglio_Scuola.py",
                    label="🏫 Vedi Scuola",
                    use_container_width=True
                )

                # Status change and response
                if stato not in ["completed", "rejected"]:
                    st.markdown("---")
                    new_status = st.selectbox(
                        "Cambia stato",
                        options=["pending", "in_review", "completed", "rejected"],
                        index=["pending", "in_review", "completed", "rejected"].index(stato),
                        key=f"status_{i}"
                    )

                    st.markdown("**Messaggio di risposta**")
                    response_message = st.text_area(
                        "Scrivi una risposta alla scuola",
                        key=f"response_{i}",
                        height=120,
                        placeholder="Es: Abbiamo revisionato l'analisi e aggiunto i seguenti elementi:\n- Progetto Orientamento Futuro\n- Convenzioni universitarie\n\nI punteggi sono stati aggiornati di conseguenza.",
                        label_visibility="collapsed"
                    )

                    if st.button("Aggiorna stato", key=f"update_{i}", use_container_width=True):
                        if update_request_status(codice, submitted_at, new_status, response_message):
                            st.success("Stato aggiornato!")
                            st.rerun()
                        else:
                            st.error("Errore nell'aggiornamento")
                else:
                    st.success(f"Stato: {label}")
                    # Allow adding additional notes even after completion
                    if st.checkbox("Aggiungi nota", key=f"add_note_{i}"):
                        additional_note = st.text_area(
                            "Nota aggiuntiva",
                            key=f"additional_{i}",
                            height=80
                        )
                        if st.button("Salva nota", key=f"save_note_{i}"):
                            current_note = req.get("note_admin", "") or ""
                            new_note = f"{current_note}\n\n[{format_date(datetime.now().isoformat())}] {additional_note}" if current_note else additional_note
                            if update_request_status(codice, submitted_at, stato, new_note):
                                st.success("Nota aggiunta!")
                                st.rerun()

    # Footer
    st.markdown("---")
    st.caption("Le richieste vengono inviate dalle scuole tramite la pagina 'Richiedi Revisione'")


if __name__ == "__main__":
    main()
