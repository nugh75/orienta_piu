#!/usr/bin/env python3
"""
PTOF Launcher - CLI interattivo per gestire tutti i processi del progetto.
Stile wizard con menu numerati e monitoraggio processi.
"""

import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ═══════════════════════════════════════════════════════════════════
# CONFIGURAZIONE
# ═══════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).resolve().parent
MODEL_LISTER = BASE_DIR / "src" / "utils" / "list_models.py"

DEFAULT_OPENROUTER_MODEL = "google/gemini-2.0-flash-exp:free"
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash-exp"
DEFAULT_OLLAMA_MODEL = "qwen3:32b"
DEFAULT_OLLAMA_URL = "http://192.168.129.14:11434"
DEFAULT_OLLAMA_CHUNK_SIZE = 30000
DEFAULT_OLLAMA_WAIT = 2

# Processi attivi (per monitoraggio)
RUNNING_PROCESSES: Dict[str, subprocess.Popen] = {}
PROCESS_LOCK = threading.Lock()


# ═══════════════════════════════════════════════════════════════════
# UTILITY DI INPUT
# ═══════════════════════════════════════════════════════════════════

def clear_screen():
    """Pulisce lo schermo."""
    os.system('clear' if os.name != 'nt' else 'cls')


def print_header():
    """Stampa header del launcher."""
    print("\n" + "═" * 60)
    print("  🚀 PTOF LAUNCHER - Gestione Processi")
    print("═" * 60)


def prompt_choice(title: str, options: List[Tuple[str, str]], allow_back: bool = True) -> Optional[str]:
    """Mostra menu numerato e restituisce la scelta."""
    print("")
    print(f"📋 {title}")
    print("-" * 40)
    for idx, (label, _) in enumerate(options, 1):
        print(f"  {idx:2}) {label}")
    if allow_back:
        print("   b) Indietro")
    print("   q) Esci")
    print("")
    
    while True:
        choice = input("Scelta > ").strip().lower()
        if choice in {"q", "quit", "exit"}:
            cleanup_all_processes()
            raise SystemExit(0)
        if allow_back and choice in {"b", "back", ""}:
            return None
        if choice.isdigit():
            index = int(choice)
            if 1 <= index <= len(options):
                return options[index - 1][1]
        print("❌ Scelta non valida. Riprova.")


def prompt_text(label: str, default: Optional[str] = None) -> Optional[str]:
    """Richiede input testuale."""
    suffix = f" [{default}]" if default else ""
    value = input(f"{label}{suffix}: ").strip()
    if not value:
        return default
    return value


def prompt_int(label: str, default: Optional[int] = None) -> Optional[int]:
    """Richiede input numerico."""
    while True:
        suffix = f" [{default}]" if default is not None else ""
        value = input(f"{label}{suffix}: ").strip()
        if not value:
            return default
        try:
            return int(value)
        except ValueError:
            print("❌ Inserisci un numero valido.")


def prompt_yes_no(label: str, default: bool = False) -> bool:
    """Richiede conferma sì/no."""
    suffix = " [Y/n]" if default else " [y/N]"
    value = input(f"{label}{suffix}: ").strip().lower()
    if not value:
        return default
    return value in {"y", "yes", "1", "si", "s"}


# ═══════════════════════════════════════════════════════════════════
# GESTIONE PROCESSI
# ═══════════════════════════════════════════════════════════════════

def run_make(target: str, variables: Optional[Dict[str, str]] = None, 
             background: bool = False, name: Optional[str] = None) -> Optional[subprocess.Popen]:
    """
    Esegue un target make.
    
    Args:
        target: Nome del target make
        variables: Variabili da passare (es. {"N": "5"})
        background: Se True, esegue in background
        name: Nome per identificare il processo
    """
    variables = variables or {}
    cmd = ["make", target]
    for key, value in variables.items():
        if value is None:
            continue
        value_str = str(value).strip()
        if value_str:
            cmd.append(f"{key}={value_str}")

    print("")
    print("📌 Comando:")
    print(f"   {' '.join(cmd)}")
    print("")
    
    if not prompt_yes_no("Eseguire?", default=True):
        return None
    
    if background:
        return run_background(cmd, name or target)
    else:
        return run_foreground(cmd)


def run_foreground(cmd: List[str]) -> None:
    """Esegue comando in foreground con output live."""
    print("")
    print("▶️ Avvio processo...")
    print("   (Ctrl+C per interrompere)")
    print("-" * 50)
    
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
            cwd=BASE_DIR,
            preexec_fn=os.setsid if os.name != 'nt' else None
        )
        
        # Leggi output in tempo reale
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                print(line.rstrip())
        
        rc = process.poll()
        print("-" * 50)
        if rc == 0:
            print(f"✅ Processo completato con successo")
        else:
            print(f"⚠️ Processo terminato con codice {rc}")
            
    except KeyboardInterrupt:
        print("\n🛑 Interruzione richiesta...")
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        except:
            process.terminate()
        process.wait()
        print("✅ Processo interrotto")


def run_background(cmd: List[str], name: str) -> subprocess.Popen:
    """Esegue comando in background."""
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    
    log_file = BASE_DIR / "logs" / f"{name}.log"
    log_file.parent.mkdir(exist_ok=True)
    
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
    
    print(f"🚀 Processo '{name}' avviato in background (PID: {process.pid})")
    print(f"   Log: {log_file}")
    return process


def stop_process(name: str) -> bool:
    """Ferma un processo in background."""
    with PROCESS_LOCK:
        if name not in RUNNING_PROCESSES:
            print(f"❌ Processo '{name}' non trovato")
            return False
        
        process = RUNNING_PROCESSES[name]
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            process.wait(timeout=5)
            print(f"✅ Processo '{name}' fermato")
        except:
            process.kill()
            print(f"⚠️ Processo '{name}' terminato forzatamente")
        
        del RUNNING_PROCESSES[name]
        return True


def cleanup_all_processes():
    """Ferma tutti i processi in background."""
    with PROCESS_LOCK:
        for name, process in list(RUNNING_PROCESSES.items()):
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                process.wait(timeout=2)
            except:
                process.kill()
            print(f"🛑 Fermato: {name}")
        RUNNING_PROCESSES.clear()


def get_process_status() -> List[Tuple[str, str, int]]:
    """Restituisce stato dei processi."""
    result = []
    with PROCESS_LOCK:
        for name, process in list(RUNNING_PROCESSES.items()):
            poll = process.poll()
            if poll is None:
                status = "🟢 Running"
            else:
                status = f"🔴 Stopped (code {poll})"
                del RUNNING_PROCESSES[name]
            result.append((name, status, process.pid))
    return result


# ═══════════════════════════════════════════════════════════════════
# SELEZIONE MODELLI
# ═══════════════════════════════════════════════════════════════════

def get_models_list(args: List[str]) -> List[str]:
    """Recupera lista modelli."""
    if not MODEL_LISTER.exists():
        return []
    cmd = [sys.executable, str(MODEL_LISTER)] + args
    result = subprocess.run(cmd, cwd=BASE_DIR, text=True, capture_output=True, check=False)
    output = result.stdout.strip()
    if not output:
        return []
    return [line.strip() for line in output.split("\n") if line.strip()]


def prompt_model_choice(provider: str, default: str, free_only: bool = True) -> str:
    """Mostra lista modelli e permette selezione."""
    print(f"\n📦 Recupero modelli {provider}...")
    
    if provider == "ollama":
        models = [
            "qwen3:32b", "qwen3:14b", "qwen3:8b",
            "llama3.3:70b", "llama3.2:latest",
            "mistral:latest", "deepseek-r1:32b",
            "gemma2:27b", "phi3:medium",
        ]
    elif provider == "openrouter":
        args = ["--openrouter"]
        if free_only:
            args.append("--free-only")
        models = get_models_list(args)
    elif provider == "gemini":
        models = get_models_list(["--gemini"])
    else:
        return default
    
    if not models:
        print(f"⚠️ Nessun modello trovato. Uso default: {default}")
        return default
    
    # Default in cima
    if default in models:
        models.remove(default)
        models.insert(0, default)
    
    print(f"\n🤖 Modelli {provider} ({len(models)} disponibili):")
    for idx, model in enumerate(models, 1):
        marker = " ← default" if model == default else ""
        print(f"  {idx:3}) {model}{marker}")
    
    print(f"\n  d) Usa default ({default})")
    print(f"  m) Digita manualmente")
    
    while True:
        choice = input("> ").strip().lower()
        if choice in {"d", ""}:
            return default
        if choice == "m":
            manual = input("Nome modello: ").strip()
            return manual if manual else default
        if choice.isdigit():
            index = int(choice)
            if 1 <= index <= len(models):
                return models[index - 1]
        print("❌ Scelta non valida.")


# ═══════════════════════════════════════════════════════════════════
# MENU PRINCIPALE
# ═══════════════════════════════════════════════════════════════════

def menu_status():
    """Mostra stato processi."""
    clear_screen()
    print_header()
    print("\n📊 STATO PROCESSI")
    print("-" * 50)
    
    processes = get_process_status()
    
    if not processes:
        print("   Nessun processo in esecuzione")
    else:
        for name, status, pid in processes:
            print(f"   {status} {name} (PID: {pid})")
    
    print("-" * 50)
    
    if processes:
        options = [("Ferma un processo", "stop"), ("Ferma tutti", "stop_all"), ("Aggiorna", "refresh")]
        choice = prompt_choice("Azioni", options)
        
        if choice == "stop":
            name = prompt_text("Nome processo da fermare")
            if name:
                stop_process(name)
        elif choice == "stop_all":
            if prompt_yes_no("Fermare tutti i processi?", default=False):
                cleanup_all_processes()
        elif choice == "refresh":
            menu_status()


def menu_download():
    """Menu download PTOF."""
    options = [
        ("📊 Dry-run (mostra stratificazione)", "download"),
        ("📥 Sample stratificato (5 per strato)", "download-sample"),
        ("📥 Stratificato con N scuole", "download-strato"),
        ("🏛️ Tutte scuole statali", "download-statali"),
        ("🏫 Tutte scuole paritarie", "download-paritarie"),
        ("🗺️ Per regione", "download-regione"),
        ("🏙️ Solo metropolitane", "download-metro"),
        ("🌾 Solo non metropolitane", "download-non-metro"),
        ("📚 Per grado", "download-grado"),
        ("🧭 Per area geografica", "download-area"),
        ("🔄 Reset stato download", "download-reset"),
    ]
    choice = prompt_choice("DOWNLOAD PTOF", options)
    if not choice:
        return

    if choice == "download-strato":
        n = prompt_int("Scuole per strato", default=5)
        run_make(choice, {"N": n})
    elif choice == "download-regione":
        regione = prompt_text("Regione (es: LAZIO)")
        run_make(choice, {"R": regione})
    elif choice == "download-grado":
        grado = prompt_text("Grado (INFANZIA/PRIMARIA/SEC_PRIMO/SEC_SECONDO)")
        run_make(choice, {"G": grado})
    elif choice == "download-area":
        area = prompt_text("Area (NORD OVEST/NORD EST/CENTRO/SUD/ISOLE)")
        run_make(choice, {"A": area})
    else:
        run_make(choice)


def menu_workflow():
    """Menu workflow analisi."""
    options = [
        ("▶️ Avvia workflow", "run"),
        ("🔄 Workflow force (ri-analizza tutto)", "run-force"),
        ("🎯 Workflow force su codice specifico", "run-force-code"),
        ("📊 Dashboard Streamlit", "dashboard"),
        ("📈 Rigenera CSV + Geocoding", "csv"),
        ("🔧 Backfill metadati LLM", "backfill"),
        ("🧹 Pulisci cache", "clean"),
        ("♻️ Recupera not_ptof con _ok", "recover-not-ptof"),
        ("🔗 Refresh (csv + dashboard)", "refresh"),
        ("🚀 Full pipeline (run + csv + dashboard)", "full"),
        ("⏱️ CSV watch (rigenera ogni N sec)", "csv-watch"),
    ]
    choice = prompt_choice("WORKFLOW ANALISI", options)
    if not choice:
        return

    if choice == "run-force-code":
        code = prompt_text("Codice meccanografico")
        run_make(choice, {"CODE": code})
    elif choice == "csv-watch":
        interval = prompt_int("Intervallo (secondi)", default=300)
        bg = prompt_yes_no("Eseguire in background?", default=False)
        run_make(choice, {"INTERVAL": interval}, background=bg, name="csv-watch")
    elif choice == "dashboard":
        bg = prompt_yes_no("Eseguire in background?", default=True)
        run_make(choice, background=bg, name="dashboard")
    else:
        run_make(choice)


def menu_review():
    """Menu revisione."""
    options = [
        ("🐢 Review slow (OpenRouter)", "review-slow"),
        ("💎 Review Gemini", "review-gemini"),
        ("🦙 Review Ollama (report)", "review-ollama"),
        ("📊 Review scores (OpenRouter)", "review-scores"),
        ("📊 Review scores Gemini", "review-scores-gemini"),
        ("📊 Review scores Ollama", "review-scores-ollama"),
        ("🦙 Ollama Score Review", "ollama-score-review"),
        ("🦙 Ollama Report Review", "ollama-report-review"),
        ("🦙 Ollama Review All", "ollama-review-all"),
        ("🗑️ Review non-PTOF", "review-non-ptof"),
    ]
    choice = prompt_choice("REVISIONE AI", options)
    if not choice:
        return

    # OpenRouter
    if choice == "review-slow":
        free_only = prompt_yes_no("Solo modelli free?", default=True)
        model = prompt_model_choice("openrouter", DEFAULT_OPENROUTER_MODEL, free_only)
        run_make(choice, {"MODEL": model})
        return

    # Gemini
    if choice == "review-gemini":
        model = prompt_model_choice("gemini", DEFAULT_GEMINI_MODEL)
        run_make(choice, {"MODEL": model})
        return

    # Ollama report
    if choice in ("review-ollama", "ollama-report-review"):
        model = prompt_model_choice("ollama", DEFAULT_OLLAMA_MODEL)
        chunk = prompt_int("Chunk size", default=DEFAULT_OLLAMA_CHUNK_SIZE)
        wait = prompt_int("Wait (sec)", default=DEFAULT_OLLAMA_WAIT)
        limit = prompt_int("Limite file", default=100)
        target = prompt_text("Target codice (opzionale)")
        run_make(choice, {
            "MODEL": model, "CHUNK": chunk, "WAIT": wait,
            "LIMIT": limit, "TARGET": target
        })
        return

    # Ollama score
    if choice in ("review-scores-ollama", "ollama-score-review"):
        model = prompt_model_choice("ollama", DEFAULT_OLLAMA_MODEL)
        chunk = prompt_int("Chunk size", default=DEFAULT_OLLAMA_CHUNK_SIZE)
        low = prompt_int("Soglia bassa", default=2)
        high = prompt_int("Soglia alta", default=6)
        wait = prompt_int("Wait (sec)", default=DEFAULT_OLLAMA_WAIT)
        limit = prompt_int("Limite file", default=100)
        target = prompt_text("Target codice (opzionale)")
        run_make(choice, {
            "MODEL": model, "CHUNK": chunk, "LOW": low, "HIGH": high,
            "WAIT": wait, "LIMIT": limit, "TARGET": target
        })
        return

    # Ollama all
    if choice == "ollama-review-all":
        model = prompt_model_choice("ollama", DEFAULT_OLLAMA_MODEL)
        limit = prompt_int("Limite file", default=100)
        target = prompt_text("Target codice (opzionale)")
        run_make(choice, {"MODEL": model, "LIMIT": limit, "TARGET": target})
        return

    # OpenRouter scores
    if choice == "review-scores":
        free_only = prompt_yes_no("Solo modelli free?", default=True)
        model = prompt_model_choice("openrouter", DEFAULT_OPENROUTER_MODEL, free_only)
        low = prompt_int("Soglia bassa", default=2)
        high = prompt_int("Soglia alta", default=6)
        target = prompt_text("Target codice (opzionale)")
        run_make(choice, {"MODEL": model, "LOW": low, "HIGH": high, "TARGET": target})
        return

    # Gemini scores
    if choice == "review-scores-gemini":
        model = prompt_model_choice("gemini", DEFAULT_GEMINI_MODEL)
        low = prompt_int("Soglia bassa", default=2)
        high = prompt_int("Soglia alta", default=6)
        target = prompt_text("Target codice (opzionale)")
        run_make(choice, {"MODEL": model, "LOW": low, "HIGH": high, "TARGET": target})
        return

    # Non-PTOF
    if choice == "review-non-ptof":
        target = prompt_text("Target codice (opzionale)")
        dry = prompt_yes_no("Dry-run?", default=True)
        limit = prompt_int("Limite file (opzionale)")
        run_make(choice, {
            "TARGET": target, "DRY": "1" if dry else None, "LIMIT": limit
        })


def menu_registry():
    """Menu registro analisi."""
    options = [
        ("📊 Stato registro", "registry-status"),
        ("📋 Lista registro", "registry-list"),
        ("🗑️ Pulisci registro", "registry-clear"),
        ("❌ Rimuovi entry", "registry-remove"),
    ]
    choice = prompt_choice("REGISTRO ANALISI", options)
    if not choice:
        return

    if choice == "registry-remove":
        code = prompt_text("Codice meccanografico")
        run_make(choice, {"CODE": code})
    else:
        run_make(choice)


def menu_outreach():
    """Menu outreach."""
    options = [
        ("🌐 Avvia portale upload", "outreach-portal"),
        ("📧 Invia email PTOF", "outreach-email"),
    ]
    choice = prompt_choice("OUTREACH PTOF", options)
    if not choice:
        return

    if choice == "outreach-portal":
        port = prompt_int("Porta", default=8502)
        bg = prompt_yes_no("Eseguire in background?", default=True)
        run_make(choice, {"PORT": port}, background=bg, name="outreach-portal")
    elif choice == "outreach-email":
        base_url = prompt_text("Base URL portale")
        limit = prompt_int("Limite invii (opzionale)")
        send = prompt_yes_no("Invio reale?", default=False)
        run_make(choice, {
            "BASE_URL": base_url, "LIMIT": limit,
            "SEND": "1" if send else None
        })


def menu_models():
    """Menu lista modelli."""
    options = [
        ("📦 Preset locali (config)", "config"),
        ("🌐 OpenRouter", "openrouter"),
        ("💎 Gemini", "gemini"),
    ]
    choice = prompt_choice("LISTA MODELLI AI", options)
    if not choice:
        return

    if choice == "config":
        subprocess.run([sys.executable, str(MODEL_LISTER), "--config"], cwd=BASE_DIR)
    elif choice == "openrouter":
        free = prompt_yes_no("Solo modelli free?", default=True)
        args = [sys.executable, str(MODEL_LISTER), "--openrouter"]
        if free:
            args.append("--free-only")
        subprocess.run(args, cwd=BASE_DIR)
    elif choice == "gemini":
        subprocess.run([sys.executable, str(MODEL_LISTER), "--gemini"], cwd=BASE_DIR)


def menu_quick():
    """Menu azioni rapide."""
    options = [
        ("🚀 Pipeline completo (download + run + csv + dashboard)", "pipeline"),
        ("🔄 Full (run + csv + dashboard)", "full"),
        ("📊 Refresh (csv + dashboard)", "refresh"),
        ("▶️ Solo workflow", "run"),
        ("📊 Solo dashboard", "dashboard"),
    ]
    choice = prompt_choice("AZIONI RAPIDE", options)
    if not choice:
        return
    
    if choice == "dashboard":
        bg = prompt_yes_no("Eseguire in background?", default=True)
        run_make(choice, background=bg, name="dashboard")
    else:
        run_make(choice)


def main_menu():
    """Menu principale."""
    while True:
        clear_screen()
        print_header()
        
        # Mostra processi attivi
        processes = get_process_status()
        if processes:
            print(f"\n🟢 Processi attivi: {len(processes)}")
            for name, status, pid in processes:
                print(f"   • {name} (PID: {pid})")
        
        options = [
            ("⚡ Azioni rapide", "quick"),
            ("📥 Download PTOF", "download"),
            ("🔄 Workflow analisi", "workflow"),
            ("🤖 Revisione AI", "review"),
            ("📋 Registro analisi", "registry"),
            ("📬 Outreach PTOF", "outreach"),
            ("🤖 Lista modelli AI", "models"),
            ("📊 Stato processi", "status"),
        ]
        
        choice = prompt_choice("MENU PRINCIPALE", options, allow_back=False)
        
        if choice == "quick":
            menu_quick()
        elif choice == "download":
            menu_download()
        elif choice == "workflow":
            menu_workflow()
        elif choice == "review":
            menu_review()
        elif choice == "registry":
            menu_registry()
        elif choice == "outreach":
            menu_outreach()
        elif choice == "models":
            menu_models()
        elif choice == "status":
            menu_status()


def main():
    """Entry point."""
    # Controlla make
    import shutil
    if not shutil.which("make"):
        print("❌ 'make' non trovato nel PATH.")
        sys.exit(1)
    
    print("🚀 PTOF Launcher")
    print("   Premi Ctrl+C per uscire")
    
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n\n🛑 Uscita...")
        cleanup_all_processes()
        print("👋 Arrivederci!")


if __name__ == "__main__":
    main()
