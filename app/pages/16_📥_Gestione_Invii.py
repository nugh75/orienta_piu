#!/usr/bin/env python3
"""
Pagina admin per gestire gli invii PTOF.
Permette di visualizzare, scaricare e aggiornare lo stato degli invii.
"""

import io
import json
import zipfile
from datetime import datetime, date
from pathlib import Path
import streamlit as st
import pandas as pd

from page_control import setup_page

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
SPONTANEOUS_LOG = DATA_DIR / "spontaneous_uploads.json"
ANALYSIS_SUMMARY_CSV = DATA_DIR / "analysis_summary.csv"
PTOF_INVIATI_DIR = BASE_DIR / "ptof_inviati"


def load_uploads() -> list:
    """Load all uploads from the log file."""
    if not SPONTANEOUS_LOG.exists():
        return []
    try:
        return json.loads(SPONTANEOUS_LOG.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_uploads(uploads: list) -> None:
    """Save uploads to the log file."""
    SPONTANEOUS_LOG.write_text(
        json.dumps(uploads, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def load_analyzed_codes() -> set:
    """Load school codes that have been analyzed (from CSV)."""
    if not ANALYSIS_SUMMARY_CSV.exists():
        return set()
    try:
        df = pd.read_csv(ANALYSIS_SUMMARY_CSV)
        return set(df['school_id'].dropna().str.upper().tolist())
    except Exception:
        return set()


def update_upload_status(codice: str, new_status: str) -> bool:
    """Update the status of an upload by school code."""
    uploads = load_uploads()
    codice_upper = codice.strip().upper()

    for upload in uploads:
        school_data = upload.get("school_data", {})
        if school_data.get("codice_meccanografico", "").upper() == codice_upper:
            upload["stato"] = new_status
            save_uploads(uploads)
            return True
    return False


def update_multiple_status(codici: list, new_status: str) -> int:
    """Update status for multiple uploads. Returns count of updated."""
    uploads = load_uploads()
    codici_upper = [c.strip().upper() for c in codici]
    updated = 0

    for upload in uploads:
        school_data = upload.get("school_data", {})
        codice = school_data.get("codice_meccanografico", "").upper()
        if codice in codici_upper:
            upload["stato"] = new_status
            updated += 1

    if updated > 0:
        save_uploads(uploads)
    return updated


def mark_as_downloaded(codici: list) -> None:
    """Mark uploads as downloaded with timestamp."""
    uploads = load_uploads()
    codici_upper = [c.strip().upper() for c in codici]
    now = datetime.now().isoformat()

    for upload in uploads:
        school_data = upload.get("school_data", {})
        codice = school_data.get("codice_meccanografico", "").upper()
        if codice in codici_upper:
            if "downloads" not in upload:
                upload["downloads"] = []
            upload["downloads"].append(now)

    save_uploads(uploads)


def get_effective_status(upload: dict, analyzed_codes: set) -> str:
    """Get the effective status, checking if in analyzed CSV."""
    codice = upload.get("school_data", {}).get("codice_meccanografico", "").upper()
    if codice in analyzed_codes:
        return "lavorato"
    return upload.get("stato", "inviato")


def format_date(iso_date: str) -> str:
    """Format ISO date to Italian format."""
    try:
        dt = datetime.fromisoformat(iso_date)
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return iso_date


def parse_date(iso_date: str) -> date | None:
    """Parse ISO date to date object."""
    try:
        return datetime.fromisoformat(iso_date).date()
    except Exception:
        return None


def get_pdf_path(upload: dict) -> Path | None:
    """Get the PDF file path for an upload."""
    stored_path = upload.get("stored_path", "")
    if stored_path:
        full_path = BASE_DIR / stored_path
        if full_path.exists():
            return full_path
    return None


def main():
    st.set_page_config(
        page_title="Gestione Invii PTOF",
        page_icon="📥",
        layout="wide"
    )

    # Setup page with admin protection
    setup_page("pages/16_📥_Gestione_Invii.py")

    st.title("📥 Gestione Invii PTOF")
    st.write("Gestisci gli invii PTOF ricevuti dalle scuole.")

    uploads = load_uploads()
    analyzed_codes = load_analyzed_codes()

    if not uploads:
        st.info("Nessun invio PTOF ricevuto.")
        return

    # Initialize selection state
    if "selected_codes" not in st.session_state:
        st.session_state.selected_codes = set()

    # Flag for select all / deselect all
    if "select_all_flag" not in st.session_state:
        st.session_state.select_all_flag = None

    # Filters section
    st.markdown("---")
    st.subheader("Filtri")

    col_filter1, col_filter2, col_filter3 = st.columns([2, 2, 2])

    with col_filter1:
        status_filter = st.selectbox(
            "Filtra per stato",
            options=["Tutti", "inviato", "in_lavorazione", "lavorato"]
        )

    with col_filter2:
        search_code = st.text_input("Cerca codice", placeholder="RMIC...")

    with col_filter3:
        download_filter = st.selectbox(
            "Filtra per download",
            options=["Tutti", "Mai scaricati", "Gia' scaricati"]
        )

    # Date range filter
    col_date1, col_date2, col_date3 = st.columns([2, 2, 2])

    # Get min/max dates from uploads
    all_dates = [parse_date(u.get("uploaded_at", "")) for u in uploads]
    all_dates = [d for d in all_dates if d is not None]
    min_date = min(all_dates) if all_dates else date.today()
    max_date = max(all_dates) if all_dates else date.today()

    with col_date1:
        date_from = st.date_input(
            "Data da",
            value=min_date,
            min_value=min_date,
            max_value=max_date
        )

    with col_date2:
        date_to = st.date_input(
            "Data a",
            value=max_date,
            min_value=min_date,
            max_value=max_date
        )

    with col_date3:
        st.write("")
        if st.button("Aggiorna", use_container_width=True):
            st.rerun()

    st.markdown("---")

    # Process and filter uploads
    processed_uploads = []
    for upload in uploads:
        effective_status = get_effective_status(upload, analyzed_codes)
        school_data = upload.get("school_data", {})
        codice = school_data.get("codice_meccanografico", "")
        upload_date = parse_date(upload.get("uploaded_at", ""))
        has_downloads = len(upload.get("downloads", [])) > 0

        # Apply status filter
        if status_filter != "Tutti" and effective_status != status_filter:
            continue

        # Apply code search
        if search_code and search_code.upper() not in codice.upper():
            continue

        # Apply download filter
        if download_filter == "Mai scaricati" and has_downloads:
            continue
        if download_filter == "Gia' scaricati" and not has_downloads:
            continue

        # Apply date filter
        if upload_date:
            if upload_date < date_from or upload_date > date_to:
                continue

        processed_uploads.append({
            "upload": upload,
            "effective_status": effective_status,
            "codice": codice,
            "has_downloads": has_downloads
        })

    # Sort by date (newest first)
    processed_uploads.sort(
        key=lambda x: x["upload"].get("uploaded_at", ""),
        reverse=True
    )

    # Stats
    stats_col1, stats_col2, stats_col3, stats_col4, stats_col5 = st.columns(5)
    all_statuses = [get_effective_status(u, analyzed_codes) for u in uploads]
    downloaded_count = sum(1 for u in uploads if len(u.get("downloads", [])) > 0)

    with stats_col1:
        st.metric("Totale", len(uploads))
    with stats_col2:
        st.metric("Inviati", all_statuses.count("inviato"))
    with stats_col3:
        st.metric("In Lavorazione", all_statuses.count("in_lavorazione"))
    with stats_col4:
        st.metric("Lavorati", all_statuses.count("lavorato"))
    with stats_col5:
        st.metric("Scaricati", downloaded_count)

    st.markdown("---")

    if not processed_uploads:
        st.warning("Nessun invio corrisponde ai filtri selezionati.")
        return

    # Selection and mass actions
    st.subheader("Selezione e Azioni di Massa")

    # Select all / deselect all
    col_sel1, col_sel2, col_sel3, col_sel4 = st.columns([1, 1, 2, 2])

    all_codes_in_view = [item["codice"] for item in processed_uploads]

    with col_sel1:
        if st.button("Seleziona tutti", use_container_width=True):
            st.session_state.select_all_flag = "select"
            st.rerun()

    with col_sel2:
        if st.button("Deseleziona tutti", use_container_width=True):
            st.session_state.select_all_flag = "deselect"
            st.rerun()

    # Apply select all / deselect all before rendering checkboxes
    if st.session_state.select_all_flag == "select":
        st.session_state.selected_codes = set(all_codes_in_view)
        st.session_state.select_all_flag = None
    elif st.session_state.select_all_flag == "deselect":
        st.session_state.selected_codes = set()
        st.session_state.select_all_flag = None

    # Count selected
    selected_in_view = [c for c in st.session_state.selected_codes if c in all_codes_in_view]
    st.info(f"**{len(selected_in_view)}** documenti selezionati")

    # Mass actions for selected
    if selected_in_view:
        col_action1, col_action2, col_action3 = st.columns([2, 2, 2])

        with col_action1:
            # Download selected as ZIP
            zip_buffer = io.BytesIO()
            files_added = 0
            codes_in_zip = []

            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for item in processed_uploads:
                    if item["codice"] in selected_in_view:
                        pdf_path = get_pdf_path(item["upload"])
                        if pdf_path:
                            codice = item["codice"]
                            zf.write(pdf_path, f"{codice}_PTOF.pdf")
                            files_added += 1
                            codes_in_zip.append(codice)

            zip_buffer.seek(0)

            if files_added > 0:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                downloaded = st.download_button(
                    label=f"📦 Scarica selezionati ({files_added} file)",
                    data=zip_buffer.getvalue(),
                    file_name=f"PTOF_selezionati_{timestamp}.zip",
                    mime="application/zip",
                    use_container_width=True
                )

                if downloaded:
                    # Mark as downloaded
                    mark_as_downloaded(codes_in_zip)
                    # Update status: inviato -> in_lavorazione
                    inviato_codes = [item["codice"] for item in processed_uploads
                                    if item["codice"] in codes_in_zip and item["effective_status"] == "inviato"]
                    if inviato_codes:
                        update_multiple_status(inviato_codes, "in_lavorazione")
                    # Clear selection
                    st.session_state.selected_codes.clear()
                    st.rerun()

        with col_action2:
            new_mass_status = st.selectbox(
                "Cambia stato a:",
                options=["-- Seleziona --", "inviato", "in_lavorazione"],
                key="mass_status_change"
            )

        with col_action3:
            # Only change non-lavorato items from selected
            changeable = [item["codice"] for item in processed_uploads
                         if item["codice"] in selected_in_view and item["effective_status"] != "lavorato"]

            st.write("")  # Spacer for alignment
            if new_mass_status != "-- Seleziona --" and changeable:
                if st.button(f"Applica stato ({len(changeable)})", use_container_width=True):
                    updated = update_multiple_status(changeable, new_mass_status)
                    st.success(f"Aggiornati {updated} invii")
                    st.session_state.selected_codes.clear()
                    st.rerun()
            elif changeable:
                st.caption(f"{len(changeable)} modificabili")
            else:
                st.caption("Nessuno modificabile")

    st.markdown("---")

    # Display uploads with checkboxes
    st.subheader(f"Invii ({len(processed_uploads)} risultati)")

    for item in processed_uploads:
        upload = item["upload"]
        effective_status = item["effective_status"]
        school_data = upload.get("school_data", {})
        codice = school_data.get("codice_meccanografico", "")
        downloads = upload.get("downloads", [])

        # Status color and icon
        if effective_status == "lavorato":
            status_color = "green"
            status_icon = "✅"
        elif effective_status == "in_lavorazione":
            status_color = "orange"
            status_icon = "🔄"
        else:
            status_color = "blue"
            status_icon = "📨"

        # Download indicator
        download_indicator = f" | 📥 {len(downloads)}x" if downloads else ""

        # Create row with checkbox
        col_check, col_content = st.columns([0.5, 9.5])

        with col_check:
            is_selected = codice in st.session_state.selected_codes
            # Use on_change callback to update selected_codes
            def toggle_selection(code=codice):
                if code in st.session_state.selected_codes:
                    st.session_state.selected_codes.discard(code)
                else:
                    st.session_state.selected_codes.add(code)

            st.checkbox(
                "",
                value=is_selected,
                key=f"chk_{codice}",
                label_visibility="collapsed",
                on_change=toggle_selection
            )

        with col_content:
            with st.expander(
                f"{status_icon} **{codice}** - {school_data.get('denominazione', 'N/D')} | "
                f":{status_color}[{effective_status}]{download_indicator}",
                expanded=False
            ):
                col1, col2, col3 = st.columns([2, 2, 1])

                with col1:
                    st.markdown("**Informazioni Scuola**")
                    st.write(f"**Denominazione:** {school_data.get('denominazione', 'N/D')}")
                    st.write(f"**Codice:** {codice}")
                    st.write(f"**Regione:** {school_data.get('regione', 'N/D')}")
                    st.write(f"**Provincia:** {school_data.get('provincia', 'N/D')}")
                    st.write(f"**Comune:** {school_data.get('comune', 'N/D')}")

                with col2:
                    st.markdown("**Dettagli Invio**")
                    st.write(f"**Tipo:** {school_data.get('tipo_scuola', 'N/D')}")
                    st.write(f"**Ordine:** {school_data.get('ordine_grado', 'N/D')}")
                    st.write(f"**Email:** {school_data.get('email', 'N/D') or 'N/D'}")
                    st.write(f"**Data invio:** {format_date(upload.get('uploaded_at', ''))}")
                    size_mb = upload.get("size", 0) / (1024 * 1024)
                    st.write(f"**Dimensione:** {size_mb:.2f} MB")

                    # Show download history
                    if downloads:
                        st.markdown("**Storico download:**")
                        for dl in downloads[-3:]:
                            st.caption(f"  - {format_date(dl)}")
                        if len(downloads) > 3:
                            st.caption(f"  ... e altri {len(downloads) - 3}")

                with col3:
                    st.markdown("**Azioni**")

                    # Download button
                    pdf_path = get_pdf_path(upload)
                    if pdf_path:
                        with open(pdf_path, "rb") as f:
                            pdf_data = f.read()

                        downloaded = st.download_button(
                            label="📥 Scarica PDF",
                            data=pdf_data,
                            file_name=f"{codice}_PTOF.pdf",
                            mime="application/pdf",
                            key=f"download_{codice}",
                            use_container_width=True
                        )

                        if downloaded:
                            mark_as_downloaded([codice])
                            if effective_status == "inviato":
                                update_upload_status(codice, "in_lavorazione")
                            st.rerun()
                    else:
                        st.warning("File non trovato")

                    # Manual status change (only if not "lavorato")
                    if effective_status != "lavorato":
                        st.markdown("---")
                        new_status = st.selectbox(
                            "Cambia stato",
                            options=["inviato", "in_lavorazione"],
                            index=0 if effective_status == "inviato" else 1,
                            key=f"status_{codice}"
                        )
                        if st.button("Aggiorna stato", key=f"update_{codice}", use_container_width=True):
                            if update_upload_status(codice, new_status):
                                st.success("Stato aggiornato")
                                st.rerun()
                    else:
                        st.success("Nel CSV analisi")

    # Footer
    st.markdown("---")
    st.caption("Stato 'lavorato': il codice meccanografico e' presente in analysis_summary.csv")


if __name__ == "__main__":
    main()
