# CONTEXT — LIste

<!-- ai4educ:context-template v1.0 -->

## Quick Reference
- **Stack**: Python, Flask, Streamlit, PostgreSQL, Ollama/OpenRouter/Gemini
- **Entry point**: `make setup && make run` o `docker compose up -d` (dashboard: 8587, web-runner: 5050)
- **Test**: manuale

## Domain
Sistema automatizzato per l'analisi dei documenti PTOF (Piano Triennale dell'Offerta Formativa) delle scuole italiane. Estrae dati strutturati dai PDF, li valida, e li presenta in dashboard interattiva. Usa LLM per estrazione e classificazione.

### Key Directories
- `ptof_inbox/` — documenti da processare
- `ptof_processed/` — documenti elaborati
- `web-runner/` — interfaccia web (Flask)
- `dashboard/` — visualizzazione (Streamlit)
