import json
import os

NOTEBOOK_PATH = "docs/CLI_Examples.ipynb"

def update_notebook():
    with open(NOTEBOOK_PATH, 'r') as f:
        nb = json.load(f)
    
    new_cells = []
    skip_nextor = False
    
    for i, cell in enumerate(nb['cells']):
        if skip_nextor:
            skip_nextor = False
            continue
            
        # Check if this is the target markdown cell
        source_text = "".join(cell.get('source', []))
        if "### Background Fixer - CLI con Logging" in source_text:
            print("Found target cell, performing replacement...")
            
            # Create new cells
            
            # 1. New Markdown
            cell1 = {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "### 🔍 Rilevamento Incongruenze\n",
                    "\n",
                    "La procedura è basata sul **rilevamento** delle anomalie.\n",
                    "1. **Rilevamento**: `run_reviewer.py` scansiona i file e crea un report anomalie (`review_flags.json`)."
                ]
            }
            
            # 2. Reviewer Code
            cell2 = {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "%%bash\n",
                    "# FASE 1: Rilevamento Anomalie\n",
                    "cd /Users/danieledragoni/git/LIste\n",
                    "source .venv/bin/activate\n",
                    "\n",
                    "echo \"🔍 Avvio Reviewer...\"\n",
                    "python run_reviewer.py\n",
                    "\n",
                    "echo \"✅ Rilevamento completato. Controlla logs/background_debug.log\""
                ]
            }
            
            new_cells.append(cell1)
            new_cells.append(cell2)
            
            # We skip the next cell (which is the old code cell for background fixer)
            skip_nextor = True
            
        else:
            new_cells.append(cell)
            
    nb['cells'] = new_cells
    
    with open(NOTEBOOK_PATH, 'w') as f:
        json.dump(nb, f, indent=4)
    print("Notebook updated successfully.")

if __name__ == "__main__":
    update_notebook()
