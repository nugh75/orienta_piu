import logging
import json
import os
import numpy as np
from sklearn.cluster import KMeans
from collections import defaultdict
from src.agents.meta_report.db_manager import DatabaseManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CLUSTERS_FILE = 'data/clusters.json'
N_CLUSTERS = 5

def main():
    logger.info("Starting School Clustering...")
    
    # 1. Initialize DB Manager and fetch embeddings
    db = DatabaseManager()
    logger.info("Fetching embeddings from database...")
    all_chunks = db.get_all_school_embeddings()
    
    if not all_chunks:
        logger.error("No embeddings found. Exiting.")
        return

    logger.info(f"Fetched {len(all_chunks)} chunks.")

    # 2. Aggregate embeddings by school
    school_embeddings = defaultdict(list)
    for chunk in all_chunks:
        emb = chunk['embedding']
        # Check if valid embedding (list or numpy array)
        if emb is not None and len(emb) > 0:
            school_embeddings[chunk['school_code']].append(emb)
    
    school_codes = []
    X = []
    
    for code, embeddings in school_embeddings.items():
        # Compute mean vector for the school
        # Convert list of lists to numpy array and mean across axis 0
        mean_vec = np.mean(np.array(embeddings), axis=0)
        school_codes.append(code)
        X.append(mean_vec)
        
    X = np.array(X)
    logger.info(f"Computed vectors for {len(school_codes)} schools. Shape: {X.shape}")
    
    # 3. Perform K-Means Clustering
    logger.info(f"Running K-Means with k={N_CLUSTERS}...")
    kmeans = KMeans(n_clusters=N_CLUSTERS, random_state=42, n_init=10)
    kmeans.fit(X)
    labels = kmeans.labels_
    
    # 4. Organize results
    cluster_assignments = {}
    cluster_stats = defaultdict(lambda: {"count": 0, "school_codes": []})
    
    for code, label in zip(school_codes, labels):
        cluster_assignments[code] = int(label)
        cluster_stats[int(label)]["count"] += 1
        cluster_stats[int(label)]["school_codes"].append(code)
        
    logger.info("Clustering complete. Assignments:")
    for label, stats in cluster_stats.items():
        logger.info(f"Cluster {label}: {stats['count']} schools")
        
    # 5. Save results
    output_data = {
        "assignments": cluster_assignments,
        "metadata": {
            "n_clusters": N_CLUSTERS,
            "centers": kmeans.cluster_centers_.tolist(), 
            "stats": cluster_stats
        }
    }
    
    os.makedirs(os.path.dirname(CLUSTERS_FILE), exist_ok=True)
    with open(CLUSTERS_FILE, 'w') as f:
        json.dump(output_data, f, indent=2)
        
    logger.info(f"Cluster data saved to {CLUSTERS_FILE}")

if __name__ == "__main__":
    main()
