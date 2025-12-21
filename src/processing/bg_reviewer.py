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

# Constants
OLLAMA_URL = "http://192.168.129.14:11434/api/generate"
MODEL_REVIEWER = "qwen3:32b"
FLAGS_FILE = "data/review_flags.json"
ANALYSIS_DIR = "analysis_results"
PROMPTS_FILE = "config/prompts.md"

class BackgroundReviewer:
    def __init__(self, model_name=MODEL_REVIEWER):
        self.model = model_name
        self.prompts = self._load_prompts()
        self.ensure_flags_file()

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

    def ensure_flags_file(self):
        """Ensure the flags persistence file exists."""
        if not os.path.exists(os.path.dirname(FLAGS_FILE)):
            os.makedirs(os.path.dirname(FLAGS_FILE))
        if not os.path.exists(FLAGS_FILE):
            with open(FLAGS_FILE, 'w') as f:
                json.dump([], f)

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

    def call_ollama(self, prompt, system_prompt=""):
        """Call Ollama API."""
        full_prompt = f"{prompt}"
        if system_prompt:
             full_prompt = f"System: {system_prompt}\nUser: {prompt}"
             
        try:
            response = requests.post(OLLAMA_URL, json={
                "model": self.model,
                "prompt": full_prompt,
                "stream": False,
                "options": {"temperature": 0.1, "num_ctx": 8192}
            }, timeout=120)
            
            if response.status_code == 200:
                return response.json().get("response", "")
            else:
                logger.error(f"Ollama error: {response.status_code}")
                return ""
        except Exception as e:
            logger.error(f"Ollama exception: {e}")
            return ""

    def sanitize_json(self, text):
        """Extract valid JSON from LLM response."""
        text = text.strip()
        if text.startswith("```json"): text = text[7:]
        if text.startswith("```"): text = text[3:]
        if text.endswith("```"): text = text[:-3]
        text = text.strip()
        
        start = text.find('[')
        end = text.rfind(']')
        if start != -1 and end != -1:
            return text[start:end+1]
        return text

    def run_heuristic_checks(self, data):
        """Run rule-based checks without LLM."""
        flags = []
        
        # 1. Metadata Checks
        meta = data.get('metadata', {})
        critical_fields = ['comune', 'tipo_scuola', 'area_geografica', 'ordine_grado']
        for field in critical_fields:
            val = meta.get(field, '')
            if not val or val in ['ND', 'N/A', 'null', None]:
                flags.append({
                    "type": "metadata_incomplete",
                    "severity": "high",
                    "field": field,
                    "message": f"Campo '{field}' mancante o non valido ('{val}')"
                })

        # 2. Score Consistency Checks
        section2 = data.get('ptof_section2', {})
        
        # Check partnership score vs count
        partnerships = section2.get('2_2_partnership', {})
        p_count = partnerships.get('partnership_count', 0)
        p_score = partnerships.get('score', 0)
        
        if p_score >= 5 and p_count < 3:
             flags.append({
                    "type": "score_anomaly",
                    "severity": "medium",
                    "field": "2_2_partnership",
                    "message": f"Punteggio alto ({p_score}) ma poche partnership riportate ({p_count})"
                })
        
        if p_score <= 2 and p_count > 5:
             flags.append({
                    "type": "score_anomaly",
                    "severity": "medium",
                    "field": "2_2_partnership",
                    "message": f"Punteggio basso ({p_score}) nonostante molte partnership ({p_count})"
                })

        return flags

    def review_single(self, json_path, status_callback=None):
        """Review a single analysis file."""
        filename = os.path.basename(json_path)
        if status_callback:
            status_callback(f"Analisi file: {filename}...")
        else:
            logger.info(f"Reviewing {json_path}...")

        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
        except Exception as e:
            msg = f"Failed to load {json_path}: {e}"
            logger.error(msg)
            if status_callback: status_callback(msg)
            return None

        school_id = data.get('metadata', {}).get('school_id', 'UNKNOWN')
        
        # 1. Heuristic Checks
        heuristic_flags = self.run_heuristic_checks(data)
        
        # 2. LLM Review
        llm_flags = []
        prompt_template = self.prompts.get("Background Reviewer")
        
        if prompt_template:
            # Simplify JSON for LLM to save tokens
            analysis_str = json.dumps(data, ensure_ascii=False)
            if len(analysis_str) > 20000:
                # Truncate narrative if too long
                data['narrative'] = data.get('narrative', '')[:5000] + "...[TRUNCATED]"
                analysis_str = json.dumps(data, ensure_ascii=False)

            prompt = prompt_template.replace("{{ANALYSIS_JSON}}", analysis_str)
            response = self.call_ollama(prompt)
            
            try:
                json_part = self.sanitize_json(response)
                parsed_llm_flags = json.loads(json_part)
                if isinstance(parsed_llm_flags, list):
                    llm_flags = parsed_llm_flags
            except Exception as e:
                logger.warning(f"Failed to parse LLM response for {filename}: {e}")
        
        all_flags = heuristic_flags + llm_flags
        
        if all_flags:
            return {
                "file": filename,
                "school_id": school_id,
                "review_date": datetime.now().isoformat(),
                "flags": all_flags,
                "requires_human_review": any(f.get('severity') == 'high' for f in all_flags)
            }
        return None

    def run_batch_review(self, status_callback=None, stop_check_callback=None):
        """
        Run review on all analysis files.
        status_callback(msg): function to report status
        stop_check_callback(): function that returns True if we should stop
        """
        json_files = glob(os.path.join(ANALYSIS_DIR, "*_analysis.json"))
        total_files = len(json_files)
        
        if status_callback:
            status_callback(f"Trovati {total_files} file da analizzare.")
        logger.info(f"Found {total_files} files to review.")
        
        current_flags = self.load_flags()
        # Index existing flags by file to avoid duplicates/overwrite
        flags_map = {item['file']: item for item in current_flags}
        
        new_flags_count = 0
        
        for i, json_file in enumerate(json_files):
            # Check for stop signal
            if stop_check_callback and stop_check_callback():
                if status_callback:
                    status_callback(f"⚠️ Processo interrotto dall'utente al file {i}/{total_files}.")
                logger.info("Batch review stopped by user.")
                break

            fname = os.path.basename(json_file)
            
            # Skip if already reviewed recently? (Optional, unimplemented generally)
            
            result = self.review_single(json_file, status_callback)
            
            if result:
                flags_map[fname] = result
                new_flags_count += 1
                msg = f"🚩 Segnalata anomalia in {fname} ({len(result['flags'])} issues)."
                if status_callback: status_callback(msg)
                logger.info(msg)
            else:
                # If clean, remove previous flags if any
                if fname in flags_map:
                    del flags_map[fname]
                    msg = f"✅ Risolti problemi per {fname}"
                    if status_callback: status_callback(msg)
                    logger.info(msg)
            
            # Periodic save (every 5 files) to avoid data loss on stop
            if i % 5 == 0:
                self.save_flags(list(flags_map.values()))

        # Save results at end
        final_list = list(flags_map.values())
        self.save_flags(final_list)
        
        if status_callback:
            status_callback(f"✅ Revisione batch completata. Totale file con anomalie: {len(final_list)}")
        logger.info(f"Batch review complete. Total flagged files: {len(final_list)}")
        return len(final_list)


if __name__ == "__main__":
    reviewer = BackgroundReviewer()
    # Mock status callback for testing
    def print_status(msg): print(msg)
    reviewer.run_batch_review(status_callback=print_status)

