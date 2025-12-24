# PTOF Outreach (Email + Upload Portal)

Questo documento descrive come inviare le email di richiesta PTOF e come raccogliere i PDF tramite una pagina web separata.

## 1) Avvio del portale upload

Esempio (porta dedicata diversa dalla dashboard):

```bash
streamlit run src/portal/ptof_upload_portal.py --server.port 8502
```

Il link pubblico usato nelle email deve puntare a questa app, ad esempio:
`https://example.org/?token=...`

## 2) Invio email alle scuole

Configura le variabili SMTP in ambiente o in un file JSON:

```
SMTP_HOST
SMTP_PORT
SMTP_USER
SMTP_PASSWORD
SMTP_FROM
SMTP_REPLY_TO (opzionale)
SMTP_USE_SSL (opzionale)
SMTP_USE_STARTTLS (opzionale)
```

Esempio di invio (dry-run di default):

```bash
python src/outreach/ptof_emailer.py --base-url "https://example.org" --limit 10
```

Esempio di invio reale:

```bash
python src/outreach/ptof_emailer.py --base-url "https://example.org" --send --limit 10
```

## Output

- I token e lo stato sono salvati in `data/ptof_upload_tokens.json`
- I PDF caricati finiscono in `ptof_inbox/{CODICE}_PTOF.pdf`
- Se esiste gia un file, viene spostato in `ptof_inbox_backup/`

