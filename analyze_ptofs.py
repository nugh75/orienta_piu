import os
import glob
import pandas as pd
import json
import logging
import time
from pypdf import PdfReader
import requests
import re

# --- Configuration ---
PTOF_DIR = 'ptof'
RESULTS_DIR = 'analysis_results'
SUMMARY_FILE = 'data/analysis_summary.csv'
METADATA_FILE = 'data/candidati_ptof.csv'
LOG_FILE = 'analysis.log'

# Ollama Configuration
OLLAMA_URL = 'http://192.168.129.14:11434/api/generate'
OLLAMA_MODEL = 'gemma3:27b'
CHUNK_SIZE = 8000  # Characters per chunk

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

# Load Metadata Cache
metadata_cache = {}
if os.path.exists(METADATA_FILE):
    try:
        df_meta = pd.read_csv(METADATA_FILE, sep=';', on_bad_lines='skip')
        df_meta.columns = [c.strip().lower() for c in df_meta.columns] 
        for _, row in df_meta.iterrows():
            code = str(row.get('istituto', '')).strip()
            if code:
                metadata_cache[code] = row.to_dict()
        logging.info(f"Loaded metadata for {len(metadata_cache)} schools")
    except Exception as e:
        logging.error(f"Error loading metadata: {e}")

def setup_dirs():
    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR)
    if not os.path.exists('data'):
        os.makedirs('data')

def extract_text_chunks(pdf_path, chunk_size=CHUNK_SIZE):
    """
    Extracts text from PDF and splits into chunks.
    """
    try:
        reader = PdfReader(pdf_path)
        full_text = ""
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                full_text += f"\n[PAGINA {i+1}]\n{text}"
        
        # Split into chunks
        chunks = []
        for i in range(0, len(full_text), chunk_size):
            chunks.append(full_text[i:i+chunk_size])
        return chunks
    except Exception as e:
        logging.error(f"Error processing PDF {pdf_path}: {e}")
        return []

def build_chunk_prompt(school_meta, chunk_num, total_chunks):
    """
    Builds a prompt for analyzing a single chunk.
    """
    school_info = f"""
    METADATI SCUOLA:
    - school_id: {school_meta.get('istituto', 'ND')}
    - denominazione: {school_meta.get('denominazionescuola', 'ND')}
    - ordine_grado: {school_meta.get('ordine_grado', 'ND')}
    """
    
    prompt = f"""
    RUOLO: Sei un analista esperto di politiche scolastiche e orientamento.
    
    CONTESTO: Stai analizzando il CHUNK {chunk_num} di {total_chunks} di un PTOF.
    {school_info}
    
    ISTRUZIONI:
    Estrai dal testo seguente SOLO le informazioni rilevanti per l'ORIENTAMENTO scolastico.
    Per ogni elemento trovato, fornisci:
    - Categoria (Finalità, Obiettivi, Partnership, Attività, Didattica, Governance)
    - Evidenza testuale (citazione breve)
    - Pagina di riferimento se presente
    - Punteggio preliminare (1-7) basato sulla qualità/dettaglio della descrizione
    
    Rispondi SOLO in formato JSON con questa struttura:
    {{
      "chunk_id": {chunk_num},
      "findings": [
        {{
          "categoria": "...",
          "sottocategoria": "...",
          "evidence_quote": "...",
          "evidence_location": "...",
          "preliminary_score": 1-7
        }}
      ]
    }}
    
    Se non trovi nulla di rilevante, rispondi con "findings": [].
    """
    return prompt

def build_aggregation_prompt(school_meta, chunk_results):
    """
    Builds a prompt to aggregate results from all chunks into final analysis.
    """
    school_info = f"""
    METADATI SCUOLA:
    - school_id: {school_meta.get('istituto', 'ND')}
    - denominazione: {school_meta.get('denominazionescuola', 'ND')}
    - ordine_grado: {school_meta.get('ordine_grado', 'ND')}
    - anno_ptof: 2022-2025
    """
    
    # Convert chunk results to string
    findings_str = json.dumps(chunk_results, indent=2, ensure_ascii=False)
    
    prompt = f"""
    RUOLO: Sei un analista esperto di politiche scolastiche e orientamento.
    
    CONTESTO:
    {school_info}
    
    HAI RICEVUTO LE SEGUENTI EVIDENZE DA TUTTI I CHUNK DEL DOCUMENTO:
    {findings_str}
    
    ISTRUZIONI:
    Aggrega le evidenze e produci l'analisi FINALE con:
    
    PARTE 1 - JSON STRUTTURATO (OBBLIGATORIO):
    Restituisci un JSON con questa struttura ESATTA:
    
    {{
      "metadata": {{
        "school_id": "...", "denominazione": "...", "ordine_grado": "I_grado|II_grado|Infanzia|ND", "anno_ptof": "2022-2025", "fonte": "PDF"
      }},
      "extraction_quality": {{ "status": "ok|parziale|critica", "notes": "..." }},

      "ptof_section2": {{
        "2_1_ptof_orientamento_sezione_dedicata": {{ 
          "has_sezione_dedicata": 0|1, 
          "score": 1-7, 
          "evidence_quote": "...", 
          "evidence_location": "...",
          "note": "has_sezione_dedicata=1 se esiste una sezione/capitolo specifico per l'orientamento. 0 se l'orientamento è menzionato solo in modo sparso nel documento. Lo score indica la qualità della descrizione."
        }},

        "2_2_partnership": {{
          "tipologie": {{
            "interni": {{ "value": 0|1, "evidence_quote": "...", "evidence_location": "..." }},
            "scuole_primarie": {{ "value": 0|1, "evidence_quote": "...", "evidence_location": "..." }},
            "licei": {{ "value": 0|1, "evidence_quote": "...", "evidence_location": "..." }},
            "tecnici": {{ "value": 0|1, "evidence_quote": "...", "evidence_location": "..." }},
            "professionali": {{ "value": 0|1, "evidence_quote": "...", "evidence_location": "..." }},
            "iefp": {{ "value": 0|1, "evidence_quote": "...", "evidence_location": "..." }},
            "universita": {{ "value": 0|1, "evidence_quote": "...", "evidence_location": "..." }},
            "aziende": {{ "value": 0|1, "evidence_quote": "...", "evidence_location": "..." }},
            "enti_pubblici_territoriali": {{ "value": 0|1, "evidence_quote": "...", "evidence_location": "..." }},
            "terzo_settore": {{ "value": 0|1, "evidence_quote": "...", "evidence_location": "..." }},
            "altro": {{ "value": 0|1, "evidence_quote": "...", "evidence_location": "..." }}
          }},
          "partner_nominati": ["..."], "altro_testo": "..."
        }},

        "2_3_finalita": {{
          "finalita_attitudini": {{ "score": 1-7, "evidence_quote": "...", "evidence_location": "..." }},
          "finalita_interessi": {{ "score": 1-7, "evidence_quote": "...", "evidence_location": "..." }},
          "finalita_progetto_vita": {{ "score": 1-7, "evidence_quote": "...", "evidence_location": "..." }},
          "finalita_transizioni_formative": {{ "score": 1-7, "evidence_quote": "...", "evidence_location": "..." }},
          "finalita_capacita_orientative_opportunita": {{ "score": 1-7, "evidence_quote": "...", "evidence_location": "..." }}
        }},

        "2_4_obiettivi": {{
          "obiettivo_ridurre_abbandono": {{ "score": 1-7, "evidence_quote": "...", "evidence_location": "..." }},
          "obiettivo_continuita_territorio": {{ "score": 1-7, "evidence_quote": "...", "evidence_location": "..." }},
          "obiettivo_contrastare_neet": {{ "score": 1-7, "evidence_quote": "...", "evidence_location": "..." }},
          "obiettivo_lifelong_learning": {{ "score": 1-7, "evidence_quote": "...", "evidence_location": "..." }}
        }},

        "2_5_azioni_sistema": {{
          "azione_coordinamento_servizi": {{ "score": 1-7, "evidence_quote": "...", "evidence_location": "..." }},
          "azione_dialogo_docenti_studenti": {{ "score": 1-7, "evidence_quote": "...", "evidence_location": "..." }},
          "azione_rapporto_scuola_genitori": {{ "score": 1-7, "evidence_quote": "...", "evidence_location": "..." }},
          "azione_monitoraggio_azioni": {{ "score": 1-7, "evidence_quote": "...", "evidence_location": "..." }},
          "azione_sistema_integrato_inclusione_fragilita": {{ "score": 1-7, "evidence_quote": "...", "evidence_location": "..." }}
        }},

        "2_6_didattica_orientativa": {{
          "didattica_da_esperienza_studenti": {{ "score": 1-7, "evidence_quote": "...", "evidence_location": "..." }},
          "didattica_laboratoriale": {{ "score": 1-7, "evidence_quote": "...", "evidence_location": "..." }},
          "didattica_flessibilita_spazi_tempi": {{ "score": 1-7, "evidence_quote": "...", "evidence_location": "..." }},
          "didattica_interdisciplinare": {{ "score": 1-7, "evidence_quote": "...", "evidence_location": "..." }}
        }},

        "2_7_opzionali_facoltative": {{
          "opzionali_culturali": {{ "score": 1-7, "evidence_quote": "...", "evidence_location": "..." }},
          "opzionali_laboratoriali_espressive": {{ "score": 1-7, "evidence_quote": "...", "evidence_location": "..." }},
          "opzionali_ludiche_ricreative": {{ "score": 1-7, "evidence_quote": "...", "evidence_location": "..." }},
          "opzionali_volontariato": {{ "score": 1-7, "evidence_quote": "...", "evidence_location": "..." }},
          "opzionali_sportive": {{ "score": 1-7, "evidence_quote": "...", "evidence_location": "..." }}
        }}
      }},

      "ptof_section2_only_if_II_grado": {{
        "2_8_rete_passaggi_orizzontali": {{ "score": 1-7, "label": "...", "evidence_quote": "...", "evidence_location": "..." }}
      }},

      "activities_register": [
        {{ "activity_id": "...", "titolo_attivita": "...", "categoria_principale": "PCTO|Orientamento|Altro", "ore_dichiarate": "...", "target": "...", "evidence_quote": "...", "evidence_location": "..." }}
      ],

      "derived_indices": {{
        "partnership_count": "...", "activities_count": "...", "mean_finalita": "...", "mean_obiettivi": "...", "mean_governance": "...", "mean_didattica_orientativa": "...", "mean_opportunita": "...", "ptof_orientamento_maturity_index": "..."
      }}
    }}

    PARTE 2 - ANALISI NARRATIVA (DOPO IL JSON):
    Scrivi un report approfondito (800-1200 parole) con queste sezioni:
    1) Collocazione dell'orientamento nel documento
    2) Finalità e obiettivi dichiarati
    3) Azioni e attività operative
    4) Reti e partnership
    5) Inclusione ed equità
    6) Monitoraggio e miglioramento
    7) Gap Analysis (cosa manca)
    
    VINCOLI IMPORTANTI:
    - Cita sempre le pagine di riferimento.
    - NON usare tag markdown come ```markdown.
    - NON DARE SUGGERIMENTI O RACCOMANDAZIONI. Non scrivere frasi come "si suggerisce di", "sarebbe opportuno", "si consiglia". 
    - Il tuo compito è FOTOGRAFARE LA SITUAZIONE ATTUALE, non proporre miglioramenti.
    - Nella Gap Analysis, limita a CONSTATARE le assenze ("Manca...", "Non è presente...", "Assente...") senza suggerire come colmarle.
    """
    return prompt

def call_ollama(prompt, text_content=""):
    """
    Calls Ollama API with the given prompt and text.
    """
    full_prompt = f"{prompt}\n\nTESTO DA ANALIZZARE:\n{text_content}" if text_content else prompt
    
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                'model': OLLAMA_MODEL,
                'prompt': full_prompt,
                'stream': False,
                'options': {
                    'temperature': 0.3,
                    'num_ctx': 16384
                }
            },
            timeout=600  # 10 minutes timeout
        )
        response.raise_for_status()
        return response.json().get('response', '')
    except Exception as e:
        logging.error(f"Ollama API Error: {e}")
        return None

def analyze_school(pdf_path):
    filename = os.path.basename(pdf_path)
    # Regex for Codice Meccanografico: 2 letters + 8 alphanumeric chars
    school_code = re.search(r'([A-Z]{2}[A-Z0-9]{8})', filename)
    if not school_code:
        school_code = re.search(r'([A-Z]{2}\w{8})', filename)

    if not school_code:
        logging.warning(f"Skipping {filename} (No school code)")
        return

    school_code = school_code.group(1).upper()
    meta = metadata_cache.get(school_code, {'istituto': school_code})
    
    result_file = os.path.join(RESULTS_DIR, f"{school_code}_analysis.json")
    if os.path.exists(result_file):
        logging.info(f"Skipping {school_code} (Already Analyzed)")
        return

    logging.info(f"Analyzing {school_code}...")
    start_time = time.time()
    
    # 1. Extract Text Chunks
    chunks = extract_text_chunks(pdf_path)
    if not chunks:
        logging.warning(f"Empty text for {school_code}")
        return
    
    logging.info(f"Extracted {len(chunks)} chunks for {school_code}")

    # PTOF Validation Check (on first chunk)
    header_text = chunks[0][:5000].lower() if chunks else ""
    valid_keywords = ["ptof", "piano triennale", "offerta formativa", "piano dell'offerta", "triennio"]
    if not any(k in header_text for k in valid_keywords):
        logging.warning(f"⏩ SKIPPED {school_code}: Not recognized as PTOF")
        return

    # 2. Analyze Each Chunk
    all_findings = []
    for i, chunk in enumerate(chunks):
        chunk_prompt = build_chunk_prompt(meta, i+1, len(chunks))
        logging.info(f"  Processing chunk {i+1}/{len(chunks)}...")
        
        chunk_response = call_ollama(chunk_prompt, chunk)
        if chunk_response:
            try:
                # Extract JSON from response
                json_start = chunk_response.find('{')
                json_end = chunk_response.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    chunk_data = json.loads(chunk_response[json_start:json_end])
                    findings = chunk_data.get('findings', [])
                    all_findings.extend(findings)
            except json.JSONDecodeError:
                logging.warning(f"  Failed to parse chunk {i+1} response")
        
        time.sleep(2)  # Rate limiting between chunks

    logging.info(f"Collected {len(all_findings)} findings from all chunks")

    # 3. Aggregate Results
    aggregation_prompt = build_aggregation_prompt(meta, all_findings)
    logging.info(f"Generating final analysis...")
    
    final_response = call_ollama(aggregation_prompt)
    if not final_response:
        logging.error(f"Failed to generate final analysis for {school_code}")
        return

    duration = time.time() - start_time
    
    # 4. Parse and Save
    try:
        json_start = final_response.find('{')
        json_end = final_response.rfind('}') + 1
        
        if json_start != -1 and json_end > json_start:
            json_str = final_response[json_start:json_end]
            json_data = json.loads(json_str)
            
            # Extract Narrative
            narrative_text = final_response[json_end:].strip()
            narrative_text = narrative_text.replace("```markdown", "").replace("```", "").strip()
            
            # Save JSON
            with open(result_file, 'w') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            
            # Save Markdown Report
            md_file = result_file.replace('.json', '.md')
            header = f"""# Analisi Orientamento PTOF

**Istituto:** {meta.get('denominazionescuola', 'ND')}
**Codice Meccanografico:** {school_code}
**Territorio:** {meta.get('nome_comune', 'ND')}
**Grado:** {meta.get('ordine_grado', 'ND')}
**Anno PTOF:** 2022-2025

---
"""
            if not narrative_text:
                narrative_text = "Nessuna narrativa generata."
            
            with open(md_file, 'w') as f:
                f.write(header + "\n" + narrative_text)

            logging.info(f"✅ Analyzed {school_code} in {duration:.1f}s")
            
            # Update Summary CSV
            summary_data = {
                'school_id': school_code,
                'denominazione': meta.get('denominazionescuola', 'ND'),
                'comune': meta.get('nome_comune', 'ND'),
                'analysis_file': md_file,
                'duration_sec': round(duration, 1),
                'extraction_status': json_data.get('extraction_quality', {}).get('status', 'ND')
            }
            
            section2 = json_data.get('ptof_section2', {})
            def get_score(sec_data):
                if isinstance(sec_data, dict):
                    return sec_data.get('score', 0)
                return 0

            summary_data['2_1_score'] = get_score(section2.get('2_1_ptof_orientamento_sezione_dedicata'))
            sec_2_3 = section2.get('2_3_finalita', {})
            for key in sec_2_3:
                summary_data[f"2_3_{key}_score"] = get_score(sec_2_3[key])
            sec_2_4 = section2.get('2_4_obiettivi', {})
            for key in sec_2_4:
                summary_data[f"2_4_{key}_score"] = get_score(sec_2_4[key])
            
            # Extract Derived Indices
            derived = json_data.get('derived_indices', {})
            for key, val in derived.items():
                summary_data[key] = val

            import csv
            file_exists = os.path.isfile(SUMMARY_FILE)
            with open(SUMMARY_FILE, 'a', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=summary_data.keys())
                if not file_exists:
                    writer.writeheader()
                writer.writerow(summary_data)
                
    except json.JSONDecodeError as e:
        logging.error(f"JSON parsing error for {school_code}: {e}")
    except Exception as e:
        logging.error(f"Error saving results for {school_code}: {e}")
    
    time.sleep(5)  # Pause between schools

def main():
    setup_dirs()
    pdf_files = glob.glob(os.path.join(PTOF_DIR, "*.pdf"))
    logging.info(f"Found {len(pdf_files)} PDFs in {PTOF_DIR}.")
    
    for pdf_path in pdf_files:
        analyze_school(pdf_path)
    
    logging.info("Analysis complete.")

if __name__ == "__main__":
    main()
