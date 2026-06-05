import os
import sys
import signal
import psutil
import logging
from pathlib import Path
import subprocess

logger = logging.getLogger(__name__)

# Use absolute path based on script location to ensure consistency
SCRIPT_DIR = Path(__file__).parent.parent  # Project root
# Store PID file in logs directory (writable in Docker container)
PID_FILE = SCRIPT_DIR / "logs" / "workflow.pid"

def is_process_running(pid):
    """Check if a process with the given PID is running."""
    try:
        process = psutil.Process(pid)
        # Check if it's a python process to be safe (optional but good)
        return process.status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False
    except psutil.AccessDenied:
        return False

def get_running_pid():
    """Get the PID and PGID from file if the process is actually running.

    Returns tuple (pid, pgid) or None if not running.
    """
    if not PID_FILE.exists():
        return None

    try:
        content = PID_FILE.read_text().strip()
        # Support both old format (just PID) and new format (PID:PGID)
        if ':' in content:
            pid_str, pgid_str = content.split(':')
            pid = int(pid_str)
            pgid = int(pgid_str)
        else:
            pid = int(content)
            pgid = pid  # Fallback: assume PGID equals PID

        if is_process_running(pid):
            return (pid, pgid)
        # Stale PID file
        PID_FILE.unlink(missing_ok=True)
        return None
    except ValueError:
        PID_FILE.unlink(missing_ok=True)
        return None

def start_workflow_process(params=None):
    """Start the strata-cycle process in background with optional parameters."""
    if get_running_pid():
        logger.warning("Strata-cycle already running.")
        return False

    try:
        # Build command with parameters
        cmd = ["make", "strata-cycle", "YES=1"]  # YES=1 to skip confirmation
        
        if params:
            if params.get("max_downloads"):
                cmd.append(f"MAX_DOWNLOADS={params['max_downloads']}")
            if params.get("grado"):
                cmd.append(f"G={params['grado']}")
            if params.get("regione"):
                cmd.append(f"R={params['regione']}")
            if params.get("gestione"):
                cmd.append(f"GESTIONE={params['gestione']}")
            if params.get("skip_analysis"):
                cmd.append("SKIP_ANALYSIS=1")
            
            if params.get("skip_download"):
                cmd.append("SKIP_DOWNLOAD=1")
                
            # Logic: Skip Activity unchecked -> WITH_ACTIVITY=1
            if not params.get("skip_activity"):
                cmd.append("WITH_ACTIVITY=1")
                
            # Sampling params
            if params.get("target_total"):
                cmd.append(f"TARGET_TOTAL={params['target_total']}")
            if params.get("target_step"):
                cmd.append(f"TARGET_STEP={params['target_step']}")
            if params.get("strato_step"):
                cmd.append(f"STRATO_STEP={params['strato_step']}")
            if params.get("yield_global"):
                cmd.append(f"YIELD_GLOBAL={params['yield_global']}")
            if params.get("max_cycles"):
                cmd.append(f"MAX_CYCLES={params['max_cycles']}")
            if params.get("seed"):
                cmd.append(f"SEED={params['seed']}")
            # Shared config
            if params.get("ollama_url"):
                cmd.append(f"OLLAMA_URL={params['ollama_url']}")
            # Validation config
            if params.get("validation_provider"):
                cmd.append(f"VALIDATION_PROVIDER={params['validation_provider']}")
            if params.get("validation_model"):
                cmd.append(f"VALIDATION_MODEL={params['validation_model']}")
            # Per-role provider+model
            if params.get("analyst_provider"):
                cmd.append(f"PROVIDER_ANALYST={params['analyst_provider']}")
            if params.get("analyst_model"):
                cmd.append(f"ANALYST_WORKFLOW={params['analyst_model']}")
            if params.get("reviewer_provider"):
                cmd.append(f"PROVIDER_REVIEWER={params['reviewer_provider']}")
            if params.get("reviewer_model"):
                cmd.append(f"REVIEWER_WORKFLOW={params['reviewer_model']}")
            if params.get("refiner_provider"):
                cmd.append(f"PROVIDER_REFINER={params['refiner_provider']}")
            if params.get("refiner_model"):
                cmd.append(f"REFINER_WORKFLOW={params['refiner_model']}")
            if params.get("synthesizer_provider"):
                cmd.append(f"PROVIDER_SYNTHESIZER={params['synthesizer_provider']}")
            if params.get("synthesizer_model"):
                cmd.append(f"SYNTHESIZER_WORKFLOW={params['synthesizer_model']}")
            if params.get("activity_provider"):
                cmd.append(f"PROVIDER_ACTIVITY={params['activity_provider']}")
            if params.get("activity_model"):
                cmd.append(f"ACTIVITY_WORKFLOW={params['activity_model']}")
        
        log_file = open(SCRIPT_DIR / "logs" / "workflow.log", "a")

        process = subprocess.Popen(
            cmd,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            cwd=SCRIPT_DIR,
            start_new_session=True  # Detach from parent
        )

        # Save PID and PGID for proper process group termination
        try:
            pgid = os.getpgid(process.pid)
        except OSError:
            pgid = process.pid
        PID_FILE.write_text(f"{process.pid}:{pgid}")
        logger.info(f"Started strata-cycle with cmd: {' '.join(cmd)}")
        return True
    except Exception as e:
        logger.error(f"Failed to start strata-cycle: {e}")
        return False

def stop_workflow_process():
    """Stop the running workflow process and all its children."""
    result = get_running_pid()
    if not result:
        return False

    pid, pgid = result

    try:
        # Kill the entire process group to terminate make + python children
        os.killpg(pgid, signal.SIGTERM)
        logger.info(f"Sent SIGTERM to process group {pgid} (main pid: {pid})")
        # The workflow handles SIGTERM to save state.
        return True
    except ProcessLookupError:
        PID_FILE.unlink(missing_ok=True)
        return False
    except PermissionError:
        # Fallback: try killing just the main process
        try:
            os.kill(pid, signal.SIGTERM)
            logger.info(f"Fallback: sent SIGTERM to process {pid}")
            return True
        except ProcessLookupError:
            PID_FILE.unlink(missing_ok=True)
            return False
    except Exception as e:
        logger.error(f"Error stopping process group {pgid}: {e}")
        return False
