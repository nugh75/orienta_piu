from flask import Flask, render_template, request, Response, jsonify
import subprocess
import os
import signal
import threading
import uuid
import time
import json
import requests

app = Flask(__name__)

# Cache for models
MODELS_CACHE = {
    "data": None,
    "timestamp": 0
}

@app.route('/api/models', methods=['GET'])
def get_models():
    # Cache for 1 hour
    if MODELS_CACHE["data"] and (time.time() - MODELS_CACHE["timestamp"] < 3600):
        return jsonify(MODELS_CACHE["data"])

    try:
        # Fetch from OpenRouter
        response = requests.get("https://openrouter.ai/api/v1/models")
        if response.status_code == 200:
            data = response.json()
            models = data.get("data", [])
            
            # Process and sort models
            processed_models = []
            for m in models:
                processed_models.append({
                    "id": m["id"],
                    "name": m["name"],
                    "context_length": m.get("context_length", 0),
                    "pricing": m.get("pricing", {}),
                    "is_free": "free" in m["id"] or float(m.get("pricing", {}).get("prompt", 0)) == 0
                })
            
            # Sort: Free first, then by name
            processed_models.sort(key=lambda x: (not x["is_free"], x["name"]))
            
            MODELS_CACHE["data"] = processed_models
            MODELS_CACHE["timestamp"] = time.time()
            return jsonify(processed_models)
        else:
            return jsonify({"error": "Failed to fetch from OpenRouter"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Global state: Dictionary of processes
# Structure: { "uuid": { "process": Popen, "command": str, "logs": [], "status": str, "condition": Condition, "timestamp": float } }
processes = {}
archived_processes = {}
processes_lock = threading.Lock()
PROCESS_FILE = "data/processes.json"
ARCHIVE_FILE = "data/processes_archive.json"

def save_processes():
    """Save processes to disk."""
    serializable = {}
    with processes_lock:
        for pid, pdata in processes.items():
            serializable[pid] = {
                "command": pdata["command"],
                "logs": pdata["logs"],
                "status": pdata["status"],
                "timestamp": pdata["timestamp"]
            }
    
    try:
        os.makedirs(os.path.dirname(PROCESS_FILE), exist_ok=True)
        with open(PROCESS_FILE, 'w') as f:
            json.dump(serializable, f, indent=2)
    except Exception as e:
        print(f"Failed to save processes: {e}")

def save_archive():
    """Save archived processes to disk."""
    try:
        os.makedirs(os.path.dirname(ARCHIVE_FILE), exist_ok=True)
        with open(ARCHIVE_FILE, 'w') as f:
            json.dump(archived_processes, f, indent=2)
    except Exception as e:
        print(f"Failed to save archive: {e}")

def load_archive():
    """Load archived processes from disk."""
    global archived_processes
    if not os.path.exists(ARCHIVE_FILE):
        return
    try:
        with open(ARCHIVE_FILE, 'r') as f:
            archived_processes = json.load(f)
    except Exception as e:
        print(f"Failed to load archive: {e}")

def load_processes():
    """Load processes from disk."""
    global processes
    if not os.path.exists(PROCESS_FILE):
        return

    try:
        with open(PROCESS_FILE, 'r') as f:
            data = json.load(f)
            
        with processes_lock:
            for pid, pdata in data.items():
                # If it was running, mark as interrupted since we lost the handle
                status = pdata["status"]
                if status in ["running", "starting"]:
                    status = "interrupted"
                    pdata["logs"].append("\n⚠️ Process interrupted by server restart")
                
                processes[pid] = {
                    "process": None,
                    "command": pdata["command"],
                    "logs": pdata["logs"],
                    "status": status,
                    "condition": threading.Condition(),
                    "timestamp": pdata["timestamp"]
                }
    except Exception as e:
        print(f"Failed to load processes: {e}")

# Load on startup
load_processes()
load_archive()

def run_command_thread(cmd_list, process_id):
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    
    with processes_lock:
        proc_data = processes[process_id]
    
    condition = proc_data["condition"]
    
    try:
        process = subprocess.Popen(
            cmd_list,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
            preexec_fn=os.setsid
        )
        
        with processes_lock:
            processes[process_id]["process"] = process
            processes[process_id]["status"] = "running"
        
        for line in process.stdout:
            with condition:
                proc_data["logs"].append(line.strip())
                condition.notify_all()
            
        process.wait()
        rc = process.returncode
        
        with condition:
            proc_data["logs"].append(f"\n✅ Process finished with code {rc}")
            condition.notify_all()
            
        with processes_lock:
            processes[process_id]["status"] = "completed" if rc == 0 else "failed"
        
        save_processes()
        
    except Exception as e:
        with condition:
            proc_data["logs"].append(f"\n❌ Error: {str(e)}")
            condition.notify_all()
        with processes_lock:
            processes[process_id]["status"] = "error"
        save_processes()
            
    finally:
        with condition:
            proc_data["logs"].append("DONE")
            condition.notify_all()

@app.route('/config', methods=['GET'])
def get_config():
    try:
        with open('config/pipeline_config.json', 'r') as f:
            config = json.load(f)
        return jsonify(config)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/config', methods=['POST'])
def update_config():
    try:
        new_config = request.json
        with open('config/pipeline_config.json', 'w') as f:
            json.dump(new_config, f, indent=2)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/processes')
def list_processes():
    with processes_lock:
        # Return list of processes (without logs to save bandwidth)
        plist = []
        for pid, pdata in processes.items():
            plist.append({
                "id": pid,
                "command": pdata["command"],
                "status": pdata["status"],
                "timestamp": pdata["timestamp"]
            })
        # Sort by timestamp desc
        plist.sort(key=lambda x: x["timestamp"], reverse=True)
        return jsonify(plist)

@app.route('/run', methods=['POST'])
def run_command():
    data = request.json
    cmd_id = data.get('id')
    params = data.get('params', {})
    
    # Command mapping
    commands = {
        "btn_sample": ["make", "download-sample"],
        "btn_strato": ["make", "download-strato", f"N={params.get('n_schools', 5)}"],
        "btn_statali": ["make", "download-statali"],
        "btn_paritarie": ["make", "download-paritarie"],
        "btn_regione": ["make", "download-regione", f"R={params.get('region', 'LAZIO')}"],
        "btn_metro": ["make", "download-metro"],
        "btn_non_metro": ["make", "download-non-metro"],
        "btn_run": ["make", "run"],
        "btn_review": ["make", "review-scores", f"MODEL={params.get('model', 'meta-llama/llama-3.3-70b-instruct:free')}"],
        "btn_review_slow": ["make", "review-slow", f"MODEL={params.get('model', 'meta-llama/llama-3.3-70b-instruct:free')}"],
        "btn_review_gemini": ["make", "review-gemini", f"MODEL={params.get('model', 'google/gemini-2.0-flash-exp:free')}"],
        "btn_review_scores_gemini": ["make", "review-scores-gemini", f"MODEL={params.get('model', 'google/gemini-2.0-flash-exp:free')}"],
        "btn_review_non_ptof": ["make", "review-non-ptof"],
        "btn_backfill": ["make", "backfill"],
        "btn_csv": ["make", "csv"],
        "btn_dash": ["make", "dashboard"],
        "btn_clean": ["make", "clean"]
    }
    
    cmd_list = commands.get(cmd_id)
    if not cmd_list:
        return jsonify({"status": "error", "message": "Invalid command"}), 400
        
    process_id = str(uuid.uuid4())
    
    with processes_lock:
        processes[process_id] = {
            "process": None, # Will be set in thread
            "command": " ".join(cmd_list),
            "logs": [],
            "status": "starting",
            "condition": threading.Condition(),
            "timestamp": time.time()
        }
        
    save_processes()
        
    thread = threading.Thread(target=run_command_thread, args=(cmd_list, process_id))
    thread.daemon = True
    thread.start()
    
    return jsonify({"status": "started", "id": process_id, "command": " ".join(cmd_list)})

@app.route('/stop/<process_id>', methods=['POST'])
def stop_command(process_id):
    with processes_lock:
        proc_data = processes.get(process_id)
        
    if proc_data and proc_data["process"] and proc_data["status"] == "running":
        try:
            os.killpg(os.getpgid(proc_data["process"].pid), signal.SIGTERM)
            return jsonify({"status": "stopped"})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    return jsonify({"status": "no_process_or_not_running"})

@app.route('/stream/<process_id>')
def stream(process_id):
    with processes_lock:
        if process_id not in processes:
            return "Process not found", 404
        proc_data = processes[process_id]
        condition = proc_data["condition"]
        
    def generate():
        curr_idx = 0
        while True:
            with condition:
                # Wait for new logs
                while curr_idx >= len(proc_data["logs"]):
                    if proc_data["logs"] and proc_data["logs"][-1] == "DONE":
                         # Send DONE marker and exit
                        yield f"data: [DONE]\n\n"
                        return
                    condition.wait()
                
                # Send all new lines
                while curr_idx < len(proc_data["logs"]):
                    msg = proc_data["logs"][curr_idx]
                    curr_idx += 1
                    if msg == "DONE":
                        yield f"data: [DONE]\n\n"
                        return
                    yield f"data: {msg}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')

@app.route('/delete/<process_id>', methods=['POST'])
def delete_process(process_id):
    """Archive a process (move from active to archive)."""
    with processes_lock:
        if process_id in processes:
            # Only archive if not running
            if processes[process_id]["status"] in ["running", "starting"]:
                 return jsonify({"status": "error", "message": "Cannot archive running process"}), 400
            
            # Move to archive
            pdata = processes[process_id]
            archived_processes[process_id] = {
                "command": pdata["command"],
                "logs": pdata["logs"],
                "status": pdata["status"],
                "timestamp": pdata["timestamp"],
                "archived_at": time.time()
            }
            del processes[process_id]
            save_processes()
            save_archive()
            return jsonify({"status": "archived"})
    return jsonify({"status": "not_found"}), 404

@app.route('/archive')
def list_archive():
    """List all archived processes."""
    plist = []
    for pid, pdata in archived_processes.items():
        plist.append({
            "id": pid,
            "command": pdata["command"],
            "status": pdata["status"],
            "timestamp": pdata["timestamp"],
            "archived_at": pdata.get("archived_at", pdata["timestamp"])
        })
    # Sort by archived_at desc
    plist.sort(key=lambda x: x["archived_at"], reverse=True)
    return jsonify(plist)

@app.route('/archive/<process_id>')
def get_archived_process(process_id):
    """Get details and logs of an archived process."""
    if process_id in archived_processes:
        return jsonify(archived_processes[process_id])
    return jsonify({"status": "not_found"}), 404

@app.route('/archive/<process_id>', methods=['DELETE'])
def delete_archived_process(process_id):
    """Permanently delete an archived process."""
    if process_id in archived_processes:
        del archived_processes[process_id]
        save_archive()
        return jsonify({"status": "deleted"})
    return jsonify({"status": "not_found"}), 404

@app.route('/restore/<process_id>', methods=['POST'])
def restore_process(process_id):
    """Restore a process from archive to active list."""
    if process_id in archived_processes:
        pdata = archived_processes[process_id]
        with processes_lock:
            processes[process_id] = {
                "process": None,
                "command": pdata["command"],
                "logs": pdata["logs"],
                "status": pdata["status"],
                "condition": threading.Condition(),
                "timestamp": pdata["timestamp"]
            }
        del archived_processes[process_id]
        save_processes()
        save_archive()
        return jsonify({"status": "restored"})
    return jsonify({"status": "not_found"}), 404

if __name__ == '__main__':
    print("🚀 LIste Web Launcher avviato su http://127.0.0.1:5001")
    app.run(debug=True, port=5001)
