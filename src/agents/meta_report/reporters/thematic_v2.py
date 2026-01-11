"""Thematic Reporter V2 - Analisi scuola per scuola.

Strategia:
1. Per ogni scuola, analizza tutte le sue attività
2. Classifica in quale sezione inserire ogni scuola (Direttrici, Metodologie, ecc.)
3. Append progressivo dei contenuti
4. Sintesi finale con introduzione e conclusioni

Ottimizzato per modelli locali 27B.
"""

import csv
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from .base import BaseReporter


# Categorie per classificazione
REPORT_SECTIONS = {
    "direttrici": "Direttrici Strategiche",
    "metodologie": "Metodologie e Strumenti",
    "partnership": "Partnership e Collaborazioni",
    "inclusione": "Inclusione e BES",
    "territoriali": "Esperienze Territoriali",
    "governance": "Azioni di Sistema e Governance",
}

# Mapping categoria attività → sezione report
CATEGORY_TO_SECTION = {
    "Progetti e Attività Esemplari": "direttrici",
    "Metodologie Didattiche Innovative": "metodologie",
    "Partnership e Collaborazioni Strategiche": "partnership",
    "Buone Pratiche per l'Inclusione": "inclusione",
    "Esperienze Territoriali Significative": "territoriali",
    "Azioni di Sistema e Governance": "governance",
}


class ThematicReporterV2(BaseReporter):
    """Reporter tematico con analisi scuola per scuola."""

    def __init__(self, provider):
        super().__init__(provider)
        self.activities_csv = Path("data/attivita.csv")

    def load_activities(self) -> list[dict]:
        """Carica attività dal CSV."""
        if not self.activities_csv.exists():
            print(f"[thematic_v2] CSV non trovato: {self.activities_csv}")
            return []

        activities = []
        with open(self.activities_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                activities.append(row)

        print(f"[thematic_v2] Caricate {len(activities)} attività")
        return activities

    def filter_activities(
        self,
        activities: list[dict],
        filters: Optional[dict] = None
    ) -> list[dict]:
        """Filtra attività per regione, ordine, ecc."""
        if not filters:
            return activities

        filtered = []
        for act in activities:
            match = True
            for key, value in filters.items():
                if key == "regione":
                    if act.get("regione", "").lower() != value.lower():
                        match = False
                elif key == "ordine_grado":
                    if value.lower() not in act.get("ordine_grado", "").lower():
                        match = False
                elif key == "provincia":
                    if act.get("provincia", "").lower() != value.lower():
                        match = False
            if match:
                filtered.append(act)

        print(f"[thematic_v2] Filtrate {len(filtered)}/{len(activities)} attività")
        return filtered

    def group_by_school(self, activities: list[dict]) -> dict:
        """Raggruppa attività per scuola."""
        schools = defaultdict(lambda: {
            "nome": "",
            "codice": "",
            "regione": "",
            "provincia": "",
            "tipo_scuola": "",
            "ordine_grado": "",
            "attivita": [],
        })

        for act in activities:
            code = act.get("codice_meccanografico", "")
            if not code:
                continue

            schools[code]["codice"] = code
            schools[code]["nome"] = act.get("nome_scuola", "")
            schools[code]["regione"] = act.get("regione", "")
            schools[code]["provincia"] = act.get("provincia", "")
            schools[code]["tipo_scuola"] = act.get("tipo_scuola", "")
            schools[code]["ordine_grado"] = act.get("ordine_grado", "")
            schools[code]["attivita"].append({
                "titolo": act.get("titolo", ""),
                "categoria": act.get("categoria", ""),
                "descrizione": act.get("descrizione", ""),
                "metodologia": act.get("metodologia", ""),
            })

        print(f"[thematic_v2] {len(schools)} scuole con attività")
        return dict(schools)

    def analyze_school(self, school: dict) -> dict:
        """Analizza una singola scuola con tutte le sue attività."""
        nome = school["nome"]
        codice = school["codice"]
        provincia = school["provincia"]
        attivita = school["attivita"]

        # Prepara prompt con tutte le attività della scuola
        activities_text = ""
        for i, att in enumerate(attivita, 1):
            activities_text += f"\n{i}. {att['titolo']} [{att['categoria']}]\n"
            activities_text += f"   {att['descrizione'][:200]}...\n"

        prompt = f"""Analizza le attività di orientamento della scuola **{nome}** ({codice}) di **{provincia}**.

ATTIVITÀ ({len(attivita)}):
{activities_text}

COMPITO:
1. Scrivi un paragrafo di 80-100 parole che descriva l'approccio della scuola all'orientamento
2. Evidenzia 2-3 punti di forza specifici
3. Indica le categorie predominanti (Direttrici, Metodologie, Partnership, Inclusione, Territoriali, Governance)

FORMATO:
- Scrivi in prosa narrativa fluida
- Usa **grassetto** per il nome della scuola
- Cita specifiche attività per nome
- NO elenchi puntati
"""

        system_prompt = (
            "Sei un analista dell'orientamento scolastico italiano. "
            "Scrivi in modo conciso, accademico e fattuale. "
            "Usa connettivi: inoltre, tuttavia, in particolare."
        )

        response = self.provider.generate(prompt, system_prompt)

        # Determina sezione principale basata sulle categorie delle attività
        category_counts = defaultdict(int)
        for att in attivita:
            cat = att.get("categoria", "")
            section = CATEGORY_TO_SECTION.get(cat, "direttrici")
            category_counts[section] += 1

        main_section = max(category_counts, key=category_counts.get) if category_counts else "direttrici"

        return {
            "nome": nome,
            "codice": codice,
            "provincia": provincia,
            "n_attivita": len(attivita),
            "analisi": response.content,
            "sezione": main_section,
            "categorie": dict(category_counts),
        }

    def generate_introduction(self, region: str, schools_data: list[dict]) -> str:
        """Genera introduzione basata sui dati aggregati."""
        n_schools = len(schools_data)
        n_activities = sum(s["n_attivita"] for s in schools_data)
        provinces = set(s["provincia"] for s in schools_data)

        prompt = f"""Scrivi un'INTRODUZIONE (150 parole) per un report sull'orientamento nel **{region}**.

DATI:
- {n_schools} scuole analizzate
- {n_activities} attività totali
- Province: {", ".join(sorted(provinces))}

CONTENUTO:
- Contesto territoriale
- Obiettivi del report
- Struttura del documento

Stile: accademico, formale. NO elenchi puntati.
"""
        response = self.provider.generate(prompt)
        return response.content

    def generate_synthesis(self, schools_data: list[dict], section_contents: dict) -> str:
        """Genera sintesi finale."""
        # Statistiche per sezione
        section_stats = defaultdict(int)
        for s in schools_data:
            section_stats[s["sezione"]] += 1

        prompt = f"""Scrivi una SINTESI CONCLUSIVA (200 parole) per il report.

STATISTICHE SEZIONI:
{chr(10).join(f"- {REPORT_SECTIONS.get(k, k)}: {v} scuole" for k, v in section_stats.items())}

CONTENUTO:
- 3-4 trend principali emersi
- Punti di forza del territorio
- 2-3 raccomandazioni operative

Stile: accademico, propositivo. NO elenchi puntati nel corpo.
"""
        response = self.provider.generate(prompt)
        return response.content

    def generate(
        self,
        dimension: str,
        filters: Optional[dict] = None,
        prompt_profile: str = "overview",
        force: bool = False,
    ) -> Path:
        """Genera report tematico con analisi scuola per scuola."""

        # 1. Carica e filtra attività
        activities = self.load_activities()
        if filters:
            activities = self.filter_activities(activities, filters)

        if not activities:
            print("[thematic_v2] Nessuna attività trovata")
            return None

        # 2. Raggruppa per scuola
        schools = self.group_by_school(activities)

        # 3. Analizza ogni scuola
        print(f"[thematic_v2] Analisi di {len(schools)} scuole...")
        schools_data = []
        for i, (code, school) in enumerate(schools.items(), 1):
            print(f"[thematic_v2] Analisi {i}/{len(schools)}: {school['nome'][:40]}...")
            analysis = self.analyze_school(school)
            schools_data.append(analysis)

        # 4. Organizza contenuti per sezione
        section_contents = defaultdict(list)
        for s in schools_data:
            section_contents[s["sezione"]].append(s)

        # 5. Genera introduzione
        region = filters.get("regione", "Italia") if filters else "Italia"
        introduction = self.generate_introduction(region, schools_data)

        # 6. Genera sintesi
        synthesis = self.generate_synthesis(schools_data, section_contents)

        # 7. Componi report
        content_parts = [
            f"# Orientamento nel {region.title()}",
            "",
            "### Introduzione",
            introduction,
            "",
        ]

        # Aggiungi sezioni con analisi delle scuole
        for section_key, section_title in REPORT_SECTIONS.items():
            schools_in_section = section_contents.get(section_key, [])
            if schools_in_section:
                content_parts.append(f"### {section_title}")
                content_parts.append("")
                for s in schools_in_section:
                    content_parts.append(s["analisi"])
                    content_parts.append("")

        # Panoramica territoriale (tabella)
        province_stats = defaultdict(lambda: {"count": 0, "schools": [], "categories": defaultdict(int)})
        for s in schools_data:
            prov = s["provincia"]
            province_stats[prov]["count"] += s["n_attivita"]
            province_stats[prov]["schools"].append(s["nome"])
            for cat, cnt in s.get("categorie", {}).items():
                province_stats[prov]["categories"][cat] += cnt

        content_parts.append("### Panoramica Territoriale")
        content_parts.append("")
        content_parts.append("| Provincia | Attività | Scuole |")
        content_parts.append("|-----------|----------|--------|")
        for prov, stats in sorted(province_stats.items(), key=lambda x: x[1]["count"], reverse=True):
            content_parts.append(f"| **{prov}** | {stats['count']} | {len(stats['schools'])} |")
        content_parts.append("")

        # Analisi differenze territoriali (narrativa)
        content_parts.append("### Differenze Territoriali")
        content_parts.append("")
        diff_terr = self._generate_territorial_differences(province_stats, region)
        content_parts.append(diff_terr)
        content_parts.append("")

        # Sintesi
        content_parts.append("### Sintesi e Raccomandazioni")
        content_parts.append(synthesis)
        content_parts.append("")

        # Statistiche
        content_parts.append(f"---")
        content_parts.append(f"📊 **Statistiche**: {sum(s['n_attivita'] for s in schools_data)} attività da {len(schools_data)} scuole")

        content = "\n".join(content_parts)

        # 8. Salva report
        output_dir = Path("reports/meta/thematic")
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filter_suffix = self._build_filter_suffix(filters) if filters else ""
        filename = f"{dimension}{filter_suffix}_v2_{timestamp}.md"
        output_path = output_dir / filename

        metadata = {
            "dimension": dimension,
            "practices_analyzed": sum(s["n_attivita"] for s in schools_data),
            "schools_involved": len(schools_data),
            "version": "v2_school_by_school",
        }
        if filters:
            metadata["filters"] = "; ".join(f"{k}={v}" for k, v in filters.items())

        self.write_report(content, output_path, metadata)
        print(f"[thematic_v2] Report saved: {output_path}")

        # Postprocessing
        try:
            from src.agents.meta_report.postprocess import postprocess_report
            postprocess_report(output_path)
        except Exception as e:
            print(f"[thematic_v2] Postprocessor warning: {e}")

        return output_path

    def _generate_territorial_differences(self, province_stats: dict, region: str) -> str:
        """Genera analisi delle differenze territoriali tra province."""
        if len(province_stats) < 2:
            return f"Con una sola provincia analizzata, non emergono differenze territoriali significative nel **{region}**."

        # Prepara dati per il prompt
        prov_data = []
        for prov, stats in sorted(province_stats.items(), key=lambda x: x[1]["count"], reverse=True):
            cats = ", ".join(f"{k}: {v}" for k, v in stats["categories"].items())
            prov_data.append(f"- **{prov}**: {stats['count']} attività, {len(stats['schools'])} scuole. Categorie: {cats}")

        prompt = f"""Analizza le DIFFERENZE TERRITORIALI tra le province del **{region}**.

DATI PER PROVINCIA:
{chr(10).join(prov_data)}

COMPITO:
Scrivi 150-200 parole che descrivano:
1. Quale provincia è più attiva e perché
2. Differenze nelle tipologie di attività tra province
3. Possibili spiegazioni (contesto economico, vicinanza università, ecc.)

Stile: narrativo, accademico. Usa **grassetto** per le province. NO elenchi puntati.
"""
        response = self.provider.generate(prompt)
        return response.content

    def _build_filter_suffix(self, filters: dict) -> str:
        """Costruisce suffisso filename dai filtri."""
        parts = []
        for key, value in filters.items():
            clean_value = value.lower().replace(" ", "-")
            parts.append(f"__{key}={clean_value}")
        return "".join(parts)
