#!/usr/bin/env python3
"""
Agentic Pipeline for PTOF Analysis
Architecture:
1. Analyst (Gemma-3 27B): Extraction & Drafting
2. Reviewer (Qwen-3 32B): Red Teaming & Critique
3. Refiner (GPT-OSS 20B): Polishing & Fixes
"""
import os
import json
import logging
import requests
import time
from glob import glob

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Configuration
OLLAMA_URL = "http://192.168.129.14:11434/api/generate"
MD_DIR = "ptof_md"
RESULTS_DIR = "analysis_results"

# Models
MODEL_ANALYST = "gemma3:27b"
MODEL_REVIEWER = "qwen3:32b"
MODEL_REFINER = "gemma3:27b"

try:
    from src.utils.config_loader import load_prompts
except ImportError:
    # Fallback for running as script from app/ dir (though recommended run is from root)
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from src.utils.config_loader import load_prompts

# Load global prompts
PROMPTS = load_prompts()

# Load Metadata Caches for JSON Enrichment
import pandas as pd
import re

def extract_canonical_code(filename_code):
    """Extract standard school code from prefixed filename."""
    match = re.search(r'([A-Z]{2,4}[A-Z0-9]{5,8}[A-Z0-9])', filename_code.upper())
    return match.group(1) if match else filename_code

def load_metadata_caches():
    """Load metadata from CSV sources."""
    caches = {'enrichment': {}, 'invalsi': {}}
    
    # Enrichment (official registry)
    if os.path.exists('data/metadata_enrichment.csv'):
        try:
            df = pd.read_csv('data/metadata_enrichment.csv', dtype=str)
            for _, row in df.iterrows():
                code = str(row.get('school_id', '')).strip()
                if code:
                    caches['enrichment'][code] = row.to_dict()
        except Exception as e:
            logging.warning(f"Failed to load enrichment: {e}")
    
    # INVALSI
    if os.path.exists('data/invalsi_unified.csv'):
        try:
            df = pd.read_csv('data/invalsi_unified.csv', sep=';', dtype=str)
            for _, row in df.iterrows():
                code = str(row.get('istituto', '')).strip()
                if code:
                    caches['invalsi'][code] = row.to_dict()
        except Exception as e:
            logging.warning(f"Failed to load INVALSI: {e}")
    
    return caches

METADATA_CACHES = load_metadata_caches()

def enrich_json_metadata(json_path, school_code_raw):
    """Enrich JSON file with metadata from CSV sources."""
    school_code = extract_canonical_code(school_code_raw)
    
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        if 'metadata' not in data:
            data['metadata'] = {}
        
        enrich = METADATA_CACHES['enrichment'].get(school_code, {})
        invalsi = METADATA_CACHES['invalsi'].get(school_code, {})
        
        # Update metadata with priority: existing > enrichment > invalsi
        data['metadata']['school_id'] = school_code
        data['metadata']['denominazione'] = enrich.get('denominazione') or invalsi.get('denominazionescuola') or data['metadata'].get('denominazione', 'ND')
        data['metadata']['comune'] = enrich.get('comune') or invalsi.get('nome_comune') or data['metadata'].get('comune', 'ND')
        data['metadata']['area_geografica'] = enrich.get('area_geografica') or data['metadata'].get('area_geografica', 'ND')
        data['metadata']['ordine_grado'] = enrich.get('ordine_grado') or invalsi.get('grado') or data['metadata'].get('ordine_grado', 'ND')
        data['metadata']['territorio'] = invalsi.get('territorio_std') or data['metadata'].get('territorio', 'ND')
        data['metadata']['tipo_scuola'] = invalsi.get('tipo_scuola_std') or data['metadata'].get('tipo_scuola', 'ND')
        
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logging.info(f"Enriched metadata for {school_code}")
        return True
    except Exception as e:
        logging.error(f"Failed to enrich {json_path}: {e}")
        return False

class BaseAgent:
    def __init__(self, model_name, role):
        self.model = model_name
        self.role = role

    def call_ollama(self, prompt, context=""):
        full_prompt = f"System: Sei un {self.role}.\nContext: {context}\nUser: {prompt}"
        try:
            response = requests.post(OLLAMA_URL, json={
                "model": self.model,
                "prompt": full_prompt,
                "stream": False,
                "options": {"temperature": 0.2, "num_ctx": 32768}
            }, timeout=300)
            if response.status_code == 200:
                return response.json().get("response", "")
            else:
                logging.error(f"Error calling {self.model}: {response.status_code}")
                return ""
        except Exception as e:
            logging.error(f"Exception calling {self.model}: {e}")
            return ""

class AnalystAgent(BaseAgent):
    def __init__(self):
        super().__init__(MODEL_ANALYST, "Analista Esperto di PTOF e Documenti Scolastici")

    def draft_report(self, ptof_text):
        logging.info(f"[{self.model}] Drafting report...")
        prompt_template = PROMPTS.get("Analyst", "")
        if not prompt_template:
            logging.error("Analyst prompt missing")
            return ""
            
        # No variables for Analyst currently
        return self.call_ollama(prompt_template, context=ptof_text)

class ReviewerAgent(BaseAgent):
    def __init__(self):
        super().__init__(MODEL_REVIEWER, "Revisore Critico e Logico (Red Teaming)")

    def critique_report(self, source_text, draft_report):
        logging.info(f"[{self.model}] Critiquing report...")
        prompt_template = PROMPTS.get("Reviewer", "")
        
        prompt = prompt_template.replace("{{DRAFT_REPORT}}", draft_report)
        return self.call_ollama(prompt, context=source_text)

class RefinerAgent(BaseAgent):
    def __init__(self):
        super().__init__(MODEL_REFINER, "Editor Finale e Correttore")

    def refine_report(self, draft_report, critique):
        logging.info(f"[{self.model}] Refining report...")
        prompt_template = PROMPTS.get("Refiner", "")
        
        prompt = prompt_template.replace("{{DRAFT_REPORT}}", draft_report).replace("{{CRITIQUE}}", critique)
        return self.call_ollama(prompt)

def run_pipeline():
    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR)
        
    md_files = glob(os.path.join(MD_DIR, "*.md"))
    logging.info(f"Found {len(md_files)} markdown files to process.")
    
    analyst = AnalystAgent()
    reviewer = ReviewerAgent()
    refiner = RefinerAgent()
    
    def sanitize_json(text):
        """Extract valid JSON object from LLM response."""
        text = text.strip()
        
        # Remove markdown code fences
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        # Find the JSON object boundaries
        start = text.find('{')
        if start == -1:
            return text
        
        # Find matching closing brace
        depth = 0
        end = start
        for i, char in enumerate(text[start:], start):
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    end = i
                    break
        
        return text[start:end+1]
    
    for md_file in md_files:
        school_Code = os.path.basename(md_file).replace('.md', '')
        
        final_md_path = os.path.join(RESULTS_DIR, f"{school_Code}_analysis.md")
        final_json_path = os.path.join(RESULTS_DIR, f"{school_Code}_analysis.json")
        
        if os.path.exists(final_md_path):
            logging.info(f"Skipping {school_Code} (Already completed)")
            continue
            
        logging.info(f"___ Processing {school_Code} ___")
        
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 1. Draft
        draft = analyst.draft_report(content)
        if not draft: continue
        
        # Save Draft JSON
        # Note: We save it even if imperfect to have the data.
        draft = sanitize_json(draft)
        with open(final_json_path, 'w') as f:
            f.write(draft) 
        
        # Enrich JSON with metadata from CSV sources
        enrich_json_metadata(final_json_path, school_Code)
            
        # Extract Narrative for review
        try:
            draft_json = json.loads(draft)
            narrative = draft_json.get('narrative', '')
        except:
            narrative = draft # Fallback
            
        # 2. Critique
        critique = reviewer.critique_report(content, narrative)
        logging.info(f"Reviewer says: {critique[:100]}...")
        
        # 3. Refine (Conditional)
        # 3. Refine (Conditional)
        if "APPROVATO" not in critique.upper() and len(critique) > 10:
             # Refiner returns a JSON string (as per prompt)
             refined_json_str = refiner.refine_report(draft, critique) # Pass full draft, not just narrative
             refined_json_str = sanitize_json(refined_json_str)
             
             try:
                 refined_data = json.loads(refined_json_str)
                 # Update JSON file with refined data
                 with open(final_json_path, 'w') as f:
                     f.write(refined_json_str)
                 
                 # Extract narrative for MD file
                 final_output = refined_data.get('narrative', '')
                 logging.info("Report and Scores refined by GPT-OSS.")
             except Exception as e:
                 logging.error(f"Failed to parse Refiner JSON: {e}")
                 final_output = narrative # Fallback
        else:
             final_output = narrative
             logging.info("Report approved directly.")

        # Save Final MD
        with open(final_md_path, 'w') as f:
            f.write(final_output)
        
        # Incrementally update CSV for dashboard
        try:
            import subprocess
            # Run refine_metadata to extract ND values from MD files
            subprocess.run(['python', 'src/processing/refine_metadata.py'], 
                           capture_output=True, timeout=60)
            # Run align_metadata to sync JSON and rebuild CSV
            subprocess.run(['python', 'src/processing/align_metadata.py'], 
                           capture_output=True, timeout=120)
            logging.info(f"CSV updated for {school_Code}")
        except Exception as e:
            logging.warning(f"CSV rebuild failed: {e}")

if __name__ == "__main__":
    run_pipeline()
