# Piano di Dockerizzazione - ORIENTA+ (Solo Dashboard)

## Approccio Ibrido

- **Dashboard Streamlit** → Docker (containerizzato)
- **Backend/Make commands** → Locale con `.venv`
- **Dati** → Directory host montate come volumi in Docker

Vantaggi:
- Semplice da gestire
- Make commands eseguiti nativamente (più veloci, accesso diretto a Ollama)
- Dashboard isolata e portabile
- Dati condivisi tra Docker e ambiente locale

---

## 1. File da Creare

### 1.1 `Dockerfile`
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Dipendenze minime per la dashboard
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia solo il codice dell'app (non i dati)
COPY app/ ./app/
COPY src/ ./src/
COPY config/ ./config/
COPY .streamlit/ ./.streamlit/

# Porta Streamlit
EXPOSE 8501

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Avvia dashboard
CMD ["streamlit", "run", "app/Home.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### 1.2 `docker-compose.yml`
```yaml
version: '3.8'

services:
  dashboard:
    build: .
    container_name: orienta-dashboard
    ports:
      - "8501:8501"
    volumes:
      # === DATI (read-only per la dashboard) ===
      - ./data:/app/data:ro                        # CSV, registry (sola lettura)
      - ./analysis_results:/app/analysis_results:ro # Report JSON/MD (sola lettura)

      # === DATI (read-write per funzionalità admin) ===
      - ./ptof_inbox:/app/ptof_inbox               # Upload PTOF
      - ./logs:/app/logs                           # Log dashboard

      # === CONFIGURAZIONE ===
      - ./.env:/app/.env:ro
    environment:
      - PYTHONUNBUFFERED=1
      - STREAMLIT_SERVER_HEADLESS=true
      - STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
    restart: unless-stopped
```

### 1.3 `.dockerignore`
```
# Virtual environment (locale)
.venv/
venv/
__pycache__/
*.pyc

# Dati (montati come volumi)
ptof_inbox/
ptof_md/
ptof/
ptof_discarded/
analysis_results/
data/
logs/
backups/

# Git e IDE
.git/
.idea/
.vscode/

# File sensibili
.env

# Non necessari nel container
Makefile
*.md
*.sh
workflow_notebook.py
```

---

## 2. Setup Ambiente Locale (.venv)

### 2.1 Creare virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2.2 Aggiungere al Makefile
```makefile
# ===== SETUP LOCALE =====

## Crea e attiva virtual environment
venv:
	python3 -m venv .venv
	@echo "Attiva con: source .venv/bin/activate"
	@echo "Poi esegui: make setup"

## Installa dipendenze nel venv attivo
setup:
	pip install -r requirements.txt

# ===== DOCKER (solo dashboard) =====

## Avvia dashboard Docker
docker-up:
	docker compose up -d

## Ferma dashboard Docker
docker-down:
	docker compose down

## Ricostruisci immagine
docker-build:
	docker compose build --no-cache

## Log dashboard
docker-logs:
	docker compose logs -f dashboard

## Stato container
docker-status:
	docker compose ps
```

---

## 3. Struttura Volumi

| Directory Host | Mount Docker | Permessi | Scopo |
|----------------|--------------|----------|-------|
| `./data/` | `/app/data` | read-only | CSV, registry, dataset |
| `./analysis_results/` | `/app/analysis_results` | read-only | Report analisi |
| `./ptof_inbox/` | `/app/ptof_inbox` | read-write | Upload PTOF da dashboard |
| `./logs/` | `/app/logs` | read-write | Log dashboard |
| `./.env` | `/app/.env` | read-only | Configurazione |

**Nota:** I volumi critici sono read-only per la dashboard. Solo i comandi `make` locali possono modificarli.

---

## 4. Flusso di Lavoro

```
┌─────────────────────────────────────────────────────────────┐
│                         HOST                                │
│  ┌──────────────────┐     ┌──────────────────────────────┐ │
│  │   .venv (locale) │     │     Docker Container         │ │
│  │                  │     │  ┌────────────────────────┐  │ │
│  │  make run        │────▶│  │  Dashboard Streamlit   │  │ │
│  │  make csv        │     │  │  (porta 8501)          │  │ │
│  │  make download   │     │  └────────────────────────┘  │ │
│  │  make review-*   │            │        ▲              │ │
│  └────────┬─────────┘            │        │              │ │
│           │                      ▼        │              │ │
│           │              ┌───────────────────────────┐   │ │
│           └─────────────▶│      VOLUMI CONDIVISI     │◀──┘ │
│                          │  ./data/                  │     │
│                          │  ./analysis_results/      │     │
│                          │  ./ptof_inbox/            │     │
│                          └───────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. Esempi di Utilizzo

### Setup iniziale (una volta)
```bash
# Crea venv locale
make venv
source .venv/bin/activate
make setup

# Build e avvia dashboard Docker
make docker-build
make docker-up
```

### Uso quotidiano
```bash
# Attiva venv
source .venv/bin/activate

# Esegui analisi (locale, veloce, accesso diretto a Ollama)
make run

# Rigenera CSV
make csv

# La dashboard Docker vede automaticamente i nuovi dati
# (basta ricaricare la pagina nel browser)
```

### Comandi Docker
```bash
make docker-up      # Avvia dashboard
make docker-down    # Ferma dashboard
make docker-logs    # Vedi log
make docker-build   # Ricostruisci dopo modifiche al codice
```

---

## 6. Vantaggi di questo Approccio

| Aspetto | Docker Completo | Solo Dashboard (scelto) |
|---------|-----------------|-------------------------|
| Complessità | Alta | Bassa |
| Make commands | Via docker exec | Nativi (veloci) |
| Accesso Ollama | Richiede network config | Diretto |
| Hot reload dati | Complesso | Automatico via volumi |
| Debugging | Difficile | Facile |
| Portabilità dashboard | ✅ | ✅ |

---

## 7. Passi di Implementazione

1. **Creare virtual environment locale**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Creare file Docker**
   - `Dockerfile` (solo dashboard)
   - `docker-compose.yml` (volumi read-only)
   - `.dockerignore`

3. **Aggiornare Makefile**
   - Target `venv` e `setup`
   - Target `docker-*`

4. **Testare**
   ```bash
   # Test locale
   make run
   make csv

   # Test Docker
   make docker-build
   make docker-up
   # Apri http://localhost:8501
   ```

5. **Verificare sincronizzazione**
   - Esegui `make csv` localmente
   - Ricarica dashboard nel browser
   - I dati devono aggiornarsi
