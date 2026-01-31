#!/usr/bin/env python3
"""
PTOF Code Cleaner Agent
=======================

Questo script scandaglia la directory dei file PTOF (MD), identifica discrepanze
tra il codice meccanografico nel nome file e quello nel contenuto, e propone
azioni correttive (rinomina/spostamento).

Usa un approccio a 3 fasi:
1. Analisi nome file (target atteso)
2. Euristiche Regex (ricerca pattern nel testo)
3. LLM Validation (Ollama/altro provider per casi ambigui)

Autore: Antigravity Agent
Date: 2026-01-31
"""

import os
import sys
import re
import json
import csv
import logging
import argparse
import shutil
from pathlib import Path
from collections import Counter
from typing import Optional, Dict, List, Tuple
from dotenv import load_dotenv

# Carica variabili d'ambiente da .env
load_dotenv()

# Configurazione Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler('ptof_cleaner.log')]
)
logger = logging.getLogger(__name__)

# Pattern Regex per codici scuola
# Formato: 2 lettere (provincia) + 2 caratteri (tipo) + 6 caratteri alfanumerici
# Nota: Rimosso \b finale per supportare suffix come _ptof
SCHOOL_CODE_PATTERN = re.compile(r'([A-Z]{2}[A-Z0-9]{2}[A-Z0-9]{6})', re.IGNORECASE)
SCHOOL_CODE_STRICT = re.compile(r'\b([A-Z]{2}[A-Z0-9]{2}\d{5}[A-Z0-9])\b', re.IGNORECASE)

class PTOFCodeCleaner:
    def __init__(self, ptof_dir: str, provider: str = "ollama", model: str = "qwen2.5:7b",
                 ollama_url: str = "http://localhost:11434", dry_run: bool = True):
        self.ptof_dir = Path(ptof_dir)
        self.project_root = Path.cwd()
        self.data_dir = self.project_root / "data"
        self.provider = provider
        self.model = model
        self.ollama_url = ollama_url
        self.dry_run = dry_run
        self.report = {
            "mismatches": [],
            "confirmed_matches": [],
            "suspicious": [],
            "not_ptof": [],
            "summary": {"total": 0, "ok": 0, "mismatch": 0, "fixed": 0}
        }
        
        # Carica database scuole per validazione esistenza
        # (Opzionale: se la classe SchoolDatabase è disponibile nel progetto)
        self.school_db = None
        try:
            sys.path.append(str(Path.cwd()))
            from src.utils.school_database import SchoolDatabase
            self.school_db = SchoolDatabase()
            logger.info("SchoolDatabase caricato correttamente.")
        except ImportError:
            logger.warning("SchoolDatabase non trovato. La validazione esistenza codici sarà limitata.")

    def scan(self):
        """Scansiona tutti i file Markdown nella directory."""
        if not self.ptof_dir.exists():
            logger.error(f"Directory non trovata: {self.ptof_dir}")
            return
            
        files = list(self.ptof_dir.glob("*_ptof.md")) + list(self.ptof_dir.glob("*_PTOF.md"))
        logger.info(f"Trovati {len(files)} file PTOF.")
        self.report["summary"]["total"] = len(files)
        
        for file_path in files:
            self._analyze_file(file_path)

        self._save_report()
        self._print_summary()

    def _analyze_file(self, file_path: Path):
        """Analizza un singolo file."""
        filename_code = self._extract_code_from_filename(file_path.name)
        if not filename_code:
            logger.warning(f"Impossibile estrarre codice dal nome file: {file_path.name}")
            return

        content = ""
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Errore lettura file {file_path.name}: {e}")
            return

        # 1. Euristiche Regex
        found_codes = self._find_codes_in_text(content)
        
        # Analisi frequenza
        most_common = found_codes.most_common(3)
        top_code = most_common[0][0] if most_common else None
        
        # Decision Logic
        if top_code == filename_code:
            # Caso ideale: il codice più frequente è quello del nome file
            self.report["confirmed_matches"].append(str(file_path))
            self.report["summary"]["ok"] += 1
            return

        # Caso Mismatch o Ambiguo
        logger.info(f"Analisi approfondita per {file_path.name}. Atteso: {filename_code}, Trovato: {most_common}")
        
        # Se non ho trovato nessun codice, potrei usare LLM per capire se è un PTOF
        if not top_code:
            self._llm_check(file_path, content, filename_code, "no_code_found")
            return
            
        # Se ho trovato un codice diverso dominante
        if top_code != filename_code:
            # Verifica se top_code è "forte" (parecchie occorrenze)
            occurences = most_common[0][1]
            if occurences >= 3:
                # Mismatch forte
                self._handle_mismatch(file_path, filename_code, top_code, confidence=0.9, reason=f"Regex frequency ({occurences})")
            else:
                # Ambiguo, chiedo a LLM
                self._llm_check(file_path, content, filename_code, "mismatch_low_confidence", candidates=[c[0] for c in most_common])

    def _extract_code_from_filename(self, filename: str) -> Optional[str]:
        match = SCHOOL_CODE_PATTERN.search(filename)
        return match.group(1).upper() if match else None

    def _find_codes_in_text(self, text: str) -> Counter:
        """Restituisce un Counter dei codici trovati nel testo."""
        # Cerca tutti i codici
        matches = SCHOOL_CODE_PATTERN.findall(text.upper())
        # Filtra codici invalidi (opzionale)
        valid_matches = [m for m in matches if self._is_plausible_code(m)]
        return Counter(valid_matches)

    def _is_plausible_code(self, code: str) -> bool:
        # Euristiche base per scartare falsi positivi
        if len(code) != 10: return False
        # Un codice meccanografico deve contenere almeno un numero (i.e. 'COMPETENZE' non è un codice)
        if not any(char.isdigit() for char in code):
            # logger.debug(f"Scartato codice senza numeri: {code}")
            return False
        return True

    def _llm_check(self, file_path: Path, content: str, current_code: str, reason: str, candidates: List[str] = None):
        """Usa LLM per risolvere l'ambiguità."""
        if not self.ollama_url and self.provider == "ollama":
            logger.warning("Ollama URL non configurato, salto check LLM.")
            return

        logger.info(f"Richiesta LLM per {file_path.name} ({reason})")
        
        # Prendi le prime righe (header) che di solito contengono l'intestazione
        snippet = content[:5000] 
        
        prompt = f"""
        Analizza l'intestazione di questo documento scolastico.
        Il file si chiama {current_code}.
        Ho trovato nel testo questi possibili codici: {candidates}.
        
        Compito: Identifica il CODICE MECCANOGRAFICO PRINCIPALE della scuola a cui appartiene questo documento.
        Se è un documento generico o non scolastico, rispondi "NOT_PTOF".
        
        Restituisci SOLO un file JSON in questo formato:
        {{
            "detected_code": "CODICE",
            "confidence": 0.0-1.0,
            "is_ptof": true/false,
            "reason": "spiegazione breve"
        }}
        
        Testo:
        {snippet}
        """
        
        try:
            response = self._call_llm(prompt)
            # Parsing JSON sporco
            import json
            # Tenta di estrarre JSON se il modello chiacchiera
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                detected = data.get("detected_code")
                confidence = data.get("confidence", 0.5)
                
                if detected and detected != "NOT_PTOF" and detected != current_code:
                     self._handle_mismatch(file_path, current_code, detected, confidence, f"LLM: {data.get('reason')}")
                elif detected == "NOT_PTOF":
                    self.report["not_ptof"].append(str(file_path))
            
        except Exception as e:
            logger.error(f"Errore LLM: {e}")

    def _call_llm(self, prompt: str) -> str:
        if self.provider == "ollama":
            import requests
            try:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                }
                resp = requests.post(f"{self.ollama_url}/api/generate", json=payload, timeout=30)
                resp.raise_for_status()
                return resp.json().get("response", "")
            except Exception as e:
                logger.error(f"Ollama call failed: {e}")
                return "{}"
        else:
            logger.warning(f"Provider {self.provider} non implementato ancora.")
            return "{}"

    def _handle_mismatch(self, file_path: Path, old_code: str, new_code: str, confidence: float, reason: str):
        """Registra e gestisce il mismatch."""
        mismatch_entry = {
            "file": str(file_path),
            "current_code": old_code,
            "suggested_code": new_code,
            "confidence": confidence,
            "reason": reason,
            "action": "RENAME"
        }
        
        # Verifica esistenza scuola target
        if self.school_db:
             target_data = self.school_db.get_school_data(new_code)
             if not target_data:
                 mismatch_entry["warning"] = "Codice target non trovato nel database MIUR"
        
        self.report["mismatches"].append(mismatch_entry)
        self.report["summary"]["mismatch"] += 1
        
        if not self.dry_run and confidence > 0.8:
            self._perform_rename(file_path, new_code)

    def _perform_rename(self, file_path: Path, new_code: str):
        """Esegue la rinomina fisica del file."""
        new_name = file_path.name.replace(self._extract_code_from_filename(file_path.name), new_code)
        new_path = file_path.with_name(new_name)
        
        if new_path.exists():
            # Gestione conflitti
            conflict_dir = self.ptof_dir / "conflicts"
            conflict_dir.mkdir(exist_ok=True)
            shutil.move(str(file_path), str(conflict_dir / file_path.name))
            logger.info(f"Conflitto! Spostato {file_path.name} in conflicts/")
        else:
            try:
                old_code = self._extract_code_from_filename(file_path.name)
                old_filename = file_path.name
                file_path.rename(new_path)
                logger.info(f"RINOMINATO: {file_path.name} -> {new_name}")
                self.report["summary"]["fixed"] += 1
                
                # Cleanup related data
                if old_code:
                    self._clean_related_data(old_code, old_filename)
                
            except Exception as e:
                logger.error(f"Errore rinomina: {e}")

    def _clean_related_data(self, old_code: str, old_filename: str):
        """
        Pulisce tutti i dati associati al vecchio codice scolastico.
        """
        if self.dry_run:
            return

        logger.info(f"Avvio pulizia dati correlati per codice errato: {old_code}")

        # 1. Rimuovi da validation_registry.json
        validation_registry_path = self.data_dir / "validation_registry.json"
        if validation_registry_path.exists():
            try:
                with open(validation_registry_path, 'r') as f:
                    data = json.load(f)
                
                if "validated_files" in data and old_filename in data["validated_files"]:
                    del data["validated_files"][old_filename]
                    logger.info(f"Rimosso entry da validation_registry per {old_filename}")
                    
                    with open(validation_registry_path, 'w') as f:
                        json.dump(data, f, indent=4)
            except Exception as e:
                logger.error(f"Errore pulizia validation_registry: {e}")

        # 2. Rimuovi file in analysis_results/
        analysis_dir = self.project_root / "analysis_results"
        for ext in ["json", "md"]:
            target = analysis_dir / f"{old_code}_PTOF_analysis.{ext}"
            if target.exists():
                try:
                    target.unlink()
                    logger.info(f"Eliminato artefatto analisi: {target.name}")
                except Exception as e:
                    logger.error(f"Errore eliminazione {target}: {e}")

        # 3. Rimuovi file in ptof_processed/ (ricerca ricorsiva)
        processed_dir = self.project_root / "ptof_processed"
        if processed_dir.exists():
            for path in processed_dir.rglob(f"{old_code}.json"):
                try:
                    path.unlink()
                    logger.info(f"Eliminato file processato: {path.name}")
                except Exception as e:
                    logger.error(f"Errore eliminazione {path}: {e}")
        
        # 4. Rimuovi entry da activity_registry.json
        activity_registry_path = self.data_dir / "activity_registry.json"
        if activity_registry_path.exists():
            try:
                with open(activity_registry_path, 'r') as f:
                    reg_data = json.load(f)
                
                updated = False
                if "processed_files" in reg_data and old_code in reg_data["processed_files"]:
                    del reg_data["processed_files"][old_code]
                    updated = True
                
                if updated:
                    logger.info(f"Rimosso {old_code} da activity_registry")
                    with open(activity_registry_path, 'w') as f:
                        json.dump(reg_data, f, indent=4)
            except Exception as e:
                logger.error(f"Errore pulizia activity_registry: {e}")

        # 5. Rimuovi righe da attivita.csv
        attivita_path = self.data_dir / "attivita.csv"
        if attivita_path.exists():
            try:
                temp_path = attivita_path.with_suffix(".tmp")
                deleted_count = 0
                with open(attivita_path, 'r', encoding='utf-8') as f_in, \
                     open(temp_path, 'w', encoding='utf-8', newline='') as f_out:
                    
                    reader = csv.DictReader(f_in)
                    writer = csv.DictWriter(f_out, fieldnames=reader.fieldnames)
                    writer.writeheader()
                    
                    for row in reader:
                        if row.get("codice_meccanografico") != old_code:
                            writer.writerow(row)
                        else:
                            deleted_count += 1
                
                if deleted_count > 0:
                    shutil.move(str(temp_path), str(attivita_path))
                    logger.info(f"Rimosse {deleted_count} righe da attivita.csv per {old_code}")
                else:
                    os.remove(temp_path)
            except Exception as e:
                logger.error(f"Errore pulizia attivita.csv: {e}")

    def _save_report(self):
        report_path = Path("data/ptof_mismatch_report.json")
        report_path.parent.mkdir(exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(self.report, f, indent=2)
        logger.info(f"Report salvato in {report_path}")

    def _print_summary(self):
        print("\n" + "="*50)
        print("PTOF CLEANER SUMMARY")
        print("="*50)
        print(f"Total Files Scanned: {self.report['summary']['total']}")
        print(f"Confirmed Matches:   {self.report['summary']['ok']}")
        print(f"Mismatches Found:    {self.report['summary']['mismatch']}")
        if not self.dry_run:
            print(f"Files Fixed:         {self.report['summary']['fixed']}")
        else:
            print(f"Files Fixed:         0 (DRY RUN)")
        print("="*50 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PTOF Code Cleaner")
    parser.add_argument("--dir", default="ptof_md", help="Directory PTOF Markdown")
    parser.add_argument("--provider", default="ollama", help="LLM Provider (ollama, etc)")
    parser.add_argument("--model", default=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"), help="LLM Model Name")
    parser.add_argument("--ollama-url", default=os.getenv("OLLAMA_HOST", "http://localhost:11434"), help="Ollama URL")
    parser.add_argument("--confirm", action="store_true", help="Esegui le modifiche (disabilita dry-run)")
    
    args = parser.parse_args()
    
    cleaner = PTOFCodeCleaner(
        ptof_dir=args.dir,
        provider=args.provider,
        model=args.model,
        ollama_url=args.ollama_url,
        dry_run=not args.confirm
    )
    cleaner.scan()
