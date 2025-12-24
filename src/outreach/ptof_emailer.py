#!/usr/bin/env python3
"""
PTOF Emailer
Send request emails to schools with a unique upload link.
"""

import argparse
import csv
import json
import logging
import os
import secrets
import smtplib
import ssl
import time
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"

DEFAULT_CSV = DATA_DIR / "SCUANAGRAFESTAT20252620250901.csv"
TOKENS_FILE = DATA_DIR / "ptof_upload_tokens.json"

DEFAULT_SUBJECT = "Richiesta PTOF"
DEFAULT_TEMPLATE = (
    "Gentile Dirigente,\n\n"
    "stiamo raccogliendo i PTOF aggiornati per il progetto di analisi.\n"
    "Vi chiediamo di caricare il documento (PDF) usando questo link:\n"
    "{upload_link}\n\n"
    "Codice scuola: {codice}\n"
    "Denominazione: {denominazione}\n"
    "Comune: {comune}\n\n"
    "Se il link non funziona, potete rispondere a questa email con il PTOF in allegato.\n\n"
    "Grazie,\n"
    "{signature}\n"
)


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


def load_tokens(path: Path) -> Dict:
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Failed to read tokens file: %s", exc)
            data = {}
    else:
        data = {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault("by_token", {})
    data.setdefault("by_code", {})
    return data


def save_tokens(path: Path, data: Dict) -> None:
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


def build_upload_link(base_url: str, token: str) -> str:
    parsed = urlparse(base_url)
    query = dict(parse_qsl(parsed.query))
    query["token"] = token
    new_query = urlencode(query)
    return urlunparse(parsed._replace(query=new_query))


def get_or_create_token(tokens: Dict, school: SchoolContact) -> Tuple[str, Dict, bool]:
    by_code = tokens.get("by_code", {})
    by_token = tokens.get("by_token", {})
    existing_token = by_code.get(school.code)
    if existing_token and existing_token in by_token:
        entry = by_token[existing_token]
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
        return existing_token, entry, updated

    token = secrets.token_urlsafe(16)
    entry = {
        "school_code": school.code,
        "denominazione": school.name,
        "comune": school.comune,
        "email": school.email,
        "pec": school.pec,
        "created_at": datetime.utcnow().isoformat(),
        "last_sent_at": None,
        "used_at": None,
        "uploads": [],
    }
    by_token[token] = entry
    by_code[school.code] = token
    tokens["by_token"] = by_token
    tokens["by_code"] = by_code
    return token, entry, True


def load_template(path: Optional[str]) -> str:
    if not path:
        return DEFAULT_TEMPLATE
    template_path = resolve_path(path)
    return template_path.read_text(encoding="utf-8")


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
    parser.add_argument("--base-url", default=os.getenv("PTOF_UPLOAD_BASE_URL", "http://localhost:8502"))
    parser.add_argument("--template", help="Path to custom email template.")
    parser.add_argument("--subject", default=DEFAULT_SUBJECT)
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

    tokens = load_tokens(TOKENS_FILE)
    template = load_template(args.template)
    subject = args.subject
    signature = args.signature
    base_url = args.base_url
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

            token, entry, updated = get_or_create_token(tokens, school)
            if updated:
                save_tokens(TOKENS_FILE, tokens)

            if entry.get("last_sent_at") and not args.resend:
                skipped += 1
                continue

            upload_link = build_upload_link(base_url, token)
            context = {
                "upload_link": upload_link,
                "codice": school.code,
                "denominazione": school.name,
                "comune": school.comune,
                "signature": signature,
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
                save_tokens(TOKENS_FILE, tokens)
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
