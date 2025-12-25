#!/usr/bin/env python3
"""
PTOF Launcher - Interfaccia grafica TUI con Textual.
Include tutti i target make con monitoraggio processi.
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, Button, Input, Label, Select, Log, Static, ListView, ListItem, OptionList
from textual.widgets.option_list import Option
from textual.screen import Screen
from textual.binding import Binding
from textual.worker import Worker, get_current_worker
from textual import on, work
import subprocess
import os
import signal
import sys
import threading
from pathlib import Path
from typing import Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent
MODEL_LISTER = BASE_DIR / "src" / "utils" / "list_models.py"

DEFAULT_OPENROUTER_MODEL = "google/gemini-3-flash-preview:free"
DEFAULT_GEMINI_MODEL = "gemini-3-flash-preview"
DEFAULT_OLLAMA_MODEL = "qwen3:32b"

# Processi attivi
RUNNING_PROCESSES: Dict[str, subprocess.Popen] = {}
PROCESS_LOCK = threading.Lock()


def get_models_list(provider: str) -> List[str]:
    """Recupera lista modelli da API."""
    if not MODEL_LISTER.exists():
        return []
    
    if provider == "openrouter":
        args = [sys.executable, str(MODEL_LISTER), "--openrouter", "--free-only"]
    elif provider == "gemini":
        args = [sys.executable, str(MODEL_LISTER), "--gemini"]
    elif provider == "ollama":
        # Lista statica per Ollama
        return [
            "qwen3:32b", "qwen3:14b", "qwen3:8b",
            "llama3.3:70b", "llama3.2:latest",
            "mistral:latest", "deepseek-r1:32b",
            "gemma2:27b", "phi3:medium",
        ]
    else:
        return []
    
    try:
        result = subprocess.run(args, cwd=BASE_DIR, text=True, capture_output=True, timeout=30)
        output = result.stdout.strip()
        if output:
            return [line.strip() for line in output.split("\n") if line.strip()]
    except:
        pass
    return []


class PTOFLauncher(App):
    """App principale PTOF Launcher."""
    
    CSS = """
    Screen {
        layout: grid;
        grid-size: 2;
        grid-columns: 35 1fr;
    }
    #sidebar {
        height: 100%;
        background: $panel;
        border-right: solid $accent;
        overflow-y: auto;
        width: 35;
    }
    #main {
        height: 100%;
        width: 100%;
        layout: vertical;
    }
    .menu-section {
        margin: 0;
        padding: 1;
        border: solid $primary;
        background: $surface;
    }
    .menu-title {
        text-align: center;
        text-style: bold;
        background: $accent;
        color: $text;
        padding: 0 1;
        margin-bottom: 1;
    }
    .submenu {
        margin-top: 1;
        padding: 1;
        border: dashed $secondary;
        display: none;
    }
    .submenu.visible {
        display: block;
    }
    Button {
        width: 100%;
        margin-bottom: 0;
        min-height: 1;
        height: auto;
    }
    Button.menu-btn {
        background: $primary;
    }
    Button.action-btn {
        background: $success;
    }
    Button.stop-btn {
        background: $error;
    }
    #console {
        border: solid $accent;
        height: 1fr;
        width: 100%;
    }
    #console-container {
        height: 1fr;
        width: 100%;
    }
    #params {
        height: auto;
        max-height: 12;
        padding: 1;
        border: solid $secondary;
        margin: 0;
        overflow-y: auto;
    }
    #controls {
        height: 3;
        padding: 0 1;
        dock: bottom;
    }
    #controls Button {
        width: auto;
        min-width: 12;
        margin-right: 1;
    }
    .param-row {
        height: 3;
        margin: 0;
    }
    .param-label {
        width: 12;
        height: 3;
    }
    .param-input {
        width: 1fr;
        height: 3;
    }
    #process-list {
        height: auto;
        max-height: 8;
        border: solid $warning;
        margin: 1;
        padding: 1;
    }
    .process-item {
        color: $success;
    }
    Select {
        width: 100%;
        height: 3;
    }
    Input {
        height: 3;
    }
    .provider-btn {
        width: auto;
        min-width: 10;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Esci"),
        Binding("escape", "back", "Indietro"),
        Binding("ctrl+c", "stop_current", "Stop"),
    ]
    
    def __init__(self):
        super().__init__()
        self.current_menu = "main"
        self.current_command = None
        self.process = None
        self.models_cache = {}
        self._pending_cmd = None
        self._current_provider = "openrouter"
        self.auto_run_on_select = True
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with Horizontal():
            # Sidebar con menu
            with ScrollableContainer(id="sidebar"):
                # Menu principale
                with Vertical(id="menu-main", classes="menu-section"):
                    yield Label("🚀 MENU PRINCIPALE", classes="menu-title")
                    yield Button("⚡ Azioni Rapide", id="btn-quick", classes="menu-btn")
                    yield Button("📥 Download PTOF", id="btn-download", classes="menu-btn")
                    yield Button("🔄 Workflow Analisi", id="btn-workflow", classes="menu-btn")
                    yield Button("🤖 Revisione AI", id="btn-review", classes="menu-btn")
                    yield Button("📋 Registro Analisi", id="btn-registry", classes="menu-btn")
                    yield Button("📬 Outreach PTOF", id="btn-outreach", classes="menu-btn")
                    yield Button("🤖 Lista Modelli", id="btn-models", classes="menu-btn")
                    yield Button("📊 Stato Processi", id="btn-status", classes="menu-btn")
                
                # Submenu Azioni Rapide
                with Vertical(id="submenu-quick", classes="submenu"):
                    yield Label("⚡ AZIONI RAPIDE", classes="menu-title")
                    yield Button("🚀 Pipeline completo", id="cmd-pipeline", classes="action-btn")
                    yield Button("🔄 Full (run+csv+dash)", id="cmd-full", classes="action-btn")
                    yield Button("📊 Refresh (csv+dash)", id="cmd-refresh", classes="action-btn")
                    yield Button("▶️ Solo workflow", id="cmd-run", classes="action-btn")
                    yield Button("📊 Solo dashboard", id="cmd-dashboard", classes="action-btn")
                    yield Button("⬅️ Indietro", id="btn-back", classes="menu-btn")
                
                # Submenu Download
                with Vertical(id="submenu-download", classes="submenu"):
                    yield Label("📥 DOWNLOAD PTOF", classes="menu-title")
                    yield Button("📊 Dry-run", id="cmd-download", classes="action-btn")
                    yield Button("📥 Sample (5/strato)", id="cmd-download-sample", classes="action-btn")
                    yield Button("📥 Stratificato N", id="cmd-download-strato", classes="action-btn")
                    yield Button("🏛️ Scuole statali", id="cmd-download-statali", classes="action-btn")
                    yield Button("🏫 Scuole paritarie", id="cmd-download-paritarie", classes="action-btn")
                    yield Button("🗺️ Per regione", id="cmd-download-regione", classes="action-btn")
                    yield Button("🏙️ Metropolitane", id="cmd-download-metro", classes="action-btn")
                    yield Button("🌾 Non metropolitane", id="cmd-download-non-metro", classes="action-btn")
                    yield Button("📚 Per grado", id="cmd-download-grado", classes="action-btn")
                    yield Button("🧭 Per area", id="cmd-download-area", classes="action-btn")
                    yield Button("🔄 Reset download", id="cmd-download-reset", classes="action-btn")
                    yield Button("⬅️ Indietro", id="btn-back", classes="menu-btn")
                
                # Submenu Workflow
                with Vertical(id="submenu-workflow", classes="submenu"):
                    yield Label("🔄 WORKFLOW ANALISI", classes="menu-title")
                    yield Button("▶️ Avvia workflow", id="cmd-run", classes="action-btn")
                    yield Button("🔄 Force (ri-analizza)", id="cmd-run-force", classes="action-btn")
                    yield Button("🎯 Force su codice", id="cmd-run-force-code", classes="action-btn")
                    yield Button("📊 Dashboard", id="cmd-dashboard", classes="action-btn")
                    yield Button("📈 Rigenera CSV", id="cmd-csv", classes="action-btn")
                    yield Button("🔧 Backfill metadati", id="cmd-backfill", classes="action-btn")
                    yield Button("🧹 Pulisci cache", id="cmd-clean", classes="action-btn")
                    yield Button("♻️ Recupera not_ptof", id="cmd-recover-not-ptof", classes="action-btn")
                    yield Button("⏱️ CSV watch", id="cmd-csv-watch", classes="action-btn")
                    yield Button("⬅️ Indietro", id="btn-back", classes="menu-btn")
                
                # Submenu Review
                with Vertical(id="submenu-review", classes="submenu"):
                    yield Label("🤖 REVISIONE AI", classes="menu-title")
                    yield Button("🐢 Review OpenRouter", id="cmd-review-slow", classes="action-btn")
                    yield Button("💎 Review Gemini", id="cmd-review-gemini", classes="action-btn")
                    yield Button("🦙 Review Ollama", id="cmd-review-ollama", classes="action-btn")
                    yield Button("📊 Scores OpenRouter", id="cmd-review-scores", classes="action-btn")
                    yield Button("📊 Scores Gemini", id="cmd-review-scores-gemini", classes="action-btn")
                    yield Button("📊 Scores Ollama", id="cmd-review-scores-ollama", classes="action-btn")
                    yield Button("🦙 Ollama Score", id="cmd-ollama-score-review", classes="action-btn")
                    yield Button("🦙 Ollama Report", id="cmd-ollama-report-review", classes="action-btn")
                    yield Button("🦙 Ollama All", id="cmd-ollama-review-all", classes="action-btn")
                    yield Button("🗑️ Review non-PTOF", id="cmd-review-non-ptof", classes="action-btn")
                    yield Button("⬅️ Indietro", id="btn-back", classes="menu-btn")
                
                # Submenu Registry
                with Vertical(id="submenu-registry", classes="submenu"):
                    yield Label("📋 REGISTRO ANALISI", classes="menu-title")
                    yield Button("📊 Stato registro", id="cmd-registry-status", classes="action-btn")
                    yield Button("📋 Lista registro", id="cmd-registry-list", classes="action-btn")
                    yield Button("🗑️ Pulisci registro", id="cmd-registry-clear", classes="action-btn")
                    yield Button("❌ Rimuovi entry", id="cmd-registry-remove", classes="action-btn")
                    yield Button("⬅️ Indietro", id="btn-back", classes="menu-btn")
                
                # Submenu Outreach
                with Vertical(id="submenu-outreach", classes="submenu"):
                    yield Label("📬 OUTREACH PTOF", classes="menu-title")
                    yield Button("🌐 Portale upload", id="cmd-outreach-portal", classes="action-btn")
                    yield Button("📧 Invia email", id="cmd-outreach-email", classes="action-btn")
                    yield Button("⬅️ Indietro", id="btn-back", classes="menu-btn")
                
                # Submenu Models
                with Vertical(id="submenu-models", classes="submenu"):
                    yield Label("🤖 LISTA MODELLI", classes="menu-title")
                    yield Button("📦 Config locali", id="cmd-list-models", classes="action-btn")
                    yield Button("🌐 OpenRouter", id="cmd-list-models-openrouter", classes="action-btn")
                    yield Button("💎 Gemini", id="cmd-list-models-gemini", classes="action-btn")
                    yield Button("⬅️ Indietro", id="btn-back", classes="menu-btn")
                
                # Submenu Status
                with Vertical(id="submenu-status", classes="submenu"):
                    yield Label("📊 PROCESSI ATTIVI", classes="menu-title")
                    yield Static(id="process-list")
                    yield Button("🔄 Aggiorna", id="btn-refresh-status", classes="menu-btn")
                    yield Button("🛑 Ferma tutti", id="btn-stop-all", classes="stop-btn")
                    yield Button("⬅️ Indietro", id="btn-back", classes="menu-btn")
            
            # Main area
            with Vertical(id="main"):
                # Parametri compatti su 2 righe
                with Vertical(id="params"):
                    with Horizontal(classes="param-row"):
                        yield Label("N:", classes="param-label")
                        yield Input(value="5", id="param-n", classes="param-input")
                        yield Label("Codice:", classes="param-label")
                        yield Input(placeholder="RMIS00100X", id="param-code", classes="param-input")
                        yield Label("Regione:", classes="param-label")
                        yield Input(placeholder="LAZIO", id="param-regione", classes="param-input")
                    with Horizontal(classes="param-row"):
                        yield Label("Modello:", classes="param-label")
                        yield Select(
                            [(m, m) for m in [
                                DEFAULT_OPENROUTER_MODEL,
                                DEFAULT_GEMINI_MODEL,
                                DEFAULT_OLLAMA_MODEL,
                                "meta-llama/llama-3.3-70b-instruct:free",
                            ]],
                            value=DEFAULT_OPENROUTER_MODEL,
                            id="param-model",
                            allow_blank=False
                        )
                        yield Button("🌐OR", id="btn-load-openrouter", classes="provider-btn")
                        yield Button("💎Gem", id="btn-load-gemini", classes="provider-btn")
                        yield Button("🦙Oll", id="btn-load-ollama", classes="provider-btn")
                    with Horizontal(classes="param-row"):
                        yield Label("Chunk:", classes="param-label")
                        yield Input(value="30000", id="param-chunk", classes="param-input")
                        yield Label("Limite:", classes="param-label")
                        yield Input(value="100", id="param-limit", classes="param-input")
                        yield Label("Low:", classes="param-label")
                        yield Input(value="2", id="param-low", classes="param-input")
                        yield Label("High:", classes="param-label")
                        yield Input(value="6", id="param-high", classes="param-input")
                
                # Console - occupa tutto lo spazio disponibile
                yield Log(id="console", highlight=True)
                
                # Controlli in basso
                with Horizontal(id="controls"):
                    yield Button("▶️ ESEGUI", id="btn-execute", variant="success")
                    yield Button("🛑 STOP", id="btn-stop", variant="error", disabled=True)
                    yield Button("🧹 CLEAR", id="btn-clear", variant="default")
                    yield Button("📋 BG", id="btn-background", variant="warning")
                    yield Button("⚡ AUTO: ON", id="btn-auto", variant="default")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Inizializzazione."""
        self.show_menu("main")
        self.call_later(self.log_message, "🚀 PTOF Launcher avviato")
        self.call_later(self.log_message, "   Seleziona un comando dal menu a sinistra")
    
    def show_menu(self, menu_id: str) -> None:
        """Mostra un menu specifico."""
        # Nascondi tutti i submenu
        for submenu in self.query(".submenu"):
            submenu.remove_class("visible")
        
        # Mostra/nascondi menu principale
        main_menu = self.query_one("#menu-main")
        if menu_id == "main":
            main_menu.styles.display = "block"
        else:
            main_menu.styles.display = "none"
            submenu = self.query_one(f"#submenu-{menu_id}")
            submenu.add_class("visible")
        
        self.current_menu = menu_id
    
    def log_message(self, msg: str) -> None:
        """Scrive nella console."""
        log = self.query_one("#console", Log)
        log.write(msg)
    
    @on(Button.Pressed)
    def handle_button(self, event: Button.Pressed) -> None:
        """Gestisce click sui bottoni."""
        try:
            self._handle_button_safe(event)
        except Exception as e:
            self.log_message(f"\n❌ Errore interfaccia: {e}")
            import traceback
            traceback.print_exc()

    def _handle_button_safe(self, event: Button.Pressed) -> None:
        """Logica gestione bottoni."""
        btn_id = event.button.id
        
        # Menu navigation
        if btn_id == "btn-back":
            self.show_menu("main")
            return
        
        menu_map = {
            "btn-quick": "quick",
            "btn-download": "download",
            "btn-workflow": "workflow",
            "btn-review": "review",
            "btn-registry": "registry",
            "btn-outreach": "outreach",
            "btn-models": "models",
            "btn-status": "status",
        }
        if btn_id in menu_map:
            self.show_menu(menu_map[btn_id])
            if btn_id == "btn-status":
                self.refresh_process_status()
            return
        
        # Controlli
        if btn_id == "btn-clear":
            self.query_one("#console", Log).clear()
            return
        
        if btn_id == "btn-stop":
            self.stop_current_process()
            return
        
        if btn_id == "btn-stop-all":
            self.stop_all_processes()
            return
        
        if btn_id == "btn-refresh-status":
            self.refresh_process_status()
            return
        
        if btn_id == "btn-execute":
            if self.current_command:
                self.execute_command(self.current_command, background=False)
            else:
                self.log_message("\n⚠️ Seleziona un comando (tasto verde) prima di eseguire")
            return
        
        if btn_id == "btn-background":
            if self.current_command:
                self.execute_command(self.current_command, background=True)
            else:
                self.log_message("\n⚠️ Seleziona un comando (tasto verde) prima di avviare in BG")
            return

        if btn_id == "btn-auto":
            self.auto_run_on_select = not self.auto_run_on_select
            label = "⚡ AUTO: ON" if self.auto_run_on_select else "⚡ AUTO: OFF"
            event.button.label = label
            return
        
        # Carica modelli
        if btn_id == "btn-load-openrouter":
            self.load_models("openrouter")
            return
        if btn_id == "btn-load-gemini":
            self.load_models("gemini")
            return
        if btn_id == "btn-load-ollama":
            self.load_models("ollama")
            return
        
        # Comandi - seleziona per esecuzione
        if btn_id.startswith("cmd-"):
            cmd = btn_id[4:]  # Rimuovi "cmd-"
            self.current_command = cmd
            self.log_message(f"\n📌 Selezionato: {cmd}")
            if self.auto_run_on_select:
                self.execute_command(cmd, background=False)
            else:
                self.log_message("   Configura i parametri in alto e premi ▶️ ESEGUI")
    
    def load_models(self, provider: str) -> None:
        """Carica modelli da provider."""
        self.log_message(f"\n📦 Caricamento modelli {provider}...")
        # Salva provider per il worker
        self._current_provider = provider
        self._load_models_worker()
    
    @work(thread=True, exclusive=True, group="models")
    def _load_models_worker(self) -> None:
        """Carica modelli in background."""
        provider = self._current_provider
        models = get_models_list(provider)
        self.call_from_thread(self._update_model_select, models, provider)
    
    def _update_model_select(self, models: List[str], provider: str) -> None:
        """Aggiorna il Select con i modelli."""
        if not models:
            self.log_message(f"   ⚠️ Nessun modello trovato per {provider}")
            return
        
        select = self.query_one("#param-model", Select)
        select.set_options([(m, m) for m in models])
        if models:
            select.value = models[0]
        self.log_message(f"   ✅ Caricati {len(models)} modelli {provider}")
    
    def get_command_args(self, cmd: str) -> List[str]:
        """Costruisce il comando make con i parametri."""
        args = ["make", cmd]
        
        # Parametri comuni
        n = self.query_one("#param-n", Input).value
        code = self.query_one("#param-code", Input).value
        regione = self.query_one("#param-regione", Input).value
        model = self.query_one("#param-model", Select).value
        chunk = self.query_one("#param-chunk", Input).value
        limit = self.query_one("#param-limit", Input).value
        low = self.query_one("#param-low", Input).value
        high = self.query_one("#param-high", Input).value
        
        # Aggiungi parametri in base al comando
        if cmd in ("download-strato",):
            if n:
                args.append(f"N={n}")
        
        if cmd in ("download-regione",):
            if regione:
                args.append(f"R={regione}")
        
        if cmd in ("run-force-code", "registry-remove"):
            if code:
                args.append(f"CODE={code}")
        
        if cmd in ("review-slow", "review-gemini", "review-ollama", 
                   "review-scores", "review-scores-gemini", "review-scores-ollama",
                   "ollama-score-review", "ollama-report-review", "ollama-review-all"):
            if model:
                args.append(f"MODEL={model}")
        
        if cmd in ("review-ollama", "review-scores-ollama"):
            if chunk:
                args.append(f"CHUNK_SIZE={chunk}")
        if cmd in ("ollama-score-review", "ollama-report-review", "ollama-review-all"):
            if chunk:
                args.append(f"CHUNK={chunk}")
        
        if cmd in ("review-ollama", "review-scores", "review-scores-gemini",
                   "review-scores-ollama", "review-non-ptof", "review-gemini",
                   "ollama-score-review", "ollama-report-review", "ollama-review-all"):
            if limit:
                args.append(f"LIMIT={limit}")
        
        if cmd in ("review-scores", "review-scores-gemini", "review-scores-ollama",
                   "ollama-score-review"):
            if low:
                args.append(f"LOW={low}")
            if high:
                args.append(f"HIGH={high}")
        
        if cmd in ("review-ollama", "review-scores", "review-scores-gemini",
                   "review-scores-ollama", "review-gemini",
                   "ollama-score-review", "ollama-report-review", "ollama-review-all"):
            if code:
                args.append(f"TARGET={code}")
        
        return args
    
    def execute_command(self, cmd: str, background: bool = False) -> None:
        """Esegue il comando."""
        args = self.get_command_args(cmd)
        
        self.log_message(f"\n🚀 Eseguo: {' '.join(args)}")
        
        if background:
            self.run_background(args, cmd)
        else:
            self.run_foreground(args)
    
    def run_foreground(self, cmd: List[str]) -> None:
        """Esegue in foreground."""
        self.query_one("#btn-stop").disabled = False
        self.query_one("#btn-execute").disabled = True
        self._pending_cmd = cmd
        self._run_subprocess()
    
    @work(thread=True, exclusive=True, group="cmd")
    def _run_subprocess(self) -> None:
        """Worker per subprocess."""
        cmd = self._pending_cmd
        if not cmd:
            return
        
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        
        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env,
                cwd=BASE_DIR,
                preexec_fn=os.setsid if os.name != 'nt' else None
            )
            
            while True:
                line = self.process.stdout.readline()
                if not line and self.process.poll() is not None:
                    break
                if line:
                    self.call_from_thread(self.log_message, line.rstrip())
            
            rc = self.process.poll()
            if rc == 0:
                self.call_from_thread(self.log_message, "\n✅ Completato con successo")
            else:
                self.call_from_thread(self.log_message, f"\n⚠️ Terminato con codice {rc}")
                
        except Exception as e:
            self.call_from_thread(self.log_message, f"\n❌ Errore: {e}")
        finally:
            self.process = None
            self.call_from_thread(self._enable_execute)
    
    def _enable_execute(self) -> None:
        """Riabilita il pulsante esegui."""
        self.query_one("#btn-stop").disabled = True
        self.query_one("#btn-execute").disabled = False
    
    def run_background(self, cmd: List[str], name: str) -> None:
        """Esegue in background."""
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        
        log_dir = BASE_DIR / "logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"{name}.log"
        
        with open(log_file, 'w') as log:
            process = subprocess.Popen(
                cmd,
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
                cwd=BASE_DIR,
                preexec_fn=os.setsid if os.name != 'nt' else None
            )
        
        with PROCESS_LOCK:
            RUNNING_PROCESSES[name] = process
        
        self.log_message(f"\n🚀 Avviato in background: {name} (PID: {process.pid})")
        self.log_message(f"   Log: {log_file}")
    
    def stop_current_process(self) -> None:
        """Ferma il processo corrente."""
        if self.process:
            self.log_message("\n🛑 Interruzione processo...")
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            except Exception as e:
                self.log_message(f"   Errore: {e}")
                try:
                    self.process.terminate()
                except:
                    pass
    
    def stop_all_processes(self) -> None:
        """Ferma tutti i processi background."""
        with PROCESS_LOCK:
            for name, proc in list(RUNNING_PROCESSES.items()):
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                    proc.wait(timeout=2)
                    self.log_message(f"🛑 Fermato: {name}")
                except:
                    proc.kill()
                    self.log_message(f"⚠️ Terminato forzatamente: {name}")
            RUNNING_PROCESSES.clear()
        self.refresh_process_status()
    
    def refresh_process_status(self) -> None:
        """Aggiorna lista processi."""
        status_widget = self.query_one("#process-list", Static)
        
        with PROCESS_LOCK:
            # Pulisci processi terminati
            for name, proc in list(RUNNING_PROCESSES.items()):
                if proc.poll() is not None:
                    del RUNNING_PROCESSES[name]
            
            if not RUNNING_PROCESSES:
                status_widget.update("   Nessun processo attivo")
            else:
                lines = []
                for name, proc in RUNNING_PROCESSES.items():
                    lines.append(f"   🟢 {name} (PID: {proc.pid})")
                status_widget.update("\n".join(lines))
    
    def action_quit(self) -> None:
        """Azione esci."""
        self.stop_all_processes()
        self.exit()
    
    def action_back(self) -> None:
        """Torna al menu principale."""
        self.show_menu("main")
    
    def action_stop_current(self) -> None:
        """Stop da shortcut."""
        self.stop_current_process()


if __name__ == "__main__":
    app = PTOFLauncher()
    app.run()
