
import threading
import time
from collections import deque
import logging
from src.processing.bg_reviewer import BackgroundReviewer
import streamlit as st
import inspect

# Configure logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', force=True)
logger = logging.getLogger(__name__)

# Add file handler for debugging with flush
f_handler = logging.FileHandler('background_debug.log', mode='a')
f_handler.setLevel(logging.DEBUG)
f_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
logger.addHandler(f_handler)

class ReviewController:
    """
    Singleton controller to manage the background review thread.
    Uses st.cache_resource to persist across re-runs.
    """
    def __init__(self):
        self._thread = None
        self._stop_event = threading.Event()
        self._is_running = False
        # Store last 50 log messages
        self.logs = deque(maxlen=50)
        # Store found issues for real-time display
        self.current_issues = [] 

    def start(self):
        """Start the background review process if not already running."""
        if self._is_running and self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._is_running = True
        self.logs.clear()
        self.add_log("🚀 Avvio processo di revisione in background...")
        
        self._thread = threading.Thread(target=self._run_process, daemon=True)
        self._thread.start()

    def start_fixer(self):
        """Start the background fixer process."""
        if self._is_running and self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._is_running = True
        self.logs.clear()
        self.add_log("🛠️ Avvio correzione automatica in background...")
        
        self._thread = threading.Thread(target=self._run_fixer_process, daemon=True)
        self._thread.start()
        logger.info(f"Started Fixer Thread: {self._thread.ident}")

    def _run_fixer_process(self):
        """Internal method for running the fixer."""
        try:
             # Force reload
            import importlib
            import src.processing.bg_fixer
            importlib.reload(src.processing.bg_fixer)
            from src.processing.bg_fixer import BackgroundFixer
            
            fixer = BackgroundFixer()
            
            fixer.run_batch_fix(
                status_callback=self.add_log,
                stop_check_callback=self.should_stop
            )
        except Exception as e:
            self.add_log(f"❌ Errore critico nel thread fixer: {e}")
            logger.error(f"Fixer thread error: {e}", exc_info=True)
        finally:
            self._is_running = False
            self.add_log("Processo di correzione terminato.")

    def stop(self):
        """Signal the background process to stop."""
        if self._is_running:
            self.add_log("🛑 Richiesta di arresto inviata...")
            self._stop_event.set()

    def _run_process(self):
        """Internal method running in the thread."""
        try:
            # Force reload to avoid stale cache
            import importlib
            import src.processing.bg_reviewer
            importlib.reload(src.processing.bg_reviewer)
            from src.processing.bg_reviewer import BackgroundReviewer

            reviewer = BackgroundReviewer()
            
            # Find issues first to restore state if needed (optional)
            # For now, just run
            
            # DEBUG: Inspect the class and method
            import inspect
            try:
                sig = inspect.signature(reviewer.run_batch_review)
                file_loc = inspect.getfile(reviewer.__class__)
                self.add_log(f"DEBUG: Reviewer File: {file_loc}")
                self.add_log(f"DEBUG: Reviewer Sig: {sig}")
            except Exception as insp_e:
                self.add_log(f"DEBUG: Inspection failed: {insp_e}")

            reviewer.run_batch_review(
                status_callback=self.add_log,
                stop_check_callback=self.should_stop
            )
        except Exception as e:
            self.add_log(f"❌ Errore critico nel thread: {e}")
            logger.error(f"Review thread error: {e}", exc_info=True)
        finally:
            self._is_running = False
            self.add_log("Processo terminato.")

    def should_stop(self):
        """Callback for the reviewer to check if it should stop."""
        return self._stop_event.is_set()

    def add_log(self, message):
        """Add a message to the log queue and file."""
        timestamp = time.strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] {message}"
        self.logs.append(formatted_msg)
        logger.info(f"UI_LOG: {message}") # Write to file
        
    def get_logs(self):
        """Return list of logs."""
        return list(self.logs)

    def is_active(self):
        """Check if running. Resets state if thread died unexpectedly."""
        if self._is_running and self._thread:
            if not self._thread.is_alive():
                 # Thread is dead but flag is true -> Zombie state
                 self._is_running = False
                 self.add_log("⚠️ Stato ripristinato (thread terminato).")
        return self._is_running

@st.cache_resource
def get_review_controller_v7():
    """Get the singleton instance."""
    return ReviewController()
