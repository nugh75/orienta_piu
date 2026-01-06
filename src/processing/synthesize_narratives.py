import json
import os

SCHOOLS = ['RMTD087023', 'RMIC8CN00V', 'PG1E00400E']
RESULTS_DIR = 'analysis_results'

def generate_markdown(data):
    meta = data.get('metadata', {})
    school_name = meta.get('denominazione', 'Scuola')
    school_id = meta.get('school_id', 'ND')
    city = meta.get('comune', 'ND')
    
    md = f"# Analisi PTOF: {school_name} ({city})\n\n"
    md += f"## 🏫 Dati Scuola\n"
    md += f"*   **Codice**: {school_id}\n"
    md += f"*   **Città**: {city}\n"
    md += f"*   **Tipo**: {meta.get('tipo_scuola', 'ND')}\n\n"
    md += "---\n\n"
    
    # Section 2 Analysis
    sec2 = data.get('ptof_section2', {})
    
    md += "## 📊 Analisi Orientamento\n\n"
    
    # 2.1
    s21 = sec2.get('2_1_ptof_orientamento_sezione_dedicata', {})
    score21 = s21.get('score', 0)
    md += f"### Sezione Dedicata (Voto: {score21}/5)\n"
    if score21 >= 3:
        md += "Il PTOF dedica una sezione specifica e strutturata all'orientamento.\n\n"
    else:
        md += "L'orientamento è trattato in modo trasversale o poco approfondito.\n\n"
        
    # 2.3 Finalita
    s23 = sec2.get('2_3_finalita', {})
    md += "### Finalità\n"
    for k, v in s23.items():
        if isinstance(v, dict):
            md += f"*   **{k.replace('finalita_', '').title()}**: {v.get('score', 0)}/5\n"
    md += "\n"
    
    # 2.4 Obiettivi
    s24 = sec2.get('2_4_obiettivi', {})
    md += "### Obiettivi\n"
    for k, v in s24.items():
        if isinstance(v, dict):
            md += f"*   **{k.replace('obiettivo_', '').replace('_', ' ').title()}**: {v.get('score', 0)}/5\n"
    md += "\n"
    
    # Strengths and Weaknesses
    md += "### Punti di Forza\n"
    high_scores = []
    for section in [s23, s24, sec2.get('2_5_azioni_sistema', {}), sec2.get('2_6_didattica_orientativa', {})]:
        for k, v in section.items():
            if isinstance(v, dict) and v.get('score', 0) >= 5:
                high_scores.append(k.replace('_', ' ').title())
    
    if high_scores:
        for s in high_scores[:5]:
            md += f"*   {s}\n"
    else:
        md += "Nessun punto di eccellenza rilevato dai dati strutturati.\n"
    md += "\n"
    
    md += "### Aree di Miglioramento\n"
    low_scores = []
    for section in [s23, s24, sec2.get('2_5_azioni_sistema', {}), sec2.get('2_6_didattica_orientativa', {})]:
        for k, v in section.items():
            if isinstance(v, dict) and 0 < v.get('score', 0) <= 2:
                low_scores.append(k.replace('_', ' ').title())
    
    if low_scores:
        for s in low_scores[:5]:
            md += f"*   {s}\n"
    else:
        md += "Nessuna criticità evidente rilevata dai dati strutturati.\n"
    md += "\n"
    
    md += "---\n"
    md += "*Report generato automaticamente dai dati dell'analisi JSON.*\n"
    
    return md

for school_id in SCHOOLS:
    json_path = os.path.join(RESULTS_DIR, f"{school_id}_PTOF_analysis.json")
    md_path = os.path.join(RESULTS_DIR, f"{school_id}_PTOF_analysis.md")
    
    if not os.path.exists(json_path):
        continue
        
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
            
        # Only overwrite if narrative is missing in file
        # But here we know it is missing in the JSON key, so we generate it
        # We also want to SAVE this narrative into the JSON to be safe for future? 
        # Ideally yes, but file lock risk. Let's just write the MD.
        
        md_content = generate_markdown(data)
        
        with open(md_path, 'w') as f:
            f.write(md_content)
        print(f"Generated {md_path}")
        
    except Exception as e:
        print(f"Error {school_id}: {e}")
