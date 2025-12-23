# Cloud LLM Review - Revisione con API Cloud

import os
import json
import requests
from typing import Optional, Dict, List
from duckduckgo_search import DDGS

# Import chunker for long documents
try:
    from src.processing.text_chunker import smart_split, get_chunk_info
except ImportError:
    from text_chunker import smart_split, get_chunk_info

from src.utils.school_database import SchoolDatabase

API_CONFIG_FILE = 'data/api_config.json'

# Chunking configuration
CHUNK_SIZE = 50000       # Max chars per chunk for analysis
# Chunking configuration
CHUNK_SIZE = 50000       # Max chars per chunk for analysis
METADATA_CHUNK_SIZE = 12000  # Reduced to ~3k tokens to fit comfortably in 8k context with prompt
LONG_DOC_THRESHOLD = 80000   # Docs longer than this use chunking

def _normalize_model_name(model: str) -> str:
    if not model:
        return ""
    name = str(model).strip().lower()
    if "/" in name:
        name = name.split("/")[-1]
    if ":" in name:
        name = name.split(":")[0]
    return name

def _uses_max_completion_tokens(model: str) -> bool:
    name = _normalize_model_name(model)
    return name.startswith("gpt-5") or name.startswith("o1") or name.startswith("o3")

def _supports_temperature(model: str) -> bool:
    name = _normalize_model_name(model)
    if not name:
        return True
    return not (name.startswith("gpt-5") or name.startswith("o1") or name.startswith("o3"))

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

def call_gemini_api(api_key: str, model: str, prompt: str, max_retries: int = 3) -> Optional[str]:
    """Call Gemini API with retry on rate limit"""
    import time
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 8192}
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=payload, timeout=120)
            if response.status_code == 200:
                data = response.json()
                return data['candidates'][0]['content']['parts'][0]['text']
            elif response.status_code == 429:
                wait_time = (attempt + 1) * 10
                print(f"⚠️ Gemini rate limit (429), waiting {wait_time}s... (attempt {attempt+1}/{max_retries})")
                time.sleep(wait_time)
            else:
                print(f"Gemini API error: {response.status_code} - {response.text[:200]}")
                break
        except Exception as e:
            print(f"Gemini API exception: {e}")
            break
    return None

def call_openai_api(api_key: str, model: str, prompt: str, max_retries: int = 3) -> Optional[str]:
    """Call OpenAI API with retry on rate limit"""
    import time
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }
    if _supports_temperature(model):
        payload["temperature"] = 0.3
    if _uses_max_completion_tokens(model):
        payload["max_completion_tokens"] = 8192
    else:
        payload["max_tokens"] = 8192
    
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=120)
            if response.status_code == 200:
                data = response.json()
                return data['choices'][0]['message']['content']
            elif response.status_code == 429:
                wait_time = (attempt + 1) * 10
                print(f"⚠️ OpenAI rate limit (429), waiting {wait_time}s... (attempt {attempt+1}/{max_retries})")
                time.sleep(wait_time)
            else:
                print(f"OpenAI API error: {response.status_code} - {response.text[:200]}")
                break
        except Exception as e:
            print(f"OpenAI API exception: {e}")
            break
    return None

def call_openrouter_api(api_key: str, model: str, prompt: str, max_retries: int = 3) -> Optional[str]:
    """Call OpenRouter API with retry on rate limit"""
    import time
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
    }
    if _supports_temperature(model):
        payload["temperature"] = 0.3
    if _uses_max_completion_tokens(model):
        payload["max_completion_tokens"] = 8192
    else:
        payload["max_tokens"] = 8192
    
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=120)
            if response.status_code == 200:
                data = response.json()
                return data['choices'][0]['message']['content']
            elif response.status_code == 429:
                wait_time = (attempt + 1) * 10  # 10, 20, 30 seconds
                print(f"⚠️ Rate limit (429), waiting {wait_time}s... (attempt {attempt+1}/{max_retries})")
                time.sleep(wait_time)
            else:
                print(f"OpenRouter API error: {response.status_code} - {response.text[:200]}")
                break
        except Exception as e:
            print(f"OpenRouter API exception: {e}")
            break
    return None

def call_ollama_api(model: str, prompt: str) -> Optional[str]:
    """Call Local Ollama API"""
    url = "http://localhost:11434/api/chat"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {
            "temperature": 0.3,
            "num_ctx": 8192
        }
    }
    try:
        response = requests.post(url, json=payload, timeout=300)
        if response.status_code == 200:
            data = response.json()
            return data['message']['content']
        else:
            print(f"Ollama API error: {response.status_code} - {response.text[:500]}")
    except Exception as e:
        print(f"Ollama API exception: {e}")
    return None

# Fallback model configuration
OLLAMA_FALLBACK_MODELS = ["gemma3:27b", "llama3.1:8b", "mistral:latest"]

def call_cloud_llm(provider: str, api_key: str, model: str, prompt: str, use_fallback: bool = True) -> Optional[str]:
    """Universal cloud LLM caller with automatic Ollama fallback on failure"""
    result = None
    
    # Try primary provider
    if provider == 'gemini':
        result = call_gemini_api(api_key, model, prompt)
    elif provider == 'openai':
        result = call_openai_api(api_key, model, prompt)
    elif provider == 'openrouter':
        result = call_openrouter_api(api_key, model, prompt)
    elif provider == 'ollama':
        result = call_ollama_api(model, prompt)
    
    # If failed and fallback enabled, try Ollama local models
    if result is None and use_fallback and provider != 'ollama':
        print(f"⚠️ {provider} failed, trying Ollama fallback...")
        for fallback_model in OLLAMA_FALLBACK_MODELS:
            print(f"   🔄 Trying {fallback_model}...")
            result = call_ollama_api(fallback_model, prompt)
            if result:
                print(f"   ✅ Fallback to {fallback_model} succeeded!")
                break
        if not result:
            print(f"   ❌ All Ollama fallback models failed")
    
    return result

def parse_json_safe(response: str) -> Optional[Dict]:
    """Safely parse JSON from LLM response."""
    if not response:
        return None
    try:
        import re
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        return json.loads(response)
    except:
        return None





def merge_partial_analyses(partials: List[Dict]) -> Dict:
    """
    Merge multiple partial JSON analyses into one.
    For scores: take maximum found. For lists: combine unique items.
    """
    if not partials:
        return {}
    if len(partials) == 1:
        return partials[0]
    
    merged = {'metadata': {}, 'ptof_section2': {}}
    
    for p in partials:
        if not p:
            continue
            
        # Merge metadata
        meta = p.get('metadata', {})
        for k, v in meta.items():
            if v and v not in ['ND', '', None]:
                if not merged['metadata'].get(k) or merged['metadata'][k] in ['ND', '', None]:
                    merged['metadata'][k] = v
        
        # Merge section scores - take max
        sec2 = p.get('ptof_section2', {})
        for section_key, section_val in sec2.items():
            if section_key not in merged['ptof_section2']:
                merged['ptof_section2'][section_key] = section_val
            elif isinstance(section_val, dict):
                existing = merged['ptof_section2'][section_key]
                if isinstance(existing, dict):
                    # Merge sub-items
                    for sub_k, sub_v in section_val.items():
                        if isinstance(sub_v, dict) and 'score' in sub_v:
                            existing_score = existing.get(sub_k, {}).get('score', 0)
                            new_score = sub_v.get('score', 0)
                            if new_score > existing_score:
                                existing[sub_k] = sub_v
                        elif sub_k == 'score':
                            if sub_v > existing.get('score', 0):
                                existing['score'] = sub_v
        
        # Merge lists (partner_nominati, activities)
        for list_key in ['partner_nominati', 'activities_register']:
            if list_key in p:
                if list_key not in merged:
                    merged[list_key] = []
                merged[list_key].extend(p.get(list_key, []))
    
    # Deduplicate lists
    for list_key in ['partner_nominati', 'activities_register']:
        if list_key in merged and isinstance(merged[list_key], list):
            seen = set()
            unique = []
            for item in merged[list_key]:
                item_str = str(item)
                if item_str not in seen:
                    seen.add(item_str)
                    unique.append(item)
            merged[list_key] = unique
    
    return merged


def review_ptof_chunked(md_content: str, provider: str, api_key: str, model: str) -> Optional[Dict]:
    """
    Analyze long PTOF documents using Map-Reduce strategy.
    1. Split document into chunks
    2. Analyze each chunk separately (MAP)
    3. Merge partial results (REDUCE)
    """
    # Load analyst prompt
    try:
        with open('config/prompts.md', 'r') as f:
            prompts_content = f.read()
        import re
        analyst_match = re.search(r'## Analyst\n(.*?)(?=\n## |\Z)', prompts_content, re.DOTALL)
        analyst_prompt = analyst_match.group(1).strip() if analyst_match else "Analizza questo PTOF."
    except:
        analyst_prompt = "Analizza questo documento PTOF e restituisci un JSON strutturato."
    
    # Split document
    chunks = smart_split(md_content, CHUNK_SIZE)
    info = get_chunk_info(chunks)
    
    print(f"[cloud_review] CHUNKED ANALYSIS: {info['count']} chunks, {info['total_chars']} total chars")
    
    # MAP: Analyze each chunk
    partial_results = []
    
    for i, chunk in enumerate(chunks):
        print(f"[cloud_review] Analyzing chunk {i+1}/{len(chunks)} ({len(chunk)} chars)...")
        
        chunk_prompt = f"""{analyst_prompt}

---

NOTA: Questa è la SEZIONE {i+1} di {len(chunks)} del documento PTOF.
Analizza SOLO questa sezione e restituisci i punteggi trovati.

SEZIONE {i+1}:

{chunk}"""
        
        response = call_cloud_llm(provider, api_key, model, chunk_prompt)
        partial_json = parse_json_safe(response)
        
        if partial_json:
            partial_results.append(partial_json)
            print(f"[cloud_review] Chunk {i+1}: Got valid JSON")
        else:
            print(f"[cloud_review] Chunk {i+1}: Parse failed")
    
    if not partial_results:
        return None
    
    # REDUCE: Merge results
    print(f"[cloud_review] Merging {len(partial_results)} partial results...")
    merged = merge_partial_analyses(partial_results)
    
    # Extract metadata iteratively if needed
    if not merged.get('metadata') or merged['metadata'].get('denominazione') in ['ND', '', None]:
        print("[cloud_review] Extracting metadata iteratively...")
        meta = extract_metadata_iterative(md_content, provider, api_key, model)
        if meta:
            if 'metadata' not in merged:
                merged['metadata'] = {}
            merged['metadata'].update(meta)
    
    return merged


def review_ptof_with_cloud(md_content: str, provider: str, api_key: str, model: str, school_id: str = None) -> Optional[Dict]:
    """
    Review a PTOF document using cloud LLM.
    Automatically uses chunked analysis for long documents.
    Returns structured JSON analysis or error dict on failure.
    
    Args:
        md_content: Markdown text of PTOF
        provider: 'gemini', 'openai', etc.
        api_key: API Key
        model: Model name
        school_id: Optional school code (e.g. MIIS08900V) to aid metadata search
    """
    content_size = len(md_content)
    
    # Use chunked analysis for long documents
    if content_size > LONG_DOC_THRESHOLD:
        print(f"[cloud_review] Long document ({content_size} chars) - using chunked analysis")
        
        result_json = review_ptof_chunked(md_content, provider, api_key, model)
        if result_json:
             # Enhancement: if metadata missing, try using school_id
             if not result_json.get('metadata') or \
                result_json['metadata'].get('denominazione') in ['ND', '', None] or \
                result_json['metadata'].get('comune') in ['ND', '', None]:
                 
                 print("[cloud_review] Metadata incomplete after chunked analysis. Trying robust extraction...")
                 meta = extract_metadata_from_header(md_content, provider, api_key, model, school_id=school_id)
                 if meta:
                    if 'metadata' not in result_json: result_json['metadata'] = {}
                    result_json['metadata'].update(meta)
        return result_json
    
    # Original logic for shorter documents
    try:
        with open('config/prompts.md', 'r') as f:
            prompts_content = f.read()
        import re
        analyst_match = re.search(r'## Analyst\n(.*?)(?=\n## |\Z)', prompts_content, re.DOTALL)
        if analyst_match:
            analyst_prompt = analyst_match.group(1).strip()
        else:
            analyst_prompt = "Analizza questo documento PTOF e restituisci un JSON strutturato con i punteggi."
    except Exception as e:
        return {"error": f"Errore caricamento prompt: {e}"}
    
    full_prompt = f"{analyst_prompt}\n\n---\n\nTESTO PTOF DA ANALIZZARE ({content_size} caratteri):\n\n{md_content}"
    
    print(f"[cloud_review] Calling {provider}/{model} with {len(full_prompt)} chars prompt")
    
    response = call_cloud_llm(provider, api_key, model, full_prompt)
    
    if response:
        print(f"[cloud_review] Got response: {len(response)} chars")
        result_json = parse_json_safe(response)
        
        if not result_json:
            return {"raw_response": response[:5000], "parse_error": "JSON parse failed"}
            
        # Extract Metadata
        if result_json:
            print("[cloud_review] Extracting/Verifying metadata via Cloud...")
            # We use the new robust function here
            meta = extract_metadata_from_header(md_content, provider, api_key, model, school_id=school_id)
            if meta:
                if 'metadata' not in result_json:
                    result_json['metadata'] = {}
                # Update but respect existing non-ND values? 
                # Actually extract_metadata_from_header is now smarter, so we trust it more if it used web search.
                # Let's merge carefully.
                for k, v in meta.items():
                    if v and v not in ['ND', '', None]:
                         result_json['metadata'][k] = v
                
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

def extract_metadata_from_header(md_content: str, provider: str, api_key: str, model: str, use_iterative: bool = False, school_id: str = None) -> Optional[Dict]:
    """
    Extract school metadata (Name, City, Type, etc.) from PTOF header using Cloud LLM.
    Returns JSON dictionary.
    
    Args:
        md_content: Document text
        provider: API Provider
        api_key: API Key
        model: Model Name
        use_iterative: If True, scans deeper if not found in header
        school_id: Optional School Code from filename (e.g. MIIS00000X) as candidate
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
        
    # Truncate content - Increased to 30000 chars (approx 10-15 pages) to catch deep metadata (User requirement: look after first few pages)
    # The user noted mechanism code might be after 2-3 pages. 30k chars is plenty.
    truncated = md_content[:30000]
    
    # 1. First Attempt - Direct Extraction
    # Enhance prompt to specifically look for ID
    full_prompt = f"{extractor_prompt}\n\bIMPORTANTE: Cerca il CODICE MECCANOGRAFICO (es. MIIS...) nel testo. Spesso si trova dopo le prime pagine.\n\n---\n\nINIZIO DOCUMENTO:\n\n{truncated}"
    
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
            
    # LOGIC: Resolve School ID priority
    # 1. ID found in text -> Best
    # 2. ID passed in valid arg -> Fallback
    detected_id = None
    if meta_json:
        raw_id = meta_json.get('school_id')
        if raw_id and raw_id not in ['ND', '', 'None', 'null'] and len(raw_id) >= 8:
            detected_id = raw_id.upper()
            
    final_id = detected_id if detected_id else school_id
    
    # Update meta_json with the winning ID
    if meta_json:
        meta_json['school_id'] = final_id
    else:
        meta_json = {'school_id': final_id} if final_id else {}

    # 3. Last Resort: Iterative Deep Scan (if requested or still missing critical info)
    if use_iterative and (not meta_json or any(meta_json.get(f) in ['ND', '', None] for f in ['denominazione', 'comune'])):
        print(f"[cloud_review] Metadata still missing. Starting Iterative Deep Scan...")
        deep_meta = extract_metadata_iterative(md_content, provider, api_key, model)
        if deep_meta:
            if not meta_json: meta_json = {}
            for k, v in deep_meta.items():
                if v and v not in ['ND', '', None]:
                    if not meta_json.get(k) or meta_json[k] in ['ND', '', None]:
                        meta_json[k] = v
            if deep_meta.get('school_id') and deep_meta['school_id'] not in ['ND', '']:
                 meta_json['school_id'] = deep_meta['school_id']
                 final_id = deep_meta['school_id']

    # New Step: Check Local Database
    # This avoids web search if we have the data locally
    db_found = False
    if final_id:
        print(f"[cloud_review] Checking Local DB for ID: {final_id}...")
        db_data = SchoolDatabase().get_school_data(final_id)
        if db_data:
            print(f"[cloud_review] ✅ Found authoritative data in Local DB for {final_id}")
            db_found = True
            # Merge DB data (DB is authoritative)
            # We overwrite conflicting LLM hallucinations with official data
            for k, v in db_data.items():
                if v and v != 'ND':
                    meta_json[k] = v
    
    # 4. Final Fallback: Web Search
    # Only search if NOT found in DB and missing critical info
    final_meta = meta_json if meta_json else {}
    
    missing_critical = False
    for field in ['denominazione', 'comune']:
        val = final_meta.get(field)
        if not val or val in ["ND", "null", None, "", "N/A"]:
            missing_critical = True
            
    # If found in DB, we trust it and likely don't need search unless DB had missing fields (unlikely for CSVs)
    should_search = (not db_found) and (missing_critical or (final_id and (not final_meta.get('denominazione') or final_meta.get('denominazione') == 'ND')))
    
    if should_search:
        # Construct Query using the BEST ID we have
        search_parts = []
        
        # Priority 1: Final ID (Text > Filename)
        if final_id:
             search_parts.append(f"Scuola {final_id}")
        
        # Priority 2: Name + City if no ID
        elif final_meta.get('denominazione') and final_meta.get('denominazione') != 'ND':
            search_parts.append(final_meta['denominazione'])
            if final_meta.get('comune') and final_meta.get('comune') != 'ND':
                search_parts.append(final_meta['comune'])
            search_parts.append("scuola")
            
        else:
             pass
        
        if search_parts:
            search_query = " ".join(search_parts)
            print(f"[cloud_review] Final Attempt: Web Search for '{search_query}'")
            web_results = search_school_on_web(search_query)
            
            if web_results:
                # Load prompt
                try:
                    with open('config/prompts.md', 'r') as f:
                        prompts_content = f.read()
                    import re
                    match = re.search(r'## Metadata Extractor\n(.*?)(?=\n## |\Z)', prompts_content, re.DOTALL)
                    extractor_prompt = match.group(1).strip() if match else "Extract school metadata to JSON."
                except:
                    extractor_prompt = "Extract school metadata to JSON."
    
                refine_prompt = f"""
    {extractor_prompt}
    
    IMPORTANTE: Completa i dati mancanti usando i risultati web. 
    CONFRONTA il codice scuola nel testo ({detected_id if detected_id else 'Non trovato'}) con i risultati web.
    Se i risultati web mostrano un codice e un nome scuola chiari (es. {final_id}), usa quelli.
    
    RISULTATI WEB:
    {web_results}
    
    ---\n\nDATI ATTUALI PARZIALI: {json.dumps(final_meta)}
    """
                response_v3 = call_cloud_llm(provider, api_key, model, refine_prompt)
                if response_v3:
                     # Extract JSON V3
                    json_match_v3 = re.search(r'```json\s*(.*?)\s*```', response_v3, re.DOTALL)
                    if json_match_v3:
                        try: return json.loads(json_match_v3.group(1))
                        except: pass
                    try: return json.loads(response_v3)
                    except: pass
    
    return meta_json
    
    return meta_json

def _extract_metadata_llm_only(chunk_content: str, provider: str, api_key: str, model: str) -> Optional[Dict]:
    """Helper: Pure LLM extraction without Web Search fallback."""
    # Load prompt
    try:
        with open('config/prompts.md', 'r') as f:
            prompts_content = f.read()
        import re
        match = re.search(r'## Metadata Extractor\n(.*?)(?=\n## |\Z)', prompts_content, re.DOTALL)
        extractor_prompt = match.group(1).strip() if match else "Extract school metadata to JSON."
    except:
        extractor_prompt = "Extract school metadata to JSON."
    
    # Prompt adapted for chunks
    full_prompt = f"{extractor_prompt}\n\n---\n\nTESTO DOCUMENTO (ESTRATTO):\n\n{chunk_content}"
    
    response = call_cloud_llm(provider, api_key, model, full_prompt)
    if response:
        # Extract JSON
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            try: return json.loads(json_match.group(1))
            except: pass
        try: return json.loads(response)
        except: pass
    return None

def extract_metadata_iterative(md_content: str, provider: str, api_key: str, model: str) -> Dict:
    """
    Iteratively extract metadata from chunks until all required fields are found.
    Stops early if all fields are populated.
    """
    required_fields = ['denominazione', 'comune', 'area_geografica', 'ordine_grado', 'tipo_scuola', 'school_id']
    found_meta = {}
    
    # Split into chunks for metadata extraction
    from src.processing.text_chunker import split_by_size
    chunks = split_by_size(md_content, METADATA_CHUNK_SIZE, overlap=5000)
    
    print(f"[cloud_review] Metadata extraction: {len(chunks)} chunks")
    
    for i, chunk in enumerate(chunks):
        # Check if all fields found
        missing = [f for f in required_fields if not found_meta.get(f) or found_meta[f] in ['ND', '', None]]
        if not missing:
            print(f"[cloud_review] All metadata found after {i} chunks")
            break
        
        
        print(f"[cloud_review] Extracting metadata from chunk {i+1}/{len(chunks)}")
        
        # USE PURE LLM EXTRACTION HERE
        chunk_meta = _extract_metadata_llm_only(chunk, provider, api_key, model)
        
        if chunk_meta:
            print(f"[cloud_review] Chunk {i+1} success: {chunk_meta.get('denominazione', 'Partial')}")
            # Merge: keep existing values, add new non-empty ones
            for k, v in chunk_meta.items():
                if v and v not in ['ND', '', None]:
                    if not found_meta.get(k) or found_meta[k] in ['ND', '', None]:
                        found_meta[k] = v
        else:
            print(f"[cloud_review] Chunk {i+1} failed to extract JSON")
    
    return found_meta
