#!/usr/bin/env python3
"""
Metadata Refinement Script
Extracts missing ND metadata from PTOF markdown files.
Runs in parallel with the main LLM analysis pipeline.

Usage:
    python src/processing/refine_metadata.py
"""
import os
import re
import json
from glob import glob

# Paths
RESULTS_DIR = "analysis_results"
PTOF_MD_DIR = "ptof_md"  # Converted markdown files

print("=" * 60)
print("🔧 Metadata Refinement Script")
print("=" * 60)

def extract_metadata_from_md(md_path):
    """
    Extract metadata from PTOF markdown file.
    Returns dict with extracted values.
    """
    with open(md_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    metadata = {}
    
    # Extract denominazione (school name)
    # Look for patterns like "Istituto Comprensivo", "Liceo", etc.
    name_patterns = [
        r'(?:ISTITUTO|I\.?C\.?|LICEO|IIS|IPSIA|ITIS|ITT|ITCG|ISTITUTO COMPRENSIVO)\s*["\']?([A-Z][A-Za-z\s\.\-\']+)',
        r'PTOF\s+(?:\d{4}[/-]\d{2,4})?\s*["\']?([A-Z][A-Za-z\s\.\-\']{5,50})',
    ]
    for pattern in name_patterns:
        match = re.search(pattern, content[:3000], re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            if len(name) > 5 and len(name) < 100:
                metadata['denominazione'] = name.title()
                break
    
    # Extract comune (city)
    # Look for "Comune di", city names near address
    comune_patterns = [
        r'[Cc]omune\s+di\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        r'(?:Via|Viale|Piazza|Corso)\s+[^,]+,\s*(?:\d+\s*[,-]?\s*)?(\d{5})?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        r'Sede\s+(?:centrale|legale)?\s*[:\-]?\s*[^,]+,\s*([A-Z][a-z]+)',
    ]
    for pattern in comune_patterns:
        match = re.search(pattern, content[:5000])
        if match:
            comune = match.group(1) if match.group(1) else match.group(2)
            if comune and len(comune) > 2:
                metadata['comune'] = comune.strip().upper()
                break
    
    # Extract ordine_grado (school level)
    if re.search(r'scuola\s+media|secondaria\s+di\s+primo|I\s*grado', content[:5000], re.IGNORECASE):
        metadata['ordine_grado'] = 'I Grado'
        metadata['tipo_scuola'] = 'I Grado'
    elif re.search(r'liceo|istituto\s+tecnico|istituto\s+professionale|secondaria\s+di\s+secondo|II\s*grado', content[:5000], re.IGNORECASE):
        metadata['ordine_grado'] = 'II Grado'
        # Try to determine specific tipo
        if re.search(r'liceo', content[:5000], re.IGNORECASE):
            metadata['tipo_scuola'] = 'Liceo'
        elif re.search(r'tecnico', content[:5000], re.IGNORECASE):
            metadata['tipo_scuola'] = 'Tecnico'
        elif re.search(r'professionale', content[:5000], re.IGNORECASE):
            metadata['tipo_scuola'] = 'Professionale'
        else:
            metadata['tipo_scuola'] = 'II Grado'
    elif re.search(r'comprensivo', content[:5000], re.IGNORECASE):
        metadata['ordine_grado'] = 'I Grado'
        metadata['tipo_scuola'] = 'I Grado'
    
    return metadata


def refine_json_metadata(json_path, md_path):
    """
    Refine a JSON file by filling in ND values from the MD source.
    """
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return False, f"JSON error: {e}"
    
    if 'metadata' not in data:
        data['metadata'] = {}
    
    meta = data['metadata']
    refined = False
    
    # Extract from MD only if we have ND values
    fields_to_check = ['denominazione', 'comune', 'ordine_grado', 'tipo_scuola']
    has_nd = any(meta.get(f) == 'ND' or not meta.get(f) for f in fields_to_check)
    
    if has_nd and os.path.exists(md_path):
        extracted = extract_metadata_from_md(md_path)
        
        for field in fields_to_check:
            if (meta.get(field) == 'ND' or not meta.get(field)) and extracted.get(field):
                meta[field] = extracted[field]
                refined = True
    
    # Bidirectional sync for I Grado
    if meta.get('ordine_grado') == 'I Grado' and meta.get('tipo_scuola') == 'ND':
        meta['tipo_scuola'] = 'I Grado'
        refined = True
    if meta.get('tipo_scuola') == 'I Grado' and meta.get('ordine_grado') == 'ND':
        meta['ordine_grado'] = 'I Grado'
        refined = True
    
    # Same for II Grado
    if meta.get('ordine_grado') == 'II Grado' and meta.get('tipo_scuola') == 'ND':
        meta['tipo_scuola'] = 'II Grado'
        refined = True
    if meta.get('tipo_scuola') in ['Liceo', 'Tecnico', 'Professionale'] and meta.get('ordine_grado') == 'ND':
        meta['ordine_grado'] = 'II Grado'
        refined = True
    
    if refined:
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    return refined, "Refined" if refined else "No changes"


def main():
    # Find all JSON files
    json_files = glob(os.path.join(RESULTS_DIR, '*_analysis.json'))
    print(f"Found {len(json_files)} JSON files to check")
    
    refined_count = 0
    error_count = 0
    
    for json_path in json_files:
        filename = os.path.basename(json_path)
        school_code = filename.replace('_PTOF_analysis.json', '').replace('_analysis.json', '')
        
        # Find corresponding MD file
        md_candidates = [
            os.path.join(PTOF_MD_DIR, f"{school_code}.md"),
            os.path.join(PTOF_MD_DIR, f"{school_code}_PTOF.md"),
        ]
        md_path = None
        for candidate in md_candidates:
            if os.path.exists(candidate):
                md_path = candidate
                break
        
        success, msg = refine_json_metadata(json_path, md_path)
        if success:
            print(f"  ✓ Refined: {school_code}")
            refined_count += 1
        elif "error" in msg.lower():
            print(f"  ✗ Error: {school_code} - {msg}")
            error_count += 1
        else:
            print(f"  · No changes: {school_code}")
    
    print(f"\n{'=' * 60}")
    print(f"✅ REFINEMENT COMPLETE")
    print(f"   - Refined: {refined_count}")
    print(f"   - Errors: {error_count}")
    print(f"   - Unchanged: {len(json_files) - refined_count - error_count}")
    print("=" * 60)


if __name__ == "__main__":
    main()
