#!/usr/bin/env python3
"""
Analysis Registry - Registro dei file PTOF già analizzati

Questo modulo gestisce un registro persistente dei file PDF analizzati,
permettendo di:
- Saltare file già analizzati (basandosi sull'hash del contenuto)
- Rilevare modifiche ai PDF sorgente (ri-analisi automatica se il file cambia)
- Tracciare quando e come ogni file è stato analizzato
"""

import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)

# Configurazione
BASE_DIR = Path(__file__).resolve().parent.parent.parent
REGISTRY_FILE = BASE_DIR / "data" / "analysis_registry.json"
REGISTRY_VERSION = "1.0"


def compute_file_hash(file_path: Path, algorithm: str = "sha256") -> str:
    """
    Calcola l'hash di un file.
    
    Args:
        file_path: Percorso del file
        algorithm: Algoritmo di hash (default: sha256)
    
    Returns:
        Hash del file in formato "algorithm:hex_digest"
    """
    hash_func = hashlib.new(algorithm)
    
    with open(file_path, "rb") as f:
        # Leggi a blocchi per file grandi
        for chunk in iter(lambda: f.read(8192), b""):
            hash_func.update(chunk)
    
    return f"{algorithm}:{hash_func.hexdigest()}"


def load_registry() -> Dict[str, Any]:
    """
    Carica il registro delle analisi.
    
    Returns:
        Dizionario con i dati del registro
    """
    if not REGISTRY_FILE.exists():
        return {
            "version": REGISTRY_VERSION,
            "last_updated": None,
            "analyzed_files": {}
        }
    
    try:
        with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Verifica versione
        if data.get("version") != REGISTRY_VERSION:
            logger.warning(f"Versione registro diversa: {data.get('version')} vs {REGISTRY_VERSION}")
        
        return data
    
    except Exception as e:
        logger.error(f"Errore caricamento registro: {e}")
        return {
            "version": REGISTRY_VERSION,
            "last_updated": None,
            "analyzed_files": {}
        }


def save_registry(registry: Dict[str, Any]) -> bool:
    """
    Salva il registro delle analisi.
    
    Args:
        registry: Dizionario con i dati del registro
    
    Returns:
        True se salvato con successo
    """
    try:
        # Assicura che la directory esista
        REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        registry["last_updated"] = datetime.now().isoformat()
        
        with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)
        
        return True
    
    except Exception as e:
        logger.error(f"Errore salvataggio registro: {e}")
        return False


def is_already_analyzed(
    school_code: str,
    pdf_path: Path,
    registry: Optional[Dict[str, Any]] = None
) -> Tuple[bool, Optional[str]]:
    """
    Verifica se un file è già stato analizzato (stesso hash).
    
    Args:
        school_code: Codice meccanografico della scuola
        pdf_path: Percorso del file PDF
        registry: Registro (se None, viene caricato)
    
    Returns:
        Tupla (is_analyzed, reason)
        - (True, None) se già analizzato con stesso hash
        - (False, "new") se non presente nel registro
        - (False, "modified") se presente ma con hash diverso
        - (False, "missing_json") se registrato ma JSON mancante
    """
    if registry is None:
        registry = load_registry()
    
    analyzed_files = registry.get("analyzed_files", {})
    
    # Non presente nel registro
    if school_code not in analyzed_files:
        return False, "new"
    
    entry = analyzed_files[school_code]
    
    # Verifica che il JSON esista ancora
    json_path = Path(entry.get("json_path", ""))
    if not json_path.exists():
        return False, "missing_json"
    
    # Calcola hash corrente
    try:
        current_hash = compute_file_hash(pdf_path)
    except Exception as e:
        logger.error(f"Errore calcolo hash per {pdf_path}: {e}")
        return False, "hash_error"
    
    # Confronta hash
    stored_hash = entry.get("pdf_hash", "")
    if current_hash == stored_hash:
        return True, None
    else:
        return False, "modified"


def register_analysis(
    school_code: str,
    pdf_path: Path,
    json_path: Path,
    md_path: Optional[Path] = None,
    registry: Optional[Dict[str, Any]] = None,
    auto_save: bool = True
) -> Dict[str, Any]:
    """
    Registra una nuova analisi completata.
    
    Args:
        school_code: Codice meccanografico della scuola
        pdf_path: Percorso del file PDF sorgente
        json_path: Percorso del file JSON di analisi
        md_path: Percorso del file MD convertito (opzionale)
        registry: Registro esistente (se None, viene caricato)
        auto_save: Se True, salva automaticamente il registro
    
    Returns:
        Registro aggiornato
    """
    if registry is None:
        registry = load_registry()
    
    # Calcola hash del PDF
    try:
        pdf_hash = compute_file_hash(pdf_path)
    except Exception as e:
        logger.error(f"Errore calcolo hash per {pdf_path}: {e}")
        pdf_hash = "error:unable_to_compute"
    
    # Crea entry
    entry = {
        "pdf_hash": pdf_hash,
        "pdf_name": pdf_path.name,
        "pdf_size": pdf_path.stat().st_size if pdf_path.exists() else 0,
        "analyzed_at": datetime.now().isoformat(),
        "json_path": str(json_path),
        "workflow_version": REGISTRY_VERSION
    }
    
    if md_path:
        entry["md_path"] = str(md_path)
    
    # Aggiorna registro
    registry["analyzed_files"][school_code] = entry
    
    if auto_save:
        save_registry(registry)
    
    return registry


def get_pending_files(
    inbox_pdfs: List[Tuple[Path, str, Any]],
    registry: Optional[Dict[str, Any]] = None,
    verbose: bool = True
) -> Tuple[List[Tuple[Path, str, Any]], Dict[str, str]]:
    """
    Filtra i PDF che devono essere analizzati.
    
    Args:
        inbox_pdfs: Lista di tuple (pdf_path, school_code, miur_data)
        registry: Registro (se None, viene caricato)
        verbose: Se True, stampa informazioni di debug
    
    Returns:
        Tupla (pending_files, skip_reasons)
        - pending_files: Lista di file da analizzare
        - skip_reasons: Dizionario {school_code: reason} per file saltati
    """
    if registry is None:
        registry = load_registry()
    
    pending = []
    skipped = {}
    
    for pdf_path, school_code, miur_data in inbox_pdfs:
        is_done, reason = is_already_analyzed(school_code, pdf_path, registry)
        
        if is_done:
            skipped[school_code] = "already_analyzed"
            if verbose:
                print(f"⏭️ {school_code}: Già analizzato (hash identico)", flush=True)
        else:
            if reason == "modified":
                if verbose:
                    print(f"🔄 {school_code}: PDF modificato, ri-analizzo", flush=True)
            elif reason == "missing_json":
                if verbose:
                    print(f"⚠️ {school_code}: JSON mancante, ri-analizzo", flush=True)
            elif reason == "new":
                if verbose:
                    print(f"🆕 {school_code}: Nuovo file da analizzare", flush=True)
            
            pending.append((pdf_path, school_code, miur_data))
    
    return pending, skipped


def get_registry_stats() -> Dict[str, Any]:
    """
    Ottiene statistiche sul registro.
    
    Returns:
        Dizionario con statistiche
    """
    registry = load_registry()
    analyzed_files = registry.get("analyzed_files", {})
    
    # Conta file con JSON ancora esistente
    valid_count = 0
    missing_json = 0
    
    for school_code, entry in analyzed_files.items():
        json_path = Path(entry.get("json_path", ""))
        if json_path.exists():
            valid_count += 1
        else:
            missing_json += 1
    
    return {
        "version": registry.get("version", "unknown"),
        "last_updated": registry.get("last_updated"),
        "total_registered": len(analyzed_files),
        "valid_entries": valid_count,
        "missing_json": missing_json,
        "registry_path": str(REGISTRY_FILE)
    }


def clear_registry() -> bool:
    """
    Pulisce completamente il registro.
    
    Returns:
        True se pulito con successo
    """
    registry = {
        "version": REGISTRY_VERSION,
        "last_updated": datetime.now().isoformat(),
        "analyzed_files": {}
    }
    return save_registry(registry)


def remove_entry(school_code: str) -> bool:
    """
    Rimuove una singola entry dal registro.
    
    Args:
        school_code: Codice meccanografico da rimuovere
    
    Returns:
        True se rimosso con successo
    """
    registry = load_registry()
    
    if school_code in registry.get("analyzed_files", {}):
        del registry["analyzed_files"][school_code]
        return save_registry(registry)
    
    return False


def register_review(
    school_code: str,
    review_type: str,
    model: str,
    status: str,
    details: Optional[Dict[str, Any]] = None,
    registry: Optional[Dict[str, Any]] = None,
    auto_save: bool = True
) -> Dict[str, Any]:
    """
    Registra un'attività di revisione nel registro.
    
    Args:
        school_code: Codice meccanografico della scuola
        review_type: Tipo di revisione (es. "ollama_score_review", "ollama_report_review", "gemini_review")
        model: Modello LLM utilizzato
        status: Stato della revisione ("completed", "failed", "partial", "error")
        details: Dettagli aggiuntivi sulla revisione
        registry: Registro esistente (se None, viene caricato)
        auto_save: Se True, salva automaticamente il registro
    
    Returns:
        Registro aggiornato
    """
    if registry is None:
        registry = load_registry()
    
    analyzed_files = registry.get("analyzed_files", {})
    
    # Se la scuola non è nel registro, crea entry base
    if school_code not in analyzed_files:
        analyzed_files[school_code] = {
            "pdf_hash": "unknown",
            "pdf_name": f"{school_code}_ptof.pdf",
            "analyzed_at": "unknown",
            "json_path": "",
            "reviews": []
        }
    
    # Assicura che esista la lista reviews
    if "reviews" not in analyzed_files[school_code]:
        analyzed_files[school_code]["reviews"] = []
    
    # Aggiungi la revisione
    review_entry = {
        "type": review_type,
        "model": model,
        "status": status,
        "timestamp": datetime.now().isoformat()
    }
    
    if details:
        review_entry["details"] = details
    
    analyzed_files[school_code]["reviews"].append(review_entry)
    analyzed_files[school_code]["last_review"] = datetime.now().isoformat()
    
    registry["analyzed_files"] = analyzed_files
    
    if auto_save:
        save_registry(registry)
    
    return registry


def get_review_status(school_code: str, review_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Ottiene lo stato delle revisioni per una scuola.
    
    Args:
        school_code: Codice meccanografico della scuola
        review_type: Tipo specifico di revisione (se None, ritorna tutte)
    
    Returns:
        Dizionario con info sulle revisioni o None se non trovato
    """
    registry = load_registry()
    analyzed_files = registry.get("analyzed_files", {})
    
    if school_code not in analyzed_files:
        return None
    
    entry = analyzed_files[school_code]
    reviews = entry.get("reviews", [])
    
    if review_type:
        # Filtra per tipo
        filtered = [r for r in reviews if r.get("type") == review_type]
        return {
            "school_code": school_code,
            "review_type": review_type,
            "total_reviews": len(filtered),
            "last_review": filtered[-1] if filtered else None,
            "reviews": filtered
        }
    else:
        return {
            "school_code": school_code,
            "total_reviews": len(reviews),
            "last_review": entry.get("last_review"),
            "reviews": reviews
        }


def was_reviewed(school_code: str, review_type: str, registry: Optional[Dict[str, Any]] = None) -> bool:
    """
    Verifica se una scuola è già stata revisionata con un certo tipo di review.
    
    Args:
        school_code: Codice meccanografico della scuola
        review_type: Tipo di revisione
        registry: Registro (se None, viene caricato)
    
    Returns:
        True se già revisionata con successo
    """
    if registry is None:
        registry = load_registry()
    
    analyzed_files = registry.get("analyzed_files", {})
    
    if school_code not in analyzed_files:
        return False
    
    reviews = analyzed_files[school_code].get("reviews", [])
    
    # Cerca una revisione completata dello stesso tipo
    for review in reviews:
        if review.get("type") == review_type and review.get("status") == "completed":
            return True
    
    return False


def get_review_stats() -> Dict[str, Any]:
    """
    Ottiene statistiche sulle revisioni.
    
    Returns:
        Dizionario con statistiche
    """
    registry = load_registry()
    analyzed_files = registry.get("analyzed_files", {})
    
    stats = {
        "total_schools": len(analyzed_files),
        "schools_with_reviews": 0,
        "reviews_by_type": {},
        "reviews_by_status": {}
    }
    
    for school_code, entry in analyzed_files.items():
        reviews = entry.get("reviews", [])
        if reviews:
            stats["schools_with_reviews"] += 1
        
        for review in reviews:
            r_type = review.get("type", "unknown")
            r_status = review.get("status", "unknown")
            
            stats["reviews_by_type"][r_type] = stats["reviews_by_type"].get(r_type, 0) + 1
            stats["reviews_by_status"][r_status] = stats["reviews_by_status"].get(r_status, 0) + 1
    
    return stats


# CLI per test e debug
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Gestione registro analisi PTOF")
    parser.add_argument("--stats", action="store_true", help="Mostra statistiche")
    parser.add_argument("--clear", action="store_true", help="Pulisce il registro")
    parser.add_argument("--remove", type=str, help="Rimuove una entry specifica")
    parser.add_argument("--list", action="store_true", help="Lista tutte le entry")
    parser.add_argument("--reviews", action="store_true", help="Mostra statistiche revisioni")
    parser.add_argument("--school", type=str, help="Mostra dettagli per una scuola specifica")
    
    args = parser.parse_args()
    
    if args.stats:
        stats = get_registry_stats()
        print("\n📊 STATISTICHE REGISTRO ANALISI")
        print("=" * 50)
        print(f"📁 File registro: {stats['registry_path']}")
        print(f"📌 Versione: {stats['version']}")
        print(f"🕐 Ultimo aggiornamento: {stats['last_updated'] or 'Mai'}")
        print(f"📋 Totale registrati: {stats['total_registered']}")
        print(f"✅ Entry valide: {stats['valid_entries']}")
        print(f"❌ JSON mancanti: {stats['missing_json']}")
        
        # Aggiungi stats revisioni
        review_stats = get_review_stats()
        if review_stats["schools_with_reviews"] > 0:
            print(f"\n🔍 REVISIONI:")
            print(f"   Scuole con revisioni: {review_stats['schools_with_reviews']}")
            print(f"   Per tipo:")
            for r_type, count in review_stats["reviews_by_type"].items():
                print(f"      - {r_type}: {count}")
            print(f"   Per stato:")
            for r_status, count in review_stats["reviews_by_status"].items():
                print(f"      - {r_status}: {count}")
    
    elif args.reviews:
        review_stats = get_review_stats()
        print("\n🔍 STATISTICHE REVISIONI")
        print("=" * 50)
        print(f"📋 Scuole totali: {review_stats['total_schools']}")
        print(f"✨ Scuole con revisioni: {review_stats['schools_with_reviews']}")
        print(f"\n📊 Per tipo di revisione:")
        for r_type, count in review_stats["reviews_by_type"].items():
            print(f"   {r_type}: {count}")
        print(f"\n📊 Per stato:")
        for r_status, count in review_stats["reviews_by_status"].items():
            emoji = "✅" if r_status == "completed" else "❌" if r_status in ["failed", "error"] else "⚠️"
            print(f"   {emoji} {r_status}: {count}")
    
    elif args.school:
        review_info = get_review_status(args.school)
        if review_info:
            print(f"\n📋 DETTAGLI SCUOLA: {args.school}")
            print("=" * 50)
            print(f"Revisioni totali: {review_info['total_reviews']}")
            print(f"Ultima revisione: {review_info['last_review']}")
            print(f"\nStorico revisioni:")
            for i, rev in enumerate(review_info['reviews'], 1):
                status_emoji = "✅" if rev['status'] == "completed" else "❌"
                print(f"  {i}. {status_emoji} {rev['type']} - {rev['model']} [{rev['timestamp'][:16]}]")
                if rev.get('details'):
                    for k, v in rev['details'].items():
                        print(f"      {k}: {v}")
        else:
            print(f"❌ Scuola {args.school} non trovata nel registro")
    
    elif args.clear:
        confirm = input("⚠️ Sei sicuro di voler pulire il registro? (s/N): ")
        if confirm.lower() == 's':
            if clear_registry():
                print("✅ Registro pulito con successo")
            else:
                print("❌ Errore pulizia registro")
        else:
            print("Operazione annullata")
    
    elif args.remove:
        if remove_entry(args.remove):
            print(f"✅ Entry {args.remove} rimossa")
        else:
            print(f"❌ Entry {args.remove} non trovata")
    
    elif args.list:
        registry = load_registry()
        analyzed = registry.get("analyzed_files", {})
        print(f"\n📋 ENTRY REGISTRATE ({len(analyzed)})")
        print("=" * 70)
        for code, entry in sorted(analyzed.items()):
            date = entry.get("analyzed_at", "?")[:10]
            reviews_count = len(entry.get("reviews", []))
            reviews_str = f" [📝{reviews_count}]" if reviews_count > 0 else ""
            print(f"  {code}: {entry.get('pdf_name', '?')[:40]} [{date}]{reviews_str}")
    
    else:
        parser.print_help()
