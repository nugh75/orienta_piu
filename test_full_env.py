import sys
import traceback
from pathlib import Path

try:
    print("STARTING TEST")
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("Dotenv loaded")
    except ImportError:
        print("Dotenv not found")

    PROJECT_ROOT = Path(__file__).resolve().parent
    sys.path.insert(0, str(PROJECT_ROOT))
    print(f"Path inserted: {PROJECT_ROOT}")

    print("Importing skeleton...")
    from src.agents.meta_report.synthesis_skeleton import SynthesisSkeleton
    print("Skeleton imported")

    print("Importing matplotlib...")
    import matplotlib.pyplot as plt
    print("Matplotlib imported")

except Exception:
    traceback.print_exc()

try:
    print("Importing filler...")
    from src.agents.meta_report.synthesis_filler import SynthesisFiller
    print("Filler imported")
except Exception:
    import traceback
    traceback.print_exc()
