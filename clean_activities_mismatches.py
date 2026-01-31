
import pandas as pd
import json
import shutil
from pathlib import Path
from datetime import datetime

def main():
    print("--- Activity Cleanup: Removing Impostor Entries ---")
    
    # Files
    log_file = Path("data/removed_impostors_log.txt")
    attivita_path = Path("data/attivita.csv")
    registry_path = Path("data/activity_registry.json")
    
    if not log_file.exists():
        print("Error: data/removed_impostors_log.txt not found. Cannot proceed.")
        return
        
    # 1. Load codes to remove
    with open(log_file, "r") as f:
        codes_to_remove = set(line.strip().upper() for line in f if line.strip())
    
    print(f"Codes marked for removal: {len(codes_to_remove)}")
    
    if len(codes_to_remove) == 0:
        print("No codes to remove.")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 2. Clean attivita.csv
    if attivita_path.exists():
        print(f"\nProcessing {attivita_path}...")
        try:
            df = pd.read_csv(attivita_path)
            if 'codice_meccanografico' in df.columns:
                original_len = len(df)
                
                # Filter
                df_clean = df[~df['codice_meccanografico'].astype(str).str.upper().str.strip().isin(codes_to_remove)]
                new_len = len(df_clean)
                removed_rows = original_len - new_len
                
                if removed_rows > 0:
                    # Backup
                    backup_path = attivita_path.with_suffix(f".bak.{timestamp}.csv")
                    shutil.copy(attivita_path, backup_path)
                    print(f" - Backup created: {backup_path}")
                    
                    df_clean.to_csv(attivita_path, index=False)
                    print(f" - Rows removed: {removed_rows}")
                else:
                    print(" - No matching activities found.")
            else:
                print(" - Error: 'codice_meccanografico' column missing.")
        except Exception as e:
            print(f" - Error processing CSV: {e}")

    # 3. Clean activity_registry.json
    if registry_path.exists():
        print(f"\nProcessing {registry_path}...")
        try:
            with open(registry_path, 'r') as f:
                data = json.load(f)
            
            modified = False
            
            # Remove from processed_files dict
            if "processed_files" in data:
                original_count = len(data["processed_files"])
                keys_to_del = [k for k in data["processed_files"] if k.upper() in codes_to_remove]
                
                for k in keys_to_del:
                    del data["processed_files"][k]
                    modified = True
                
                print(f" - Removed {len(keys_to_del)} entries from processed_files")
            
            if modified:
                backup_path = registry_path.with_suffix(f".bak.{timestamp}.json")
                shutil.copy(registry_path, backup_path)
                print(f" - Backup created: {backup_path}")
                
                with open(registry_path, 'w') as f:
                    json.dump(data, f, indent=4)
                print(" - Registry updated.")
            else:
                print(" - No changes needed.")
                
        except Exception as e:
             print(f" - Error processing JSON: {e}")

    print("\n--- Cleanup Finished ---")

if __name__ == "__main__":
    main()
