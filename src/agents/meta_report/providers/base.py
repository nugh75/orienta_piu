"""Base provider interface for LLM calls."""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

# Fase 2.1, 2.2, 2.3: Import componenti modulari
try:
    from ..prompts.examples import get_example_block
    from ..prompts.components import get_profile_instructions, PROFILE_STRUCTURES, REPORT_STRUCTURES
    PROMPTS_AVAILABLE = True
except ImportError:
    PROMPTS_AVAILABLE = False


class ProviderError(Exception):
    """Error from LLM provider."""
    pass


@dataclass
class LLMResponse:
    """Response from LLM provider."""
    content: str
    model: str
    provider: str
    tokens_used: Optional[int] = None
    cost: Optional[float] = None
    # Fase 1.1: Tracking codici validati
    invalid_codes: list[str] = field(default_factory=list)
    validation_applied: bool = False


class BaseProvider(ABC):
    """Abstract base class for LLM providers."""

    name: str = "base"
    
    # Default recommended chunk size (subclasses can override)
    recommended_chunk_size: int = 30

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is configured and available."""
        pass

    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
        """Generate text from prompt."""
        pass

    def generate_best_practices(
        self,
        analysis_data: dict,
        report_type: str = "school",
        prompt_profile: str = "overview",
        valid_school_codes: Optional[set[str]] = None
    ) -> LLMResponse:
        """Generate activities report from analysis data.

        Args:
            analysis_data: Data to analyze
            report_type: Type of report to generate
            prompt_profile: Focus profile for the report
            valid_school_codes: Optional set of valid school codes for validation

        Returns:
            LLMResponse with content and validation info
        """
        system_prompt = self._get_system_prompt(report_type, prompt_profile)
        user_prompt = self._format_analysis_prompt(analysis_data, report_type, prompt_profile)
        response = self.generate(user_prompt, system_prompt)

        # Fase 1.1: Validazione post-generazione dei codici scuola
        if valid_school_codes:
            validated_content, invalid_codes = self.validate_school_codes(
                response.content,
                valid_school_codes
            )
            response.content = validated_content
            response.invalid_codes = invalid_codes
            response.validation_applied = True

            if invalid_codes:
                print(f"[validation] Found {len(invalid_codes)} invalid school codes: {invalid_codes[:5]}...")

        return response

    def validate_school_codes(
        self,
        content: str,
        valid_codes: set[str]
    ) -> tuple[str, list[str]]:
        """Validate and flag invalid school codes in the report.

        Fase 1.1: Post-generation validation to catch hallucinated codes.

        Args:
            content: Generated report content
            valid_codes: Set of valid school codes from the data

        Returns:
            Tuple of (cleaned content, list of invalid codes found)
        """
        # Pattern per codici meccanografici italiani:
        # 2 lettere regione + 2 lettere tipo istituto + 5-7 caratteri alfanumerici
        # Es: RMPS12345X, MIIS00900T, TOPS01000B
        pattern = r'\b([A-Z]{2}[A-Z]{2}[A-Z0-9]{5,7})\b'

        found_codes = set(re.findall(pattern, content))
        invalid_codes = [code for code in found_codes if code not in valid_codes]

        if invalid_codes:
            for code in invalid_codes:
                # Sostituisci con segnalazione visibile
                content = content.replace(
                    f"({code})",
                    f"(~~{code}~~ [codice non verificato])"
                )

        return content, invalid_codes

    def extract_valid_codes_from_data(self, analysis_data: dict) -> set[str]:
        """Extract valid school codes from analysis data.

        Helper method to build the set of valid codes from the input data.

        Args:
            analysis_data: The analysis data passed to generate_best_practices

        Returns:
            Set of valid school codes found in the data
        """
        valid_codes = set()

        # Estrai da sample_cases
        for case in analysis_data.get("sample_cases", []):
            # Cerca codice in vari formati possibili
            if "(" in case and ")" in case:
                # Estrai da formato "Nome Scuola (CODICE)"
                match = re.search(r'\(([A-Z]{2}[A-Z]{2}[A-Z0-9]{5,7})\)', case)
                if match:
                    valid_codes.add(match.group(1))

        # Estrai da practices/casi strutturati
        for practice in analysis_data.get("practices", []):
            if isinstance(practice, dict):
                school = practice.get("scuola", {}) or practice.get("school", {})
                code = (
                    school.get("codice") or
                    school.get("codice_meccanografico") or
                    school.get("code")
                )
                if code:
                    valid_codes.add(code)

        # Estrai da school_info
        school_info = analysis_data.get("school_info", {})
        if school_info:
            code = school_info.get("code") or school_info.get("codice_meccanografico")
            if code:
                valid_codes.add(code)

        # Estrai da school_code diretto
        if analysis_data.get("school_code"):
            valid_codes.add(analysis_data["school_code"])

        # Estrai da top_schools_by_province
        for province_schools in analysis_data.get("top_schools_by_province", {}).values():
            for school in province_schools:
                if isinstance(school, dict) and school.get("code"):
                    valid_codes.add(school["code"])

        # Estrai da top_10_schools
        for school in analysis_data.get("top_10_schools", []):
            if isinstance(school, dict) and school.get("code"):
                valid_codes.add(school["code"])

        return valid_codes

    def _get_system_prompt(self, report_type: str, prompt_profile: str) -> str:
        """Get system prompt based on report type."""
        # Fase 1.3: Chiarimento istruzioni Markdown per tipo di report
        # Report completi (standalone) -> usano titoli Markdown
        # Chunk parziali (da integrare) -> NO titoli Markdown
        report_types_with_headers = {
            "school", "regional", "national", "thematic",
            "thematic_chunk_merge", "thematic_group_merge",
            "thematic_school_analysis",
            "thematic_intro", "thematic_territorial_analysis", "thematic_conclusion",
            "thematic_category_type_synthesis", "thematic_similar_schools"
        }
        report_types_without_headers = {
            "thematic_chunk", "thematic_group_chunk",
            "thematic_summary_merge", "regional_summary_merge"
        }

        if report_type in report_types_with_headers:
            markdown_instruction = (
                "FORMATO: Usa titoli Markdown per strutturare il report:\n"
                "- # per il titolo principale\n"
                "- ## per sezioni maggiori\n"
                "- ### per sottosezioni\n"
                "NON usare blocchi di codice (```)."
            )
        elif report_type in report_types_without_headers:
            markdown_instruction = (
                "FORMATO: Questo è un output PARZIALE che verrà integrato.\n"
                "- NON usare titoli Markdown (#, ##, ###)\n"
                "- NON usare righe in grassetto che fungono da titoli\n"
                "- Scrivi paragrafi continui e discorsivi\n"
                "- NON usare blocchi di codice (```)."
            )
        else:
            markdown_instruction = "NON usare blocchi di codice (```)."

        # System prompt condensato per ottimizzare token (modelli locali 27B)
        base = (
            "Analista orientamento scolastico italiano. Stile: accademico, formale, conciso.\n\n"
            f"{markdown_instruction}\n\n"
            "REGOLE:\n"
            "- Solo prosa narrativa (MAI elenchi puntati/numerati nel corpo)\n"
            "- Citazioni: Nome Scuola (CODICE) - es: Liceo Volta (RMPS12345X)\n"
            "- Cita SOLO scuole nei dati forniti, NO invenzioni\n"
            "- Connettivi: inoltre, tuttavia, in particolare, analogamente\n"
            "- NO superlativi, NO ripetizioni"
        )

        specifics = {
            "school": (
                "Genera un report sulle attivita di orientamento per una singola scuola.\n"
                "STRUTTURA OBBLIGATORIA:\n"
                "1) CONTESTO: tipo scuola, territorio, caratteristiche distintive\n"
                "2) PUNTI DI FORZA: iniziative efficaci, metodologie innovative, partnership attive\n"
                "3) AREE DI SVILUPPO: cosa potrebbe essere potenziato (senza toni critici)\n"
                "4) CONCLUSIONI: sintesi del profilo orientativo della scuola\n\n"
                "Includi citazioni dal PTOF per dare concretezza. "
                "Se mancano dati per una sezione, indica 'Dati non disponibili' senza inventare."
            ),
            "regional": (
                "Genera un report sulle attivita di orientamento a livello regionale.\n"
                "STRUTTURA OBBLIGATORIA:\n"
                "1) PANORAMA REGIONALE: caratteristiche del territorio e del sistema scolastico\n"
                "2) CONFRONTO TRA PROVINCE: differenze significative, aree di eccellenza\n"
                "3) SCUOLE DI RIFERIMENTO: 3-5 esempi concreti con Nome (Codice) e motivazione\n"
                "4) TREND E INNOVAZIONI: pratiche emergenti, collaborazioni territoriali\n"
                "5) RACCOMANDAZIONI REGIONALI: 2-3 suggerimenti per policy maker locali\n\n"
                "Usa dati quantitativi quando disponibili (N scuole, % distribuzione)."
            ),
            "national": (
                "Genera un report sulle attivita di orientamento a livello nazionale.\n"
                "STRUTTURA OBBLIGATORIA:\n"
                "1) QUADRO GENERALE: stato dell'orientamento in Italia, numeri chiave\n"
                "2) ANALISI TERRITORIALE: differenze Nord/Centro/Sud, regioni virtuose\n"
                "3) GAP ANALYSIS: divari territoriali, aree sottorappresentate\n"
                "4) BEST PRACTICES NAZIONALI: 5-7 esempi eccellenti con Nome (Codice)\n"
                "5) TREND EMERGENTI: innovazioni, nuove metodologie, temi in crescita\n"
                "6) RACCOMANDAZIONI SISTEMICHE: 3-4 suggerimenti per policy maker nazionali\n\n"
                "Mantieni equilibrio tra analisi critica e valorizzazione delle eccellenze."
            ),
            "thematic": (
                "Genera un report su una specifica dimensione dell'orientamento. "
                "Esplora in profondita questo aspetto: perche e importante, come le scuole lo affrontano, "
                "quali approcci innovativi emergono, cosa possono imparare le altre scuole. "
                "Usa esempi concreti e racconta le attivita in modo narrativo."
            ),
            "thematic_chunk": (
                "Produci note analitiche su un sottoinsieme di casi. "
                "Sii conciso, descrivi pattern ricorrenti e segnala attivita interessanti con contesto essenziale. "
                "Non generare un report completo."
            ),
            "thematic_chunk_merge": (
                "Integra note parziali e dati aggregati in un report finale coerente e accademico. "
                "Evidenzia pattern comuni, segnali quantitativi ricorrenti e implicazioni operative."
            ),
            # Prompt per modelli locali 27B - mantiene struttura ma riduce verbosità
            "thematic_group_chunk": (
                "Analizza le attività e identifica pattern chiave. "
                "Scrivi 3-4 paragrafi narrativi densi. "
                "Cita 3-5 scuole con Nome (Codice). "
                "Max 500 parole. NO elenchi puntati."
            ),
            "thematic_group_merge": (
                "Scrivi un REPORT MONOGRAFICO completo integrando le analisi parziali.\n\n"
                "STRUTTURA OBBLIGATORIA (usa ### per i titoli):\n"
                "### Executive Summary (100 parole)\n"
                "### Direttrici Strategiche (200 parole, cita 5+ scuole)\n"
                "### Intersezioni Multidisciplinari (150 parole)\n"
                "### Metodologie e Strumenti (150 parole)\n"
                "### Casi Rilevanti (200 parole, cita esempi specifici)\n"
                "### Analisi Territoriale (150 parole per provincia)\n"
                "### Sintesi (150 parole)\n\n"
                "REGOLE: Prosa narrativa, grassetto per **Scuole**, **Province**, **Regioni**. NO elenchi puntati."
            ),
            "thematic_summary_merge": (
                "Sintetizza le analisi dei temi in un quadro unitario strutturato.\n"
                "STRUTTURA OBBLIGATORIA:\n"
                "1) TREND PRINCIPALI: 3-5 tendenze chiave emerse dall'analisi\n"
                "2) DIFFERENZE TERRITORIALI: variazioni Nord/Centro/Sud, regioni di eccellenza\n"
                "3) TEMI CONSOLIDATI vs EMERGENTI: quali pratiche sono mature, quali in sviluppo\n"
                "4) RACCOMANDAZIONI: 2-3 suggerimenti operativi per policy maker o scuole\n\n"
                "Scrivi in modo discorsivo, evita elenchi puntati lunghi. "
                "Se citi una scuola, usa sempre Nome Scuola (Codice) dai dati forniti."
            ),
            "thematic_summary_merge_regional": (
                "Sintetizza le analisi dei temi per una SINGOLA REGIONE.\n"
                "STRUTTURA OBBLIGATORIA:\n"
                "1) TREND REGIONALI: 3-5 tendenze chiave nella regione analizzata\n"
                "2) DIFFERENZE PROVINCIALI: variazioni tra province, aree di eccellenza locale\n"
                "3) TEMI CONSOLIDATI vs EMERGENTI: quali pratiche sono mature, quali in sviluppo\n"
                "4) RACCOMANDAZIONI REGIONALI: 2-3 suggerimenti per USR e scuole della regione\n\n"
                "IMPORTANTE: NON fare confronti con altre regioni (i dati sono solo di questa regione). "
                "Concentrati sulle differenze INTERNE alla regione (tra province, tipi di scuola). "
                "Scrivi in modo discorsivo. Se citi una scuola, usa Nome Scuola (Codice)."
            ),
            "regional_summary_merge": (
                "Sintetizza le analisi tematiche per una regione.\n"
                "STRUTTURA OBBLIGATORIA:\n"
                "1) IDENTITÀ REGIONALE: cosa caratterizza l'orientamento in questa regione\n"
                "2) TEMI DOMINANTI: quali ambiti sono più sviluppati e perché\n"
                "3) PUNTI DI FORZA: eccellenze regionali con esempi Nome (Codice)\n"
                "4) AREE DI SVILUPPO: temi meno presenti, opportunità di crescita\n\n"
                "Scrivi in modo discorsivo, evita elenchi. NON usare titoli markdown."
            ),
        }

        # Componi il prompt finale
        specific = specifics.get(report_type, specifics['school'])
        prompt = f"{base}\n\n{specific}"

        # Fase 2.1: Aggiungi few-shot examples se disponibili
        if PROMPTS_AVAILABLE:
            example_block = get_example_block(report_type)
            if example_block:
                prompt += example_block

        return prompt

    def _format_analysis_prompt(self, analysis_data: dict, report_type: str, prompt_profile: str) -> str:
        """Format analysis data into a prompt."""
        import json

        # Fase 2.2: Usa istruzioni potenziate se disponibili
        if PROMPTS_AVAILABLE:
            focus_line = get_profile_instructions(prompt_profile)
        else:
            # Fallback alle istruzioni base
            profile_focus = {
                "overview": (
                    "FOCUS OVERVIEW: Quadro complessivo e bilanciato.\n"
                    "- Copri tutti gli aspetti principali senza approfondire troppo\n"
                    "- Bilancia punti di forza e aree di sviluppo\n"
                    "- Adatto a: dirigenti, stakeholder generici"
                ),
                "innovative": (
                    "FOCUS INNOVAZIONE: Evidenzia solo le pratiche più originali.\n"
                    "- Cerca approcci non convenzionali, sperimentazioni, primi in Italia\n"
                    "- Spiega PERCHÉ sono innovative (cosa cambia rispetto alla prassi)\n"
                    "- Ignora pratiche standard anche se ben fatte\n"
                    "- Adatto a: ricercatori, policy maker, scuole che vogliono innovare"
                ),
                "comparative": (
                    "FOCUS COMPARATIVO: Analizza differenze e pattern.\n"
                    "- Confronta tra regioni, tipi di scuola, ordini scolastici\n"
                    "- Identifica cluster e outlier\n"
                    "- Usa dati quantitativi per supportare i confronti\n"
                    "- Adatto a: analisti, uffici scolastici regionali"
                ),
                "impact": (
                    "FOCUS IMPATTO: Valuta efficacia e sostenibilità.\n"
                    "- Cerca evidenze di risultati (anche indiretti)\n"
                    "- Valuta risorse necessarie vs benefici\n"
                    "- Identifica pratiche replicabili vs contesto-specifiche\n"
                    "- Adatto a: valutatori, enti finanziatori"
                ),
                "operational": (
                    "FOCUS OPERATIVO: Sintesi per l'azione immediata.\n"
                    "- Raccomandazioni concrete e realizzabili\n"
                    "- Prioritizza per urgenza/impatto\n"
                    "- Indica risorse, tempi, prerequisiti\n"
                    "- Adatto a: dirigenti scolastici, docenti referenti"
                ),
            }
            focus_line = profile_focus.get(prompt_profile, profile_focus["overview"])
        filters = analysis_data.get("filters") or {}
        filters_line = f"Filtri attivi: {filters}" if filters else "Filtri attivi: nessuno"

        structure = (
            "Struttura obbligatoria:\n"
            "1) SINTESI INIZIALE: 2-3 frasi che catturano l'essenza\n"
            "2) ANALISI: perché le pratiche sono interessanti/innovative\n"
            "3) NARRAZIONE: casi distinti raggruppati per tema o territorio\n"
            "4) DATI: statistiche chiave (N scuole, distribuzione, frequenze)\n"
            "5) CONCLUSIONI: implicazioni e raccomandazioni\n\n"
            "IMPORTANTE: Basa l'analisi SOLO sui dati forniti. "
            "Se i dati sono limitati, indica chiaramente il perimetro senza inventare."
        )

        thematic_structure = (
            "Struttura obbligatoria:\n"
            "1) SINTESI: cosa emerge complessivamente su questo tema\n"
            "2) QUADRO TEMATICO: sotto-temi, approcci ricorrenti, perché questo tema conta\n"
            "3) LETTURA TERRITORIALE: differenze Nord/Centro/Sud, regioni di eccellenza\n"
            "4) DATI CHIAVE: N scuole coinvolte, distribuzione per regione/tipo\n"
            "5) CONCLUSIONI OPERATIVE: cosa si può imparare, raccomandazioni\n\n"
            "IMPORTANTE: Scrivi in modo narrativo e discorsivo. "
            "NON creare inventari o elenchi lunghi. Il dettaglio attività è in tabella CSV separata."
        )

        thematic_structure_regional = (
            "Struttura obbligatoria (ANALISI REGIONALE):\n"
            "1) SINTESI REGIONALE: cosa emerge su questo tema nella regione\n"
            "2) QUADRO TEMATICO: sotto-temi, approcci ricorrenti, specificità locali\n"
            "3) LETTURA PROVINCIALE: differenze tra province, aree di eccellenza\n"
            "4) DATI CHIAVE: N scuole coinvolte, distribuzione per provincia/tipo\n"
            "5) CONCLUSIONI OPERATIVE: cosa si può imparare, raccomandazioni per la regione\n\n"
            "IMPORTANTE: I dati sono di UNA SOLA REGIONE. NON fare confronti con altre regioni. "
            "Concentrati sulle differenze INTERNE (tra province, tipi di scuola, ordini). "
            "NON creare inventari o elenchi lunghi."
        )

        if report_type == "thematic_chunk":
            dimension_name = analysis_data.get("dimension_name", "questa dimensione")
            return f"""Analizza il seguente sottoinsieme di casi per la dimensione "{dimension_name}":

Profilo: {prompt_profile}
{filters_line}
Focus: {focus_line}

DATI CHUNK:
{json.dumps(analysis_data, indent=2, ensure_ascii=False)}

Output richiesto (note sintetiche, NON report finale):
- Pattern ricorrenti (2-5 punti)
- Temi emergenti e loro declinazione territoriale (max 2-3 esempi)
- Indicatori numerici principali (conteggi per categorie/regioni)
- Spunti narr hookup (brevi frasi guida per la sintesi finale)
IMPORTANTE: non creare inventari o liste estese di casi.
"""

        if report_type == "thematic_chunk_merge":
            dimension_name = analysis_data.get("dimension_name", "questa dimensione")
            # Usa struttura regionale se c'è filtro regione
            is_regional = bool(filters.get("regione"))
            active_structure = thematic_structure_regional if is_regional else thematic_structure
            return f"""Integra le note dei chunk e i dati aggregati per produrre il report finale sulla dimensione "{dimension_name}":

Profilo: {prompt_profile}
{filters_line}
Focus: {focus_line}

DATI AGGREGATI:
{json.dumps(analysis_data, indent=2, ensure_ascii=False)}

Scrivi un report NARRATIVO e DISCORSIVO (non una lista di punti) che includa:

# {dimension_name}

{active_structure}

IMPORTANTE: Scrivi in modo narrativo e coinvolgente, come un articolo di approfondimento. Evita elenchi puntati lunghi.
NON includere inventari completi: il dettaglio attivita e in tabella separata.
"""

        if report_type == "thematic_group_chunk":
            dimension_name = analysis_data.get("dimension_name", "questa dimensione")
            theme = analysis_data.get("theme", "tema")
            scope = analysis_data.get("scope", "national")
            region = analysis_data.get("region")
            # Determina se è regionale da scope O da filtro regione
            is_regional = (scope == "region" and region) or bool(filters.get("regione"))
            if is_regional:
                region_name = region or filters.get("regione", "questa regione")
                scope_line = f"Ambito: regionale ({region_name})"
                territorial_note = "Differenze tra PROVINCE (i dati sono di una sola regione)"
            else:
                scope_line = "Ambito: nazionale"
                territorial_note = "Differenze territoriali rilevanti (se presenti)"
            # Prompt condensato per modelli locali - usa dati compressi se disponibili
            compressed_data = analysis_data.get("sample_cases", "")
            if isinstance(compressed_data, list):
                compressed_data = "\n".join(str(c)[:200] for c in compressed_data[:20])

            return f"""TEMA: {dimension_name} - {theme}
{scope_line}
CASI: {analysis_data.get('cases_count', 0)}

DATI:
{compressed_data}

COMPITO: Identifica 3 pattern chiave e 2-3 scuole virtuose (con codice).
FORMATO: 3 paragrafi narrativi (4-5 frasi). Max 400 parole. NO elenchi.
"""

        if report_type == "thematic_group_merge":
            dimension_name = analysis_data.get("dimension_name", "questa dimensione")
            theme = analysis_data.get("theme", "tema")
            scope = analysis_data.get("scope", "national")
            cases_count = analysis_data.get("cases_count", 0)
            schools_count = analysis_data.get("schools_count", 0)
            detail_level = analysis_data.get("detail_level", "medio")
            region = analysis_data.get("region")

            # Determina se è regionale da scope O da filtro regione
            is_regional = (scope == "region" and region) or bool(filters.get("regione"))
            if is_regional:
                region_name = region or filters.get("regione", "questa regione")
                scope_line = f"Ambito: regionale ({region_name})"
                territorial_note = "Indica dove sono localizzate le attività emerse nel campione."
            else:
                scope_line = "Ambito: nazionale"
                territorial_note = "Indica la provenienza geografica delle attività citate."
            
            # Usa la struttura definita centralmente in components.py (Monografica AI-Driven)
            # Nota: Recuperiamo 'thematic' perché 'thematic_group_merge' è solo un alias
            structure_template = REPORT_STRUCTURES.get("thematic", "")
            
            # Calcolo percentuale citazione dinamica
            if schools_count <= 20:
                citation_pct = "100%"
                citation_note = "CITA TUTTE LE SCUOLE SENZA ECCEZIONI."
            elif schools_count <= 30:
                citation_pct = "90%"
                citation_note = f"CITA ALMENO IL 90% DELLE SCUOLE (minimo {int(schools_count * 0.9)} su {schools_count})."
            elif schools_count <= 50:
                citation_pct = "80%"
                citation_note = f"CITA ALMENO L'80% DELLE SCUOLE (minimo {int(schools_count * 0.8)} su {schools_count})."
            elif schools_count <= 100:
                citation_pct = "70%"
                citation_note = f"CITA ALMENO IL 70% DELLE SCUOLE (minimo {int(schools_count * 0.7)} su {schools_count})."
            else:
                citation_pct = "50%"
                citation_note = "Cita un'ampia rappresentanza di scuole (almeno il 50%)."

            # Prompt per merge - struttura completa per report monografico
            chunk_notes = analysis_data.get("chunk_notes", [])
            chunk_text = "\n\n---\n\n".join(chunk_notes) if chunk_notes else "Nessuna nota disponibile"

            # Calcola quante scuole citare (proporzionale)
            min_citations = max(8, min(schools_count, int(schools_count * 0.6)))

            return f"""REPORT MONOGRAFICO: {dimension_name} nel {region_name if is_regional else 'territorio nazionale'}
{scope_line}
Statistiche: {cases_count} attività, {schools_count} scuole

ANALISI PARZIALI DA INTEGRARE:
{chunk_text}

COMPITO: Scrivi UN SOLO PARAGRAFO introduttivo (max 80-100 parole) che riassuma concretamente di cosa trattano le attività in questa categoria.

REGOLE:
- Sii specifico e basati SOLO sui dati forniti.
- NON usare titoli o sottotitoli.
- NON usare elenchi puntati.
- NON usare frasi generiche o "fluff" (es. "L'analisi rivela...", "scenario in evoluzione").
- Vai dritto al punto: "Le scuole si concentrano su...", "I progetti principali riguardano...".
"""

        if report_type == "thematic_summary_merge":
            dimension_name = analysis_data.get("dimension_name", "questa dimensione")
            structure_template = REPORT_STRUCTURES.get("thematic", "")
            
            # Istruzioni differenziate per region vs national
            is_regional = bool(filters.get("regione"))
            territorial_instruction = (
                "evidenziando specificità provinciali." if is_regional 
                else "evidenziando differenze regionali (Nord/Centro/Sud)."
            )

            return f"""Redigi un EXECUTIVE SUMMARY conclusivo per il report sulla dimensione "{dimension_name}".

Profilo: {prompt_profile}
{filters_line}

DATI (Analisi Tematiche):
{json.dumps(analysis_data, indent=2, ensure_ascii=False)}

OBIETTIVO:
Fornire una visione d'insieme strategica e concisa (max 1-2 pagine).
Non ripetere i dettagli dei singoli progetti (già presenti nell'analisi), ma sintetizza i TREND e le LINEE GUIDA emerse, {territorial_instruction}.

STRUTTURA (Semplificata):
1. Visione d'Insieme (Trend principali)
2. Punti di Forza e Criticità
3. Raccomandazioni Strategiche

FORMATO:
- Prosa narrativa concisa.
- Niente elenchi puntati.
- Grassetto per entità geografiche.
"""

        if report_type == "regional_summary_merge":
            dimension_name = analysis_data.get("dimension_name", "questa dimensione")
            region = analysis_data.get("region", "Regione")
            return f"""Sintetizza le analisi tematiche per la regione "{region}" nella dimensione "{dimension_name}":

Profilo: {prompt_profile}
{filters_line}
Focus: {focus_line}

DATI REGIONALI:
{json.dumps(analysis_data, indent=2, ensure_ascii=False)}

Output richiesto:
- 1-2 paragrafi di sintesi, senza elenchi lunghi
- Metti in evidenza temi dominanti e specificita regionali
Nota: non usare titoli Markdown (#, ##, ###) o righe in grassetto che fungono da titoli.
"""

        if report_type == "school":
            return f"""Analizza i seguenti dati PTOF e genera un report sulle attivita:

Profilo: {prompt_profile}
{filters_line}
Focus: {focus_line}

DATI ANALISI:
{json.dumps(analysis_data, indent=2, ensure_ascii=False)}

{structure}
"""

        elif report_type == "regional":
            return f"""Analizza i seguenti dati aggregati a livello regionale:

Profilo: {prompt_profile}
{filters_line}
Focus: {focus_line}

DATI REGIONALI:
{json.dumps(analysis_data, indent=2, ensure_ascii=False)}

{structure}
"""

        elif report_type == "national":
            return f"""Analizza i seguenti dati aggregati a livello nazionale:

Profilo: {prompt_profile}
{filters_line}
Focus: {focus_line}

DATI NAZIONALI:
{json.dumps(analysis_data, indent=2, ensure_ascii=False)}

{structure}
"""

        if report_type == "thematic_category_school_analysis":
            school_name = analysis_data.get("school_name", "Scuola")
            category = analysis_data.get("category", "Categoria")
            dimension = analysis_data.get("dimension", "Dimensione")
            school_level = analysis_data.get("school_level", "Ordine")

            return f"""Analizza le attività della scuola "{school_name}" per la categoria: "{category}".

Profilo: {prompt_profile}
Filtri Attivi: Dimensione="{dimension}", Ordine="{school_level}"

DATI ATTIVITÀ (Grezzi):
{json.dumps(analysis_data.get("practices", []), indent=2, ensure_ascii=False)}

COMPITO:
1. Identifica SOLO le attività pertinenti alla categoria "{category}" E alla dimensione "{dimension}" (escludi altri ordini scolastici se specificato).
2. Scrivi un breve paragrafo narrativo che descriva queste attività.
3. Se un'attività appartiene ANCHE ad altre categorie (es. "{dimension}" e "BES/Inclusione"), DEVI ESPLICITARE questa connessione nel testo. Spiega il legame.

REGOLE:
- Se NON ci sono attività pertinenti per questa categoria, restituisci UNA STRINGA VUOTA.
- NON usare titoli Markdown (saranno aggiunti esternamente).
- Cita i titoli delle attività tra virgolette.
- Stile conciso e diretto.
"""

        if report_type == "thematic_intro":
            dimension_name = analysis_data.get("dimension_name", "questa dimensione")
            # Analysis data now contains the full text of the report so far or specific context
            report_context = analysis_data.get("report_context", "")
            return f"""Scrivi l'INTRODUZIONE per il report sulla dimensione "{dimension_name}".

Profilo: {prompt_profile}
{filters_line}

CONTESTO REPORT (Bozza parziale):
{report_context[:4000]}... (troncato per brevità)

COMPITO:
Scrivi un'introduzione di alto livello (max 300 parole).
- Anticipa i temi chiave emersi nel report.
- Stile narrativo e coinvolgente.
- NON inventare dati non presenti nel contesto.
"""

        if report_type == "thematic_territorial_analysis":
            dimension_name = analysis_data.get("dimension_name", "questa dimensione")
            scope = analysis_data.get("scope", "national")
            report_context = analysis_data.get("report_context", "")
            return f"""Scrivi l'ANALISI TERRITORIALE per il report sulla dimensione "{dimension_name}".

Profilo: {prompt_profile}
Ambito: {scope}
{filters_line}

CONTESTO REPORT (Bozza parziale):
{report_context[:8000]}... (troncato)

STATISTICHE TERRITORIALI:
{json.dumps(analysis_data.get("territorial_stats", {}), indent=2, ensure_ascii=False)}

COMPITO:
Analizza le differenze territoriali basandoti SU QUANTO GIA SCRITTO nel report.
- Dove si concentrano le eccellenze?
- Ci sono specificità provinciali/regionali evidenti nel testo?
- Max 400 parole.
"""

        if report_type == "thematic_conclusion":
            dimension_name = analysis_data.get("dimension_name", "questa dimensione")
            report_context = analysis_data.get("report_context", "")
            return f"""Scrivi le CONCLUSIONI per il report sulla dimensione "{dimension_name}".

Profilo: {prompt_profile}
{filters_line}

CONTESTO REPORT (Completo):
{report_context[:8000]}... (troncato)

COMPITO:
Scrivi una sintesi finale descrittiva (max 300 parole).
- Basati interamente su quanto emerso nel report.
- Riassumi le tendenze principali osservate.
- Evidenzia i pattern comuni e le peculiarità emerse.

IMPORTANTE:
- Questa è un'analisi ESPLORATIVA e DESCRITTIVA.
- NON dare giudizi di valore, valutazioni o raccomandazioni.
- NON suggerire miglioramenti o azioni da intraprendere.
- Limitati a descrivere ciò che è emerso dall'analisi.
"""

        elif report_type == "thematic_category_type_synthesis":
            category = analysis_data.get("category", "")
            school_type = analysis_data.get("school_type", "")
            content = analysis_data.get("content", "")
            school_count = analysis_data.get("school_count", 0)
            
            return f"""Sintetizza le attività di orientamento per gli istituti **{school_type}** nella categoria "{category}".

Numero di scuole {school_type}: {school_count}

CONTENUTO DA SINTETIZZARE:
{content[:6000]}

COMPITO:
Genera un paragrafo di sintesi (max 120 parole) che evidenzi:
1. Caratteristiche distintive dell'approccio di questi istituti
2. Tendenze comuni tra le scuole
3. Punti di forza specifici del tipo di istituto

IMPORTANTE:
- Scrivi in modo narrativo, NON usare elenchi puntati.
- Fai riferimento a esempi concreti dal contenuto.
- Non citare codici meccanografici, usa solo nomi di scuole se necessario.
- NON dare raccomandazioni o giudizi, solo descrizione.
"""

        elif report_type == "thematic_similar_schools":
            category = analysis_data.get("category", "")
            schools_data = analysis_data.get("schools_data", "")
            
            return f"""Identifica gruppi di scuole con attività simili nella categoria "{category}".

CONTENUTO DEL REPORT (già scritto):
{schools_data[:8000]}

COMPITO:
Basandoti sul contenuto già scritto nel report, identifica gruppi di scuole che presentano approcci o focus simili (max 200 parole).

Per ogni gruppo identificato, scrivi:
- Il tema/focus comune che accomuna le scuole
- L'elenco delle scuole che condividono questo approccio

Esempio di formato:
**Focus su [tema]**: [Scuola A], [Scuola B], [Scuola C] condividono un approccio orientato a [descrizione breve].

IMPORTANTE:
- Identifica 2-4 gruppi significativi di scuole con affinità.
- Descrivi SOLO le similarità osservate, non suggerire collaborazioni.
- Usa nomi delle scuole, non codici meccanografici.
- Scrivi in modo descrittivo e oggettivo.
- NON dare raccomandazioni o suggerimenti operativi.
"""

        else:  # thematic
            dimension_name = analysis_data.get("dimension_name", "questa dimensione")
            return f"""Analizza i seguenti dati sulla dimensione "{dimension_name}":

{prompt_profile}
{filters_line}
{focus_line}

DATI TEMATICI:
{json.dumps(analysis_data, indent=2, ensure_ascii=False)}

Scrivi un report NARRATIVO e DISCORSIVO (non una lista di punti) che includa:

# {dimension_name}

{thematic_structure}

IMPORTANTE: Scrivi in modo narrativo e coinvolgente.
"""
