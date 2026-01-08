import pandas as pd
import sys
import os

try:
    df = pd.read_csv('data/analysis_summary.csv')
    print("Loaded data/analysis_summary.csv")
    print(f"Shape: {df.shape}")
    
    if 'ptof_orientamento_maturity_index' in df.columns:
        col = df['ptof_orientamento_maturity_index']
        print("\nptof_orientamento_maturity_index stats:")
        print(col.describe())
        print("\nHead:")
        print(col.head())
        
        # Test function from data_utils
        def scale_to_pct(score):
            if pd.isna(score): return 0.0
            return max(0.0, min(100.0, (score - 1.0) / 6.0 * 100.0))
            
        scaled = col.apply(scale_to_pct)
        print("\nScaled stats (using 1-7 formula):")
        print(scaled.describe())
        
        print("\nPercentiles of scaled:")
        print(f"P25: {scaled.quantile(0.25)}")
        print(f"P75: {scaled.quantile(0.75)}")

    else:
        print("Column 'ptof_orientamento_maturity_index' not found.")
        
except Exception as e:
    print(f"Error: {e}")
