#!/usr/bin/env python3
"""
Interactive CLI to run Make targets with guided prompts.
"""

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


BASE_DIR = Path(__file__).resolve().parent.parent.parent
MODEL_LISTER = BASE_DIR / "src" / "utils" / "list_models.py"

DEFAULT_OPENROUTER_MODEL = "google/gemini-2.0-flash-exp:free"
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash-exp"
DEFAULT_OLLAMA_MODEL = "qwen3:32b"
DEFAULT_OLLAMA_URL = "http://192.168.129.14:11434"
DEFAULT_OLLAMA_CHUNK_SIZE = 30000
DEFAULT_OLLAMA_WAIT = 2


def prompt_choice(title: str, options: List[Tuple[str, str]], allow_back: bool = True) -> Optional[str]:
    print("")
    print(title)
    for idx, (label, _) in enumerate(options, 1):
        print(f"  {idx}) {label}")
    if allow_back:
        print("  b) Indietro")
    print("  q) Esci")
    while True:
        choice = input("> ").strip().lower()
        if choice in {"q", "quit", "exit"}:
            raise SystemExit(0)
        if allow_back and choice in {"b", "back"}:
            return None
        if choice.isdigit():
            index = int(choice)
            if 1 <= index <= len(options):
                return options[index - 1][1]
        print("Scelta non valida. Riprova.")


def prompt_text(label: str, default: Optional[str] = None) -> Optional[str]:
    suffix = f" [default: {default}]" if default else ""
    value = input(f"{label}{suffix}: ").strip()
    if not value:
        return default
    return value


def prompt_int(label: str, default: Optional[int] = None) -> Optional[int]:
    while True:
        suffix = f" [default: {default}]" if default is not None else ""
        value = input(f"{label}{suffix}: ").strip()
        if not value:
            return default
        try:
            return int(value)
        except ValueError:
            print("Inserisci un numero valido.")


def prompt_yes_no(label: str, default: bool = False) -> bool:
    suffix = " [Y/n]" if default else " [y/N]"
    value = input(f"{label}{suffix}: ").strip().lower()
    if not value:
        return default
    return value in {"y", "yes", "1", "si"}


def run_make(target: str, variables: Optional[Dict[str, str]] = None) -> None:
    variables = variables or {}
    cmd = ["make", target]
    for key, value in variables.items():
        if value is None:
            continue
        value_str = str(value).strip()
        if value_str == "":
            continue
        cmd.append(f"{key}={value_str}")

    print("")
    print("Comando:")
    print("  " + " ".join(cmd))
    if not prompt_yes_no("Eseguire il comando?", default=False):
        return
    subprocess.run(cmd, cwd=BASE_DIR, check=False)


def show_models(args: List[str]) -> None:
    if not MODEL_LISTER.exists():
        print("Script modelli non trovato:", MODEL_LISTER)
        return
    cmd = [sys.executable, str(MODEL_LISTER)] + args + ["--prefix", " - "]
    result = subprocess.run(cmd, cwd=BASE_DIR, text=True, capture_output=True, check=False)
    output = result.stdout.strip()
    if output:
        print(output)
    else:
        print("(nessun modello trovato)")
        if result.stderr:
            print(result.stderr.strip())


def menu_download() -> None:
    options = [
        ("Dry-run stratificazione", "download"),
        ("Sample per strato", "download-sample"),
        ("Stratificato con N", "download-strato"),
        ("Tutte statali", "download-statali"),
        ("Tutte paritarie", "download-paritarie"),
        ("Per regione", "download-regione"),
        ("Solo metropolitane", "download-metro"),
        ("Solo non metropolitane", "download-non-metro"),
        ("Per grado", "download-grado"),
        ("Per area geografica", "download-area"),
        ("Reset stato download", "download-reset"),
    ]
    choice = prompt_choice("Download PTOF - scegli operazione", options)
    if not choice:
        return

    if choice == "download-strato":
        n = prompt_int("Numero scuole per strato", default=5)
        run_make(choice, {"N": n})
    elif choice == "download-regione":
        regione = prompt_text("Regione (es: LAZIO)")
        run_make(choice, {"R": regione})
    elif choice == "download-grado":
        grado = prompt_text("Grado (INFANZIA/PRIMARIA/SEC_PRIMO/SEC_SECONDO/ALTRO)")
        run_make(choice, {"G": grado})
    elif choice == "download-area":
        area = prompt_text("Area (NORD OVEST/NORD EST/CENTRO/SUD/ISOLE)")
        run_make(choice, {"A": area})
    else:
        run_make(choice)


def menu_workflow() -> None:
    options = [
        ("Run workflow", "run"),
        ("Run force", "run-force"),
        ("Run force su codice", "run-force-code"),
        ("Dashboard", "dashboard"),
        ("Rigenera CSV + Geo", "csv"),
        ("Backfill metadati", "backfill"),
        ("Clean cache", "clean"),
        ("Recupera not_ptof con _ok (sposta in inbox)", "recover-not-ptof"),
        ("Refresh (csv + dashboard)", "refresh"),
        ("Full (run + csv + dashboard)", "full"),
        ("Pipeline (download sample + run + csv + dashboard)", "pipeline"),
        ("CSV watch", "csv-watch"),
    ]
    choice = prompt_choice("Workflow - scegli operazione", options)
    if not choice:
        return

    if choice == "run-force-code":
        code = prompt_text("Codice meccanografico")
        run_make(choice, {"CODE": code})
    elif choice == "csv-watch":
        interval = prompt_int("Intervallo secondi", default=300)
        run_make(choice, {"INTERVAL": interval})
    else:
        run_make(choice)


def menu_review() -> None:
    options = [
        ("Review slow (OpenRouter)", "review-slow"),
        ("Review gemini", "review-gemini"),
        ("Review ollama (report)", "review-ollama"),
        ("Review scores (OpenRouter)", "review-scores"),
        ("Review scores gemini", "review-scores-gemini"),
        ("Review scores ollama", "review-scores-ollama"),
        ("Review non-ptof", "review-non-ptof"),
    ]
    choice = prompt_choice("Review - scegli operazione", options)
    if not choice:
        return

    if choice == "review-slow":
        if prompt_yes_no("Mostrare lista modelli OpenRouter?", default=False):
            free_only = prompt_yes_no("Solo modelli free?", default=True)
            args = ["--openrouter"]
            if free_only:
                args.append("--free-only")
            show_models(args)
        model = prompt_text("Modello OpenRouter", default=DEFAULT_OPENROUTER_MODEL)
        run_make(choice, {"MODEL": model})
        return

    if choice == "review-gemini":
        if prompt_yes_no("Mostrare lista modelli Gemini?", default=False):
            show_models(["--gemini"])
        model = prompt_text("Modello Gemini", default=DEFAULT_GEMINI_MODEL)
        run_make(choice, {"MODEL": model})
        return

    if choice == "review-ollama":
        model = prompt_text("Modello Ollama", default=DEFAULT_OLLAMA_MODEL)
        ollama_url = prompt_text("URL Ollama", default=DEFAULT_OLLAMA_URL)
        chunk_size = prompt_int("Chunk size", default=DEFAULT_OLLAMA_CHUNK_SIZE)
        wait = prompt_int("Attesa secondi tra chiamate", default=DEFAULT_OLLAMA_WAIT)
        limit = prompt_int("Limite file", default=100)
        target = prompt_text("Target codice (opzionale)")
        run_make(
            choice,
            {
                "MODEL": model,
                "OLLAMA_URL": ollama_url,
                "CHUNK_SIZE": chunk_size,
                "WAIT": wait,
                "LIMIT": limit,
                "TARGET": target,
            },
        )
        return

    if choice in {"review-scores", "review-scores-gemini"}:
        if choice == "review-scores":
            if prompt_yes_no("Mostrare lista modelli OpenRouter?", default=False):
                free_only = prompt_yes_no("Solo modelli free?", default=True)
                args = ["--openrouter"]
                if free_only:
                    args.append("--free-only")
                show_models(args)
            model_default = DEFAULT_OPENROUTER_MODEL
        else:
            if prompt_yes_no("Mostrare lista modelli Gemini?", default=False):
                show_models(["--gemini"])
            model_default = DEFAULT_GEMINI_MODEL

        model = prompt_text("Modello", default=model_default)
        low = prompt_int("Soglia bassa", default=2)
        high = prompt_int("Soglia alta", default=6)
        target = prompt_text("Target codice (opzionale)")
        wait = prompt_int("Attesa secondi tra richieste (opzionale)")
        limit = prompt_int("Limite file (opzionale)")
        max_chars = prompt_int("Max chars prompt (opzionale)")
        run_make(
            choice,
            {
                "MODEL": model,
                "LOW": low,
                "HIGH": high,
                "TARGET": target,
                "WAIT": wait,
                "LIMIT": limit,
                "MAX_CHARS": max_chars,
            },
        )
        return

    if choice == "review-scores-ollama":
        model = prompt_text("Modello Ollama", default=DEFAULT_OLLAMA_MODEL)
        ollama_url = prompt_text("URL Ollama", default=DEFAULT_OLLAMA_URL)
        chunk_size = prompt_int("Chunk size", default=DEFAULT_OLLAMA_CHUNK_SIZE)
        low = prompt_int("Soglia bassa", default=2)
        high = prompt_int("Soglia alta", default=6)
        wait = prompt_int("Attesa secondi tra chiamate", default=DEFAULT_OLLAMA_WAIT)
        limit = prompt_int("Limite file", default=100)
        target = prompt_text("Target codice (opzionale)")
        run_make(
            choice,
            {
                "MODEL": model,
                "OLLAMA_URL": ollama_url,
                "CHUNK_SIZE": chunk_size,
                "LOW": low,
                "HIGH": high,
                "WAIT": wait,
                "LIMIT": limit,
                "TARGET": target,
            },
        )
        return

    if choice == "review-non-ptof":
        target = prompt_text("Target codice (opzionale)")
        dry = prompt_yes_no("Dry-run?", default=True)
        no_llm = prompt_yes_no("No LLM?", default=False)
        no_move = prompt_yes_no("Non spostare PDF?", default=False)
        limit = prompt_int("Limite file (opzionale)")
        run_make(
            choice,
            {
                "TARGET": target,
                "DRY": "1" if dry else None,
                "NO_LLM": "1" if no_llm else None,
                "NO_MOVE": "1" if no_move else None,
                "LIMIT": limit,
            },
        )


def menu_outreach() -> None:
    options = [
        ("Avvia portale upload", "outreach-portal"),
        ("Invia email PTOF", "outreach-email"),
    ]
    choice = prompt_choice("Outreach PTOF - scegli operazione", options)
    if not choice:
        return

    if choice == "outreach-portal":
        port = prompt_int("Porta", default=8502)
        run_make(choice, {"PORT": port})
        return

    if choice == "outreach-email":
        base_url = prompt_text("Base URL portale upload (es: https://example.org)")
        limit = prompt_int("Limite invii (opzionale)")
        send = prompt_yes_no("Invio reale?", default=False)
        use_pec = prompt_yes_no("Usa PEC se email assente?", default=False)
        template = prompt_text("Template email (opzionale)")
        subject = prompt_text("Oggetto email (opzionale)")
        signature = prompt_text("Firma email (opzionale)")
        csv_list = prompt_text("CSV lista scuole (spazi per piu file, opzionale)")
        run_make(
            choice,
            {
                "BASE_URL": base_url,
                "LIMIT": limit,
                "SEND": "1" if send else None,
                "USE_PEC": "1" if use_pec else None,
                "TEMPLATE": template,
                "SUBJECT": subject,
                "SIGNATURE": signature,
                "CSV": csv_list,
            },
        )


def menu_registry() -> None:
    options = [
        ("Stato registro", "registry-status"),
        ("Lista registro", "registry-list"),
        ("Pulisci registro", "registry-clear"),
        ("Rimuovi entry per codice", "registry-remove"),
    ]
    choice = prompt_choice("Registro analisi - scegli operazione", options)
    if not choice:
        return

    if choice == "registry-remove":
        code = prompt_text("Codice meccanografico")
        run_make(choice, {"CODE": code})
    else:
        run_make(choice)


def menu_models() -> None:
    options = [
        ("Preset locali (config)", "config"),
        ("OpenRouter", "openrouter"),
        ("Gemini", "gemini"),
    ]
    choice = prompt_choice("Lista modelli AI", options)
    if not choice:
        return

    if choice == "config":
        show_models(["--config"])
        return
    if choice == "openrouter":
        free_only = prompt_yes_no("Solo modelli free?", default=True)
        args = ["--openrouter"]
        if free_only:
            args.append("--free-only")
        show_models(args)
        return
    if choice == "gemini":
        show_models(["--gemini"])


def main() -> None:
    if not shutil.which("make"):
        print("make non trovato nel PATH.")
        raise SystemExit(1)

    print("PTOF Make Wizard")
    try:
        while True:
            options = [
                ("Download PTOF", "download"),
                ("Workflow", "workflow"),
                ("Review", "review"),
                ("Outreach PTOF", "outreach"),
                ("Registro analisi", "registry"),
                ("Lista modelli AI", "models"),
            ]
            choice = prompt_choice("Seleziona area", options, allow_back=False)
            if choice == "download":
                menu_download()
            elif choice == "workflow":
                menu_workflow()
            elif choice == "review":
                menu_review()
            elif choice == "outreach":
                menu_outreach()
            elif choice == "registry":
                menu_registry()
            elif choice == "models":
                menu_models()
    except KeyboardInterrupt:
        print("\nUscita.")


if __name__ == "__main__":
    main()
