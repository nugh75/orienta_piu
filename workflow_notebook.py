# ══════════════════════════════════════════════════════════════════════
# COMPLETO ANALISI PTOF (VERSIONE SEMPLIFICATA)
# ══════════════════════════════════════════════════════════════════════
# 🚀 PDF → MD → Analisi Multi-Agente → JSON (arricchito) → rebuild_csv → CSV
# ✅ Catena dati: Normalizzazioni nel JSON, CSV è derivato (solo lettura)
import sys
import os
import re
import json
import shutil
import subprocess
import logging
import importlib
import signal
from pathlib import Path
from datetime import datetime
import time
import argparse

# Parse command line arguments
parser = argparse.ArgumentParser(description="Workflow analisi PTOF")
parser.add_argument("--force", action="store_true", help="Forza ri-analisi di tutti i file (ignora registro)")
parser.add_argument("--force-code", type=str, help="Forza ri-analisi di un codice specifico")
args, _ = parser.parse_known_args()

FORCE_REANALYSIS = args.force
FORCE_CODE = args.force_code

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Configurazione
BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)
sys.path.insert(0, str(BASE_DIR))

INBOX_DIR = BASE_DIR / "ptof_inbox"
PROCESSED_DIR = BASE_DIR / "ptof_processed"
MD_DIR = BASE_DIR / "ptof_md"
ANALYSIS_DIR = BASE_DIR / "analysis_results"
CSV_FILE = BASE_DIR / "data" / "analysis_summary.csv"
DOWNLOAD_LOCK = INBOX_DIR / ".download_in_progress"
WAIT_SECONDS = int(os.environ.get("PTOF_DOWNLOAD_WAIT_SECONDS", "10"))

# Flag per uscita controllata
EXIT_REQUESTED = False

def graceful_exit_handler(signum, frame):
    """Handler per uscita controllata con Ctrl+C."""
    global EXIT_REQUESTED
    if EXIT_REQUESTED:
        print("\n\n⚠️ Uscita forzata (seconda interruzione).", flush=True)
        sys.exit(1)
    
    EXIT_REQUESTED = True
    print("\n\n🛑 USCITA RICHIESTA - Salvataggio in corso...", flush=True)
    print("   (Premi Ctrl+C di nuovo per uscita forzata)", flush=True)

# Registra handler per SIGINT (Ctrl+C)
signal.signal(signal.SIGINT, graceful_exit_handler)

def save_and_exit():
    """Salva tutti i dati e esce in modo pulito."""
    print("\n📝 Salvataggio registro analisi...", flush=True)
    try:
        from src.utils.analysis_registry import save_registry, load_registry
        registry = load_registry()
        save_registry(registry)
        print("   ✅ Registro salvato", flush=True)
    except Exception as e:
        print(f"   ⚠️ Errore salvataggio registro: {e}", flush=True)
    
    print("\n📊 Rigenerazione CSV...", flush=True)
    try:
        subprocess.run([sys.executable, "src/data/rebuild_csv.py"], cwd=BASE_DIR, check=False, timeout=60)
        print("   ✅ CSV rigenerato", flush=True)
    except Exception as e:
        print(f"   ⚠️ Errore rigenerazione CSV: {e}", flush=True)
    
    print("\n✅ Uscita completata. I risultati parziali sono stati salvati.", flush=True)
    sys.exit(0)

# Crea directory
for d in [INBOX_DIR, PROCESSED_DIR, MD_DIR, ANALYSIS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

print("="*70, flush=True)
print("[workflow] 🚀 WORKFLOW COMPLETO ANALISI PTOF", flush=True)
print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
print("💡 Premi Ctrl+C per uscita controllata con salvataggio", flush=True)
print("="*70, flush=True)

# =====================================================
# INIZIALIZZAZIONE DATABASE MIUR
# =====================================================
print("\n🔧 Caricamento database...", flush=True)

import src.utils.school_database as school_db_module
importlib.reload(school_db_module)
from src.utils.school_database import SchoolDatabase

SchoolDatabase._instance = None
SchoolDatabase._loaded = False
SCHOOL_DB = SchoolDatabase()
print(f"   ✅ Database MIUR: {len(SCHOOL_DB._data)} scuole", flush=True)

# Carica registro analisi
from src.utils.analysis_registry import (
    load_registry, save_registry, is_already_analyzed,
    register_analysis, get_registry_stats, get_pending_files
)

ANALYSIS_REGISTRY = load_registry()
reg_stats = get_registry_stats()
print(f"   ✅ Registro analisi: {reg_stats['valid_entries']} file già analizzati", flush=True)
if FORCE_REANALYSIS:
    print(f"   ⚠️ Modalità FORCE attiva: tutti i file verranno ri-analizzati", flush=True)
if FORCE_CODE:
    print(f"   ⚠️ Forza ri-analisi per: {FORCE_CODE}", flush=True)

# Conta PDF
while True:
    # Controllo uscita richiesta
    if EXIT_REQUESTED:
        save_and_exit()
    
    inbox_pdfs = list(INBOX_DIR.glob("*.pdf"))
    print(f"\n📥 PDF in inbox: {len(inbox_pdfs)}", flush=True)

    if not inbox_pdfs:
        if DOWNLOAD_LOCK.exists():
            print(f"⏳ Download in corso, attendo {WAIT_SECONDS}s...", flush=True)
            time.sleep(WAIT_SECONDS)
            continue
        print("⚠️ Nessun PDF da processare!", flush=True)
        print("💡 Copia i PDF in ptof_inbox/ e riprova", flush=True)
    else:
        # =====================================================
        # STEP -1: VALIDAZIONE PTOF (PRE-ANALISI)
        # =====================================================
        print("\n" + "="*70, flush=True)
        print("[workflow] 🔍 STEP -1: Validazione PTOF (pre-analisi)", flush=True)
        print("="*70, flush=True)

        # Salta validazione se è stato specificato --force-code (l'utente sa che è valido)
        if FORCE_CODE:
            print(f"⏭️ Validazione saltata: --force-code {FORCE_CODE} specificato", flush=True)
        else:
            try:
                from src.validation.ptof_validator import validate_inbox
                validation_results = validate_inbox(move_invalid=True, use_registry=True)
                stats = validation_results.get("stats", {})
                if stats:
                    skipped = stats.get('skipped_already_valid', 0)
                    msg = (
                        f"   ✅ Validi: {stats.get('valid', 0)} | "
                        f"❌ Non PTOF: {stats.get('not_ptof', 0)} | "
                        f"📄 Troppo corti: {stats.get('too_short', 0)} | "
                        f"💔 Corrotti: {stats.get('corrupted', 0)} | "
                        f"❓ Ambigui: {stats.get('ambiguous', 0)}"
                    )
                    if skipped > 0:
                        msg += f" | ⏭️ Già validati: {skipped}"
                    print(msg, flush=True)
            except Exception as e:
                print(f"⚠️ Validazione PTOF fallita: {e}", flush=True)

        # Refresh inbox after validation
        inbox_pdfs = list(INBOX_DIR.glob("*.pdf"))
        print(f"\n📥 PDF in inbox dopo validazione: {len(inbox_pdfs)}", flush=True)
        if not inbox_pdfs:
            if DOWNLOAD_LOCK.exists():
                print(f"⏳ Download in corso, attendo {WAIT_SECONDS}s...", flush=True)
                time.sleep(WAIT_SECONDS)
                continue
            print("⚠️ Nessun PDF da processare!", flush=True)
            print("💡 Copia i PDF in ptof_inbox/ e riprova", flush=True)
            continue

        # =====================================================
        # STEP 0: VALIDAZIONE PRE-ANALISI
        # =====================================================
        print("\n" + "="*70, flush=True)
        print("[workflow] 🔍 STEP 0: Validazione codici meccanografici", flush=True)
        print("="*70, flush=True)
    
        recognized_pdfs = []
        process_pdfs = {}
        already_analyzed = set()
        code_pattern = re.compile(r'([A-Z]{2}[A-Z0-9]{2}[A-Z0-9]{6})', re.IGNORECASE)
    
        def extract_text_from_pdf(pdf_path, max_pages=4, max_chars=20000):
            text_parts = []
            total_chars = 0
            try:
                from pypdf import PdfReader
                reader = PdfReader(str(pdf_path))
                for i, page in enumerate(reader.pages):
                    if i >= max_pages:
                        break
                    try:
                        page_text = page.extract_text() or ""
                    except Exception:
                        continue
                    text_parts.append(page_text)
                    total_chars += len(page_text)
                    if total_chars >= max_chars:
                        break
                return "\n".join(text_parts).strip()
            except Exception:
                try:
                    import fitz
                    doc = fitz.open(str(pdf_path))
                    for i in range(min(max_pages, len(doc))):
                        page_text = doc[i].get_text("text") or ""
                        text_parts.append(page_text)
                        total_chars += len(page_text)
                        if total_chars >= max_chars:
                            break
                    return "\n".join(text_parts).strip()
                except Exception:
                    return ""

        def extract_school_code(name, school_db, pdf_path=None):
            def dedupe(candidates):
                seen = set()
                unique = []
                for code in candidates:
                    if code in seen:
                        continue
                    seen.add(code)
                    unique.append(code)
                return unique

            def pick_valid(candidates):
                if not school_db:
                    return None, None
                for code in candidates:
                    miur_data = school_db.get_school_data(code)
                    if miur_data:
                        return code, miur_data
                return None, None

            filename_candidates = code_pattern.findall(name.upper())
            filename_candidates = [c for c in filename_candidates if any(ch.isdigit() for ch in c)]
            filename_candidates = dedupe(filename_candidates)

            code, miur_data = pick_valid(filename_candidates)
            if code:
                return code, filename_candidates, miur_data, "filename"

            pdf_candidates = []
            if pdf_path is not None:
                text = extract_text_from_pdf(pdf_path)
                if text:
                    pdf_candidates = code_pattern.findall(text.upper())
                    pdf_candidates = [c for c in pdf_candidates if any(ch.isdigit() for ch in c)]
                    pdf_candidates = dedupe(pdf_candidates)
                    code, miur_data = pick_valid(pdf_candidates)
                    if code:
                        combined = filename_candidates + [c for c in pdf_candidates if c not in filename_candidates]
                        return code, combined, miur_data, "pdf"

            combined = filename_candidates + [c for c in pdf_candidates if c not in filename_candidates]
            if pdf_candidates:
                return pdf_candidates[0], combined, None, "pdf"
            if filename_candidates:
                return filename_candidates[0], combined, None, "filename"
            return None, [], None, None

        def json_status(path):
            if not path.exists():
                return 'missing'
            if path.stat().st_size == 0:
                return 'empty'
            try:
                json.loads(path.read_text())
            except Exception:
                return 'invalid'
            return 'valid'
    
        def get_analysis_status(school_code):
            candidates = [
                ANALYSIS_DIR / f"{school_code}_PTOF_analysis.json",
                ANALYSIS_DIR / f"{school_code}_analysis.json",
            ]
            statuses = [(path, json_status(path)) for path in candidates]
            for path, status in statuses:
                if status == 'valid':
                    return path, status
            for path, status in statuses:
                if status in ('empty', 'invalid'):
                    return path, status
            return candidates[0], 'missing'

        def choose_preferred_pdf(current_path, new_path):
            current_stat = current_path.stat()
            new_stat = new_path.stat()
            if new_stat.st_mtime != current_stat.st_mtime:
                return new_path if new_stat.st_mtime > current_stat.st_mtime else current_path
            if new_stat.st_size != current_stat.st_size:
                return new_path if new_stat.st_size > current_stat.st_size else current_path
            return current_path

        def get_priority(status, skip_reason):
            if skip_reason == 'new':
                return 0, 'new'
            if skip_reason == 'missing_json':
                return 1, 'missing_json'
            if status == 'empty':
                return 2, 'empty_json'
            if status == 'invalid':
                return 2, 'invalid_json'
            if skip_reason == 'modified':
                return 3, 'modified_pdf'
            if skip_reason == 'forced':
                return 4, 'forced'
            if skip_reason == 'hash_error':
                return 4, 'hash_error'
            return 5, skip_reason or status
    
        for pdf_path in inbox_pdfs:
            # Controllo uscita richiesta
            if EXIT_REQUESTED:
                save_and_exit()
            
            school_code, candidates, miur_data, source = extract_school_code(pdf_path.stem, SCHOOL_DB, pdf_path)
            if not school_code:
                print(f"❌ {pdf_path.name}: Codice non estratto", flush=True)
                continue
            if source == 'pdf':
                print(f"🔎 {pdf_path.name}: codice estratto dal PDF → {school_code}", flush=True)
            if len(candidates) > 1:
                print(f"⚠️ {pdf_path.name}: codici trovati {candidates}, scelto {school_code}", flush=True)
        
            if miur_data:
                print(f"✅ {school_code}: {miur_data.get('denominazione', 'ND')[:50]}", flush=True)
            else:
                print(f"⚠️ {school_code}: Non in MIUR (procedo comunque)", flush=True)
        
            recognized_pdfs.append((pdf_path, school_code, miur_data))
        
            analysis_path, status = get_analysis_status(school_code)
            
            # Controllo registro (basato su hash del PDF)
            is_done, skip_reason = is_already_analyzed(school_code, pdf_path, ANALYSIS_REGISTRY)
            
            # Forza ri-analisi se richiesto
            if FORCE_REANALYSIS or (FORCE_CODE and school_code == FORCE_CODE):
                is_done = False
                skip_reason = "forced"
                print(f"🔄 {school_code}: Ri-analisi forzata", flush=True)

            if status == 'valid' and is_done:
                if school_code not in already_analyzed:
                    print(f"⏭️ {school_code}: Già analizzato (hash verificato)", flush=True)
                    already_analyzed.add(school_code)
                continue
            
            # File modificato dall'ultima analisi
            if status == 'valid' and skip_reason == 'modified':
                print(f"🔄 {school_code}: PDF modificato, ri-analizzo", flush=True)
            elif status == 'empty':
                print(f"⚠️ {school_code}: JSON vuoto, rieseguo analisi", flush=True)
            elif status == 'invalid':
                print(f"⚠️ {school_code}: JSON non valido, rieseguo analisi", flush=True)
            elif skip_reason == 'new':
                print(f"🆕 {school_code}: Nuovo file da analizzare", flush=True)
            elif skip_reason == 'missing_json':
                print(f"⚠️ {school_code}: JSON mancante, rieseguo analisi", flush=True)
        
            if school_code in process_pdfs:
                kept = choose_preferred_pdf(process_pdfs[school_code][0], pdf_path)
                if kept == pdf_path:
                    print(f"⚠️ Duplicato {school_code}: tengo {pdf_path.name}, scarto {process_pdfs[school_code][0].name}", flush=True)
                    priority_value, priority_label = get_priority(status, skip_reason)
                    process_pdfs[school_code] = (pdf_path, school_code, miur_data, priority_value, priority_label)
                else:
                    print(f"⚠️ Duplicato {school_code}: tengo {process_pdfs[school_code][0].name}, scarto {pdf_path.name}", flush=True)
                continue
        
            priority_value, priority_label = get_priority(status, skip_reason)
            process_pdfs[school_code] = (pdf_path, school_code, miur_data, priority_value, priority_label)
    
        process_pdfs = sorted(process_pdfs.values(), key=lambda item: (item[3], item[0].name))
        print(f"\n📋 PDF riconosciuti: {len(recognized_pdfs)}", flush=True)
        print(f"📋 PDF da processare (deduplicati): {len(process_pdfs)}", flush=True)
        if process_pdfs:
            priority_counts = {}
            for _, _, _, _, reason in process_pdfs:
                priority_counts[reason] = priority_counts.get(reason, 0) + 1
            priority_order = [
                'new', 'missing_json', 'empty_json', 'invalid_json',
                'modified_pdf', 'forced', 'hash_error'
            ]
            ordered = sorted(
                priority_counts.items(),
                key=lambda item: priority_order.index(item[0]) if item[0] in priority_order else len(priority_order)
            )
            print("[workflow] Priorita analisi: new -> missing_json -> empty/invalid -> modified -> forced -> other", flush=True)
            print("[workflow] Coda per priorita: " + ", ".join(f"{key}={val}" for key, val in ordered), flush=True)
    
        # =====================================================
        # STEP 1: CONVERSIONE PDF → MARKDOWN
        # =====================================================
        print("\n" + "="*70, flush=True)
        print("[workflow] 📝 STEP 1: Conversione PDF → Markdown", flush=True)
        print("="*70, flush=True)
    
        from src.processing.convert_pdfs_to_md import pdf_to_markdown
    
        converted = []
    
        for pdf_path, school_code, miur_data, _, _ in process_pdfs:
            # Controllo uscita richiesta
            if EXIT_REQUESTED:
                save_and_exit()
            
            md_output = MD_DIR / f"{school_code}_ptof.md"
        
            # Verifica se già analizzato
            analysis_path, status = get_analysis_status(school_code)
            if status == 'valid':
                print(f"⏭️ Già analizzato: {school_code} ({analysis_path.name})", flush=True)
                continue
        
            print(f"🔄 Convertendo: {pdf_path.name} → {school_code}_ptof.md", flush=True)
        
            try:
                if pdf_to_markdown(str(pdf_path), str(md_output)):
                    converted.append((pdf_path, school_code, miur_data))
                    print(f"   ✅ Convertito!", flush=True)
                else:
                    print(f"   ❌ Errore conversione", flush=True)
            except Exception as e:
                print(f"   ❌ Errore: {e}", flush=True)
    
        print(f"\n📊 Convertiti: {len(converted)} file", flush=True)
    
        if converted:
            # =====================================================
            # STEP 2: ANALISI MULTI-AGENTE
            # =====================================================
            print("\n" + "="*70, flush=True)
            print("[workflow] 🤖 STEP 2: Analisi Multi-Agente", flush=True)
            print("="*70, flush=True)
        
            # Forza reload del modulo pipeline
            import app.agentic_pipeline as agentic_module
            importlib.reload(agentic_module)
            from app.agentic_pipeline import (
                AnalystAgent, RefinerAgent, ReviewerAgent, SynthesizerAgent,
                process_single_ptof
            )
        
            analyst = AnalystAgent()
            refiner = RefinerAgent()
            reviewer = ReviewerAgent()
            synthesizer = SynthesizerAgent()
        
            analyzed = []

            for pdf_path, school_code, miur_data in converted:
                # Controllo uscita richiesta
                if EXIT_REQUESTED:
                    save_and_exit()

                md_file = MD_DIR / f"{school_code}_ptof.md"

                if not md_file.exists():
                    print(f"⚠️ MD non trovato: {school_code}", flush=True)
                    continue

                print(f"\n📝 Analizzando: {school_code}", flush=True)

                try:
                    def status_cb(msg):
                        print(f"   {msg}", flush=True)

                    # process_single_ptof salva JSON già arricchito (con enrich_json_metadata)
                    result = process_single_ptof(
                        str(md_file),
                        analyst,
                        reviewer,
                        refiner,
                        synthesizer,
                        str(ANALYSIS_DIR),
                        status_callback=status_cb
                    )

                    if result:
                        analyzed.append(school_code)
                        # Leggi metadati dal JSON salvato per feedback
                        json_path = ANALYSIS_DIR / f"{school_code}_PTOF_analysis.json"
                        with open(json_path, 'r') as f:
                            data = json.load(f)
                        md_path = ANALYSIS_DIR / f"{school_code}_PTOF_analysis.md"
                        if not md_path.exists() or md_path.stat().st_size == 0:
                            print("   ⚠️ Report MD mancante o vuoto (narrativa non generata)", flush=True)
                        meta = data.get('metadata', {})
                        print(f"   ✅ Salvato - {meta.get('provincia', 'ND')}, {meta.get('regione', 'ND')}", flush=True)

                        # Registra nel registro analisi
                        ANALYSIS_REGISTRY = register_analysis(
                            school_code=school_code,
                            pdf_path=pdf_path,
                            json_path=json_path,
                            md_path=md_file,
                            registry=ANALYSIS_REGISTRY,
                            auto_save=True
                        )
                        print(f"   📝 Registrato nel registro analisi", flush=True)
                    else:
                        print(f"   ⚠️ Nessun risultato", flush=True)

                except Exception as e:
                    print(f"   ❌ Errore analisi: {e}", flush=True)
                    import traceback
                    traceback.print_exc()

            print(f"\n📊 Analizzati: {len(analyzed)} file", flush=True)
    
    # =====================================================
    # STEP 2.5: AUTO-FILL REGIONI DA COMUNI
    # =====================================================
    print("\n" + "="*70, flush=True)
    print("[workflow] 🧭 STEP 2.5: Auto-fill regioni da comuni", flush=True)
    print("="*70, flush=True)
    
    result = subprocess.run(
        ['python3', 'src/processing/autofill_region_from_comuni.py'],
        capture_output=True, text=True, cwd=str(BASE_DIR)
    )
    print(result.stdout, flush=True)
    if result.returncode != 0:
        print(f"⚠️ Errore: {result.stderr}", flush=True)

    # =====================================================
    # STEP 3: REBUILD CSV DA JSON
    # =====================================================
    print("\n" + "="*70, flush=True)
    print("[workflow] 📊 STEP 3: Rebuild CSV da JSON", flush=True)
    print("="*70, flush=True)
    
    # Esegui rebuild_csv_clean.py
    result = subprocess.run(
        ['python3', 'src/processing/rebuild_csv_clean.py'],
        capture_output=True, text=True, cwd=str(BASE_DIR)
    )
    print(result.stdout, flush=True)
    if result.returncode != 0:
        print(f"⚠️ Errore: {result.stderr}", flush=True)
    
    # =====================================================
    # STEP 4: VERIFICA CSV FINALE
    # =====================================================
    print("\n" + "="*70, flush=True)
    print("[workflow] 📊 STEP 4: Verifica CSV", flush=True)
    print("="*70, flush=True)
    
    if CSV_FILE.exists():
        import pandas as pd
        df = pd.read_csv(CSV_FILE)
        print(f"📊 CSV contiene {len(df)} scuole", flush=True)
        print(f"\nColonne principali:", flush=True)
        print(df[['school_id', 'denominazione', 'provincia', 'regione', 'area_geografica', 'ptof_orientamento_maturity_index']].to_string(), flush=True)
    else:
        print("⚠️ CSV non ancora creato", flush=True)
    
    # =====================================================
    # STEP 5: SPOSTA PDF PROCESSATI
    # =====================================================
    print("\n" + "="*70, flush=True)
    print("[workflow] 📦 STEP 5: Organizzazione file processati", flush=True)
    print("="*70, flush=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    batch_dir = PROCESSED_DIR / f"batch_{timestamp}"
    batch_dir.mkdir(exist_ok=True)
    
    processed_count = 0
    for pdf_path, school_code, _ in recognized_pdfs:
        analysis_path, status = get_analysis_status(school_code)
        if status == 'valid':
            dest = batch_dir / pdf_path.name
            shutil.move(str(pdf_path), str(dest))
            processed_count += 1
            print(f"📦 Spostato: {pdf_path.name}", flush=True)
        else:
            print(f"⚠️ Analisi non valida ({analysis_path.name}), non sposto: {pdf_path.name}", flush=True)
    
    print(f"\n📊 PDF spostati in batch: {processed_count}", flush=True)
    
    # =====================================================
    # RIEPILOGO FINALE
    # =====================================================
    print("\n" + "="*70, flush=True)
    print("[workflow] 📊 RIEPILOGO FINALE", flush=True)
    print("="*70, flush=True)
    
    final_count = len(list(ANALYSIS_DIR.glob("*_analysis.json")))
    print(f"📁 Totale analisi JSON: {final_count}", flush=True)
    print(f"📊 CSV generato: {CSV_FILE}", flush=True)
    print(f"\n💡 Catena dati:", flush=True)
    print(f"   JSON (verità) → rebuild_csv_clean.py → CSV (derivato)", flush=True)
    print(f"\n🚀 Avvia dashboard: streamlit run app/Home.py", flush=True)
    print("="*70, flush=True)
    if DOWNLOAD_LOCK.exists():
        print(f"\n⏳ Download in corso, attendo {WAIT_SECONDS}s per nuovi PDF...", flush=True)
        time.sleep(WAIT_SECONDS)
        continue
    break
