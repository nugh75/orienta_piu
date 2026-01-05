
import re
import csv
from pathlib import Path
from datetime import datetime

# Configurazioni
LOG_FILE = Path("logs/activity_extractor.log")
OUTPUT_CSV = Path("data/api_costs.csv")

def parse_log_for_costs():
    """Analizza il log e estrae i costi delle chiamate API."""
    if not LOG_FILE.exists():
        print(f"File di log non trovato: {LOG_FILE}")
        return

    # Regex versioni:
    # V1: ... 💰 Usage: In (\d+), Out (\d+) | Costo: \$(\d+\.\d+) ...
    # V2: ... 💰 Usage: \[([^:]+)::([^\]]+)\] In (\d+), Out (\d+) | Costo: \$(\d+\.\d+) ...
    
    regex_v1 = r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ - INFO - 💰 Usage: In (\d+), Out (\d+) \| Costo: \$(\d+\.\d+) \(Tot: \$(\d+\.\d+)\)"
    regex_v2 = r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ - INFO - 💰 Usage: \[([^:]+)::([^\]]+)\] In (\d+), Out (\d+) \| Costo: \$(\d+\.\d+) \(Tot: \$(\d+\.\d+)\)"
    
    costs = []
    
    print(f"Lettura log: {LOG_FILE}...")
    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            # Prova V2 (con provider/model)
            match = re.search(regex_v2, line)
            if match:
                timestamp, provider, model, prompt_tokens, completion_tokens, cost, cumulative_cost = match.groups()
                costs.append({
                    "Timestamp": timestamp,
                    "Provider": provider,
                    "Model": model,
                    "Prompt Tokens": prompt_tokens,
                    "Completion Tokens": completion_tokens,
                    "Cost ($)": cost,
                    "Cumulative Cost ($)": cumulative_cost
                })
                continue

            # Fallback V1 (vecchi log senza provider esplicito)
            match = re.search(regex_v1, line)
            if match:
                timestamp, prompt_tokens, completion_tokens, cost, cumulative_cost = match.groups()
                costs.append({
                    "Timestamp": timestamp,
                    "Provider": "openrouter",  # Default per vecchi log
                    "Model": "google/gemini-2.5-flash-lite", 
                    "Prompt Tokens": prompt_tokens,
                    "Completion Tokens": completion_tokens,
                    "Cost ($)": cost,
                    "Cumulative Cost ($)": cumulative_cost
                })

    if not costs:
        print("Nessun dato sui costi trovato nel log.")
        return

    # Scrivi CSV
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fields = ["Timestamp", "Provider", "Model", "Prompt Tokens", "Completion Tokens", "Cost ($)", "Cumulative Cost ($)"]
    
    print(f"Scrittura report: {OUTPUT_CSV} ({len(costs)} righe)...")
    with open(OUTPUT_CSV, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(costs)
        
    # Calcola totali riepilogativi per modello
    from collections import defaultdict
    summary = defaultdict(lambda: {"input": 0, "output": 0, "cost": 0.0, "count": 0})

    for c in costs:
        key = f"{c['Provider']}::{c['Model']}"
        summary[key]["input"] += int(c["Prompt Tokens"])
        summary[key]["output"] += int(c["Completion Tokens"])
        summary[key]["cost"] += float(c["Cost ($)"])
        summary[key]["count"] += 1
        
    total_input = sum(int(c["Prompt Tokens"]) for c in costs)
    total_output = sum(int(c["Completion Tokens"]) for c in costs)

    print("\n------------------------------------------------")
    print("RIEPILOGO COSTI API (Dettaglio Modelli)")
    print("------------------------------------------------")
    
    total_global_usd = 0.0
    
    for key, stats in summary.items():
        print(f"🔹 {key}")
        print(f"   Chiamate: {stats['count']}")
        print(f"   Tokens: In {stats['input']:,} | Out {stats['output']:,}")
        print(f"   Costo: ${stats['cost']:.4f}")
        total_global_usd += stats['cost']
        print("-")

    print(f"💵 COSTO TOTALE GLOBALE: ${total_global_usd:.4f}")
    print("------------------------------------------------")

    # Genera Report Markdown
    OUTPUT_MD = Path("data/api_costs.md")
    print(f"Generazione report MD: {OUTPUT_MD}...")
    
    with open(OUTPUT_MD, 'w', encoding='utf-8') as f:
        f.write("# 💰 Report Costi API LLM\n\n")
        f.write(f"**Ultimo aggiornamento:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## 📊 Riepilogo per Modello\n\n")
        f.write("| Provider | Modello | Chiamate | Token Input | Token Output | Costo ($) |\n")
        f.write("|---|---|---|---|---|---|\n")
        
        for key, stats in summary.items():
            provider, model = key.split("::", 1)
            f.write(f"| {provider} | {model} | {stats['count']} | {stats['input']:,} | {stats['output']:,} | ${stats['cost']:.4f} |\n")
            
        f.write(f"| **TOTALE** | | **{len(costs)}** | **{total_input:,}** | **{total_output:,}** | **${total_global_usd:.4f}** |\n\n")
        
        f.write("## 📝 Dettaglio Ultime 50 Chiamate\n\n")
        f.write("| Timestamp | Modello | In | Out | $\n")
        f.write("|---|---|---|---|---|\n")
        
        # Ultime 50 chiamate
        for c in list(reversed(costs))[:50]:
             f.write(f"| {c['Timestamp']} | {c['Model']} | {c['Prompt Tokens']} | {c['Completion Tokens']} | ${c['Cost ($)']} |\n")

if __name__ == "__main__":
    parse_log_for_costs()
