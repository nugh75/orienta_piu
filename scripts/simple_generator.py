import sys
print("STARTING SIMPLE GENERATOR", flush=True)
from pathlib import Path
from dotenv import load_dotenv
import logging

load_dotenv()
print("ENV LOADED", flush=True)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# logging setup
logging.basicConfig(level=logging.INFO)

try:
    from src.agents.meta_report.synthesis_skeleton import SynthesisSkeleton
    print("IMPORTED SKELETON", flush=True)
except ImportError as e:
    print(f"IMPORT ERROR: {e}")
    sys.exit(1)

print("INSTANTIATING SKELETON...", flush=True)
filters = {"ordine_grado": "II Grado"}
skeleton = SynthesisSkeleton(
    base_dir=PROJECT_ROOT,
    filters=filters,
    max_narrative_samples=30
)

print("LOADING DATA...", flush=True)
try:
    skeleton.load_data()
    print("DATA LOADED", flush=True)
except Exception as e:
    print(f"DATA LOAD ERROR: {e}")
    sys.exit(1)

print("GENERATING SKELETON...", flush=True)
try:
    text = skeleton.generate_skeleton()
    print("SKELETON GENERATED", flush=True)
except Exception as e:
    print(f"GENERATION ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Save
output_path = PROJECT_ROOT / "reports" / "synthesis" / "simple_skeleton.md"
output_path.write_text(text, encoding="utf-8")
print(f"SAVED TO {output_path}", flush=True)
