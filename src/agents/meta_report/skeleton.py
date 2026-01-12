"""Skeleton builder for meta-reports.

Generates the complete report structure with placeholders that will be
filled by LLM calls. All formatting (headers, tables, school names) is
determined here, not by the LLM.
"""

import csv
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# Category order and mapping
CATEGORY_ORDER = [
    "Progetti e Attività Esemplari",
    "Metodologie Didattiche Innovative",
    "Partnership e Collaborazioni",
    "Azioni di Sistema",
    "Inclusione e BES",
    "Esperienze Territoriali",
]

CATEGORY_MAP = {
    "Progetti e Attività Esemplari": "Progetti e Attività Esemplari",
    "Metodologie Didattiche Innovative": "Metodologie Didattiche Innovative",
    "Partnership e Collaborazioni Strategiche": "Partnership e Collaborazioni",
    "Partnership e Collaborazioni": "Partnership e Collaborazioni",
    "Azioni di Sistema e Governance": "Azioni di Sistema",
    "Azioni di Sistema": "Azioni di Sistema",
    "Buone Pratiche per l'Inclusione": "Inclusione e BES",
    "Inclusione e BES": "Inclusione e BES",
    "Esperienze Territoriali Significative": "Esperienze Territoriali",
    "Esperienze Territoriali": "Esperienze Territoriali",
}

CATEGORY_SLUGS = {
    "Progetti e Attività Esemplari": "progetti",
    "Metodologie Didattiche Innovative": "metodologie",
    "Partnership e Collaborazioni": "partnership",
    "Azioni di Sistema": "azioni",
    "Inclusione e BES": "inclusione",
    "Esperienze Territoriali": "esperienze",
}

SCHOOL_TYPE_ORDER = ["Licei", "Istituti Tecnici", "Istituti Professionali"]


@dataclass
class SchoolInfo:
    """Information about a school."""
    code: str
    name: str
    province: str
    school_type: str  # Liceo, Tecnico, Professionale, etc.
    activities_by_category: dict = field(default_factory=dict)
    
    def get_type_group(self) -> str:
        """Return the school type group (Licei, Istituti Tecnici, Istituti Professionali)."""
        tipo = self.school_type.lower()
        if "liceo" in tipo:
            return "Licei"
        elif "tecnico" in tipo:
            return "Istituti Tecnici"
        elif "professionale" in tipo or "i grado" in tipo or "primaria" in tipo:
            return "Istituti Professionali"
        return "Altro"


@dataclass 
class CategoryStructure:
    """Structure for a category with schools grouped by province."""
    name: str
    slug: str
    provinces: dict = field(default_factory=dict)  # province -> {code: [activities]}
    
    def total_activities(self) -> int:
        return sum(
            len(acts) 
            for prov in self.provinces.values() 
            for acts in prov.values()
        )
    
    def total_schools(self) -> int:
        return sum(len(prov) for prov in self.provinces.values())


class SkeletonBuilder:
    """Builds report skeleton with placeholders for LLM content."""
    
    def __init__(
        self,
        activities: list[dict],
        filters: dict,
        dimension: str = "orientamento"
    ):
        self.activities = activities
        self.filters = filters
        self.dimension = dimension
        
        # Built during build_structure()
        self.schools: dict[str, SchoolInfo] = {}
        self.categories: dict[str, CategoryStructure] = {}
        self.cross_links: dict[str, list[str]] = {}
        
    def build_structure(self) -> None:
        """Build the hierarchical structure from activities."""
        
        # Initialize categories
        for cat_name in CATEGORY_ORDER:
            slug = CATEGORY_SLUGS[cat_name]
            self.categories[cat_name] = CategoryStructure(name=cat_name, slug=slug)
        
        # Process activities
        for row in self.activities:
            raw_cat = row.get("categoria", "")
            cat = CATEGORY_MAP.get(raw_cat, raw_cat)
            
            if cat not in self.categories:
                continue
                
            code = row.get("codice_meccanografico", "")
            if not code:
                continue
            
            province = row.get("provincia", "Altro")
            name = row.get("nome_scuola", "")
            school_type = row.get("tipo_scuola", "")
            activity = {
                "titolo": row.get("titolo", ""),
                "descrizione": row.get("descrizione", ""),
                "metodologia": row.get("metodologia", ""),
                "citazione_ptof": row.get("citazione_ptof", ""),
                "pagina_evidenza": row.get("pagina_evidenza", ""),
            }
            
            # Register school
            if code not in self.schools:
                self.schools[code] = SchoolInfo(
                    code=code,
                    name=name,
                    province=province,
                    school_type=school_type,
                )
            
            # Add activity to category structure
            if province not in self.categories[cat].provinces:
                self.categories[cat].provinces[province] = {}
            
            if code not in self.categories[cat].provinces[province]:
                self.categories[cat].provinces[province][code] = []
            
            self.categories[cat].provinces[province][code].append(activity)
            
            # Track activities by category for each school
            if cat not in self.schools[code].activities_by_category:
                self.schools[code].activities_by_category[cat] = []
            self.schools[code].activities_by_category[cat].append(activity)
    
    def compute_cross_links(self) -> None:
        """Compute cross-category links for each school."""
        for code, school in self.schools.items():
            categories = list(school.activities_by_category.keys())
            self.cross_links[code] = categories
    
    def _get_cross_link_note(self, code: str, current_category: str) -> str:
        """Generate cross-link note for a school entry."""
        other_cats = [c for c in self.cross_links.get(code, []) if c != current_category]
        if len(other_cats) > 1:
            # Show up to 2 other categories
            shown = other_cats[:2]
            return f" (si collega anche a: {', '.join(shown)})"
        return ""
    
    def generate_skeleton(self) -> str:
        """Generate the complete markdown skeleton with placeholders."""
        lines = []
        
        # Title
        lines.append(f"# {self.dimension.title()}")
        lines.append("")
        
        # Methodology note
        lines.append(self._generate_methodology_note())
        lines.append("")
        
        # Introduction
        lines.append("## Introduzione")
        lines.append("")
        lines.append("[SLOT:intro_generale]")
        lines.append("")
        
        # Categories
        for cat_name in CATEGORY_ORDER:
            cat = self.categories.get(cat_name)
            if not cat or cat.total_activities() == 0:
                continue
            
            lines.extend(self._generate_category_section(cat))
        
        # Territorial differences
        lines.append("## Differenze Territoriali")
        lines.append("")
        lines.append("[SLOT:differenze_territoriali]")
        lines.append("")
        lines.append(self.generate_territorial_table())
        lines.append("")
        
        # Conclusions
        lines.append("## Conclusioni")
        lines.append("")
        lines.append("[SLOT:conclusioni]")
        lines.append("")
        
        # Appendix
        total_activities = sum(c.total_activities() for c in self.categories.values())
        lines.append("## Appendice")
        lines.append("")
        lines.append(f"Analisi basata su {total_activities} attività di {len(self.schools)} scuole.")
        lines.append("")
        
        return "\n".join(lines)
    
    def _generate_methodology_note(self) -> str:
        """Generate the fixed methodology note."""
        return """### Nota Metodologica

Il presente report offre un'analisi monografica delle attività di orientamento estratte dai PTOF (Piani Triennali dell'Offerta Formativa) degli istituti scolastici, catalogate nel dataset `attivita.csv`. L'elaborazione si basa su un'analisi qualitativa automatizzata supportata da modelli linguistici avanzati (LLM), che hanno classificato ogni iniziativa secondo una tassonomia standardizzata in sei categorie chiave:

| Categoria | Descrizione e Obiettivi |
|-----------|-------------------------|
| 🎯 Progetti e Attività Esemplari | Iniziative di eccellenza, innovative e ad alto impatto, potenzialmente replicabili in altri contesti. |
| 📚 Metodologie Didattiche Innovative | Adozione di nuovi approcci pedagogici (es. debate, peer tutoring, gamification) per rendere l'orientamento attivo e coinvolgente. |
| 🤝 Partnership e Collaborazioni | Reti strategiche con Università, ITS, aziende ed enti territoriali per connettere scuola e mondo del lavoro. |
| ⚙️ Azioni di Sistema | Interventi strutturali di governance, coordinamento dei dipartimenti e formazione dedicata ai docenti referenti. |
| 🌈 Inclusione e BES | Strategie specifiche per garantire l'accessibilità dei percorsi orientativi a studenti con BES, DSA e disabilità. |
| 🗺️ Esperienze Territoriali | Progetti radicati nel tessuto socio-economico locale, analizzando le specificità territoriali a livello provinciale. |

L'obiettivo è restituire una narrazione coerente che non si limiti a un elenco di attività, ma evidenzi le direttrici strategiche, le interconnessioni multidisciplinari e le specificità territoriali.

### Come leggere questo report

- Panoramica Territoriale: Distribuzione delle attività per area (Regioni o Province).
- Analisi Monografica: Approfondimento strutturato sulle direttrici strategiche e operative.
- Sintesi Executive: Visione d'insieme per i decisori con raccomandazioni finali.
"""
    
    def _generate_category_section(self, cat: CategoryStructure) -> list[str]:
        """Generate a category section with all schools and synthesis slots."""
        lines = []
        
        lines.append(f"## {cat.name}")
        lines.append("")
        lines.append(f"[SLOT:intro_cat_{cat.slug}]")
        lines.append("")
        
        # Schools by province (alphabetical)
        for province in sorted(cat.provinces.keys()):
            lines.append(f"#### {province}")
            lines.append("")
            
            # Schools in province (alphabetical by name)
            school_codes = list(cat.provinces[province].keys())
            school_codes_sorted = sorted(
                school_codes, 
                key=lambda c: self.schools[c].name
            )
            
            for code in school_codes_sorted:
                school = self.schools[code]
                cross_note = self._get_cross_link_note(code, cat.name)
                
                lines.append(f"{school.name} ({code}){cross_note}")
                lines.append("")
                lines.append(f"[SLOT:{cat.slug}_{code}]")
                lines.append("")
        
        # Separator
        lines.append("---")
        lines.append("")
        
        # Synthesis by school type
        for school_type in SCHOOL_TYPE_ORDER:
            # Check if we have schools of this type in this category
            has_schools = any(
                self.schools[code].get_type_group() == school_type
                for prov in cat.provinces.values()
                for code in prov.keys()
            )
            if has_schools:
                type_slug = school_type.lower().replace(" ", "_")
                lines.append(f"### Sintesi {school_type}")
                lines.append("")
                lines.append(f"[SLOT:{cat.slug}_sintesi_{type_slug}]")
                lines.append("")
        
        # Similar schools comparison
        lines.append("### Scuole con Attività Simili")
        lines.append("")
        lines.append(f"[SLOT:{cat.slug}_comparazione]")
        lines.append("")
        
        return lines
    
    def generate_territorial_table(self) -> str:
        """Generate the territorial summary table."""
        # Collect data by province
        province_data = defaultdict(lambda: {"schools": set(), "cats": defaultdict(int)})
        
        for cat_name, cat in self.categories.items():
            for province, schools in cat.provinces.items():
                for code, activities in schools.items():
                    province_data[province]["schools"].add(code)
                    province_data[province]["cats"][cat_name] += len(activities)
        
        # Build table
        lines = []
        
        # Header
        cat_abbrevs = ["Prog.", "Meto.", "Part.", "Azio.", "Incl.", "Espe."]
        lines.append("| Provincia | Scuole | " + " | ".join(cat_abbrevs) + " | Tot |")
        lines.append("| --- | --- | " + " | ".join(["---"] * 6) + " | --- |")
        
        # Rows (sorted by total descending)
        sorted_provinces = sorted(
            province_data.keys(),
            key=lambda p: sum(province_data[p]["cats"].values()),
            reverse=True
        )
        
        for province in sorted_provinces:
            data = province_data[province]
            n_schools = len(data["schools"])
            counts = [str(data["cats"].get(cat, 0)) for cat in CATEGORY_ORDER]
            total = sum(data["cats"].values())
            
            lines.append(f"| {province} | {n_schools} | " + " | ".join(counts) + f" | {total} |")
        
        lines.append("")
        lines.append("_Legenda: Prog.=Progetti Esemplari, Meto.=Metodologie, Part.=Partnership, Azio.=Azioni Sistema, Incl.=Inclusione, Espe.=Esperienze Territoriali_")
        
        return "\n".join(lines)
    
    def get_slot_info(self) -> dict:
        """Return information about all slots for LLM processing."""
        slots = {}
        
        # Intro generale
        slots["intro_generale"] = {
            "type": "intro",
            "provider": "synthesis",
            "context": {
                "total_schools": len(self.schools),
                "total_activities": sum(c.total_activities() for c in self.categories.values()),
                "categories": list(self.categories.keys()),
                "provinces": list(set(s.province for s in self.schools.values())),
            }
        }
        
        # Category intros
        for cat_name, cat in self.categories.items():
            if cat.total_activities() == 0:
                continue
            
            slots[f"intro_cat_{cat.slug}"] = {
                "type": "category_intro",
                "provider": "school",
                "context": {
                    "category": cat_name,
                    "n_schools": cat.total_schools(),
                    "n_activities": cat.total_activities(),
                    "provinces": list(cat.provinces.keys()),
                }
            }
        
        # School × Category
        for cat_name, cat in self.categories.items():
            for province, schools in cat.provinces.items():
                for code, activities in schools.items():
                    school = self.schools[code]
                    slots[f"{cat.slug}_{code}"] = {
                        "type": "school_analysis",
                        "provider": "school",
                        "context": {
                            "school_name": school.name,
                            "code": code,
                            "province": province,
                            "school_type": school.school_type,
                            "category": cat_name,
                            "activities": activities,
                        }
                    }
        
        # Synthesis by school type
        for cat_name, cat in self.categories.items():
            if cat.total_activities() == 0:
                continue
            
            for school_type in SCHOOL_TYPE_ORDER:
                # Get schools of this type
                type_schools = []
                for prov in cat.provinces.values():
                    for code in prov.keys():
                        if self.schools[code].get_type_group() == school_type:
                            type_schools.append(code)
                
                if type_schools:
                    type_slug = school_type.lower().replace(" ", "_")
                    slots[f"{cat.slug}_sintesi_{type_slug}"] = {
                        "type": "synthesis",
                        "provider": "synthesis",
                        "context": {
                            "category": cat_name,
                            "school_type": school_type,
                            "school_codes": type_schools,
                        }
                    }
        
        # Comparisons
        for cat_name, cat in self.categories.items():
            if cat.total_activities() == 0:
                continue
            
            all_codes = [
                code 
                for prov in cat.provinces.values() 
                for code in prov.keys()
            ]
            
            slots[f"{cat.slug}_comparazione"] = {
                "type": "comparison",
                "provider": "synthesis",
                "context": {
                    "category": cat_name,
                    "school_codes": all_codes,
                }
            }
        
        # Territorial differences
        slots["differenze_territoriali"] = {
            "type": "territorial",
            "provider": "synthesis",
            "context": {
                "provinces": list(set(s.province for s in self.schools.values())),
                "category_totals": {c: cat.total_activities() for c, cat in self.categories.items()},
            }
        }
        
        # Conclusions
        slots["conclusioni"] = {
            "type": "conclusion",
            "provider": "synthesis",
            "context": {
                "total_schools": len(self.schools),
                "total_activities": sum(c.total_activities() for c in self.categories.values()),
                "categories": list(self.categories.keys()),
            }
        }
        
        return slots


def load_activities_from_csv(
    csv_path: Path,
    filters: Optional[dict] = None
) -> list[dict]:
    """Load and filter activities from CSV file."""
    activities = []
    
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Apply filters
            if filters:
                if filters.get("regione"):
                    if row.get("regione", "").lower() != filters["regione"].lower():
                        continue
                if filters.get("ordine_grado"):
                    if filters["ordine_grado"] not in row.get("ordine_grado", ""):
                        continue
                if filters.get("provincia"):
                    if row.get("provincia", "").lower() != filters["provincia"].lower():
                        continue
            
            activities.append(row)
    
    return activities
