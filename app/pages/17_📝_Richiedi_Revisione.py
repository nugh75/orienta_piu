#!/usr/bin/env python3
"""
Pagina per richiedere la revisione di un'analisi PTOF.
Le scuole possono segnalare elementi mancanti o errori nell'analisi.
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
ANALYSIS_SUMMARY_CSV = DATA_DIR / "analysis_summary.csv"
REVISION_REQUESTS_FILE = DATA_DIR / "revision_requests.json"


def load_analyzed_codes() -> dict:
    """Load school codes that have been analyzed (from CSV) with their names."""
    if not ANALYSIS_SUMMARY_CSV.exists():
        return {}
    try:
        df = pd.read_csv(ANALYSIS_SUMMARY_CSV)
        result = {}
        for _, row in df.iterrows():
            code = str(row.get('school_id', '')).upper()
            name = row.get('denominazione', 'N/D')
            if code:
                result[code] = name
        return result
    except Exception:
        return {}


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


def add_revision_request(codice: str, denominazione: str, email: str,
                         motivo: str, dettagli: str) -> bool:
    """Add a new revision request."""
    requests = load_revision_requests()

    new_request = {
        "codice_meccanografico": codice.upper(),
        "denominazione": denominazione,
        "email_contatto": email,
        "motivo": motivo,
        "dettagli": dettagli,
        "submitted_at": datetime.now().isoformat(),
        "stato": "pending",  # pending, in_review, completed, rejected
        "note_admin": None,
        "completed_at": None
    }

    requests.append(new_request)
    save_revision_requests(requests)
    return True


def get_requests_for_code(codice: str) -> list:
    """Get all requests for a school code."""
    requests = load_revision_requests()
    codice_upper = codice.strip().upper()
    return [r for r in requests
            if r.get("codice_meccanografico", "").upper() == codice_upper]


def format_date(iso_date: str) -> str:
    """Format ISO date to Italian format."""
    try:
        dt = datetime.fromisoformat(iso_date)
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return iso_date or "N/D"


def main():
    st.set_page_config(
        page_title="Richiedi Revisione",
        page_icon="📝",
        layout="centered"
    )
    setup_page("pages/17_📝_Richiedi_Revisione.py")

    st.title("📝 Richiedi Revisione Analisi")
    st.write("""
    Se ritieni che l'analisi del PTOF della tua scuola non rifletta correttamente
    le pratiche di orientamento presenti nel documento, puoi richiedere una revisione.
    """)

    st.info("""
    **Nota importante:** L'analisi ORIENTA+ rileva la presenza di azioni e pratiche
    di orientamento nel PTOF. Non esprime giudizi di valore sulla scuola, ma identifica
    gli elementi caratterizzanti l'offerta orientativa così come emergono dal documento.
    """)

    # Load analyzed schools
    analyzed_schools = load_analyzed_codes()

    st.markdown("---")

    # Step 1: Enter school code
    st.subheader("1. Inserisci il codice meccanografico")

    codice = st.text_input(
        "Codice meccanografico",
        max_chars=10,
        placeholder="Es: RMIC8GA002",
        help="Il codice meccanografico della tua scuola (10 caratteri)"
    ).strip().upper()

    if not codice:
        st.caption("Inserisci il codice meccanografico per verificare se l'analisi è disponibile.")
        return

    if len(codice) < 10:
        st.warning("Il codice meccanografico deve essere di 10 caratteri.")
        return

    # Check if school has been analyzed
    if codice not in analyzed_schools:
        st.error(f"""
        **Scuola non trovata nel database delle analisi.**

        Il codice `{codice}` non risulta tra le scuole analizzate.

        Possibili cause:
        - Il PTOF non è ancora stato inviato
        - L'analisi è ancora in corso
        - Il codice meccanografico non è corretto

        **Cosa fare:**
        - Verifica lo stato dell'invio: [Verifica Invio](/Verifica_Invio)
        - Invia il PTOF: [Invia PTOF](/Invia_PTOF)
        """)
        return

    denominazione = analyzed_schools[codice]
    st.success(f"**Scuola trovata:** {denominazione}")

    # Check for existing requests and show history
    existing_requests = get_requests_for_code(codice)
    if existing_requests:
        st.markdown("---")
        st.subheader("📋 Storico richieste di revisione")

        # Sort by date (newest first)
        existing_requests.sort(key=lambda x: x.get("submitted_at", ""), reverse=True)

        for req in existing_requests:
            stato = req.get("stato", "pending")
            submitted_at = req.get("submitted_at", "")

            # Status display
            status_map = {
                "pending": ("🟡", "In Attesa"),
                "in_review": ("🔵", "In Revisione"),
                "completed": ("🟢", "Completata"),
                "rejected": ("🔴", "Respinta")
            }
            icon, label = status_map.get(stato, ("⚪", stato))

            with st.expander(f"{icon} Richiesta del {format_date(submitted_at)[:10]} - {label}"):
                st.write(f"**Motivo:** {req.get('motivo', 'N/D')}")
                st.write(f"**Dettagli:** {req.get('dettagli', 'N/D')}")
                st.write(f"**Email:** {req.get('email_contatto', 'N/D')}")

                if req.get("note_admin"):
                    st.info(f"**Risposta:** {req.get('note_admin')}")

                if req.get("completed_at"):
                    st.caption(f"Completata il: {format_date(req.get('completed_at'))}")

        # Check if there's a pending request
        pending = [r for r in existing_requests if r.get("stato") == "pending"]
        if pending:
            st.warning("""
            **Nota:** Hai già una richiesta in attesa di revisione.
            Puoi comunque inviare una nuova richiesta se hai ulteriori segnalazioni.
            """)

    st.markdown("---")

    # Step 2: Revision details
    st.subheader("2. Descrivi la richiesta di revisione")

    email = st.text_input(
        "Email di contatto *",
        placeholder="dirigente@scuola.edu.it",
        help="Riceverai aggiornamenti sullo stato della revisione"
    )

    motivo = st.selectbox(
        "Motivo della richiesta *",
        options=[
            "-- Seleziona --",
            "Elementi di orientamento non rilevati",
            "Punteggi non corrispondenti al contenuto",
            "Progetti/attività non identificati",
            "Errore nei dati della scuola",
            "Altro"
        ]
    )

    dettagli = st.text_area(
        "Descrivi nel dettaglio cosa ritieni manchi o sia errato *",
        height=150,
        placeholder="""Esempio:
- Il progetto "Orientamento Futuro" con laboratori settimanali non è stato rilevato
- Le convenzioni con le università del territorio non compaiono nell'analisi
- La sezione dedicata all'orientamento (pag. 45-52) non sembra considerata""",
        help="Più dettagli fornisci, più accurata sarà la revisione"
    )

    st.markdown("---")

    # Step 3: Submit
    st.subheader("3. Invia la richiesta")

    st.caption("""
    Inviando questa richiesta, confermi che le informazioni fornite sono corrette
    e che sei autorizzato a richiedere la revisione per conto della scuola.
    """)

    # Validation
    can_submit = True
    errors = []

    if not email or "@" not in email:
        errors.append("Inserisci un indirizzo email valido")
        can_submit = False

    if motivo == "-- Seleziona --":
        errors.append("Seleziona un motivo per la richiesta")
        can_submit = False

    if len(dettagli.strip()) < 20:
        errors.append("Descrivi più nel dettaglio la richiesta (almeno 20 caratteri)")
        can_submit = False

    if errors:
        for error in errors:
            st.error(error)

    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("📤 Invia Richiesta", disabled=not can_submit, use_container_width=True):
            success = add_revision_request(
                codice=codice,
                denominazione=denominazione,
                email=email,
                motivo=motivo,
                dettagli=dettagli.strip()
            )

            if success:
                st.success("""
                **Richiesta inviata con successo!**

                La tua richiesta di revisione è stata registrata.
                Riceverai aggiornamenti all'indirizzo email fornito.

                Tempi di risposta indicativi: 5-10 giorni lavorativi.
                """)
                st.balloons()
            else:
                st.error("Errore durante l'invio. Riprova più tardi.")

    with col2:
        st.page_link("pages/15_🔎_Verifica_Invio.py", label="🔎 Verifica stato invio", use_container_width=True)

    # Footer
    st.markdown("---")
    st.caption("Per assistenza: orienta.piu@gmail.com")


if __name__ == "__main__":
    main()
