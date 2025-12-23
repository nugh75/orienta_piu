.PHONY: setup run dashboard csv backfill clean help

PYTHON = python3
PIP = pip
STREAMLIT = streamlit

help:
	@echo "Comandi disponibili:"
	@echo "  make setup      - Installa le dipendenze"
	@echo "  make run        - Esegue il workflow completo (workflow_notebook.py)"
	@echo "  make dashboard  - Avvia la dashboard Streamlit"
	@echo "  make csv        - Rigenera il CSV dai file JSON (rebuild_csv_clean.py)"
	@echo "  make backfill   - Backfill metadati mancanti con scan LLM mirata"
	@echo "  make clean      - Pulisce file temporanei e cache"
	@echo ""
	@echo "Combinazioni:"
	@echo "  make refresh    - Rigenera CSV e avvia dashboard"
	@echo "  make full       - Esegue run, rigenera CSV e avvia dashboard"

setup:
	$(PIP) install -r requirements.txt

run:
	$(PYTHON) workflow_notebook.py

dashboard:
	@echo "🛑 Arresto eventuali istanze precedenti..."
	-pkill -f "streamlit run app/Home.py" || true
	@sleep 1
	$(STREAMLIT) run app/Home.py --server.port 8501

csv:
	$(PYTHON) src/processing/rebuild_csv_clean.py

backfill:
	$(PYTHON) src/processing/backfill_metadata_llm.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Combinazioni
refresh: csv dashboard

full: run csv dashboard
