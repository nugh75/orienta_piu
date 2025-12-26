#!/usr/bin/env python3
"""
Best Practice Ollama Agent - Genera un report incrementale sulle best practice.

Approccio INCREMENTALE:
1. Legge UN report (MD + JSON) alla volta
2. Chiama Ollama per arricchire il report esistente con le nuove informazioni
3. Passa al prossimo report e ripete
4. Il report cresce progressivamente, focalizzandosi su AZIONI e BUONE PRATICHE

Focus: azioni concrete, metodologie, progetti, partnership - NON statistiche/numeri
"""

import os
import sys
import json
import glob
import time
import signal
import requests
from datetime import datetime
from pathlib import Path

# Configurazione
ANALYSIS_DIR = 'analysis_results'
OUTPUT_DIR = 'reports'
OUTPUT_FILE = 'best_practice_orientamento_narrativo.md'
OUTPUT_FILE_SYNTH = 'best_practice_orientamento_sintetico.md'
OUTPUT_FILE_SYNTH_FULL = 'best_practice_orientamento_sintetico_full.md'
PROGRESS_FILE = 'reports/.best_practice_progress.json'
SYNTH_PROGRESS_FILE = 'reports/.best_practice_synth_progress.json'

# Ollama settings
OLLAMA_URL = os.environ.get('OLLAMA_URL', "http://192.168.129.14:11434")
OLLAMA_MODEL = os.environ.get('MODEL', "qwen3:32b")
MAX_RETRIES = 3
REQUEST_TIMEOUT = 300
SYNTH_BACKOFF_START = 30
SYNTH_BACKOFF_MAX = 60 * 60 * 2
SYNTH_REFRESH_INTERVAL = 60 * 30

# Gemini refactoring settings
GEMINI_MODEL = "gemini-3-flash-preview"
REFACTOR_EVERY = 10  # Ogni N scuole chiama Gemini per refactoring

# Flag per uscita controllata
EXIT_REQUESTED = False


def graceful_exit_handler(signum, frame):
    """Handler per uscita controllata con Ctrl+C."""
    global EXIT_REQUESTED
    if EXIT_REQUESTED:
        print("\n\n⚠️ Uscita forzata.", flush=True)
        sys.exit(1)
    EXIT_REQUESTED = True
    print("\n\n🛑 USCITA RICHIESTA - Salvataggio in corso...", flush=True)

signal.signal(signal.SIGINT, graceful_exit_handler)


def get_gemini_key():
    """Ottiene la chiave API Gemini da .env o file config."""
    # Prima prova .env
    try:
        from dotenv import load_dotenv
        load_dotenv()
        key = os.getenv("GEMINI_API_KEY")
        if key:
            return key
    except ImportError:
        pass

    # Poi prova file config
    config_path = Path("data/api_config.json")
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                return config.get("gemini_api_key")
        except:
            pass

    return None


def get_openrouter_key():
    """Ottiene la chiave API OpenRouter da .env o file config."""
    # Prima prova .env
    try:
        from dotenv import load_dotenv
        load_dotenv()
        key = os.getenv("OPENROUTER_API_KEY")
        if key:
            return key
    except ImportError:
        pass

    # Poi prova file config
    config_path = Path("data/api_config.json")
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                return config.get("openrouter_api_key")
        except:
            pass

    return None


# Fallback model per OpenRouter (default: GPT OSS 120B free)
OPENROUTER_FALLBACK_MODEL = "openai/gpt-oss-120b:free"


def call_gemini(prompt: str, model: str, api_key: str):
    """
    Chiama Google Gemini API per refactoring del report.

    Returns:
        tuple: (success: bool, response: str or None)
        - Se rate limit (429): returns (False, None) per segnalare di riprovare dopo
        - Se successo: returns (True, response_text)
        - Se errore permanente: returns (True, None) per non riprovare
    """
    clean_model = model.replace("google/", "").replace(":free", "")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model}:generateContent?key={api_key}"

    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 32000
        }
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=180)

        if response.status_code == 200:
            result = response.json()
            try:
                text = result['candidates'][0]['content']['parts'][0]['text']
                return (True, text)
            except (KeyError, IndexError):
                print(f"    ❌ Risposta Gemini imprevista")
                return (True, None)

        elif response.status_code == 429:
            # Rate limit - segnala di riprovare dopo
            print("    ⚠️ Gemini rate limit (429) - riprovero piu tardi")
            return (False, None)

        else:
            print(f"    ❌ Errore Gemini {response.status_code}: {response.text[:200]}")
            return (True, None)

    except requests.exceptions.Timeout:
        print(f"    ⚠️ Timeout Gemini")
        return (True, None)
    except Exception as e:
        print(f"    ❌ Errore Gemini: {e}")
        return (True, None)


def call_openrouter(prompt: str, model: str, api_key: str):
    """
    Chiama OpenRouter API come fallback.

    Returns:
        tuple: (success: bool, response: str or None)
    """
    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/ptof-analysis",
        "X-Title": "PTOF Best Practice Report"
    }

    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 32000
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=300)

        if response.status_code == 200:
            result = response.json()
            try:
                text = result['choices'][0]['message']['content']
                return (True, text)
            except (KeyError, IndexError):
                print(f"      ❌ Risposta OpenRouter imprevista")
                return (True, None)

        elif response.status_code == 429:
            print(f"      ⚠️ OpenRouter rate limit (429)")
            return (False, None)

        else:
            print(f"      ❌ Errore OpenRouter {response.status_code}: {response.text[:200]}")
            return (True, None)

    except requests.exceptions.Timeout:
        print(f"      ⚠️ Timeout OpenRouter")
        return (True, None)
    except Exception as e:
        print(f"      ❌ Errore OpenRouter: {e}")
        return (True, None)


class BestPracticeOllamaAgent:
    """Agente per generare report incrementale sulle best practice con Ollama."""

    # Mapping tipo_scuola CSV -> intestazione report
    TIPO_SCUOLA_MAP = {
        'Infanzia': 'Nelle Scuole dell\'Infanzia',
        'Primaria': 'Nelle Scuole Primarie',
        'I Grado': 'Nelle Scuole Secondarie di Primo Grado',
        'Liceo': 'Nei Licei',
        'Tecnico': 'Negli Istituti Tecnici',
        'Professionale': 'Negli Istituti Professionali',
    }

    def __init__(self, analysis_dir=ANALYSIS_DIR, output_dir=OUTPUT_DIR,
                 ollama_url=OLLAMA_URL, model=OLLAMA_MODEL,
                 refactor_every=REFACTOR_EVERY, refactor_model=GEMINI_MODEL,
                 fallback_model=OPENROUTER_FALLBACK_MODEL):
        self.analysis_dir = analysis_dir
        self.output_dir = output_dir
        self.ollama_url = ollama_url
        self.model = model
        self.current_report = ""
        self.processed_schools = set()
        self.schools_count = 0

        # Gemini refactoring settings
        self.refactor_every = refactor_every
        self.refactor_model = refactor_model
        self.gemini_key = get_gemini_key()
        self.openrouter_key = get_openrouter_key()
        self.fallback_model = fallback_model  # Modello OpenRouter per fallback
        self.schools_since_refactor = 0
        self.refactor_pending = False  # True se rate limit, riprova dopo

        # Carica dati scuole dal CSV
        self.schools_csv_data = self._load_schools_csv()

    def _load_schools_csv(self):
        """Carica i dati delle scuole dal CSV."""
        import csv
        csv_path = 'data/analysis_summary.csv'
        schools_data = {}

        if os.path.exists(csv_path):
            try:
                with open(csv_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        school_id = row.get('school_id', '')
                        if school_id:
                            schools_data[school_id] = {
                                'denominazione': row.get('denominazione', ''),
                                'tipo_scuola': row.get('tipo_scuola', ''),
                                'regione': row.get('regione', ''),
                                'comune': row.get('comune', ''),
                            }
                print(f"📊 Caricati dati di {len(schools_data)} scuole dal CSV")
            except Exception as e:
                print(f"⚠️ Errore caricamento CSV: {e}")

        return schools_data

    def get_tipo_scuola_label(self, school_id):
        """Restituisce l'intestazione per il tipo di scuola."""
        if school_id not in self.schools_csv_data:
            return None

        tipo_scuola = self.schools_csv_data[school_id].get('tipo_scuola', '')

        # Il tipo_scuola può contenere più valori separati da virgola (es. "I Grado, Infanzia")
        # Prendiamo il primo valore significativo
        for tipo in tipo_scuola.split(','):
            tipo = tipo.strip()
            if tipo in self.TIPO_SCUOLA_MAP:
                return self.TIPO_SCUOLA_MAP[tipo]

        return None
        
    def call_ollama(self, prompt: str) -> str:
        """Chiama Ollama API."""
        url = f"{self.ollama_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_ctx": 16384,
                "num_predict": -1
            }
        }
        
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get('response', '')
                else:
                    print(f"    ❌ Errore Ollama {response.status_code}")
                    time.sleep(5)
                    
            except requests.exceptions.Timeout:
                print(f"    ⚠️ Timeout (attempt {attempt+1}/{MAX_RETRIES})")
                time.sleep(10)
            except requests.exceptions.ConnectionError:
                print(f"    ❌ Connessione fallita a {self.ollama_url}")
                time.sleep(5)
            except Exception as e:
                print(f"    ❌ Errore: {e}")
                time.sleep(5)
                
        return ""
    
    def load_progress(self):
        """Carica il progresso precedente e il report esistente."""
        # Carica report esistente SEMPRE (se esiste)
        output_path = os.path.join(self.output_dir, OUTPUT_FILE)
        if os.path.exists(output_path):
            with open(output_path, 'r', encoding='utf-8') as f:
                self.current_report = f.read()
            print(f"📄 Report esistente caricato ({len(self.current_report)} caratteri)")
        
        # Carica lista scuole già elaborate
        if os.path.exists(PROGRESS_FILE):
            try:
                with open(PROGRESS_FILE, 'r') as f:
                    data = json.load(f)
                    self.processed_schools = set(data.get('processed', []))
                    print(f"📂 Scuole già elaborate: {len(self.processed_schools)}")
            except:
                pass
    
    def save_progress(self):
        """Salva il progresso."""
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Salva checkpoint
        with open(PROGRESS_FILE, 'w') as f:
            json.dump({'processed': list(self.processed_schools)}, f)
        
        # Salva report
        output_path = os.path.join(self.output_dir, OUTPUT_FILE)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(self.current_report)
    
    def load_school_data(self, school_id):
        """Carica i dati di una scuola."""
        json_path = os.path.join(self.analysis_dir, f"{school_id}_PTOF_analysis.json")
        md_path = os.path.join(self.analysis_dir, f"{school_id}_PTOF_analysis.md")
        
        data = {'school_id': school_id, 'json': None, 'md': None}
        
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data['json'] = json.load(f)
            except:
                pass
        
        if os.path.exists(md_path):
            try:
                with open(md_path, 'r', encoding='utf-8') as f:
                    data['md'] = f.read()
            except:
                pass
        
        return data
    
    def calculate_maturity_index(self, json_data):
        """Calcola l'indice di maturità."""
        if not json_data or 'ptof_section2' not in json_data:
            return 0
        
        sec2 = json_data['ptof_section2']
        scores = []
        
        for key, value in sec2.items():
            if isinstance(value, dict):
                if 'score' in value and value['score'] is not None:
                    scores.append(value['score'])
                else:
                    for subval in value.values():
                        if isinstance(subval, dict) and 'score' in subval and subval['score'] is not None:
                            scores.append(subval['score'])
        
        return sum(scores) / len(scores) if scores else 0
    
    def extract_school_content(self, data):
        """Estrae contenuto rilevante per le best practice."""
        content = []
        school_id = data['school_id']

        # Prendi il tipo di scuola dal CSV (fonte affidabile)
        tipo_scuola_label = self.get_tipo_scuola_label(school_id)
        csv_data = self.schools_csv_data.get(school_id, {})

        # Metadata
        if data['json']:
            meta = data['json'].get('metadata', {})
            denominazione = csv_data.get('denominazione') or meta.get('denominazione', school_id)
            regione = csv_data.get('regione') or meta.get('regione', 'N/D')

            content.append(f"SCUOLA: {denominazione}")
            content.append(f"CODICE: {school_id}")
            # Usa il tipo di scuola dal CSV con l'etichetta corretta per il report
            if tipo_scuola_label:
                content.append(f"TIPOLOGIA SCUOLA: {tipo_scuola_label}")
            else:
                content.append(f"Tipo: {csv_data.get('tipo_scuola', 'N/D')}")
            content.append(f"Regione: {regione}")
            
            # Partnership
            sec2 = data['json'].get('ptof_section2', {})
            partners = sec2.get('2_2_partnership', {}).get('partner_nominati', [])
            if partners:
                content.append(f"Partnership: {', '.join(partners[:10])}")
        
        # Contenuto MD (punti di forza, azioni, metodologie)
        if data['md']:
            import re
            
            # Punti di forza
            match = re.search(r'###?\s*\d*\.?\s*Punti di Forza\s*\n(.*?)(?=###|\Z)', 
                            data['md'], re.DOTALL | re.IGNORECASE)
            if match:
                content.append(f"\nPUNTI DI FORZA:\n{match.group(1).strip()[:2000]}")
            
            # Didattica orientativa
            match = re.search(r'###?\s*\d*\.?\d*\.?\s*Didattica Orientativa\s*\n(.*?)(?=###|\Z)', 
                            data['md'], re.DOTALL | re.IGNORECASE)
            if match:
                content.append(f"\nDIDATTICA ORIENTATIVA:\n{match.group(1).strip()[:1500]}")
            
            # Opportunità formative
            match = re.search(r'###?\s*\d*\.?\d*\.?\s*Opportunit[àa]\s*\n(.*?)(?=###|\Z)', 
                            data['md'], re.DOTALL | re.IGNORECASE)
            if match:
                content.append(f"\nOPPORTUNITÀ FORMATIVE:\n{match.group(1).strip()[:1500]}")
            
            # Azioni di sistema
            match = re.search(r'###?\s*\d*\.?\d*\.?\s*(?:Governance|Azioni di Sistema)\s*\n(.*?)(?=###|\Z)', 
                            data['md'], re.DOTALL | re.IGNORECASE)
            if match:
                content.append(f"\nAZIONI DI SISTEMA:\n{match.group(1).strip()[:1500]}")
        
        return '\n'.join(content)
    
    # Tipologie di scuola per la struttura del report
    TIPOLOGIE_REPORT = [
        "Nelle Scuole dell'Infanzia",
        "Nelle Scuole Primarie",
        "Nelle Scuole Secondarie di Primo Grado",
        "Nei Licei",
        "Negli Istituti Tecnici",
        "Negli Istituti Professionali",
    ]

    # Categorie di best practice
    CATEGORIE_REPORT = [
        ("Metodologie Didattiche Innovative", "metodologie didattiche più efficaci"),
        ("Progetti e Attività Esemplari", "progetti concreti e attività di orientamento"),
        ("Partnership e Collaborazioni Strategiche", "collaborazioni con enti esterni, università, imprese"),
        ("Azioni di Sistema e Governance", "coordinamento e azioni sistemiche"),
        ("Buone Pratiche per l'Inclusione", "orientamento inclusivo, attento alle fragilità"),
        ("Esperienze Territoriali Significative", "legame con il territorio e specificità locali"),
    ]

    def build_initial_report(self):
        """Crea la struttura iniziale del report organizzata per tipologia di scuola."""
        report = f"""# Report sulle Best Practice dell'Orientamento nelle Scuole Italiane

*Report incrementale generato con {self.model}*
*Ultimo aggiornamento: {datetime.now().strftime('%d/%m/%Y %H:%M')}*

---

## Introduzione

Questo documento raccoglie le migliori pratiche sull'orientamento scolastico emerse dall'analisi dei PTOF delle scuole italiane. Il focus è sulle azioni concrete, le metodologie innovative e le esperienze replicabili che possono ispirare altre istituzioni scolastiche nel miglioramento delle proprie attività di orientamento.

L'orientamento scolastico rappresenta oggi una dimensione fondamentale dell'offerta formativa, chiamata a guidare gli studenti nella costruzione del proprio progetto di vita, nella scoperta delle proprie attitudini e nella scelta consapevole del percorso formativo e professionale.

Il report è organizzato per tipologia di scuola, permettendo di confrontare le pratiche specifiche di ogni ordine e grado.

---

"""
        # Genera sezioni per ogni tipologia di scuola
        for tipologia in self.TIPOLOGIE_REPORT:
            report += f"## {tipologia}\n\n"
            for categoria, descrizione in self.CATEGORIE_REPORT:
                report += f"### {categoria}\n\n"
                report += f"*{descrizione.capitalize()}.*\n\n"
                report += "---\n\n"

        return report
    
    def build_enrichment_prompt(self, school_content, current_section_count):
        """Costruisce il prompt per arricchire il report."""

        # Limita il report corrente per non superare il contesto
        report_excerpt = self.current_report[:12000] if len(self.current_report) > 12000 else self.current_report

        return f"""/no_think
SEI UN ESPERTO DI POLITICHE EDUCATIVE E ORIENTAMENTO SCOLASTICO.

HAI UN REPORT ESISTENTE sulle best practice dell'orientamento, ORGANIZZATO PER TIPOLOGIA DI SCUOLA.
Devi ARRICCHIRLO con le informazioni di una nuova scuola.

REPORT ESISTENTE (estratto):
{report_excerpt}

---

NUOVA SCUOLA DA ANALIZZARE:
{school_content}

---

COMPITO:
Analizza la nuova scuola e ARRICCHISCI il report esistente.

STRUTTURA DEL REPORT:
Il report è organizzato per TIPOLOGIA DI SCUOLA (## sezione principale), poi per CATEGORIA (### sottosezione):

## [Tipologia Scuola]
### [Categoria]
#### [Sottotitolo Specifico]
[Contenuto narrativo]

Le 6 TIPOLOGIE DI SCUOLA (sezioni ##) sono:
- Nelle Scuole dell'Infanzia
- Nelle Scuole Primarie
- Nelle Scuole Secondarie di Primo Grado
- Nei Licei
- Negli Istituti Tecnici
- Negli Istituti Professionali

Le 6 CATEGORIE (sottosezioni ###) sono:
- Metodologie Didattiche Innovative
- Progetti e Attività Esemplari
- Partnership e Collaborazioni Strategiche
- Azioni di Sistema e Governance
- Buone Pratiche per l'Inclusione
- Esperienze Territoriali Significative

REGOLE FONDAMENTALI:
1. NON riscrivere tutto il report, restituisci SOLO LE AGGIUNTE
2. LEGGI la TIPOLOGIA SCUOLA nei dati (es: "TIPOLOGIA SCUOLA: Nei Licei") per sapere in quale sezione ## inserire
3. I nomi dei PROGETTI devono essere sempre in **neretto** (es: **Progetto Futuro**)
4. **CRITICO**: OGNI attività/progetto DEVE includere SEMPRE il CODICE MECCANOGRAFICO e il NOME della scuola in **neretto**!
   - Formato: **CODICE** - **Nome Scuola**
   - Esempio: **RMIC8GA002** - **I.C. Via Roma**
   - QUESTO È OBBLIGATORIO per OGNI paragrafo che descrive un'attività!
5. RAGGRUPPA pratiche simili sotto SOTTOTITOLI SPECIFICI (usa #### per i sottotitoli)
6. I SOTTOTITOLI devono essere SPECIFICI e DESCRITTIVI dell'attività, non generici!
   - SBAGLIATO: "#### Orientamento Universitario" (troppo generico)
   - CORRETTO: "#### Visite ai campus e incontri con docenti universitari"
   - CORRETTO: "#### Stage estivi presso aziende del territorio"
7. NON fare elenchi puntati - scrivi in modo NARRATIVO e DISCORSIVO
8. Spiega COME funzionano le pratiche, non solo cosa sono
9. IGNORA informazioni generiche o poco significative
10. Se non ci sono elementi nuovi degni di nota, rispondi solo: "NESSUNA AGGIUNTA"

IMPORTANTE - TRACCIABILITÀ:
Ogni pratica DEVE essere attribuita alla scuola che la realizza.
Il lettore deve poter identificare SUBITO quale scuola implementa ogni attività.
NON scrivere MAI un'attività senza indicare la scuola e il suo codice meccanografico.

FORMATO OUTPUT:
Restituisci le aggiunte nel formato:

## [Tipologia Scuola] ##
### [Categoria] ###
#### [Sottotitolo Specifico che descrive l'attività]
[Testo da aggiungere, in forma narrativa]

Esempio corretto per un LICEO:
## Nei Licei ##
### Progetti e Attività Esemplari ###
#### Visite ai campus universitari e preparazione ai test d'ingresso
Particolarmente significativa è l'esperienza del **Progetto Ponte** di **RMPC030007** - **Liceo Virgilio**, che prevede un percorso strutturato di accompagnamento degli studenti del quinto anno attraverso visite guidate ai campus universitari, incontri con docenti delle varie facoltà e sessioni di simulazione dei test d'ingresso.

#### Laboratori di scoperta delle attitudini personali
Il **Liceo Scientifico Galilei** (**TOPS010203**) propone il **Progetto Scopri Te Stesso**, un percorso di auto-orientamento attraverso questionari attitudinali e colloqui individuali con psicologi dell'orientamento.

Esempio corretto per una SCUOLA PRIMARIA:
## Nelle Scuole Primarie ##
### Metodologie Didattiche Innovative ###
#### Giochi di ruolo sui mestieri
La **Scuola Primaria Rodari** (**ROEE8GA001**) introduce già nella classe quinta attività ludico-didattiche per esplorare i diversi mestieri e professioni attraverso il gioco di ruolo.

Se non ci sono elementi significativi, rispondi SOLO:
NESSUNA AGGIUNTA"""

    def parse_and_integrate(self, response):
        """Integra le aggiunte nel report organizzato per tipologia."""
        if not response or 'NESSUNA AGGIUNTA' in response.upper():
            return False

        import re

        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r'^```[a-zA-Z]*\s*', '', cleaned)
            cleaned = re.sub(r'\s*```$', '', cleaned)
            cleaned = cleaned.strip()

        # Pattern per tipologia di scuola (solo ## non ### o ####)
        tipologia_pattern = r'^##\s+([^#\n]+?)(?:\s*##)?\s*$'
        # Pattern per categoria (solo ### non ####)
        categoria_pattern = r'^###\s+([^#\n]+?)(?:\s*###)?\s*$'

        # Trova tutte le tipologie nell'output
        tipologia_matches = list(re.finditer(tipologia_pattern, cleaned, re.MULTILINE))

        if not tipologia_matches:
            print("    ⚠️ Nessuna tipologia riconosciuta dall'output Ollama")
            return False

        added = False

        for i, tipo_match in enumerate(tipologia_matches):
            tipologia_name = tipo_match.group(1).strip()

            # Estrai il blocco di contenuto per questa tipologia
            start = tipo_match.end()
            end = tipologia_matches[i + 1].start() if i + 1 < len(tipologia_matches) else len(cleaned)
            tipologia_block = cleaned[start:end]

            # Trova la tipologia corrispondente nel report
            tipologia_header = None
            for tipo in self.TIPOLOGIE_REPORT:
                if tipo.lower() in tipologia_name.lower() or tipologia_name.lower() in tipo.lower():
                    tipologia_header = f"## {tipo}"
                    break

            if not tipologia_header:
                continue

            # Trova le categorie in questo blocco
            categoria_matches = list(re.finditer(categoria_pattern, tipologia_block, re.MULTILINE))

            for j, cat_match in enumerate(categoria_matches):
                categoria_name = cat_match.group(1).strip()

                # Estrai il contenuto per questa categoria
                cat_start = cat_match.end()
                cat_end = categoria_matches[j + 1].start() if j + 1 < len(categoria_matches) else len(tipologia_block)
                content = tipologia_block[cat_start:cat_end].strip()

                if not content or len(content) < 50:
                    continue

                # Trova la categoria corrispondente nel report
                categoria_header = None
                for cat_name, _ in self.CATEGORIE_REPORT:
                    if cat_name.lower() in categoria_name.lower() or categoria_name.lower() in cat_name.lower():
                        categoria_header = f"### {cat_name}"
                        break

                if not categoria_header:
                    continue

                # Trova la posizione esatta nel report: tipologia + categoria
                tipo_idx = self.current_report.find(tipologia_header)
                if tipo_idx == -1:
                    continue

                # Trova la prossima tipologia (## )
                next_tipo_idx = self.current_report.find('\n## ', tipo_idx + len(tipologia_header))
                if next_tipo_idx == -1:
                    next_tipo_idx = len(self.current_report)

                # Cerca la categoria dentro questa tipologia
                cat_idx = self.current_report.find(categoria_header, tipo_idx, next_tipo_idx)
                if cat_idx == -1:
                    continue

                # Trova la prossima categoria (### ) o la prossima tipologia
                next_cat_idx = self.current_report.find('\n### ', cat_idx + len(categoria_header))
                if next_cat_idx == -1 or next_cat_idx > next_tipo_idx:
                    next_cat_idx = next_tipo_idx

                # Trova dove inserire (prima del ---)
                insert_pos = self.current_report.rfind('---', cat_idx, next_cat_idx)
                if insert_pos == -1:
                    insert_pos = next_cat_idx

                # Aggiungi il contenuto
                self.current_report = (
                    self.current_report[:insert_pos] +
                    f"\n\n{content}\n\n" +
                    self.current_report[insert_pos:]
                )
                added = True

        return added

    def build_refactor_prompt(self):
        """Costruisce il prompt per il refactoring con Gemini."""
        return f"""Sei un editor esperto di documenti educativi.

HAI UN REPORT sulle best practice dell'orientamento scolastico che è stato costruito INCREMENTALMENTE analizzando diverse scuole. Il report può avere ridondanze, ripetizioni e sottotitoli duplicati.

STRUTTURA DEL REPORT:
Il report è organizzato per TIPOLOGIA DI SCUOLA (## sezione principale), poi per CATEGORIA (### sottosezione):
- ## Nelle Scuole dell'Infanzia / Primarie / Secondarie di Primo Grado / Licei / Istituti Tecnici / Professionali
  - ### Metodologie Didattiche Innovative
  - ### Progetti e Attività Esemplari
  - ### Partnership e Collaborazioni Strategiche
  - ### Azioni di Sistema e Governance
  - ### Buone Pratiche per l'Inclusione
  - ### Esperienze Territoriali Significative

IL REPORT DA RIORGANIZZARE:
{self.current_report}

---

IL TUO COMPITO:
Riorganizza e migliora questo report mantenendo TUTTO il contenuto informativo ma:

1. ELIMINA RIDONDANZE: Se lo stesso concetto è ripetuto in più punti, unificalo in un unico paragrafo più completo
2. UNIFICA SOTTOTITOLI SIMILI: Se ci sono #### simili (es. "Visite ai campus" e "Orientamento universitario"), uniscili sotto un unico sottotitolo descrittivo
3. MIGLIORA LA NARRAZIONE: Rendi il testo più fluido con connettivi (inoltre, analogamente, in particolare, d'altra parte)
4. MANTIENI SEMPRE il CODICE e il NOME delle scuole in **neretto** (es: **RMIC8GA002** - **I.C. Via Roma**)
5. MANTIENI SEMPRE i nomi dei PROGETTI in **neretto** (es: **Progetto Futuro**)
6. NON ELIMINARE informazioni o esempi specifici - solo unificali e riorganizzali
7. MANTIENI LA STRUTTURA GERARCHICA: ## per tipologie di scuola, ### per categorie

REGOLE CRITICHE:
- NON inventare nuove informazioni
- NON eliminare esempi concreti di scuole
- PRESERVA tutti i nomi di progetti, partner e scuole menzionati
- Se due scuole hanno pratiche simili, descrivile insieme collegandole narrativamente

OUTPUT:
Restituisci IL REPORT COMPLETO riorganizzato in formato Markdown.
Non includere commenti o spiegazioni, solo il report."""

    def do_refactor(self):
        """Esegue il refactoring del report con Gemini."""
        if not self.gemini_key:
            print("    ⚠️ Chiave Gemini non configurata - skip refactoring")
            return False

        print(f"\n🔄 REFACTORING REPORT con Gemini ({self.refactor_model})...")
        prompt = self.build_refactor_prompt()

        success, response = call_gemini(prompt, self.refactor_model, self.gemini_key)

        if not success:
            # Rate limit - segna come pending per riprovare dopo
            self.refactor_pending = True
            return False

        if response:
            # Pulisci eventuali code blocks markdown
            if response.startswith("```markdown"):
                response = response.replace("```markdown", "", 1)
            if response.startswith("```"):
                response = response.replace("```", "", 1)
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

            # Verifica che il report non sia troppo corto (errore)
            if len(response) < len(self.current_report) * 0.5:
                print("    ⚠️ Report refactored troppo corto - mantengo originale")
                return False

            self.current_report = response
            self.schools_since_refactor = 0
            self.refactor_pending = False
            print("    ✅ Report riorganizzato con successo")
            return True
        else:
            print("    ⚠️ Nessuna risposta da Gemini - mantengo report originale")
            return False

    def build_full_synth_prompt(self):
        """Costruisce il prompt per la sintesi completa del report."""
        return f"""Sei un editor esperto di documenti educativi.

HAI UN REPORT COMPLETO sulle best practice dell'orientamento scolastico. Devi creare una SINTESI COMPLETA mantenendo la struttura e le informazioni chiave.

OBIETTIVI:
1. Riduci il testo del 30-50% eliminando ridondanze e ripetizioni
2. Mantieni la struttura delle sezioni principali:
   - ## Introduzione
   - ## Metodologie Didattiche Innovative
   - ## Progetti e Attività Esemplari
   - ## Partnership e Collaborazioni Strategiche
   - ## Azioni di Sistema e Governance
   - ## Buone Pratiche per l'Inclusione
   - ## Esperienze Territoriali Significative
3. Mantieni sempre il CODICE e il NOME della scuola in **neretto**
4. Mantieni sempre i nomi dei PROGETTI in **neretto**
5. Non inventare informazioni
6. Stile narrativo, evita elenchi puntati salvo indispensabili

REPORT ORIGINALE:
{self.current_report}

OUTPUT:
Restituisci il report completo in Markdown, senza commenti o spiegazioni."""

    def _load_synth_progress(self):
        """Carica il progresso della sintesi per capitoli."""
        data = {"full_synth_done": False, "sections": {}}
        if os.path.exists(SYNTH_PROGRESS_FILE):
            try:
                with open(SYNTH_PROGRESS_FILE, 'r') as f:
                    stored = json.load(f)
                if isinstance(stored, dict):
                    data.update(stored)
            except Exception:
                pass
        return data

    def _save_synth_progress(self, data):
        """Salva il progresso della sintesi per capitoli."""
        os.makedirs(self.output_dir, exist_ok=True)
        with open(SYNTH_PROGRESS_FILE, 'w') as f:
            json.dump(data, f, indent=2)

    def _clean_llm_response(self, text):
        """Pulisce eventuali code blocks e spazi."""
        import re
        if not text:
            return ""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r'^```[a-zA-Z]*\s*', '', cleaned)
            cleaned = re.sub(r'\s*```$', '', cleaned)
            cleaned = cleaned.strip()
        return cleaned

    def _is_refusal_response(self, text):
        """Rileva rifiuti o risposte non operative."""
        if not text:
            return True
        lowered = text.lower()
        refusal_markers = [
            "non posso",
            "non sono in grado",
            "mi dispiace",
            "non posso aiutare",
            "non posso assistere",
            "non posso soddisfare",
            "cannot",
            "can't",
            "i'm sorry",
            "as an ai",
            "unable to",
        ]
        return any(marker in lowered for marker in refusal_markers)

    def _validate_full_synth_response(self, text):
        """Valida la sintesi completa."""
        import re
        cleaned = text.strip()
        if self._is_refusal_response(cleaned):
            return False
        if not cleaned.startswith("#"):
            return False
        min_len = max(1200, int(len(self.current_report) * 0.2))
        if len(cleaned) < min_len:
            return False
        if len(re.findall(r'^##\s+', cleaned, re.MULTILINE)) < 3:
            return False
        return True

    def _validate_section_response(self, section_name, original, text):
        """Valida la sintesi di una singola sezione."""
        cleaned = text.strip()
        if self._is_refusal_response(cleaned):
            return False
        min_len = max(150, int(len(original) * 0.2))
        return len(cleaned) >= min_len

    def _strip_section_title(self, section_name, text):
        """Rimuove un titolo di sezione duplicato se presente."""
        import re
        cleaned = text.strip()
        pattern = rf'^##+\s*{re.escape(section_name)}\s*\n+'
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        return cleaned.strip()

    def _call_llm_with_retry(self, prompt, validate_fn, stage_label):
        """Chiama LLM con retry e fallback, senza avanzare finche non valida."""
        backoff = SYNTH_BACKOFF_START
        attempts = 0
        last_error = ""

        while True:
            attempts += 1
            if EXIT_REQUESTED:
                return None, attempts, "exit_requested", None

            response = None
            if self.gemini_key:
                success, response = call_gemini(prompt, self.refactor_model, self.gemini_key)
                if success and response:
                    response = self._clean_llm_response(response)
                    if validate_fn(response):
                        return response, attempts, "", "gemini"
                    last_error = "gemini_invalid"
                elif not success:
                    last_error = "gemini_rate_limit"
                else:
                    last_error = "gemini_error"

            if self.openrouter_key:
                if self.gemini_key:
                    print(f"      -> {stage_label}: fallback OpenRouter ({self.fallback_model})")
                success, response = call_openrouter(prompt, self.fallback_model, self.openrouter_key)
                if success and response:
                    response = self._clean_llm_response(response)
                    if validate_fn(response):
                        if self.gemini_key:
                            print(f"      OK {stage_label}: fallback OpenRouter riuscito")
                        return response, attempts, "", "openrouter"
                    last_error = "openrouter_invalid"
                elif not success:
                    last_error = "openrouter_rate_limit"
                else:
                    last_error = "openrouter_error"

            if not self.gemini_key and not self.openrouter_key:
                print("❌ Nessuna chiave LLM configurata")
                return None, attempts, "missing_keys", None

            wait_time = min(backoff, SYNTH_BACKOFF_MAX)
            print(f"      ⚠️ {stage_label}: {last_error}. Ritento tra {wait_time}s")
            time.sleep(wait_time)
            backoff = min(backoff * 2, SYNTH_BACKOFF_MAX)

    def _build_synth_report(self, header, sections, refactored_sections):
        """Ricostruisce il report sintetico includendo tutte le sezioni."""
        synth_report = header
        for section_name, section_content in sections.items():
            content = refactored_sections.get(section_name, section_content)
            synth_report += f"## {section_name}\n\n{content}\n\n"
        return synth_report

    def _build_provider_summary(self, sections, synth_state):
        """Costruisce una tabella provider per sezione (ultimo refactoring)."""
        if not synth_state:
            return ""
        section_states = synth_state.get("sections", {})
        rows = []
        for section_name in sections.keys():
            if section_name == "Introduzione":
                continue
            provider = section_states.get(section_name, {}).get("provider") or "N/D"
            rows.append(f"| {section_name} | {provider} |")
        if not rows:
            return ""
        table = "\n".join(["| Sezione | Provider |", "|---|---|"] + rows)
        return f"\n**Provider per sezione (ultimo refactoring):**\n\n{table}\n"

    def _build_synth_header(self, sections, synth_state):
        """Header per il report sintetico con provider effettivi."""
        provider_note = self._build_provider_summary(sections, synth_state)
        return f"""# Report Sintetico Best Practice Orientamento

*Modello primario: {self.refactor_model}*
*Basato su {len(self.processed_schools)} scuole analizzate*
*Generato il: {datetime.now().strftime('%d/%m/%Y %H:%M')}*
{provider_note}
---

"""

    def extract_sections(self, report_text):
        """Estrae le sezioni principali dal report."""
        import re
        sections = {}

        # Pattern per trovare le sezioni ##
        pattern = r'^## (.+?)$'
        matches = list(re.finditer(pattern, report_text, re.MULTILINE))

        for i, match in enumerate(matches):
            section_name = match.group(1).strip()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(report_text)
            content = report_text[start:end].strip()

            # Ignora sezioni vuote o troppo corte (mantieni sempre l'introduzione)
            if section_name == "Introduzione" or len(content) > 100:
                sections[section_name] = content

        return sections

    def build_section_refactor_prompt(self, section_name, section_content):
        """Costruisce il prompt per refactoring di una singola sezione."""
        return f"""Sei un editor esperto di documenti educativi e un autore di report professionali.

HAI UNA SEZIONE del report sulle best practice dell'orientamento scolastico. La sezione è stata costruita INCREMENTALMENTE e può avere ridondanze e ripetizioni.

SEZIONE: {section_name}

CONTENUTO:
{section_content}

---

IL TUO COMPITO:
Riscrivi questa sezione come un REPORT NARRATIVO PROFESSIONALE.

STILE NARRATIVO OBBLIGATORIO:
- Scrivi in PROSA DISCORSIVA, come un saggio o un articolo accademico
- EVITA i punti elenco (bullet points) - usali SOLO se strettamente necessario per liste tecniche
- Usa PARAGRAFI articolati con frasi complete e connettivi logici
- Spiega le diverse TIPOLOGIE DI ATTIVITÀ descrivendo COME funzionano, perché sono efficaci e quali risultati producono
- Collega narrativamente le esperienze di scuole diverse che adottano approcci simili
- Usa connettivi come: "In questo contesto...", "Analogamente...", "Un approccio particolarmente innovativo...", "Sul versante delle...", "Merita particolare attenzione..."

STRUTTURA:
- Ogni sottosezione (####) deve introdurre una TIPOLOGIA di pratica
- Descrivi la tipologia in modo generale, poi porta esempi concreti di scuole
- Spiega il VALORE AGGIUNTO di ogni approccio

REGOLE DI SINTESI:
1. ELIMINA RIDONDANZE: Unifica concetti ripetuti in un unico paragrafo
2. UNIFICA SOTTOTITOLI SIMILI: Raggruppa pratiche affini sotto un unico titolo descrittivo
3. RIDUCI del 30-50% mantenendo le informazioni chiave
4. MANTIENI il CODICE e il NOME delle scuole in **neretto**
5. MANTIENI i nomi dei PROGETTI in **neretto**

REGOLE CRITICHE:
- NON inventare informazioni
- PRESERVA almeno 3-5 esempi concreti di scuole per sottosezione
- Il testo deve essere FLUIDO, PROFESSIONALE e LEGGIBILE
- NO elenchi puntati dove possibile - preferisci sempre la prosa

OUTPUT:
Restituisci SOLO la sezione riscritta in Markdown (senza il titolo ##).
Non includere commenti o spiegazioni."""

    def do_full_synth(self, synth_state):
        """Esegue la sintesi completa del report e salva il file full."""
        if not self.current_report or len(self.current_report) < 1000:
            print("⚠️ Report troppo corto per la sintesi completa")
            return False

        if not self.gemini_key and not self.openrouter_key:
            print("⚠️ Nessuna chiave LLM configurata - impossibile creare report sintetico")
            return False

        print(f"\n🔄 SINTESI COMPLETA REPORT ({self.refactor_model})...")
        prompt = self.build_full_synth_prompt()
        response, attempts, last_error, provider = self._call_llm_with_retry(
            prompt,
            self._validate_full_synth_response,
            "Sintesi completa"
        )

        if response is None:
            return False

        self.current_report = response
        os.makedirs(self.output_dir, exist_ok=True)
        full_path = os.path.join(self.output_dir, OUTPUT_FILE_SYNTH_FULL)

        if os.path.exists(full_path):
            backup_path = full_path + '.bak'
            import shutil
            shutil.copy2(full_path, backup_path)
            print(f"   💾 Backup creato: {backup_path}")

        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(self.current_report)

        synth_state["full_synth_done"] = True
        synth_state["full_synth_attempts"] = attempts
        synth_state["full_synth_provider"] = provider or ""
        synth_state["full_synth_updated"] = datetime.now().isoformat()
        synth_state["full_synth_last_error"] = last_error
        self._save_synth_progress(synth_state)

        print(f"✅ Report sintetico completo salvato in: {full_path}")
        return True

    def do_section_refactor(self, synth_state=None):
        """Esegue la sintesi sezione per sezione e salva il report sintetico."""
        if not self.gemini_key and not self.openrouter_key:
            print("⚠️ Nessuna chiave LLM configurata - impossibile creare report sintetico")
            return False

        if not self.current_report or len(self.current_report) < 1000:
            print("⚠️ Report troppo corto per il refactoring")
            return False

        synth_state = synth_state or self._load_synth_progress()
        synth_state.setdefault("sections", {})

        print(f"\n🔄 CREAZIONE REPORT SINTETICO per sezioni ({self.refactor_model})...")

        sections = self.extract_sections(self.current_report)
        if not sections:
            print("⚠️ Nessuna sezione trovata nel report")
            return False

        print(f"   📑 Trovate {len(sections)} sezioni da processare")

        synth_path = os.path.join(self.output_dir, OUTPUT_FILE_SYNTH)
        existing_sections = {}
        if os.path.exists(synth_path):
            try:
                with open(synth_path, 'r', encoding='utf-8') as f:
                    existing_text = f.read()
                existing_sections = self.extract_sections(existing_text)
            except Exception:
                existing_sections = {}

        refactored_sections = {}
        completed = synth_state["sections"]

        for section_name, section_content in sections.items():
            if section_name == "Introduzione":
                refactored_sections[section_name] = section_content
                continue

            if completed.get(section_name, {}).get("status") == "completed":
                if section_name in existing_sections:
                    refactored_sections[section_name] = existing_sections[section_name]
                else:
                    completed.pop(section_name, None)

        if os.path.exists(synth_path):
            backup_path = synth_path + '.bak'
            import shutil
            shutil.copy2(synth_path, backup_path)
            print(f"   💾 Backup creato: {backup_path}")

        sections_list = list(sections.items())
        total_sections = len(sections_list)

        for i, (section_name, section_content) in enumerate(sections_list, start=1):
            if section_name == "Introduzione":
                continue

            if section_name in refactored_sections:
                print(f"   [{i}/{total_sections}] Sezione gia completata: {section_name[:40]}")
                continue

            print(f"   [{i}/{total_sections}] Refactoring: {section_name[:40]}...")

            prompt = self.build_section_refactor_prompt(section_name, section_content)
            response, attempts, last_error, provider = self._call_llm_with_retry(
                prompt,
                lambda text, sn=section_name, sc=section_content: self._validate_section_response(sn, sc, text),
                f"Sezione {section_name}"
            )

            if response is None:
                return False

            response = self._strip_section_title(section_name, response)
            refactored_sections[section_name] = response

            synth_state["sections"][section_name] = {
                "status": "completed",
                "attempts": attempts,
                "provider": provider or "",
                "last_error": last_error,
                "updated": datetime.now().isoformat()
            }
            self._save_synth_progress(synth_state)

            header = self._build_synth_header(sections, synth_state)
            synth_report = self._build_synth_report(header, sections, refactored_sections)
            with open(synth_path, 'w', encoding='utf-8') as f:
                f.write(synth_report)

        header = self._build_synth_header(sections, synth_state)
        synth_report = self._build_synth_report(header, sections, refactored_sections)
        with open(synth_path, 'w', encoding='utf-8') as f:
            f.write(synth_report)

        print(f"\n✅ Report sintetico salvato in: {synth_path}")
        print(f"   📊 Dimensione originale: {len(self.current_report):,} caratteri")
        print(f"   📊 Dimensione sintetico: {len(synth_report):,} caratteri")
        print(f"   📊 Riduzione totale: {(1 - len(synth_report) / len(self.current_report)) * 100:.0f}%")

        return True

    def _load_full_synth_for_refresh(self, synth_state):
        """Carica il report sintetico completo o lo rigenera se mancante."""
        full_path = os.path.join(self.output_dir, OUTPUT_FILE_SYNTH_FULL)
        if os.path.exists(full_path):
            with open(full_path, 'r', encoding='utf-8') as f:
                self.current_report = f.read()
            return True

        print("⚠️ Report sintetico completo non trovato, rigenero")
        synth_state["full_synth_done"] = False
        return self.do_full_synth(synth_state)

    def refresh_one_section(self, synth_state):
        """Rigenera la sintesi di un capitolo in modo ciclico."""
        if not self._load_full_synth_for_refresh(synth_state):
            return False

        sections = self.extract_sections(self.current_report)
        if not sections:
            print("⚠️ Nessuna sezione trovata nel report completo")
            return False

        section_names = [name for name in sections.keys() if name != "Introduzione"]
        if not section_names:
            print("⚠️ Nessun capitolo disponibile per il refresh")
            return False

        refresh_index = synth_state.get("refresh_index", 0) % len(section_names)
        section_name = section_names[refresh_index]
        section_content = sections[section_name]

        synth_path = os.path.join(self.output_dir, OUTPUT_FILE_SYNTH)
        if not os.path.exists(synth_path):
            print("⚠️ Report sintetico mancante, rigenero tutte le sezioni")
            return self.do_section_refactor(synth_state)

        print(f"🔁 Refresh capitolo: {section_name}")

        prompt = self.build_section_refactor_prompt(section_name, section_content)
        response, attempts, last_error, provider = self._call_llm_with_retry(
            prompt,
            lambda text, sn=section_name, sc=section_content: self._validate_section_response(sn, sc, text),
            f"Sezione {section_name}"
        )
        if response is None:
            return False

        response = self._strip_section_title(section_name, response)

        try:
            with open(synth_path, 'r', encoding='utf-8') as f:
                existing_text = f.read()
            existing_sections = self.extract_sections(existing_text)
        except Exception:
            existing_sections = {}

        refactored_sections = {}
        for name, content in sections.items():
            refactored_sections[name] = existing_sections.get(name, content)
        refactored_sections[section_name] = response

        synth_state.setdefault("sections", {})
        synth_state["sections"][section_name] = {
            "status": "refreshed",
            "attempts": attempts,
            "provider": provider or "",
            "last_error": last_error,
            "updated": datetime.now().isoformat()
        }
        synth_state["refresh_index"] = (refresh_index + 1) % len(section_names)
        synth_state["last_refresh"] = datetime.now().isoformat()
        self._save_synth_progress(synth_state)

        header = self._build_synth_header(sections, synth_state)
        synth_report = self._build_synth_report(header, sections, refactored_sections)
        with open(synth_path, 'w', encoding='utf-8') as f:
            f.write(synth_report)

        return True

    def run_synth(self):
        """Esegue sintesi completa e poi sintesi per capitoli."""
        if not self.current_report or len(self.current_report) < 1000:
            print("⚠️ Nessun report narrativo valido trovato. Esegui prima make best-practice-llm")
            return False

        if not self.gemini_key and not self.openrouter_key:
            print("⚠️ Nessuna chiave LLM configurata - impossibile creare report sintetico")
            return False

        synth_state = self._load_synth_progress()

        if not synth_state.get("full_synth_done"):
            if not self.do_full_synth(synth_state):
                return False
        else:
            full_path = os.path.join(self.output_dir, OUTPUT_FILE_SYNTH_FULL)
            if os.path.exists(full_path):
                with open(full_path, 'r', encoding='utf-8') as f:
                    self.current_report = f.read()
            else:
                print("⚠️ Report sintetico completo non trovato, rigenero")
                synth_state["full_synth_done"] = False
                if not self.do_full_synth(synth_state):
                    return False

        if not self.do_section_refactor(synth_state):
            return False

        if SYNTH_REFRESH_INTERVAL % 3600 == 0:
            interval_label = f"{SYNTH_REFRESH_INTERVAL // 3600} ore"
        else:
            interval_label = f"{SYNTH_REFRESH_INTERVAL // 60} minuti"
        print(f"🔁 Loop attivo: aggiorno un capitolo ogni {interval_label}")
        while not EXIT_REQUESTED:
            time.sleep(SYNTH_REFRESH_INTERVAL)
            if EXIT_REQUESTED:
                break
            if not self.refresh_one_section(synth_state):
                return False

        return True

    def get_schools_to_process(self):
        """Ottiene la lista delle scuole da processare (TUTTE le scuole)."""
        json_files = glob.glob(os.path.join(self.analysis_dir, "*_PTOF_analysis.json"))
        schools = []
        
        for f in json_files:
            school_id = os.path.basename(f).replace('_PTOF_analysis.json', '')
            if school_id in self.processed_schools:
                continue
            
            # Carica dati scuola (analizza TUTTE le scuole)
            data = self.load_school_data(school_id)
            if data['json'] or data['md']:  # Basta che abbia almeno uno dei due
                index = self.calculate_maturity_index(data['json']) if data['json'] else 0
                schools.append((school_id, index, data))
        
        # Ordina per indice decrescente (scuole migliori prima, ma analizza tutte)
        schools.sort(key=lambda x: x[1], reverse=True)
        return schools
    
    def run(self):
        """Esegue l'agente in modo incrementale (solo Ollama, senza refactoring Gemini)."""
        print("🚀 Avvio Best Practice Ollama Agent (Incrementale)")
        print(f"📂 Directory analisi: {self.analysis_dir}")
        print(f"🤖 Modello Ollama: {self.model}")
        print(f"🔗 Ollama URL: {self.ollama_url}")
        print(f"💡 Per il refactoring usa: make best-practice-llm-synth")
        print()
        
        # Carica progresso
        self.load_progress()
        
        # Se non c'è report, crealo
        if not self.current_report:
            self.current_report = self.build_initial_report()
            print("📝 Creato report iniziale")
        
        # Ottieni scuole da processare
        schools = self.get_schools_to_process()
        print(f"📊 Scuole da elaborare: {len(schools)}")
        print()
        
        if not schools:
            print("✅ Tutte le scuole sono già state elaborate!")
            return
        
        processed_count = 0
        for school_id, index, data in schools:
            if EXIT_REQUESTED:
                break
            
            print(f"📖 [{processed_count+1}/{len(schools)}] {school_id} (indice: {index:.2f})")
            
            # Estrai contenuto
            content = self.extract_school_content(data)
            if len(content) < 200:
                print("    ⏭️ Contenuto insufficiente, skip")
                self.processed_schools.add(school_id)
                self.save_progress()  # Salva subito
                continue
            
            # Chiama Ollama
            print("    🤖 Analisi con LLM...")
            prompt = self.build_enrichment_prompt(content, len(self.processed_schools))
            response = self.call_ollama(prompt)
            
            if response:
                added = self.parse_and_integrate(response)
                if added:
                    print("    ✅ Report arricchito")
                else:
                    print("    ⏭️ Nessun elemento nuovo")
            else:
                print("    ⚠️ Nessuna risposta da Ollama")
            
            self.processed_schools.add(school_id)
            processed_count += 1

            # Salva SEMPRE dopo ogni scuola
            self.save_progress()
            print(f"    💾 Report salvato ({len(self.processed_schools)} scuole totali)")

            # Breve pausa
            time.sleep(1)
        
        # Aggiorna metadata nel report
        import re
        # Rimuovi vecchia riga scuole analizzate se presente
        self.current_report = re.sub(r'\*Scuole analizzate: \d+\*\n', '', self.current_report)
        # Aggiorna timestamp
        self.current_report = re.sub(
            r'\*Ultimo aggiornamento: [^*]+\*',
            f'*Scuole analizzate: {len(self.processed_schools)}*\n*Ultimo aggiornamento: {datetime.now().strftime("%d/%m/%Y %H:%M")}*',
            self.current_report
        )
        
        # Salva finale
        self.save_progress()
        
        output_path = os.path.join(self.output_dir, OUTPUT_FILE)
        print()
        print(f"📄 Report salvato in: {output_path}")
        print(f"✅ Elaborate {processed_count} scuole in questa sessione")
        print(f"📊 Totale scuole nel report: {len(self.processed_schools)}")


def main():
    """Entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Best Practice Ollama Agent (Incrementale)')
    parser.add_argument('--model', default=OLLAMA_MODEL, help='Modello Ollama')
    parser.add_argument('--url', default=OLLAMA_URL, help='URL Ollama')
    parser.add_argument('--analysis-dir', default=ANALYSIS_DIR, help='Directory analisi')
    parser.add_argument('--output-dir', default=OUTPUT_DIR, help='Directory output')
    parser.add_argument('--reset', action='store_true', help='Ricomincia da zero')
    parser.add_argument('--refactor-every', type=int, default=REFACTOR_EVERY,
                        help=f'Ogni N scuole chiama Gemini per refactoring (default: {REFACTOR_EVERY})')
    parser.add_argument('--refactor-model', default=GEMINI_MODEL,
                        help=f'Modello Gemini per refactoring (default: {GEMINI_MODEL})')
    parser.add_argument('--fallback-model', default=OPENROUTER_FALLBACK_MODEL,
                        help=f'Modello OpenRouter fallback (default: {OPENROUTER_FALLBACK_MODEL})')
    parser.add_argument('--synth', action='store_true',
                        help='Genera solo il report sintetico dal report narrativo esistente')

    args = parser.parse_args()

    # Reset se richiesto
    if args.reset:
        if os.path.exists(PROGRESS_FILE):
            os.remove(PROGRESS_FILE)
        output_path = os.path.join(args.output_dir, OUTPUT_FILE)
        if os.path.exists(output_path):
            os.remove(output_path)
        print("🔄 Reset completato")

    agent = BestPracticeOllamaAgent(
        analysis_dir=args.analysis_dir,
        output_dir=args.output_dir,
        ollama_url=args.url,
        model=args.model,
        refactor_every=args.refactor_every,
        refactor_model=args.refactor_model,
        fallback_model=args.fallback_model
    )

    # Se richiesto solo report sintetico
    if args.synth:
        print("📝 Generazione Report Sintetico...")
        agent.load_progress()  # Carica il report esistente
        if agent.current_report:
            agent.run_synth()
        else:
            print("❌ Nessun report narrativo trovato. Esegui prima make best-practice-llm")
    else:
        agent.run()


if __name__ == '__main__':
    main()
