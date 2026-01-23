# Pagina Admin - Riferimento Comandi Make
# Documentazione completa di tutti i comandi disponibili

import streamlit as st
import sys
from pathlib import Path

# Add parent for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from page_control import setup_page, is_admin_logged_in
from data_utils import render_footer

st.set_page_config(page_title="ORIENTA+ | Comandi Make", page_icon="🔧", layout="wide")
setup_page("pages/23_Comandi.py")

st.title("🔧 Riferimento Comandi Make")
st.markdown("Documentazione completa di tutti i comandi disponibili per la gestione del sistema ORIENTA+")

# Admin check
if not is_admin_logged_in():
    st.warning("⚠️ Questa pagina è riservata all'amministratore.")
    st.info("Effettua il login come admin dalla sidebar per accedere.")
    st.stop()

st.success("✅ Connesso come amministratore")

# Sidebar con indice rapido
st.sidebar.markdown("## 📑 Indice Rapido")
st.sidebar.markdown("""
- [Setup e Configurazione](#setup-e-configurazione)
- [Download PTOF](#download-ptof)
- [Strata-Cycle](#strata-cycle-ciclo-stratificato)
- [Analisi e Workflow](#analisi-e-workflow)
- [Revisione](#revisione)
- [Attività](#catalogo-attivita)
- [Meta Report](#meta-report)
- [Dashboard e Dati](#dashboard-e-dati)
- [Modelli AI](#modelli-ai)
- [Manutenzione](#manutenzione)
- [Docker](#docker)
- [Git](#git-automatico)
""")

# =============================================================================
# SETUP E CONFIGURAZIONE
# =============================================================================
st.header("⚙️ Setup e Configurazione", anchor="setup-e-configurazione")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Comandi Base")
    st.markdown("""
| Comando | Descrizione |
|---------|-------------|
| `make setup` | Installa le dipendenze |
| `make help` | Mostra elenco comandi |
| `make wizard` | Wizard interattivo |
| `make config` | Wizard configurazione pipeline |
| `make config-show` | Mostra configurazione attuale |
""")

with col2:
    st.subheader("Esempi")
    st.code("""# Setup iniziale del progetto
make setup

# Mostra tutti i comandi disponibili
make help

# Wizard interattivo per scegliere cosa fare
make wizard""", language="bash")

# =============================================================================
# DOWNLOAD PTOF
# =============================================================================
st.header("📥 Download PTOF", anchor="download-ptof")

st.markdown("""
### Comandi Base Download

| Comando | Descrizione |
|---------|-------------|
| `make download` | Dry-run: mostra stratificazione senza scaricare |
| `make download-sample` | Scarica 5 scuole per ogni strato |
| `make download-strato N=X` | Scarica X scuole per ogni strato |
| `make download-reset` | Reset stato download e ricomincia |
""")

st.markdown("### Filtri Specifici")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
| Comando | Descrizione |
|---------|-------------|
| `make download-statali` | Solo scuole statali |
| `make download-paritarie` | Solo scuole paritarie |
| `make download-regione R=X` | Scuole di una regione |
| `make download-metro` | Solo province metropolitane |
| `make download-non-metro` | Solo province NON metropolitane |
| `make download-grado G=X` | Per grado scolastico |
| `make download-area A=X` | Per area geografica |
""")

with col2:
    st.markdown("""
**Valori ammessi per G (grado):**
- `INFANZIA`, `PRIMARIA`, `SEC_PRIMO`, `SEC_SECONDO`, `ALTRO`

**Valori ammessi per A (area):**
- `NORD OVEST`, `NORD EST`, `CENTRO`, `SUD`, `ISOLE`

**Valori ammessi per R (regione):**
- Tutte le regioni italiane (es: `LAZIO`, `LOMBARDIA`, `SICILIA`)
""")

st.subheader("Esempi Download")
st.code("""# Campione stratificato con 10 scuole per strato
make download-strato N=10

# Tutte le scuole del Lazio
make download-regione R=LAZIO

# Solo licei e istituti tecnici
make download-grado G=SEC_SECONDO

# Solo scuole del Sud
make download-area A=SUD

# Solo province metropolitane paritarie
make download-metro
make download-paritarie""", language="bash")

# =============================================================================
# STRATA-CYCLE
# =============================================================================
st.header("🔄 Strata-Cycle (Ciclo Stratificato)", anchor="strata-cycle-ciclo-stratificato")

st.info("Il comando `strata-cycle` è il modo principale per scaricare e analizzare PTOF in modo incrementale e bilanciato.")

st.markdown("""
### Parametri

| Parametro | Descrizione | Default |
|-----------|-------------|---------|
| `MAX_DOWNLOADS=X` | Limita il numero di download | Nessun limite |
| `G=X` | Filtra per grado (Infanzia, Primaria, I Grado, II Grado) | Tutti |
| `R=X` | Filtra per regione | Tutte |
| `GESTIONE=X` | Filtra per gestione (Statale, Paritaria) | Tutte |
| `SKIP_ANALYSIS=1` | Salta l'analisi dopo il download | 0 (analizza) |
| `PROVIDER=X` | Provider LLM (ollama, openrouter, gemini) | - |
| `MODEL=X` | Modello da usare | - |
| `OLLAMA_URL=X` | URL server Ollama | http://localhost:11434 |
""")

st.subheader("Esempi Strata-Cycle")

tab1, tab2, tab3 = st.tabs(["🏠 Ollama Locale", "🌐 OpenRouter", "🔬 Filtri Avanzati"])

with tab1:
    st.code("""# Ciclo con Ollama remoto (40 download)
OLLAMA_URL=http://192.168.129.14:11434 \\
MODEL=gemma3:27b \\
PROVIDER=ollama \\
MAX_DOWNLOADS=40 \\
make strata-cycle

# Solo download senza analisi
OLLAMA_URL=http://192.168.129.14:11434 \\
MODEL=gemma3:27b \\
PROVIDER=ollama \\
MAX_DOWNLOADS=50 \\
SKIP_ANALYSIS=1 \\
make strata-cycle

# Ciclo completo senza limiti
OLLAMA_URL=http://192.168.129.14:11434 \\
MODEL=gemma3:27b \\
PROVIDER=ollama \\
make strata-cycle""", language="bash")

with tab2:
    st.code("""# Con OpenRouter (modelli economici)
PROVIDER=openrouter \\
MODEL=qwen/qwen-2.5-72b-instruct \\
MAX_DOWNLOADS=40 \\
make strata-cycle

# Con Gemini Flash (gratis ma rate limited)
PROVIDER=openrouter \\
MODEL=google/gemini-2.0-flash-exp:free \\
MAX_DOWNLOADS=20 \\
make strata-cycle""", language="bash")

with tab3:
    st.code("""# Solo Primaria Statale
OLLAMA_URL=http://192.168.129.14:11434 \\
MODEL=gemma3:27b \\
PROVIDER=ollama \\
G=Primaria \\
GESTIONE=Statale \\
MAX_DOWNLOADS=30 \\
make strata-cycle

# Solo Infanzia Paritaria (per bilanciare campione)
OLLAMA_URL=http://192.168.129.14:11434 \\
MODEL=gemma3:27b \\
PROVIDER=ollama \\
G=Infanzia \\
GESTIONE=Paritaria \\
MAX_DOWNLOADS=40 \\
make strata-cycle

# Solo Lombardia II Grado
PROVIDER=openrouter \\
MODEL=qwen/qwen-2.5-72b-instruct \\
R=Lombardia \\
G="II Grado" \\
MAX_DOWNLOADS=25 \\
make strata-cycle""", language="bash")

# =============================================================================
# ANALISI E WORKFLOW
# =============================================================================
st.header("🔬 Analisi e Workflow", anchor="analisi-e-workflow")

st.markdown("""
### Comandi Workflow

| Comando | Descrizione |
|---------|-------------|
| `make run` | Esegue analisi PTOF (può coesistere con altri processi) |
| `make run-force` | Forza ri-analisi di tutti i file |
| `make run-force-code CODE=X` | Ri-analizza una scuola specifica |
| `make workflow` | Analisi PTOF pulita (una scuola alla volta) |
| `make workflow-force` | Come workflow ma ri-analizza tutto |
""")

st.markdown("""
### Parametri Workflow

| Parametro | Descrizione | Esempio |
|-----------|-------------|---------|
| `PROVIDER` | Provider LLM | `PROVIDER=ollama` |
| `MODEL` | Modello da usare | `MODEL=gemma3:27b` |
| `PRESET` | ID configurazione (da config) | `PRESET=8` |
| `FORCE_CODE` | Ri-analizza SOLO una scuola | `FORCE_CODE=BA1MD7500G` |
| `SKIP_VALIDATION` | Salta validazione PTOF | `SKIP_VALIDATION=1` |
| `OLLAMA_URL` | URL server Ollama | `OLLAMA_URL=http://192.168.129.14:11434` |
""")

st.subheader("Esempi Workflow")

st.code("""# Analisi con Ollama
OLLAMA_URL=http://192.168.129.14:11434 \\
MODEL=gemma3:27b \\
PROVIDER=ollama \\
make workflow

# Ri-analizza una singola scuola
make run-force-code CODE=RMIC8GA002

# Workflow con OpenRouter
PROVIDER=openrouter \\
MODEL=qwen/qwen-2.5-72b-instruct \\
make workflow

# Workflow ibrido (Ollama per analisi, OpenRouter per sintesi)
make workflow ANALYST=qwen3:32b PROVIDER_ANALYST=ollama \\
              REFINER=google/gemini-2.5-flash PROVIDER_REFINER=openrouter""", language="bash")

# =============================================================================
# REVISIONE
# =============================================================================
st.header("📝 Revisione", anchor="revisione")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
### Revisione Report (arricchimento MD)

| Comando | Provider |
|---------|----------|
| `make review-report-openrouter` | OpenRouter |
| `make review-report-gemini` | Google Gemini |
| `make review-report-ollama` | Ollama locale |
""")

with col2:
    st.markdown("""
### Revisione Scores (punteggi JSON)

| Comando | Provider |
|---------|----------|
| `make review-scores-openrouter` | OpenRouter |
| `make review-scores-gemini` | Google Gemini |
| `make review-scores-ollama` | Ollama locale |
""")

st.markdown("""
### Parametri Revisione

| Parametro | Descrizione | Default |
|-----------|-------------|---------|
| `MODEL=X` | Nome del modello | Varia |
| `TARGET=X` | Codice scuola specifico | Tutti |
| `LIMIT=X` | Numero max di file | 100 |
| `WAIT=X` | Secondi tra chiamate | 120 |
| `LOW=X` | Soglia bassa score | 2 |
| `HIGH=X` | Soglia alta score | 6 |
| `OLLAMA_URL=X` | URL server Ollama | localhost |
""")

st.subheader("Esempi Revisione")

st.code("""# Revisione scores con Ollama
make review-scores-ollama MODEL=qwen3:32b \\
    OLLAMA_URL=http://192.168.129.14:11434 \\
    LOW=2 HIGH=6

# Revisione report con OpenRouter
make review-report-openrouter MODEL="qwen/qwen-2.5-72b-instruct"

# Revisione singola scuola
make review-scores-gemini TARGET=RMIC8GA002

# Rimuovi analisi per documenti non-PTOF (dry-run)
make review-non-ptof DRY=1

# Rimuovi effettivamente
make review-non-ptof TARGET=RMIC8GA002""", language="bash")

# =============================================================================
# CATALOGO ATTIVITÀ
# =============================================================================
st.header("🌟 Catalogo Attività", anchor="catalogo-attivita")

st.markdown("""
| Comando | Descrizione |
|---------|-------------|
| `make activity-extract` | Estrae attività dai PDF PTOF |
| `make activity-extract-reset` | Reset e ri-estrazione completa |
| `make activity-extract-stats` | Mostra statistiche estrazione |
| `make activity-theme-backfill` | Backfill temi mancanti con LLM |
""")

st.subheader("Esempi Estrazione Attività")

st.code("""# Estrazione con OpenRouter (economico)
PROVIDER=openrouter \\
MODEL=qwen/qwen-2.5-72b-instruct \\
LIMIT=40 \\
make activity-extract

# Estrazione con Ollama
OLLAMA_URL=http://192.168.129.14:11434 \\
MODEL=gemma3:27b \\
PROVIDER=ollama \\
LIMIT=50 \\
make activity-extract

# Gestione rate limit (batch + pausa)
make activity-extract BATCH_SIZE=10 BATCH_WAIT=300

# Forza ri-elaborazione
make activity-extract FORCE=1

# Statistiche rapide
make activity-extract-stats""", language="bash")

# =============================================================================
# META REPORT
# =============================================================================
st.header("📊 Meta Report", anchor="meta-report")

st.markdown("""
| Comando | Descrizione |
|---------|-------------|
| `make meta-skeleton DIM=X` | Report tematico skeleton-first (raccomandato) |
| `make meta-status` | Stato dei report (pending/current/stale) |
| `make meta-school CODE=X` | Report singola scuola |
| `make meta-next` | Genera prossimo report pendente |
| `make meta-batch N=5` | Genera N report pendenti |
| `make meta-refine` | Raffina report esistenti |
""")

st.subheader("Esempi Meta Report")

st.code("""# Report tematico con filtri
make meta-skeleton DIM=orientamento REGIONE=Marche ORDINE="II Grado"

# Solo Ollama (locale, no costi)
make meta-skeleton DIM=orientamento REGIONE=Marche \\
    PROVIDER_SCHOOL=ollama PROVIDER_SYNTHESIS=ollama

# Dual provider (Ollama per scuole, OpenRouter per sintesi)
make meta-skeleton DIM=orientamento REGIONE=Marche \\
    PROVIDER_SCHOOL=ollama PROVIDER_SYNTHESIS=openrouter

# Report singola scuola
make meta-school CODE=RMIC8GA002

# Genera 10 report pendenti
make meta-batch N=10""", language="bash")

# =============================================================================
# DASHBOARD E DATI
# =============================================================================
st.header("📈 Dashboard e Dati", anchor="dashboard-e-dati")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
| Comando | Descrizione |
|---------|-------------|
| `make dashboard` | Avvia dashboard Streamlit |
| `make csv` | Rigenera CSV dai JSON |
| `make csv-watch` | Rigenera CSV ogni 5 min |
| `make backfill` | Backfill metadati mancanti |
""")

with col2:
    st.markdown("""
| Comando | Descrizione |
|---------|-------------|
| `make refresh` | csv + dashboard |
| `make full` | run + csv + dashboard |
| `make pipeline` | download + run + csv + dashboard |
| `make pipeline-ollama` | Analisi + revisione Ollama + CSV |
""")

st.subheader("Esempi")

st.code("""# Avvia dashboard
make dashboard

# Rigenera CSV e avvia dashboard
make refresh

# Watch mode: rigenera CSV ogni 60 secondi
make csv-watch INTERVAL=60

# Pipeline completa con Ollama
make pipeline-ollama MODEL=qwen3:32b INTERVAL=300""", language="bash")

# =============================================================================
# MODELLI AI
# =============================================================================
st.header("🤖 Modelli AI", anchor="modelli-ai")

st.markdown("""
| Comando | Descrizione |
|---------|-------------|
| `make models` | Mostra TUTTI i modelli disponibili |
| `make list-models` | Lista modelli dai preset |
| `make list-models-openrouter` | Lista modelli OpenRouter |
| `make list-models-gemini` | Lista modelli Gemini |
| `make models-ollama` | Lista modelli Ollama scaricati |
| `make models-ollama-pull MODEL=X` | Scarica/aggiorna modello Ollama |
""")

st.subheader("Modelli Consigliati")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
**🌐 OpenRouter (economici)**
- `qwen/qwen-2.5-72b-instruct` ($0.12/1M) 🔥
- `qwen/qwen3-32b` ($0.08/1M)
- `google/gemini-flash-1.5` ($0.075/1M)
- `anthropic/claude-3-haiku` ($0.25/1M)
""")

with col2:
    st.markdown("""
**🆓 OpenRouter (gratis)**
- `google/gemini-2.0-flash-exp:free`
- `qwen/qwen3-4b:free`
- `meta-llama/llama-3.3-70b-instruct:free`

⚠️ Rate limited!
""")

with col3:
    st.markdown("""
**🏠 Ollama (locale)**
- `gemma3:27b` (raccomandato)
- `qwen3:32b` (bilanciato)
- `qwen3:14b` (veloce)
- `llama3.3:70b` (alta qualità)
""")

st.code("""# Lista modelli OpenRouter free
make list-models-openrouter FREE_ONLY=1

# Scarica modello Ollama
make models-ollama-pull MODEL=gemma3:27b

# Lista modelli Ollama disponibili
make models-ollama OLLAMA_HOST=http://192.168.129.14:11434""", language="bash")

# =============================================================================
# MANUTENZIONE
# =============================================================================
st.header("🔧 Manutenzione", anchor="manutenzione")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
### Registro Analisi

| Comando | Descrizione |
|---------|-------------|
| `make registry-status` | Stato del registro |
| `make registry-list` | Lista file registrati |
| `make registry-clear` | Pulisce registro (forza ri-analisi) |
| `make registry-remove CODE=X` | Rimuove entry specifica |
""")

with col2:
    st.markdown("""
### Pulizia File

| Comando | Descrizione |
|---------|-------------|
| `make cleanup-dry` | Mostra cosa verrebbe eliminato |
| `make cleanup` | Elimina file obsoleti |
| `make cleanup-bak` | Elimina file .bak recenti |
| `make cleanup-bak-old` | Elimina .bak > 7 giorni |
| `make clean` | Pulisce cache e temp |
""")

st.markdown("""
### Report e Recovery

| Comando | Descrizione |
|---------|-------------|
| `make check-truncated` | Trova report MD troncati |
| `make fix-truncated` | Ripristina dai backup |
| `make list-backups` | Elenca backup disponibili |
| `make recover-not-ptof` | Recupera PDF con `_ok` da discarded |
""")

st.subheader("Esempi Manutenzione")

st.code("""# Analisi bloccata su un file? Rimuovi dal registro
make registry-remove CODE=RMIC8GA002
make run

# Trova e ripristina report troncati
make check-truncated
make fix-truncated

# Pulizia sicura (prima dry-run)
make cleanup-dry
make cleanup

# Costi API
make report-costs
make check-credits""", language="bash")

# =============================================================================
# DOCKER
# =============================================================================
st.header("🐳 Docker", anchor="docker")

st.markdown("""
| Comando | Descrizione |
|---------|-------------|
| `make docker-up` | Avvia container |
| `make docker-down` | Ferma container |
| `make docker-build` | Ricostruisce immagine |
| `make docker-logs` | Mostra log container |
| `make docker-status` | Stato container |
| `make docker-shell` | Shell interattiva |
| `make venv` | Crea virtual environment |
""")

st.code("""# Avvia tutto con Docker
make docker-build
make docker-up

# Entra nel container
make docker-shell

# Controlla lo stato
make docker-status
make docker-logs""", language="bash")

# =============================================================================
# GIT AUTOMATICO
# =============================================================================
st.header("🔄 Git Automatico", anchor="git-automatico")

st.markdown("""
| Comando | Descrizione |
|---------|-------------|
| `make git-auto` | Add/commit/push ogni 10 min |
| `make git-status` | Mostra stato git |
| `make git-pull` | Pull da remote |
| `make git-push` | Push a remote |
| `make git-commit` | Commit con messaggio auto |
""")

st.code("""# Auto-commit ogni 5 minuti
make git-auto INTERVAL=300

# Sincronizza manualmente
make git-pull
make git-status
make git-commit
make git-push""", language="bash")

# =============================================================================
# LOG E MONITORING
# =============================================================================
st.header("📺 Log e Monitoring", anchor="log-e-monitoring")

st.markdown("""
| Comando | Descrizione |
|---------|-------------|
| `make logs` | Visualizzatore interattivo (lnav) |
| `make logs-live` | Log in tempo reale |
""")

st.code("""# Visualizza log interattivamente
make logs

# Log live (tail -f)
make logs-live

# Ultime 200 righe
make logs LINES=200""", language="bash")

# =============================================================================
# OUTREACH
# =============================================================================
st.header("📬 Outreach PTOF", anchor="outreach")

st.markdown("""
| Comando | Descrizione |
|---------|-------------|
| `make outreach-portal` | Avvia portale upload PTOF |
| `make outreach-email` | Invia email PTOF |
""")

st.code("""# Avvia portale upload (porta 8502)
make outreach-portal PORT=8502

# Invia email (dry-run)
make outreach-email BASE_URL=https://orienta.example.com LIMIT=10

# Invia email reali
make outreach-email BASE_URL=https://orienta.example.com LIMIT=10 SEND=1""", language="bash")

# =============================================================================
# TMUX TIPS
# =============================================================================
st.header("💡 Tips: Sessioni TMUX", anchor="tmux")

st.info("Usa TMUX per eseguire comandi lunghi in background senza perdere la sessione.")

st.code("""# Crea nuova sessione con nome
tmux new -s strata-cycle

# Esegui comando nella sessione
cd /home/nugh75/LIste && \\
OLLAMA_URL=http://192.168.129.14:11434 \\
MODEL=gemma3:27b \\
PROVIDER=ollama \\
MAX_DOWNLOADS=100 \\
make strata-cycle

# Detach dalla sessione (senza chiuderla)
# Premi: Ctrl+b poi d

# Lista sessioni attive
tmux ls

# Riconnetti a sessione
tmux attach -t strata-cycle

# Chiudi sessione
tmux kill-session -t strata-cycle""", language="bash")

# Footer
st.divider()
render_footer()
