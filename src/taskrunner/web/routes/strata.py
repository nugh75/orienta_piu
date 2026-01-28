from flask import Blueprint, render_template, jsonify, request, send_file
import pandas as pd
import json
import os
import sys
import re
import requests
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
PROJECT_ROOT = Path(__file__).parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.process_manager import start_workflow_process, stop_workflow_process, get_running_pid

strata_bp = Blueprint('strata', __name__)

BASE_DIR = PROJECT_ROOT
INBOX_DIR = BASE_DIR / "ptof_inbox"
DISCARDED_DIR = BASE_DIR / "ptof_discarded"
LOG_FILE = BASE_DIR / "logs" / "workflow.log"
PID_FILE = BASE_DIR / "logs" / "workflow.pid"

# Ollama config from .env
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://192.168.129.14:11434")

def load_registry():
    """Load analysis registry safely."""
    registry_path = BASE_DIR / "data" / "analysis_registry.json"
    if not registry_path.exists():
        return {"analyzed_files": {}}
    try:
        with open(registry_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"analyzed_files": {}}

def parse_log_for_current_step(log_content):
    """Extract the current workflow step from log content."""
    step_patterns = [
        r"\[PHASE\]\s*(.+)", # New explicit phase logging
        r"\[workflow\].*STEP\s*(-?\d+):\s*(.+)",
        r"STEP\s*(-?\d+):\s*(.+)",
        r"🔍\s*STEP\s*(-?\d+):\s*(.+)",
        r"📝\s*STEP\s*(-?\d+):\s*(.+)",
        r"🤖\s*STEP\s*(-?\d+):\s*(.+)",
    ]
    
    lines = log_content.strip().split('\n')
    for line in reversed(lines):
        for pattern in step_patterns:
            match = re.search(pattern, line)
            if match:
                if "PHASE" in pattern:
                     return f"Phase: {match.group(1).strip()}"
                return f"Step {match.group(1)}: {match.group(2).strip()[:50]}"
    return "Initializing..."

def parse_skipped_phases_from_logs(log_content):
    """Extract skipped phases from log content."""
    skipped = {
        "download": False,
        "analysis": False,
        "extraction": False
    }
    
    patterns = {
        "download": r"\[CONFIG\] Skip Download: True",
        "analysis": r"\[CONFIG\] Skip Analysis: True",
        "extraction": r"\[CONFIG\] Skip Activity: True"
    }
    
    for phase, pattern in patterns.items():
        if re.search(pattern, log_content):
            skipped[phase] = True
            
    return skipped

def count_errors_in_log(log_content):
    """Count error indicators in log content."""
    error_patterns = [r'❌', r'\bERROR\b', r'\bFailed\b', r'\bException\b']
    count = 0
    for pattern in error_patterns:
        count += len(re.findall(pattern, log_content, re.IGNORECASE))
    return count

def get_uptime():
    """Get process uptime from PID file modification time."""
    if not PID_FILE.exists():
        return None
    try:
        mtime = PID_FILE.stat().st_mtime
        start_time = datetime.fromtimestamp(mtime)
        delta = datetime.now() - start_time
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    except:
        return None

@strata_bp.route('/strata')
def index():
    """Render the Strata Cycle dashboard."""
    return render_template('strata.html')

@strata_bp.route('/strata/logs/download')
def download_logs():
    """Download the full workflow log."""
    if LOG_FILE.exists():
        return send_file(LOG_FILE, as_attachment=True, download_name="workflow_full.log")
    return jsonify({"error": "Log file not found"}), 404

@strata_bp.route('/strata/status')
def status():
    """Get real-time status and metrics."""
    pid_result = get_running_pid()
    # get_running_pid now returns (pid, pgid) tuple or None
    pid = pid_result[0] if pid_result else None
    running = pid is not None

    # Fallback: If PID check fails, check if log file was modified recently
    # This handles the case where `make` exits but the Python script continues
    if not running and LOG_FILE.exists():
        try:
            log_mtime = LOG_FILE.stat().st_mtime
            age_seconds = (datetime.now() - datetime.fromtimestamp(log_mtime)).total_seconds()
            if age_seconds < 60:  # Log updated in last 60 seconds
                running = True
                pid = None  # We don't know the actual PID
        except:
            pass
    
    try:
        # Basic Metrics
        inbox_count = len(list(INBOX_DIR.glob("*.pdf")))

        # Fonte di verita: analysis_summary.csv (allineato a Sintesi Streamlit)
        analysis_csv_path = BASE_DIR / "data" / "analysis_summary.csv"
        processed_count = 0
        if analysis_csv_path.exists():
            try:
                with open(analysis_csv_path, "r", encoding="utf-8") as f:
                    processed_count = max(0, sum(1 for line in f if line.strip()) - 1)
            except:
                processed_count = 0

        # Registry usato solo per dettagli (recent files, narrative_count)
        registry = load_registry()
        analyzed_files = registry.get("analyzed_files", {})
            
        discarded_count = 0
        for r, d, f in os.walk(DISCARDED_DIR):
            for file in f:
                if file.endswith(".pdf"):
                    discarded_count += 1
                    
        # Cycle info from strata_cycle_state.json
        cycle_current = 0
        cycle_target = 0
        cycle_state_path = BASE_DIR / "data" / "strata_cycle_state.json"
        if cycle_state_path.exists():
            try:
                with open(cycle_state_path, "r", encoding="utf-8") as f:
                    cycle_state = json.load(f)
                cycle_current = cycle_state.get("cycle_id", 0)
                cycle_target = cycle_state.get("target_total", 0)
            except:
                pass

        # Progress calculation
        total_known = processed_count + inbox_count
        progress_pct = round((processed_count / total_known * 100), 1) if total_known > 0 else 0
        
        # Scores from CSV
        avg_iipo = "N/A"
        iipo_min = "N/A"
        iipo_max = "N/A"
        analysis_csv = BASE_DIR / "data" / "analysis_summary.csv"
        if analysis_csv.exists():
            try:
                df_analysis = pd.read_csv(analysis_csv)
                if "ptof_idpo" in df_analysis.columns:
                    avg_iipo = f"{df_analysis['ptof_idpo'].mean():.2f}"
                    iipo_min = f"{df_analysis['ptof_idpo'].min():.2f}"
                    iipo_max = f"{df_analysis['ptof_idpo'].max():.2f}"
            except:
                pass

        # Activities from CSV
        activities_count = "N/A"
        cva_csv = BASE_DIR / "data" / "attivita.csv"
        if cva_csv.exists():
            try:
                with open(cva_csv, "r", encoding="utf-8") as f: # Use text mode
                        # Count non-empty strings, minus header
                        lines = [line for line in f if line.strip()]
                        activities_count = max(0, len(lines) - 1)
            except:
                    pass
                    
        # Recent Files
        recent = []
        
        # 1. Load from main analysis registry ONLY
        if analyzed_files:
            for code, data in analyzed_files.items():
                date_val = data.get("last_review") or data.get("analyzed_at") or ""
                recent.append({
                    "code": code,
                    "name": data.get("pdf_name", "N/A"),
                    "date": date_val,
                    "reviews": len(data.get("reviews", [])),
                    "source": "registry"
                })

        # Sort by date desc
        recent.sort(key=lambda x: x.get("date") or "", reverse=True)
        recent = recent[:20] # Show top 20

        # Logs (Tail) + Current Step + Errors
        logs = ""
        current_step = "Not running"
        error_count = 0
        if LOG_FILE.exists():
            try:
                file_size = LOG_FILE.stat().st_size
                read_size = min(file_size, 200000)  # Read more (200KB) for step parsing and display
                with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
                    if file_size > read_size:
                        f.seek(file_size - read_size)
                    content = f.read()
                    
                    # Parse status from full content chunk
                    if running:
                        current_step = parse_log_for_current_step(content)
                        skipped_phases = parse_skipped_phases_from_logs(content)
                    else:
                        skipped_phases = {}
                    error_count = count_errors_in_log(content)
                    
                    # Return last 500 lines for display
                    lines = content.split('\n')
                    logs = "\n".join(lines[-500:])
            except:
                logs = "Error reading logs."

        # Uptime
        uptime = get_uptime() if running else None

        return jsonify({
            "running": running,
            "pid": pid,
            "uptime": uptime,
            "current_step": current_step,
            "skipped": skipped_phases if running else {},
            "error_count": error_count,
            "metrics": {
                "inbox": inbox_count,
                "processed": processed_count,
                "discarded": discarded_count,
                "cycle_current": cycle_current,
                "cycle_target": cycle_target,
                "avg_iipo": avg_iipo,
                "iipo_min": iipo_min,
                "iipo_max": iipo_max,
                "activities": activities_count,
                "progress_pct": progress_pct
            },
            "recent": recent,
            "logs": logs
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@strata_bp.route('/strata/start', methods=['POST'])
def start():
    data = request.json or {}
    params = {
        "max_downloads": data.get("max_downloads"),
        "grado": data.get("grado"),
        "regione": data.get("regione"),
        "gestione": data.get("gestione"),
        "skip_analysis": data.get("skip_analysis"),
        "skip_download": data.get("skip_download"),
        "skip_activity": data.get("skip_activity"),
        # Sampling options
        "target_total": data.get("target_total"),
        "target_step": data.get("target_step"),
        "strato_step": data.get("strato_step"),
        "yield_global": data.get("yield_global"),
        "max_cycles": data.get("max_cycles"),
        "seed": data.get("seed"),
        # Shared config
        "ollama_url": data.get("ollama_url"),
        # Validation config
        "validation_provider": data.get("validation_provider"),
        "validation_model": data.get("validation_model"),
        "validation_timeout": data.get("validation_timeout"),
        # Per-role provider+model
        "analyst_provider": data.get("analyst_provider"),
        "analyst_model": data.get("analyst_model"),
        "reviewer_provider": data.get("reviewer_provider"),
        "reviewer_model": data.get("reviewer_model"),
        "refiner_provider": data.get("refiner_provider"),
        "refiner_model": data.get("refiner_model"),
        "synthesizer_provider": data.get("synthesizer_provider"),
        "synthesizer_model": data.get("synthesizer_model"),
        "activity_provider": data.get("activity_provider"),
        "activity_model": data.get("activity_model"),
    }
    # Remove None values
    params = {k: v for k, v in params.items() if v}
    
    if start_workflow_process(params if params else None):
         return jsonify({"status": "started", "params": params})
    return jsonify({"error": "Failed to start"}), 400

@strata_bp.route('/strata/stop', methods=['POST'])
def stop():
    if stop_workflow_process():
         return jsonify({"status": "stopped"})
    return jsonify({"error": "Failed to stop"}), 400


@strata_bp.route('/strata/models')
def get_models():
    """Fetch available models from Ollama API."""
    models = {"ollama": [], "openrouter": [], "gemini": []}
    
    # Fetch Ollama models
    try:
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            models["ollama"] = [m["name"] for m in data.get("models", [])]
    except Exception as e:
        pass  # Ollama not available
    
    # Static list for OpenRouter and Gemini (common models)
    models["openrouter"] = [
        "google/gemini-2.5-flash",
        "google/gemini-2.5-pro",
        "anthropic/claude-3.5-sonnet",
        "openai/gpt-4o",
        "meta-llama/llama-3.3-70b-instruct",
    ]
    models["gemini"] = [
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-3-flash-preview",
        "gemini-3-pro-preview",
    ]
    
    return jsonify(models)


# --- Preset Management for Strata ---

CONFIG_PATH = BASE_DIR / "config" / "pipeline_config.json"

def load_pipeline_config():
    """Load pipeline config."""
    if not CONFIG_PATH.exists():
        return {"presets": {}, "active_preset": 0}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"presets": {}, "active_preset": 0}

def save_pipeline_config(config):
    """Save pipeline config."""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

@strata_bp.route('/strata/presets')
def get_presets():
    """Get all presets and active preset."""
    config = load_pipeline_config()
    presets = config.get("presets", {})
    active = config.get("active_preset", 0)
    
    preset_list = []
    for pid, pdata in presets.items():
        preset_list.append({
            "id": pid,
            "name": pdata.get("name", f"Preset {pid}"),
            "type": pdata.get("type", "unknown"),
            "models": {
                "analyst": pdata.get("model_analyst", ""),
                "reviewer": pdata.get("model_reviewer", ""),
                "refiner": pdata.get("model_refiner", ""),
                "synthesizer": pdata.get("model_synthesizer", "")
            }
        })
    
    return jsonify({
        "presets": preset_list,
        "active_preset": str(active)
    })

@strata_bp.route('/strata/presets/active', methods=['POST'])
def set_active_preset():
    """Set the active preset."""
    data = request.json
    if not data or "preset_id" not in data:
        return jsonify({"error": "preset_id required"}), 400
    
    config = load_pipeline_config()
    config["active_preset"] = data["preset_id"]
    save_pipeline_config(config)
    
    return jsonify({"status": "ok", "active_preset": data["preset_id"]})
