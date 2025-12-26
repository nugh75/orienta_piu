# Windows + WSL Autostart (Streamlit)

Queste note servono per avviare la dashboard automaticamente all'avvio di Windows,
continuare a usare i comandi `make` in WSL e, se necessario, esporre la pagina.

## Obiettivo
- La dashboard Streamlit parte da sola all'accensione di Windows.
- I comandi `make` si usano dentro WSL quando serve.
- Le analisi restano persistenti nei folder del repo o in una cartella dati.

## Prerequisiti
- WSL installato (es. Ubuntu) con Python + venv + make.
- Repo presente in WSL, esempio: `/home/<user>/LIste`.
- `.env` configurato se usi servizi esterni.

## Avvio automatico con Task Scheduler
1. Apri **Operazioni Pianificate** (Task Scheduler).
2. Crea una nuova attivita':
   - Trigger: **All'avvio** (o **All'accesso**).
   - Azione: **Avvia programma**.
   - Programma: `wsl.exe`
   - Argomenti:
     ```text
     -d Ubuntu -- bash -lc "cd /home/<user>/LIste && STREAMLIT_SERVER_ADDRESS=0.0.0.0 make dashboard"
     ```
3. (Opzionale) Aggiungi una seconda azione per aprire il browser:
   - Programma: `cmd.exe`
   - Argomenti:
     ```text
     /c start http://localhost:8501
     ```

## Comandi `make` da Windows (semplice)
Esegui i comandi nel container WSL senza aprire una shell:
```bash
wsl -d Ubuntu -- bash -lc "cd /home/<user>/LIste && make run"
wsl -d Ubuntu -- bash -lc "cd /home/<user>/LIste && make csv"
wsl -d Ubuntu -- bash -lc "cd /home/<user>/LIste && make dashboard"
```

## Deploy solo Streamlit + dati (read-only)
Se vuoi solo la dashboard, ti basta copiare questi folder:
- `app/`
- `data/analysis_summary.csv`
- `analysis_results/` (per dettaglio scuole)
- `reports/` (best practice)
- `ptof_md/` (se vuoi lookup report)
- `requirements.txt` (per setup)

Poi avvii:
```bash
make dashboard
```

Se mancano alcuni dataset, puoi nascondere le pagine corrispondenti
dalla pagina **Amministrazione**.

## Opzionale: esposizione con cloudflared
Se vuoi pubblicare la dashboard via tunnel:
```bash
cloudflared tunnel --url http://localhost:8501
```
Per una configurazione stabile usa un tunnel nominato e un `config.yml`.
