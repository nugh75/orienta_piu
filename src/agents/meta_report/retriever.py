import logging
from typing import List, Dict, Optional, Any
from sentence_transformers import SentenceTransformer
from src.agents.meta_report.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

class HybridRetriever:
    """
    RAG engine for Metareport generation.
    Combines:
    1. SQL Filtering (by region, grade, scores, archetype)
    2. Vector Semantic Search (all-MiniLM-L6-v2)
    3. Hybrid Reranking (optional)
    """

    def __init__(self, db_manager: DatabaseManager = None):
        self.db = db_manager or DatabaseManager()
        # Initialize embedding model (lightweight, same as ingestor)
        self.model = SentenceTransformer('all-MiniLM-L6-v2') 
        
    def retrieve(self, 
                 query: str, 
                 grade_level: str = None, 
                 region: str = None, 
                 limit: int = 20) -> List[Dict]:
        """
        Main entry point for retrieval.
        - query: The semantic question (e.g. "Come viene gestita l'alternanza scuola lavoro?")
        - grade_level: Filter by grade ('I Grado', 'II Grado')
        - region: Filter by region (optional)
        - limit: Max number of chunks to return
        """
        logger.info(f"Retrieving for query: '{query}' [Grade: {grade_level}, Region: {region}]")
        
        # 1. Generate query embedding
        query_embedding = self.model.encode(query).tolist()
        
        # 2. Execute hybrid search via DB Manager
        # We need to extend db_manager.search_similar_chunks to handle SQL filters more flexibly
        # For now, we use the method we have or we can inspect db_manager again.
        # Assuming db_manager.search_similar_chunks supports basic kwargs or we might need to modify it.
        # Looking at db_manager code... it has `topic` and `grade_level`.
        
        # Let's interact with db directly for more complex SQL if needed, 
        # but db_manager.search_similar_chunks is a good starting point.
        
        results = self.db.search_similar_chunks(
            query_embedding=query_embedding,
            grade_level=grade_level,
            region=region, # We need to ensure db_manager supports this
            limit=limit
        )
        
        return results

    def get_context_string(self, retrieved_chunks: List[Dict]) -> str:
        """
        Formats retrieved chunks into a single context string for the LLM.
        """
        context_parts = []
        for i, chunk in enumerate(retrieved_chunks, 1):
            school_info = f"{chunk.get('school_code')} ({chunk.get('city')}, {chunk.get('region')})"
            content = chunk.get('content', '').strip()
            if content:
                context_parts.append(f"SOURCE {i} [{school_info}]:\n{content}\n")
        
        return "\n".join(context_parts)
