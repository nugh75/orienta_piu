FROM python:3.11-slim

WORKDIR /app

# Tool di sistema necessari (make per task runner)
RUN apt-get update && apt-get install -y --no-install-recommends \
    make \
    && rm -rf /var/lib/apt/lists/*

# Dipendenze minime per la dashboard
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia solo il codice dell'app (non i dati)
COPY app/ ./app/
COPY src/ ./src/
COPY config/ ./config/
COPY scripts/ ./scripts/
COPY .streamlit/ ./.streamlit/

# Porta Streamlit
EXPOSE 8587

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8587/_stcore/health')" || exit 1

# Avvia dashboard
CMD ["streamlit", "run", "app/Home.py", "--server.port=8587", "--server.address=0.0.0.0"]
