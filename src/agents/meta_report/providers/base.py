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

    def generate_best_practices(self, analysis_data: dict, report_type: str = "school") -> LLMResponse:
        """Generate best practices report from analysis data."""
        system_prompt = self._get_system_prompt(report_type)
        user_prompt = self._format_analysis_prompt(analysis_data, report_type)
        return self.generate(user_prompt, system_prompt)

    def _get_system_prompt(self, report_type: str) -> str:
        """Get system prompt based on report type."""
        base = (
            "Sei un esperto di orientamento scolastico italiano che scrive per dirigenti, docenti e famiglie. "
            "Il tuo compito e produrre report narrativi, scorrevoli e coinvolgenti sulle buone pratiche di orientamento. "
            "Scrivi in italiano con un tono professionale ma accessibile, evitando elenchi puntati eccessivi. "
            "Usa paragrafi discorsivi, collega le idee con transizioni fluide, e racconta le pratiche come storie di successo. "
            "NON usare blocchi di codice (```) nel report. Scrivi direttamente in markdown semplice con titoli (#, ##, ###)."
        )

        specifics = {
            "school": (
                "Genera un report narrativo sulle buone pratiche di orientamento per una singola scuola. "
                "Racconta la storia dell'orientamento in questa scuola: cosa la rende speciale, "
                "quali iniziative hanno funzionato, come supportano gli studenti nelle scelte future. "
                "Includi citazioni dal PTOF per dare concretezza."
            ),
            "regional": (
                "Genera un report narrativo sulle buone pratiche di orientamento a livello regionale. "
                "Descrivi il panorama dell'orientamento nella regione: quali sono le tendenze dominanti, "
                "quali scuole si distinguono e perche, come il territorio influenza le pratiche. "
                "Usa esempi concreti per illustrare i pattern."
            ),
            "national": (
                "Genera un report narrativo sulle buone pratiche di orientamento a livello nazionale. "
                "Offri una panoramica del sistema italiano dell'orientamento: cosa funziona bene, "
                "quali innovazioni stanno emergendo, come variano le pratiche tra Nord, Centro e Sud. "
                "Racconta le eccellenze con esempi concreti."
            ),
            "thematic": (
                "Genera un report narrativo su una specifica dimensione dell'orientamento. "
                "Esplora in profondita questo aspetto: perche e importante, come le scuole lo affrontano, "
                "quali approcci innovativi emergono, cosa possono imparare le altre scuole. "
                "Usa esempi concreti e racconta le storie di successo."
            ),
        }

        return f"{base}\n\n{specifics.get(report_type, specifics['school'])}"

    def _format_analysis_prompt(self, analysis_data: dict, report_type: str) -> str:
        """Format analysis data into a prompt."""
        import json

        if report_type == "school":
            return f"""Analizza i seguenti dati PTOF e genera un report sulle buone pratiche:

DATI ANALISI:
{json.dumps(analysis_data, indent=2, ensure_ascii=False)}

Genera un report markdown strutturato con:
1. Executive Summary (2-3 frasi)
2. Pratiche di Eccellenza (con citazioni dal PTOF se disponibili)
3. Punti di Forza per Dimensione
4. Raccomandazioni
"""

        elif report_type == "regional":
            return f"""Analizza i seguenti dati aggregati a livello regionale:

DATI REGIONALI:
{json.dumps(analysis_data, indent=2, ensure_ascii=False)}

Genera un report markdown strutturato con:
1. Overview Regionale
2. Top 5 Pratiche Piu' Diffuse
3. Eccellenze Provinciali
4. Pattern e Trend
5. Raccomandazioni per il Territorio
"""

        elif report_type == "national":
            return f"""Analizza i seguenti dati aggregati a livello nazionale:

DATI NAZIONALI:
{json.dumps(analysis_data, indent=2, ensure_ascii=False)}

Genera un report markdown strutturato con:
1. Executive Summary Nazionale
2. Top 10 Pratiche Piu' Diffuse
3. Analisi per Macro-Area Geografica
4. Trend e Innovazioni
5. Raccomandazioni Strategiche
"""

        else:  # thematic
            dimension_name = analysis_data.get("dimension_name", "questa dimensione")
            return f"""Analizza i seguenti dati sulla dimensione "{dimension_name}":

DATI TEMATICI:
{json.dumps(analysis_data, indent=2, ensure_ascii=False)}

Scrivi un report NARRATIVO e DISCORSIVO (non una lista di punti) che includa:

# {dimension_name}

## Introduzione
Un paragrafo che spiega l'importanza di questa dimensione nell'orientamento scolastico.

## Il Panorama Attuale
Descrivi come le scuole italiane affrontano questa dimensione, basandoti sui dati. Usa paragrafi discorsivi.

## Storie di Eccellenza
Racconta 2-3 esempi concreti di scuole che si distinguono, spiegando cosa fanno di speciale.

## Lezioni Apprese
Cosa possono imparare le altre scuole? Quali sono gli ingredienti del successo?

## Prospettive Future
Come potrebbero evolvere le pratiche in questa area?

IMPORTANTE: Scrivi in modo narrativo e coinvolgente, come un articolo di approfondimento. Evita elenchi puntati lunghi.
"""
