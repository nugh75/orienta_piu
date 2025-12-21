
import sys
import os
import inspect

# Add project root to path
sys.path.insert(0, os.getcwd())

from src.processing.background_reviewer import BackgroundReviewer

def check_signature():
    print(f"File location: {inspect.getfile(BackgroundReviewer)}")
    sig = inspect.signature(BackgroundReviewer.run_batch_review)
    print(f"Signature of run_batch_review: {sig}")
    
    try:
        reviewer = BackgroundReviewer()
        # Mock callbacks
        def status_cb(msg): print(f"Status: {msg}")
        def stop_cb(): return False
        
        print("Attempting to call run_batch_review...")
        reviewer.run_batch_review(status_callback=status_cb, stop_check_callback=stop_cb)
        print("Success!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_signature()
