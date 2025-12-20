import os
import logging

# Path relative to the execution root (assuming run from root)
PROMPTS_FILE = "config/prompts.md"

def load_prompts():
    """Parses config/prompts.md into a dictionary."""
    if not os.path.exists(PROMPTS_FILE):
        logging.error(f"Prompts file {PROMPTS_FILE} not found!")
        return {}
        
    prompts = {}
    current_section = None
    current_text = []
    
    with open(PROMPTS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith("## "):
                if current_section:
                    prompts[current_section] = "\n".join(current_text).strip()
                current_section = line.replace("## ", "").strip()
                current_text = []
            elif current_section:
                current_text.append(line)
                
    if current_section:
        prompts[current_section] = "\n".join(current_text).strip()
        
    return prompts
