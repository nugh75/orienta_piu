"""
Multi-Stage Pipeline Functions for PTOF Analysis
Stage 2: Deep Activity Analysis
Stage 3: Narrative Synthesis
"""

def build_activity_deep_prompt(activity, school_meta, relevant_chunks):
    """
    Builds a prompt for deep 5W+H analysis of a single activity.
    """
    school_info = f"""
    SCUOLA: {school_meta.get('denominazionescuola', 'ND')}
    CODICE: {school_meta.get('istituto', 'ND')}
    """
    
    chunks_text = "\n\n".join([f"[CHUNK {i+1}]\n{chunk[:1000]}" for i, chunk in enumerate(relevant_chunks[:3])])
    
    prompt = f"""
    RUOLO: Sei un analista esperto di politiche scolastiche e orientamento.
    
    ⚠️ LINGUA: Scrivi TUTTO in ITALIANO. L'analisi deve essere completamente in italiano.
    
    CONTESTO:
    {school_info}
    
    ATTIVITÀ DA ANALIZZARE IN PROFONDITÀ:
    - Titolo: {activity.get('titolo_attivita', 'ND')}
    - Categoria: {activity.get('categoria_principale', 'ND')}
    - Ore dichiarate: {activity.get('ore_dichiarate', 'ND')}
    - Target: {activity.get('target', 'ND')}
    - Evidenza: {activity.get('evidence_quote', 'ND')}
    - Posizione: {activity.get('evidence_location', 'ND')}
    
    ESTRATTI RILEVANTI DAL DOCUMENTO:
    {chunks_text}
    
    COMPITO:
    Scrivi un'analisi approfondita di questa attività usando il FRAMEWORK 5W+H.
    Il testo deve essere un UNICO PARAGRAFO DISCORSIVO di 150-200 parole.
    
    FRAMEWORK 5W+H (DA INTEGRARE NEL PARAGRAFO):
    1. **CHI** (Attori): Chi sono i protagonisti? (Docenti specifici, dipartimenti, partner esterni nominati, studenti di quali classi)
    2. **COSA** (Contenuto): In cosa consiste concretamente l'attività? Quali sono le azioni specifiche?
    3. **COME** (Metodologia): Come viene svolta? (Laboratorio, lezione frontale, co-progettazione, uscita didattica, modalità mista)
    4. **PERCHÉ** (Obiettivo): Qual è il bisogno educativo o l'obiettivo strategico che questa attività affronta?
    5. **ASPETTATIVE** (Outcome): Cosa ci si aspetta che cambi negli studenti? Quali competenze sviluppano?
    
    VINCOLI:
    - NON usare elenchi puntati
    - Scrivi un paragrafo fluido e coeso
    - Cita sempre le pagine di riferimento
    - Se mancano informazioni per una delle 5W, dillo esplicitamente ("Non è specificato chi...")
    
    ESEMPIO DI FORMATO ATTESO:
    "Il laboratorio di biologia marina (PAGINA 45) coinvolge gli studenti del triennio scientifico e i docenti del dipartimento di Scienze, in collaborazione con la Fondazione Mare Nostrum (CHI). L'attività si articola in tre incontri teorici in aula e due uscite didattiche presso il laboratorio costiero di Villasimius (COSA), seguendo una metodologia esperienziale che alterna momenti di osservazione diretta e analisi di campioni in laboratorio (COME). L'obiettivo è sviluppare competenze scientifiche di base e consapevolezza ambientale, rispondendo al bisogno di connettere teoria e pratica nelle discipline STEM (PERCHÉ). Ci si aspetta che gli studenti acquisiscano autonomia nella conduzione di esperimenti e capacità di presentare risultati scientifici, competenze certificate attraverso un project work finale (ASPETTATIVE)."
    
    Ora scrivi il tuo paragrafo per l'attività indicata:
    """
    return prompt


def deep_analyze_activities(school_code, json_data, chunks, call_ollama_func):
    """
    Stage 2: Performs deep 5W+H analysis for each activity.
    Returns a list of deep analyses.
    """
    import logging
    
    activities = json_data.get('activities_register', [])
    if not activities:
        logging.warning(f"No activities found for {school_code}")
        return []
    
    deep_analyses = []
    school_meta = json_data.get('metadata', {})
    
    logging.info(f"Stage 2: Deep analyzing {len(activities)} activities for {school_code}")
    
    for idx, activity in enumerate(activities):
        logging.info(f"  Analyzing activity {idx+1}/{len(activities)}: {activity.get('titolo_attivita', 'ND')}")
        
        # Build prompt for this specific activity
        prompt = build_activity_deep_prompt(activity, school_meta, chunks)
        
        # Call LLM for deep analysis
        narrative_paragraph = call_ollama_func(prompt)
        
        if not narrative_paragraph:
            logging.warning(f"  Failed to generate deep analysis for activity {idx+1}")
            narrative_paragraph = f"Analisi non disponibile per {activity.get('titolo_attivita', 'ND')}."
        
        deep_analyses.append({
            'activity_id': activity.get('activity_id', f'act_{idx+1}'),
            'titolo': activity.get('titolo_attivita', 'ND'),
            'categoria': activity.get('categoria_principale', 'ND'),
            'narrative_paragraph': narrative_paragraph.strip()
        })
    
    logging.info(f"Stage 2 completed: {len(deep_analyses)} deep analyses generated")
    return deep_analyses


def build_synthesis_prompt(school_meta, json_data, deep_activities):
    """
    Builds a prompt for Stage 3: Narrative Synthesis.
    """
    school_info = f"""
    SCUOLA: {school_meta.get('denominazionescuola', 'ND')}
    CODICE: {school_meta.get('istituto', 'ND')}
    GRADO: {school_meta.get('ordine_grado', 'ND')}
    """
    
    # Prepare deep activities text
    activities_text = "\n\n".join([
        f"**{act['titolo']}** ({act['categoria']})\n{act['narrative_paragraph']}"
        for act in deep_activities
    ])
    
    # Extract partnership info
    partnerships = json_data.get('ptof_section2', {}).get('2_2_partnership', {})
    partner_names = partnerships.get('partner_nominati', [])
    
    prompt = f"""
    RUOLO: Sei un analista esperto di politiche scolastiche e orientamento.
    
    ⚠️ LINGUA: Scrivi TUTTO in ITALIANO. Il report narrativo deve essere completamente in italiano.
    
    CONTESTO:
    {school_info}
    
    HAI A DISPOSIZIONE:
    1. Dati strutturati (JSON) con score e partnership
    2. {len(deep_activities)} ANALISI PROFONDE già pronte per le attività
    
    ANALISI PROFONDE DELLE ATTIVITÀ:
    {activities_text}
    
    PARTNERSHIP RILEVATE:
    {', '.join(partner_names[:10]) if partner_names else 'Nessuna partnership nominata'}
    
    COMPITO:
    Assembla un report narrativo completo usando ESCLUSIVAMENTE i materiali forniti sopra.
    NON inventare nuove informazioni. Usa SOLO le analisi profonde e i dati strutturati.
    
    STRUTTURA DEL REPORT (7 SEZIONI):
    
    **1) Collocazione dell'orientamento nel documento**
    Descrivi se esiste una sezione dedicata e come l'orientamento è distribuito nel PTOF.
    Usa il campo has_sezione_dedicata={json_data.get('ptof_section2', {}).get('2_1_ptof_orientamento_sezione_dedicata', {}).get('has_sezione_dedicata', 0)}
    
    **2) Finalità e obiettivi dichiarati**
    Sintetizza le finalità principali basandoti sui score delle finalità.
    
    **3) Azioni e attività operative**
    QUESTA È LA SEZIONE PIÙ IMPORTANTE.
    Inserisci QUI tutte le {len(deep_activities)} analisi profonde fornite sopra.
    Organizzale per categoria (PCTO, Laboratori, Stage, etc).
    Ogni attività deve avere il suo paragrafo completo (già fornito).
    
    **4) Reti e partnership**
    Descrivi le collaborazioni usando i nomi dei partner forniti.
    
    **5) Inclusione ed equità**
    Cerca nelle attività profonde eventuali riferimenti a inclusione, BES, DSA.
    
    **6) Monitoraggio e miglioramento**
    Cerca nelle attività profonde riferimenti a valutazione e monitoraggio.
    
    **7) Gap Analysis**
    Elenca cosa MANCA (senza suggerire soluzioni).
    
    VINCOLI:
    - NON usare elenchi puntati
    - Scrivi in paragrafi discorsivi
    - Cita sempre le pagine (già presenti nelle analisi profonde)
    - NON inventare attività non presenti nelle analisi fornite
    
    Genera il report completo:
    """
    return prompt


def generate_narrative_report(school_code, json_data, deep_activities, chunks, call_ollama_func):
    """
    Stage 3: Generates final narrative report using deep analyses.
    """
    import logging
    
    logging.info(f"Stage 3: Generating narrative synthesis for {school_code}")
    
    school_meta = json_data.get('metadata', {})
    prompt = build_synthesis_prompt(school_meta, json_data, deep_activities)
    
    narrative_text = call_ollama_func(prompt)
    
    if not narrative_text:
        logging.error(f"Stage 3 failed for {school_code}")
        return "Errore nella generazione del report narrativo."
    
    logging.info(f"Stage 3 completed for {school_code}")
    return narrative_text.strip()


def validate_and_correct_json(school_code, json_data, md_content):
    """
    Stage 4: Validates JSON scores against narrative report and corrects inconsistencies.
    Uses rule-based approach: if MD is very negative, reduce high scores.
    """
    import logging
    
    logging.info(f"Stage 4: Validating JSON consistency for {school_code}")
    
    # Define negative keywords that indicate problems/gaps
    negative_keywords = [
        'manca', 'assente', 'non presente', 'non sono', 'non è', 'non fornisce',
        'lacune', 'limitato', 'limitata', 'frammentario', 'frammentaria',
        'non esplicita', 'non specificato', 'non identificat', 'non includ',
        'gap', 'carenza', 'insufficiente', 'scarso', 'scarsa'
    ]
    
    # Count negative indicators in the report
    md_lower = md_content.lower()
    negative_count = sum(md_lower.count(kw) for kw in negative_keywords)
    
    # Count paragraphs (rough estimate)
    paragraphs = len([p for p in md_content.split('\n\n') if len(p.strip()) > 50])
    
    # Calculate negativity score
    negativity_score = (negative_count / paragraphs * 100) if paragraphs > 0 else 0
    
    logging.info(f"  Negativity analysis: {negative_count} negative words in {paragraphs} paragraphs = {negativity_score:.1f}%")
    
    # Determine correction threshold based on negativity
    if negativity_score > 70:
        max_allowed_score = 2
        correction_reason = "Report molto negativo (>70% negatività)"
    elif negativity_score > 50:
        max_allowed_score = 3
        correction_reason = "Report negativo (>50% negatività)"
    elif negativity_score > 30:
        max_allowed_score = 4
        correction_reason = "Report parzialmente negativo (>30% negatività)"
    else:
        logging.info(f"  No correction needed (negativity: {negativity_score:.1f}%)")
        return json_data, False  # No correction
    
    logging.warning(f"  Applying correction: max score = {max_allowed_score} ({correction_reason})")
    
    # Apply corrections to all scores in ptof_section2
    corrected = False
    for section_key in json_data.get('ptof_section2', {}):
        section = json_data['ptof_section2'][section_key]
        if isinstance(section, dict):
            # Handle nested structures
            for item_key, item in section.items():
                if isinstance(item, dict) and 'score' in item:
                    original_score = item['score']
                    if original_score > max_allowed_score:
                        item['score'] = max_allowed_score
                        corrected = True
                        logging.info(f"    Corrected {section_key}.{item_key}: {original_score} → {max_allowed_score}")
    
    if corrected:
        logging.info(f"  Stage 4 completed: JSON scores corrected based on narrative negativity")
    else:
        logging.info(f"  Stage 4 completed: No scores exceeded threshold")
    
    return json_data, corrected
