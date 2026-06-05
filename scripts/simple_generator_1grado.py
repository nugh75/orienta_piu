import sys
from pathlib import Path
from dotenv import load_dotenv
import logging

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO)

from src.agents.meta_report.synthesis_skeleton import SynthesisSkeleton

print("GENERATING I GRADO REPORT...", flush=True)

filters = {"ordine_grado": "I Grado"}
skeleton = SynthesisSkeleton(
    base_dir=PROJECT_ROOT,
    filters=filters,
    max_narrative_samples=30
)

skeleton.load_data()
print(f"DATA LOADED — {skeleton.stats.get('n_schools', '?')} schools", flush=True)

text = skeleton.generate_skeleton()

output_path = PROJECT_ROOT / "reports" / "synthesis" / "skeleton_1grado.md"
output_path.write_text(text, encoding="utf-8")
print(f"SAVED TO {output_path}", flush=True)
