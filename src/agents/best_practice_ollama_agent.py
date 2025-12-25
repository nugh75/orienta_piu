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
PROGRESS_FILE = 'reports/.best_practice_progress.json'

# Ollama settings
OLLAMA_URL = os.environ.get('OLLAMA_URL', "http://192.168.129.14:11434")
OLLAMA_MODEL = os.environ.get('MODEL', "qwen3:32b")
MAX_RETRIES = 3
REQUEST_TIMEOUT = 300

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
            print(f"    ⚠️ Gemini rate limit (429) - riproverò dopo altre {REFACTOR_EVERY} scuole")
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
                if 'score' in value:
                    scores.append(value['score'])
                else:
                    for subval in value.values():
                        if isinstance(subval, dict) and 'score' in subval:
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
    
    def build_initial_report(self):
        """Crea la struttura iniziale del report."""
        return f"""# Report sulle Best Practice dell'Orientamento nelle Scuole Italiane

*Report incrementale generato con {self.model}*
*Ultimo aggiornamento: {datetime.now().strftime('%d/%m/%Y %H:%M')}*

---

## Introduzione

Questo documento raccoglie le migliori pratiche sull'orientamento scolastico emerse dall'analisi dei PTOF delle scuole italiane. Il focus è sulle azioni concrete, le metodologie innovative e le esperienze replicabili che possono ispirare altre istituzioni scolastiche nel miglioramento delle proprie attività di orientamento.

L'orientamento scolastico rappresenta oggi una dimensione fondamentale dell'offerta formativa, chiamata a guidare gli studenti nella costruzione del proprio progetto di vita, nella scoperta delle proprie attitudini e nella scelta consapevole del percorso formativo e professionale.

---

## Metodologie Didattiche Innovative

In questa sezione vengono descritte le metodologie didattiche più efficaci adottate dalle scuole per l'orientamento.

---

## Progetti e Attività Esemplari

Raccolta di progetti concreti e attività di orientamento che si distinguono per efficacia e innovatività.

---

## Partnership e Collaborazioni Strategiche

Le collaborazioni con enti esterni, università, imprese e territorio rappresentano un elemento chiave per un orientamento efficace.

---

## Azioni di Sistema e Governance

Organizzazione, coordinamento e azioni sistemiche per garantire un orientamento strutturato e continuo.

---

## Buone Pratiche per l'Inclusione

Approcci e azioni specifiche per garantire un orientamento inclusivo, attento alle fragilità e alle diverse esigenze.

---

## Esperienze Territoriali Significative

Iniziative che valorizzano il legame con il territorio e le specificità locali.

---

"""
    
    def build_enrichment_prompt(self, school_content, current_section_count):
        """Costruisce il prompt per arricchire il report."""
        
        # Limita il report corrente per non superare il contesto
        report_excerpt = self.current_report[:12000] if len(self.current_report) > 12000 else self.current_report
        
        return f"""/no_think
SEI UN ESPERTO DI POLITICHE EDUCATIVE E ORIENTAMENTO SCOLASTICO.

HAI UN REPORT ESISTENTE sulle best practice dell'orientamento. Devi ARRICCHIRLO con le informazioni di una nuova scuola.

REPORT ESISTENTE (estratto):
{report_excerpt}

---

NUOVA SCUOLA DA ANALIZZARE:
{school_content}

---

COMPITO:
Analizza la nuova scuola e ARRICCHISCI il report esistente.

REGOLE FONDAMENTALI:
1. NON riscrivere tutto il report, restituisci SOLO LE AGGIUNTE o MODIFICHE
2. I nomi dei PROGETTI devono essere sempre in **neretto** (es: **Progetto Futuro**)
3. Il CODICE MECCANOGRAFICO e il NOME della scuola devono essere SEMPRE in **neretto** (es: **RMIC8GA002** - **I.C. Via Roma**)
4. RAGGRUPPA pratiche simili sotto SOTTOTITOLI SPECIFICI (usa #### per i sottotitoli)
5. I SOTTOTITOLI devono essere SPECIFICI e DESCRITTIVI dell'attività, non generici!
   - SBAGLIATO: "#### Orientamento Universitario" (troppo generico)
   - CORRETTO: "#### Visite ai campus e incontri con docenti universitari"
   - CORRETTO: "#### Simulazioni di test d'ingresso e preparazione ai concorsi"
   - CORRETTO: "#### Stage estivi presso aziende del territorio"
   - CORRETTO: "#### Laboratori di autobiografia e scoperta delle attitudini"
6. Se nel report esistente c'è già un sottotitolo che descrive la stessa attività, aggiungi sotto quello
7. Se trovi una NUOVA TIPOLOGIA di attività, CREA UN NUOVO SOTTOTITOLO specifico
8. NON fare elenchi puntati - scrivi in modo NARRATIVO e DISCORSIVO
9. Spiega COME funzionano le pratiche, non solo cosa sono
10. Cita SEMPRE il CODICE e il NOME della scuola in **neretto** quando descrivi una pratica specifica
11. Se una pratica è simile a una già presente, collegale narrativamente
12. IGNORA informazioni generiche o poco significative
13. Se non ci sono elementi nuovi degni di nota, rispondi solo: "NESSUNA AGGIUNTA"

DIVISIONE PER TIPO DI SCUOLA (OBBLIGATORIA):
All'interno di ogni sottotitolo (####), ORGANIZZA il contenuto per TIPO DI SCUOLA usando ##### come intestazione.

IMPORTANTE: La TIPOLOGIA SCUOLA è indicata nei dati della scuola (es: "TIPOLOGIA SCUOLA: Nei Licei").
USA ESATTAMENTE quella tipologia come intestazione ##### per inserire il contenuto nella sezione corretta.

Le 6 tipologie possibili sono:
- ##### Nelle Scuole dell'Infanzia
- ##### Nelle Scuole Primarie
- ##### Nelle Scuole Secondarie di Primo Grado
- ##### Nei Licei
- ##### Negli Istituti Tecnici
- ##### Negli Istituti Professionali

Questo permette di confrontare come la stessa pratica viene declinata nei diversi ordini e gradi di scuola.

ESEMPI DI SOTTOTITOLI SPECIFICI (creane di simili):
- #### Visite ai campus universitari e open day
- #### Simulazioni di colloqui di lavoro
- #### Stage e tirocini presso aziende locali
- #### Laboratori di scoperta delle attitudini personali
- #### Mentoring tra studenti di anni diversi
- #### Incontri con professionisti e testimonianze
- #### Percorsi di orientamento narrativo e autobiografico
- #### Certificazioni linguistiche e informatiche
- #### Sportelli di ascolto e supporto psicologico
- #### Progetti ponte con la scuola secondaria di primo grado
- #### Collaborazioni con ITS e formazione professionale
- (CREA NUOVI sottotitoli specifici per ogni nuova tipologia di attività!)

STILE:
- Paragrafi articolati e collegati
- Connettivi logici (inoltre, analogamente, in particolare, d'altra parte)
- Progetti in **neretto**
- Sottotitoli SPECIFICI con #### che descrivono l'attività concreta
- Sotto-sottotitoli ##### per tipo di scuola
- Spiegazioni dettagliate di COME si realizzano le pratiche

FORMATO OUTPUT:
Restituisci le aggiunte nel formato:

### [SEZIONE] ###
#### [Sottotitolo Specifico che descrive l'attività]
##### [Tipo di Scuola]
[Testo da aggiungere, in forma narrativa]

Le sezioni principali sono:
- Metodologie Didattiche Innovative
- Progetti e Attività Esemplari
- Partnership e Collaborazioni Strategiche
- Azioni di Sistema e Governance
- Buone Pratiche per l'Inclusione
- Esperienze Territoriali Significative

Esempio corretto:
### Progetti e Attività Esemplari ###
#### Visite ai campus universitari e preparazione ai test d'ingresso
##### Nei Licei
Particolarmente significativa è l'esperienza del **Progetto Ponte** di **RMPC030007** - **Liceo Virgilio**, che prevede un percorso strutturato di accompagnamento degli studenti del quinto anno attraverso visite guidate ai campus universitari, incontri con docenti delle varie facoltà e sessioni di simulazione dei test d'ingresso.

##### Negli Istituti Tecnici
Il **Progetto Futuro Prossimo** di **TOTF030517** - **I.T.I.S. Galilei** propone stage estivi presso le facoltà universitarie, con particolare enfasi sulle lauree STEM e ingegneria.

##### Negli Istituti Professionali
L'**I.P.S.I.A. Fermi** (**NARI030005**) integra l'orientamento universitario con percorsi verso gli ITS, proponendo visite sia agli atenei che agli Istituti Tecnici Superiori del territorio.

#### Laboratori di scoperta delle attitudini personali
##### Nelle Scuole Secondarie di Primo Grado
La **Scuola Media Mazzini** (**ROMM8GA002**) propone il **Progetto Scopri Te Stesso**, un percorso triennale che accompagna gli studenti nella scoperta delle proprie attitudini attraverso questionari, colloqui individuali e attività laboratoriali.

##### Nelle Scuole Primarie
La **Scuola Primaria Rodari** (**ROEE8GA001**) introduce già nella classe quinta attività ludico-didattiche per esplorare i diversi mestieri e professioni attraverso il gioco di ruolo.

##### Nelle Scuole dell'Infanzia
La **Scuola dell'Infanzia Montessori** (**ROAA8GA003**) propone attività di esplorazione sensoriale e gioco simbolico che gettano le basi per la futura consapevolezza delle proprie inclinazioni.

Se non ci sono elementi significativi, rispondi SOLO:
NESSUNA AGGIUNTA"""

    def parse_and_integrate(self, response):
        """Integra le aggiunte nel report."""
        if not response or 'NESSUNA AGGIUNTA' in response.upper():
            return False
        
        import re
        
        # Trova le sezioni da aggiungere
        sections = re.findall(r'###\s*([^#]+?)\s*###\s*\n(.*?)(?=###|\Z)', response, re.DOTALL)
        
        added = False
        for section_name, content in sections:
            section_name = section_name.strip()
            content = content.strip()
            
            if not content or len(content) < 50:
                continue
            
            # Trova la sezione nel report e aggiungi il contenuto
            section_patterns = [
                ('Metodologie Didattiche', '## Metodologie Didattiche Innovative'),
                ('Progetti', '## Progetti e Attività Esemplari'),
                ('Partnership', '## Partnership e Collaborazioni Strategiche'),
                ('Azioni di Sistema', '## Azioni di Sistema e Governance'),
                ('Governance', '## Azioni di Sistema e Governance'),
                ('Inclusione', '## Buone Pratiche per l\'Inclusione'),
                ('Territoriali', '## Esperienze Territoriali Significative'),
            ]
            
            for pattern, header in section_patterns:
                if pattern.lower() in section_name.lower():
                    # Trova la posizione della sezione
                    idx = self.current_report.find(header)
                    if idx != -1:
                        # Trova la fine della sezione (prossimo ## o fine)
                        next_section = self.current_report.find('\n## ', idx + len(header))
                        if next_section == -1:
                            next_section = len(self.current_report)
                        
                        # Inserisci prima del prossimo ---
                        insert_pos = self.current_report.rfind('---', idx, next_section)
                        if insert_pos == -1:
                            insert_pos = next_section
                        
                        # Aggiungi il contenuto
                        self.current_report = (
                            self.current_report[:insert_pos] + 
                            f"\n\n{content}\n\n" + 
                            self.current_report[insert_pos:]
                        )
                        added = True
                        break
        
        return added

    def build_refactor_prompt(self):
        """Costruisce il prompt per il refactoring con Gemini."""
        return f"""Sei un editor esperto di documenti educativi.

HAI UN REPORT sulle best practice dell'orientamento scolastico che è stato costruito INCREMENTALMENTE analizzando diverse scuole. Il report può avere ridondanze, ripetizioni e sottotitoli duplicati.

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
7. MANTIENI LA STRUTTURA delle sezioni principali (## Metodologie, ## Progetti, etc.)

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

            # Ignora sezioni vuote o troppo corte
            if len(content) > 100:
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

    def do_section_refactor(self):
        """Esegue il refactoring sezione per sezione e salva il report sintetico."""
        if not self.gemini_key:
            print("⚠️ Chiave Gemini non configurata - impossibile creare report sintetico")
            return False

        if not self.current_report or len(self.current_report) < 1000:
            print("⚠️ Report troppo corto per il refactoring")
            return False

        print(f"\n🔄 CREAZIONE REPORT SINTETICO per sezioni con Gemini ({self.refactor_model})...")

        # Estrai l'header (titolo, intro, metadata)
        import re
        intro_match = re.search(r'^(# .+?)\n---\n\n## Introduzione\n\n(.+?)\n\n---',
                                self.current_report, re.DOTALL)
        if intro_match:
            header = intro_match.group(0)
        else:
            header = "# Report Sintetico Best Practice Orientamento\n\n---\n\n"

        # Estrai le sezioni
        sections = self.extract_sections(self.current_report)

        if not sections:
            print("⚠️ Nessuna sezione trovata nel report")
            return False

        print(f"   📑 Trovate {len(sections)} sezioni da processare")

        # Refactora ogni sezione
        refactored_sections = {}
        for i, (section_name, section_content) in enumerate(sections.items()):
            if section_name == "Introduzione":
                # L'introduzione la teniamo com'è
                refactored_sections[section_name] = section_content
                continue

            print(f"   [{i+1}/{len(sections)}] Refactoring: {section_name[:40]}...")

            prompt = self.build_section_refactor_prompt(section_name, section_content)

            # Prova prima Gemini
            success, response = call_gemini(prompt, self.refactor_model, self.gemini_key)

            # Se Gemini ha rate limit, prova OpenRouter come fallback
            if not success and self.openrouter_key:
                print(f"      🔄 Fallback a OpenRouter ({self.fallback_model})...")
                time.sleep(2)
                success, response = call_openrouter(prompt, self.fallback_model, self.openrouter_key)

            if not success:
                print(f"      ⚠️ Rate limit su entrambi - mantengo sezione originale")
                refactored_sections[section_name] = section_content
                time.sleep(5)  # Pausa prima della prossima chiamata
                continue

            if response:
                # Pulisci eventuali code blocks
                if response.startswith("```markdown"):
                    response = response.replace("```markdown", "", 1)
                if response.startswith("```"):
                    response = response.replace("```", "", 1)
                if response.endswith("```"):
                    response = response[:-3]
                response = response.strip()

                # Verifica che non sia troppo corto
                if len(response) < len(section_content) * 0.2:
                    print(f"      ⚠️ Sezione troppo corta - mantengo originale")
                    refactored_sections[section_name] = section_content
                else:
                    refactored_sections[section_name] = response
                    reduction = (1 - len(response) / len(section_content)) * 100
                    print(f"      ✅ Riduzione: {reduction:.0f}%")
            else:
                print(f"      ⚠️ Nessuna risposta - mantengo originale")
                refactored_sections[section_name] = section_content

            time.sleep(2)  # Pausa tra le chiamate

        # Ricostruisci il report sintetico
        synth_report = f"""# Report Sintetico Best Practice Orientamento

*Report sintetico generato con {self.refactor_model}*
*Basato su {len(self.processed_schools)} scuole analizzate*
*Generato il: {datetime.now().strftime('%d/%m/%Y %H:%M')}*

---

"""
        for section_name, section_content in refactored_sections.items():
            synth_report += f"## {section_name}\n\n{section_content}\n\n---\n\n"

        # Salva il report sintetico (con backup se esiste già)
        synth_path = os.path.join(self.output_dir, OUTPUT_FILE_SYNTH)

        # Crea backup se esiste già un report sintetico
        if os.path.exists(synth_path):
            backup_path = synth_path + '.bak'
            import shutil
            shutil.copy2(synth_path, backup_path)
            print(f"   💾 Backup creato: {backup_path}")

        with open(synth_path, 'w', encoding='utf-8') as f:
            f.write(synth_report)

        print(f"\n✅ Report sintetico salvato in: {synth_path}")
        print(f"   📊 Dimensione originale: {len(self.current_report):,} caratteri")
        print(f"   📊 Dimensione sintetico: {len(synth_report):,} caratteri")
        print(f"   📊 Riduzione totale: {(1 - len(synth_report) / len(self.current_report)) * 100:.0f}%")

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
            agent.do_section_refactor()
        else:
            print("❌ Nessun report narrativo trovato. Esegui prima make best-practice-llm")
    else:
        agent.run()


if __name__ == '__main__':
    main()
