import sys
import traceback
try:
    print("Importing synthesis_skeleton...")
    from src.agents.meta_report.synthesis_skeleton import SynthesisSkeleton
    print("Import successful!")
    print("Testing matplotlib backend...")
    import matplotlib.pyplot as plt
    print("Matplotlib imported.")
except Exception:
    traceback.print_exc()
