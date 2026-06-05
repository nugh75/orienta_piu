import logging
import json
import os
import requests
from sentence_transformers import SentenceTransformer
from src.agents.meta_report.db_manager import DatabaseManager
from src.agents.meta_report.synthesis_skeleton import THEMATIC_SECTIONS
from src.agents.meta_report.providers.ollama import OllamaProvider

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CLUSTERS_FILE = 'data/clusters.json'
OUTPUT_FILE = 'data/cluster_summaries.json'
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
OLLAMA_MODEL = "gemma3:27b"

def main():
    logger.info("Starting Cluster Summarization...")
    
    # 1. Load Clusters
    with open(CLUSTERS_FILE, 'r') as f:
        cluster_data = json.load(f)
        
    assignments = cluster_data['assignments']
    # Group schools by cluster
    clusters = {}
    for code, label in assignments.items():
        label = str(label)
        if label not in clusters:
            clusters[label] = []
        clusters[label].append(code)
        
    logger.info(f"Loaded {len(clusters)} clusters.")
    
    # 2. Init components
    db = DatabaseManager()
    encoder = SentenceTransformer(MODEL_NAME)
    llm = OllamaProvider(model=OLLAMA_MODEL)
    
    summaries = {}
    
    # 3. Iterate Clusters
    for label, school_codes in clusters.items():
        logger.info(f"Processing Cluster {label} ({len(school_codes)} schools)...")
        summaries[label] = {}
        
        # 4. Iterate Sections
        for section in THEMATIC_SECTIONS:
            key = section['key']
            query = section['retrieval_query']
            logger.info(f"  > Section: {key}")
            
            # Encode query
            query_emb = encoder.encode(query).tolist()
            
            # Retrieve Cluster-Specific Chunks
            chunks = db.search_similar_chunks(
                query_embedding=query_emb,
                school_codes=school_codes,
                limit=20 
            )
            
            if not chunks:
                logger.warning(f"  No chunks found for {key} in Cluster {label}")
                summaries[label][key] = "Nessuna evidenza rilevata."
                continue
                
            # Prepare Prompt
            narratives = "\n\n".join([
                f"SCUOLA {c['school_code']} ({c.get('region', 'N/A')}): {c['content']}" 
                for c in chunks
            ])
            
            prompt = f"""
            Analizza questi estratti di PTOF provenienti da un gruppo omogeneo di scuole (Cluster {label}).
            Tema: {section['title']} ({section['description']}).
            
            Scrivi un breve paragrafo (max 150 parole) che sintetizzi l'approccio DOMINANTE di questo gruppo su questo tema.
            Evidenzia:
            - Cosa accomuna queste scuole?
            - Cita 1-2 esempi specifici o "gemme" usando il formato: "La scuola [CODICE]...".
            - Tono: Obiettivo e analitico.
            
            ESTRATTI:
            {narratives}
            """
            
            # Generate
            try:
                # Use a simple system prompt or none
                response = llm.generate(prompt, "Sei un analista di dati scolastici.")
                if hasattr(response, 'content'):
                    text = response.content
                else:
                    text = str(response)
                    
                summaries[label][key] = text.strip()
            except Exception as e:
                logger.error(f"LLM Generation failed: {e}")
                summaries[label][key] = "Errore nella generazione."
                
    # 5. Generate representative names for each cluster
    logger.info("Generating representative cluster names...")
    for label in summaries:
        sintesi = summaries[label].get("sintesi_generale", "")
        if not sintesi or sintesi == "Nessuna evidenza rilevata.":
            summaries[label]["_cluster_name"] = f"Cluster {label}"
            continue

        name_prompt = f"""Basandoti sulla seguente sintesi di un gruppo di scuole, genera un NOME BREVE
e rappresentativo (massimo 5 parole) che catturi il tratto dominante di questo gruppo.

Il nome deve essere descrittivo e neutro (non giudicante).
Esempi di formato: "Orientamento frammentario e implicito", "Forte integrazione territoriale",
"Documentazione strutturata e completa", "Focus su didattica laboratoriale".

Rispondi SOLO con il nome, senza virgolette, senza spiegazioni.

SINTESI:
{sintesi[:1500]}"""

        try:
            response = llm.generate(name_prompt, "Sei un analista di dati scolastici.")
            if hasattr(response, 'content'):
                name = response.content.strip()
            else:
                name = str(response).strip()
            # Clean up: remove quotes, markdown, extra whitespace
            name = name.strip('"\'').strip()
            name = name.split('\n')[0].strip()
            if len(name) > 80:
                name = name[:80].rsplit(' ', 1)[0]
            summaries[label]["_cluster_name"] = name
            logger.info(f"  Cluster {label} → {name}")
        except Exception as e:
            logger.error(f"Failed to generate name for Cluster {label}: {e}")
            summaries[label]["_cluster_name"] = f"Cluster {label}"

    # 6. Save Summaries
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(summaries, f, indent=2)

    logger.info(f"Summaries saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
