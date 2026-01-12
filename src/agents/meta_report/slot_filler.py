"""Slot filler for skeleton-first report generation.

This module handles filling placeholders in the report skeleton
with LLM-generated content.
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .providers import get_provider_for_slot, BaseProvider
from .prompts.components import format_slot_prompt, COMMON_RULES, NARRATIVE_STYLE
from .skeleton import SkeletonBuilder, CATEGORY_ORDER


logger = logging.getLogger(__name__)


@dataclass
class SlotFillerConfig:
    """Configuration for slot filler."""
    provider_school: str = "ollama"
    provider_synthesis: str = "openrouter"
    model_school: Optional[str] = None
    model_synthesis: Optional[str] = None
    dim: str = "orientamento"  # Dimensione tematica del report
    region: str = ""  # Regione geografica (es: Marche)
    

class SlotFiller:
    """Fills skeleton slots with LLM-generated content."""
    
    def __init__(
        self,
        builder: SkeletonBuilder,
        config: SlotFillerConfig,
        output_path: Path,
    ):
        self.builder = builder
        self.config = config
        self.output_path = output_path
        self.generated_content: dict[str, str] = {}
        
    def fill_all_slots(self) -> str:
        """Fill all slots in the skeleton and return the final content."""
        # Get skeleton and slot info
        skeleton = self.builder.generate_skeleton()
        slot_info = self.builder.get_slot_info()
        
        # Write initial skeleton
        self.output_path.write_text(skeleton, encoding="utf-8")
        logger.info(f"[skeleton] Wrote initial skeleton to {self.output_path}")
        
        # Phase 1: School × Category analysis
        logger.info("[fill] Phase 1: School analysis...")
        self._fill_school_slots(slot_info)
        
        # Phase 2: Category intros
        logger.info("[fill] Phase 2: Category intros...")
        self._fill_category_intro_slots(slot_info)
        
        # Phase 3: Synthesis by school type
        logger.info("[fill] Phase 3: Synthesis by school type...")
        self._fill_synthesis_slots(slot_info)
        
        # Phase 4: Comparisons
        logger.info("[fill] Phase 4: Comparisons...")
        self._fill_comparison_slots(slot_info)
        
        # Phase 5: Intro and conclusions
        logger.info("[fill] Phase 5: Intro and conclusions...")
        self._fill_global_slots(slot_info)
        
        # Replace all slots in skeleton
        final_content = self._replace_slots(skeleton)
        
        # Write final content
        self.output_path.write_text(final_content, encoding="utf-8")
        logger.info(f"[fill] Completed! Written to {self.output_path}")
        
        return final_content
    
    def _get_provider(self, slot_type: str) -> BaseProvider:
        """Get the appropriate provider for a slot type."""
        return get_provider_for_slot(
            slot_type,
            provider_school=self.config.provider_school,
            provider_synthesis=self.config.provider_synthesis,
            model_school=self.config.model_school,
            model_synthesis=self.config.model_synthesis,
        )
    
    def _fill_school_slots(self, slot_info: dict) -> None:
        """Fill school analysis slots."""
        school_slots = [
            (name, info) for name, info in slot_info.items()
            if info["type"] == "school_analysis"
        ]
        
        total = len(school_slots)
        for i, (slot_name, info) in enumerate(school_slots, 1):
            ctx = info["context"]
            activities = ctx["activities"]
            school_code = ctx.get("code", "")
            school_name = ctx.get("school_name", "Scuola sconosciuta")
            
            # Format activities for prompt
            activities_text = self._format_activities(activities)
            
            prompt = format_slot_prompt(
                "school_analysis",
                n_activities=len(activities),
                school_name=school_name,
                code=school_code,
                category=ctx["category"],
                dim=self.config.dim,
                region=self.config.region,
                activities_text=activities_text,
            )
            
            system_prompt = COMMON_RULES + NARRATIVE_STYLE
            
            provider = self._get_provider("school_analysis")
            logger.info(f"[fill]   {i}/{total}: {slot_name} ({provider.name})")
            
            try:
                response = provider.generate(prompt, system_prompt)
                self.generated_content[slot_name] = response.content.strip()
            except Exception as e:
                logger.error(f"[fill] Error generating {slot_name}: {e}")
                self.generated_content[slot_name] = f"[Errore generazione: {e}]"
    
    def _fill_category_intro_slots(self, slot_info: dict) -> None:
        """Fill category intro slots."""
        intro_slots = [
            (name, info) for name, info in slot_info.items()
            if info["type"] == "category_intro"
        ]
        
        for slot_name, info in intro_slots:
            ctx = info["context"]
            
            prompt = format_slot_prompt(
                "category_intro",
                category=ctx["category"],
                n_schools=ctx["n_schools"],
                n_activities=ctx["n_activities"],
                provinces=", ".join(ctx["provinces"]),
                dim=self.config.dim,
                region=self.config.region,
            )
            
            system_prompt = COMMON_RULES + NARRATIVE_STYLE
            provider = self._get_provider("category_intro")
            logger.info(f"[fill]   Intro: {ctx['category']} ({provider.name})")
            
            try:
                response = provider.generate(prompt, system_prompt)
                self.generated_content[slot_name] = response.content.strip()
            except Exception as e:
                logger.error(f"[fill] Error generating {slot_name}: {e}")
                self.generated_content[slot_name] = f"[Errore generazione: {e}]"
    
    def _fill_synthesis_slots(self, slot_info: dict) -> None:
        """Fill synthesis slots using already generated school content."""
        synthesis_slots = [
            (name, info) for name, info in slot_info.items()
            if info["type"] == "synthesis"
        ]
        
        for slot_name, info in synthesis_slots:
            ctx = info["context"]
            
            # Collect school texts for this synthesis
            school_texts = []
            for code in ctx["school_codes"]:
                # Find the corresponding school slot
                cat_slug = slot_name.split("_sintesi_")[0]
                school_slot = f"{cat_slug}_{code}"
                if school_slot in self.generated_content:
                    school = self.builder.schools.get(code)
                    name = school.name if school else code
                    school_texts.append(f"--- {name} ({code}) ---\n{self.generated_content[school_slot]}")
            
            if not school_texts:
                self.generated_content[slot_name] = "Dati non disponibili."
                continue
            
            prompt = format_slot_prompt(
                "synthesis",
                school_type=ctx["school_type"],
                category=ctx["category"],
                dim=self.config.dim,
                region=self.config.region,
                school_texts="\n\n".join(school_texts),
            )
            
            system_prompt = COMMON_RULES + NARRATIVE_STYLE
            provider = self._get_provider("synthesis")
            logger.info(f"[fill]   Synthesis: {ctx['category']} - {ctx['school_type']} ({provider.name})")
            
            try:
                response = provider.generate(prompt, system_prompt)
                self.generated_content[slot_name] = response.content.strip()
            except Exception as e:
                logger.error(f"[fill] Error generating {slot_name}: {e}")
                self.generated_content[slot_name] = f"[Errore generazione: {e}]"
    
    def _fill_comparison_slots(self, slot_info: dict) -> None:
        """Fill comparison slots."""
        comparison_slots = [
            (name, info) for name, info in slot_info.items()
            if info["type"] == "comparison"
        ]
        
        for slot_name, info in comparison_slots:
            ctx = info["context"]
            
            # Build schools focus list
            schools_focus = []
            cat_slug = slot_name.replace("_comparazione", "")
            for code in ctx["school_codes"]:
                school = self.builder.schools.get(code)
                if school:
                    school_slot = f"{cat_slug}_{code}"
                    content = self.generated_content.get(school_slot, "")
                    # Extract first 200 chars as focus summary
                    focus = content[:200].replace("\n", " ") + "..." if content else "Dati non disponibili"
                    schools_focus.append(f"- {school.name} ({code}): {focus}")
            
            prompt = format_slot_prompt(
                "comparison",
                category=ctx["category"],
                dim=self.config.dim,
                region=self.config.region,
                schools_focus="\n".join(schools_focus),
            )
            
            system_prompt = COMMON_RULES + NARRATIVE_STYLE
            provider = self._get_provider("comparison")
            logger.info(f"[fill]   Comparison: {ctx['category']} ({provider.name})")
            
            try:
                response = provider.generate(prompt, system_prompt)
                self.generated_content[slot_name] = response.content.strip()
            except Exception as e:
                logger.error(f"[fill] Error generating {slot_name}: {e}")
                self.generated_content[slot_name] = f"[Errore generazione: {e}]"
    
    def _fill_global_slots(self, slot_info: dict) -> None:
        """Fill intro, territorial, and conclusion slots."""
        
        # Intro generale
        if "intro_generale" in slot_info:
            ctx = slot_info["intro_generale"]["context"]
            prompt = format_slot_prompt(
                "intro_generale",
                n_schools=ctx["total_schools"],
                n_activities=ctx["total_activities"],
                categories=", ".join(ctx["categories"]),
                provinces=", ".join(ctx["provinces"]),
                dim=self.config.dim,
                region=self.config.region,
            )
            
            system_prompt = COMMON_RULES + NARRATIVE_STYLE
            provider = self._get_provider("intro_generale")
            logger.info(f"[fill]   Intro generale ({provider.name})")
            
            try:
                response = provider.generate(prompt, system_prompt)
                self.generated_content["intro_generale"] = response.content.strip()
            except Exception as e:
                logger.error(f"[fill] Error generating intro_generale: {e}")
                self.generated_content["intro_generale"] = f"[Errore generazione: {e}]"
        
        # Territorial differences
        if "differenze_territoriali" in slot_info:
            ctx = slot_info["differenze_territoriali"]["context"]
            province_data = "\n".join([
                f"- {prov}: {counts}" 
                for prov, counts in ctx.get("category_totals", {}).items()
            ])
            
            prompt = format_slot_prompt(
                "territorial",
                province_data=province_data,
                dim=self.config.dim,
                region=self.config.region,
            )
            
            system_prompt = COMMON_RULES + NARRATIVE_STYLE
            provider = self._get_provider("territorial")
            logger.info(f"[fill]   Differenze territoriali ({provider.name})")
            
            try:
                response = provider.generate(prompt, system_prompt)
                self.generated_content["differenze_territoriali"] = response.content.strip()
            except Exception as e:
                logger.error(f"[fill] Error generating differenze_territoriali: {e}")
                self.generated_content["differenze_territoriali"] = f"[Errore generazione: {e}]"
        
        # Conclusions
        if "conclusioni" in slot_info:
            ctx = slot_info["conclusioni"]["context"]
            prompt = format_slot_prompt(
                "conclusion",
                n_schools=ctx["total_schools"],
                n_activities=ctx["total_activities"],
                categories=", ".join(ctx["categories"]),
                dim=self.config.dim,
                region=self.config.region,
            )
            
            system_prompt = COMMON_RULES + NARRATIVE_STYLE
            provider = self._get_provider("conclusion")
            logger.info(f"[fill]   Conclusioni ({provider.name})")
            
            try:
                response = provider.generate(prompt, system_prompt)
                self.generated_content["conclusioni"] = response.content.strip()
            except Exception as e:
                logger.error(f"[fill] Error generating conclusioni: {e}")
                self.generated_content["conclusioni"] = f"[Errore generazione: {e}]"
    
    def _format_activities(self, activities: list[dict]) -> str:
        """Format activities for the prompt."""
        lines = []
        for i, act in enumerate(activities, 1):
            title = act.get("titolo", "Senza titolo")
            desc = act.get("descrizione", "")[:300]
            page = act.get("pagina_evidenza", "")
            
            entry = f"{i}. {title}"
            if desc:
                entry += f"\n   {desc}"
            if page:
                entry += f"\n   (PTOF: {page})"
            
            lines.append(entry)
        
        return "\n\n".join(lines)
    
    def _replace_slots(self, skeleton: str) -> str:
        """Replace all [SLOT:xxx] placeholders with generated content."""
        content = skeleton
        
        for slot_name, text in self.generated_content.items():
            placeholder = f"[SLOT:{slot_name}]"
            content = content.replace(placeholder, text)
        
        # Remove any remaining unfilled slots
        content = re.sub(r'\[SLOT:[^\]]+\]', '', content)
        
        # Clean up extra blank lines
        content = re.sub(r'\n{4,}', '\n\n\n', content)
        
        return content
