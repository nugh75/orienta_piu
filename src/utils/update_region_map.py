#!/usr/bin/env python3
"""
Script per aggiungere automaticamente le regioni mancanti usando LLM.
Legge i comuni non mappati e chiede a Gemini di identificare la regione italiana.
"""

import json
import os
import sys
import requests
from typing import List, Dict, Optional

# Paths - Use absolute paths relative to project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_DIR = os.path.join(PROJECT_ROOT, 'config')
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
REGION_MAP_FILE = os.path.join(CONFIG_DIR, 'region_map.json')
API_CONFIG_FILE = os.path.join(DATA_DIR, 'api_config.json')


def load_api_config() -> Dict:
    """Load API configuration."""
    config = {}
    if os.path.exists(API_CONFIG_FILE):
        try:
            with open(API_CONFIG_FILE, 'r') as f:
                config = json.load(f)
        except Exception:
            pass
            
    # Override/Augment with env vars
    try:
        from dotenv import load_dotenv
        load_dotenv()
        if os.getenv("GEMINI_API_KEY"):
            config["gemini_api_key"] = os.getenv("GEMINI_API_KEY")
        if os.getenv("OPENROUTER_API_KEY"):
            config["openrouter_api_key"] = os.getenv("OPENROUTER_API_KEY")
    except ImportError:
        pass
        
    return config


def load_region_map() -> Dict:
    """Load the region mapping."""
    if os.path.exists(REGION_MAP_FILE):
        with open(REGION_MAP_FILE, 'r') as f:
            return json.load(f)
    return {"comuni": {}, "regioni_valide": []}


def save_region_map(region_map: Dict) -> None:
    """Save the region mapping."""
    with open(REGION_MAP_FILE, 'w', encoding='utf-8') as f:
        json.dump(region_map, f, ensure_ascii=False, indent=2)


def call_gemini_api(api_key: str, comuni: List[str]) -> Optional[Dict[str, str]]:
    """
    Call Gemini API to identify regions for Italian comuni.
    Returns a dict mapping comune -> regione.
    """
    if not comuni:
        return {}
    
    prompt = f"""Sei un esperto di geografia italiana. Per ciascuno dei seguenti comuni italiani, 
indica la regione di appartenenza. Rispondi SOLO con un JSON valido nel formato:
{{"NOME_COMUNE": "Nome Regione", ...}}

Le regioni valide sono: Piemonte, Valle d'Aosta, Lombardia, Trentino-Alto Adige, Veneto, 
Friuli Venezia Giulia, Liguria, Emilia-Romagna, Toscana, Umbria, Marche, Lazio, 
Abruzzo, Molise, Campania, Puglia, Basilicata, Calabria, Sicilia, Sardegna.

Comuni da identificare:
{json.dumps(comuni, ensure_ascii=False)}

Rispondi SOLO con il JSON, senza markdown o altro testo."""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    
    try:
        response = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.1}
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            text = result['candidates'][0]['content']['parts'][0]['text']
            
            # Clean up the response (remove markdown code blocks if present)
            text = text.strip()
            if text.startswith('```'):
                text = text.split('\n', 1)[1]  # Remove first line
            if text.endswith('```'):
                text = text.rsplit('\n', 1)[0]  # Remove last line
            text = text.strip()
            
            # Parse JSON
            return json.loads(text)
        else:
            print(f"❌ Errore API Gemini: {response.status_code} - {response.text[:200]}")
            return None
            
    except json.JSONDecodeError as e:
        print(f"❌ Errore parsing JSON dalla risposta LLM: {e}")
        print(f"   Risposta: {text[:200]}")
        return None
    except Exception as e:
        print(f"❌ Errore nella chiamata API: {e}")
        return None


def call_openrouter_api(api_key: str, comuni: List[str]) -> Optional[Dict[str, str]]:
    """
    Call OpenRouter API as fallback for region identification.
    """
    if not comuni:
        return {}
    
    prompt = f"""Sei un esperto di geografia italiana. Per ciascuno dei seguenti comuni italiani, 
indica la regione di appartenenza. Rispondi SOLO con un JSON valido nel formato:
{{"NOME_COMUNE": "Nome Regione", ...}}

Le regioni valide sono: Piemonte, Valle d'Aosta, Lombardia, Trentino-Alto Adige, Veneto, 
Friuli Venezia Giulia, Liguria, Emilia-Romagna, Toscana, Umbria, Marche, Lazio, 
Abruzzo, Molise, Campania, Puglia, Basilicata, Calabria, Sicilia, Sardegna.

Comuni da identificare:
{json.dumps(comuni, ensure_ascii=False)}

Rispondi SOLO con il JSON, senza markdown o altro testo."""

    url = "https://openrouter.ai/api/v1/chat/completions"
    
    try:
        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/LIste-PTOF"
            },
            json={
                "model": "google/gemini-3-flash-preview:free",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            text = result['choices'][0]['message']['content']
            
            # Clean up the response
            text = text.strip()
            if text.startswith('```'):
                text = text.split('\n', 1)[1]
            if text.endswith('```'):
                text = text.rsplit('\n', 1)[0]
            text = text.strip()
            
            return json.loads(text)
        else:
            print(f"❌ Errore API OpenRouter: {response.status_code} - {response.text[:200]}")
            return None
            
    except json.JSONDecodeError as e:
        print(f"❌ Errore parsing JSON dalla risposta OpenRouter: {e}")
        return None
    except Exception as e:
        print(f"❌ Errore nella chiamata OpenRouter: {e}")
        return None


# Ollama Configuration
OLLAMA_URL = "http://192.168.129.14:11434/api/generate"
OLLAMA_MODEL = "gpt-oss:20b"

def call_ollama_api(comuni: List[str]) -> Optional[Dict[str, str]]:
    """
    Call local Ollama instance as final fallback.
    """
    if not comuni:
        return {}
        
    prompt = f"""Sei un esperto di geografia italiana. Per ciascuno dei seguenti comuni italiani, 
indica la regione di appartenenza. Rispondi SOLO con un JSON valido nel formato:
{{"NOME_COMUNE": "Nome Regione", ...}}

Le regioni valide sono: Piemonte, Valle d'Aosta, Lombardia, Trentino-Alto Adige, Veneto, 
Friuli Venezia Giulia, Liguria, Emilia-Romagna, Toscana, Umbria, Marche, Lazio, 
Abruzzo, Molise, Campania, Puglia, Basilicata, Calabria, Sicilia, Sardegna.

Comuni da identificare:
{json.dumps(comuni, ensure_ascii=False)}

Rispondi SOLO con il JSON, senza markdown o altro testo."""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1, "num_ctx": 4096}
            },
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            text = result.get('response', '')
            
            # Clean up the response
            text = text.strip()
            if text.startswith('```'):
                # Handle cases like ```json ... ``` or just ``` ... ```
                lines = text.split('\n')
                if lines[0].strip().startswith('```'):
                    text = '\n'.join(lines[1:])
            if text.endswith('```'):
                text = text.rsplit('```', 1)[0]
            text = text.strip()
            
            # Try to extract JSON if there's surrounding text
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1:
                text = text[start:end+1]
            
            return json.loads(text)
        else:
            print(f"❌ Errore API Ollama: {response.status_code} - {response.text[:200]}")
            return None
            
    except json.JSONDecodeError as e:
        print(f"❌ Errore parsing JSON dalla risposta Ollama: {e}")
        print(f"   Risposta grezza: {text[:200]}...")
        return None
    except Exception as e:
        print(f"❌ Errore nella chiamata Ollama: {e}")
        return None


def update_region_map(unmapped_comuni: List[str]) -> Dict[str, str]:
    """
    Use LLM to identify regions for unmapped comuni and update the region map.
    Returns the mapping of newly added comuni.
    """
    if not unmapped_comuni:
        print("✅ Nessun comune da mappare.")
        return {}
    
    print(f"🔍 Trovati {len(unmapped_comuni)} comuni senza regione:")
    for c in unmapped_comuni[:10]:
        print(f"   - {c}")
    if len(unmapped_comuni) > 10:
        print(f"   ... e altri {len(unmapped_comuni) - 10}")
    
    # Load API config
    config = load_api_config()
    gemini_key = config.get('gemini_api_key')
    openrouter_key = config.get('openrouter_api_key')
    
    new_mappings = None
    
    # Try Gemini first
    if gemini_key:
        print("\n🤖 Tentativo con Gemini...")
        new_mappings = call_gemini_api(gemini_key, unmapped_comuni)
    
    # Fallback to OpenRouter if Gemini fails
    if not new_mappings and openrouter_key:
        print("\n🔄 Gemini non disponibile, provo con OpenRouter...")
        new_mappings = call_openrouter_api(openrouter_key, unmapped_comuni)
        
    # Fallback to Ollama if both fail
    if not new_mappings:
        print("\n🔄 Gemini e OpenRouter non disponibili, provo con Ollama (gpt-oss:20b)...")
        new_mappings = call_ollama_api(unmapped_comuni)
    
    if not new_mappings:
        if not gemini_key and not openrouter_key:
            print("❌ Nessuna API key configurata (Gemini o OpenRouter) in .env o data/api_config.json e Ollama non ha risposto")
        else:
            print("❌ Impossibile ottenere mappature da nessun LLM")
        return {}
    
    # Load and update region map
    region_map = load_region_map()
    valid_regions = set(region_map.get('regioni_valide', []))
    
    added = {}
    for comune, regione in new_mappings.items():
        comune_upper = comune.upper()
        if regione in valid_regions:
            region_map['comuni'][comune_upper] = regione
            added[comune_upper] = regione
            print(f"   ✅ {comune_upper} → {regione}")
        else:
            print(f"   ⚠️ {comune_upper} → '{regione}' (regione non valida, ignorato)")
    
    if added:
        save_region_map(region_map)
        print(f"\n✅ Aggiunti {len(added)} nuovi comuni al file region_map.json")
    
    return added


def get_unmapped_comuni_from_csv() -> List[str]:
    """
    Read the analysis summary CSV and find comuni not in the region map.
    """
    import pandas as pd
    
    csv_path = os.path.join(DATA_DIR, 'analysis_summary.csv')
    if not os.path.exists(csv_path):
        print(f"❌ File non trovato: {csv_path}")
        return []
    
    df = pd.read_csv(csv_path)
    if 'comune' not in df.columns:
        print("❌ Colonna 'comune' non trovata nel CSV")
        return []
    
    region_map = load_region_map()
    mapped_comuni = set(region_map.get('comuni', {}).keys())
    
    # Get unique comuni from CSV
    csv_comuni = df['comune'].dropna().unique()
    
    unmapped = []
    for comune in csv_comuni:
        comune_upper = str(comune).upper().strip()
        # Check if already mapped (exact or partial match)
        is_mapped = False
        for mapped in mapped_comuni:
            if mapped in comune_upper or comune_upper in mapped:
                is_mapped = True
                break
        if not is_mapped and comune_upper and comune_upper != 'ND':
            unmapped.append(comune_upper)
    
    return unmapped


def main():
    """Main entry point."""
    print("=" * 60)
    print("🗺️  Auto-Update Region Map")
    print("=" * 60)
    
    # Get unmapped comuni
    unmapped = get_unmapped_comuni_from_csv()
    
    if not unmapped:
        print("\n✅ Tutti i comuni sono già mappati!")
        return 0
    
    # Update using LLM
    added = update_region_map(unmapped)
    
    if added:
        print("\n" + "=" * 60)
        print("✅ Aggiornamento completato!")
        print(f"   Nuovi comuni aggiunti: {len(added)}")
        print("=" * 60)
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
