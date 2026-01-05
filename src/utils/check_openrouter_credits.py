
import os
import requests
import json
from dotenv import load_dotenv

def check_openrouter_status():
    load_dotenv()
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ OPENROUTER_API_KEY non trovata nelle variabili d'ambiente.")
        return

    headers = {
        "Authorization": f"Bearer {api_key}"
    }

    print("🔍 Verifica stato account OpenRouter...\n")

    # 1. Check Key Limits & Usage
    try:
        response = requests.get("https://openrouter.ai/api/v1/key", headers=headers)
        if response.status_code == 200:
            data = response.json().get("data", {})
            print(f"🔑 Chiave API: {data.get('label', 'Unnamed')}")
            
            limit = data.get('limit')
            usage = data.get('usage')
            limit_remaining = data.get('limit_remaining')
            
            limit_str = f"${limit:.4f}" if limit is not None else "Nessuno"
            usage_str = f"${usage:.4f}" if usage is not None else "0.0000"
            remaining_str = f"${limit_remaining:.4f}" if limit_remaining is not None else "Illimitato"
            
            print(f"   • Limite impostato: {limit_str}")
            print(f"   • Usato (totale): {usage_str}")
            print(f"   • Rimanente (limite): {remaining_str}")
        else:
            print(f"⚠️ Impossibile recuperare info chiave (Status: {response.status_code})")
            print(response.text)
    except Exception as e:
        print(f"❌ Errore durante richiesta /key: {e}")

    print("")

    # 2. Check Credits
    try:
        response = requests.get("https://openrouter.ai/api/v1/credits", headers=headers)
        if response.status_code == 200:
            data = response.json().get("data", {})
            total_credits = data.get("total_credits", 0)
            total_usage = data.get("total_usage", 0)
            
            print(f"💳 Crediti Account")
            print(f"   • Crediti Totali: ${total_credits:.4f}")
            print(f"   • Utilizzo Totale: ${total_usage:.4f}")
            
            remaining = total_credits - total_usage
            print(f"   • Saldo Rimanente Stimato: ${remaining:.4f}")
        else:
            print(f"⚠️ Impossibile recuperare info crediti (Status: {response.status_code})")
            print(response.text)
    except Exception as e:
        print(f"❌ Errore durante richiesta /credits: {e}")

    print("")

    # 3. Check Activity (Last 30 days)
    print("📊 Attività Recente (Ultimi 30gg da /activity)...")
    
    # OpenRouter recommend these headers
    activity_headers = headers.copy()
    activity_headers["HTTP-Referer"] = "https://github.com/nugh75/orienta_piu"
    activity_headers["X-Title"] = "Orienta Piu Analysis"

    try:
         # Activity endpoint returns aggregated stats
         response = requests.get("https://openrouter.ai/api/v1/activity", headers=activity_headers)
         if response.status_code == 200:
             resp_json = response.json()
             data = resp_json.get("data", [])
             
             if not data:
                 print("   Nessuna attività registrata negli ultimi 30 giorni.")
             else:
                 print(f"{'Data':<12} | {'Sorgente':<20} | {'Modello':<30} | {'Reqs':<6} | {'Credits ($)':<12}")
                 print("-" * 90)
                 
                 # Sort by date descending
                 try:
                     sorted_data = sorted(data, key=lambda x: x.get('date', ''), reverse=True)
                     
                     for item in sorted_data:
                         date = item.get('date', 'N/D')
                         # Some entries might be grouped by provider if model is null, or vice versa
                         model = item.get('model') or "Unknown"
                         provider = item.get('provider_name') or "Unknown"
                         
                         # Truncate for display
                         model_short = (model[:28] + '..') if len(model) > 28 else model
                         prov_short = (provider[:18] + '..') if len(provider) > 18 else provider
                         
                         # Fields based on search findings
                         # "total_usage" is likely the cost in credits
                         count = item.get('requests', 0)
                         usage = float(item.get('total_usage', 0)) 
                         
                         print(f"{date:<12} | {prov_short:<20} | {model_short:<30} | {str(count):<6} | {usage:.6f}")
                 except Exception as e:
                     print(f"⚠️ Errore parsing lista attività: {e}")
         else:
             print(f"⚠️ Impossibile recuperare attività (Status: {response.status_code})")
             if response.status_code == 403:
                 print("   🔒 Accesso negato: solo le 'Provisioning Keys' possono leggere lo storico attività.")
                 print("   💡 Usa 'make report-costs' per vedere i dettagli basati sui log locali.")
    except Exception as e:
        print(f"❌ Errore durante richiesta /activity: {e}")

if __name__ == "__main__":
    check_openrouter_status()
