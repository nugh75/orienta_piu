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

# Chunking configuration
CHUNK_SIZE = 40000       # Max chars per chunk for Ollama (smaller context)
LONG_DOC_THRESHOLD = 60000  # Use chunking for docs longer than this

# Import chunker
try:
    from src.processing.text_chunker import smart_split, get_chunk_info
except ImportError:
    import sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from src.processing.text_chunker import smart_split, get_chunk_info

# Models
MODEL_ANALYST = "gemma3:27b"
MODEL_REVIEWER = "qwen3:32b"
MODEL_REFINER = "gemma3:27b"
MODEL_SYNTHESIZER = "gemma3:27b"

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
    caches = {'enrichment': {}}
    
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
    
    return caches

METADATA_CACHES = load_metadata_caches()

def enrich_json_metadata(json_path, school_code_raw):
    """Enrich JSON file with metadata from enrichment cache (LLM generated metadata is primary)."""
    school_code = extract_canonical_code(school_code_raw)
    
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        if 'metadata' not in data:
            data['metadata'] = {}
        
        enrich = METADATA_CACHES['enrichment'].get(school_code, {})
        
        # Update metadata with priority: existing (from LLM) > enrichment
        data['metadata']['school_id'] = school_code
        data['metadata']['denominazione'] = data['metadata'].get('denominazione') or enrich.get('denominazione') or 'ND'
        data['metadata']['comune'] = data['metadata'].get('comune') or enrich.get('comune') or 'ND'
        data['metadata']['area_geografica'] = data['metadata'].get('area_geografica') or enrich.get('area_geografica') or 'ND'
        data['metadata']['ordine_grado'] = data['metadata'].get('ordine_grado') or enrich.get('ordine_grado') or 'ND'
        data['metadata']['territorio'] = data['metadata'].get('territorio') or 'ND'
        data['metadata']['tipo_scuola'] = data['metadata'].get('tipo_scuola') or 'ND'
        
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
            
        return self.call_ollama(prompt_template, context=ptof_text)
    
    def draft_chunk(self, chunk_text, chunk_num, total_chunks):
        """Analyze a single chunk of the document."""
        logging.info(f"[{self.model}] Drafting chunk {chunk_num}/{total_chunks}...")
        prompt_template = PROMPTS.get("Analyst", "")
        if not prompt_template:
            return ""
        
        chunk_prompt = f"""{prompt_template}

NOTA: Questa è la SEZIONE {chunk_num} di {total_chunks} del documento PTOF.
Analizza SOLO questa sezione e restituisci i punteggi trovati."""
        
        return self.call_ollama(chunk_prompt, context=chunk_text)


class SynthesizerAgent(BaseAgent):
    """Agent that synthesizes multiple partial analyses into one."""
    def __init__(self):
        super().__init__(MODEL_SYNTHESIZER, "Sintetizzatore di Analisi Multiple")
    
    def synthesize(self, partial_results):
        """Combine multiple JSON analyses into one unified result."""
        logging.info(f"[{self.model}] Synthesizing {len(partial_results)} partial results...")
        
        synthesis_prompt = f"""Sei un sintetizzatore di analisi PTOF.
Hai ricevuto {len(partial_results)} analisi parziali dello stesso documento PTOF.

ISTRUZIONI:
1. Unifica tutte le analisi in un singolo JSON completo
2. Per ogni indicatore con punteggio, scegli il punteggio PIÙ ALTO trovato
3. Per liste (partner, attività), combina tutti gli elementi unici
4. Per metadata, usa i valori non-ND trovati
5. Restituisci SOLO il JSON unificato, nessun altro testo

ANALISI PARZIALI:
{json.dumps(partial_results, indent=2, ensure_ascii=False)}

JSON UNIFICATO:"""
        
        return self.call_ollama(synthesis_prompt)

class ReviewerAgent(BaseAgent):
    def __init__(self):
        super().__init__(MODEL_REVIEWER, "Revisore Critico e Logico (Red Teaming)")

    def critique_report(self, source_text, draft_report):
        logging.info(f"[{self.model}] Critiquing report...")
        
        if not draft_report:
            logging.error("[Reviewer] draft_report is None or empty!")
            return None
            
        prompt_template = PROMPTS.get("Reviewer", "")
        if not prompt_template:
            logging.error("[Reviewer] Reviewer prompt not found!")
            return None
        
        prompt = prompt_template.replace("{{DRAFT_REPORT}}", str(draft_report))
        return self.call_ollama(prompt, context=source_text)

class RefinerAgent(BaseAgent):
    def __init__(self):
        super().__init__(MODEL_REFINER, "Editor Finale e Correttore")

    def refine_report(self, draft_report, critique):
        logging.info(f"[{self.model}] Refining report...")
        
        if not draft_report:
            logging.error("[Refiner] draft_report is None or empty!")
            return None
        if not critique:
            logging.warning("[Refiner] critique is None - using empty string")
            critique = ""
            
        prompt_template = PROMPTS.get("Refiner", "")
        if not prompt_template:
            logging.error("[Refiner] Refiner prompt not found!")
            return None
        
        prompt = prompt_template.replace("{{DRAFT_REPORT}}", str(draft_report)).replace("{{CRITIQUE}}", str(critique))
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

def process_single_ptof(md_file, analyst, reviewer, refiner, synthesizer=None, results_dir=RESULTS_DIR, status_callback=None):
    """
    Process a single PTOF file through the Agentic Pipeline.
    Automatically uses chunked analysis for long documents.
    status_callback: function(msg) to report progress
    """
    school_Code = os.path.basename(md_file).replace('.md', '')
    final_md_path = os.path.join(results_dir, f"{school_Code}_analysis.md")
    final_json_path = os.path.join(results_dir, f"{school_Code}_analysis.json")
    
    if status_callback: status_callback(f"Processing {school_Code}...")
    
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    content_size = len(content)
    
    # Check if we need chunked analysis
    if content_size > LONG_DOC_THRESHOLD:
        logging.info(f"[Pipeline] Long document ({content_size} chars) - using chunked analysis")
        if status_callback: status_callback(f"Long doc ({content_size//1000}k chars) - chunking...")
        
        # Split document
        chunks = smart_split(content, CHUNK_SIZE)
        info = get_chunk_info(chunks)
        logging.info(f"[Pipeline] Split into {info['count']} chunks")
        
        # Analyze each chunk
        partial_results = []
        for i, chunk in enumerate(chunks):
            if status_callback: status_callback(f"Analyst: Chunk {i+1}/{len(chunks)}...")
            
            chunk_draft = analyst.draft_chunk(chunk, i+1, len(chunks))
            if chunk_draft:
                chunk_draft = sanitize_json(chunk_draft)
                try:
                    partial_json = json.loads(chunk_draft)
                    partial_results.append(partial_json)
                except:
                    logging.warning(f"[Pipeline] Chunk {i+1} parse failed")
        
        if not partial_results:
            logging.error("[Pipeline] No valid chunk results")
            return None
        
        # Synthesize if we have a synthesizer
        if synthesizer and len(partial_results) > 1:
            if status_callback: status_callback("Synthesizer: Combining results...")
            draft = synthesizer.synthesize(partial_results)
            draft = sanitize_json(draft)
        elif len(partial_results) == 1:
            draft = json.dumps(partial_results[0])
        else:
            # Manual merge if no synthesizer
            from src.processing.cloud_review import merge_partial_analyses
            merged = merge_partial_analyses(partial_results)
            draft = json.dumps(merged)
    else:
        # Standard single-pass analysis
        if status_callback: status_callback("Analyst: Drafting report...")
        draft = analyst.draft_report(content)
        if not draft: return None
        draft = sanitize_json(draft)
    
    # Save Draft JSON
    try:
        with open(final_json_path, 'w') as f:
            f.write(draft) 
    except:
        pass
    
    # Enrich JSON
    # Try to extract metadata using Cloud (if available) or basic rules
    try:
        from src.processing.cloud_review import extract_metadata_from_header, load_api_config
        
        # Load config to get keys for extraction
        api_config = load_api_config()
        # Use OpenRouter with free model for metadata extraction
        # Reason: Gemini quota limits (429 errors), OpenRouter has free models
        prov = 'openrouter'
        key = api_config.get('openrouter_api_key')
        
        if key:
            logging.info("Extracting metadata with Cloud LLM (OpenRouter)...")
            meta = extract_metadata_from_header(content, prov, key, "google/gemini-2.0-flash-exp:free")
            if meta:
                # Merge into JSON
                try:
                    with open(final_json_path, 'r') as f:
                        curr_data = json.load(f)
                    
                    if 'metadata' not in curr_data: curr_data['metadata'] = {}
                    curr_data['metadata'].update(meta)
                    
                    with open(final_json_path, 'w') as f:
                        json.dump(curr_data, f, indent=2)
                except Exception as ex:
                    logging.error(f"Failed merging metadata: {ex}")
    except Exception as e:
        logging.error(f"Metadata extraction failed: {e}")

    enrich_json_metadata(final_json_path, school_Code)
        
    # Extract Narrative
    try:
        draft_json = json.loads(draft)
        narrative = draft_json.get('narrative', '')
    except:
        narrative = draft

    # 2. Critique
    if status_callback: status_callback("Reviewer: Critiquing...")
    critique = reviewer.critique_report(content, narrative)
    
    if critique:
        logging.info(f"Reviewer says: {critique[:100]}...")
    else:
        logging.warning("Reviewer returned None - skipping review step")
        critique = ""
    
    # 3. Refine (only if critique has content)
    final_output = narrative
    if critique and "APPROVATO" not in critique.upper() and len(critique) > 10:
         if status_callback: status_callback("Refiner: Improving report...")
         refined_json_str = refiner.refine_report(draft, critique)
         
         if refined_json_str:
             refined_json_str = sanitize_json(refined_json_str)
             try:
                 refined_data = json.loads(refined_json_str)
                 with open(final_json_path, 'w') as f:
                     f.write(refined_json_str)
                 
                 final_output = refined_data.get('narrative', '')
             except Exception as e:
                 logging.error(f"Failed to parse Refiner JSON: {e}")
         else:
             logging.warning("Refiner returned None - keeping original draft")
    else:
         logging.info("Report approved directly or no critique available.")

    # Save Final MD
    with open(final_md_path, 'w') as f:
        f.write(final_output)
    
    # Return parsed JSON result
    try:
        with open(final_json_path, 'r') as f:
             return json.load(f)
    except:
        return {}

def run_pipeline():
    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR)
        
    md_files = glob(os.path.join(MD_DIR, "*.md"))
    logging.info(f"Found {len(md_files)} markdown files to process.")
    
    analyst = AnalystAgent()
    reviewer = ReviewerAgent()
    refiner = RefinerAgent()
    synthesizer = SynthesizerAgent()
    
    for md_file in md_files:
        school_Code = os.path.basename(md_file).replace('.md', '')
        final_md_path = os.path.join(RESULTS_DIR, f"{school_Code}_analysis.md")
        
        if os.path.exists(final_md_path):
            logging.info(f"Skipping {school_Code} (Already completed)")
            continue
            
        logging.info(f"___ Processing {school_Code} ___")
        
        process_single_ptof(md_file, analyst, reviewer, refiner, synthesizer)
        
        # Incrementally update CSV for dashboard (Batch update mainly, but do it per file to help)
        try:
            import subprocess
            subprocess.run(['python', 'src/processing/refine_metadata.py'], capture_output=True, timeout=60)
            subprocess.run(['python', 'src/processing/align_metadata.py'], capture_output=True, timeout=120)
            logging.info(f"CSV updated for {school_Code}")
        except Exception as e:
            logging.warning(f"CSV rebuild failed: {e}")

if __name__ == "__main__":
    run_pipeline()
