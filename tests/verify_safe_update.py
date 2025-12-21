
import pandas as pd
import os
import shutil
from src.data.data_manager import update_index_safe, SUMMARY_FILE

def verify_fix():
    print("--- Verification Start ---")
    
    # 1. Backup existing
    if os.path.exists(SUMMARY_FILE):
        shutil.copy(SUMMARY_FILE, SUMMARY_FILE + ".bak")
        
    # 2. Simulate a Manual Edit
    # Load CSV, pick first school, change name to "MANUAL_EDIT_TEST"
    df = pd.read_csv(SUMMARY_FILE)
    if df.empty:
        print("CSV empty, cannot verify manual edit preservation.")
        return
        
    test_id = df.iloc[0]['school_id']
    original_name = df.iloc[0]['denominazione']
    print(f"Test School: {test_id} | Original Name: {original_name}")
    
    df.at[0, 'denominazione'] = "MANUAL_EDIT_TEST"
    df.to_csv(SUMMARY_FILE, index=False)
    print("-> Manual edit applied (Name changed to MANUAL_EDIT_TEST)")
    
    # 3. Run Safe Update
    print("-> Running update_index_safe()...")
    success, count = update_index_safe()
    
    # 4. Check Result
    df_new = pd.read_csv(SUMMARY_FILE)
    row = df_new[df_new['school_id'] == test_id].iloc[0]
    new_name = row['denominazione']
    
    print(f"-> Name after update: {new_name}")
    
    if new_name == "MANUAL_EDIT_TEST":
        print("✅ SUCCESS: Manual edit preserved!")
    else:
        print(f"❌ FAILURE: Name reverted to {new_name}")
        
    # 5. Restore
    shutil.move(SUMMARY_FILE + ".bak", SUMMARY_FILE)
    print("--- Verification End (Restored original CSV) ---")

if __name__ == "__main__":
    verify_fix()
