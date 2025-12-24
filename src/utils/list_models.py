#!/usr/bin/env python3
"""
List available AI models from presets or providers.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, List, Set

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_FILE = BASE_DIR / "config" / "pipeline_config.json"
API_CONFIG_FILE = BASE_DIR / "data" / "api_config.json"


def load_json(path: Path) -> Dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def get_api_key(env_name: str, config_key: str) -> str:
    value = os.getenv(env_name)
    if value:
        return value
    config = load_json(API_CONFIG_FILE)
    if isinstance(config, dict):
        return str(config.get(config_key, "") or "")
    return ""


def list_config_models() -> List[str]:
    data = load_json(CONFIG_FILE)
    models: Set[str] = set()
    presets = (data.get("presets") or {}).values()
    for preset in presets:
        model_map = preset.get("models") if isinstance(preset, dict) else None
        if not isinstance(model_map, dict):
            continue
        for value in model_map.values():
            if isinstance(value, str) and value:
                models.add(value)
            elif isinstance(value, dict):
                model = value.get("model")
                if model:
                    models.add(model)
    return sorted(models)


def fetch_openrouter_models(api_key: str, free_only: bool) -> List[str]:
    url = "https://openrouter.ai/api/v1/models"
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError):
        return []

    models: List[str] = []
    for item in data.get("data", []) or []:
        model_id = item.get("id")
        if not model_id:
            continue
        if free_only:
            pricing = item.get("pricing", {}) or {}
            prompt = pricing.get("prompt")
            if str(prompt) != "0" and prompt != 0:
                continue
        models.append(model_id)
    return sorted(set(models))


def fetch_gemini_models(api_key: str) -> List[str]:
    if not api_key:
        return []
    url = f"https://generativelanguage.googleapis.com/v1/models?key={api_key}"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError):
        return []

    models: List[str] = []
    for item in data.get("models", []) or []:
        methods = item.get("supportedGenerationMethods", []) or []
        if "generateContent" not in methods:
            continue
        name = item.get("name", "").replace("models/", "")
        if name:
            models.append(name)
    return sorted(set(models))


def print_list(items: List[str], prefix: str, empty_message: str) -> None:
    if not items:
        print(f"{prefix}{empty_message}")
        return
    for item in items:
        print(f"{prefix}{item}")


def main() -> None:
    parser = argparse.ArgumentParser(description="List available AI models.")
    parser.add_argument("--config", action="store_true", help="List models from config presets.")
    parser.add_argument("--openrouter", action="store_true", help="List OpenRouter models.")
    parser.add_argument("--gemini", action="store_true", help="List Gemini models.")
    parser.add_argument("--free-only", action="store_true", help="OpenRouter: list free models only.")
    parser.add_argument("--prefix", default="", help="Prefix for each output line.")
    args = parser.parse_args()

    if not (args.config or args.openrouter or args.gemini):
        args.config = True

    if args.config:
        print_list(list_config_models(), args.prefix, "(nessun modello trovato)")

    if args.openrouter:
        api_key = get_api_key("OPENROUTER_API_KEY", "openrouter_api_key")
        models = fetch_openrouter_models(api_key, args.free_only)
        print_list(models, args.prefix, "(nessun modello trovato)")

    if args.gemini:
        api_key = get_api_key("GEMINI_API_KEY", "gemini_api_key")
        if not api_key:
            print_list([], args.prefix, "(GEMINI_API_KEY non configurata)")
        else:
            models = fetch_gemini_models(api_key)
            print_list(models, args.prefix, "(nessun modello trovato)")


if __name__ == "__main__":
    main()

