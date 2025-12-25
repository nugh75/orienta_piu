import os
import subprocess
from pathlib import Path

ANALYSIS_DIR = Path("analysis_results")
SCRIPT_PATH = Path("src/processing/ollama_report_reviewer.py")

def is_truncated(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return True
            
            if content.startswith("```") and not content.endswith("```"):
                return True
            
            last_char = content[-1]
            if last_char not in ['.', '!', '?', '>', '`', '\n']:
                return True
            
            return False
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False

def main():
    truncated_files = []
    for file_path in ANALYSIS_DIR.glob("*_PTOF_analysis.md"):
        if is_truncated(file_path):
            truncated_files.append(file_path)

    if not truncated_files:
        print("No truncated files found.")
        return

    print(f"Found {len(truncated_files)} truncated files. Starting regeneration...")

    for i, file_path in enumerate(truncated_files, 1):
        school_code = file_path.name.split('_')[0]
        print(f"[{i}/{len(truncated_files)}] Regenerating report for {school_code}...")
        
        # Run the reviewer script targeting this school
        # We use subprocess to run it as a separate process
        cmd = ["python3", str(SCRIPT_PATH), "--target", school_code]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Successfully regenerated {school_code}")
            else:
                print(f"❌ Failed to regenerate {school_code}")
                print(f"Error output:\n{result.stderr}")
        except Exception as e:
            print(f"❌ Exception running script for {school_code}: {e}")

if __name__ == "__main__":
    main()
