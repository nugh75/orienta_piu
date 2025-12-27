#!/usr/bin/env python3
"""
Wizard interattivo per configurare la pipeline di analisi PTOF.
Permette di scegliere modelli e parametri di chunking.
"""
import os
import sys
import json
import requests
from pathlib import Path

# Configurazione
CONFIG_FILE = Path(__file__).parent.parent.parent / "config" / "pipeline_config.json"
DEFAULT_OLLAMA_URL = "http://192.168.129.14:11434"


def load_config():
    """Carica la configurazione corrente."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_config(config):
    """Salva la configurazione."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Configurazione salvata in {CONFIG_FILE}")


def get_ollama_models(ollama_url=None):
    """Ottiene la lista dei modelli Ollama disponibili."""
    if ollama_url is None:
        ollama_url = DEFAULT_OLLAMA_URL

    # Rimuovi /api/generate se presente
    base_url = ollama_url.replace("/api/generate", "").rstrip("/")

    try:
        response = requests.get(f"{base_url}/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = []
            for model in data.get("models", []):
                name = model.get("name", "")
                size_gb = model.get("size", 0) / (1024**3)
                models.append({
                    "name": name,
                    "size_gb": size_gb,
                    "modified": model.get("modified_at", "")
                })
            return sorted(models, key=lambda x: x["name"])
        return []
    except Exception as e:
        print(f"⚠️ Impossibile connettersi a Ollama ({base_url}): {e}")
        return []


def print_header(title):
    """Stampa un header formattato."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_menu(options, current=None):
    """Stampa un menu numerato."""
    for i, opt in enumerate(options, 1):
        marker = " ← attuale" if opt == current else ""
        print(f"  {i}. {opt}{marker}")


def get_choice(prompt, max_val, default=None):
    """Ottiene una scelta numerica dall'utente."""
    while True:
        try:
            hint = f" [{default}]" if default else ""
            choice = input(f"{prompt}{hint}: ").strip()
            if not choice and default:
                return default
            choice = int(choice)
            if 1 <= choice <= max_val:
                return choice
            print(f"  ⚠️ Inserisci un numero tra 1 e {max_val}")
        except ValueError:
            print(f"  ⚠️ Inserisci un numero valido")
        except KeyboardInterrupt:
            print("\n\n❌ Configurazione annullata")
            sys.exit(1)


def wizard_preset(config):
    """Wizard per scegliere il preset."""
    print_header("🎛️  SELEZIONE PRESET")

    presets = config.get("presets", {})
    current_preset = str(config.get("active_preset", 0))

    print("\nPreset disponibili:\n")
    preset_list = []
    for key in sorted(presets.keys(), key=int):
        preset = presets[key]
        name = preset.get("name", f"Preset {key}")
        desc = preset.get("description", "")[:50]
        marker = " ← ATTIVO" if key == current_preset else ""
        print(f"  {int(key)+1}. {name}{marker}")
        if desc:
            print(f"      {desc}")
        preset_list.append(key)

    print(f"\n  0. Mantieni attuale ({presets.get(current_preset, {}).get('name', 'Default')})")

    choice = input("\nScegli preset [0]: ").strip()
    if choice == "" or choice == "0":
        return config

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(preset_list):
            config["active_preset"] = int(preset_list[idx])
            print(f"\n✅ Preset cambiato a: {presets[preset_list[idx]]['name']}")
    except ValueError:
        print("  ⚠️ Scelta non valida, mantengo preset attuale")

    return config


def wizard_models(config):
    """Wizard per configurare i modelli del preset attivo."""
    print_header("🤖  CONFIGURAZIONE MODELLI")

    # Ottieni modelli Ollama disponibili
    preset_key = str(config.get("active_preset", 0))
    preset = config.get("presets", {}).get(preset_key, {})
    ollama_url = preset.get("ollama_url", DEFAULT_OLLAMA_URL)

    print(f"\n📡 Connessione a Ollama ({ollama_url})...")
    ollama_models = get_ollama_models(ollama_url)

    if not ollama_models:
        print("⚠️ Nessun modello Ollama trovato. Usa 'make models-ollama' per verificare.")
        return config

    print(f"\n✅ Trovati {len(ollama_models)} modelli:\n")
    for i, m in enumerate(ollama_models, 1):
        size_str = f"{m['size_gb']:.1f}GB" if m['size_gb'] > 0 else ""
        print(f"  {i}. {m['name']} {size_str}")

    # Modelli attuali
    models = preset.get("models", {})
    print(f"\n📋 Configurazione attuale:")
    print(f"   Analyst:     {models.get('analyst', 'N/D')}")
    print(f"   Reviewer:    {models.get('reviewer', 'N/D')}")
    print(f"   Refiner:     {models.get('refiner', 'N/D')}")
    print(f"   Synthesizer: {models.get('synthesizer', 'N/D')}")

    change = input("\n🔄 Vuoi cambiare i modelli? [s/N]: ").strip().lower()
    if change != 's':
        return config

    model_names = [m["name"] for m in ollama_models]

    for role in ["analyst", "reviewer", "refiner", "synthesizer"]:
        current = models.get(role, "")
        print(f"\n{role.upper()} (attuale: {current}):")
        print("  0. Mantieni attuale")
        for i, name in enumerate(model_names, 1):
            print(f"  {i}. {name}")

        choice = input(f"Scegli [0]: ").strip()
        if choice and choice != "0":
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(model_names):
                    models[role] = model_names[idx]
                    print(f"  ✅ {role} → {model_names[idx]}")
            except ValueError:
                pass

    preset["models"] = models
    config["presets"][preset_key] = preset
    return config


def wizard_chunking(config):
    """Wizard per configurare i parametri di chunking."""
    print_header("📄  CONFIGURAZIONE CHUNKING")

    chunking = config.get("chunking", {})
    current_size = chunking.get("chunk_size", 30000)
    current_threshold = chunking.get("long_doc_threshold", 50000)

    print(f"\n📋 Configurazione attuale:")
    print(f"   Dimensione chunk:  {current_size:,} caratteri")
    print(f"   Soglia chunking:   {current_threshold:,} caratteri")

    print("\n📊 Preimpostazioni consigliate:")
    print("  1. Conservativo (modelli piccoli): chunk=20000, soglia=40000")
    print("  2. Bilanciato (gemma3:27b):        chunk=30000, soglia=50000 ← attuale")
    print("  3. Aggressivo (modelli grandi):    chunk=40000, soglia=60000")
    print("  4. Personalizzato")
    print("  0. Mantieni attuale")

    choice = input("\nScegli [0]: ").strip()

    if choice == "1":
        chunking["chunk_size"] = 20000
        chunking["long_doc_threshold"] = 40000
    elif choice == "2":
        chunking["chunk_size"] = 30000
        chunking["long_doc_threshold"] = 50000
    elif choice == "3":
        chunking["chunk_size"] = 40000
        chunking["long_doc_threshold"] = 60000
    elif choice == "4":
        try:
            size = input(f"  Dimensione chunk [{current_size}]: ").strip()
            if size:
                chunking["chunk_size"] = int(size)
            threshold = input(f"  Soglia chunking [{current_threshold}]: ").strip()
            if threshold:
                chunking["long_doc_threshold"] = int(threshold)
        except ValueError:
            print("  ⚠️ Valori non validi, mantengo attuali")

    if choice in ["1", "2", "3", "4"]:
        print(f"\n✅ Chunking: chunk={chunking['chunk_size']}, soglia={chunking['long_doc_threshold']}")

    config["chunking"] = chunking
    return config


def run_wizard():
    """Esegue il wizard completo."""
    print("\n" + "=" * 60)
    print("  🧙 WIZARD CONFIGURAZIONE PIPELINE PTOF")
    print("=" * 60)
    print("\nQuesto wizard ti guiderà nella configurazione della pipeline.")
    print("Premi Invio per mantenere i valori attuali.\n")

    config = load_config()

    # Step 1: Preset
    config = wizard_preset(config)

    # Step 2: Modelli (solo se preset Ollama)
    preset_key = str(config.get("active_preset", 0))
    preset = config.get("presets", {}).get(preset_key, {})
    if preset.get("type") == "ollama":
        config = wizard_models(config)

    # Step 3: Chunking
    config = wizard_chunking(config)

    # Salva
    print_header("💾  SALVATAGGIO")
    save = input("Salvare la configurazione? [S/n]: ").strip().lower()
    if save != 'n':
        save_config(config)
    else:
        print("\n❌ Configurazione non salvata")

    print("\n✨ Wizard completato!\n")


def show_current_config():
    """Mostra la configurazione corrente in formato compatto."""
    config = load_config()
    preset_key = str(config.get("active_preset", 0))
    preset = config.get("presets", {}).get(preset_key, {})
    chunking = config.get("chunking", {})

    print("\n📋 Configurazione attuale:")
    print(f"   Preset: {preset.get('name', 'N/D')} (#{preset_key})")
    print(f"   Tipo:   {preset.get('type', 'N/D')}")

    models = preset.get("models", {})
    if isinstance(models.get("analyst"), dict):
        print(f"   Analyst:     {models.get('analyst', {}).get('model', 'N/D')}")
    else:
        print(f"   Analyst:     {models.get('analyst', 'N/D')}")

    print(f"   Chunking:   size={chunking.get('chunk_size', 'N/D')}, threshold={chunking.get('long_doc_threshold', 'N/D')}")
    print()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--show":
        show_current_config()
    else:
        run_wizard()
