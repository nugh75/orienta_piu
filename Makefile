.PHONY: setup run workflow dashboard csv backfill clean help download download-sample download-strato download-dry review-slow review-gemini review-scores review-scores-gemini

PYTHON = python3
PIP = pip
STREAMLIT = streamlit
DOWNLOADER = src/downloaders/ptof_downloader.py

help:
	@echo "Comandi disponibili:"
	@echo ""
	@echo "📥 DOWNLOAD PTOF:"
	@echo "  make download              - Scarica PTOF (dry-run, mostra stratificazione)"
	@echo "  make download-sample       - Scarica campione stratificato (5 per strato)"
	@echo "  make download-strato N=X   - Scarica X scuole per ogni strato (es: N=20)"
	@echo "  make download-statali      - Scarica tutte le scuole statali"
	@echo "  make download-paritarie    - Scarica tutte le scuole paritarie"
	@echo "  make download-regione R=X  - Scarica scuole di una regione (es: R=LAZIO)"
	@echo "  make download-metro        - Scarica solo province metropolitane"
	@echo "  make download-non-metro    - Scarica solo province NON metropolitane"
	@echo ""
	@echo "🤖 ANALISI & REVISIONE:"
	@echo "  make run                   - Esegue analisi sui PDF in ptof_inbox/"
	@echo "  make review-slow           - Revisione lenta con modelli free (usa MODEL=... per cambiare)"
	@echo "  make review-gemini         - Revisione con Google Gemini (usa MODEL=... per cambiare)"
	@echo "  make review-scores         - Revisione punteggi estremi (MODEL=..., LOW=2, HIGH=6, TARGET=...)"
	@echo "  make review-scores-gemini  - Revisione punteggi estremi con Google (MODEL=..., LOW=2, HIGH=6, TARGET=...)"
	@echo ""
	@echo "🔄 WORKFLOW ANALISI:"
	@echo "  make setup      - Installa le dipendenze"
	@echo "  make run        - Esegue il workflow completo (workflow_notebook.py)"
	@echo "  make workflow   - Alias di run (workflow_notebook.py)"
	@echo "  make dashboard  - Avvia la dashboard Streamlit"
	@echo "  make csv        - Rigenera il CSV dai file JSON (rebuild_csv_clean.py)"
	@echo "  make backfill   - Backfill metadati mancanti con scan LLM mirata"
	@echo "  make clean      - Pulisce file temporanei e cache"
	@echo ""
	@echo "🔗 COMBINAZIONI:"
	@echo "  make refresh    - Rigenera CSV e avvia dashboard"
	@echo "  make full       - Esegue run, rigenera CSV e avvia dashboard"
	@echo "  make pipeline   - Download sample + run + csv + dashboard"

setup:
	$(PIP) install -r requirements.txt

run:
	$(PYTHON) workflow_notebook.py

workflow: run

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

pipeline: download-sample run csv dashboard

# ═══════════════════════════════════════════════════════════════════
# DOWNLOAD PTOF
# ═══════════════════════════════════════════════════════════════════

# Dry-run: mostra stratificazione senza scaricare
download:
	$(PYTHON) $(DOWNLOADER) --tutte --dry-run

# Campione stratificato: 5 scuole per ogni strato
download-sample:
	$(PYTHON) $(DOWNLOADER) --tutte --sample-per-strato 5

# Campione stratificato con N scuole per strato (uso: make download-strato N=10)
download-strato:
ifndef N
	@echo "❌ Specificare il numero per strato con N=NUMERO"
	@echo "   Esempio: make download-strato N=10"
	@echo "   Esempio: make download-strato N=50"
	@echo ""
	@echo "   Scaricherà N scuole per ogni combinazione di:"
	@echo "   - Tipo scuola (STAT/PAR)"
	@echo "   - Area geografica (NORD OVEST/NORD EST/CENTRO/SUD/ISOLE)"
	@echo "   - Provincia (METRO/NON_METRO)"
	@echo "   - Grado (INFANZIA/PRIMARIA/SEC_PRIMO/SEC_SECONDO/ALTRO)"
else
	$(PYTHON) $(DOWNLOADER) --tutte --sample-per-strato $(N)
endif

# Tutte le scuole statali
download-statali:
	$(PYTHON) $(DOWNLOADER) --statali

# Tutte le scuole paritarie
download-paritarie:
	$(PYTHON) $(DOWNLOADER) --paritarie

# Scuole di una regione specifica (uso: make download-regione R=LAZIO)
download-regione:
ifndef R
	@echo "❌ Specificare la regione con R=NOME_REGIONE"
	@echo "   Esempio: make download-regione R=LAZIO"
	@echo ""
	@echo "   Regioni disponibili:"
	@echo "   ABRUZZO, BASILICATA, CALABRIA, CAMPANIA, EMILIA ROMAGNA,"
	@echo "   FRIULI-VENEZIA G., LAZIO, LIGURIA, LOMBARDIA, MARCHE,"
	@echo "   MOLISE, PIEMONTE, PUGLIA, SARDEGNA, SICILIA, TOSCANA,"
	@echo "   TRENTINO-ALTO ADIGE, UMBRIA, VALLE D'AOSTA, VENETO"
else
	$(PYTHON) $(DOWNLOADER) --tutte --regioni "$(R)"
endif

# Solo province metropolitane
download-metro:
	$(PYTHON) $(DOWNLOADER) --tutte --solo-metropolitane

# Solo province NON metropolitane
download-non-metro:
	$(PYTHON) $(DOWNLOADER) --tutte --solo-non-metropolitane

# Download per grado (uso: make download-grado G=SEC_SECONDO)
download-grado:
ifndef G
	@echo "❌ Specificare il grado con G=GRADO"
	@echo "   Esempio: make download-grado G=SEC_SECONDO"
	@echo ""
	@echo "   Gradi disponibili:"
	@echo "   INFANZIA, PRIMARIA, SEC_PRIMO, SEC_SECONDO, ALTRO"
else
	$(PYTHON) $(DOWNLOADER) --tutte --gradi $(G)
endif

# Download per area geografica (uso: make download-area A=SUD)
download-area:
ifndef A
	@echo "❌ Specificare l'area con A=AREA"
	@echo "   Esempio: make download-area A=SUD"
	@echo ""
	@echo "   Aree disponibili:"
	@echo "   NORD OVEST, NORD EST, CENTRO, SUD, ISOLE"
else
	$(PYTHON) $(DOWNLOADER) --tutte --aree "$(A)"
endif

# Reset stato download e ricomincia
download-reset:
	rm -f src/downloaders/download_state.json
	@echo "Stato download resettato."

# Slow Review (uso: make review-slow MODEL=google/gemini-2.0-flash-exp:free)
review-slow:
	$(PYTHON) src/processing/slow_reviewer.py $(if $(MODEL),--model "$(MODEL)",)

# Gemini Review (uso: make review-gemini MODEL=gemini-1.5-pro)
review-gemini:
	$(PYTHON) src/processing/gemini_reviewer.py $(if $(MODEL),--model "$(MODEL)",)

# Score Review (uso: make review-scores MODEL=... LOW=2 HIGH=6 TARGET=RMIC8GA002)
review-scores:
	$(PYTHON) src/processing/score_reviewer.py $(if $(MODEL),--model "$(MODEL)",) $(if $(LOW),--low-threshold $(LOW),) $(if $(HIGH),--high-threshold $(HIGH),) $(if $(TARGET),--target "$(TARGET)",) $(if $(WAIT),--wait $(WAIT),) $(if $(LIMIT),--limit $(LIMIT),) $(if $(MAX_CHARS),--max-chars $(MAX_CHARS),)

# Score Review (Gemini) (uso: make review-scores-gemini MODEL=gemini-2.0-flash-exp LOW=2 HIGH=6)
review-scores-gemini:
	$(PYTHON) src/processing/score_reviewer.py --provider gemini $(if $(MODEL),--model "$(MODEL)",) $(if $(LOW),--low-threshold $(LOW),) $(if $(HIGH),--high-threshold $(HIGH),) $(if $(TARGET),--target "$(TARGET)",) $(if $(WAIT),--wait $(WAIT),) $(if $(LIMIT),--limit $(LIMIT),) $(if $(MAX_CHARS),--max-chars $(MAX_CHARS),)

# Watch CSV: rigenera il CSV ogni N secondi (default 300s = 5min)
# Uso: make csv-watch INTERVAL=60
csv-watch:
	@echo "🔄 Avvio watch CSV (intervallo: $(or $(INTERVAL),300)s)..."
	@while true; do \
		make csv; \
		echo "💤 Attesa $(or $(INTERVAL),300)s..."; \
		sleep $(or $(INTERVAL),300); \
	done
