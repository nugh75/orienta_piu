import os
import sys
import psutil
import subprocess
import time
import argparse
from pathlib import Path

def kill_process_on_port(port):
    """Find and kill process listening on specific port."""
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            for conn in proc.net_connections():
                if conn.laddr.port == port:
                    print(f"⚠️ Port {port} is occupied by PID {proc.info['pid']} ({proc.info['name']}). Killing...")
                    proc.kill()
                    proc.wait()
                    print(f"✅ Process killed.")
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False

def main():
    parser = argparse.ArgumentParser(description="Force start Flask App")
    parser.add_argument("--port", type=int, default=5000, help="Port (default: 5000)")
    parser.add_argument("--host", default="0.0.0.0", help="Host (default: 0.0.0.0)")
    args = parser.parse_args()

    # 1. Kill invalidators
    kill_process_on_port(args.port)
    
    # 2. Wait a moment
    time.sleep(1)

    # 3. Start App
    cmd = [
        sys.executable, "-m", "src.taskrunner.web", 
        "--host", args.host, 
        "--port", str(args.port)
    ]
    
    print(f"🚀 Starting Task Runner on {args.host}:{args.port}...")
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n🛑 Stopped by user.")

if __name__ == "__main__":
    # Add project root to path
    project_root = Path(__file__).resolve().parent.parent
    sys.path.append(str(project_root))
    main()
