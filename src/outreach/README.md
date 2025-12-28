# PTOF Outreach Automation

This module handles the email outreach to schools and the upload portal for PTOF PDFs.

## Components

- Email sender: `src/outreach/ptof_emailer.py`
- Upload portal: `src/portal/ptof_upload_portal.py`

## Quick start

1) Start the upload portal (optional, separate from the main dashboard):

```bash
streamlit run src/portal/ptof_upload_portal.py --server.port 8502
```

2) Configure SMTP (env vars or JSON file):

```
SMTP_HOST
SMTP_PORT
SMTP_USER
SMTP_PASSWORD
SMTP_FROM
SMTP_REPLY_TO (optional)
SMTP_USE_SSL (optional)
SMTP_USE_STARTTLS (optional)
```

3) Send emails (dry-run by default):

```bash
python src/outreach/ptof_emailer.py --base-url "https://orientapiu.it/Invia_PTOF" --limit 10
```

4) Send for real:

```bash
python src/outreach/ptof_emailer.py --base-url "https://orientapiu.it/Invia_PTOF" --send --limit 10
```

## Data flow

- Email registry is saved in `data/ptof_upload_registry.json`
- Uploads are saved in `ptof_inviati/{CODICE}_PTOF.pdf`
- Existing files are moved to `ptof_inviati_backup/`

## CSV input

By default the emailer uses:
`data/SCUANAGRAFESTAT20252620250901.csv`

You can pass multiple CSVs:

```bash
python src/outreach/ptof_emailer.py --csv data/SCUANAGRAFESTAT20252620250901.csv --csv data/SCUANAGRAFEPAR20252620250901.csv
```

## Notes

- The upload link points directly to the upload page (no token required).
