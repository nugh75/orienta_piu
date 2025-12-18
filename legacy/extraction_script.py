import pandas as pd
import glob
import math

def main():
    # 1. Load Data
    files = glob.glob('paccmb_elenc*.csv')
    print(f"Loading {len(files)} files...")
    
    dfs = []
    for f in files:
        try:
            # Using latin1 as seen in previous steps (common for Italian stats files)
            df_temp = pd.read_csv(f, sep=';', encoding='latin1')
            dfs.append(df_temp)
        except Exception as e:
            print(f"Error reading {f}: {e}")

    if not dfs:
        print("No data loaded.")
        return

    full_df = pd.concat(dfs, ignore_index=True)
    print(f"Total schools loaded: {len(full_df)}")
    
    # 2. Stratification Analysis
    strat_col = 'strato'
    if strat_col not in full_df.columns:
        print(f"Error: Column '{strat_col}' not found.")
        return

    # Add 'grado' column
    # If percorso2 is NA/NaN -> Primo Grado
    # Else -> Secondo Grado
    full_df['grado'] = full_df['percorso2'].apply(lambda x: 'Primo Grado' if pd.isna(x) or str(x).strip() == '' or str(x).lower() == 'nan' else 'Secondo Grado')
    
    # Check distribution
    print("\nDistribution by Grade:")
    print(full_df['grado'].value_counts())

    # Clean duplicates if any (based on 'istituto' and 'plesso')
    # Using both ensures that if plesso is NA, we still distinguish by institute code.
    if 'plesso' in full_df.columns and 'istituto' in full_df.columns:
        initial_len = len(full_df)
        # Pandas treats (NA, NA) as equal to (NA, NA), but (ID1, NA) != (ID2, NA)
        full_df.drop_duplicates(subset=['istituto', 'plesso'], inplace=True)
        if len(full_df) < initial_len:
            print(f"Removed {initial_len - len(full_df)} duplicate rows based on 'istituto' + 'plesso'.")

    # 3. Calculate Stratified Sample
    TARGET_SIZE = 25
    population_size = len(full_df)
    
    # Calculate counts per stratum
    strata_counts = full_df[strat_col].value_counts()
    print("\nPopulation by Stratum:")
    print(strata_counts)

    # Initialize sample collection
    sample_df = pd.DataFrame()
    
    # We want proportional allocation.
    # Formula: n_h = (N_h / N) * n
    # But we need at least 1 per stratum if we want full coverage, 
    # BUT with 20 strata and n=25, most will be 1, some 2.
    # Let's simply shuffle and pick top N distributed proportionally?
    # Or use sklearn/pandas sampling.
    
    # Let's try to allocate roughly.
    allocation = (strata_counts / population_size * TARGET_SIZE).round().astype(int)
    
    # Fix allocation to ensure sum is 25 and min is 1 (if possible, otherwise fair sharing)
    # Actually, with 20 strata and 25 target, some will get 1, maybe some 2.
    # If we force min 1, we use 20 spots. 5 spots left for the largest strata.
    
    # Strategy: 
    # 1. Assign 1 to every stratum (since 20 <= 25).
    # 2. Distribute remaining 5 based on largest remainders or largest populations.
    
    if len(strata_counts) > TARGET_SIZE:
        print("Warning: Sample size smaller than number of strata. Some strata will be empty.")
    
    # Simple standardized way:
    # Use pandas sample with weights? No, that's random sampling.
    # We want *stratified* random sampling.
    
    # Let's implement the "1 minimum + proportional remainder" logic for robustness
    # given the user's specific "25" request vs "20" strata.
    
    allocated_counts = {k: 1 for k in strata_counts.index}
    current_total = sum(allocated_counts.values()) # Should be 20
    
    remaining_slots = TARGET_SIZE - current_total
    
    if remaining_slots > 0:
        # Give remaining slots to the most populous strata
        # Sort by size
        sorted_strata = strata_counts.sort_values(ascending=False).index
        for i in range(remaining_slots):
            stratum = sorted_strata[i % len(sorted_strata)] # Round robin if needed, but here simple top-k
            allocated_counts[stratum] += 1
            
    print("\nPlanned Allocation:")
    print(pd.Series(allocated_counts).sort_values(ascending=False))

    # Perform Sampling
    sampled_rows = []
    for stratum, count in allocated_counts.items():
        subset = full_df[full_df[strat_col] == stratum]
        
        if len(subset) < count:
            print(f"Warning: Stratum {stratum} has {len(subset)} items, requested {count}. Taking all.")
            sampled = subset
        else:
            sampled = subset.sample(n=count, random_state=42) # Fixed seed for reproducibility
            
        sampled_rows.append(sampled)

    final_sample = pd.concat(sampled_rows)
    
    # 4. Verification Check
    print("\nFinal Sample Size:", len(final_sample))
    print("Sample distribution by Strato:")
    print(final_sample[strat_col].value_counts())
    print("\nSample distribution by Grade:")
    print(final_sample['grado'].value_counts())

    # 5. Export
    output_file = 'campione_scuole.csv'
    final_sample.to_csv(output_file, sep=';', index=False, encoding='latin1')
    print(f"\nSaved sample to {output_file}")

if __name__ == "__main__":
    main()
