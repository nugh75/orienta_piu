
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

    # Regex versions (Legacy)
    regex_v1 = r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ - INFO - 💰 Usage: In (\d+), Out (\d+) \| Costo: \$(\d+\.\d+) \(Tot: \$(\d+\.\d+)\)"
    regex_v2 = r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ - INFO - 💰 Usage: \[([^:]+)::([^\]]+)\] In (\d+), Out (\d+) \| Costo: \$(\d+\.\d+) \(Tot: \$(\d+\.\d+)\)"
    
    costs = []
    
    # 1. Parse Legacy Log
    if LOG_FILE.exists():
        print(f"Lettura log legacy: {LOG_FILE}...")
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
                        "Context": "activity_extraction",
                        "Prompt Tokens": int(prompt_tokens),
                        "Completion Tokens": int(completion_tokens),
                        "Cost ($)": float(cost),
                        "Cumulative Cost ($)": float(cumulative_cost)
                    })
                    continue

                # Fallback V1
                match = re.search(regex_v1, line)
                if match:
                    timestamp, prompt_tokens, completion_tokens, cost, cumulative_cost = match.groups()
                    costs.append({
                        "Timestamp": timestamp,
                        "Provider": "openrouter",
                        "Model": "google/gemini-2.5-flash-lite", 
                        "Context": "activity_extraction", # Default for legacy log
                        "Prompt Tokens": int(prompt_tokens),
                        "Completion Tokens": int(completion_tokens),
                        "Cost ($)": float(cost),
                        "Cumulative Cost ($)": float(cumulative_cost)
                    })
    
    # 2. Parse New JSONL Log (Workflow)
    JSONL_LOG = Path("logs/usage_costs.jsonl")
    if JSONL_LOG.exists():
        print(f"Lettura log JSONL: {JSONL_LOG}...")
        import json
        cumulative = 0.0
        with open(JSONL_LOG, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    cost = float(entry.get('cost', 0.0))
                    
                    costs.append({
                        "Timestamp": entry['timestamp'][:19].replace('T', ' '),
                        "Provider": entry.get('provider', 'unknown'),
                        "Model": entry.get('model', 'unknown'),
                        "Context": entry.get('context', 'workflow'),
                        "Prompt Tokens": entry['usage'].get('prompt_tokens', 0),
                        "Completion Tokens": entry['usage'].get('completion_tokens', 0),
                        "Cost ($)": cost,
                        "Cumulative Cost ($)": 0.0
                    })
                except Exception as e:
                    print(f"Skipping bad json line: {e}")

    if not costs:
        print("Nessun dato sui costi trovato.")
        return

    # Sort by Timestamp text
    costs.sort(key=lambda x: x['Timestamp'])
    
    # Recalculate Cumulative
    running_total = 0.0
    for c in costs:
        running_total += c['Cost ($)']
        c['Cumulative Cost ($)'] = f"{running_total:.6f}"

    # Scrivi CSV
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fields = ["Timestamp", "Context", "Provider", "Model", "Prompt Tokens", "Completion Tokens", "Cost ($)", "Cumulative Cost ($)"]
    
    print(f"Scrittura report: {OUTPUT_CSV} ({len(costs)} righe)...")
    with open(OUTPUT_CSV, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(costs)
        
    # Calcola totali riepilogativi per Context/Provider/Model
    from collections import defaultdict
    summary = defaultdict(lambda: {"input": 0, "output": 0, "cost": 0.0, "count": 0})

    for c in costs:
        key = f"{c.get('Context', 'n/a')} :: {c['Provider']} :: {c['Model']}"
        summary[key]["input"] += int(c["Prompt Tokens"])
        summary[key]["output"] += int(c["Completion Tokens"])
        summary[key]["cost"] += float(c["Cost ($)"])
        summary[key]["count"] += 1
        
    total_input = sum(int(c["Prompt Tokens"]) for c in costs)
    total_output = sum(int(c["Completion Tokens"]) for c in costs)

    print("\n------------------------------------------------")
    print("RIEPILOGO COSTI API (Dettaglio Contesto/Modelli)")
    print("------------------------------------------------")
    
    total_global_usd = 0.0
    
    for key, stats in summary.items():
        print(f"🔹 {key}")
        print(f"   Chiamate: {stats['count']}")
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
        
        f.write("## 📊 Riepilogo per Contesto e Modello\n\n")
        f.write("| Contesto | Provider | Modello | Chiamate | Token In | Token Out | Costo ($) |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        
        for key, stats in summary.items():
            context, provider, model = key.split(" :: ", 2)
            f.write(f"| **{context}** | {provider} | {model} | {stats['count']} | {stats['input']:,} | {stats['output']:,} | ${stats['cost']:.4f} |\n")
            
        f.write(f"| **TOTALE** | | | **{len(costs)}** | **{total_input:,}** | **{total_output:,}** | **${total_global_usd:.4f}** |\n\n")
        
        f.write("## 📝 Dettaglio Ultime 50 Chiamate\n\n")
        f.write("| Timestamp | Contesto | Modello | In | Out | $\n")
        f.write("|---|---|---|---|---|---|\n")
        
        # Ultime 50 chiamate
        for c in list(reversed(costs))[:50]:
             f.write(f"| {c['Timestamp']} | {c.get('Context','-')} | {c['Model']} | {c['Prompt Tokens']} | {c['Completion Tokens']} | ${c['Cost ($)']} |\n")

if __name__ == "__main__":
    parse_log_for_costs()
