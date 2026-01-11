
import pandas as pd
import sys

# Mocking the functions to test logic without importing from the streamlit app which would run it
def normalize_multivalue_field(
    series: pd.Series,
    separator: str = '|',
    canonical_map: dict[str, str] | None = None
) -> list[str]:
    if series.empty:
        return []
    values = series.dropna().astype(str).str.split(separator).explode()
    canonical = {}
    for v in values:
        v_stripped = v.strip()
        if not v_stripped:
            continue
        key = v_stripped.lower()
        if key not in canonical:
            if canonical_map and key in canonical_map:
                canonical[key] = canonical_map[key]
            else:
                canonical[key] = v_stripped 
    return sorted(canonical.values())

def build_geo_hierarchy(df: pd.DataFrame) -> dict:
    hierarchy = {
        "area_to_regioni": {},
        "regione_to_province": {}
    }
    if df.empty:
        return hierarchy

    if 'area_geografica' in df.columns and 'regione' in df.columns:
        area_reg = df[['area_geografica', 'regione']].dropna().drop_duplicates()
        for area in area_reg['area_geografica'].unique():
            regioni = sorted(area_reg[area_reg['area_geografica'] == area]['regione'].unique().tolist())
            hierarchy["area_to_regioni"][area] = regioni

    if 'regione' in df.columns and 'provincia' in df.columns:
        reg_prov = df[['regione', 'provincia']].dropna().drop_duplicates()
        for regione in reg_prov['regione'].unique():
            province = sorted(reg_prov[reg_prov['regione'] == regione]['provincia'].unique().tolist())
            hierarchy["regione_to_province"][regione] = province

    return hierarchy

def main():
    print("Testing Geo Hierarchy Logic...")
    
    # Create dummy data
    data = {
        'area_geografica': ['Nord Ovest', 'Nord Ovest', 'Sud', 'Sud', 'Nord Est'],
        'regione': ['Lombardia', 'Piemonte', 'Campania', 'Puglia', 'Veneto'],
        'provincia': ['Milano', 'Torino', 'Napoli', 'Bari', 'Venezia'],
        'ambiti_attivita': ['Coding|Robotica', 'Coding ', 'arte', 'Arte', 'musica']
    }
    df = pd.DataFrame(data)
    
    # Test Hierarchy
    hierarchy = build_geo_hierarchy(df)
    
    assert 'Nord Ovest' in hierarchy['area_to_regioni']
    assert 'Lombardia' in hierarchy['area_to_regioni']['Nord Ovest']
    assert 'Piemonte' in hierarchy['area_to_regioni']['Nord Ovest']
    assert 'Campania' not in hierarchy['area_to_regioni']['Nord Ovest']
    
    assert 'Lombardia' in hierarchy['regione_to_province']
    assert 'Milano' in hierarchy['regione_to_province']['Lombardia']
    
    print("Hierarchy matches expected structure.")
    
    # Test Normalization
    print("Testing Normalization...")
    normalized_ambiti = normalize_multivalue_field(df['ambiti_attivita'])
    print(f"Normalized: {normalized_ambiti}")
    
    assert 'Coding' in normalized_ambiti or 'coding' in normalized_ambiti
    assert 'Robotica' in normalized_ambiti or 'robotica' in normalized_ambiti
    # Check deduplication (Coding vs Coding ) and case (arte vs Arte)
    # Based on implementation, it keeps the first one encountered or stripped version
    
    assert len(normalized_ambiti) == 4 # Coding, Robotica, arte, musica (unique case insensitive)
    
    print("Normalization logic verified.")

if __name__ == "__main__":
    main()
