#!/usr/bin/env python3
"""
Pagina per l'invio del PTOF.
Supporta l'upload con compilazione dati scuola.
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
SPONTANEOUS_LOG = DATA_DIR / "spontaneous_uploads.json"

# Local storage
PTOF_INVIATI_DIR = BASE_DIR / "ptof_inviati"
PTOF_INVIATI_BACKUP_DIR = BASE_DIR / "ptof_inviati_backup"

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
            "size": size,
            "stato": "inviato"
        })

        SPONTANEOUS_LOG.write_text(json.dumps(logs, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


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

        uploaded = st.file_uploader(
            "Seleziona il file PTOF (PDF) *",
            type=["pdf"],
            help="Il file verrà rinominato automaticamente in CODICEMECCANOGRAFICO_PTOF.pdf per uniformità con gli altri PTOF"
        )

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
    ensure_dir(PTOF_INVIATI_DIR)

    st.markdown("---")

    render_spontaneous_upload()

    # Footer
    st.markdown("---")
    st.caption("I dati inseriti saranno utilizzati esclusivamente per l'analisi del PTOF. "
               "Per informazioni: orienta.piu@gmail.com")


if __name__ == "__main__":
    main()
