import sys
import os
import time
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from scripts.process_manager import start_workflow_process, stop_workflow_process, get_running_pid, is_process_running

def test_lifecycle():
    print("Testing Workflow Lifecycle...")
    
    # Ensure clean state
    if get_running_pid():
        print("Workflow already running, stopping first...")
        stop_workflow_process()
        time.sleep(2)
        
    # 1. Start
    print("1. Starting workflow...")
    if start_workflow_process():
        print("   ✅ Start successful.")
    else:
        print("   ❌ Start failed.")
        return
        
    time.sleep(2)
    
    # 2. Check PID
    pid = get_running_pid()
    if pid and is_process_running(pid):
        print(f"   ✅ Process running with PID: {pid}")
    else:
        print("   ❌ Process not found or PID file missing.")
        return

    # 3. Stop
    print("3. Stopping workflow...")
    if stop_workflow_process():
        print("   ✅ Stop signal sent.")
    else:
        print("   ❌ Stop failed.")
        return
        
    time.sleep(2)
    
    # 4. Verify Stop
    if not is_process_running(pid):
        print("   ✅ Process stopped successfully.")
    else:
        print("   ❌ Process still running.")

if __name__ == "__main__":
    test_lifecycle()
