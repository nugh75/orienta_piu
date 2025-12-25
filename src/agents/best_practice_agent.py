#!/usr/bin/env python3
"""
Best Practice Agent - Analizza i report delle scuole per estrarre best practice sull'orientamento.

Questo agente:
1. Legge i file MD e JSON di ogni scuola in analysis_results/
2. Estrae best practice, progetti, metodologie, partnership
3. Genera un report aggregato delle best practice sull'orientamento
"""

import os
import json
import glob
import re
from collections import Counter, defaultdict
from datetime import datetime
import pandas as pd

# Configurazione
ANALYSIS_DIR = 'analysis_results'
OUTPUT_DIR = 'reports'
OUTPUT_FILE = 'best_practice_orientamento.md'
SUMMARY_FILE = 'data/analysis_summary.csv'

# Soglie
MIN_SCORE_TOP_SCHOOL = 4.5  # Scuole con indice >= 4.5 considerate "top"
MIN_DIMENSION_SCORE = 5.0   # Punteggio minimo per considerare una dimensione eccellente


class BestPracticeAgent:
    """Agente per l'estrazione delle best practice sull'orientamento."""
    
    def __init__(self, analysis_dir=ANALYSIS_DIR, output_dir=OUTPUT_DIR):
        self.analysis_dir = analysis_dir
        self.output_dir = output_dir
        self.schools_data = []
        self.best_practices = defaultdict(list)
        self.methodologies = Counter()
        self.partnerships = Counter()
        self.projects = Counter()
        self.activities = []
        
    def load_school_data(self, school_id):
        """Carica i dati MD e JSON di una scuola."""
        json_path = os.path.join(self.analysis_dir, f"{school_id}_PTOF_analysis.json")
        md_path = os.path.join(self.analysis_dir, f"{school_id}_PTOF_analysis.md")
        
        data = {'school_id': school_id, 'json': None, 'md': None}
        
        # Carica JSON
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data['json'] = json.load(f)
            except Exception as e:
                print(f"⚠️ Errore lettura JSON {school_id}: {e}")
        
        # Carica MD
        if os.path.exists(md_path):
            try:
                with open(md_path, 'r', encoding='utf-8') as f:
                    data['md'] = f.read()
            except Exception as e:
                print(f"⚠️ Errore lettura MD {school_id}: {e}")
        
        return data
    
    def calculate_maturity_index(self, json_data):
        """Calcola l'indice di maturità da JSON."""
        if not json_data or 'ptof_section2' not in json_data:
            return 0
        
        sec2 = json_data['ptof_section2']
        scores = []
        
        # Estrai tutti i punteggi
        for key, value in sec2.items():
            if isinstance(value, dict):
                if 'score' in value:
                    scores.append(value['score'])
                else:
                    for subkey, subval in value.items():
                        if isinstance(subval, dict) and 'score' in subval:
                            scores.append(subval['score'])
        
        return sum(scores) / len(scores) if scores else 0
    
    def extract_from_md(self, md_text):
        """Estrae informazioni chiave dal report MD."""
        extracted = {
            'punti_forza': [],
            'metodologie': [],
            'progetti': [],
            'partnership': [],
            'attivita': []
        }
        
        if not md_text:
            return extracted
        
        # Estrai Punti di Forza
        match = re.search(r'###?\s*\d*\.?\s*Punti di Forza\s*\n(.*?)(?=###|\Z)', md_text, re.DOTALL | re.IGNORECASE)
        if match:
            extracted['punti_forza'] = [match.group(1).strip()]
        
        # Estrai metodologie menzionate
        metodologie_keywords = [
            'project based learning', 'problem based learning', 'flipped classroom',
            'cooperative learning', 'peer tutoring', 'service learning',
            'apprendimento cooperativo', 'didattica laboratoriale', 'outdoor education',
            'coding', 'STEM', 'STEAM', 'debate', 'storytelling', 'gamification',
            'learning by doing', 'role playing', 'simulazione', 'case study',
            'mentoring', 'tutoring', 'orientamento narrativo', 'career counseling',
            'portfolio competenze', 'autobiografia', 'bilancio competenze'
        ]
        
        md_lower = md_text.lower()
        for kw in metodologie_keywords:
            if kw.lower() in md_lower:
                extracted['metodologie'].append(kw.title())
        
        # Estrai progetti (pattern: "Progetto X", "progetto Y")
        progetti = re.findall(r'[Pp]rogetto\s+["\']?([A-Z][^"\'\.]{3,40})["\']?', md_text)
        extracted['progetti'] = list(set(progetti))
        
        # Estrai attività menzionate
        attivita = re.findall(r'attività\s+(?:di\s+)?([^\.]{5,50})', md_text, re.IGNORECASE)
        extracted['attivita'] = list(set([a.strip() for a in attivita[:5]]))
        
        return extracted
    
    def extract_from_json(self, json_data):
        """Estrae informazioni chiave dal JSON."""
        extracted = {
            'metadata': {},
            'partnership': [],
            'scores': {},
            'best_dimensions': []
        }
        
        if not json_data:
            return extracted
        
        # Metadata
        extracted['metadata'] = json_data.get('metadata', {})
        
        # Partnership
        sec2 = json_data.get('ptof_section2', {})
        partnership_data = sec2.get('2_2_partnership', {})
        extracted['partnership'] = partnership_data.get('partner_nominati', [])
        
        # Scores e best dimensions
        dimension_scores = {}
        
        # Finalità
        finalita = sec2.get('2_3_finalita', {})
        for key, val in finalita.items():
            if isinstance(val, dict) and 'score' in val:
                dimension_scores[key] = val['score']
        
        # Obiettivi
        obiettivi = sec2.get('2_4_obiettivi', {})
        for key, val in obiettivi.items():
            if isinstance(val, dict) and 'score' in val:
                dimension_scores[key] = val['score']
        
        # Azioni sistema
        azioni = sec2.get('2_5_azioni_sistema', {})
        for key, val in azioni.items():
            if isinstance(val, dict) and 'score' in val:
                dimension_scores[key] = val['score']
        
        # Didattica
        didattica = sec2.get('2_6_didattica_orientativa', {})
        for key, val in didattica.items():
            if isinstance(val, dict) and 'score' in val:
                dimension_scores[key] = val['score']
        
        # Opzionali
        opzionali = sec2.get('2_7_opzionali_facoltative', {})
        for key, val in opzionali.items():
            if isinstance(val, dict) and 'score' in val:
                dimension_scores[key] = val['score']
        
        extracted['scores'] = dimension_scores
        extracted['best_dimensions'] = [k for k, v in dimension_scores.items() if v >= MIN_DIMENSION_SCORE]
        
        return extracted
    
    def analyze_school(self, school_id):
        """Analizza una singola scuola."""
        print(f"📖 Analisi scuola: {school_id}")
        
        data = self.load_school_data(school_id)
        
        if not data['json'] and not data['md']:
            print(f"  ⚠️ Nessun dato disponibile")
            return None
        
        # Calcola indice
        maturity_index = self.calculate_maturity_index(data['json'])
        
        # Estrai da entrambi i formati
        md_extracted = self.extract_from_md(data['md'])
        json_extracted = self.extract_from_json(data['json'])
        
        school_analysis = {
            'school_id': school_id,
            'maturity_index': maturity_index,
            'denominazione': json_extracted['metadata'].get('denominazione', school_id),
            'tipo_scuola': json_extracted['metadata'].get('tipo_scuola', 'N/D'),
            'regione': json_extracted['metadata'].get('regione', 'N/D'),
            'comune': json_extracted['metadata'].get('comune', 'N/D'),
            'is_top': maturity_index >= MIN_SCORE_TOP_SCHOOL,
            'punti_forza': md_extracted['punti_forza'],
            'metodologie': md_extracted['metodologie'],
            'progetti': md_extracted['progetti'],
            'partnership': json_extracted['partnership'],
            'best_dimensions': json_extracted['best_dimensions'],
            'scores': json_extracted['scores']
        }
        
        # Aggiorna contatori globali
        for m in md_extracted['metodologie']:
            self.methodologies[m] += 1
        for p in json_extracted['partnership']:
            self.partnerships[p] += 1
        for proj in md_extracted['progetti']:
            self.projects[proj] += 1
        
        # Se è una scuola top, salva le best practice
        if school_analysis['is_top']:
            for pf in school_analysis['punti_forza']:
                self.best_practices['punti_forza'].append({
                    'school': school_id,
                    'denominazione': school_analysis['denominazione'],
                    'content': pf
                })
            
            for dim in school_analysis['best_dimensions']:
                self.best_practices['dimensioni_eccellenti'].append({
                    'school': school_id,
                    'denominazione': school_analysis['denominazione'],
                    'dimension': dim,
                    'score': school_analysis['scores'].get(dim, 0)
                })
        
        return school_analysis
    
    def run(self):
        """Esegue l'analisi su tutte le scuole."""
        print("🚀 Avvio Best Practice Agent")
        print(f"📂 Directory analisi: {self.analysis_dir}")
        print()
        
        # Trova tutti i file JSON
        json_files = glob.glob(os.path.join(self.analysis_dir, "*_PTOF_analysis.json"))
        school_ids = [os.path.basename(f).replace('_PTOF_analysis.json', '') for f in json_files]
        
        print(f"📊 Scuole da analizzare: {len(school_ids)}")
        print()
        
        # Analizza ogni scuola
        for school_id in school_ids:
            result = self.analyze_school(school_id)
            if result:
                self.schools_data.append(result)
        
        print()
        print(f"✅ Analizzate {len(self.schools_data)} scuole")
        
        # Genera report
        self.generate_report()
    
    def generate_report(self):
        """Genera il report delle best practice."""
        os.makedirs(self.output_dir, exist_ok=True)
        output_path = os.path.join(self.output_dir, OUTPUT_FILE)
        
        # Statistiche
        top_schools = [s for s in self.schools_data if s['is_top']]
        avg_index = sum(s['maturity_index'] for s in self.schools_data) / len(self.schools_data) if self.schools_data else 0
        
        report = []
        report.append("# 📚 Report Best Practice sull'Orientamento")
        report.append(f"\n*Generato il {datetime.now().strftime('%d/%m/%Y %H:%M')}*")
        report.append("")
        report.append("---")
        report.append("")
        
        # Executive Summary
        report.append("## 📊 Executive Summary")
        report.append("")
        report.append(f"- **Scuole analizzate**: {len(self.schools_data)}")
        report.append(f"- **Scuole eccellenti** (Indice ≥ {MIN_SCORE_TOP_SCHOOL}): {len(top_schools)}")
        report.append(f"- **Indice medio**: {avg_index:.2f}/7")
        report.append(f"- **Metodologie identificate**: {len(self.methodologies)}")
        report.append(f"- **Partnership estratte**: {len(self.partnerships)}")
        report.append(f"- **Progetti documentati**: {len(self.projects)}")
        report.append("")
        report.append("---")
        report.append("")
        
        # Scuole Top
        report.append("## 🏆 Scuole Eccellenti")
        report.append("")
        if top_schools:
            top_schools_sorted = sorted(top_schools, key=lambda x: x['maturity_index'], reverse=True)
            for i, school in enumerate(top_schools_sorted[:15], 1):
                report.append(f"### {i}. {school['denominazione']} ({school['school_id']})")
                report.append(f"- **Indice RO**: {school['maturity_index']:.2f}")
                report.append(f"- **Tipo**: {school['tipo_scuola']} | **Regione**: {school['regione']}")
                if school['metodologie']:
                    report.append(f"- **Metodologie**: {', '.join(school['metodologie'][:5])}")
                if school['partnership']:
                    report.append(f"- **Partnership**: {', '.join(school['partnership'][:3])}")
                if school['best_dimensions']:
                    dims = [d.replace('_', ' ').title() for d in school['best_dimensions'][:3]]
                    report.append(f"- **Dimensioni eccellenti**: {', '.join(dims)}")
                report.append("")
        else:
            report.append("*Nessuna scuola con indice ≥ {MIN_SCORE_TOP_SCHOOL}*")
        report.append("")
        report.append("---")
        report.append("")
        
        # Metodologie più diffuse
        report.append("## 🎓 Metodologie Didattiche più Diffuse")
        report.append("")
        if self.methodologies:
            for meth, count in self.methodologies.most_common(15):
                pct = count / len(self.schools_data) * 100
                bar = "█" * int(pct / 5)
                report.append(f"- **{meth}**: {count} scuole ({pct:.1f}%) {bar}")
        else:
            report.append("*Nessuna metodologia identificata*")
        report.append("")
        report.append("---")
        report.append("")
        
        # Partnership più frequenti
        report.append("## 🤝 Tipologie di Partnership")
        report.append("")
        if self.partnerships:
            # Raggruppa per tipo
            partnership_types = Counter()
            for partner in self.partnerships:
                partner_lower = partner.lower()
                if 'universit' in partner_lower:
                    partnership_types['Università'] += self.partnerships[partner]
                elif 'asl' in partner_lower or 'sanitari' in partner_lower:
                    partnership_types['Enti Sanitari'] += self.partnerships[partner]
                elif 'comune' in partner_lower or 'municipal' in partner_lower:
                    partnership_types['Enti Locali'] += self.partnerships[partner]
                elif 'associa' in partner_lower:
                    partnership_types['Associazioni'] += self.partnerships[partner]
                elif 'impres' in partner_lower or 'aziend' in partner_lower:
                    partnership_types['Imprese'] += self.partnerships[partner]
                elif 'rete' in partner_lower:
                    partnership_types['Reti Scolastiche'] += self.partnerships[partner]
                else:
                    partnership_types['Altri Enti'] += self.partnerships[partner]
            
            for ptype, count in partnership_types.most_common():
                report.append(f"- **{ptype}**: {count} menzioni")
            
            report.append("")
            report.append("### Esempi di Partnership")
            for partner, count in self.partnerships.most_common(10):
                report.append(f"- {partner} ({count} scuole)")
        else:
            report.append("*Nessuna partnership identificata*")
        report.append("")
        report.append("---")
        report.append("")
        
        # Dimensioni eccellenti
        report.append("## 📈 Dimensioni di Eccellenza")
        report.append("")
        dim_counter = Counter()
        for school in self.schools_data:
            for dim in school.get('best_dimensions', []):
                dim_counter[dim] += 1
        
        if dim_counter:
            # Raggruppa per macro-dimensione
            macro_dims = {
                'Finalità': ['finalita_attitudini', 'finalita_interessi', 'finalita_progetto_vita', 
                            'finalita_transizioni_formative', 'finalita_capacita_orientative_opportunita'],
                'Obiettivi': ['obiettivo_ridurre_abbandono', 'obiettivo_continuita_territorio',
                             'obiettivo_contrastare_neet', 'obiettivo_lifelong_learning'],
                'Governance': ['azione_coordinamento_servizi', 'azione_dialogo_docenti_studenti',
                              'azione_rapporto_scuola_genitori', 'azione_monitoraggio_azioni',
                              'azione_sistema_integrato_inclusione_fragilita'],
                'Didattica': ['didattica_da_esperienza_studenti', 'didattica_laboratoriale',
                             'didattica_flessibilita_spazi_tempi', 'didattica_interdisciplinare'],
                'Opportunità': ['opzionali_culturali', 'opzionali_laboratoriali_espressive',
                               'opzionali_ludiche_ricreative', 'opzionali_volontariato', 'opzionali_sportive']
            }
            
            for macro, dims in macro_dims.items():
                macro_count = sum(dim_counter.get(d, 0) for d in dims)
                if macro_count > 0:
                    report.append(f"### {macro} ({macro_count} eccellenze)")
                    for dim in dims:
                        if dim in dim_counter:
                            dim_label = dim.replace('_', ' ').replace('finalita ', '').replace('obiettivo ', '').replace('azione ', '').replace('didattica ', '').replace('opzionali ', '').title()
                            report.append(f"- {dim_label}: {dim_counter[dim]} scuole")
                    report.append("")
        else:
            report.append("*Nessuna dimensione con punteggio ≥ 5*")
        report.append("")
        report.append("---")
        report.append("")
        
        # Punti di forza comuni
        report.append("## 💪 Punti di Forza Ricorrenti")
        report.append("")
        if self.best_practices['punti_forza']:
            # Estrai parole chiave dai punti di forza
            keywords = Counter()
            kw_patterns = [
                ('inclusione', 'Inclusione'),
                ('collaborazione', 'Collaborazione'),
                ('territorio', 'Territorio'),
                ('laboratori', 'Didattica Laboratoriale'),
                ('partner', 'Partnership'),
                ('famiglie', 'Coinvolgimento Famiglie'),
                ('continuità', 'Continuità'),
                ('orientamento', 'Orientamento'),
                ('competenze', 'Competenze'),
                ('innovazione', 'Innovazione'),
                ('digitalizzazione', 'Digitalizzazione'),
                ('personalizzazione', 'Personalizzazione'),
            ]
            
            for bp in self.best_practices['punti_forza']:
                content_lower = bp['content'].lower()
                for pattern, label in kw_patterns:
                    if pattern in content_lower:
                        keywords[label] += 1
            
            if keywords:
                for kw, count in keywords.most_common(10):
                    report.append(f"- **{kw}**: citato in {count} scuole eccellenti")
            
            report.append("")
            report.append("### Esempi di Best Practice")
            for bp in self.best_practices['punti_forza'][:5]:
                report.append(f"\n> **{bp['denominazione']}** ({bp['school']})")
                # Estrai prima frase
                content = bp['content'][:300] + "..." if len(bp['content']) > 300 else bp['content']
                report.append(f"> {content}")
        else:
            report.append("*Nessun punto di forza estratto*")
        report.append("")
        report.append("---")
        report.append("")
        
        # Raccomandazioni
        report.append("## 💡 Raccomandazioni per le Scuole")
        report.append("")
        report.append("Basandosi sull'analisi delle scuole eccellenti, si raccomanda di:")
        report.append("")
        
        if self.methodologies:
            top_meth = self.methodologies.most_common(3)
            report.append(f"### 1. Adottare metodologie innovative")
            for meth, _ in top_meth:
                report.append(f"   - {meth}")
        
        report.append("")
        report.append("### 2. Sviluppare partnership strategiche")
        report.append("   - Collaborare con università e centri di ricerca")
        report.append("   - Coinvolgere enti del territorio")
        report.append("   - Partecipare a reti scolastiche tematiche")
        
        report.append("")
        report.append("### 3. Rafforzare le dimensioni deboli")
        
        # Calcola dimensioni mediamente più deboli
        weak_dims = Counter()
        for school in self.schools_data:
            for dim, score in school.get('scores', {}).items():
                if score < 3:
                    weak_dims[dim] += 1
        
        if weak_dims:
            for dim, count in weak_dims.most_common(3):
                dim_label = dim.replace('_', ' ').title()
                report.append(f"   - {dim_label} (debole in {count} scuole)")
        
        report.append("")
        report.append("### 4. Documentare le pratiche di orientamento")
        report.append("   - Creare una sezione dedicata nel PTOF")
        report.append("   - Definire obiettivi specifici e misurabili")
        report.append("   - Monitorare e valutare i risultati")
        
        report.append("")
        report.append("---")
        report.append("")
        report.append("## 📊 Appendice: Statistiche per Regione")
        report.append("")
        
        # Stats per regione
        region_stats = defaultdict(lambda: {'count': 0, 'sum_index': 0, 'top_count': 0})
        for school in self.schools_data:
            reg = school.get('regione', 'N/D')
            region_stats[reg]['count'] += 1
            region_stats[reg]['sum_index'] += school['maturity_index']
            if school['is_top']:
                region_stats[reg]['top_count'] += 1
        
        report.append("| Regione | Scuole | Media Indice | Top Schools |")
        report.append("|---------|--------|--------------|-------------|")
        
        for reg, stats in sorted(region_stats.items(), key=lambda x: x[1]['sum_index']/x[1]['count'] if x[1]['count'] > 0 else 0, reverse=True):
            avg = stats['sum_index'] / stats['count'] if stats['count'] > 0 else 0
            report.append(f"| {reg} | {stats['count']} | {avg:.2f} | {stats['top_count']} |")
        
        report.append("")
        report.append("---")
        report.append(f"\n*Report generato automaticamente dal Best Practice Agent*")
        
        # Scrivi il file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))
        
        print(f"\n📄 Report salvato in: {output_path}")
        return output_path


def main():
    """Entry point."""
    agent = BestPracticeAgent()
    agent.run()


if __name__ == '__main__':
    main()
