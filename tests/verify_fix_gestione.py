
import pandas as pd
import os

TEST_FILE = 'test_data.csv'

def setup_data():
    # Create dummy data with 10 rows
    df = pd.DataFrame({'id': range(10), 'val': range(10)})
    df.to_csv(TEST_FILE, index=False)
    return df

def simulate_bug():
    print("--- Simulating BUG (Old Logic) ---")
    setup_data()
    
    # 1. Load Data
    df = pd.read_csv(TEST_FILE)
    print(f"Original Rows: {len(df)}")
    
    # 2. Apply Filter (View)
    df_filtered = df[df['id'] < 2] # Only 2 rows
    print(f"Filtered Rows: {len(df_filtered)}")
    
    # 3. Save (The Bug: saving filtered DF)
    df_filtered.to_csv(TEST_FILE, index=False)
    
    # 4. Check Result
    df_after = pd.read_csv(TEST_FILE)
    print(f"Rows after Save: {len(df_after)}")
    if len(df_after) < 10:
        print("❌ BUG REPRODUCED: Data loss occurred!")
    else:
        print("✅ No Bug.")

def simulate_fix():
    print("\n--- Simulating FIX (New Logic) ---")
    setup_data()
    
    # 1. Load Data (View)
    df = pd.read_csv(TEST_FILE)
    
    # 2. Apply Filter (View)
    df_filtered = df[df['id'] < 2]
    
    # 3. User Edits on View (e.g. Row ID 0)
    # Simulator: User wants to change val of id=0 to 999
    
    # 4. Save (The Fix: Reload Full -> Update -> Save Full)
    # RELOAD
    df_full = pd.read_csv(TEST_FILE)
    
    # UPDATE
    idx = df_full[df_full['id'] == 0].index[0]
    df_full.at[idx, 'val'] = 999
    
    # SAVE
    df_full.to_csv(TEST_FILE, index=False)
    
    # 5. Check Result
    df_after = pd.read_csv(TEST_FILE)
    print(f"Rows after Save: {len(df_after)}")
    if len(df_after) == 10:
        print("✅ FIX VERIFIED: No data loss!")
        print(f"Value Updated: {df_after.iloc[0]['val'] == 999}")
    else:
        print("❌ Fix Failed.")

if __name__ == "__main__":
    simulate_bug()
    simulate_fix()
    if os.path.exists(TEST_FILE):
        os.remove(TEST_FILE)
