"""Modular prompt components for meta reports.

Fase 2.3: Sistema di composizione modulare dei prompt.

I componenti possono essere combinati per costruire system prompt
personalizzati per ogni tipo di report.
"""

# =============================================================================
# Regole comuni a tutti i report
# =============================================================================

COMMON_RULES = """
REGOLE GENERALI:
- Scrivi in italiano accademico, registro formale
- Evita toni celebrativi e superlativi
- NON usare blocchi di codice (```)
- NON usare emoji
- Basa l'analisi SOLO sui dati forniti
"""

CITATION_RULES = """
REGOLE CITAZIONI:
- Cita SOLO scuole presenti nei dati forniti (sample_cases o chunk_notes)
- Usa SEMPRE il formato: Nome Scuola (CODICE)
- Esempio: Liceo Galilei (RMPS12345X)
- NON inventare codici meccanografici
- Se non hai il codice, non citare la scuola
- Codici italiani: 2 lettere regione + 2 lettere tipo + 5-6 caratteri alfanumerici
"""

NARRATIVE_STYLE = """
STILE NARRATIVO OBBLIGATORIO:
- Scrivi ESCLUSIVAMENTE in prosa fluida e discorsiva
- NON usare MAI elenchi puntati (-, *, •)
- NON usare MAI elenchi numerati (1., 2., 3.)
- Usa connettivi logici: inoltre, tuttavia, in particolare, analogamente, similmente
- Metti in **grassetto** nomi di scuole, partner, progetti chiave
- Costruisci paragrafi coesi di 4-6 frasi

VIETATO CATEGORICAMENTE:
- Creare liste di qualsiasi tipo
- Usare ":" seguito da elenchi
- Strutturare il testo come bullet points mascherati
"""

# =============================================================================
# Istruzioni formato Markdown
# =============================================================================

NO_MARKDOWN_HEADERS = """
FORMATO OUTPUT (contenuto parziale):
- NON usare titoli Markdown (#, ##, ###)
- NON usare righe in grassetto che fungono da titoli
- Scrivi paragrafi continui e discorsivi
- Questo testo verrà integrato in un documento più ampio
"""

WITH_MARKDOWN_HEADERS = """
FORMATO OUTPUT (report completo):
- Usa titoli Markdown per strutturare il report:
  - # per il titolo principale (uno solo)
  - ## per sezioni maggiori
  - ### per sottosezioni
- Mantieni gerarchia coerente
"""

# =============================================================================
# Fase 2.2: Strutture potenziate per i profili
# =============================================================================

PROFILE_STRUCTURES = {
    "overview": {
        "name": "Quadro Complessivo",
        "focus": "bilanciato",
        "description": "Copri tutti gli aspetti principali senza approfondire troppo. Bilancia punti di forza e aree di sviluppo.",
        "target_audience": "dirigenti, stakeholder generici",
        "word_count": "800-1200 parole",
        "sections": ["Sintesi", "Analisi", "Punti di Forza", "Aree di Sviluppo", "Conclusioni"],
        "requirements": []
    },
    "innovative": {
        "name": "Focus Innovazione",
        "focus": "pratiche originali e non convenzionali",
        "description": "Evidenzia SOLO le pratiche più originali. Cerca approcci non convenzionali, sperimentazioni, primi in Italia.",
        "target_audience": "ricercatori, policy maker, scuole che vogliono innovare",
        "word_count": "600-900 parole",
        "sections": ["Innovazioni Chiave", "Analisi Critica", "Potenziale di Scalabilità"],
        "requirements": [
            "Almeno 3 pratiche innovative con spiegazione del PERCHÉ sono innovative",
            "Confronto esplicito con la prassi standard",
            "Valutazione della replicabilità in altri contesti"
        ]
    },
    "comparative": {
        "name": "Focus Comparativo",
        "focus": "differenze e pattern territoriali",
        "description": "Analizza differenze e pattern. Confronta tra regioni, tipi di scuola, ordini scolastici.",
        "target_audience": "analisti, uffici scolastici regionali",
        "word_count": "900-1300 parole",
        "sections": ["Matrice Comparativa", "Pattern Territoriali", "Gap Analysis", "Cluster Identificati"],
        "requirements": [
            "Almeno 1 tabella o matrice comparativa",
            "Dati quantitativi per ogni confronto",
            "Identificazione esplicita di outlier (positivi e negativi)"
        ]
    },
    "impact": {
        "name": "Focus Impatto",
        "focus": "efficacia e sostenibilità",
        "description": "Valuta efficacia e sostenibilità. Cerca evidenze di risultati, anche indiretti.",
        "target_audience": "valutatori, enti finanziatori, decisori",
        "word_count": "700-1000 parole",
        "sections": ["Evidenze di Impatto", "Analisi Costi-Benefici", "Sostenibilità", "Raccomandazioni"],
        "requirements": [
            "KPI o metriche citate dal PTOF (se disponibili)",
            "Valutazione delle risorse impiegate vs benefici",
            "Distinzione tra pratiche replicabili e contesto-specifiche"
        ]
    },
    "operational": {
        "name": "Focus Operativo",
        "focus": "raccomandazioni attuabili",
        "description": "Sintesi per l'azione immediata. Raccomandazioni concrete e realizzabili.",
        "target_audience": "dirigenti scolastici, docenti referenti orientamento",
        "word_count": "600-900 parole",
        "sections": ["Quick Wins (azioni immediate)", "Azioni a Medio Termine", "Roadmap suggerita"],
        "requirements": [
            "Almeno 5 raccomandazioni concrete e attuabili",
            "Per ogni azione: prerequisiti, risorse stimate, priorità",
            "Ordine di priorità basato su rapporto impatto/effort"
        ]
    }
}


def get_profile_instructions(profile: str) -> str:
    """Get detailed instructions for a specific profile.

    Fase 2.2: Istruzioni potenziate per ogni profilo.

    Args:
        profile: Profile name (overview, innovative, comparative, impact, operational)

    Returns:
        Formatted instruction block for the profile
    """
    config = PROFILE_STRUCTURES.get(profile, PROFILE_STRUCTURES["overview"])

    lines = [
        f"PROFILO: {config['name'].upper()}",
        f"Focus: {config['focus']}",
        f"Pubblico target: {config['target_audience']}",
        f"Lunghezza indicativa: {config['word_count']}",
        "",
        f"Descrizione: {config['description']}",
        "",
        "Sezioni suggerite:",
    ]

    for section in config["sections"]:
        lines.append(f"  - {section}")

    if config["requirements"]:
        lines.append("")
        lines.append("REQUISITI SPECIFICI:")
        for req in config["requirements"]:
            lines.append(f"  * {req}")

    return "\n".join(lines)


def compose_prompt(*components: str) -> str:
    """Compose a system prompt from modular components.

    Args:
        *components: Variable number of prompt component strings

    Returns:
        Combined prompt with proper spacing
    """
    # Filtra componenti vuoti e unisci con doppio newline
    valid_components = [c.strip() for c in components if c and c.strip()]
    return "\n\n".join(valid_components)


# =============================================================================
# Template strutture per tipo di report
# =============================================================================

REPORT_STRUCTURES = {
    "school": """
STRUTTURA OBBLIGATORIA:
1) CONTESTO: tipo scuola, territorio, caratteristiche distintive
2) PUNTI DI FORZA: iniziative efficaci, metodologie innovative, partnership attive
3) AREE DI SVILUPPO: cosa potrebbe essere potenziato (senza toni critici)
4) CONCLUSIONI: sintesi del profilo orientativo della scuola

Includi citazioni dal PTOF per dare concretezza.
Se mancano dati per una sezione, indica 'Dati non disponibili' senza inventare.
""",

    "regional": """
STRUTTURA OBBLIGATORIA:
1) PANORAMA REGIONALE: caratteristiche del territorio e del sistema scolastico
2) CONFRONTO TRA PROVINCE: differenze significative, aree di eccellenza
3) SCUOLE DI RIFERIMENTO: 3-5 esempi concreti con Nome (Codice) e motivazione
4) TREND E INNOVAZIONI: pratiche emergenti, collaborazioni territoriali
5) RACCOMANDAZIONI REGIONALI: 2-3 suggerimenti per policy maker locali

Usa dati quantitativi quando disponibili (N scuole, % distribuzione).
""",

    "national": """
STRUTTURA OBBLIGATORIA:
1) QUADRO GENERALE: stato dell'orientamento in Italia, numeri chiave
2) ANALISI TERRITORIALE: differenze Nord/Centro/Sud, regioni virtuose
3) GAP ANALYSIS: divari territoriali, aree sottorappresentate
4) BEST PRACTICES NAZIONALI: 5-7 esempi eccellenti con Nome (Codice)
5) TREND EMERGENTI: innovazioni, nuove metodologie, temi in crescita
6) RACCOMANDAZIONI SISTEMICHE: 3-4 suggerimenti per policy maker nazionali

Mantieni equilibrio tra analisi critica e valorizzazione delle eccellenze.
""",

    "thematic": """
STRUTTURA MONOGRAFICA AI-DRIVEN (OBBLIGATORIA):

1) 📋 EXECUTIVE SUMMARY: Visione d'insieme sintetica (numeri chiave, scuole, trend dominante).

2) 🧭 DIRETTRICI STRATEGICHE: Come le scuole interpretano questo tema?
   *   [ISTRUZIONE]: Cerca attività con categoria '⚙️ Azioni di Sistema e Governance' per capire la visione organizzativa.
   *   [ISTRUZIONE]: Cerca '🌈 Buone Pratiche per l'Inclusione' per evidenziare strategie inclusive trasversali.

3) 🔗 INTERSEZIONI MULTIDISCIPLINARI: Analisi narrativa di come questo tema si intreccia con altri ambiti.
   *   [ISTRUZIONE]: Usa '🤝 Partnership e Collaborazioni' per mostrare l'apertura verso università, aziende ed enti.

4) 🛠️ METODOLOGIE E STRUMENTI: Focus operativo (laboratori, tecnologie, reti, PCTO).
   *   [ISTRUZIONE]: Attingi a '📚 Metodologie Didattiche Innovative' per descrivere il "come".

5) 🏫 CASI RILEVANTI: Menzione esplicita delle scuole e pratiche più significative.
   *   [ISTRUZIONE]: Dai priorità assoluta a '🎯 Progetti e Attività Esemplari' come casi studio principali.

6) 🗺️ ANALISI TERRITORIALE:
   *   [ISTRUZIONE]: Valorizza '🗺️ Esperienze Territoriali Significative' per descrivere il radicamento locale.
   - Se REGIONALE: Confronta le PROVINCE. Chi è più attivo? Ci sono specificità provinciali (es. Roma vs Viterbo)?
   - Se NAZIONALE: Confronta le REGIONI o macro-aree (Nord/Centro/Sud).

FORMATO NARRATIVO OBBLIGATORIO:
Scrivi in modo narrativo e discorsivo. Collega le idee con connettivi logici.
METTI SEMPRE IN GRASSETTO:
- Regioni e Province (es. **Lazio**, **provincia di Viterbo**)
- Nomi delle Scuole e relativi codici (es. **Liceo Fermi (RMPC0000)**)
DIVIETO ASSOLUTO: NON creare elenchi puntati o numerati nel corpo del testo.
Nessuna lista. Nessun bullet point. Solo prosa narrativa continua.
""",
    # Alias per i template di merge (usano la stessa struttura monografica)
    "thematic_group_merge": "USA LA STRUTTURA 'thematic' DEFINITA SOPRA.",
    "thematic_summary_merge": "USA LA STRUTTURA 'thematic' DEFINITA SOPRA.",

    "thematic_regional": """
STRUTTURA OBBLIGATORIA (ANALISI REGIONALE):
1) SINTESI REGIONALE: cosa emerge su questo tema nella regione
2) QUADRO TEMATICO: sotto-temi, approcci ricorrenti, specificità locali
3) LETTURA PROVINCIALE: differenze tra province, aree di eccellenza
4) DATI CHIAVE: N scuole coinvolte, distribuzione per provincia/tipo
5) CONCLUSIONI OPERATIVE: cosa si può imparare, raccomandazioni per la regione

IMPORTANTE: I dati sono di UNA SOLA REGIONE. NON fare confronti con altre regioni.
Concentrati sulle differenze INTERNE (tra province, tipi di scuola, ordini).
""",
}


def get_report_structure(report_type: str, is_regional: bool = False) -> str:
    """Get the structure template for a report type.

    Args:
        report_type: Type of report
        is_regional: Whether this is a regional-scoped report

    Returns:
        Structure template string
    """
    if report_type == "thematic" and is_regional:
        return REPORT_STRUCTURES.get("thematic_regional", "")
    return REPORT_STRUCTURES.get(report_type, "")
