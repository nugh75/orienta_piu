.PHONY: setup run workflow dashboard csv backfill clean help download download-sample download-strato download-dry review-slow-openrouter review-slow-gemini review-report-ollama review-scores-openrouter review-scores-gemini review-scores-ollama review-non-ptof outreach-portal outreach-email list-models list-models-openrouter list-models-gemini recover-not-ptof wizard best-practice best-practice-llm best-practice-llm-synth best-practice-llm-synth-ollama best-practice-llm-synth-restore pipeline-ollama cleanup cleanup-dry cleanup-bak cleanup-bak-old

PYTHON = .venv/bin/python
PIP = .venv/bin/pip
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
	@echo "  make run                     - Esegue analisi sui PDF in ptof_inbox/"
	@echo ""
	@echo "  📝 REVISIONE REPORT (arricchimento MD):"
	@echo "  make review-report-openrouter - Revisione report con OpenRouter (MODEL=...)"
	@echo "  make review-report-gemini     - Revisione report con Gemini (MODEL=...)"
	@echo "  make review-report-ollama     - Revisione report con Ollama (MODEL=..., OLLAMA_URL=...)"
	@echo ""
	@echo "  🎯 REVISIONE SCORES (JSON punteggi estremi):"
	@echo "  make review-scores-openrouter - Revisione scores con OpenRouter (MODEL=..., LOW=2, HIGH=6)"
	@echo "  make review-scores-gemini     - Revisione scores con Gemini (MODEL=..., LOW=2, HIGH=6)"
	@echo "  make review-scores-ollama     - Revisione scores con Ollama (MODEL=..., LOW=2, HIGH=6)"
	@echo ""
	@echo "  🔍 VALIDAZIONE:"
	@echo "  make review-non-ptof          - Rimuove analisi per documenti non-PTOF (TARGET=..., DRY=1)"
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
	@echo "� MANUTENZIONE REPORT:"
	@echo "  make check-truncated  - Trova report MD troncati"
	@echo "  make fix-truncated    - Trova troncati e ripristina SOLO quelli dai backup"
	@echo "  make list-backups     - Elenca tutti i file di backup disponibili"
	@echo ""
	@echo "🔗 COMBINAZIONI:"
	@echo "  make refresh    - Rigenera CSV e avvia dashboard"
	@echo "  make full       - Esegue run, rigenera CSV e avvia dashboard"
	@echo "  make pipeline   - Download sample + run + csv + dashboard"
	@echo "  make pipeline-ollama - Analisi + revisione Ollama (scores+report) + CSV refresh"
	@echo "                         MODEL=X, INTERVAL=300, LOW=2, HIGH=6"
	@echo ""
	@echo "📚 REPORT & ANALISI:"
	@echo "  make best-practice               - Genera report best practice (statistico)"
	@echo "  make best-practice-llm           - Genera report narrativo con Ollama (incrementale)"
	@echo "                                     MODEL=X per modello Ollama (default qwen3:32b)"
	@echo "  make best-practice-llm-reset     - Rigenera report narrativo da zero"
	@echo "  make best-practice-llm-synth     - Genera report sintetico con Gemini/OpenRouter"
	@echo "                                     REFACTOR_MODEL=X per modello Gemini"
	@echo "  make best-practice-llm-synth-ollama - Genera report sintetico con solo Ollama"
	@echo "                                        MODEL=X, OLLAMA_URL=X"
	@echo "  make best-practice-llm-synth-restore - Ripristina report sintetico dal backup"
	@echo ""
	@echo "🤖 MODELLI AI:"
	@echo "  make models                  - Mostra tutti i modelli disponibili"
	@echo "  make list-models             - Lista modelli dai preset"
	@echo "  make list-models-openrouter  - Lista modelli OpenRouter (FREE_ONLY=1 per limitare)"
	@echo "  make list-models-gemini      - Lista modelli Gemini (richiede GEMINI_API_KEY)"
	@echo ""
	@echo "⏰ AUTOMAZIONE:"
	@echo "  make csv-watch             - Rigenera CSV ogni 5 min (INTERVAL=X per cambiare)"
	@echo ""
	@echo "🧭 WIZARD:"
	@echo "  make wizard               - Avvia wizard interattivo per i comandi make"
	@echo ""
	@echo "🧹 PULIZIA FILE OBSOLETI:"
	@echo "  make cleanup-dry          - Mostra cosa verrebbe eliminato (dry-run)"
	@echo "  make cleanup              - Elimina file obsoleti (chiede conferma)"
	@echo "  make cleanup-bak          - Elimina obsoleti + file .bak (chiede conferma)"
	@echo "  make cleanup-bak-old DAYS=N - Elimina solo .bak più vecchi di N giorni (default 7)"

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

best-practice:
	@echo "📚 Generazione report Best Practice Orientamento..."
	$(PYTHON) -m src.agents.best_practice_agent
	@echo "✅ Report generato in reports/best_practice_orientamento.md"

best-practice-llm:
	@echo "🤖 Generazione report Best Practice con Ollama LLM (incrementale)..."
	$(PYTHON) -m src.agents.best_practice_ollama_agent $(if $(MODEL),--model $(MODEL)) $(if $(OLLAMA_URL),--url $(OLLAMA_URL)) $(if $(RESET),--reset)
	@echo "✅ Report narrativo generato in reports/best_practice_orientamento_narrativo.md"
	@echo "💡 Per creare il report sintetico: make best-practice-llm-synth"

best-practice-llm-reset:
	@echo "🔄 Reset e rigenerazione report Best Practice con Ollama LLM..."
	$(PYTHON) -m src.agents.best_practice_ollama_agent --reset $(if $(MODEL),--model $(MODEL)) $(if $(OLLAMA_URL),--url $(OLLAMA_URL))
	@echo "✅ Report narrativo generato in reports/best_practice_orientamento_narrativo.md"

best-practice-llm-synth:
	@echo "✨ Generazione Report Sintetico con Gemini/OpenRouter..."
	$(PYTHON) -m src.agents.best_practice_ollama_agent --synth $(if $(REFACTOR_MODEL),--refactor-model $(REFACTOR_MODEL)) $(if $(FALLBACK_MODEL),--fallback-model $(FALLBACK_MODEL))
	@echo "✅ Report sintetico generato in reports/best_practice_orientamento_sintetico.md"

# Sintesi con solo Ollama (senza Gemini/OpenRouter)
best-practice-llm-synth-ollama:
	@echo "✨ Generazione Report Sintetico con Ollama..."
	$(PYTHON) -m src.agents.best_practice_ollama_agent --synth-ollama $(if $(MODEL),--model $(MODEL)) $(if $(OLLAMA_URL),--url $(OLLAMA_URL))
	@echo "✅ Report sintetico generato in reports/best_practice_orientamento_sintetico.md"

best-practice-llm-synth-restore:
	@if [ -f reports/best_practice_orientamento_sintetico.md.bak ]; then \
		cp reports/best_practice_orientamento_sintetico.md.bak reports/best_practice_orientamento_sintetico.md; \
		echo "✅ Report sintetico ripristinato dal backup"; \
	else \
		echo "❌ Nessun backup trovato"; \
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
	@echo "🦙 OLLAMA (locale - modelli consigliati):"
	@echo "   qwen3:32b"
	@echo "   qwen3:14b"
	@echo "   llama3.3:70b"
	@echo "   deepseek-r1:32b"
	@echo "   gemma2:27b"
	@echo ""

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
