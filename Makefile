.PHONY: setup run workflow dashboard csv backfill clean help download download-sample download-strato download-dry review-slow review-gemini review-ollama review-scores review-scores-gemini review-scores-ollama review-non-ptof outreach-portal outreach-email list-models list-models-openrouter list-models-gemini recover-not-ptof wizard

PYTHON = python3
PIP = pip
STREAMLIT = streamlit
DOWNLOADER = src/downloaders/ptof_downloader.py
UPLOAD_PORTAL = src/portal/ptof_upload_portal.py
EMAILER = src/outreach/ptof_emailer.py
MODEL_LISTER = src/utils/list_models.py

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
	@echo "  make download-grado G=X    - Scarica per grado (G=INFANZIA/PRIMARIA/SEC_PRIMO/SEC_SECONDO)"
	@echo "  make download-area A=X     - Scarica per area geografica (A=NORD OVEST/SUD/ISOLE...)"
	@echo "  make download-reset        - Reset stato download e ricomincia"
	@echo ""
	@echo "🤖 ANALISI & REVISIONE:"
	@echo "  make run                   - Esegue analisi sui PDF in ptof_inbox/"
	@echo "  make review-slow           - Revisione lenta con modelli free (usa MODEL=... per cambiare)"
	@echo "  make review-gemini         - Revisione con Google Gemini (usa MODEL=... per cambiare)"
	@echo "  make review-scores         - Revisione punteggi estremi (MODEL=..., LOW=2, HIGH=6, TARGET=...)"
	@echo "  make review-scores-gemini  - Revisione punteggi estremi con Google (MODEL=..., LOW=2, HIGH=6, TARGET=...)"
	@echo "  make review-ollama         - Revisione report con Ollama locale (MODEL=..., OLLAMA_URL=..., CHUNK_SIZE=..., WAIT=..., LIMIT=..., TARGET=...)"
	@echo "  make review-scores-ollama  - Revisione punteggi estremi con Ollama locale (MODEL=..., OLLAMA_URL=..., CHUNK_SIZE=..., LOW=2, HIGH=6, WAIT=..., LIMIT=..., TARGET=...)"
	@echo "  make review-non-ptof       - Rimuove analisi per documenti non-PTOF (TARGET=..., DRY=1)"
	@echo ""
	@echo "🦙 OLLAMA REVIEWERS (chunking, server 192.168.129.14):"
	@echo "  make ollama-score-review   - Revisione score JSON (MODEL=..., TARGET=..., LOW=2, HIGH=6)"
	@echo "  make ollama-report-review  - Arricchimento report MD (MODEL=..., TARGET=..., CHUNK=30000)"
	@echo "  make ollama-review-all     - Esegue entrambi in sequenza"
	@echo ""
	@echo "📬 OUTREACH PTOF:"
	@echo "  make outreach-portal       - Avvia portale upload PTOF (PORT=8502)"
	@echo "  make outreach-email        - Invia email PTOF (BASE_URL=..., LIMIT=..., SEND=1, CSV=\"... ...\")"
	@echo ""
	@echo "🔄 WORKFLOW ANALISI:"
	@echo "  make setup          - Installa le dipendenze"
	@echo "  make run            - Esegue il workflow completo (workflow_notebook.py)"
	@echo "  make run-force      - Forza ri-analisi di tutti i file"
	@echo "  make run-force-code CODE=X - Forza ri-analisi di un codice specifico"
	@echo "  make workflow       - Alias di run (workflow_notebook.py)"
	@echo "  make dashboard      - Avvia la dashboard Streamlit"
	@echo "  make csv            - Rigenera il CSV dai file JSON (rebuild_csv_clean.py)"
	@echo "  make backfill       - Backfill metadati mancanti con scan LLM mirata"
	@echo "  make clean          - Pulisce file temporanei e cache"
	@echo ""
	@echo "📋 REGISTRO ANALISI:"
	@echo "  make registry-status - Mostra stato del registro analisi"
	@echo "  make registry-list   - Lista tutti i file registrati"
	@echo "  make registry-clear  - Pulisce il registro (forza ri-analisi di tutto)"
	@echo ""
	@echo "♻️ RECOVERY PTOF:"
	@echo "  make recover-not-ptof - Recupera solo i PDF con suffisso _ok in ptof_discarded/not_ptof"
	@echo ""
	@echo "🔗 COMBINAZIONI:"
	@echo "  make refresh    - Rigenera CSV e avvia dashboard"
	@echo "  make full       - Esegue run, rigenera CSV e avvia dashboard"
	@echo "  make pipeline   - Download sample + run + csv + dashboard"
	@echo ""
	@echo "🤖 MODELLI AI (PRESET):"
	@echo "  make list-models             - Lista modelli dai preset (config/pipeline_config.json)"
	@$(PYTHON) $(MODEL_LISTER) --config --prefix "   - "
	@echo "🤖 MODELLI AI (OPENROUTER):"
	@echo "  make list-models-openrouter  - Lista modelli OpenRouter (FREE_ONLY=1 per limitare)"
	@$(PYTHON) $(MODEL_LISTER) --openrouter --prefix "   - "
	@echo "🤖 MODELLI AI (GEMINI API):"
	@echo "  make list-models-gemini      - Lista modelli Gemini (richiede GEMINI_API_KEY)"
	@$(PYTHON) $(MODEL_LISTER) --gemini --prefix "   - "
	@echo ""
	@echo "⏰ AUTOMAZIONE:"
	@echo "  make csv-watch             - Rigenera CSV ogni 5 min (INTERVAL=X per cambiare)"
	@echo ""
	@echo "🧭 WIZARD:"
	@echo "  make wizard               - Avvia wizard interattivo per i comandi make"

setup:
	$(PIP) install -r requirements.txt

wizard:
	$(PYTHON) src/utils/make_wizard.py

run:
	$(PYTHON) workflow_notebook.py

run-force:
	$(PYTHON) workflow_notebook.py --force

run-force-code:
ifndef CODE
	@echo "❌ Specificare il codice con CODE=CODICE_MECCANOGRAFICO"
	@echo "   Esempio: make run-force-code CODE=RMIC8GA002"
else
	$(PYTHON) workflow_notebook.py --force-code $(CODE)
endif

workflow: run

dashboard:
	@echo "🛑 Arresto eventuali istanze precedenti..."
	-pkill -f "streamlit run app/Home.py" || true
	@sleep 1
	$(STREAMLIT) run app/Home.py --server.port 8501

csv:
	$(PYTHON) -m src.processing.rebuild_csv_clean
	$(PYTHON) src/processing/geocode_schools.py

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
	$(PYTHON) -m src.processing.slow_reviewer $(if $(MODEL),--model "$(MODEL)",)

# Gemini Review (uso: make review-gemini MODEL=gemini-1.5-pro)
review-gemini:
	$(PYTHON) -m src.processing.gemini_reviewer $(if $(MODEL),--model "$(MODEL)",) $(if $(TARGET),--target "$(TARGET)",) $(if $(LIMIT),--limit $(LIMIT),) $(if $(WAIT),--wait $(WAIT),)

# Ollama Report Review (uso: make review-ollama MODEL=qwen3:32b)
review-ollama:
	$(PYTHON) -m src.processing.ollama_report_reviewer \
		$(if $(MODEL),--model "$(MODEL)",) \
		$(if $(OLLAMA_URL),--ollama-url "$(OLLAMA_URL)",) \
		$(if $(CHUNK_SIZE),--chunk-size $(CHUNK_SIZE),) \
		$(if $(WAIT),--wait $(WAIT),) \
		$(if $(LIMIT),--limit $(LIMIT),) \
		$(if $(TARGET),--target "$(TARGET)",)

# Score Review (uso: make review-scores MODEL=... LOW=2 HIGH=6 TARGET=RMIC8GA002)
review-scores:
	$(PYTHON) -m src.processing.score_reviewer $(if $(MODEL),--model "$(MODEL)",) $(if $(LOW),--low-threshold $(LOW),) $(if $(HIGH),--high-threshold $(HIGH),) $(if $(TARGET),--target "$(TARGET)",) $(if $(WAIT),--wait $(WAIT),) $(if $(LIMIT),--limit $(LIMIT),) $(if $(MAX_CHARS),--max-chars $(MAX_CHARS),)

# Score Review (Gemini) (uso: make review-scores-gemini MODEL=gemini-2.0-flash-exp LOW=2 HIGH=6)
review-scores-gemini:
	$(PYTHON) -m src.processing.score_reviewer --provider gemini $(if $(MODEL),--model "$(MODEL)",) $(if $(LOW),--low-threshold $(LOW),) $(if $(HIGH),--high-threshold $(HIGH),) $(if $(TARGET),--target "$(TARGET)",) $(if $(WAIT),--wait $(WAIT),) $(if $(LIMIT),--limit $(LIMIT),) $(if $(MAX_CHARS),--max-chars $(MAX_CHARS),)

# Score Review (Ollama) (uso: make review-scores-ollama MODEL=qwen3:32b LOW=2 HIGH=6)
review-scores-ollama:
	$(PYTHON) -m src.processing.ollama_score_reviewer \
		$(if $(MODEL),--model "$(MODEL)",) \
		$(if $(OLLAMA_URL),--ollama-url "$(OLLAMA_URL)",) \
		$(if $(CHUNK_SIZE),--chunk-size $(CHUNK_SIZE),) \
		$(if $(LOW),--low-threshold $(LOW),) \
		$(if $(HIGH),--high-threshold $(HIGH),) \
		$(if $(WAIT),--wait $(WAIT),) \
		$(if $(LIMIT),--limit $(LIMIT),) \
		$(if $(TARGET),--target "$(TARGET)",)

# Non-PTOF Review (uso: make review-non-ptof TARGET=RMIC8GA002 DRY=1)
review-non-ptof:
	$(PYTHON) -m src.processing.non_ptof_reviewer $(if $(TARGET),--target "$(TARGET)",) $(if $(DRY),--dry-run,) $(if $(NO_LLM),--no-llm,) $(if $(NO_MOVE),--no-move-pdf,) $(if $(LIMIT),--limit $(LIMIT),)

# ═══════════════════════════════════════════════════════════════════
# OLLAMA REVIEWERS (locale su 192.168.129.14)
# ═══════════════════════════════════════════════════════════════════

# Ollama Score Review (uso: make ollama-score-review MODEL=qwen3:32b TARGET=RMIC8GA002)
ollama-score-review:
	$(PYTHON) -m src.processing.ollama_score_reviewer $(if $(MODEL),--model "$(MODEL)",) $(if $(TARGET),--target "$(TARGET)",) $(if $(LIMIT),--limit $(LIMIT),) $(if $(LOW),--low-threshold $(LOW),) $(if $(HIGH),--high-threshold $(HIGH),) $(if $(CHUNK),--chunk-size $(CHUNK),) $(if $(WAIT),--wait $(WAIT),)

# Ollama Report Review (uso: make ollama-report-review MODEL=qwen3:32b TARGET=RMIC8GA002)
ollama-report-review:
	$(PYTHON) -m src.processing.ollama_report_reviewer $(if $(MODEL),--model "$(MODEL)",) $(if $(TARGET),--target "$(TARGET)",) $(if $(LIMIT),--limit $(LIMIT),) $(if $(CHUNK),--chunk-size $(CHUNK),) $(if $(WAIT),--wait $(WAIT),)

# Esegue entrambi i reviewer Ollama in sequenza
ollama-review-all:
	@echo "🔍 Fase 1: Revisione Score..."
	$(PYTHON) -m src.processing.ollama_score_reviewer $(if $(MODEL),--model "$(MODEL)",) $(if $(TARGET),--target "$(TARGET)",) $(if $(LIMIT),--limit $(LIMIT),)
	@echo ""
	@echo "✨ Fase 2: Arricchimento Report..."
	$(PYTHON) -m src.processing.ollama_report_reviewer $(if $(MODEL),--model "$(MODEL)",) $(if $(TARGET),--target "$(TARGET)",) $(if $(LIMIT),--limit $(LIMIT),)
	@echo ""
	@echo "🏁 Revisione Ollama completata!"

# Watch CSV: rigenera il CSV ogni N secondi (default 300s = 5min)
# Uso: make csv-watch INTERVAL=60
csv-watch:
	@echo "🔄 Avvio watch CSV (intervallo: $(or $(INTERVAL),300)s)..."
	@while true; do \
		make csv; \
		echo "💤 Attesa $(or $(INTERVAL),300)s..."; \
		sleep $(or $(INTERVAL),300); \
	done

# ═══════════════════════════════════════════════════════════════════
# REGISTRO ANALISI
# ═══════════════════════════════════════════════════════════════════

# Mostra statistiche del registro
registry-status:
	$(PYTHON) -m src.utils.analysis_registry --stats

# Lista tutti i file registrati
registry-list:
	$(PYTHON) src/utils/analysis_registry.py --list

# Pulisce il registro (forza ri-analisi di tutto)
registry-clear:
	$(PYTHON) src/utils/analysis_registry.py --clear

# Rimuove una entry specifica (uso: make registry-remove CODE=RMIC8GA002)
registry-remove:
ifndef CODE
	@echo "❌ Specificare il codice con CODE=CODICE_MECCANOGRAFICO"
	@echo "   Esempio: make registry-remove CODE=RMIC8GA002"
else
	$(PYTHON) src/utils/analysis_registry.py --remove $(CODE)
endif

# ═══════════════════════════════════════════════════════════════════
# RECOVERY PTOF
# ═══════════════════════════════════════════════════════════════════

recover-not-ptof:
	$(PYTHON) src/validation/ptof_validator.py recover --category not_ptof --only-ok

# ═══════════════════════════════════════════════════════════════════
# OUTREACH PTOF
# ═══════════════════════════════════════════════════════════════════

outreach-portal:
	$(STREAMLIT) run $(UPLOAD_PORTAL) --server.port $(or $(PORT),8502)

outreach-email:
	$(PYTHON) $(EMAILER) \
		$(if $(BASE_URL),--base-url "$(BASE_URL)",) \
		$(if $(LIMIT),--limit $(LIMIT),) \
		$(if $(SEND),--send,) \
		$(if $(USE_PEC),--use-pec,) \
		$(if $(TEMPLATE),--template "$(TEMPLATE)",) \
		$(if $(SUBJECT),--subject "$(SUBJECT)",) \
		$(if $(SIGNATURE),--signature "$(SIGNATURE)",) \
		$(foreach f,$(CSV),--csv "$(f)")

list-models:
	@$(PYTHON) $(MODEL_LISTER) --config

list-models-openrouter:
	@$(PYTHON) $(MODEL_LISTER) --openrouter $(if $(FREE_ONLY),--free-only,)

list-models-gemini:
	@$(PYTHON) $(MODEL_LISTER) --gemini
