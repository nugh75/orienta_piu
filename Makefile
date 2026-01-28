.PHONY: \
	help setup wizard config config-show \
	run run-force run-force-code workflow workflow-force \
	dashboard csv csv-watch backfill clean \
	logs logs-live \
	refresh full pipeline pipeline-ollama \
	download download-sample download-strato download-statali download-paritarie \
	download-regione download-metro download-non-metro download-grado download-area download-reset download-retry sync-sampling \
	strata-cycle \
	review-report-openrouter review-report-gemini review-report-ollama \
	review-scores-openrouter review-scores-gemini review-scores-ollama \
	review-non-ptof \
	best-practice-extract best-practice-extract-reset best-practice-extract-stats \
	activity-extract activity-extract-reset activity-extract-stats \
	registry-status registry-list registry-clear registry-remove \
	recover-not-ptof \
	outreach-portal outreach-email \
	list-models list-models-openrouter list-models-gemini models models-ollama models-ollama-pull \
	cleanup-dry cleanup cleanup-bak cleanup-bak-old \
	check-truncated fix-truncated list-backups \
	git-auto git-status git-pull git-push git-commit \
	meta-status meta-school meta-regional meta-national meta-thematic meta-next meta-batch \
	docker-up docker-down docker-build docker-logs docker-status docker-shell venv \
	tui web-runner

PYTHON ?= .venv/bin/python
PIP ?= .venv/bin/pip
STREAMLIT = streamlit
DOWNLOADER = src/downloaders/ptof_downloader.py
UPLOAD_PORTAL = src/portal/ptof_upload_portal.py
EMAILER = src/outreach/ptof_emailer.py
EMAILER = src/outreach/ptof_emailer.py
MODEL_LISTER = src/utils/list_models.py
LOG_VIEWER = scripts/log_viewer.py

help:
	@echo "Comandi disponibili:"
	@echo "Guida completa: docs/MAP.md e docs/reference/MAKE_REFERENCE.md"
	@echo ""
	@echo "SETUP E CONFIG:"
	@echo "  make setup                - Installa le dipendenze"
	@echo "  make help                 - Mostra questo elenco"
	@echo "  make wizard               - Wizard interattivo per i comandi make"
	@echo "  make tui                  - Avvia Task Runner TUI (terminale)"
	@echo "  make web-runner PORT=5000 - Avvia Task Runner Web UI"
	@echo "  make config               - Wizard configurazione pipeline (modelli, chunking)"
	@echo "  make config-show          - Mostra configurazione attuale"
	@echo "  make logs                 - Visualizzatore interattivo log (lnav se installato)"
	@echo "  make logs-live            - Segui i log in tempo reale (lnav/multitail/tail)"
	@echo ""
	@echo "DOWNLOAD PTOF:"
	@echo "  make download              - Dry-run: mostra stratificazione senza scaricare"
	@echo "  make download-sample       - Scarica campione stratificato (5 per strato)"
	@echo "  make download-strato N=X   - Scarica X scuole per ogni strato (es: N=20)"
	@echo "  make strata-cycle          - Ciclo incrementale stratificato (target MIUR proporzionale)"
	@echo "                             - Usa MAX_DOWNLOADS=50 per limitare il ciclo"
	@echo "                             - Filtra: G=grado, R=regione, GESTIONE=Statale|Paritaria"
	@echo "  make download-statali      - Scarica tutte le scuole statali"
	@echo "  make download-paritarie    - Scarica tutte le scuole paritarie"
	@echo "  make download-regione R=X  - Scarica scuole di una regione (es: R=LAZIO)"
	@echo "  make download-metro        - Scarica solo province metropolitane"
	@echo "  make download-non-metro    - Scarica solo province NON metropolitane"
	@echo "  make download-grado G=X    - Scarica per grado (G=INFANZIA/PRIMARIA/SEC_PRIMO/SEC_SECONDO)"
	@echo "  make download-area A=X     - Scarica per area geografica (A=NORD OVEST/SUD/ISOLE...)"
	@echo "  make download-retry N=50   - Riprova N download falliti (MIN_ATTEMPTS=1, MAX_ATTEMPTS=10)"
	@echo "  make download-reset        - Reset stato download e ricomincia"
	@echo ""
	@echo "ANALISI E WORKFLOW:"
	@echo "  make run                     - Esegue analisi PTOF (puo coesistere con altri processi)"
	@echo "  make run CONF=1              - Come sopra, ma con wizard configurazione"
	@echo "  make run-force               - Forza ri-analisi di tutti i file"
	@echo "  make run-force-code CODE=X   - Ri-analizza una scuola specifica"
	@echo "  make workflow                - Analisi PTOF pulita (ferma altri processi, una scuola alla volta)"
	@echo "  make workflow CONF=1         - Come sopra, ma con wizard configurazione"
	@echo "  make workflow-force          - Come workflow ma ri-analizza tutto"
	@echo ""
	@echo "REVISIONE:"
	@echo "  make review-report-openrouter - Revisione report con OpenRouter (MODEL=...)"
	@echo "  make review-report-gemini     - Revisione report con Gemini (MODEL=...)"
	@echo "  make review-report-ollama     - Revisione report con Ollama (MODEL=..., OLLAMA_URL=...)"
	@echo "  make review-scores-openrouter - Revisione scores con OpenRouter (MODEL=..., LOW=2, HIGH=6)"
	@echo "  make review-scores-gemini     - Revisione scores con Gemini (MODEL=..., LOW=2, HIGH=6)"
	@echo "  make review-scores-ollama     - Revisione scores con Ollama (MODEL=..., LOW=2, HIGH=6)"
	@echo "  make review-non-ptof          - Rimuove analisi per documenti non-PTOF (TARGET=..., DRY=1)"
	@echo ""
	@echo "DASHBOARD E DATI:"
	@echo "  make dashboard      - Avvia la dashboard Streamlit"
	@echo "  make csv            - Rigenera il CSV dai file JSON (rebuild_csv_clean.py)"
	@echo "  make csv-watch       - Rigenera CSV ogni 5 min (INTERVAL=X per cambiare)"
	@echo "  make backfill       - Backfill metadati mancanti con scan LLM mirata"
	@echo ""
	@echo "CATALOGO ATTIVITÀ (ex buone pratiche):"
	@echo "  make activity-extract            - Estrae attività dai PDF PTOF"
	@echo "                                     Opzioni: PROVIDER=openrouter, MODEL=..., LIMIT=..., MAX_COST=..."
	@echo "  make activity-extract-reset      - Reset e ri-estrazione completa"
	@echo "  make activity-extract-stats      - Mostra statistiche estrazione"
	@echo ""
	@echo "COSTI E CREDITI:"
	@echo "  make report-costs                - Genera report costi API (CSV/MD) in data/"
	@echo "  make check-credits               - Verifica credito residuo OpenRouter"
	@echo ""
	@echo "META REPORT (Best Practices):"
	@echo "  make meta-skeleton DIM=X      - Report tematico skeleton-first (RACCOMANDATO)"
	@echo "                                  Opzioni: REGIONE, ORDINE, PROVIDER_SCHOOL, PROVIDER_SYNTHESIS"
	@echo "  make meta-status              - Stato dei report (pending/current/stale)"
	@echo "  make meta-school CODE=X       - Genera report singola scuola"


	@echo "  make meta-next                - Genera prossimo report pendente"
	@echo "  make meta-batch N=5           - Genera N report pendenti"
	@echo "  Provider: PROVIDER=gemini|openrouter|ollama (default: auto)"
	@echo ""
	@echo "OUTREACH PTOF:"
	@echo "  make outreach-portal       - Avvia portale upload PTOF (PORT=8502)"
	@echo "  make outreach-email        - Invia email PTOF (BASE_URL=..., LIMIT=..., SEND=1, CSV=\"... ...\")"
	@echo ""
	@echo "REGISTRO ANALISI:"
	@echo "  make registry-status - Mostra stato del registro analisi"
	@echo "  make registry-list   - Lista tutti i file registrati"
	@echo "  make registry-clear  - Pulisce il registro (forza ri-analisi di tutto)"
	@echo "  make registry-remove CODE=X - Rimuove una entry specifica"
	@echo ""
	@echo "RECOVERY E MANUTENZIONE:"
	@echo "  make recover-not-ptof - Recupera solo i PDF con suffisso _ok in ptof_discarded/not_ptof"
	@echo "  make check-truncated  - Trova report MD troncati"
	@echo "  make fix-truncated    - Trova troncati e ripristina SOLO quelli dai backup"
	@echo "  make list-backups     - Elenca tutti i file di backup disponibili"
	@echo "  make git-auto         - Add/commit/push ogni 10 min (INTERVAL=600)"
	@echo "  make clean            - Pulisce file temporanei e cache"
	@echo ""
	@echo "COMBINAZIONI:"
	@echo "  make refresh    - Rigenera CSV e avvia dashboard"
	@echo "  make full       - Esegue run, rigenera CSV e avvia dashboard"
	@echo "  make pipeline   - Download sample + run + csv + dashboard"
	@echo "  make pipeline-ollama - Analisi + revisione Ollama (scores+report) + CSV refresh"
	@echo "                         MODEL=X, INTERVAL=300, LOW=2, HIGH=6"
	@echo ""
	@echo "MODELLI AI:"
	@echo "  make models                  - Mostra tutti i modelli disponibili"
	@echo "  make models-ollama           - Lista modelli Ollama scaricati (OLLAMA_HOST=X)"
	@echo "  make models-ollama-pull MODEL=X - Scarica/aggiorna un modello Ollama"
	@echo "  make list-models             - Lista modelli dai preset"
	@echo ""
	@echo "WORKFLOW AVANZATO (Ruoli):"
	@echo "  make workflow ANALYST=gemma3:27b REVIEWER=qwen3:32b REFINER=... SYNTHESIZER=..."
	@echo "  make workflow OLLAMA_URL=http://localhost:11434 MODEL=..."
	@echo ""
	@echo "WORKFLOW IBRIDO (Ollama + Cloud):"
	@echo "  make workflow ANALYST=qwen3:32b PROVIDER_ANALYST=ollama \\"
	@echo "                REFINER=google/gemini-3-pro-preview PROVIDER_REFINER=openrouter \\"
	@echo "                SYNTHESIZER=google/gemini-3-pro-preview PROVIDER_SYNTHESIZER=openrouter"
	@echo ""
	@echo "PULIZIA FILE OBSOLETI:"
	@echo "  make cleanup-dry          - Mostra cosa verrebbe eliminato (dry-run)"
	@echo "  make cleanup              - Elimina file obsoleti (chiede conferma)"
	@echo "  make cleanup-bak          - Elimina obsoleti + file .bak (chiede conferma)"
	@echo "  make cleanup-bak-old DAYS=N - Elimina solo .bak piu vecchi di N giorni (default 7)"
	@echo ""
	@echo "GIT:"
	@echo "  make git-auto             - Add/commit/push automatico ogni 10 min (INTERVAL=600)"
	@echo "  make git-status           - Mostra stato git"
	@echo "  make git-pull             - Pull dal remote"
	@echo "  make git-push             - Push al remote"
	@echo "  make git-commit MSG=\"...\" - Commit con messaggio personalizzato"

setup:
	$(PIP) install -r requirements.txt

wizard:
	$(PYTHON) src/utils/make_wizard.py

# Configurazione pipeline (wizard interattivo)
config:
	$(PYTHON) src/utils/pipeline_wizard.py

# Mostra configurazione corrente
config-show:
	@$(PYTHON) src/utils/pipeline_wizard.py --show

run:
ifdef CONF
	@$(PYTHON) src/utils/pipeline_wizard.py
endif
	$(PYTHON) workflow_notebook.py

run-force:
ifdef CONF
	@$(PYTHON) src/utils/pipeline_wizard.py
endif
	$(PYTHON) workflow_notebook.py --force

run-force-code:
ifndef CODE
	@echo "❌ Specificare il codice con CODE=CODICE_MECCANOGRAFICO"
	@echo "   Esempio: make run-force-code CODE=RMIC8GA002"
else
ifdef CONF
	@$(PYTHON) src/utils/pipeline_wizard.py
endif
	$(PYTHON) workflow_notebook.py --force-code $(CODE)
endif

# Workflow pulito: ferma altri processi e analizza una scuola alla volta
workflow:
ifdef CONF
	@$(PYTHON) src/utils/pipeline_wizard.py
endif
	@echo ""
	@echo "════════════════════════════════════════════════════════════"
	@echo "📋 RIEPILOGO WORKFLOW ANALISI PTOF"
	@echo "════════════════════════════════════════════════════════════"
	@echo "  Provider:      $(or $(PROVIDER),auto)"
	@echo "  Modello:       $(or $(MODEL),default)"
	@echo "  Analyst:       $(or $(ANALYST),default)"
	@echo "  Reviewer:      $(or $(REVIEWER),default)"
	@echo "  Refiner:       $(or $(REFINER),default)"
	@echo "  Synthesizer:   $(or $(SYNTHESIZER),default)"
	@echo "  Ollama URL:    $(or $(OLLAMA_URL),default)"
	@echo "  Preset:        $(or $(PRESET),nessuno)"
	@echo "  Force Code:    $(or $(FORCE_CODE),nessuno)"
	@echo "  Skip Valid.:   $(or $(SKIP_VALIDATION),no)"
	@echo "  Auto-confirm:  $(if $(YES),si,no)"
	@echo "════════════════════════════════════════════════════════════"
	@echo ""
ifndef YES
	@read -p "Procedere con il workflow? [y/N] " confirm && [ "$$confirm" = "y" ] || (echo "❌ Operazione annullata." && exit 1)
endif
	@echo ""
	@echo "🛑 Arresto eventuali processi di analisi in corso..."
	-@pkill -f "workflow_notebook.py" 2>/dev/null || true
	-@pkill -f "ollama_report_reviewer" 2>/dev/null || true
	-@pkill -f "ollama_score_reviewer" 2>/dev/null || true
	@sleep 1
	@echo "🚀 Avvio analisi PTOF (una scuola alla volta)..."
	$(PYTHON) workflow_notebook.py \
		$(if $(MODEL),--model "$(MODEL)",) \
		$(if $(ANALYST),--analyst "$(ANALYST)",) \
		$(if $(REVIEWER),--reviewer "$(REVIEWER)",) \
		$(if $(REFINER),--refiner "$(REFINER)",) \
		$(if $(SYNTHESIZER),--synthesizer "$(SYNTHESIZER)",) \
		$(if $(OLLAMA_URL),--ollama-url "$(OLLAMA_URL)",) \
		$(if $(PROVIDER),--provider "$(PROVIDER)",) \
		$(if $(PROVIDER_ANALYST),--provider-analyst "$(PROVIDER_ANALYST)",) \
		$(if $(PROVIDER_REVIEWER),--provider-reviewer "$(PROVIDER_REVIEWER)",) \
		$(if $(PROVIDER_REFINER),--provider-refiner "$(PROVIDER_REFINER)",) \
		$(if $(PROVIDER_SYNTHESIZER),--provider-synthesizer "$(PROVIDER_SYNTHESIZER)",) \
		$(if $(PRESET),--preset "$(PRESET)",) \
		$(if $(FORCE_CODE),--force-code "$(FORCE_CODE)",) \
		$(if $(SKIP_VALIDATION),--skip-validation,)

workflow-force:
ifdef CONF
	@$(PYTHON) src/utils/pipeline_wizard.py
endif
	@echo "🛑 Arresto eventuali processi di analisi in corso..."
	-@pkill -f "workflow_notebook.py" 2>/dev/null || true
	-@pkill -f "ollama_report_reviewer" 2>/dev/null || true
	-@pkill -f "ollama_score_reviewer" 2>/dev/null || true
	@sleep 1
	@echo "🚀 Avvio analisi PTOF (FORCE - ri-analizza tutto)..."
	$(PYTHON) workflow_notebook.py --force

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

# ═══════════════════════════════════════════════════════════════════
# ESTRAZIONE BUONE PRATICHE DA PDF
# ═══════════════════════════════════════════════════════════════════

# Estrae attività dai PDF originali con Ollama
# Uso: make activity-extract MODEL=qwen3:32b LIMIT=10
activity-extract:
	@echo ""
	@echo "════════════════════════════════════════════════════════════"
	@echo "📋 RIEPILOGO ESTRAZIONE ATTIVITÀ"
	@echo "════════════════════════════════════════════════════════════"
	@echo "  Provider:       $(or $(PROVIDER),auto)"
	@echo "  Modello:        $(or $(MODEL),default)"
	@echo "  Ollama URL:     $(or $(OLLAMA_URL),default)"
	@echo "  Limite scuole:  $(or $(LIMIT),nessuno)"
	@echo "  Attesa (sec):   $(or $(WAIT),default)"
	@echo "  Batch size:     $(or $(BATCH_SIZE),default)"
	@echo "  Batch wait:     $(or $(BATCH_WAIT),default)"
	@echo "  Shard:          $(or $(SHARD),nessuno)"
	@echo "  Max costo:      $(or $(MAX_COST),nessuno)"
	@echo "  Force:          $(if $(FORCE),si,no)"
	@echo "  Target:         $(or $(TARGET),tutti)"
	@echo "  Auto-confirm:   $(if $(YES),si,no)"
	@echo "════════════════════════════════════════════════════════════"
	@echo ""
ifndef YES
	@read -p "Procedere con l'estrazione attività? [y/N] " confirm && [ "$$confirm" = "y" ] || (echo "❌ Operazione annullata." && exit 1)
endif
	@echo ""
	@echo "🌟 Estrazione Attività dai PDF PTOF..."
	$(PYTHON) -m src.agents.activity_extractor \
		$(if $(MODEL),--model "$(MODEL)",) \
		$(if $(OLLAMA_URL),--ollama-url "$(OLLAMA_URL)",) \
		$(if $(LIMIT),--limit $(LIMIT),) \
		$(if $(WAIT),--wait $(WAIT),) \
		$(if $(BATCH_SIZE),--batch-size $(BATCH_SIZE),) \
		$(if $(BATCH_WAIT),--batch-wait $(BATCH_WAIT),) \
		$(if $(PROVIDER),--provider "$(PROVIDER)",) \
		$(if $(SHARD),--shard "$(SHARD)",) \
		$(if $(MAX_COST),--max-cost $(MAX_COST),) \
		$(if $(FORCE),--force,) \
		$(if $(TARGET),--target "$(TARGET)",)
	@echo "✅ Attività salvate in data/attivita.json e data/attivita.csv"

report-costs:
	@echo "💰 Generazione Report Costi API..."
	$(PYTHON) src/utils/cost_reporter.py

# Check crediti OpenRouter (Live API)
check-credits:
	@$(PYTHON) src/utils/check_openrouter_credits.py

# Reset e ri-estrazione completa
activity-extract-reset:
	@echo "🔄 Reset e ri-estrazione attività..."
	rm -f data/activity_registry.json data/attivita.json data/attivita.csv
	$(PYTHON) -m src.agents.activity_extractor --force \
		$(if $(MODEL),--model "$(MODEL)",) \
		$(if $(OLLAMA_URL),--ollama-url "$(OLLAMA_URL)",)
	@echo "✅ Ri-estrazione completata"

# Statistiche estrazione
activity-extract-stats:
	@if [ -f data/attivita.json ]; then \
		$(PYTHON) -c "import json; \
d=json.load(open('data/attivita.json')); \
total=d.get('total_activities', d.get('total_practices', 0)); \
print('📊 Statistiche Attività'); \
print(f'   Attività totali: {total}'); \
print(f'   Scuole processate: {d.get(\"schools_processed\", 0)}'); \
print(f'   Modello: {d.get(\"extraction_model\", \"N/D\")}'); \
print(f'   Ultimo aggiornamento: {d.get(\"last_updated\", \"N/D\")[:19]}')"; \
	else \
		echo "❌ File data/attivita.json non trovato. Esegui prima: make activity-extract"; \
	fi

# Backfill temi mancanti usando LLM (uso: make activity-theme-backfill)
activity-theme-backfill:
	@echo "🎯 Backfill temi mancanti in attivita.csv..."
	$(PYTHON) -m src.processing.theme_backfill \
		$(if $(MODEL),--model "$(MODEL)",) \
		$(if $(OLLAMA_URL),--ollama-url "$(OLLAMA_URL)",) \
		$(if $(LIMIT),--limit $(LIMIT),) \
		$(if $(DRY),--dry-run,)
	@echo "✅ Backfill completato"

# Alias retrocompatibili
best-practice-extract: activity-extract
	@echo "ℹ️  Alias: usa make activity-extract"

best-practice-extract-reset: activity-extract-reset
	@echo "ℹ️  Alias: usa make activity-extract-reset"

best-practice-extract-stats: activity-extract-stats
	@echo "ℹ️  Alias: usa make activity-extract-stats"

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Combinazioni
refresh: csv dashboard

full: run csv dashboard

pipeline: download-sample run csv dashboard

# Pipeline completa: analisi + revisione Ollama (scores + report) + refresh periodico CSV
# Uso: make pipeline-ollama MODEL=qwen3:32b INTERVAL=300
# - Avvia analisi PTOF in background
# - Avvia revisione scores Ollama in background
# - Avvia revisione report MD Ollama in background
# - Ogni INTERVAL secondi (default 300 = 5min) rigenera CSV
pipeline-ollama:
	@echo "🚀 Avvio pipeline completa (analisi + revisione Ollama scores/report + CSV refresh)"
	@echo "   Modello: $(or $(MODEL),qwen3:32b)"
	@echo "   Intervallo refresh: $(or $(INTERVAL),300)s"
	@echo ""
	@echo "📊 Avvio analisi PTOF..."
	@$(PYTHON) workflow_notebook.py &
	@echo "🎯 Avvio revisione scores Ollama..."
	@$(PYTHON) -m src.processing.ollama_score_reviewer --model "$(or $(MODEL),qwen3:32b)" $(if $(OLLAMA_URL),--ollama-url "$(OLLAMA_URL)",) $(if $(LOW),--low-threshold $(LOW),) $(if $(HIGH),--high-threshold $(HIGH),) &
	@echo "📝 Avvio revisione report MD Ollama..."
	@$(PYTHON) -m src.processing.ollama_report_reviewer --model "$(or $(MODEL),qwen3:32b)" $(if $(OLLAMA_URL),--ollama-url "$(OLLAMA_URL)",) $(if $(CHUNK_SIZE),--chunk-size $(CHUNK_SIZE),) &
	@echo ""
	@echo "✅ Tutti i processi avviati in parallelo!"
	@echo "💡 Usa 'make csv' per aggiornare il CSV quando vuoi"
	@echo "💡 Usa 'ps aux | grep python' per vedere i processi attivi"

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

# Ciclo incrementale stratificato (target proporzionale MIUR)
TARGET_TOTAL ?= 6000
TARGET_STEP ?= 300
STRATO_STEP ?= 3
SEED ?= 42
MAX_CYCLES ?= 1
YIELD_GLOBAL ?= 0.6
MAX_DOWNLOADS ?=
SKIP_ANALYSIS ?= 0
SKIP_DOWNLOAD ?= 0
# Parametri Workflow (Analisi)
PROVIDER_WORKFLOW ?=
MODEL_WORKFLOW ?=
OLLAMA_URL ?= $(shell grep -s '^OLLAMA_HOST=' .env | cut -d'=' -f2 || echo "http://localhost:11434")
ANALYST_WORKFLOW ?=
REVIEWER_WORKFLOW ?=
REFINER_WORKFLOW ?=
SYNTHESIZER_WORKFLOW ?=
# Parametri Attività
WITH_ACTIVITY ?= 0
PROVIDER_ACTIVITY ?=
MODEL_ACTIVITY ?=
MAX_COST_ACTIVITY ?=

strata-cycle:
	@echo ""
	@echo "════════════════════════════════════════════════════════════"
	@echo "📋 RIEPILOGO CICLO STRATIFICATO"
	@echo "════════════════════════════════════════════════════════════"
	@echo ""
	@echo "  --- DOWNLOAD ---"
	@echo "  Target totale:    $(TARGET_TOTAL)"
	@echo "  Target per step:  $(TARGET_STEP)"
	@echo "  Per strato step:  $(STRATO_STEP)"
	@echo "  Yield globale:    $(YIELD_GLOBAL)"
	@echo "  Max cicli:        $(MAX_CYCLES)"
	@echo "  Max downloads:    $(or $(MAX_DOWNLOADS),illimitato)"
	@echo "  Seed:             $(SEED)"
	@echo "  Filtro grado:     $(or $(G),tutti)"
	@echo "  Filtro regione:   $(or $(R),tutte)"
	@echo "  Filtro gestione:  $(or $(GESTIONE),tutte)"
	@echo ""
	@echo "  --- ANALISI (Workflow) ---"
	@echo "  Skip analisi:     $(if $(filter 1,$(SKIP_ANALYSIS)),si,no)"
	@echo "  Skip download:    $(if $(filter 1,$(SKIP_DOWNLOAD)),si,no)"
	@echo "  Provider:         $(or $(PROVIDER_WORKFLOW),auto)"
	@echo "  Ollama URL:       $(or $(OLLAMA_URL),http://localhost:11434)"
	@echo "  Modello:          $(or $(MODEL_WORKFLOW),default)"
	@echo "  Analyst:          $(or $(ANALYST_WORKFLOW),default)"
	@echo "  Reviewer:         $(or $(REVIEWER_WORKFLOW),default)"
	@echo "  Refiner:          $(or $(REFINER_WORKFLOW),default)"
	@echo "  Synthesizer:      $(or $(SYNTHESIZER_WORKFLOW),default)"
	@echo ""
	@echo "  --- ESTRAZIONE ATTIVITÀ ---"
	@echo "  Esegui attività:  $(if $(filter 1,$(WITH_ACTIVITY)),si,no)"
	@echo "  Provider:         $(or $(PROVIDER_ACTIVITY),auto)"
	@echo "  Ollama URL:       $(or $(OLLAMA_URL),http://localhost:11434)"
	@echo "  Modello:          $(or $(MODEL_ACTIVITY),default)"
	@echo "  Max costo:        $(or $(MAX_COST_ACTIVITY),nessuno)"
	@echo "  Auto-confirm:     $(if $(YES),si,no)"
	@echo ""
	@echo "════════════════════════════════════════════════════════════"
	@echo ""
	@echo "════════════════════════════════════════════════════════════"
	@echo ""
ifneq ($(YES),1)
	@read -p "Procedere con il ciclo stratificato? [y/N] " confirm && [ "$$confirm" = "y" ] || (echo "❌ Operazione annullata." && exit 1)
endif
	@echo ""
	$(PYTHON) -m src.processing.strata_cycle \
		--target-total $(TARGET_TOTAL) \
		--target-step $(TARGET_STEP) \
		--per-strato-step $(STRATO_STEP) \
		--yield-global $(YIELD_GLOBAL) \
		--max-cycles $(MAX_CYCLES) \
		$(if $(MAX_DOWNLOADS),--max-downloads $(MAX_DOWNLOADS),) \
		--seed $(SEED) \
		$(if $(filter 1,$(SKIP_ANALYSIS)),--skip-analysis,) \
		$(if $(filter 1,$(SKIP_DOWNLOAD)),--skip-download,) \
		$(if $(G),--grado "$(G)",) \
		$(if $(R),--regione "$(R)",) \
		$(if $(GESTIONE),--gestione "$(GESTIONE)",) \
		$(if $(PROVIDER_WORKFLOW),--provider-workflow "$(PROVIDER_WORKFLOW)",) \
		$(if $(MODEL_WORKFLOW),--model-workflow "$(MODEL_WORKFLOW)",) \
		$(if $(OLLAMA_URL),--ollama-url "$(OLLAMA_URL)",) \
		$(if $(ANALYST_WORKFLOW),--analyst "$(ANALYST_WORKFLOW)",) \
		$(if $(REVIEWER_WORKFLOW),--reviewer "$(REVIEWER_WORKFLOW)",) \
		$(if $(REFINER_WORKFLOW),--refiner "$(REFINER_WORKFLOW)",) \
		$(if $(SYNTHESIZER_WORKFLOW),--synthesizer "$(SYNTHESIZER_WORKFLOW)",) \
		$(if $(filter 1,$(WITH_ACTIVITY)),--with-activity,) \
		$(if $(PROVIDER_ACTIVITY),--provider-activity "$(PROVIDER_ACTIVITY)",) \
		$(if $(MODEL_ACTIVITY),--model-activity "$(MODEL_ACTIVITY)",) \
		$(if $(MAX_COST_ACTIVITY),--max-cost-activity $(MAX_COST_ACTIVITY),)

# Riprova download falliti
# Uso: make download-retry N=50 MIN_ATTEMPTS=1 MAX_ATTEMPTS=5
download-retry:
	@echo ""
	@echo "════════════════════════════════════════════════════════════"
	@echo "🔄 RETRY DOWNLOAD FALLITI"
	@echo "════════════════════════════════════════════════════════════"
	@echo "  Scuole da riprovare: $(or $(N),50)"
	@echo "  Min tentativi:       $(or $(MIN_ATTEMPTS),1)"
	@echo "  Max tentativi:       $(or $(MAX_ATTEMPTS),10)"
	@echo "════════════════════════════════════════════════════════════"
	@echo ""
	$(PYTHON) $(DOWNLOADER) \
		--retry-failed $(or $(N),50) \
		--retry-min-attempts $(or $(MIN_ATTEMPTS),1) \
		--retry-max-attempts $(or $(MAX_ATTEMPTS),10) \
		$(if $(DRY),--dry-run,)

# Sincronizza dati campionamento con download effettivi
# Uso: make sync-sampling [DRY=1]
sync-sampling:
	@echo "🔄 Sincronizzazione dati campionamento..."
	$(PYTHON) -m src.processing.sync_sampling $(if $(DRY),--dry-run,)

# Reset stato download e ricomincia
download-reset:
	rm -f data/download_state.json
	@echo "Stato download resettato."

# ═══════════════════════════════════════════════════════════════════
# REVISIONE REPORT (arricchimento MD)
# ═══════════════════════════════════════════════════════════════════

# Report Review con OpenRouter (uso: make review-report-openrouter MODEL=google/gemini-2.0-flash-exp:free)
review-report-openrouter:
	$(PYTHON) -m src.processing.slow_reviewer $(if $(MODEL),--model "$(MODEL)",) $(if $(TARGET),--target "$(TARGET)",) $(if $(LIMIT),--limit $(LIMIT),) $(if $(WAIT),--wait $(WAIT),)

# Report Review con Gemini (uso: make review-report-gemini MODEL=gemini-1.5-pro)
review-report-gemini:
	$(PYTHON) -m src.processing.gemini_reviewer $(if $(MODEL),--model "$(MODEL)",) $(if $(TARGET),--target "$(TARGET)",) $(if $(LIMIT),--limit $(LIMIT),) $(if $(WAIT),--wait $(WAIT),)

# Report Review con Ollama (uso: make review-report-ollama MODEL=qwen3:32b)
review-report-ollama:
	$(PYTHON) -m src.processing.ollama_report_reviewer \
		$(if $(MODEL),--model "$(MODEL)",) \
		$(if $(OLLAMA_URL),--ollama-url "$(OLLAMA_URL)",) \
		$(if $(CHUNK_SIZE),--chunk-size $(CHUNK_SIZE),) \
		$(if $(WAIT),--wait $(WAIT),) \
		$(if $(LIMIT),--limit $(LIMIT),) \
		$(if $(TARGET),--target "$(TARGET)",)

# ═══════════════════════════════════════════════════════════════════
# REVISIONE SCORES (punteggi estremi JSON)
# ═══════════════════════════════════════════════════════════════════

# Score Review con OpenRouter (uso: make review-scores-openrouter MODEL=... LOW=2 HIGH=6)
review-scores-openrouter:
	$(PYTHON) -m src.processing.score_reviewer --provider openrouter $(if $(MODEL),--model "$(MODEL)",) $(if $(LOW),--low-threshold $(LOW),) $(if $(HIGH),--high-threshold $(HIGH),) $(if $(TARGET),--target "$(TARGET)",) $(if $(WAIT),--wait $(WAIT),) $(if $(LIMIT),--limit $(LIMIT),) $(if $(MAX_CHARS),--max-chars $(MAX_CHARS),)

# Score Review con Gemini (uso: make review-scores-gemini MODEL=gemini-2.0-flash-exp LOW=2 HIGH=6)
review-scores-gemini:
	$(PYTHON) -m src.processing.score_reviewer --provider gemini $(if $(MODEL),--model "$(MODEL)",) $(if $(LOW),--low-threshold $(LOW),) $(if $(HIGH),--high-threshold $(HIGH),) $(if $(TARGET),--target "$(TARGET)",) $(if $(WAIT),--wait $(WAIT),) $(if $(LIMIT),--limit $(LIMIT),) $(if $(MAX_CHARS),--max-chars $(MAX_CHARS),)

# Score Review con Ollama (uso: make review-scores-ollama MODEL=qwen3:32b LOW=2 HIGH=6)
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
	$(PYTHON) -m src.processing.non_ptof_reviewer $(if $(TARGET),--target "$(TARGET)",) $(if $(DRY),--dry-run,) $(if $(NO_LLM),--no-llm,) $(if $(NO_MOVE),--no-move-pdf,) $(if $(LIMIT),--limit $(LIMIT),) $(if $(MAX_SCORE),--max-score $(MAX_SCORE),)

# Watch CSV: rigenera il CSV ogni N secondi (default 300s = 5min)
# Uso: make csv-watch INTERVAL=60
csv-watch:
	@echo "🔄 Avvio watch CSV (intervallo: $(or $(INTERVAL),300)s)..."
	@while true; do \
		make csv; \
		echo "💤 Attesa $(or $(INTERVAL),300)s..."; \
		sleep $(or $(INTERVAL),300); \
	done

# Git auto: add/commit/push ogni N secondi (default 600s = 10min)
# Uso: make git-auto INTERVAL=600
git-auto:
	@echo "🔄 Avvio auto Git (intervallo: $(or $(INTERVAL),600)s)..."
	@while true; do \
		git add -A; \
		if git diff --cached --quiet; then \
			echo "✅ Nessuna modifica da committare"; \
		else \
			TS=$$(date "+%Y-%m-%d %H:%M"); \
			echo "📦 Commit automatico: $$TS"; \
			git commit -m "Auto update $$TS" && git push; \
		fi; \
		echo "💤 Attesa $(or $(INTERVAL),600)s..."; \
		sleep $(or $(INTERVAL),600); \
	done

# Mostra stato git
git-status:
	@git status

# Pull dal remote
git-pull:
	@git pull

# Push al remote
git-push:
	@git push

# Commit con messaggio (uso: make git-commit MSG="fix bug")
git-commit:
ifndef MSG
	@echo "❌ Specificare il messaggio con MSG=\"...\""
	@echo "   Esempio: make git-commit MSG=\"fix: risolto bug login\""
else
	@git add -A
	@git commit -m "$(MSG)"
	@echo "✅ Commit creato. Usa 'make git-push' per pushare."
endif

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

# ═══════════════════════════════════════════════════════════════════
# VALIDAZIONE PTOF
# ═══════════════════════════════════════════════════════════════════

# Esegue validazione batch sui PDF nella inbox (o altra directory)
# Uso: make validator [DIR=ptof_inbox] [MOVE=1] [IGNORE_REGISTRY=0]
validator:
	@echo ""
	@echo "════════════════════════════════════════════════════════════"
	@echo "🔍 VALIDAZIONE PTOF"
	@echo "════════════════════════════════════════════════════════════"
	@echo "  Directory: $(or $(DIR),ptof_inbox)"
	@echo "  Sposta invalidi: $(if $(filter 0 no No false False,$(MOVE)),no,si)"
	@echo "  Usa registro: $(if $(filter 1 si Si true True,$(IGNORE_REGISTRY)),no,si)"
	@echo "  Forza LLM: $(if $(filter 1 si Si Sì true True,$(FORCE_LLM)),si,no) (input: '$(FORCE_LLM)')"
	@echo "  Controlla duplicati: $(if $(filter 0 no No false False,$(CHECK_DUPLICATES)),no,si)"
	@echo "════════════════════════════════════════════════════════════"
	@echo ""
	$(PYTHON) src/validation/ptof_validator.py validate-batch "$(or $(DIR),ptof_inbox)" \
		$(if $(filter 0 no No false False,$(MOVE)),--no-move,) \
		$(if $(filter 1 si Si true True,$(IGNORE_REGISTRY)),--no-registry,) \
		$(if $(filter 1 si Si Sì true True,$(FORCE_LLM)),--force-llm,) \
		$(if $(filter 0 no No false False,$(CHECK_DUPLICATES)),--no-duplicates,)

validate: validator

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

# Mostra TUTTI i modelli disponibili in un unico comando
models:
	@echo ""
	@echo "════════════════════════════════════════════════════════════"
	@echo "🤖 MODELLI AI DISPONIBILI"
	@echo "════════════════════════════════════════════════════════════"
	@echo ""
	@echo "📝 PRESET (config/pipeline_config.json):"
	@$(PYTHON) $(MODEL_LISTER) --config --prefix "   "
	@echo ""
	@echo "🌐 OPENROUTER (modelli free):"
	@$(PYTHON) $(MODEL_LISTER) --openrouter --free-only --prefix "   "
	@echo ""
	@echo "✨ GEMINI (Google AI - da API):"
	@$(PYTHON) $(MODEL_LISTER) --gemini --prefix "   "
	@echo ""
	@echo "🚀 GEMINI GENERAZIONE 3 (Dicembre 2025):"
	@echo "   gemini-3-flash-preview     ← Latest, advanced reasoning, low latency"
	@echo "   gemini-3-pro-preview       ← Top tier, complex tasks"
	@echo ""
	@echo "⭐ GEMINI 2.5 (Stabili):"
	@echo "   gemini-2.5-flash           ← Bilanciato velocità/qualità (DEFAULT)"
	@echo "   gemini-2.5-pro             ← 2M token context, production"
	@echo "   gemini-2.5-flash-lite-preview ← Ultra-light, high throughput"
	@echo ""
	@echo "🦙 OLLAMA (locale):"
	@echo "   Usa 'make models-ollama' per vedere i modelli scaricati"
	@echo ""

# Lista modelli Ollama scaricati (via curl)
OLLAMA_HOST ?= 192.168.129.14
OLLAMA_PORT ?= 11434

models-ollama:
	@echo ""
	@echo "🦙 MODELLI OLLAMA SCARICATI ($(OLLAMA_HOST):$(OLLAMA_PORT))"
	@echo "════════════════════════════════════════════════════════════"
	@curl -s http://$(OLLAMA_HOST):$(OLLAMA_PORT)/api/tags 2>/dev/null | \
		python3 -c "import sys,json; \
		data=json.load(sys.stdin); \
		models=data.get('models',[]); \
		print(f'\n  Totale: {len(models)} modelli\n') if models else print('\n  ⚠️ Nessun modello o Ollama non raggiungibile\n'); \
		[print(f\"  • {m['name']:30} {m['size']/1e9:.1f}GB\") for m in sorted(models, key=lambda x: x['name'])]" \
		2>/dev/null || echo "  ⚠️ Impossibile connettersi a Ollama ($(OLLAMA_HOST):$(OLLAMA_PORT))"
	@echo ""

# Aggiorna/pull un modello Ollama
models-ollama-pull:
ifndef MODEL
	@echo "❌ Specificare il modello con MODEL=nome_modello"
	@echo "   Esempio: make models-ollama-pull MODEL=gemma3:27b"
	@echo ""
	@echo "   Modelli consigliati:"
	@echo "   - gemma3:27b     (analisi PTOF)"
	@echo "   - qwen3:32b      (review critico)"
	@echo "   - llama3.3:70b   (alta qualità)"
	@echo "   - deepseek-r1:32b (ragionamento)"
else
	@echo "📥 Pulling $(MODEL) da Ollama..."
	@curl -X POST http://$(OLLAMA_HOST):$(OLLAMA_PORT)/api/pull \
		-H "Content-Type: application/json" \
		-d '{"name": "$(MODEL)"}' 2>/dev/null | \
		python3 -c "import sys,json; \
		[print(json.loads(line).get('status','')) for line in sys.stdin if line.strip()]" \
		|| echo "  ⚠️ Errore durante il pull"
	@echo ""
endif

# ═══════════════════════════════════════════════════════════════════
# PULIZIA FILE OBSOLETI
# ═══════════════════════════════════════════════════════════════════

# Mostra cosa verrebbe eliminato (dry-run)
cleanup-dry:
	$(PYTHON) cleanup_obsolete.py --dry-run

# Elimina file obsoleti (chiede conferma)
cleanup:
	$(PYTHON) cleanup_obsolete.py

# Elimina file obsoleti inclusi .bak (chiede conferma)
cleanup-bak:
	$(PYTHON) cleanup_obsolete.py --include-bak

# Elimina solo file .bak più vecchi di N giorni (uso: make cleanup-bak-old DAYS=7)
cleanup-bak-old:
	$(PYTHON) cleanup_obsolete.py --bak-only --older-than $(or $(DAYS),7) --force

# ═══════════════════════════════════════════════════════════════════
# MANUTENZIONE REPORT
# ═══════════════════════════════════════════════════════════════════

# Trova report MD troncati
check-truncated:
	@$(PYTHON) src/utils/check_truncated.py

# Trova e ripristina SOLO i report troncati dai backup (.bak)
fix-truncated:
	@$(PYTHON) src/utils/restore_from_backup.py

# Elenca tutti i file di backup disponibili
list-backups:
	@echo "📦 File .bak in analysis_results/:"
	@ls -la analysis_results/*.bak 2>/dev/null | wc -l | xargs -I {} echo "   Totale: {} file"
	@ls analysis_results/*.bak 2>/dev/null | head -20 || echo "   (nessun backup trovato)"

# ═══════════════════════════════════════════════════════════════════
# LOGS & DEBUGGING
# ═══════════════════════════════════════════════════════════════════

# Visualizzatore log interattivo (uso: make logs [LINES=50])
logs:
	@if command -v lnav >/dev/null 2>&1; then \
		echo "🔎 Aprendo lnav su logs/ (q per uscire)"; \
		lnav logs; \
	else \
		$(PYTHON) $(LOG_VIEWER) $(if $(LINES),--lines $(LINES),); \
	fi

# Visualizzazione live multi-log (lnav > multitail > tail -F)
logs-live:
	@if command -v lnav >/dev/null 2>&1; then \
		echo "🔎 Aprendo lnav su logs/ (q per uscire)"; \
		lnav logs; \
	elif command -v multitail >/dev/null 2>&1; then \
		echo "🔎 Aprendo multitail su log principali (q per uscire)"; \
		multitail logs/analysis_debug.log logs/dashboard_run.log logs/activity_extractor.log; \
	else \
		echo "ℹ️ lnav/multitail non trovati: fallback su tail -F logs/*.log (Ctrl+C per uscire)"; \
		tail -F logs/*.log; \
	fi

# ═══════════════════════════════════════════════════════════════════
# META REPORT - Best Practices Reports
# ═══════════════════════════════════════════════════════════════════

META_CLI = src/agents/meta_report/cli.py

# Mostra stato dei report
meta-status:
	@$(PYTHON) $(META_CLI) status

# Report singola scuola (uso: make meta-school CODE=RMIS001 PROVIDER=gemini)
meta-school:
ifndef CODE
	@echo "❌ Specificare il codice con CODE=CODICE_MECCANOGRAFICO"
	@echo "   Esempio: make meta-school CODE=RMIS001"
	@echo "   Opzioni: PROVIDER=gemini|openrouter|ollama FORCE=1 REFINE=1"
	@echo "   Prompt: PROMPT=overview|innovative|comparative|impact|operational"
else
	$(PYTHON) $(META_CLI) school --code $(CODE) \
		$(if $(PROVIDER),--provider $(PROVIDER),) \
		$(if $(FORCE),--force,) \
		$(if $(PROMPT),--prompt-profile "$(PROMPT)",) \
		$(if $(REFINE),--refine,)
endif



# Genera prossimo report pendente
meta-next:
	$(PYTHON) $(META_CLI) next \
		$(if $(PROVIDER),--provider $(PROVIDER),)

# Genera N report pendenti (uso: make meta-batch N=10)
meta-batch:
	$(PYTHON) $(META_CLI) batch \
		--count $(or $(N),5) \
		$(if $(PROVIDER),--provider $(PROVIDER),)

# Raffina formattazione report (uso: make meta-refine REPORT=path/to/report.md)
meta-refine:
ifeq ($(REPORT),)
	@echo "❌ Specificare il report con REPORT=path/to/report.md"
	@echo "   Esempio: make meta-refine REPORT=reports/meta/thematic/example.md"
	@echo "   Opzioni: PROVIDER=gemini|openrouter|ollama DRY_RUN=1"
else
	$(PYTHON) -m src.agents.meta_report.refine $(REPORT) \
		$(if $(PROVIDER),--provider $(PROVIDER),) \
		$(if $(DRY_RUN),--dry-run,)
endif

# === SKELETON-FIRST ARCHITECTURE ===
# Genera report con architettura skeleton-first e dual provider
# Variabili: PROVIDER_SCHOOL (ollama), PROVIDER_SYNTHESIS (openrouter)
#            MODEL_SCHOOL (gemma3:27b), MODEL_SYNTHESIS (google/gemini-2.0-flash-lite-001)
PROVIDER_SCHOOL ?= ollama
PROVIDER_SYNTHESIS ?= openrouter
MODEL_SCHOOL ?= 
MODEL_SYNTHESIS ?= 

meta-skeleton:
ifndef DIM
	@echo "❌ Specificare la dimensione con DIM=NOME"
	@echo ""
	@echo "   Uso: make meta-skeleton DIM=orientamento REGIONE=Marche ORDINE='II Grado'"
	@echo ""
	@echo "   PROVIDER (dual mode):"
	@echo "     PROVIDER_SCHOOL=ollama         - Per analisi singole scuole (default: ollama)"
	@echo "     PROVIDER_SYNTHESIS=openrouter  - Per sintesi e conclusioni (default: openrouter)"
	@echo "     MODEL_SCHOOL=gemma3:27b        - Modello per scuole"
	@echo "     MODEL_SYNTHESIS=google/gemini-2.0-flash-lite-001  - Modello per sintesi"
	@echo ""
	@echo "   Filtri: REGIONE=... ORDINE=... TIPO=... PROVINCIA=... etc."
else
	$(PYTHON) $(META_CLI) skeleton --dim $(DIM) \
		--provider-school $(PROVIDER_SCHOOL) \
		--provider-synthesis $(PROVIDER_SYNTHESIS) \
		$(if $(MODEL_SCHOOL),--model-school "$(MODEL_SCHOOL)",) \
		$(if $(MODEL_SYNTHESIS),--model-synthesis "$(MODEL_SYNTHESIS)",) \
		$(if $(REGIONE),--region "$(REGIONE)",) \
		$(if $(TIPO),--tipo-scuola "$(TIPO)",) \
		$(if $(ORDINE),--ordine-grado "$(ORDINE)",) \
		$(if $(PROVINCIA),--provincia "$(PROVINCIA)",) \
		$(if $(AREA),--area-geografica "$(AREA)",) \
		$(if $(STATO),--statale-paritaria "$(STATO)",) \
		$(if $(TERRITORIO),--territorio "$(TERRITORIO)",) \
		$(if $(FORCE),--force,)
endif


# ===== DOCKER (solo dashboard) =====

## Avvia dashboard Docker
docker-up:
	docker compose up -d

## Ferma dashboard Docker
docker-down:
	docker compose down

## Ricostruisci immagine Docker
docker-build:
	docker compose build --no-cache

## Log dashboard Docker
docker-logs:
	docker compose logs -f dashboard

## Stato container Docker
docker-status:
	docker compose ps

## Shell nel container Docker
docker-shell:
	docker exec -it orienta-dashboard /bin/bash

## Rimuove i PTOF duplicati (basandosi sull'hash) spostandoli in ptof_discarded
remove-duplicates:
	@echo "🧹 Pulizia duplicati in ptof_inbox..."
	$(PYTHON) -m src.validation.ptof_validator validate-batch ptof_inbox
	@echo "🧹 Pulizia duplicati in ptof_processed..."
	$(PYTHON) -m src.validation.ptof_validator validate-batch ptof_processed

# ===== SETUP LOCALE =====

## Crea virtual environment
venv:
	python3 -m venv .venv
	@echo "Attiva con: source .venv/bin/activate"
	@echo "Poi esegui: make setup"

# ═══════════════════════════════════════════════════════════════════
# TASK RUNNER (TUI + Web)
# ═══════════════════════════════════════════════════════════════════

## TUI - Interfaccia terminale con Textual
tui:
	@echo "🖥️  Avvio Task Runner TUI..."
	$(PYTHON) -m src.taskrunner.tui

## Web Runner - Interfaccia web con Flask + SSE
web-runner:
	@echo "🌐 Avvio Task Runner Web UI..."
	@echo "   URL: http://localhost:$(or $(PORT),5000)"
	@-fuser -k $(or $(PORT),5000)/tcp 2>/dev/null || true
	@sleep 0.5
	$(PYTHON) -m src.taskrunner.web --port $(or $(PORT),5000)
