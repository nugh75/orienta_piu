"""Base provider interface for LLM calls."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


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


class BaseProvider(ABC):
    """Abstract base class for LLM providers."""

    name: str = "base"

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
        prompt_profile: str = "overview"
    ) -> LLMResponse:
        """Generate activities report from analysis data."""
        system_prompt = self._get_system_prompt(report_type, prompt_profile)
        user_prompt = self._format_analysis_prompt(analysis_data, report_type, prompt_profile)
        return self.generate(user_prompt, system_prompt)

    def _get_system_prompt(self, report_type: str, prompt_profile: str) -> str:
        """Get system prompt based on report type."""
        base = (
            "Sei un esperto di orientamento scolastico italiano. "
            "Scrivi in italiano con stile accademico, registro formale e lessico metodologico. "
            "Produci report analitici e sintetici sulle attivita di orientamento, con argomentazioni chiare e coerenti. "
            "Evita toni celebrativi e superlativi. "
            "NON usare blocchi di codice (```) nel report. Scrivi in markdown semplice con titoli (#, ##, ###).\n\n"
            "REGOLE CITAZIONI:\n"
            "- Cita SOLO scuole presenti nei dati forniti (sample_cases o chunk_notes)\n"
            "- Usa SEMPRE il formato: Nome Scuola (CODICE) - es: Liceo Galilei (RMPS12345X)\n"
            "- NON inventare codici meccanografici: se non hai il codice, non citare la scuola\n"
            "- I codici italiani hanno formato: 2 lettere regione + 2 lettere tipo + 5-6 caratteri alfanumerici"
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
            "thematic_group_chunk": (
                "Analizza questo gruppo di attività per estrarre dettagli significativi. "
                "Scrivi dei PARAGRAFI DENSI E NARRATIVI che descrivano cosa fanno le scuole, citando esempi specifici con Nome Scuola (Codice). "
                "VIETATO USARE ELENCHI PUNTATI. "
                "Focalizzati su: metodologie originali, partnership, impatto sugli studenti. "
                "Questo testo servirà come base per un capitolo approfondito."
            ),
            "thematic_group_merge": (
                "Usa le note parziali (chunk) per scrivere un SAGGIO APPROFONDITO E ARTICOLATO sul tema.\\n\\n"
                "STRUTTURA OBBLIGATORIA (8-12 paragrafi):\\n\\n"
                "1) INTRODUZIONE ESTESA: Contesto e rilevanza del tema.\\n"
                "2) ANALISI DEI CLUSTER (corpo centrale): Sviluppa un discorso fluido che colleghi le varie esperienze. Raggruppa per affinità semantica.\\n"
                "3) APPROFONDIMENTI: Dedica paragrafi specifici ai progetti più innovativi citati nelle note.\\n"
                "4) CONCLUSIONI RAGIONATE.\\n\\n"
                "REGOLE FERREE:\\n"
                "- VIETATO USARE ELENCHI PUNTATI O NUMERATI (tranne per i titoli dei paragrafi).\\n"
                "- Scrivi tutto in forma discorsiva, usando connettivi logici (inoltre, tuttavia, in particolare...).\\n"
                "- Cita MOLTISSIME scuole (Nome Scuola - CODICE) per dare concretezza.\\n"
                "- Non usare le categorie amministrative come nomi dei cluster.\\n"
                "- Lunghezza minima: 1000 parole."
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

        return f"{base}\n\n{specifics.get(report_type, specifics['school'])}"

    def _format_analysis_prompt(self, analysis_data: dict, report_type: str, prompt_profile: str) -> str:
        """Format analysis data into a prompt."""
        import json

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
            return f"""Analizza il seguente sottoinsieme di casi per il tema "{theme}" nella dimensione "{dimension_name}":

Profilo: {prompt_profile}
{filters_line}
Focus: {focus_line}
{scope_line}

DATI CHUNK:
{json.dumps(analysis_data, indent=2, ensure_ascii=False)}

Output richiesto (note sintetiche, NON report finale):
- Pattern ricorrenti e come si manifestano nelle scuole
- {territorial_note}
- 2-4 esempi puntuali citando sempre Nome Scuola (Codice)
IMPORTANTE: non creare inventari o liste lunghe. Non usare titoli Markdown (#, ##, ###) o righe in grassetto che fungono da titoli.
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
            
            return f"""Produci un'analisi DETTAGLIATA e COMPLETA del tema "{theme}" nella dimensione "{dimension_name}":

Profilo: {prompt_profile}
{filters_line}
Focus: {focus_line}
{scope_line}

STATISTICHE TOTALI: {cases_count} attività in {schools_count} scuole
CAMPIONE ANALIZZATO: I dati seguenti sono un campione sistematico (1 caso ogni 5, ~20%) delle attività totali.
LIVELLO DETTAGLIO RICHIESTO: {detail_level}

DATI DEL CAMPIONE:
{json.dumps(analysis_data, indent=2, ensure_ascii=False)}

OUTPUT RICHIESTO:

1) INTRODUZIONE:
   - Importanza del tema e numeri chiave.
   - Disclaimer: "L'analisi si basa su un campione rappresentativo delle attività censite nel PTOF."

2) CLUSTER DI ATTIVITÀ (adatta la lunghezza al livello di dettaglio richiesto):
   - Raggruppa le attività per similarità di CONTENUTO e METODOLOGIA.
   - ATTENZIONE: I cluster NON devono corrispondere alle categorie amministrative ("Progetti Esemplari", "Inclusione", ecc.), ma riflettere cosa fanno concretamente le scuole (es. "Laboratori STEM", "Orientamento Universitario", "Orto didattico").
   - Per ogni cluster: descrivi pattern + cita ESEMPI CONCRETI (Nome Scuola - Codice).
   - Se livello "molto dettagliato": crea 4-5 cluster e cita 10-15 esempi totali.
   - Se livello "sintetico": bastano 1 cluster e 2-3 esempi.

3) DISTRIBUZIONE GEOGRAFICA (Nel campione):
   - {territorial_note}
   - EVITA categoricamente confronti del tipo "La provincia X è più virtuosa di Y" o "C'è un gap territoriale", poiché i dati sono parziali e relativi al solo campione disponibile. Limitati a descrivere il campione.

4) CONCLUSIONI: Pattern emergenti e spunti di interesse, senza generalizzazioni statistiche eccessive.

IMPORTANTE:
- Cita SEMPRE le scuole nel formato Nome Scuola (CODICE).
- Scrivi in modo discorsivo.
- NON usare titoli Markdown (#, ##, ###).
- NON usare le categorie amministrative come nomi dei cluster.
"""

        if report_type == "thematic_summary_merge":
            dimension_name = analysis_data.get("dimension_name", "questa dimensione")
            # Usa istruzioni diverse per scope regionale vs nazionale
            is_regional = bool(filters.get("regione"))
            if is_regional:
                region_name = filters.get("regione", "questa regione")
                output_instructions = (
                    f"Output richiesto (ANALISI REGIONALE per {region_name}):\n"
                    "- 1-2 paragrafi di sintesi, senza elenchi lunghi\n"
                    "- Evidenzia temi dominanti e differenze tra PROVINCE (NON tra regioni)\n"
                    "- NON fare confronti con altre regioni, i dati sono solo di questa regione"
                )
            else:
                output_instructions = (
                    "Output richiesto:\n"
                    "- 1-2 paragrafi di sintesi, senza elenchi lunghi\n"
                    "- Evidenzia temi dominanti e differenze territoriali (Nord/Centro/Sud)"
                )
            return f"""Sintetizza le analisi tematiche della dimensione "{dimension_name}":

Profilo: {prompt_profile}
{filters_line}
Focus: {focus_line}

DATI TEMATICI:
{json.dumps(analysis_data, indent=2, ensure_ascii=False)}

{output_instructions}
Nota: non usare titoli Markdown (#, ##, ###) o righe in grassetto che fungono da titoli.
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

        else:  # thematic
            dimension_name = analysis_data.get("dimension_name", "questa dimensione")
            return f"""Analizza i seguenti dati sulla dimensione "{dimension_name}":

Profilo: {prompt_profile}
{filters_line}
Focus: {focus_line}

DATI TEMATICI:
{json.dumps(analysis_data, indent=2, ensure_ascii=False)}

Scrivi un report NARRATIVO e DISCORSIVO (non una lista di punti) che includa:

# {dimension_name}

{thematic_structure}

IMPORTANTE: Scrivi in modo narrativo e coinvolgente, come un articolo di approfondimento. Evita elenchi puntati lunghi.
NON includere inventari completi: il dettaglio attivita e in tabella separata.
"""
