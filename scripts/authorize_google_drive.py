#!/usr/bin/env python3
"""
Script per autorizzare l'accesso a Google Drive.
Esegui una volta per generare il token di refresh.
"""

import json
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

# Paths
CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
OAUTH_CREDS_FILE = CONFIG_DIR / "oauth_credentials.json"
TOKEN_FILE = CONFIG_DIR / "google_token.json"

# Scopes necessari
SCOPES = ['https://www.googleapis.com/auth/drive.file']


def main():
    print("=" * 50)
    print("Autorizzazione Google Drive")
    print("=" * 50)
    print()

    if not OAUTH_CREDS_FILE.exists():
        print(f"Errore: file {OAUTH_CREDS_FILE} non trovato!")
        return

    # Avvia il flusso OAuth
    print("Si aprira il browser per l'autorizzazione...")
    print("Accedi con l'account: orienta.piu@gmail.com")
    print()

    flow = InstalledAppFlow.from_client_secrets_file(
        str(OAUTH_CREDS_FILE),
        scopes=SCOPES
    )

    # Questo apre il browser per l'autenticazione
    creds = flow.run_local_server(port=8090)

    # Salva il token
    token_data = {
        'token': creds.token,
        'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri,
        'client_id': creds.client_id,
        'client_secret': creds.client_secret,
        'scopes': creds.scopes
    }

    TOKEN_FILE.write_text(json.dumps(token_data, indent=2))

    print()
    print("=" * 50)
    print("Autorizzazione completata!")
    print(f"Token salvato in: {TOKEN_FILE}")
    print("=" * 50)


if __name__ == "__main__":
    main()
