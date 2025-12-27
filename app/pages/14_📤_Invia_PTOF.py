#!/usr/bin/env python3
"""
Pagina per l'invio del PTOF.
Supporta:
1. Upload con token (link ricevuto via email)
2. Upload spontaneo con compilazione dati scuola
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
import streamlit as st
import pandas as pd

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
TOKENS_FILE = DATA_DIR / "ptof_upload_tokens.json"
SPONTANEOUS_LOG = DATA_DIR / "spontaneous_uploads.json"

# Local storage
PTOF_INBOX_DIR = BASE_DIR / "ptof_inbox"
PTOF_INBOX_BACKUP_DIR = BASE_DIR / "ptof_inbox_backup"

# Liste per i dropdown
REGIONI = [
    "Abruzzo", "Basilicata", "Calabria", "Campania", "Emilia Romagna",
    "Friuli-Venezia G.", "Lazio", "Liguria", "Lombardia", "Marche",
    "Molise", "Piemonte", "Puglia", "Sardegna", "Sicilia", "Toscana",
    "Trentino-Alto Adige", "Umbria", "Valle d'Aosta", "Veneto"
]

TIPI_SCUOLA = [
    "Infanzia",
    "Primaria",
    "I Grado (Medie)",
    "II Grado (Superiori)",
    "Comprensivo",
    "Liceo",
    "Tecnico",
    "Professionale"
]

ORDINI_GRADO = [
    "Infanzia",
    "Primaria",
    "Secondaria I Grado",
    "Secondaria II Grado",
    "Comprensivo (Infanzia + Primaria + Medie)",
    "Istituto Superiore"
]


def ensure_dir(path: Path) -> None:
    """Ensure a directory exists."""
    path.mkdir(parents=True, exist_ok=True)


def relative_path(path: Path) -> str:
    """Return path relative to BASE_DIR when possible."""
    try:
        return str(path.relative_to(BASE_DIR))
    except ValueError:
        return str(path)


def save_ptof_file(data: bytes, filename: str) -> Optional[Path]:
    """Save PTOF PDF locally. Returns the saved path or None."""
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
    """Load tokens from file."""
    try:
        if hasattr(st, 'secrets') and 'ptof_tokens' in st.secrets:
            data = dict(st.secrets['ptof_tokens'])
            data.setdefault("by_token", {})
            data.setdefault("by_code", {})
            return data
    except Exception:
        pass

    if TOKENS_FILE.exists():
        try:
            data = json.loads(TOKENS_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    else:
        data = {}
    data.setdefault("by_token", {})
    data.setdefault("by_code", {})
    return data


def save_tokens(data: Dict) -> None:
    """Save tokens."""
    try:
        TOKENS_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = TOKENS_FILE.with_suffix(TOKENS_FILE.suffix + ".tmp")
        tmp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp_path.replace(TOKENS_FILE)
    except Exception:
        pass


def log_spontaneous_upload(school_data: Dict, stored_path: str, filename: str, size: int) -> None:
    """Log spontaneous upload."""
    try:
        if SPONTANEOUS_LOG.exists():
            logs = json.loads(SPONTANEOUS_LOG.read_text(encoding="utf-8"))
        else:
            logs = []

        logs.append({
            "uploaded_at": datetime.utcnow().isoformat(),
            "school_data": school_data,
            "stored_path": stored_path,
            "filename": filename,
            "size": size
        })

        SPONTANEOUS_LOG.write_text(json.dumps(logs, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def update_token_entry(tokens: Dict, token: str, upload_name: str, size: int, stored_path: str) -> None:
    """Update token with upload info."""
    entry = tokens["by_token"].get(token, {})
    entry.setdefault("uploads", [])
    now = datetime.utcnow().isoformat()
    entry["used_at"] = now
    entry["uploads"].append({
        "uploaded_at": now,
        "source_name": upload_name,
        "stored_path": stored_path,
        "size": size,
    })
    tokens["by_token"][token] = entry
    save_tokens(tokens)


def sanitize_code(code: str) -> str:
    """Sanitize school code."""
    code = (code or "").strip().upper()
    return "".join(ch for ch in code if ch.isalnum())


def get_province_for_region(regione: str) -> list:
    """Get provinces for a region from the data."""
    try:
        df = pd.read_csv(DATA_DIR / "analysis_summary.csv")
        provinces = df[df['regione'] == regione]['provincia'].dropna().unique()
        return sorted(provinces.tolist())
    except Exception:
        return []


def render_token_upload():
    """Render upload form for token-based access."""
    st.subheader("Upload con Codice Invito")

    token = st.query_params.get("token", "")
    if not token:
        token = st.text_input("Inserisci il codice ricevuto via email:", key="token_input")

    if not token:
        st.info("Inserisci il codice ricevuto via email per procedere.")
        return

    tokens = load_tokens()
    entry = tokens.get("by_token", {}).get(token)

    if not entry:
        st.error("Codice non valido o scaduto.")
        return

    school_code = sanitize_code(entry.get("school_code", ""))
    if not school_code:
        st.error("Codice non valido.")
        return

    # Show school info
    st.success("Codice valido!")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Scuola:** {entry.get('denominazione', 'N/D')}")
    with col2:
        st.markdown(f"**Comune:** {entry.get('comune', 'N/D')}")

    st.markdown("---")

    uploaded = st.file_uploader("Seleziona il file PTOF (PDF)", type=["pdf"], key="token_upload")

    if st.button("Carica PTOF", type="primary", key="token_submit"):
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
            st.error("Errore durante il caricamento. Riprova.")


def render_spontaneous_upload():
    """Render upload form for spontaneous submission."""
    st.subheader("Invia il tuo PTOF")
    st.write("Compila i dati della tua scuola e carica il PTOF.")

    with st.form("spontaneous_form"):
        col1, col2 = st.columns(2)

        with col1:
            codice_meccanografico = st.text_input(
                "Codice Meccanografico *",
                placeholder="Es. RMIC8GA002",
                help="Il codice identificativo della scuola (10 caratteri)"
            )

            denominazione = st.text_input(
                "Denominazione Scuola *",
                placeholder="Es. IC Via Roma"
            )

            regione = st.selectbox(
                "Regione *",
                options=[""] + REGIONI,
                index=0
            )

            # Province dinamiche basate sulla regione
            if regione:
                province_list = get_province_for_region(regione)
                if not province_list:
                    province_list = ["Altra provincia"]
                provincia = st.selectbox(
                    "Provincia *",
                    options=[""] + province_list
                )
            else:
                provincia = st.text_input("Provincia *", placeholder="Es. Roma")

        with col2:
            comune = st.text_input(
                "Comune *",
                placeholder="Es. Roma"
            )

            tipo_scuola = st.selectbox(
                "Tipo Scuola *",
                options=[""] + TIPI_SCUOLA
            )

            ordine_grado = st.selectbox(
                "Ordine e Grado *",
                options=[""] + ORDINI_GRADO
            )

            statale_paritaria = st.radio(
                "Statale o Paritaria *",
                options=["Statale", "Paritaria"],
                horizontal=True
            )

        st.markdown("---")

        col_email, col_tel = st.columns(2)
        with col_email:
            email = st.text_input(
                "Email di contatto",
                placeholder="segreteria@scuola.it"
            )
        with col_tel:
            telefono = st.text_input(
                "Telefono (opzionale)",
                placeholder="06 12345678"
            )

        st.markdown("---")

        uploaded = st.file_uploader("Seleziona il file PTOF (PDF) *", type=["pdf"])

        submitted = st.form_submit_button("Invia PTOF", type="primary", use_container_width=True)

        if submitted:
            # Validazione
            errors = []
            if not codice_meccanografico or len(codice_meccanografico.strip()) < 8:
                errors.append("Codice meccanografico non valido (minimo 8 caratteri)")
            if not denominazione:
                errors.append("Inserisci la denominazione della scuola")
            if not regione:
                errors.append("Seleziona la regione")
            if not provincia:
                errors.append("Inserisci la provincia")
            if not comune:
                errors.append("Inserisci il comune")
            if not tipo_scuola:
                errors.append("Seleziona il tipo di scuola")
            if not ordine_grado:
                errors.append("Seleziona l'ordine e grado")
            if not uploaded:
                errors.append("Seleziona un file PDF")

            if errors:
                for err in errors:
                    st.error(err)
                return

            data = uploaded.getbuffer()
            if not data:
                st.error("File vuoto.")
                return

            if not bytes(data[:4]) == b"%PDF":
                st.error("Il file non sembra un PDF valido.")
                return

            # Sanitize code
            clean_code = sanitize_code(codice_meccanografico)

            with st.spinner("Caricamento in corso..."):
                filename = f"{clean_code}_PTOF.pdf"
                stored_path = save_ptof_file(bytes(data), filename)

            if stored_path:
                # Log the upload
                school_data = {
                    "codice_meccanografico": clean_code,
                    "denominazione": denominazione,
                    "regione": regione,
                    "provincia": provincia,
                    "comune": comune,
                    "tipo_scuola": tipo_scuola,
                    "ordine_grado": ordine_grado,
                    "statale_paritaria": statale_paritaria,
                    "email": email,
                    "telefono": telefono
                }
                log_spontaneous_upload(school_data, relative_path(stored_path), uploaded.name, len(data))

                st.success("Caricamento completato con successo! Grazie per aver inviato il PTOF.")
                st.balloons()
                st.info("Il PTOF verra analizzato e i risultati saranno disponibili nella dashboard.")
            else:
                st.error("Errore durante il caricamento. Riprova o contattaci.")


def main():
    st.set_page_config(
        page_title="Invia PTOF",
        page_icon="📤",
        layout="centered"
    )

    st.title("📤 Invia il tuo PTOF")
    st.write("Carica il Piano Triennale dell'Offerta Formativa della tua scuola.")

    # Ensure local storage is ready
    ensure_dir(PTOF_INBOX_DIR)

    st.markdown("---")

    # Check if token in URL
    token = st.query_params.get("token", "")

    if token:
        # Token mode
        render_token_upload()
    else:
        # Tabs for different modes
        tab1, tab2 = st.tabs(["📝 Invio Spontaneo", "🔑 Ho un Codice Invito"])

        with tab1:
            render_spontaneous_upload()

        with tab2:
            render_token_upload()

    # Footer
    st.markdown("---")
    st.caption("I dati inseriti saranno utilizzati esclusivamente per l'analisi del PTOF. "
               "Per informazioni: orienta.piu@gmail.com")


if __name__ == "__main__":
    main()
