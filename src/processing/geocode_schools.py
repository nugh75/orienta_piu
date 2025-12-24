#!/usr/bin/env python3
"""
Geocode schools in analysis_summary.csv using data/italy_geo.json.
Adds 'lat' and 'lon' columns to the CSV.
"""
import pandas as pd
import json
import os
import sys
from pathlib import Path

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

DATA_DIR = BASE_DIR / "data"
SUMMARY_FILE = DATA_DIR / "analysis_summary.csv"
GEO_FILE = DATA_DIR / "italy_geo.json"

def normalize_name(name):
    if pd.isna(name):
        return ""
    return str(name).strip().lower()

def main():
    if not SUMMARY_FILE.exists():
        print(f"❌ {SUMMARY_FILE} not found.")
        return
    
    if not GEO_FILE.exists():
        print(f"❌ {GEO_FILE} not found.")
        return

    print("⏳ Loading data...")
    df = pd.read_csv(SUMMARY_FILE)
    
    with open(GEO_FILE, 'r', encoding='utf-8') as f:
        geo_data = json.load(f)
    
    # Create mapping: normalized_name -> (lat, lon)
    # Also map by ISTAT code if available in CSV (but we likely only have comune name)
    geo_map = {}
    for entry in geo_data:
        try:
            if 'comune' not in entry:
                continue
            name = normalize_name(entry['comune'])
            if 'lat' not in entry or 'lng' not in entry:
                continue
            if not entry['lat'] or not entry['lng']:
                continue
            lat = float(entry['lat'])
            lng = float(entry['lng'])
            geo_map[name] = (lat, lng)
        except ValueError:
            continue
    
    print(f"📍 Loaded {len(geo_map)} locations.")
    
    # Apply geocoding
    def get_coords(row):
        comune = normalize_name(row.get('comune', ''))
        if comune in geo_map:
            return geo_map[comune]
        return None, None

    # Add columns if not exist
    if 'lat' not in df.columns:
        df['lat'] = None
    if 'lon' not in df.columns:
        df['lon'] = None
        
    # Update coordinates
    matches = 0
    for idx, row in df.iterrows():
        lat, lon = get_coords(row)
        if lat is not None:
            df.at[idx, 'lat'] = lat
            df.at[idx, 'lon'] = lon
            matches += 1
            
    print(f"✅ Geocoded {matches}/{len(df)} schools.")
    
    # Save
    df.to_csv(SUMMARY_FILE, index=False)
    print(f"💾 Saved to {SUMMARY_FILE}")

if __name__ == "__main__":
    main()
