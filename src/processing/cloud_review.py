# Cloud LLM Review - Revisione con API Cloud

import os
import json
import requests
from typing import Optional, Dict, List
from duckduckgo_search import DDGS
from duckduckgo_search import DDGS

API_CONFIG_FILE = 'data/api_config.json'

def load_api_config() -> Dict:
    """Load API configuration from JSON file"""
    if os.path.exists(API_CONFIG_FILE):
        try:
            with open(API_CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {
        "gemini_api_key": "",
        "openai_api_key": "",
        "openrouter_api_key": "",
        "default_provider": "gemini",
        "default_model": ""
    }

def save_api_config(config: Dict) -> bool:
    """Save API configuration to JSON file"""
    try:
        os.makedirs(os.path.dirname(API_CONFIG_FILE), exist_ok=True)
        with open(API_CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False

def fetch_gemini_models(api_key: str) -> List[str]:
    """Fetch available Gemini models"""
    if not api_key:
        return []
    try:
        url = f"https://generativelanguage.googleapis.com/v1/models?key={api_key}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            models = [m['name'].replace('models/', '') for m in data.get('models', []) 
                     if 'generateContent' in m.get('supportedGenerationMethods', [])]
            return sorted(models)
    except Exception as e:
        print(f"Error fetching Gemini models: {e}")
    return []

def fetch_openai_models(api_key: str) -> List[str]:
    """Fetch available OpenAI models"""
    if not api_key:
        return []
    try:
        url = "https://api.openai.com/v1/models"
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            models = [m['id'] for m in data.get('data', []) 
                     if 'gpt' in m['id'].lower()]
            return sorted(models)
    except Exception as e:
        print(f"Error fetching OpenAI models: {e}")
    return []

def fetch_openrouter_models_free(api_key: str = "") -> List[str]:
    """Fetch FREE OpenRouter models only"""
    try:
        url = "https://openrouter.ai/api/v1/models"
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            free_models = []
            for m in data.get('data', []):
                pricing = m.get('pricing', {})
                # Free models have 0 cost
                if pricing.get('prompt') == '0' or pricing.get('prompt') == 0:
                    free_models.append(m['id'])
            return sorted(free_models)
    except Exception as e:
        print(f"Error fetching OpenRouter models: {e}")
    return []

def call_gemini_api(api_key: str, model: str, prompt: str) -> Optional[str]:
    """Call Gemini API"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 8192}
    }
    try:
        response = requests.post(url, json=payload, timeout=120)
        if response.status_code == 200:
            data = response.json()
            return data['candidates'][0]['content']['parts'][0]['text']
        else:
            print(f"Gemini API error: {response.status_code} - {response.text[:200]}")
    except Exception as e:
        print(f"Gemini API exception: {e}")
    return None

def call_openai_api(api_key: str, model: str, prompt: str) -> Optional[str]:
    """Call OpenAI API"""
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 8192
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        if response.status_code == 200:
            data = response.json()
            return data['choices'][0]['message']['content']
        else:
            print(f"OpenAI API error: {response.status_code} - {response.text[:200]}")
    except Exception as e:
        print(f"OpenAI API exception: {e}")
    return None

def call_openrouter_api(api_key: str, model: str, prompt: str) -> Optional[str]:
    """Call OpenRouter API"""
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/LIste-PTOF",
        "X-Title": "PTOF Analysis"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 8192
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        if response.status_code == 200:
            data = response.json()
            return data['choices'][0]['message']['content']
        else:
            print(f"OpenRouter API error: {response.status_code} - {response.text[:200]}")
    except Exception as e:
        print(f"OpenRouter API exception: {e}")
    return None

def call_cloud_llm(provider: str, api_key: str, model: str, prompt: str) -> Optional[str]:
    """Universal cloud LLM caller"""
    if provider == 'gemini':
        return call_gemini_api(api_key, model, prompt)
    elif provider == 'openai':
        return call_openai_api(api_key, model, prompt)
    elif provider == 'openrouter':
        return call_openrouter_api(api_key, model, prompt)
    return None

def review_ptof_with_cloud(md_content: str, provider: str, api_key: str, model: str) -> Optional[Dict]:
    """
    Review a PTOF document using cloud LLM.
    Returns structured JSON analysis or error dict on failure.
    """
    # Load prompt from config file
    try:
        with open('config/prompts.md', 'r') as f:
            prompts_content = f.read()
        # Extract Analyst section
        import re
        analyst_match = re.search(r'## Analyst\n(.*?)(?=\n## |\Z)', prompts_content, re.DOTALL)
        if analyst_match:
            analyst_prompt = analyst_match.group(1).strip()
        else:
            analyst_prompt = "Analizza questo documento PTOF e restituisci un JSON strutturato con i punteggi."
    except Exception as e:
        return {"error": f"Errore caricamento prompt: {e}"}
    
    # Limit content size
    content_size = len(md_content)
    truncated_content = md_content[:80000]  # Increased limit
    
    full_prompt = f"{analyst_prompt}\n\n---\n\nTESTO PTOF DA ANALIZZARE ({content_size} caratteri):\n\n{truncated_content}"
    
    print(f"[cloud_review] Calling {provider}/{model} with {len(full_prompt)} chars prompt")
    
    # 1. Main Analysis
    response = call_cloud_llm(provider, api_key, model, full_prompt)
    
    if response:
        print(f"[cloud_review] Got response: {len(response)} chars")
        result_json = None
        
        # Try to extract JSON from response
        try:
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                result_json = json.loads(json_match.group(1))
            else:
                result_json = json.loads(response)
        except Exception as e:
            # Return raw response with parse error info
            return {"raw_response": response[:5000], "parse_error": str(e)}
            
        # 2. Extract Metadata (Separate Call)
        if result_json:
            print("[cloud_review] Extracting metadata via Cloud...")
            meta = extract_metadata_from_header(md_content, provider, api_key, model)
            if meta:
                if 'metadata' not in result_json: result_json['metadata'] = {}
                result_json['metadata'].update(meta)
                
        return result_json
            
    return None


if __name__ == "__main__":
    # Test fetching models
    config = load_api_config()
    
    print("Testing model fetch...")
    
    if config.get('gemini_api_key'):
        models = fetch_gemini_models(config['gemini_api_key'])
        print(f"Gemini models: {models[:5]}...")
    
    free_models = fetch_openrouter_models_free()
    print(f"Free OpenRouter models: {len(free_models)} found")
    if free_models:
        print(f"Examples: {free_models[:5]}")

def validate_ptof_header(md_content: str, provider: str, api_key: str, model: str) -> Optional[Dict]:
    """
    Validate if the document is likely a PTOF based on header/first pages using Cloud LLM.
    Returns JSON with {is_ptof, confidence, reasoning, document_type} or None on error.
    """
    # Load prompt from Validator section
    try:
        with open('config/prompts.md', 'r') as f:
            prompts_content = f.read()
            
        import re
        match = re.search(r'## Validator\n(.*?)(?=\n## |\Z)', prompts_content, re.DOTALL)
        if match:
            validator_prompt = match.group(1).strip()
        else:
            validator_prompt = "Is this a PTOF? Return JSON."
    except Exception as e:
        print(f"Error loading validator prompt: {e}")
        validator_prompt = "Is this a PTOF? Return JSON."
        
    # Truncate content - focus on first 4000 chars (approx 2 pages)
    truncated = md_content[:4000]
    
    full_prompt = f"{validator_prompt}\n\n---\n\nINIZIO DOCUMENTO:\n\n{truncated}"
    
    # Reuse existing caller
    response = call_cloud_llm(provider, api_key, model, full_prompt)
    
    if response:
        # Extract JSON
        import re
        json_match = re.search(r'', response, re.DOTALL)
        if not json_match:
            # Try finding first { and last }
            json_match = re.search(r'(\{.*\})', response, re.DOTALL)
            
        json_str = json_match.group(1) if json_match else response
        # Cleanup comments if any
        json_str = re.sub(r'//.*', '', json_str)
        
        try:
            return json.loads(json_str)
        except:
            return {"is_ptof": False, "reasoning": "JSON parsing failed", "raw_response": response}
            
    return None

def search_school_on_web(query: str) -> str:
    """
    Search for school details on the web using DuckDuckGo.
    Returns a summary string of the top results.
    """
    try:
        results = DDGS().text(query, max_results=3)
        summary = ""
        for i, res in enumerate(results, 1):
            summary += f"Result {i}: {res['title']} - {res['body']}\n"
        return summary
    except Exception as e:
        print(f"Web search error: {e}")
        return ""

def extract_metadata_from_header(md_content: str, provider: str, api_key: str, model: str) -> Optional[Dict]:
    """
    Extract school metadata (Name, City, Type, etc.) from PTOF header using Cloud LLM.
    Returns JSON dictionary.
    """
    # Load prompt from Metadata Extractor section
    try:
        with open('config/prompts.md', 'r') as f:
            prompts_content = f.read()
            
        import re
        match = re.search(r'## Metadata Extractor\n(.*?)(?=\n## |\Z)', prompts_content, re.DOTALL)
        if match:
            extractor_prompt = match.group(1).strip()
        else:
            extractor_prompt = "Extract school metadata to JSON."
    except Exception as e:
        print(f"Error loading extractor prompt: {e}")
        extractor_prompt = "Extract school metadata to JSON."
        
    # Truncate content - Increased to 30000 chars (approx 10-15 pages) to catch deep metadata
    truncated = md_content[:30000]
    
    # 1. First Attempt - Direct Extraction
    full_prompt = f"{extractor_prompt}\n\n---\n\nINIZIO DOCUMENTO:\n\n{truncated}"
    
    print(f"[cloud_review] Identifying school metadata via Cloud (Context: {len(truncated)} chars)...")
    response = call_cloud_llm(provider, api_key, model, full_prompt)
    
    meta_json = None
    if response:
        # Extract JSON
        import re
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            try:
                meta_json = json.loads(json_match.group(1))
            except: pass
        if not meta_json:
            try:
                meta_json = json.loads(response)
            except: pass
            
    # 2. Validation & Fallback Web Search
    needs_enrichment = False
    search_query = ""
    
    if not meta_json:
        needs_enrichment = True
        # Try to guess name from filename if possible, or just search generic
        search_query = "Scuola italiana PTOF"
    else:
        # Check for missing critical fields
        missing_fields = []
        for field in ['area_geografica', 'denominazione', 'comune', 'school_id']:
            val = meta_json.get(field)
            if not val or val in ["ND", "null", None, ""]:
                missing_fields.append(field)
        
        if missing_fields:
            needs_enrichment = True
            # Construct intelligent query
            name = meta_json.get('denominazione', '')
            city = meta_json.get('comune', '')
            code = meta_json.get('school_id', '')
            
            search_parts = [p for p in [name, city, code, "scuola", "indirizzo", "codice meccanografico"] if p and p not in ["ND", "null"]]
            search_query = " ".join(search_parts)
            
    if needs_enrichment and search_query:
        print(f"[cloud_review] Metadata incomplete. Fallback Web Search for: '{search_query}'")
        web_results = search_school_on_web(search_query)
        
        if web_results:
            print(f"[cloud_review] Found web info. Refining metadata...")
            # Second Pass with Web Context
            refine_prompt = f"""
{extractor_prompt}

IMPORTANTE: Il documento originale era incompleto.
Usa ANCHE queste informazioni trovate sul web per completare i campi mancanti (specie school_id, comune, denominazione):

RISULTATI WEB:
{web_results}

---\n\nINIZIO DOCUMENTO ORIGINALE:\n\n{truncated}
"""
            response_v2 = call_cloud_llm(provider, api_key, model, refine_prompt)
            if response_v2:
                 # Extract JSON V2
                json_match_v2 = re.search(r'```json\s*(.*?)\s*```', response_v2, re.DOTALL)
                if json_match_v2:
                    try:
                        return json.loads(json_match_v2.group(1))
                    except: pass
                try:
                    return json.loads(response_v2)
                except: pass
    
    return meta_json

