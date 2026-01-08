import pandas as pd
import sys
sys.path.append('app')
from data_utils import scale_to_pct

# Mock format_pct exactly as in data_utils
def format_pct(score: float, decimals: int = 1) -> str:
    if pd.isna(score):
        return "N/D"
    pct = scale_to_pct(score)
    return f"{pct:.{decimals}f}%"

def verify_fix():
    print("--- Loading Data ---")
    df = pd.read_csv('data/analysis_summary.csv')
    
    # Mimic Home.py loading
    col = 'ptof_orientamento_maturity_index'
    if col in df.columns:
        # Step 1: Convert to numeric and scale to pct (Home.py lines 149-151)
        df[col] = pd.to_numeric(df[col], errors='coerce')
        df[col] = df[col].apply(scale_to_pct)
        
        ro_series = df[col].dropna()
        
        mean_ro = ro_series.mean()
        median_ro = ro_series.median()
        p25 = ro_series.quantile(0.25)
        p75 = ro_series.quantile(0.75)
        
        print(f"\nCalculated Values (Pct 0-100):")
        print(f"Mean: {mean_ro}")
        print(f"Median: {median_ro}")
        print(f"P25: {p25}")
        print(f"P75: {p75}")
        
        print("\n--- Comparison ---")
        print(f"BUGGY (Old Code): {format_pct(p25)}")
        print(f"FIXED (New Code): {p25:.1f}%")
        
        print(f"BUGGY Distribution: {format_pct(p25)} - {format_pct(p75)}")
        print(f"FIXED Distribution: {p25:.1f}% - {p75:.1f}%")
        
        if p25 > 20 and p75 < 80: # Rough sanity check
             print("\nSUCCESS: Values look reasonable.")
        else:
             print("\nWARNING: Values might still be odd.")

if __name__ == "__main__":
    verify_fix()
