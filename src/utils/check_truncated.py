import os
from pathlib import Path

ANALYSIS_DIR = Path("analysis_results")

def is_truncated(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return True # Empty file is "truncated"
            
            # Check if it ends with a code block closure if it started with one
            if content.startswith("```") and not content.endswith("```"):
                return True
            
            # If it doesn't end with a code block, check for punctuation
            # Many files end with a period, but some might end with a newline or other char.
            # The truncated ones we saw ended in the middle of a sentence.
            last_char = content[-1]
            if last_char not in ['.', '!', '?', '>', '`', '\n']:
                # It might be truncated.
                # Let's look at the last 50 chars to be sure.
                # print(f"Checking {file_path.name}: ...{content[-50:]}")
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

    if truncated_files:
        print(f"Found {len(truncated_files)} potentially truncated files:")
        for tf in truncated_files:
            print(f"- {tf.name}")
            # Print the last line to verify
            with open(tf, 'r') as f:
                lines = f.readlines()
                if lines:
                    print(f"  Last line: {lines[-1].strip()}")
    else:
        print("No truncated files found.")

if __name__ == "__main__":
    main()
