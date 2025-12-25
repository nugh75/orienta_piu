import os
import subprocess
import json
from pathlib import Path

ANALYSIS_DIR = Path("analysis_results")

def is_truncated(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return True
            if content.startswith("```") and not content.endswith("```"):
                return True
            last_char = content[-1]
            if last_char not in ['.', '!', '?', '>', '`', '\n', '}', ']']:
                return True
            return False
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False

def get_file_history(filepath):
    """Get list of commit hashes that modified the file."""
    try:
        result = subprocess.run(
            ['git', 'log', '--format=%H', '--', filepath],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip().splitlines()
    except subprocess.CalledProcessError as e:
        print(f"Error getting history for {filepath}: {e}")
        return []

def get_file_content_at_commit(filepath, commit_hash):
    """Retrieve file content from a specific commit."""
    try:
        result = subprocess.run(
            ['git', 'show', f"{commit_hash}:{filepath}"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError:
        return None

def recover_file(filepath):
    print(f"Attempting to recover {filepath}...")
    
    commits = get_file_history(filepath)
    if not commits:
        print(f"  No history found for {filepath}")
        return False

    # Iterate through commits starting from the second one (index 1)
    # assuming index 0 is the current bad state.
    # If the file hasn't been committed in its bad state yet, index 0 might be the last good one?
    # But we are seeing bad content on disk.
    
    for i, commit in enumerate(commits):
        # Skip the first one if it's the one that introduced the truncation?
        # Actually, let's just check them all. If the current HEAD has bad content, 
        # git show HEAD:file will show bad content.
        
        # print(f"  Checking commit {commit[:8]}...")
        content = get_file_content_at_commit(filepath, commit)
        
        if not content:
            continue

        try:
            # Try to parse as JSON
            data = json.loads(content)
            
            if isinstance(data, dict) and "report" in data:
                report_content = data["report"]
                # Write back to file
                with open(filepath, 'w', encoding='utf-8') as f:
                    if isinstance(report_content, str):
                        f.write(report_content)
                    else:
                        f.write(json.dumps(report_content, indent=2, ensure_ascii=False))
                print(f"  Successfully recovered {filepath} from commit {commit[:8]} (JSON)")
                return True
            elif isinstance(data, str):
                 # If it's just a string, let's check if it looks like markdown
                 if len(data) > 100: 
                     with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(data)
                     print(f"  Successfully recovered {filepath} from commit {commit[:8]} (JSON string)")
                     return True
        except json.JSONDecodeError:
            # Not JSON, check if it's valid Markdown
            if not content.strip().endswith(('.', '!', '?', '"', '>', '}', ']')):
                 # print(f"    Commit {commit[:8]} content also looks truncated.")
                 pass
            else:
                 # print(f"    Commit {commit[:8]} looks like valid Markdown. Restoring...")
                 with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                 print(f"  Successfully restored Markdown from commit {commit[:8]}")
                 return True
    
    print(f"  Could not find a valid version in history for {filepath}")
    return False

def main():
    files = sorted(list(ANALYSIS_DIR.glob("*_PTOF_analysis.md")))
    truncated_files = []
    
    for file_path in files:
        if is_truncated(file_path):
            print(f"Found truncated: {file_path.name}")
            truncated_files.append(str(file_path))
            
    print(f"\nFound {len(truncated_files)} truncated files. Starting recovery...\n")
    
    recovered_count = 0
    for filepath in truncated_files:
        if recover_file(filepath):
            recovered_count += 1
            
    print(f"\nRecovery complete. Recovered {recovered_count}/{len(truncated_files)} files.")

if __name__ == "__main__":
    main()
