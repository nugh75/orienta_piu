#!/usr/bin/env python3
"""
Pagina admin per gestire gli invii PTOF.
Permette di visualizzare, scaricare e aggiornare lo stato degli invii.
"""

import io
import json
import shutil
import zipfile
from datetime import datetime, date
from pathlib import Path
import streamlit as st
import pandas as pd

from page_control import setup_page

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
CONFIG_DIR = BASE_DIR / "config"
SPONTANEOUS_LOG = DATA_DIR / "spontaneous_uploads.json"
ANALYSIS_SUMMARY_CSV = DATA_DIR / "analysis_summary.csv"
PTOF_INVIATI_DIR = BASE_DIR / "ptof_inviati"
PTOF_INBOX_DIR = BASE_DIR / "ptof_inbox"
OUTREACH_LINKS_FILE = CONFIG_DIR / "outreach_links.json"
EMAIL_TEMPLATE_FILE = CONFIG_DIR / "email_template.txt"
EMAIL_SUBJECT_FILE = CONFIG_DIR / "email_subject.txt"

# Default links
DEFAULT_LINKS = {
    "dashboard_url": "https://orientapiu.it",
    "invia_ptof_url": "https://orientapiu.it/Invia_PTOF",
    "verifica_invio_url": "https://orientapiu.it/Verifica_Invio",
    "richiedi_revisione_url": "https://orientapiu.it/Richiedi_Revisione",
    "metodologia_url": "https://github.com/ddragoni/orientapiu",
    "documentazione_url": "https://github.com/ddragoni/orientapiu",
    "email_contatto": "orienta.piu@gmail.com"
}

DEFAULT_SUBJECT = "ORIENTA+ - Analisi gratuita del PTOF della vostra scuola"

DEFAULT_TEMPLATE = """Gentile Dirigente Scolastico,

mi chiamo Daniele Dragoni e sono dottorando impegnato nello sviluppo di ORIENTA+, un progetto di ricerca dedicato all'orientamento scolastico in Italia.
Questa richiesta rientra nella mia ricerca di dottorato.

L'obiettivo di ORIENTA+ e' analizzare i Piani Triennali dell'Offerta Formativa per individuare azioni, pratiche e strategie di orientamento presenti nel documento. L'analisi non esprime giudizi di valore sulla scuola: mira esclusivamente a descrivere e rendere visibili gli elementi che caratterizzano l'offerta formativa relativa all'orientamento.

Perche' puo' essere utile alla sua scuola:
- verificare quali pratiche di orientamento emergono dal PTOF;
- confrontare il profilo della scuola con istituti simili del territorio;
- individuare buone pratiche diffuse a livello nazionale o regionale.

Se possibile, Le chiedo cortesemente di caricare il PTOF aggiornato (PDF) al seguente link:
{upload_link}

Dati della scuola:
- Codice meccanografico: {codice}
- Denominazione: {denominazione}
- Comune: {comune}

Una volta completata l'analisi, utilizzando il codice meccanografico sara' possibile:
- consultare la pagina dedicata alla sua scuola: {dashboard_url}
- consultare i risultati dell'indagine con statistiche e altri documenti: {dashboard_url}
- verificare lo stato dell'elaborazione del PTOF: {verifica_invio_url}
- richiedere una revisione: {richiedi_revisione_url}

Indici utilizzati nell'analisi:
- Indice di Completezza: sintesi complessiva delle dimensioni valutate (scala 1-7);
- Finalita': chiarezza e coerenza delle finalita' orientative;
- Obiettivi: definizione di obiettivi e risultati attesi;
- Governance: organizzazione, ruoli e responsabilita' dell'orientamento;
- Didattica orientativa: integrazione dell'orientamento nelle attivita' didattiche;
- Opportunita' e percorsi: esperienze e iniziative rivolte agli studenti;
- Partnership e attivita': collaborazioni e iniziative con enti esterni.

Il PTOF e' un documento pubblico e l'analisi non comporta raccolta di dati personali ne' oneri per l'istituto.

Metodologia: {metodologia_url}
Codice e ulteriori informazioni: {documentazione_url}

La prego di non rispondere a questa email con allegati: Le chiedo di caricare il PTOF esclusivamente tramite il modulo indicato sopra.

Per qualsiasi chiarimento: {email_contatto}

La ringrazio per l'attenzione e per la collaborazione.

Cordiali saluti,
{signature}
"""


def load_outreach_links() -> dict:
    """Load outreach links configuration."""
    if not OUTREACH_LINKS_FILE.exists():
        return DEFAULT_LINKS.copy()
    try:
        data = json.loads(OUTREACH_LINKS_FILE.read_text(encoding="utf-8"))
        # Merge with defaults to ensure all keys exist
        result = DEFAULT_LINKS.copy()
        result.update(data)
        return result
    except Exception:
        return DEFAULT_LINKS.copy()


def save_outreach_links(links: dict) -> None:
    """Save outreach links configuration."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    OUTREACH_LINKS_FILE.write_text(
        json.dumps(links, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def load_email_template() -> str:
    """Load email template from file or return default."""
    if EMAIL_TEMPLATE_FILE.exists():
        try:
            return EMAIL_TEMPLATE_FILE.read_text(encoding="utf-8")
        except Exception:
            pass
    return DEFAULT_TEMPLATE


def save_email_template(template: str) -> None:
    """Save email template to file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    EMAIL_TEMPLATE_FILE.write_text(template, encoding="utf-8")


def load_email_subject() -> str:
    """Load email subject from file or return default."""
    if EMAIL_SUBJECT_FILE.exists():
        try:
            return EMAIL_SUBJECT_FILE.read_text(encoding="utf-8").strip()
        except Exception:
            pass
    return DEFAULT_SUBJECT


def save_email_subject(subject: str) -> None:
    """Save email subject to file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    EMAIL_SUBJECT_FILE.write_text(subject, encoding="utf-8")


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


def move_file_to_inbox(upload: dict) -> bool:
    """Move file from ptof_inviati to ptof_inbox. Returns True if successful."""
    stored_path = upload.get("stored_path", "")
    if not stored_path:
        return False

    source_path = BASE_DIR / stored_path
    if not source_path.exists():
        return False

    # Create inbox directory if needed
    PTOF_INBOX_DIR.mkdir(parents=True, exist_ok=True)

    # Build destination path
    dest_path = PTOF_INBOX_DIR / source_path.name

    # If file already exists in inbox, add timestamp
    if dest_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stem = dest_path.stem
        suffix = dest_path.suffix
        dest_path = PTOF_INBOX_DIR / f"{stem}_{timestamp}{suffix}"

    try:
        shutil.move(str(source_path), str(dest_path))
        # Update stored_path in upload record
        upload["stored_path"] = str(dest_path.relative_to(BASE_DIR))
        return True
    except Exception:
        return False


def update_upload_status(codice: str, new_status: str) -> bool:
    """Update the status of an upload by school code."""
    uploads = load_uploads()
    codice_upper = codice.strip().upper()

    for upload in uploads:
        school_data = upload.get("school_data", {})
        if school_data.get("codice_meccanografico", "").upper() == codice_upper:
            # Move file to inbox if status is changing to in_lavorazione
            if new_status == "in_lavorazione":
                move_file_to_inbox(upload)
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
            # Move file to inbox if status is changing to in_lavorazione
            if new_status == "in_lavorazione":
                move_file_to_inbox(upload)
            upload["stato"] = new_status
            updated += 1

    if updated > 0:
        save_uploads(uploads)
    return updated


def move_all_pending_to_inbox() -> tuple[int, int]:
    """Move all files with status 'inviato' or 'in_lavorazione' to inbox.
    Returns (moved_count, total_pending)."""
    uploads = load_uploads()
    moved = 0
    pending = 0

    for upload in uploads:
        status = upload.get("stato", "inviato")
        if status in ("inviato", "in_lavorazione"):
            pending += 1
            if move_file_to_inbox(upload):
                moved += 1
            # Set status to in_lavorazione if it was inviato
            if status == "inviato":
                upload["stato"] = "in_lavorazione"

    if moved > 0 or pending > 0:
        save_uploads(uploads)

    return moved, pending


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

    # Configurable links section
    with st.expander("⚙️ Configurazione Link Email", expanded=False):
        st.write("Configura i link che verranno utilizzati nelle email di outreach.")

        links = load_outreach_links()

        col1, col2 = st.columns(2)

        with col1:
            new_dashboard = st.text_input(
                "URL Dashboard",
                value=links.get("dashboard_url", ""),
                key="link_dashboard"
            )
            new_invia = st.text_input(
                "URL Invia PTOF",
                value=links.get("invia_ptof_url", ""),
                key="link_invia"
            )
            new_verifica = st.text_input(
                "URL Verifica Invio",
                value=links.get("verifica_invio_url", ""),
                key="link_verifica"
            )

        with col2:
            new_revisione = st.text_input(
                "URL Richiedi Revisione",
                value=links.get("richiedi_revisione_url", ""),
                key="link_revisione"
            )
            new_metodo = st.text_input(
                "URL Metodologia",
                value=links.get("metodologia_url", ""),
                key="link_metodo"
            )
            new_docs = st.text_input(
                "URL Documentazione/GitHub",
                value=links.get("documentazione_url", ""),
                key="link_docs"
            )
            new_email = st.text_input(
                "Email di contatto",
                value=links.get("email_contatto", ""),
                key="link_email"
            )

        if st.button("💾 Salva configurazione link", use_container_width=True):
            new_links = {
                "dashboard_url": new_dashboard,
                "invia_ptof_url": new_invia,
                "verifica_invio_url": new_verifica,
                "richiedi_revisione_url": new_revisione,
                "metodologia_url": new_metodo,
                "documentazione_url": new_docs,
                "email_contatto": new_email
            }
            save_outreach_links(new_links)
            st.success("Configurazione salvata!")
            st.rerun()

        st.markdown("---")
        st.caption("Questi link vengono usati nel template email di `ptof_emailer.py`")

    # Quick links section
    with st.expander("🔗 Link Rapidi", expanded=False):
        links = load_outreach_links()
        col_link1, col_link2, col_link3 = st.columns(3)
        with col_link1:
            st.markdown("**Pagine Pubbliche**")
            st.markdown(f"- [Dashboard]({links['dashboard_url']})")
            st.markdown("- [Invia PTOF](/Invia_PTOF)")
            st.markdown("- [Verifica Invio](/Verifica_Invio)")
            st.markdown("- [Richiedi Revisione](/Richiedi_Revisione)")
        with col_link2:
            st.markdown("**Documentazione**")
            st.markdown(f"- [Metodologia]({links['metodologia_url']})")
            st.markdown(f"- [GitHub]({links['documentazione_url']})")
        with col_link3:
            st.markdown("**Pagine Admin**")
            st.markdown("- [Gestione Dati](/Gestione_Dati)")
            st.markdown("- [Gestione Revisioni](/Gestione_Revisioni)")

    # Email template editing section
    with st.expander("📧 Template Email", expanded=False):
        st.write("Modifica il template email utilizzato per le comunicazioni alle scuole.")

        # Load current values
        current_subject = load_email_subject()
        current_template = load_email_template()

        # Subject input
        new_subject = st.text_input(
            "Oggetto email",
            value=current_subject,
            key="email_subject_input",
            help="L'oggetto dell'email inviata alle scuole"
        )

        # Template text area
        new_template = st.text_area(
            "Corpo email",
            value=current_template,
            height=400,
            key="email_template_input",
            help="Il testo dell'email. Usa i placeholder tra parentesi graffe."
        )

        # Placeholder help
        st.markdown("**Placeholder disponibili:**")
        st.markdown("""
        - `{upload_link}` - Link per caricare il PTOF
        - `{codice}` - Codice meccanografico della scuola
        - `{denominazione}` - Nome della scuola
        - `{comune}` - Comune della scuola
        - `{signature}` - Firma dell'email
        - `{dashboard_url}` - URL dashboard (da config link)
        - `{invia_ptof_url}` - URL pagina invio PTOF
        - `{verifica_invio_url}` - URL pagina verifica invio
        - `{richiedi_revisione_url}` - URL pagina richiesta revisione
        - `{metodologia_url}` - URL metodologia
        - `{documentazione_url}` - URL documentazione
        - `{email_contatto}` - Email di contatto
        """)

        col_save, col_reset = st.columns(2)

        with col_save:
            if st.button("💾 Salva template", use_container_width=True):
                save_email_subject(new_subject)
                save_email_template(new_template)
                st.success("Template salvato!")
                st.rerun()

        with col_reset:
            if st.button("🔄 Ripristina default", use_container_width=True):
                # Delete custom files to revert to defaults
                if EMAIL_TEMPLATE_FILE.exists():
                    EMAIL_TEMPLATE_FILE.unlink()
                if EMAIL_SUBJECT_FILE.exists():
                    EMAIL_SUBJECT_FILE.unlink()
                st.success("Template ripristinato ai valori di default!")
                st.rerun()

        st.caption("Il template viene usato da `ptof_emailer.py` per le email di outreach.")

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

    # Filters section in expander
    with st.expander("🔍 Filtri", expanded=False):
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

    # Stats row with action button
    all_statuses = [get_effective_status(u, analyzed_codes) for u in uploads]
    downloaded_count = sum(1 for u in uploads if len(u.get("downloads", [])) > 0)
    pending_count = all_statuses.count("inviato") + all_statuses.count("in_lavorazione")

    col_stats, col_action_btn = st.columns([5, 1])

    with col_stats:
        stats_col1, stats_col2, stats_col3, stats_col4, stats_col5 = st.columns(5)
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

    with col_action_btn:
        st.write("")  # Spacer
        if pending_count > 0:
            if st.button(f"📂 Inbox ({pending_count})", use_container_width=True, help="Sposta tutti i file pendenti in ptof_inbox"):
                moved, total = move_all_pending_to_inbox()
                if moved > 0:
                    st.success(f"Spostati {moved}/{total} in inbox")
                else:
                    st.info("Gia' tutti in inbox")
                st.rerun()

    if not processed_uploads:
        st.warning("Nessun invio corrisponde ai filtri selezionati.")
        return

    # Selection toolbar
    all_codes_in_view = [item["codice"] for item in processed_uploads]
    selected_in_view = [c for c in st.session_state.selected_codes if c in all_codes_in_view]

    col_sel1, col_sel2, col_count, col_action1, col_action2, col_action3 = st.columns([1, 1, 1, 2, 2, 1])

    with col_sel1:
        if st.button("✓ Tutti", use_container_width=True):
            for code in all_codes_in_view:
                st.session_state[f"chk_{code}"] = True
            st.session_state.selected_codes = set(all_codes_in_view)
            st.rerun()

    with col_sel2:
        if st.button("✗ Nessuno", use_container_width=True):
            for code in all_codes_in_view:
                st.session_state[f"chk_{code}"] = False
            st.session_state.selected_codes = set()
            st.rerun()

    with col_count:
        st.caption(f"**{len(selected_in_view)}** sel.")

    # Mass actions (only show if items selected)
    if selected_in_view:
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
                    label=f"📦 Scarica ({files_added})",
                    data=zip_buffer.getvalue(),
                    file_name=f"PTOF_selezionati_{timestamp}.zip",
                    mime="application/zip",
                    use_container_width=True
                )

                if downloaded:
                    mark_as_downloaded(codes_in_zip)
                    inviato_codes = [item["codice"] for item in processed_uploads
                                    if item["codice"] in codes_in_zip and item["effective_status"] == "inviato"]
                    if inviato_codes:
                        update_multiple_status(inviato_codes, "in_lavorazione")
                    st.session_state.selected_codes.clear()
                    st.rerun()

        with col_action2:
            new_mass_status = st.selectbox(
                "Stato",
                options=["--", "inviato", "in_lavorazione"],
                key="mass_status_change",
                label_visibility="collapsed"
            )

        with col_action3:
            changeable = [item["codice"] for item in processed_uploads
                         if item["codice"] in selected_in_view and item["effective_status"] != "lavorato"]
            if new_mass_status != "--" and changeable:
                if st.button("Applica", use_container_width=True):
                    updated = update_multiple_status(changeable, new_mass_status)
                    st.toast(f"Aggiornati {updated} invii")
                    st.session_state.selected_codes.clear()
                    st.rerun()

    # Display uploads with checkboxes
    st.subheader(f"Invii ({len(processed_uploads)})")

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
            # Sync checkbox with selected_codes
            checkbox_key = f"chk_{codice}"
            is_selected = codice in st.session_state.selected_codes

            # Initialize checkbox state if not set
            if checkbox_key not in st.session_state:
                st.session_state[checkbox_key] = is_selected

            def sync_selection(code=codice, key=checkbox_key):
                if st.session_state[key]:
                    st.session_state.selected_codes.add(code)
                else:
                    st.session_state.selected_codes.discard(code)

            st.checkbox(
                "",
                key=checkbox_key,
                label_visibility="collapsed",
                on_change=sync_selection
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
                        new_status = st.selectbox(
                            "Stato",
                            options=["inviato", "in_lavorazione"],
                            index=0 if effective_status == "inviato" else 1,
                            key=f"status_{codice}",
                            label_visibility="collapsed"
                        )
                        if st.button("Aggiorna", key=f"update_{codice}", use_container_width=True):
                            if update_upload_status(codice, new_status):
                                st.toast("Stato aggiornato")
                                st.rerun()
                    else:
                        st.success("Analizzato")

    # Footer
    st.caption("Stato 'lavorato' = codice presente in analysis_summary.csv")


if __name__ == "__main__":
    main()
