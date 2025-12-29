#!/usr/bin/env python3
import os
import time
import sys
import subprocess
import argparse
from datetime import datetime

# Configuration
LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')

def get_log_files():
    """List all files in the logs directory, sorted by modification time (newest first)."""
    if not os.path.exists(LOGS_DIR):
        print(f"Error: Logs directory not found at {LOGS_DIR}")
        return []

    files = []
    for f in os.listdir(LOGS_DIR):
        full_path = os.path.join(LOGS_DIR, f)
        if os.path.isfile(full_path) and not f.startswith('.'):
            stats = os.stat(full_path)
            files.append({
                'name': f,
                'path': full_path,
                'size': stats.st_size,
                'mtime': stats.st_mtime
            })
    
    # Sort by modification time, descending
    files.sort(key=lambda x: x['mtime'], reverse=True)
    return files

def format_size(size_bytes):
    """Format size in bytes to human readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:3.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"

def print_menu(files):
    """Print the list of log files."""
    print(f"\n{'='*60}")
    print(f" LOG VIEWER - {LOGS_DIR}")
    print(f"{'='*60}")
    print(f"{'ID':<4} | {'Filename':<35} | {'Size':<10} | {'Last Modified'}")
    print(f"{'-'*60}")
    
    for idx, f in enumerate(files):
        mod_time = datetime.fromtimestamp(f['mtime']).strftime('%Y-%m-%d %H:%M:%S')
        print(f"{idx+1:<4} | {f['name']:<35} | {format_size(f['size']):<10} | {mod_time}")
    print(f"{'='*60}")

def view_log(file_path, follow=False, lines=100):
    """View log file using tail."""
    try:
        if follow:
            print(f"Following {os.path.basename(file_path)}... (Press Ctrl+C to stop)")
            subprocess.run(['tail', '-f', '-n', str(lines), file_path])
        else:
            print(f"Viewing last {lines} lines of {os.path.basename(file_path)}...")
            subprocess.run(['tail', '-n', str(lines), file_path])
            input("\nPress Enter to return to menu...")
    except KeyboardInterrupt:
        print("\nStopped.")
    except Exception as e:
        print(f"Error: {e}")
        input("Press Enter to continue...")

def main():
    parser = argparse.ArgumentParser(description="CLI tool to view logs.")
    parser.add_argument('--lines', '-n', type=int, default=50, help='Number of lines to show (default: 50)')
    args = parser.parse_args()

    while True:
        # Clear screen for better UX (optional, maybe distracting if running in workflow)
        # os.system('cls' if os.name == 'nt' else 'clear') 
        
        files = get_log_files()
        if not files:
            print("No log files found.")
            break

        print_menu(files)
        print("\nOptions:")
        print("  <ID>        : View last N lines (static)")
        print("  <ID> -f     : Follow file (tail -f)")
        print("  q           : Quit")
        
        choice = input("\nEnter choice: ").strip().lower()
        
        if choice == 'q':
            break
        
        if not choice:
            continue

        follow = False
        file_idx = -1
        
        try:
            if choice.endswith(' -f'):
                follow = True
                choice = choice.replace(' -f', '').strip()
            
            file_idx = int(choice) - 1
            
            if 0 <= file_idx < len(files):
                view_log(files[file_idx]['path'], follow=follow, lines=args.lines)
            else:
                print("Invalid ID.")
                time.sleep(1)
        except ValueError:
            print("Invalid input.")
            time.sleep(1)

if __name__ == "__main__":
    main()
