"""Test suite per validare i prompt e i componenti del meta report.

Fase 4.2: Verifica che i prompt producano output validi e consistenti.
"""

import pytest
import re
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Aggiungi il path del progetto
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.meta_report.providers.base import BaseProvider, LLMResponse


class MockProvider(BaseProvider):
    """Provider mock per i test."""

    name = "mock"

    def is_available(self) -> bool:
        return True

    def generate(self, prompt: str, system_prompt: str = None) -> LLMResponse:
        return LLMResponse(
            content="Test response",
            model="mock-model",
            provider="mock"
        )


class TestSchoolCodeValidation:
    """Test per la validazione dei codici meccanografici."""

    def test_valid_code_pattern(self):
        """Verifica che il pattern riconosca codici validi."""
        pattern = r'\b([A-Z]{2}[A-Z]{2}[A-Z0-9]{5,6})\b'

        valid_codes = [
            "RMPS12345X",  # Roma - Liceo Scientifico
            "MIIS00900T",  # Milano - Istituto Superiore
            "TOPS01000B",  # Torino - Liceo Scientifico
            "NAIS00700R",  # Napoli - Istituto Superiore
            "BOIS01900X",  # Bologna - Istituto Superiore
            "VIIS00200X",  # Vicenza
            "LCPS02000T",  # Lecco
        ]

        for code in valid_codes:
            match = re.match(pattern, code)
            assert match is not None, f"Codice valido non riconosciuto: {code}"
            assert match.group(1) == code

    def test_invalid_code_pattern(self):
        """Verifica che il pattern non riconosca codici invalidi."""
        pattern = r'\b([A-Z]{2}[A-Z]{2}[A-Z0-9]{5,6})\b'

        invalid_codes = [
            "XXXX",        # Troppo corto
            "rm12345",     # Minuscolo
            "RMPS123",     # Troppo corto (7 caratteri totali)
            "1234567890",  # Solo numeri
            "RMPS12345678", # Troppo lungo
        ]

        for code in invalid_codes:
            match = re.match(pattern, code)
            if match:
                # Se c'è un match, non deve essere il codice completo
                assert match.group(1) != code, f"Codice invalido riconosciuto: {code}"

    def test_validate_school_codes_method(self):
        """Testa il metodo validate_school_codes del provider."""
        provider = MockProvider()

        valid_codes = {"RMPS12345X", "MIIS00900T"}
        content = """
        Il Liceo Galilei (RMPS12345X) eccelle in orientamento.
        L'IIS Fermi (MIIS00900T) ha sviluppato un progetto.
        Il Liceo Fantasia (ABCD99999Z) ha fatto bene.
        """

        validated, invalid = provider.validate_school_codes(content, valid_codes)

        assert "ABCD99999Z" in invalid
        assert len(invalid) == 1
        assert "[codice non verificato]" in validated

    def test_extract_valid_codes_from_data(self):
        """Testa l'estrazione dei codici validi dai dati."""
        provider = MockProvider()

        data = {
            "school_code": "RMPS12345X",
            "school_info": {"code": "MIIS00900T"},
            "top_10_schools": [
                {"code": "TOPS01000B", "name": "Test"},
                {"code": "NAIS00700R", "name": "Test2"},
            ],
        }

        codes = provider.extract_valid_codes_from_data(data)

        assert "RMPS12345X" in codes
        assert "MIIS00900T" in codes
        assert "TOPS01000B" in codes
        assert "NAIS00700R" in codes


class TestSystemPrompts:
    """Test per i system prompt."""

    def test_system_prompt_contains_citation_rules(self):
        """Verifica che tutti i system prompt contengano regole citazioni."""
        provider = MockProvider()

        report_types = [
            "school", "regional", "national", "thematic",
            "thematic_chunk", "thematic_group_chunk"
        ]

        for report_type in report_types:
            prompt = provider._get_system_prompt(report_type, "overview")

            assert "Nome Scuola" in prompt or "Nome (Codice)" in prompt, \
                f"Regola citazione mancante in {report_type}"
            assert "NON inventare" in prompt.lower() or "non inventare" in prompt.lower(), \
                f"Regola anti-invenzione mancante in {report_type}"

    def test_system_prompt_markdown_rules(self):
        """Verifica che le regole Markdown siano coerenti."""
        provider = MockProvider()

        # Report che DEVONO avere titoli Markdown
        with_headers = ["school", "regional", "national", "thematic_group_merge"]
        for report_type in with_headers:
            prompt = provider._get_system_prompt(report_type, "overview")
            assert "Usa titoli Markdown" in prompt or "# per" in prompt, \
                f"{report_type} dovrebbe permettere titoli Markdown"

        # Report che NON devono avere titoli Markdown
        without_headers = ["thematic_group_chunk", "thematic_summary_merge"]
        for report_type in without_headers:
            prompt = provider._get_system_prompt(report_type, "overview")
            assert "NON usare titoli" in prompt or "contenuto PARZIALE" in prompt, \
                f"{report_type} non dovrebbe permettere titoli Markdown"


class TestPromptProfiles:
    """Test per i profili dei prompt."""

    def test_all_profiles_generate_different_prompts(self):
        """Verifica che ogni profilo generi prompt diversi."""
        provider = MockProvider()

        profiles = ["overview", "innovative", "comparative", "impact", "operational"]
        prompts = []

        data = {"dimension_name": "test", "filters": {}}

        for profile in profiles:
            prompt = provider._format_analysis_prompt(data, "thematic", profile)
            prompts.append(prompt)

        # Tutti i prompt devono essere diversi tra loro
        unique_prompts = set(prompts)
        assert len(unique_prompts) == len(profiles), \
            "I profili devono generare prompt diversi"

    def test_profile_focus_in_prompt(self):
        """Verifica che il focus del profilo sia presente nel prompt."""
        provider = MockProvider()

        data = {"dimension_name": "test", "filters": {}}

        # Verifica che ogni profilo menzioni il suo focus
        expectations = {
            "innovative": ["innovazione", "originali", "non convenzionali"],
            "comparative": ["comparativo", "differenze", "pattern"],
            "impact": ["impatto", "efficacia", "sostenibilità"],
            "operational": ["operativo", "raccomandazioni", "azione"],
        }

        for profile, keywords in expectations.items():
            prompt = provider._format_analysis_prompt(data, "thematic", profile)
            prompt_lower = prompt.lower()

            found_any = any(kw.lower() in prompt_lower for kw in keywords)
            assert found_any, \
                f"Profilo '{profile}' non contiene keyword attese: {keywords}"


class TestPromptExamples:
    """Test per i few-shot examples."""

    def test_examples_exist(self):
        """Verifica che esistano esempi per i tipi principali."""
        from agents.meta_report.prompts.examples import EXAMPLES, get_example

        required_types = ["school", "regional", "national", "thematic"]

        for report_type in required_types:
            assert report_type in EXAMPLES, f"Manca esempio per {report_type}"
            example = get_example(report_type, "good")
            assert example, f"Esempio 'good' vuoto per {report_type}"
            assert len(example) > 100, f"Esempio troppo corto per {report_type}"

    def test_examples_contain_school_codes(self):
        """Verifica che gli esempi contengano codici scuola validi."""
        from agents.meta_report.prompts.examples import get_example

        code_pattern = r'\([A-Z]{2}[A-Z]{2}[A-Z0-9]{5,6}\)'

        examples_with_codes = ["regional", "national", "thematic"]

        for report_type in examples_with_codes:
            example = get_example(report_type, "good")
            matches = re.findall(code_pattern, example)
            assert len(matches) > 0, \
                f"Esempio '{report_type}' non contiene codici scuola"


class TestPromptComponents:
    """Test per i componenti modulari dei prompt."""

    def test_components_exist(self):
        """Verifica che i componenti principali esistano."""
        from agents.meta_report.prompts.components import (
            COMMON_RULES,
            CITATION_RULES,
            NARRATIVE_STYLE,
            NO_MARKDOWN_HEADERS,
            WITH_MARKDOWN_HEADERS,
        )

        assert len(COMMON_RULES) > 50
        assert len(CITATION_RULES) > 50
        assert len(NARRATIVE_STYLE) > 50
        assert len(NO_MARKDOWN_HEADERS) > 20
        assert len(WITH_MARKDOWN_HEADERS) > 20

    def test_compose_prompt(self):
        """Testa la composizione dei prompt."""
        from agents.meta_report.prompts.components import compose_prompt

        result = compose_prompt("First", "Second", "", "Third")

        assert "First" in result
        assert "Second" in result
        assert "Third" in result
        # I componenti vuoti non devono essere inclusi
        assert "\n\n\n" not in result

    def test_profile_structures_complete(self):
        """Verifica che tutti i profili abbiano strutture complete."""
        from agents.meta_report.prompts.components import PROFILE_STRUCTURES

        required_profiles = ["overview", "innovative", "comparative", "impact", "operational"]
        required_fields = ["name", "focus", "description", "target_audience", "word_count", "sections"]

        for profile in required_profiles:
            assert profile in PROFILE_STRUCTURES, f"Manca profilo {profile}"

            config = PROFILE_STRUCTURES[profile]
            for field in required_fields:
                assert field in config, f"Manca campo '{field}' in profilo '{profile}'"


class TestThematicReporter:
    """Test per il ThematicReporter."""

    def test_semantic_chunk_cases_region(self):
        """Testa il chunking semantico per regione."""
        from agents.meta_report.reporters.thematic import ThematicReporter

        # Mock del provider
        mock_provider = MagicMock()
        reporter = ThematicReporter(mock_provider)

        cases = [
            {"scuola": {"regione": "Lombardia", "codice": "MIIS001"}},
            {"scuola": {"regione": "Lombardia", "codice": "MIIS002"}},
            {"scuola": {"regione": "Lazio", "codice": "RMIS001"}},
            {"scuola": {"regione": "Lazio", "codice": "RMIS002"}},
            {"scuola": {"regione": "Campania", "codice": "NAIS001"}},
        ]

        chunks = reporter._semantic_chunk_cases(cases, chunk_size=3, strategy="region")

        # Verifica che i casi della stessa regione siano insieme
        for chunk in chunks:
            regions = set(c.get("scuola", {}).get("regione") for c in chunk)
            # Se il chunk ha casi di una sola regione o è l'ultimo
            # (che può contenere regioni miste per bilanciamento), è ok
            assert len(regions) <= 2, "Chunk con troppe regioni miste"

    def test_stratified_sample_coverage(self):
        """Testa che il sampling stratificato copra tutte le regioni."""
        from agents.meta_report.reporters.thematic import ThematicReporter

        mock_provider = MagicMock()
        reporter = ThematicReporter(mock_provider)

        # Crea casi con distribuzione sbilanciata
        cases = []
        for i in range(50):
            cases.append({"scuola": {"regione": "Lombardia", "codice": f"MI{i:04d}"}})
        for i in range(5):
            cases.append({"scuola": {"regione": "Molise", "codice": f"CB{i:04d}"}})
        for i in range(3):
            cases.append({"scuola": {"regione": "Basilicata", "codice": f"MT{i:04d}"}})

        sampled = reporter._stratified_sample(cases, min_per_stratum=2, max_total=20)

        # Verifica che tutte le regioni siano rappresentate
        sampled_regions = set(c.get("scuola", {}).get("regione") for c in sampled)
        assert "Lombardia" in sampled_regions
        assert "Molise" in sampled_regions
        assert "Basilicata" in sampled_regions

    def test_extract_patterns_from_chunk(self):
        """Testa l'estrazione di pattern dal contenuto del chunk."""
        from agents.meta_report.reporters.thematic import ThematicReporter

        mock_provider = MagicMock()
        reporter = ThematicReporter(mock_provider)

        content = """
        Emerge un pattern interessante nelle scuole del Nord.
        Il Liceo Galilei (RMPS12345X) ha sviluppato un approccio innovativo.
        Si nota una tendenza verso la digitalizzazione.
        """

        patterns = reporter._extract_patterns_from_chunk(content)

        assert len(patterns) <= 3
        assert len(patterns) > 0


class TestLLMResponseValidation:
    """Test per la validazione delle risposte LLM."""

    def test_llm_response_has_validation_fields(self):
        """Verifica che LLMResponse abbia i campi di validazione."""
        response = LLMResponse(
            content="Test",
            model="test",
            provider="test"
        )

        assert hasattr(response, 'invalid_codes')
        assert hasattr(response, 'validation_applied')
        assert response.invalid_codes == []
        assert response.validation_applied is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
