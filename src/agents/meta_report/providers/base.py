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
            "NON usare blocchi di codice (```) nel report. Scrivi in markdown semplice con titoli (#, ##, ###)."
        )

        specifics = {
            "school": (
                "Genera un report sulle attivita di orientamento per una singola scuola. "
                "Evidenzia cosa funziona, quali iniziative sono interessanti e in che modo supportano gli studenti. "
                "Includi citazioni dal PTOF per dare concretezza."
            ),
            "regional": (
                "Genera un report sulle attivita di orientamento a livello regionale. "
                "Descrivi il panorama dell'orientamento nella regione: quali sono le tendenze dominanti, "
                "quali scuole presentano attivita interessanti e perche, come il territorio influenza le attivita. "
                "Usa esempi concreti per illustrare i pattern."
            ),
            "national": (
                "Genera un report sulle attivita di orientamento a livello nazionale. "
                "Offri una panoramica del sistema italiano dell'orientamento: cosa funziona bene, "
                "quali innovazioni stanno emergendo, come variano le attivita tra Nord, Centro e Sud. "
                "Racconta attivita interessanti con esempi concreti."
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
                "Analizza un sottoinsieme di casi per un tema specifico. "
                "Sii conciso, descrivi pattern e segnala esempi mirati citando sempre Nome Scuola (Codice). "
                "Non generare inventari o liste lunghe."
            ),
            "thematic_group_merge": (
                "Integra note parziali e dati aggregati in una sintesi narrativa del tema. "
                "Se citi una scuola, usa sempre Nome Scuola (Codice). "
                "Evita inventari o liste estese."
            ),
            "thematic_summary_merge": (
                "Sintetizza le analisi dei temi in un quadro unitario. "
                "Evidenzia i temi principali e le differenze territoriali senza elenchi lunghi. "
                "Se citi una scuola, usa sempre Nome Scuola (Codice)."
            ),
            "regional_summary_merge": (
                "Sintetizza le analisi tematiche per una regione. "
                "Metti in luce i temi dominanti e i tratti distintivi regionali. "
                "Se citi una scuola, usa sempre Nome Scuola (Codice)."
            ),
        }

        return f"{base}\n\n{specifics.get(report_type, specifics['school'])}"

    def _format_analysis_prompt(self, analysis_data: dict, report_type: str, prompt_profile: str) -> str:
        """Format analysis data into a prompt."""
        import json

        profile_focus = {
            "overview": "Offrire un quadro complessivo e bilanciato, senza inventari completi.",
            "innovative": "Evidenziare pratiche interessanti e innovative, spiegando perche lo sono.",
            "comparative": "Mettere in luce differenze, variabilita e pattern ricorrenti.",
            "impact": "Valutare impatto e fattibilita delle pratiche interessanti.",
            "operational": "Fornire una sintesi operativa e raccomandazioni realistiche.",
        }

        focus_line = profile_focus.get(prompt_profile, profile_focus["overview"])
        filters = analysis_data.get("filters") or {}
        filters_line = f"Filtri attivi: {filters}" if filters else "Filtri attivi: nessuno"

        structure = (
            "Struttura obbligatoria:\n"
            "1) Sintesi\n"
            "2) Analisi (perche sono interessanti/innovative)\n"
            "3) Sezione narrativa (casi distinti, raggruppati in gruppi coerenti)\n"
            "4) Sezione numerica (quanti casi, dove ricorrono, frequenze)\n"
            "5) Conclusioni\n"
            "Se i dati disponibili non consentono 50 casi, dichiara il limite senza inventare."
        )

        thematic_structure = (
            "Struttura obbligatoria:\n"
            "1) Sintesi\n"
            "2) Quadro tematico (sotto-temi, approcci ricorrenti, perche conta)\n"
            "3) Lettura territoriale (differenze tra regioni/aree, fattori contestuali)\n"
            "4) Evidenze quantitative sintetiche (conteggi per regioni/categorie)\n"
            "5) Conclusioni operative\n"
            "Nota: NON creare inventari completi o elenchi lunghi; il dettaglio attivita e in tabella separata."
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
            return f"""Integra le note dei chunk e i dati aggregati per produrre il report finale sulla dimensione "{dimension_name}":

Profilo: {prompt_profile}
{filters_line}
Focus: {focus_line}

DATI AGGREGATI:
{json.dumps(analysis_data, indent=2, ensure_ascii=False)}

Scrivi un report NARRATIVO e DISCORSIVO (non una lista di punti) che includa:

# {dimension_name}

{thematic_structure}

IMPORTANTE: Scrivi in modo narrativo e coinvolgente, come un articolo di approfondimento. Evita elenchi puntati lunghi.
NON includere inventari completi: il dettaglio attivita e in tabella separata.
"""

        if report_type == "thematic_group_chunk":
            dimension_name = analysis_data.get("dimension_name", "questa dimensione")
            theme = analysis_data.get("theme", "tema")
            scope = analysis_data.get("scope", "national")
            region = analysis_data.get("region")
            scope_line = f"Ambito: regionale ({region})" if scope == "region" and region else "Ambito: nazionale"
            return f"""Analizza il seguente sottoinsieme di casi per il tema "{theme}" nella dimensione "{dimension_name}":

Profilo: {prompt_profile}
{filters_line}
Focus: {focus_line}
{scope_line}

DATI CHUNK:
{json.dumps(analysis_data, indent=2, ensure_ascii=False)}

Output richiesto (note sintetiche, NON report finale):
- Pattern ricorrenti e come si manifestano nelle scuole
- Differenze territoriali rilevanti (se presenti)
- 2-4 esempi puntuali citando sempre Nome Scuola (Codice)
IMPORTANTE: non creare inventari o liste lunghe. Non usare titoli Markdown (#, ##, ###) o righe in grassetto che fungono da titoli.
"""

        if report_type == "thematic_group_merge":
            dimension_name = analysis_data.get("dimension_name", "questa dimensione")
            theme = analysis_data.get("theme", "tema")
            scope = analysis_data.get("scope", "national")
            region = analysis_data.get("region")
            scope_line = f"Ambito: regionale ({region})" if scope == "region" and region else "Ambito: nazionale"
            return f"""Integra note e dati aggregati per produrre una sintesi narrativa del tema "{theme}" nella dimensione "{dimension_name}":

Profilo: {prompt_profile}
{filters_line}
Focus: {focus_line}
{scope_line}

DATI TEMATICI:
{json.dumps(analysis_data, indent=2, ensure_ascii=False)}

Output richiesto:
- 1-2 paragrafi discorsivi, senza elenchi lunghi
- Se citi una scuola, usa sempre Nome Scuola (Codice)
Nota: non usare titoli Markdown (#, ##, ###) o righe in grassetto che fungono da titoli.
"""

        if report_type == "thematic_summary_merge":
            dimension_name = analysis_data.get("dimension_name", "questa dimensione")
            return f"""Sintetizza le analisi tematiche della dimensione "{dimension_name}":

Profilo: {prompt_profile}
{filters_line}
Focus: {focus_line}

DATI TEMATICI:
{json.dumps(analysis_data, indent=2, ensure_ascii=False)}

Output richiesto:
- 1-2 paragrafi di sintesi, senza elenchi lunghi
- Evidenzia temi dominanti e differenze territoriali
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
