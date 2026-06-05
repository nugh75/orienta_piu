import sys
from pathlib import Path
import logging

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.agents.meta_report.synthesis_skeleton import SynthesisSkeleton

logging.basicConfig(level=logging.INFO)

def test_retrieval():
    print("Initializing SynthesisSkeleton...")
    filters = {"ordine_grado": ["I Grado", "II Grado"]}
    skeleton = SynthesisSkeleton(base_dir=PROJECT_ROOT, filters=filters)
    
    print("Calling get_slot_contexts()...")
    contexts = skeleton.get_slot_contexts()
    
    print(f"Retrieved contexts for {len(contexts)} slots.")
    
    for key, ctx in contexts.items():
        n_chunks = len(ctx.get("narrative_excerpts", []))
        print(f"Slot: {key} -> {n_chunks} chunks")
        if n_chunks > 0:
            first = ctx["narrative_excerpts"][0]
            print(f"  Sample: {first['denominazione']} ({first['regione']})")
            print(f"  Excerpt: {first['excerpt'][:100]}...")

if __name__ == "__main__":
    test_retrieval()
