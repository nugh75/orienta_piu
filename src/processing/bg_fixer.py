import os
import json
import logging
import requests
import time
from datetime import datetime
from glob import glob

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants (Shared configuration)
OLLAMA_URL = "http://192.168.129.14:11434/api/generate"
MODEL_REVIEWER = "gemma3:27b"
FLAGS_FILE = "data/review_flags.json"
ANALYSIS_DIR = "analysis_results"
PROMPTS_FILE = "config/prompts.md"

class BackgroundFixer:
    def __init__(self, model_name=MODEL_REVIEWER):
        self.model = model_name
        self.prompts = self._load_prompts()
        self.flags = self.load_flags()

    def _load_prompts(self):
        """Load prompts from config file."""
        prompts = {}
        current_section = None
        try:
            with open(PROMPTS_FILE, 'r') as f:
                for line in f:
                    if line.strip().startswith("## "):
                        current_section = line.strip()[3:].strip()
                        prompts[current_section] = ""
                    elif current_section:
                        prompts[current_section] += line
        except Exception as e:
            logger.error(f"Failed to load prompts: {e}")
        return prompts

    def load_flags(self):
        """Load existing flags."""
        try:
            with open(FLAGS_FILE, 'r') as f:
                return json.load(f)
        except:
            return []

    def save_flags(self, flags):
        """Save flags to file."""
        with open(FLAGS_FILE, 'w') as f:
            json.dump(flags, f, indent=2)

    def call_ollama(self, prompt, system_prompt="", stop_check_callback=None):
        """Call Ollama API with streaming to allow interruption."""
        full_prompt = f"{prompt}"
        if system_prompt:
             full_prompt = f"System: {system_prompt}\nUser: {prompt}"
             
        try:
            # Use stream=True to allow interruption
            response = requests.post(OLLAMA_URL, json={
                "model": self.model,
                "prompt": full_prompt,
                "stream": True,
                "options": {"temperature": 0.1, "num_ctx": 16384}
            }, stream=True, timeout=180)
            
            if response.status_code != 200:
                logger.error(f"Ollama error: {response.status_code}")
                return ""
                
            full_response = []
            for line in response.iter_lines():
                # Check for stop signal during generation
                if stop_check_callback and stop_check_callback():
                    logger.info("Ollama generation interrupted by user.")
                    return None # Signal interruption

                if line:
                    decoded = json.loads(line.decode('utf-8'))
                    if 'response' in decoded:
                        full_response.append(decoded['response'])
                    if decoded.get('done', False):
                        break
            
            return "".join(full_response)
            
        except Exception as e:
            logger.error(f"Ollama exception: {e}")
            return ""

    def sanitize_json(self, text):
        """Extract valid JSON from LLM response."""
        if not text: return "" # Handle None/Empty from interruption
        text = text.strip()
        if text.startswith("```json"): text = text[7:]
        if text.startswith("```"): text = text[3:]
        if text.endswith("```"): text = text[:-3]
        text = text.strip()
        
        start = text.find('{') # Fixer returns an object, not a list
        end = text.rfind('}')
        if start != -1 and end != -1:
            return text[start:end+1]
        return text

    def fix_single(self, flag_entry, status_callback=None, stop_check_callback=None):
        """Apply fixes for a single file."""
        filename = flag_entry['file']
        flags = flag_entry.get('flags', [])
        
        if not flags:
            return True # Nothing to fix
            
        json_path = os.path.join(ANALYSIS_DIR, filename)
        if not os.path.exists(json_path):
            msg = f"File non trovato: {filename}"
            logger.error(msg)
            if status_callback: status_callback(f"❌ {msg}")
            return False

        if status_callback:
            status_callback(f"🛠️ Correzione file: {filename} ({len(flags)} issues)...")

        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"Error loading {filename}: {e}")
            return False

        # Prepare prompt
        prompt_template = self.prompts.get("Background Fixer")
        if not prompt_template:
            logger.error("Prompt 'Background Fixer' not found")
            return False

        prompt = prompt_template.replace("{{FLAGS_JSON}}", json.dumps(flags, ensure_ascii=False, indent=2))
        prompt = prompt.replace("{{ANALYSIS_JSON}}", json.dumps(data, ensure_ascii=False))

        # Pass stop callback to allow interruption inside the net call
        response = self.call_ollama(prompt, stop_check_callback=stop_check_callback)
        
        # Check if interrupted (None response)
        if response is None:
             if status_callback: status_callback(f"⚠️ Operazione interrotta su {filename}")
             return False

        if not response:
            msg = f"Nessuna risposta dal modello (Timeout o Errore) per {filename}"
            logger.error(msg)
            if status_callback: status_callback(f"⚠️ {msg}")
            return False

        # Parse result
        try:
            fixed_json_str = self.sanitize_json(response)
            if not fixed_json_str:
                raise ValueError("Il modello non ha restituito un JSON valido.")
                
            fixed_data = json.loads(fixed_json_str)
            
            # Sanity check: ensure valid JSON object
            if not isinstance(fixed_data, dict):
                raise ValueError("LLM did not return a dictionary")
                
            # Save corrected file
            with open(json_path, 'w') as f:
                json.dump(fixed_data, f, ensure_ascii=False, indent=2)
                
            msg = f"✅ File corretto e salvato: {filename}"
            if status_callback: status_callback(msg)
            logger.info(msg)
            return True
            
        except Exception as e:
            msg = f"Failed to apply fix for {filename}: {e}"
            logger.error(msg)
            if status_callback: status_callback(f"❌ {msg}")
            return False

    def run_batch_fix(self, status_callback=None, stop_check_callback=None, target_files=None):
        """
        Run fix on all flagged files.
        :param target_files: Optional list of filenames to restrict correction to.
        """
        current_flags = self.load_flags()
        total_flags = len(current_flags)
        
        if status_callback:
            if target_files:
                status_callback(f"Tentativo correzione per {len(target_files)} file selezionati (su {total_flags} totali).")
            else:
                status_callback(f"Trovati {total_flags} file con anomalie da correggere.")
            
        remaining_flags = []
        fixed_count = 0
        
        for i, entry in enumerate(current_flags):
            filename = entry['file']
            
            # Skip if filtering and not in target
            if target_files is not None and filename not in target_files:
                remaining_flags.append(entry)
                continue

            # Check stop
            if stop_check_callback and stop_check_callback():
                if status_callback: status_callback("⚠️ Correzione interrotta dall'utente.")
                # Add current and all subsequent to remaining
                remaining_flags.append(entry)
                remaining_flags.extend(current_flags[i+1:]) 
                break
                
            # Pass stop callback down
            success = self.fix_single(entry, status_callback, stop_check_callback)
            
            if success:
                fixed_count += 1
            else:
                remaining_flags.append(entry) # Keep if failed
                
            # Update flags file incrementally (every item processed)
            # We rebuild the full list: processed_so_far(in remaining or fixed) + unprocessed
            # Note: current_flags[i+1:] are the unprocessed ones.
            # So current state of file should be: remaining_flags + current_flags[i+1:]
            self.save_flags(remaining_flags + current_flags[i+1:])

        # Final save
        self.save_flags(remaining_flags)
        
        if status_callback:
            status_callback(f"🏁 Correzione completata. File corretti: {fixed_count}, Rimasti: {len(remaining_flags)}")
        
        return fixed_count
