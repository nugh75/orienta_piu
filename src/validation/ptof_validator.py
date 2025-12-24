#!/usr/bin/env python3
"""
PTOFValidator - Validazione progressiva documenti PTOF
======================================================

Sistema di validazione in 3 fasi:
1. HEURISTICS (veloce): keywords, struttura, pagine
2. OLLAMA (se ambiguo): analisi intelligente contenuto
3. RECOVERY: sistema per recuperare file scartati erroneamente

Autore: PTOF Analysis System
"""

import os
import sys
import json
import shutil
import logging
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Tuple, List
from dataclasses import dataclass, asdict
from enum import Enum

# Aggiungi path progetto
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

import requests
from pypdf import PdfReader

# Configurazione logging
logger = logging.getLogger(__name__)

# =====================================================
# CONFIGURAZIONE
# =====================================================

OLLAMA_URL = "http://192.168.129.14:11434/api/generate"
OLLAMA_MODEL = "qwen3:32b"  # Modello per validazione

# Directory
DISCARDED_DIR = BASE_DIR / "ptof_discarded"
DISCARDED_NOT_PTOF = DISCARDED_DIR / "not_ptof"
DISCARDED_TOO_SHORT = DISCARDED_DIR / "too_short"
DISCARDED_CORRUPTED = DISCARDED_DIR / "corrupted"
RECOVERY_LOG = DISCARDED_DIR / "recovery_log.json"
ALLOWLIST_FILE = BASE_DIR / "data" / "ptof_validator_allowlist.txt"

# Soglie
MIN_PAGES = 5  # Minimo pagine per un PTOF valido
MIN_CHARS = 3000  # Minimo caratteri estratti
CONFIDENCE_THRESHOLD_HEURISTIC = 0.65  # Se > 0.65, skip LLM
CONFIDENCE_THRESHOLD_LLM = 0.45  # Se > 0.45 dopo LLM, accetta


class ValidationResult(Enum):
    """Risultato validazione"""
    VALID_PTOF = "valid_ptof"
    NOT_PTOF = "not_ptof"
    TOO_SHORT = "too_short"
    CORRUPTED = "corrupted"
    AMBIGUOUS = "ambiguous"


@dataclass
class ValidationReport:
    """Report dettagliato validazione"""
    file_path: str
    file_name: str
    result: str
    confidence: float
    phase: str  # 'heuristic', 'llm', 'manual'
    
    # Dettagli euristici
    page_count: int = 0
    char_count: int = 0
    ptof_keywords_found: int = 0
    exclusion_keywords_found: int = 0
    school_code_found: Optional[str] = None
    
    # Dettagli LLM (se usato)
    llm_analysis: Optional[str] = None
    llm_confidence: Optional[float] = None
    
    # Metadati
    timestamp: str = ""
    reason: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        return asdict(self)


class PTOFValidator:
    """
    Validatore progressivo per documenti PTOF.
    
    Fasi:
    1. Heuristics: analisi veloce basata su keywords e struttura
    2. LLM: analisi intelligente con Ollama (solo se ambiguo)
    3. Recovery: sistema per recuperare file scartati
    """
    
    # Keywords che indicano un PTOF
    PTOF_KEYWORDS = [
        "piano triennale",
        "piano dell'offerta formativa",
        "offerta formativa",
        "ptof",
        "p.t.o.f",
        "triennio",
        "curricolo",
        "curricolo verticale",
        "rav",
        "piano di miglioramento",
        "pdm",
        "mission",
        "vision",
        "organigramma",
        "funzionigramma",
        "organico",
        "docenti",
        "ata",
        "invalsi",
        "competenze",
        "obiettivi formativi",
        "ampliamento offerta",
        "pcto",
        "alternanza scuola",
        "inclusione",
        "bes",
        "dsa",
        "valutazione",
        "certificazione competenze",
        "orientamento",
        "continuità",
        "atto di indirizzo",
        "profilo educativo",
        "indirizzi di studio",
        "piano di formazione",
        "pnsd",
        "piano digitale",
        "animatore digitale",
        "formazione docenti",
        "fabbisogno",
        "risorse umane",
        "infrastrutture",
        "laboratori",
    ]
    
    # Keywords che indicano NON è un PTOF
    EXCLUSION_KEYWORDS = [
        "circolare n.",
        "circolare n°",
        "prot. n.",
        "protocollo n.",
        "oggetto:",
        "ai genitori",
        "alle famiglie",
        "verbale",
        "delibera n.",
        "delibera n°",
        "convocazione",
        "modulistica",
        "modulo di",
        "domanda di",
        "richiesta di",
        "autorizzazione",
        "liberatoria",
        "consenso informato",
        "iscrizione",
        "regolamento d'istituto",
        "regolamento disciplinare",
        "carta dei servizi",
        "patto educativo",
        "calendario scolastico",
        "orario delle lezioni",
        "graduatoria",
        "bando",
        "avviso pubblico",
        "determina",
        "decreto",
    ]

    STRONG_PTOF_KEYWORDS = [
        "piano triennale dell'offerta formativa",
        "piano triennale",
        "offerta formativa",
        "ptof",
        "p.t.o.f",
    ]
    OK_SUFFIXES = ("_ok", "-ok", " ok")
    
    def __init__(self, ollama_url: str = None, ollama_model: str = None):
        """Inizializza il validatore."""
        self.ollama_url = ollama_url or OLLAMA_URL
        self.ollama_model = ollama_model or OLLAMA_MODEL
        self.allowlist = self._load_allowlist()
        self.allowlist_norm = {item.lower() for item in self.allowlist}
        
        # Crea directory
        for d in [DISCARDED_NOT_PTOF, DISCARDED_TOO_SHORT, DISCARDED_CORRUPTED]:
            d.mkdir(parents=True, exist_ok=True)
        
        # Carica log recuperi
        self.recovery_log = self._load_recovery_log()
        
        logger.info(f"🔍 PTOFValidator inizializzato")
        logger.info(f"   Ollama: {self.ollama_url}")
        logger.info(f"   Modello: {self.ollama_model}")
    
    def _load_recovery_log(self) -> dict:
        """Carica log dei recuperi."""
        if RECOVERY_LOG.exists():
            try:
                with open(RECOVERY_LOG, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {"recovered": [], "discarded": []}
    
    def _save_recovery_log(self):
        """Salva log dei recuperi."""
        with open(RECOVERY_LOG, 'w') as f:
            json.dump(self.recovery_log, f, ensure_ascii=False, indent=2)

    def _load_allowlist(self) -> set:
        """Carica allowlist per forzare l'accettazione di file PTOF."""
        if not ALLOWLIST_FILE.exists():
            return set()
        items = set()
        for line in ALLOWLIST_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            items.add(line)
        return items
    
    def _extract_text_from_pdf(self, pdf_path: Path, max_pages: int = 10) -> Tuple[str, int]:
        """
        Estrae testo dalle prime N pagine del PDF.
        
        Returns:
            (testo_estratto, numero_pagine_totali)
        """
        try:
            reader = PdfReader(str(pdf_path))
            total_pages = len(reader.pages)
            
            text = ""
            for i, page in enumerate(reader.pages):
                if i >= max_pages:
                    break
                try:
                    text += page.extract_text() or ""
                except:
                    pass
            
            return text.strip(), total_pages
            
        except Exception as e:
            logger.error(f"❌ Errore lettura PDF {pdf_path.name}: {e}")
            return "", 0
    
    def _count_keywords(self, text: str, keywords: List[str]) -> int:
        """Conta quante keywords sono presenti nel testo."""
        text_lower = text.lower()
        count = 0
        for kw in keywords:
            if kw.lower() in text_lower:
                count += 1
        return count
    
    def _extract_school_code(self, text: str) -> Optional[str]:
        """Estrae codice meccanografico dal testo."""
        patterns = [
            r'[Cc]odice\s*[Mm]eccanografico[:\s]*([A-Z]{2}[A-Z]{2}[A-Z0-9]{6})',
            r'[Cc]od\.?\s*[Mm]ecc\.?[:\s]*([A-Z]{2}[A-Z]{2}[A-Z0-9]{6})',
            r'\b([A-Z]{2}[A-Z]{2}\d{6}[A-Z]?)\b',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text.upper())
            if match:
                return match.group(1)
        return None

    def _extract_school_code_from_name(self, name: str) -> Optional[str]:
        match = re.search(r'\b([A-Z]{2}[A-Z]{2}\d{6}[A-Z]?)\b', name.upper())
        if match:
            return match.group(1)
        return None

    def _force_accept_reason(self, pdf_path: Path, text: str = "") -> Optional[str]:
        """Ritorna motivo di accettazione forzata se attivo."""
        stem_lower = pdf_path.stem.lower()
        for suffix in self.OK_SUFFIXES:
            if stem_lower.endswith(suffix):
                return f"Override filename suffix ({suffix})"

        if not self.allowlist_norm:
            return None

        name_lower = pdf_path.name.lower()
        if name_lower in self.allowlist_norm or stem_lower in self.allowlist_norm:
            return "Override allowlist (nome file)"

        code_from_name = self._extract_school_code_from_name(pdf_path.name)
        if code_from_name and code_from_name.lower() in self.allowlist_norm:
            return "Override allowlist (codice)"

        if text:
            code_from_text = self._extract_school_code(text)
            if code_from_text and code_from_text.lower() in self.allowlist_norm:
                return "Override allowlist (codice nel testo)"

        return None

    def _is_ok_filename(self, name: str) -> bool:
        stem_lower = Path(name).stem.lower()
        return any(stem_lower.endswith(suffix) for suffix in self.OK_SUFFIXES)
    
    def _heuristic_validation(self, text: str, page_count: int) -> Tuple[float, ValidationReport]:
        """
        Fase 1: Validazione euristica veloce.
        
        Returns:
            (confidence, report_parziale)
        """
        # Conta keywords
        ptof_count = self._count_keywords(text, self.PTOF_KEYWORDS)
        strong_count = self._count_keywords(text, self.STRONG_PTOF_KEYWORDS)
        exclusion_count = self._count_keywords(text, self.EXCLUSION_KEYWORDS)
        school_code = self._extract_school_code(text)
        char_count = len(text)
        
        # Calcola confidence
        confidence = 0.0
        
        # Fattori positivi
        if ptof_count >= 12:
            confidence += 0.4
        elif ptof_count >= 6:
            confidence += 0.25
        elif ptof_count >= 2:
            confidence += 0.12

        if strong_count > 0:
            confidence += 0.2
        
        if page_count >= 50:
            confidence += 0.3
        elif page_count >= 30:
            confidence += 0.25
        elif page_count >= 20:
            confidence += 0.2
        elif page_count >= 10:
            confidence += 0.15
        elif page_count >= MIN_PAGES:
            confidence += 0.1
        
        if school_code:
            confidence += 0.15
        
        if char_count >= 50000:
            confidence += 0.1
        elif char_count >= 20000:
            confidence += 0.05
        
        # Fattori negativi
        if exclusion_count >= 5:
            confidence -= 0.35
        elif exclusion_count >= 2:
            confidence -= 0.1 if ptof_count >= 6 else 0.2
        
        if page_count < MIN_PAGES:
            confidence -= 0.3
        
        # Normalizza
        confidence = max(0.0, min(1.0, confidence))
        
        report = ValidationReport(
            file_path="",
            file_name="",
            result=ValidationResult.AMBIGUOUS.value,
            confidence=confidence,
            phase="heuristic",
            page_count=page_count,
            char_count=char_count,
            ptof_keywords_found=ptof_count,
            exclusion_keywords_found=exclusion_count,
            school_code_found=school_code
        )
        
        return confidence, report
    
    def _llm_validation(self, text: str, heuristic_report: ValidationReport) -> Tuple[float, str]:
        """
        Fase 2: Validazione con Ollama per casi ambigui.
        
        Returns:
            (confidence, analisi_testuale)
        """
        # Prendi solo i primi 5000 caratteri per velocità
        sample_text = text[:5000]
        
        prompt = f"""/no_think
Sei un esperto di documenti scolastici italiani. Analizza questo testo e determina se è un PTOF (Piano Triennale dell'Offerta Formativa).

Un PTOF valido deve contenere:
- Piano triennale dell'offerta formativa
- Informazioni su curricolo, didattica, organizzazione
- Riferimenti a RAV, PDM, obiettivi formativi
- Struttura articolata (non una circolare o modulo)

NON è un PTOF:
- Circolari, comunicazioni
- Moduli, domande, liberatorie
- Regolamenti, verbali
- Documenti brevi o frammentari

TESTO DA ANALIZZARE:
---
{sample_text}
---

INFORMAZIONI EURISTICHE:
- Pagine: {heuristic_report.page_count}
- Keywords PTOF trovate: {heuristic_report.ptof_keywords_found}
- Keywords esclusione trovate: {heuristic_report.exclusion_keywords_found}
- Codice scuola trovato: {heuristic_report.school_code_found or 'No'}

Rispondi SOLO in questo formato JSON:
{{
  "is_ptof": true/false,
  "confidence": 0.0-1.0,
  "reason": "breve spiegazione",
  "document_type": "PTOF/circolare/modulo/altro"
}}"""

        try:
            response = requests.post(
                f"{self.ollama_url}",
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.1, "num_predict": 300}
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json().get("response", "")
                try:
                    # Parse JSON dalla risposta
                    data = json.loads(result)
                    confidence = float(data.get("confidence", 0.5))
                    is_ptof = data.get("is_ptof", False)
                    reason = data.get("reason", "")
                    doc_type = data.get("document_type", "sconosciuto")
                    
                    # Aggiusta confidence basata su is_ptof
                    if not is_ptof:
                        confidence = 1.0 - confidence  # Inverti per "not ptof"
                    
                    analysis = f"{doc_type}: {reason}"
                    return confidence, analysis
                    
                except json.JSONDecodeError:
                    logger.warning(f"⚠️ Risposta LLM non è JSON valido")
                    return 0.5, result[:200]
            else:
                logger.error(f"❌ Errore Ollama: {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ Errore connessione Ollama: {e}")
        
        return 0.5, "Errore analisi LLM"
    
    def validate(self, pdf_path: Path, use_llm_if_ambiguous: bool = True) -> ValidationReport:
        """
        Valida un documento PDF in modo progressivo.
        
        Args:
            pdf_path: Percorso al file PDF
            use_llm_if_ambiguous: Se True, usa LLM per casi ambigui
            
        Returns:
            ValidationReport con risultato e dettagli
        """
        pdf_path = Path(pdf_path)
        logger.info(f"🔍 Validazione: {pdf_path.name}")
        
        # Fase 0: Verifica file esiste
        if not pdf_path.exists():
            return ValidationReport(
                file_path=str(pdf_path),
                file_name=pdf_path.name,
                result=ValidationResult.CORRUPTED.value,
                confidence=1.0,
                phase="check",
                reason="File non trovato"
            )
        
        force_reason = self._force_accept_reason(pdf_path)

        # Fase 1: Estrai testo
        text, page_count = self._extract_text_from_pdf(pdf_path)
        
        if page_count == 0:
            return ValidationReport(
                file_path=str(pdf_path),
                file_name=pdf_path.name,
                result=ValidationResult.CORRUPTED.value,
                confidence=1.0,
                phase="extraction",
                reason="Impossibile leggere PDF"
            )
        
        if not force_reason:
            force_reason = self._force_accept_reason(pdf_path, text=text)

        if force_reason:
            school_code = self._extract_school_code(text)
            return ValidationReport(
                file_path=str(pdf_path),
                file_name=pdf_path.name,
                result=ValidationResult.VALID_PTOF.value,
                confidence=1.0,
                phase="override",
                page_count=page_count,
                char_count=len(text),
                school_code_found=school_code,
                reason=force_reason
            )

        if page_count < MIN_PAGES:
            return ValidationReport(
                file_path=str(pdf_path),
                file_name=pdf_path.name,
                result=ValidationResult.TOO_SHORT.value,
                confidence=0.9,
                phase="heuristic",
                page_count=page_count,
                char_count=len(text),
                reason=f"Solo {page_count} pagine (minimo: {MIN_PAGES})"
            )
        
        if len(text) < MIN_CHARS:
            return ValidationReport(
                file_path=str(pdf_path),
                file_name=pdf_path.name,
                result=ValidationResult.CORRUPTED.value,
                confidence=0.8,
                phase="extraction",
                page_count=page_count,
                char_count=len(text),
                reason=f"Testo insufficiente: {len(text)} caratteri"
            )
        
        # Fase 2: Heuristics
        h_confidence, report = self._heuristic_validation(text, page_count)
        report.file_path = str(pdf_path)
        report.file_name = pdf_path.name
        
        logger.info(f"   📊 Heuristic confidence: {h_confidence:.2f}")
        logger.info(f"      PTOF keywords: {report.ptof_keywords_found}")
        logger.info(f"      Exclusion keywords: {report.exclusion_keywords_found}")
        
        # Decisione basata su heuristics
        if h_confidence >= CONFIDENCE_THRESHOLD_HEURISTIC:
            report.result = ValidationResult.VALID_PTOF.value
            report.reason = f"Alta confidenza euristica ({h_confidence:.2f})"
            logger.info(f"   ✅ PTOF VALIDO (heuristic: {h_confidence:.2f})")
            return report
        
        if h_confidence <= 0.15:
            report.result = ValidationResult.NOT_PTOF.value
            report.reason = f"Bassa confidenza euristica ({h_confidence:.2f})"
            logger.info(f"   ❌ NON PTOF (heuristic: {h_confidence:.2f})")
            return report
        
        # Fase 3: LLM per casi ambigui
        if use_llm_if_ambiguous:
            logger.info(f"   🤖 Caso ambiguo, analisi LLM...")
            llm_confidence, llm_analysis = self._llm_validation(text, report)
            
            report.phase = "llm"
            report.llm_analysis = llm_analysis
            report.llm_confidence = llm_confidence
            
            # Combina confidence (media pesata)
            combined = (h_confidence * 0.4) + (llm_confidence * 0.6)
            report.confidence = combined
            
            logger.info(f"   📊 LLM confidence: {llm_confidence:.2f}")
            logger.info(f"   📊 Combined: {combined:.2f}")
            
            if combined >= CONFIDENCE_THRESHOLD_LLM:
                report.result = ValidationResult.VALID_PTOF.value
                report.reason = f"Validato da LLM ({llm_analysis})"
                logger.info(f"   ✅ PTOF VALIDO (LLM)")
            else:
                report.result = ValidationResult.NOT_PTOF.value
                report.reason = f"Rifiutato da LLM ({llm_analysis})"
                logger.info(f"   ❌ NON PTOF (LLM: {llm_analysis})")
        else:
            report.result = ValidationResult.AMBIGUOUS.value
            report.reason = "Richiede validazione manuale"
        
        return report
    
    def discard(self, pdf_path: Path, report: ValidationReport) -> Path:
        """
        Sposta un file nella directory appropriata di scarto.
        
        Returns:
            Path della destinazione
        """
        pdf_path = Path(pdf_path)
        
        # Determina directory destinazione
        if report.result == ValidationResult.TOO_SHORT.value:
            dest_dir = DISCARDED_TOO_SHORT
        elif report.result == ValidationResult.CORRUPTED.value:
            dest_dir = DISCARDED_CORRUPTED
        else:
            dest_dir = DISCARDED_NOT_PTOF
        
        dest_path = dest_dir / pdf_path.name
        
        # Evita sovrascrittura
        if dest_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest_path = dest_dir / f"{pdf_path.stem}_{timestamp}{pdf_path.suffix}"
        
        # Sposta file
        shutil.move(str(pdf_path), str(dest_path))
        logger.info(f"   🗑️ Spostato in: {dest_path.relative_to(BASE_DIR)}")
        
        # Salva nel log per recovery
        self.recovery_log["discarded"].append({
            "original_path": str(pdf_path),
            "discarded_path": str(dest_path),
            "report": report.to_dict(),
            "timestamp": datetime.now().isoformat()
        })
        self._save_recovery_log()
        
        return dest_path
    
    def validate_batch(self, pdf_dir: Path, move_invalid: bool = True) -> Dict:
        """
        Valida tutti i PDF in una directory.
        
        Returns:
            Dizionario con statistiche e reports
        """
        pdf_dir = Path(pdf_dir)
        results = {
            "valid": [],
            "not_ptof": [],
            "too_short": [],
            "corrupted": [],
            "ambiguous": [],
            "stats": {}
        }
        
        pdf_files = list(pdf_dir.glob("*.pdf"))
        logger.info(f"📂 Validazione batch: {len(pdf_files)} PDF in {pdf_dir}")
        
        for pdf_path in pdf_files:
            report = self.validate(pdf_path)
            
            if report.result == ValidationResult.VALID_PTOF.value:
                results["valid"].append(report)
            elif report.result == ValidationResult.NOT_PTOF.value:
                results["not_ptof"].append(report)
                if move_invalid:
                    self.discard(pdf_path, report)
            elif report.result == ValidationResult.TOO_SHORT.value:
                results["too_short"].append(report)
                if move_invalid:
                    self.discard(pdf_path, report)
            elif report.result == ValidationResult.CORRUPTED.value:
                results["corrupted"].append(report)
                if move_invalid:
                    self.discard(pdf_path, report)
            else:
                results["ambiguous"].append(report)
        
        # Statistiche
        total = len(pdf_files)
        results["stats"] = {
            "total": total,
            "valid": len(results["valid"]),
            "not_ptof": len(results["not_ptof"]),
            "too_short": len(results["too_short"]),
            "corrupted": len(results["corrupted"]),
            "ambiguous": len(results["ambiguous"]),
            "valid_rate": len(results["valid"]) / total if total > 0 else 0
        }
        
        logger.info(f"📊 Risultati batch:")
        logger.info(f"   ✅ Validi: {results['stats']['valid']}")
        logger.info(f"   ❌ Non PTOF: {results['stats']['not_ptof']}")
        logger.info(f"   📄 Troppo corti: {results['stats']['too_short']}")
        logger.info(f"   💔 Corrotti: {results['stats']['corrupted']}")
        logger.info(f"   ❓ Ambigui: {results['stats']['ambiguous']}")
        
        return results
    
    # =====================================================
    # SISTEMA DI RECOVERY
    # =====================================================
    
    def list_discarded(self) -> List[Dict]:
        """
        Lista tutti i file scartati che possono essere recuperati.
        
        Returns:
            Lista di dizionari con info sui file scartati
        """
        discarded = []
        
        for category, dir_path in [
            ("not_ptof", DISCARDED_NOT_PTOF),
            ("too_short", DISCARDED_TOO_SHORT),
            ("corrupted", DISCARDED_CORRUPTED)
        ]:
            for pdf in dir_path.glob("*.pdf"):
                # Cerca report nel log
                report_info = None
                for item in self.recovery_log.get("discarded", []):
                    if item.get("discarded_path") == str(pdf):
                        report_info = item
                        break
                
                discarded.append({
                    "path": str(pdf),
                    "name": pdf.name,
                    "category": category,
                    "report": report_info.get("report") if report_info else None,
                    "timestamp": report_info.get("timestamp") if report_info else None
                })
        
        return discarded
    
    def recover(self, discarded_path: Path, dest_dir: Path = None) -> Optional[Path]:
        """
        Recupera un file scartato, spostandolo nella directory di destinazione.
        
        Args:
            discarded_path: Path del file scartato
            dest_dir: Directory di destinazione (default: ptof_inbox)
            
        Returns:
            Path del file recuperato, o None se fallisce
        """
        discarded_path = Path(discarded_path)
        
        if not discarded_path.exists():
            logger.error(f"❌ File non trovato: {discarded_path}")
            return None
        
        dest_dir = dest_dir or (BASE_DIR / "ptof_inbox")
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        dest_path = dest_dir / discarded_path.name
        
        # Evita sovrascrittura
        if dest_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest_path = dest_dir / f"{discarded_path.stem}_{timestamp}{discarded_path.suffix}"
        
        # Sposta file
        shutil.move(str(discarded_path), str(dest_path))
        
        # Aggiorna log
        self.recovery_log["recovered"].append({
            "original_discarded": str(discarded_path),
            "recovered_to": str(dest_path),
            "timestamp": datetime.now().isoformat()
        })
        self._save_recovery_log()
        
        logger.info(f"♻️ Recuperato: {discarded_path.name} → {dest_path.relative_to(BASE_DIR)}")
        return dest_path
    
    def recover_all(self, category: str = None, dest_dir: Path = None, only_ok: bool = False) -> List[Path]:
        """
        Recupera tutti i file scartati (opzionalmente filtrati per categoria).
        
        Args:
            category: 'not_ptof', 'too_short', 'corrupted' o None per tutti
            dest_dir: Directory di destinazione
            only_ok: Recupera solo file con suffisso _ok/-ok/ ok
            
        Returns:
            Lista dei path recuperati
        """
        discarded = self.list_discarded()
        
        if category:
            discarded = [d for d in discarded if d["category"] == category]
        if only_ok:
            discarded = [d for d in discarded if self._is_ok_filename(d["name"])]
        
        recovered = []
        for item in discarded:
            path = self.recover(Path(item["path"]), dest_dir)
            if path:
                recovered.append(path)
        
        logger.info(f"♻️ Recuperati {len(recovered)} file")
        return recovered


# =====================================================
# FUNZIONI HELPER
# =====================================================

def validate_inbox(move_invalid: bool = True) -> Dict:
    """
    Valida tutti i PDF in ptof_inbox/.
    Funzione di convenienza per uso da CLI.
    """
    validator = PTOFValidator()
    inbox_dir = BASE_DIR / "ptof_inbox"
    return validator.validate_batch(inbox_dir, move_invalid=move_invalid)


def show_discarded():
    """Mostra tutti i file scartati."""
    validator = PTOFValidator()
    discarded = validator.list_discarded()
    
    print(f"\n📂 FILE SCARTATI ({len(discarded)})")
    print("=" * 60)
    
    for item in discarded:
        cat = item["category"]
        name = item["name"]
        ts = item.get("timestamp", "N/A")[:10]
        report = item.get("report", {})
        reason = report.get("reason", "N/A") if report else "N/A"
        
        icon = {"not_ptof": "❌", "too_short": "📄", "corrupted": "💔"}.get(cat, "❓")
        print(f"  {icon} [{cat}] {name}")
        print(f"      Motivo: {reason}")
        print(f"      Data: {ts}")
        print()


def recover_file(filename: str) -> bool:
    """
    Recupera un file per nome.
    
    Args:
        filename: Nome del file da recuperare
        
    Returns:
        True se recuperato, False altrimenti
    """
    validator = PTOFValidator()
    discarded = validator.list_discarded()
    
    for item in discarded:
        if item["name"] == filename:
            result = validator.recover(Path(item["path"]))
            return result is not None
    
    print(f"❌ File non trovato: {filename}")
    return False


# =====================================================
# CLI
# =====================================================

if __name__ == "__main__":
    import argparse
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    parser = argparse.ArgumentParser(description="PTOFValidator - Validazione progressiva PTOF")
    parser.add_argument("action", choices=["validate", "list", "recover"],
                       help="Azione da eseguire")
    parser.add_argument("--file", "-f", help="File specifico da validare/recuperare")
    parser.add_argument("--no-llm", action="store_true", help="Disabilita LLM per casi ambigui")
    parser.add_argument("--dry-run", action="store_true", help="Non sposta i file")
    parser.add_argument("--category", "-c", choices=["not_ptof", "too_short", "corrupted"],
                       help="Categoria per recover")
    parser.add_argument("--only-ok", action="store_true",
                       help="Recupera solo file con suffisso _ok/-ok/ ok")
    
    args = parser.parse_args()
    
    if args.action == "validate":
        if args.file:
            validator = PTOFValidator()
            report = validator.validate(Path(args.file), use_llm_if_ambiguous=not args.no_llm)
            print(f"\n📋 REPORT: {report.file_name}")
            print(f"   Risultato: {report.result}")
            print(f"   Confidenza: {report.confidence:.2f}")
            print(f"   Fase: {report.phase}")
            print(f"   Pagine: {report.page_count}")
            print(f"   Motivo: {report.reason}")
            if report.llm_analysis:
                print(f"   LLM: {report.llm_analysis}")
        else:
            results = validate_inbox(move_invalid=not args.dry_run)
            print(f"\n📊 RIEPILOGO:")
            print(f"   ✅ Validi: {results['stats']['valid']}")
            print(f"   ❌ Non PTOF: {results['stats']['not_ptof']}")
            print(f"   📄 Troppo corti: {results['stats']['too_short']}")
            print(f"   💔 Corrotti: {results['stats']['corrupted']}")
    
    elif args.action == "list":
        show_discarded()
    
    elif args.action == "recover":
        if args.file:
            recover_file(args.file)
        else:
            validator = PTOFValidator()
            recovered = validator.recover_all(category=args.category, only_ok=args.only_ok)
            print(f"\n♻️ Recuperati {len(recovered)} file")
