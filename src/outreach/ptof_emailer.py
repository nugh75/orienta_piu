#!/usr/bin/env python3
"""
PTOF Emailer
Send request emails to schools with an upload link.
"""

import argparse
import csv
import json
import logging
import os
import smtplib
import ssl
import time
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
CONFIG_DIR = BASE_DIR / "config"
LOG_DIR = BASE_DIR / "logs"

DEFAULT_CSV = DATA_DIR / "SCUANAGRAFESTAT20252620250901.csv"
REGISTRY_FILE = DATA_DIR / "ptof_upload_registry.json"
OUTREACH_LINKS_FILE = CONFIG_DIR / "outreach_links.json"
EMAIL_TEMPLATE_FILE = CONFIG_DIR / "email_template.txt"
EMAIL_SUBJECT_FILE = CONFIG_DIR / "email_subject.txt"

# Default links (fallback if config file doesn't exist)
DEFAULT_LINKS = {
    "dashboard_url": "https://orientapiu.it",
    "invia_ptof_url": "https://orientapiu.it/Invia_PTOF",
    "verifica_invio_url": "https://orientapiu.it/Verifica_Invio",
    "richiedi_revisione_url": "https://orientapiu.it/Richiedi_Revisione",
    "metodologia_url": "https://github.com/ddragoni/orientapiu",
    "documentazione_url": "https://github.com/ddragoni/orientapiu",
    "email_contatto": "orienta.piu@gmail.com"
}


def load_outreach_links() -> Dict:
    """Load outreach links from config file."""
    if OUTREACH_LINKS_FILE.exists():
        try:
            data = json.loads(OUTREACH_LINKS_FILE.read_text(encoding="utf-8"))
            result = DEFAULT_LINKS.copy()
            result.update(data)
            return result
        except Exception:
            pass
    return DEFAULT_LINKS.copy()


def get_default_template() -> str:
    """Generate email template using configured links."""
    return (
        "Gentile Dirigente Scolastico,\n\n"
        "mi chiamo Daniele Dragoni e sono dottorando impegnato nello sviluppo di ORIENTA+, "
        "un progetto di ricerca dedicato all'orientamento scolastico in Italia.\n"
        "Questa richiesta rientra nella mia ricerca di dottorato.\n\n"
        "L'obiettivo di ORIENTA+ e' analizzare i Piani Triennali dell'Offerta Formativa per "
        "individuare azioni, pratiche e strategie di orientamento presenti nel documento. "
        "L'analisi non esprime giudizi di valore sulla scuola: mira esclusivamente a descrivere "
        "e rendere visibili gli elementi che caratterizzano l'offerta formativa relativa all'orientamento.\n\n"
        "Perche' puo' essere utile alla sua scuola:\n"
        "- verificare quali pratiche di orientamento emergono dal PTOF;\n"
        "- confrontare il profilo della scuola con istituti simili del territorio;\n"
        "- individuare buone pratiche diffuse a livello nazionale o regionale.\n\n"
        "Se possibile, Le chiedo cortesemente di caricare il PTOF aggiornato (PDF) al seguente link:\n"
        "{upload_link}\n\n"
        "Dati della scuola:\n"
        "- Codice meccanografico: {codice}\n"
        "- Denominazione: {denominazione}\n"
        "- Comune: {comune}\n\n"
        "Una volta completata l'analisi, utilizzando il codice meccanografico sara' possibile:\n"
        "- consultare la pagina dedicata alla sua scuola: {dashboard_url}\n"
        "- consultare i risultati dell'indagine con statistiche e altri documenti: {dashboard_url}\n"
        "- verificare lo stato dell'elaborazione del PTOF: {verifica_invio_url}\n"
        "- richiedere una revisione: {richiedi_revisione_url}\n\n"
        "Indici utilizzati nell'analisi:\n"
        "- Indice RO (Robustezza dell'Orientamento): sintesi complessiva delle dimensioni valutate;\n"
        "- Finalita': chiarezza e coerenza delle finalita' orientative;\n"
        "- Obiettivi: definizione di obiettivi e risultati attesi;\n"
        "- Governance: organizzazione, ruoli e responsabilita' dell'orientamento;\n"
        "- Didattica orientativa: integrazione dell'orientamento nelle attivita' didattiche;\n"
        "- Opportunita' e percorsi: esperienze e iniziative rivolte agli studenti;\n"
        "- Partnership e attivita': collaborazioni e iniziative con enti esterni.\n\n"
        "Il PTOF e' un documento pubblico e l'analisi non comporta raccolta di dati personali "
        "ne' oneri per l'istituto.\n\n"
        "Metodologia: {metodologia_url}\n"
        "Codice e ulteriori informazioni: {documentazione_url}\n\n"
        "La prego di non rispondere a questa email con allegati: Le chiedo di "
        "caricare il PTOF esclusivamente tramite il modulo indicato sopra.\n\n"
        "Per qualsiasi chiarimento: {email_contatto}\n\n"
        "La ringrazio per l'attenzione e per la collaborazione.\n\n"
        "Cordiali saluti,\n"
        "{signature}\n"
    )


DEFAULT_SUBJECT = "ORIENTA+ - Analisi gratuita del PTOF della vostra scuola"


def setup_logging() -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("ptof_emailer")
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    file_handler = logging.FileHandler(LOG_DIR / "ptof_emailer.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)
    return logger


logger = setup_logging()


@dataclass
class SchoolContact:
    code: str
    name: str
    comune: str
    email: str
    pec: str


class SafeDict(dict):
    def __missing__(self, key: str) -> str:
        return ""


def normalize_value(value: str) -> str:
    return value.strip() if value else ""


def normalize_email(value: str) -> str:
    return value.strip().lower() if value else ""


def is_valid_email(value: str) -> bool:
    if not value:
        return False
    if "@" not in value:
        return False
    return True


def resolve_path(path_str: str) -> Path:
    path = Path(path_str)
    return path if path.is_absolute() else BASE_DIR / path


def load_registry(path: Path) -> Dict:
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Failed to read registry file: %s", exc)
            data = {}
    else:
        data = {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault("by_code", {})
    return data


def save_registry(path: Path, data: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp_path.replace(path)


def extract_school(row: Dict) -> Optional[SchoolContact]:
    code = normalize_value(row.get("CODICESCUOLA", "")).upper()
    if not code:
        return None
    name = normalize_value(row.get("DENOMINAZIONESCUOLA", ""))
    comune = normalize_value(row.get("DESCRIZIONECOMUNE", ""))
    email = normalize_email(row.get("INDIRIZZOEMAILSCUOLA", ""))
    pec = normalize_email(row.get("INDIRIZZOPECSCUOLA", ""))
    return SchoolContact(code=code, name=name, comune=comune, email=email, pec=pec)


def iter_schools(csv_paths: Iterable[Path]) -> Iterable[SchoolContact]:
    for path in csv_paths:
        if not path.exists():
            logger.warning("CSV not found: %s", path)
            continue
        with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                school = extract_school(row)
                if school:
                    yield school


def select_recipient(school: SchoolContact, use_pec: bool) -> str:
    if school.email:
        return school.email
    if use_pec and school.pec:
        return school.pec
    return ""


def get_or_create_entry(registry: Dict, school: SchoolContact) -> Tuple[Dict, bool]:
    by_code = registry.get("by_code", {})
    entry = by_code.get(school.code)
    if entry:
        updated = False
        if school.name and entry.get("denominazione") != school.name:
            entry["denominazione"] = school.name
            updated = True
        if school.comune and entry.get("comune") != school.comune:
            entry["comune"] = school.comune
            updated = True
        if school.email and entry.get("email") != school.email:
            entry["email"] = school.email
            updated = True
        if school.pec and entry.get("pec") != school.pec:
            entry["pec"] = school.pec
            updated = True
        return entry, updated

    entry = {
        "school_code": school.code,
        "denominazione": school.name,
        "comune": school.comune,
        "email": school.email,
        "pec": school.pec,
        "created_at": datetime.utcnow().isoformat(),
        "last_sent_at": None,
        "last_sent_to": None,
    }
    by_code[school.code] = entry
    registry["by_code"] = by_code
    return entry, True


def load_template(path: Optional[str]) -> str:
    """Load email template from custom file, config file, or default."""
    if path:
        template_path = resolve_path(path)
        return template_path.read_text(encoding="utf-8")
    # Check for config file template
    if EMAIL_TEMPLATE_FILE.exists():
        try:
            return EMAIL_TEMPLATE_FILE.read_text(encoding="utf-8")
        except Exception:
            pass
    return get_default_template()


def load_subject() -> str:
    """Load email subject from config file or return default."""
    if EMAIL_SUBJECT_FILE.exists():
        try:
            return EMAIL_SUBJECT_FILE.read_text(encoding="utf-8").strip()
        except Exception:
            pass
    return DEFAULT_SUBJECT


def render_template(template: str, context: Dict) -> str:
    return template.format_map(SafeDict(context))


def parse_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    try:
        text = str(value).strip().lower()
    except Exception:
        return default
    return text in {"1", "true", "yes", "y", "on"}


def load_smtp_config(args: argparse.Namespace) -> Dict:
    config = {}
    if args.smtp_config:
        config_path = resolve_path(args.smtp_config)
        if config_path.exists():
            config.update(json.loads(config_path.read_text(encoding="utf-8")))
    if config:
        alias_map = {
            "smtp_host": ["smtp_host", "host"],
            "smtp_port": ["smtp_port", "port"],
            "smtp_user": ["smtp_user", "user", "username"],
            "smtp_password": ["smtp_password", "password", "pass"],
            "smtp_from": ["smtp_from", "from", "mail_from"],
            "smtp_reply_to": ["smtp_reply_to", "reply_to", "reply-to"],
            "smtp_use_ssl": ["smtp_use_ssl", "use_ssl", "ssl"],
            "smtp_use_starttls": ["smtp_use_starttls", "use_starttls", "starttls"],
        }
        normalized = {}
        for key, aliases in alias_map.items():
            for alias in aliases:
                if alias in config and config[alias] not in (None, ""):
                    normalized[key] = config[alias]
                    break
        config.update(normalized)

    def pick(name: str, env_name: str, fallback=None):
        value = getattr(args, name, None)
        if value is not None:
            return value
        env_val = os.getenv(env_name)
        if env_val is not None:
            return env_val
        return config.get(name, fallback)

    smtp = {
        "host": pick("smtp_host", "SMTP_HOST"),
        "port": int(pick("smtp_port", "SMTP_PORT", 587)),
        "user": pick("smtp_user", "SMTP_USER"),
        "password": pick("smtp_password", "SMTP_PASSWORD"),
        "mail_from": pick("smtp_from", "SMTP_FROM"),
        "reply_to": pick("smtp_reply_to", "SMTP_REPLY_TO"),
        "use_ssl": parse_bool(pick("smtp_use_ssl", "SMTP_USE_SSL"), False),
        "use_starttls": parse_bool(pick("smtp_use_starttls", "SMTP_USE_STARTTLS"), True),
    }
    return smtp


def build_message(to_addr: str, subject: str, body: str, mail_from: str, reply_to: Optional[str]) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = mail_from
    message["To"] = to_addr
    if reply_to:
        message["Reply-To"] = reply_to
    message.set_content(body)
    return message


def smtp_connect(config: Dict) -> smtplib.SMTP:
    if config["use_ssl"]:
        context = ssl.create_default_context()
        server = smtplib.SMTP_SSL(config["host"], config["port"], context=context)
    else:
        server = smtplib.SMTP(config["host"], config["port"])
        server.ehlo()
        if config["use_starttls"]:
            context = ssl.create_default_context()
            server.starttls(context=context)
            server.ehlo()
    if config["user"]:
        server.login(config["user"], config.get("password") or "")
    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="Send PTOF request emails with upload link.")
    parser.add_argument("--csv", action="append", help="CSV path(s) for schools.")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--template", help="Path to custom email template.")
    parser.add_argument("--subject", default=None, help="Email subject (default: from config or built-in)")
    parser.add_argument("--signature", default=os.getenv("PTOF_EMAIL_SIGNATURE", "Team PTOF"))
    parser.add_argument("--use-pec", action="store_true", help="Use PEC if email is missing.")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of emails.")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between sends (seconds).")
    parser.add_argument("--send", action="store_true", help="Send emails (default is dry-run).")
    parser.add_argument("--resend", action="store_true", help="Resend even if already sent.")
    parser.add_argument("--smtp-config", help="Path to JSON SMTP config.")
    parser.add_argument("--smtp-host")
    parser.add_argument("--smtp-port", type=int)
    parser.add_argument("--smtp-user")
    parser.add_argument("--smtp-password")
    parser.add_argument("--smtp-from")
    parser.add_argument("--smtp-reply-to")
    parser.add_argument("--smtp-use-ssl")
    parser.add_argument("--smtp-use-starttls")
    args = parser.parse_args()

    csv_paths = args.csv or [str(DEFAULT_CSV)]
    csv_paths = [resolve_path(path) for path in csv_paths]

    registry = load_registry(REGISTRY_FILE)
    links = load_outreach_links()
    template = load_template(args.template)
    subject = args.subject if args.subject else load_subject()
    signature = args.signature
    base_url = args.base_url or os.getenv("PTOF_UPLOAD_BASE_URL") or links["invia_ptof_url"]
    send_emails = args.send

    smtp_config = load_smtp_config(args)
    if send_emails:
        missing = [key for key in ("host", "mail_from") if not smtp_config.get(key)]
        if missing:
            raise SystemExit(f"Missing SMTP config values: {', '.join(missing)}")

    server = None
    if send_emails:
        server = smtp_connect(smtp_config)

    total = 0
    sent = 0
    skipped = 0
    invalid = 0

    try:
        for school in iter_schools(csv_paths):
            if args.limit and total >= args.limit:
                break

            recipient = select_recipient(school, args.use_pec)
            if not is_valid_email(recipient):
                invalid += 1
                continue

            entry, updated = get_or_create_entry(registry, school)
            if updated:
                save_registry(REGISTRY_FILE, registry)

            if entry.get("last_sent_at") and not args.resend:
                skipped += 1
                continue

            upload_link = base_url
            context = {
                "upload_link": upload_link,
                "codice": school.code,
                "denominazione": school.name,
                "comune": school.comune,
                "signature": signature,
                "dashboard_url": links["dashboard_url"],
                "invia_ptof_url": links["invia_ptof_url"],
                "verifica_invio_url": links["verifica_invio_url"],
                "richiedi_revisione_url": links["richiedi_revisione_url"],
                "metodologia_url": links["metodologia_url"],
                "documentazione_url": links["documentazione_url"],
                "email_contatto": links["email_contatto"],
            }
            body = render_template(template, context)
            email_subject = render_template(subject, context)

            total += 1
            if not send_emails:
                logger.info("DRY RUN -> %s (%s)", school.code, recipient)
                continue

            message = build_message(recipient, email_subject, body, smtp_config["mail_from"], smtp_config.get("reply_to"))
            try:
                server.send_message(message)
                entry["last_sent_at"] = datetime.utcnow().isoformat()
                entry["last_sent_to"] = recipient
                save_registry(REGISTRY_FILE, registry)
                sent += 1
                logger.info("Sent -> %s (%s)", school.code, recipient)
            except Exception as exc:
                logger.error("Failed -> %s (%s): %s", school.code, recipient, exc)
            if args.delay:
                time.sleep(args.delay)
    finally:
        if server:
            server.quit()

    logger.info("Done. processed=%s sent=%s skipped=%s invalid=%s", total, sent, skipped, invalid)


if __name__ == "__main__":
    main()
