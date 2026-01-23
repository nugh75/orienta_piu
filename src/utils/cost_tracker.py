#!/usr/bin/env python3
"""
Cost Tracker - Tracciamento centralizzato dei costi LLM.

Permette a diversi moduli (workflow, activity_extractor, etc.) di registrare
i costi delle chiamate LLM e di visualizzare un riepilogo aggregato.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Dict, Optional

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
COST_FILE = DATA_DIR / "cost_tracker.json"

_file_lock = Lock()


def _load_data() -> Dict:
    """Carica i dati dal file JSON."""
    if not COST_FILE.exists():
        return {
            "session_id": None,
            "started_at": None,
            "phases": {},
            "total_cost": 0.0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
        }
    try:
        with COST_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {
            "session_id": None,
            "started_at": None,
            "phases": {},
            "total_cost": 0.0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
        }


def _save_data(data: Dict) -> None:
    """Salva i dati nel file JSON."""
    COST_FILE.parent.mkdir(parents=True, exist_ok=True)
    with COST_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def start_session(session_id: Optional[str] = None) -> str:
    """
    Inizia una nuova sessione di tracciamento costi.
    Resetta tutti i contatori precedenti.

    Args:
        session_id: ID opzionale della sessione (es. "cycle_5")

    Returns:
        L'ID della sessione creata
    """
    with _file_lock:
        if session_id is None:
            session_id = datetime.now().strftime("session_%Y%m%d_%H%M%S")

        data = {
            "session_id": session_id,
            "started_at": datetime.now().isoformat(),
            "phases": {},
            "total_cost": 0.0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
        }
        _save_data(data)
        logger.info(f"Cost tracker: nuova sessione '{session_id}'")
        return session_id


def record_cost(
    phase: str,
    cost: float,
    input_tokens: int = 0,
    output_tokens: int = 0,
    provider: str = "",
    model: str = "",
) -> None:
    """
    Registra un costo per una fase specifica.

    Args:
        phase: Nome della fase (es. "workflow", "activity")
        cost: Costo in dollari
        input_tokens: Numero di token in input
        output_tokens: Numero di token in output
        provider: Provider usato (es. "ollama", "openrouter")
        model: Modello usato (es. "gemma3:27b")
    """
    with _file_lock:
        data = _load_data()

        if phase not in data["phases"]:
            data["phases"][phase] = {
                "cost": 0.0,
                "input_tokens": 0,
                "output_tokens": 0,
                "calls": 0,
                "provider": provider,
                "model": model,
                "last_updated": None,
            }

        phase_data = data["phases"][phase]
        phase_data["cost"] += cost
        phase_data["input_tokens"] += input_tokens
        phase_data["output_tokens"] += output_tokens
        phase_data["calls"] += 1
        phase_data["last_updated"] = datetime.now().isoformat()
        if provider:
            phase_data["provider"] = provider
        if model:
            phase_data["model"] = model

        data["total_cost"] += cost
        data["total_input_tokens"] += input_tokens
        data["total_output_tokens"] += output_tokens

        _save_data(data)


def get_summary() -> Dict:
    """
    Ottiene il riepilogo dei costi della sessione corrente.

    Returns:
        Dizionario con i dati aggregati
    """
    with _file_lock:
        return _load_data()


def format_summary(data: Optional[Dict] = None) -> str:
    """
    Formatta il riepilogo dei costi per la visualizzazione.

    Args:
        data: Dati opzionali (se None, carica dal file)

    Returns:
        Stringa formattata con il riepilogo
    """
    if data is None:
        data = get_summary()

    lines = [
        "",
        "=" * 60,
        "RIEPILOGO COSTI",
        "=" * 60,
    ]

    if data.get("session_id"):
        lines.append(f"  Sessione: {data['session_id']}")
    if data.get("started_at"):
        lines.append(f"  Iniziata: {data['started_at'][:19]}")
    lines.append("")

    phases = data.get("phases", {})
    if phases:
        for phase_name, phase_data in phases.items():
            cost = phase_data.get("cost", 0)
            input_t = phase_data.get("input_tokens", 0)
            output_t = phase_data.get("output_tokens", 0)
            calls = phase_data.get("calls", 0)
            provider = phase_data.get("provider", "")
            model = phase_data.get("model", "")

            provider_info = f" [{provider}::{model}]" if provider and model else ""
            lines.append(
                f"  {phase_name.capitalize():15} ${cost:8.4f}  "
                f"({input_t:,} in / {output_t:,} out, {calls} calls){provider_info}"
            )

        lines.append("  " + "-" * 56)

    total_cost = data.get("total_cost", 0)
    total_in = data.get("total_input_tokens", 0)
    total_out = data.get("total_output_tokens", 0)

    lines.append(
        f"  {'TOTALE':15} ${total_cost:8.4f}  "
        f"({total_in:,} in / {total_out:,} out)"
    )
    lines.append("=" * 60)
    lines.append("")

    return "\n".join(lines)


def print_summary() -> None:
    """Stampa il riepilogo dei costi su stdout."""
    print(format_summary())


def log_summary(log: Optional[logging.Logger] = None) -> None:
    """
    Logga il riepilogo dei costi.

    Args:
        log: Logger opzionale (se None, usa il logger del modulo)
    """
    if log is None:
        log = logger

    for line in format_summary().split("\n"):
        if line.strip():
            log.info(line)


def clear_session() -> None:
    """Cancella la sessione corrente."""
    with _file_lock:
        if COST_FILE.exists():
            COST_FILE.unlink()
        logger.info("Cost tracker: sessione cancellata")


if __name__ == "__main__":
    # Test
    start_session("test_session")
    record_cost("workflow", 0.0234, 45123, 12456, "ollama", "gemma3:27b")
    record_cost("workflow", 0.0156, 32456, 8234, "ollama", "gemma3:27b")
    record_cost("activity", 0.0312, 65000, 15000, "openrouter", "gemini-2.0-flash")
    print_summary()
