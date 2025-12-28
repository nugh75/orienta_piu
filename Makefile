.PHONY: \
	help setup wizard config config-show \
	run run-force run-force-code workflow workflow-force \
	dashboard csv csv-watch backfill clean \
	refresh full pipeline pipeline-ollama \
	download download-sample download-strato download-statali download-paritarie \
	download-regione download-metro download-non-metro download-grado download-area download-reset \
	review-report-openrouter review-report-gemini review-report-ollama \
	review-scores-openrouter review-scores-gemini review-scores-ollama \
	review-non-ptof \
	best-practice-extract best-practice-extract-reset best-practice-extract-stats \
	registry-status registry-list registry-clear registry-remove \
	recover-not-ptof \
	outreach-portal outreach-email \
	list-models list-models-openrouter list-models-gemini models models-ollama models-ollama-pull \
	cleanup-dry cleanup cleanup-bak cleanup-bak-old \
	check-truncated fix-truncated list-backups \
	meta-status meta-school meta-regional meta-national meta-thematic meta-next meta-batch

PYTHON = .venv/bin/python
PIP = .venv/bin/pip
STREAMLIT = streamlit
DOWNLOADER = src/downloaders/ptof_downloader.py
UPLOAD_PORTAL = src/portal/ptof_upload_portal.py
EMAILER = src/outreach/ptof_emailer.py
MODEL_LISTER = src/utils/list_models.py

help:
	@echo "Comandi disponibili:"
	@echo "Guida completa: docs/MAP.md e docs/reference/MAKE_REFERENCE.md"
	@echo ""
	@echo "SETUP E CONFIG:"
	@echo "  make setup                - Installa le dipendenze"
	@echo "  make help                 - Mostra questo elenco"
	@echo "  make wizard               - Wizard interattivo per i comandi make"
	@echo "  make config               - Wizard configurazione pipeline (modelli, chunking)"
	@echo "  make config-show          - Mostra configurazione attuale"
	@echo ""
	@echo "DOWNLOAD PTOF:"
	@echo "  make download              - Dry-run: mostra stratificazione senza scaricare"
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
	@echo "CATALOGO BUONE PRATICHE:"
	@echo "  make best-practice-extract       - Estrae buone pratiche dai PDF PTOF"
	@echo "                                     MODEL=X, OLLAMA_URL=X, LIMIT=N, FORCE=1"
	@echo "  make best-practice-extract-reset - Reset e ri-estrazione completa"
	@echo "  make best-practice-extract-stats - Mostra statistiche estrazione"
	@echo ""
	@echo "META REPORT (Best Practices):"
	@echo "  make meta-status              - Stato dei report (pending/current/stale)"
	@echo "  make meta-school CODE=X       - Genera report singola scuola"
	@echo "  make meta-regional REGION=X   - Genera report regionale"
	@echo "  make meta-national            - Genera report nazionale"
	@echo "  make meta-thematic DIM=X      - Genera report tematico (governance, didattica...)"
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
	@echo "  make list-models-openrouter  - Lista modelli OpenRouter (FREE_ONLY=1 per limitare)"
	@echo "  make list-models-gemini      - Lista modelli Gemini (richiede GEMINI_API_KEY)"
	@echo ""
	@echo "PULIZIA FILE OBSOLETI:"
	@echo "  make cleanup-dry          - Mostra cosa verrebbe eliminato (dry-run)"
	@echo "  make cleanup              - Elimina file obsoleti (chiede conferma)"
	@echo "  make cleanup-bak          - Elimina obsoleti + file .bak (chiede conferma)"
	@echo "  make cleanup-bak-old DAYS=N - Elimina solo .bak piu vecchi di N giorni (default 7)"

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
	@echo "🛑 Arresto eventuali processi di analisi in corso..."
	-@pkill -f "workflow_notebook.py" 2>/dev/null || true
	-@pkill -f "ollama_report_reviewer" 2>/dev/null || true
	-@pkill -f "ollama_score_reviewer" 2>/dev/null || true
	@sleep 1
	@echo "🚀 Avvio analisi PTOF (una scuola alla volta)..."
	$(PYTHON) workflow_notebook.py

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

# Estrae buone pratiche dai PDF originali con Ollama
# Uso: make best-practice-extract MODEL=qwen3:32b LIMIT=10
best-practice-extract:
	@echo "🌟 Estrazione Buone Pratiche dai PDF PTOF..."
	$(PYTHON) -m src.agents.best_practice_extractor \
		$(if $(MODEL),--model "$(MODEL)",) \
		$(if $(OLLAMA_URL),--ollama-url "$(OLLAMA_URL)",) \
		$(if $(LIMIT),--limit $(LIMIT),) \
		$(if $(WAIT),--wait $(WAIT),) \
		$(if $(FORCE),--force,) \
		$(if $(TARGET),--target "$(TARGET)",)
	@echo "✅ Buone pratiche salvate in data/best_practices.json"

# Reset e ri-estrazione completa
best-practice-extract-reset:
	@echo "🔄 Reset e ri-estrazione buone pratiche..."
	rm -f data/.best_practice_extraction_progress.json
	rm -f data/best_practice_registry.json
	$(PYTHON) -m src.agents.best_practice_extractor --force \
		$(if $(MODEL),--model "$(MODEL)",) \
		$(if $(OLLAMA_URL),--ollama-url "$(OLLAMA_URL)",)
	@echo "✅ Ri-estrazione completata"

# Statistiche estrazione
best-practice-extract-stats:
	@if [ -f data/best_practices.json ]; then \
		$(PYTHON) -c "import json; \
d=json.load(open('data/best_practices.json')); \
print(f'📊 Statistiche Buone Pratiche'); \
print(f'   Pratiche totali: {d.get(\"total_practices\", 0)}'); \
print(f'   Scuole processate: {d.get(\"schools_processed\", 0)}'); \
print(f'   Modello: {d.get(\"extraction_model\", \"N/D\")}'); \
print(f'   Ultimo aggiornamento: {d.get(\"last_updated\", \"N/D\")[:19]}'); \
cats={}; \
[cats.update({p[\"pratica\"][\"categoria\"]: cats.get(p[\"pratica\"][\"categoria\"], 0)+1}) for p in d.get(\"practices\", [])]; \
print(f'\\n📋 Per categoria:'); \
[print(f'   {k}: {v}') for k,v in sorted(cats.items(), key=lambda x: -x[1])]"; \
	else \
		echo "❌ File data/best_practices.json non trovato. Esegui prima: make best-practice-extract"; \
	fi

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

# Reset stato download e ricomincia
download-reset:
	rm -f src/downloaders/download_state.json
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
	@echo "   Opzioni: PROVIDER=gemini|openrouter|ollama FORCE=1"
else
	$(PYTHON) $(META_CLI) school --code $(CODE) \
		$(if $(PROVIDER),--provider $(PROVIDER),) \
		$(if $(FORCE),--force,)
endif

# Report regionale (uso: make meta-regional REGION=Lazio PROVIDER=ollama)
meta-regional:
ifndef REGION
	@echo "❌ Specificare la regione con REGION=NOME"
	@echo "   Esempio: make meta-regional REGION=Lazio"
	@echo "   Opzioni: PROVIDER=gemini|openrouter|ollama FORCE=1"
else
	$(PYTHON) $(META_CLI) regional --region "$(REGION)" \
		$(if $(PROVIDER),--provider $(PROVIDER),) \
		$(if $(FORCE),--force,)
endif

# Report nazionale
meta-national:
	$(PYTHON) $(META_CLI) national \
		$(if $(PROVIDER),--provider $(PROVIDER),) \
		$(if $(FORCE),--force,)

# Report tematico (uso: make meta-thematic DIM=governance)
meta-thematic:
ifndef DIM
	@echo "❌ Specificare la dimensione con DIM=NOME"
	@echo ""
	@echo "   DIMENSIONI STRUTTURALI:"
	@echo "     finalita, obiettivi, governance, didattica, partnership"
	@echo ""
	@echo "   DIMENSIONI OPPORTUNITÀ (granulari):"
	@echo "     pcto        - PCTO e Alternanza Scuola-Lavoro"
	@echo "     stage       - Stage e Tirocini"
	@echo "     openday     - Open Day e Orientamento in Entrata"
	@echo "     visite      - Visite Aziendali e Universitarie"
	@echo "     laboratori  - Laboratori Orientativi e Simulazioni"
	@echo "     testimonianze - Testimonianze e Incontri con Esperti"
	@echo "     counseling  - Counseling e Percorsi Individualizzati"
	@echo "     alumni      - Rete Alumni e Mentoring"
	@echo ""
	@echo "   Esempio: make meta-thematic DIM=pcto"
	@echo "   Opzioni: PROVIDER=gemini|openrouter|ollama FORCE=1"
else
	$(PYTHON) $(META_CLI) thematic --dim $(DIM) \
		$(if $(PROVIDER),--provider $(PROVIDER),) \
		$(if $(FORCE),--force,)
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
