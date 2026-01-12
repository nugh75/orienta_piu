#!/usr/bin/env python3
"""Agente raffinatore per report meta-report.

Chunkizza il testo del report e corregge la formattazione markdown
usando chiamate LLM per ogni chunk.

Uso:
    python -m src.agents.meta_report.refine REPORT_PATH [--provider PROVIDER]
"""

import argparse
import os
import re
import difflib
from pathlib import Path
from typing import Optional

from .providers.ollama import OllamaProvider
from .providers.gemini import GeminiProvider
from .providers.openrouter import OpenRouterProvider


CHUNK_SIZE = 3000  # Caratteri per chunk
OVERLAP = 200  # Overlap tra chunk per mantenere contesto


def get_provider(provider_name: str):
    """Ottiene il provider LLM appropriato."""
    if provider_name == "gemini":
        return GeminiProvider()
    elif provider_name == "openrouter":
        return OpenRouterProvider()
    else:
        return OllamaProvider()


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = OVERLAP) -> list[tuple[int, int, str]]:
    """Divide il testo in chunk con overlap.
    
    Returns:
        Lista di (start_pos, end_pos, chunk_text)
    """
    chunks = []
    start = 0
    
    while start < len(text):
        end = min(start + chunk_size, len(text))
        
        # Cerca un punto di rottura naturale (fine paragrafo o fine frase)
        if end < len(text):
            # Cerca fine paragrafo
            newline_pos = text.rfind('\n\n', start, end)
            if newline_pos > start + chunk_size // 2:
                end = newline_pos + 2
            else:
                # Cerca fine frase
                sentence_end = max(
                    text.rfind('. ', start, end),
                    text.rfind('.\n', start, end),
                    text.rfind('! ', start, end),
                    text.rfind('? ', start, end)
                )
                if sentence_end > start + chunk_size // 2:
                    end = sentence_end + 2
        
        chunk = text[start:end]
        chunks.append((start, end, chunk))
        
        # Prossimo chunk con overlap
        start = end - overlap if end < len(text) else end
    
    return chunks


def refine_chunk(provider, chunk: str, chunk_index: int, total_chunks: int) -> str:
    """Raffina un singolo chunk di testo."""
    
    prompt = f"""Correggi e raffina la formattazione di questo testo markdown (chunk {chunk_index + 1}/{total_chunks}).

TESTO DA RAFFINARE:
{chunk}

COMPITI:
1. Correggi problemi di formattazione markdown:
   - Rimuovi ** orfani o mal posizionati
   - Assicura che il grassetto (**testo**) sia correttamente chiuso
   - Correggi header malformati
   - Rimuovi righe duplicate

2. NON modificare il contenuto testuale, solo la formattazione

3. NON aggiungere commenti o spiegazioni

4. Restituisci SOLO il testo corretto, nient'altro

TESTO CORRETTO:"""

    try:
        response = provider.generate(prompt)
        # Handle LLMResponse object
        if hasattr(response, 'content'):
            return response.content.strip()
        return str(response).strip()
    except Exception as e:
        print(f"[refine] Errore chunk {chunk_index + 1}: {e}")
        return chunk  # Ritorna originale in caso di errore


from .postprocess import postprocess_report

# ... (omitted code) ...


def merge_chunks(base: str, extension: str, overlap_hint: int = 500) -> str:
    """Merges extension into base, removing the overlapping part from extension."""
    if not base:
        return extension

    # Look at the end of base and start of extension
    # We expect roughly OVERLAP chars to match
    tail = base[-overlap_hint:] 
    head = extension[:overlap_hint]

    s = difflib.SequenceMatcher(None, tail, head)
    match = s.find_longest_match(0, len(tail), 0, len(head))

    # If we found a significant match (> 20 chars), we assume that is the alignment point.
    if match.size > 20:
        return base + extension[match.b + match.size:]
    
    # Fallback to simple line checking
    lines = extension.split('\n')
    skip_lines = 0
    for line in lines[:5]:
        stripped = line.strip()
        if stripped and stripped in base[-500:]:
             skip_lines += 1
        elif not stripped:
             pass # keep skipping empty lines if we are in overlap zone
        else:
             break # divergent line found
    
    return base + "\n" + "\n".join(lines[skip_lines:])


# ... (omitted code) ...

def refine_report(
    report_path: Path,
    provider_name: str = "ollama",
    output_path: Optional[Path] = None,
    dry_run: bool = False
) -> str:
    """Raffina un intero report."""
    
    if not report_path.exists():
        raise FileNotFoundError(f"Report non trovato: {report_path}")
    
    print(f"[refine] Caricamento report: {report_path}")
    content = report_path.read_text(encoding="utf-8")
    original_len = len(content)
    
    # Ottieni provider
    provider = get_provider(provider_name)
    print(f"[refine] Provider: {provider_name}")
    
    # Chunkizza
    chunks = chunk_text(content)
    print(f"[refine] Report suddiviso in {len(chunks)} chunk")
    
    # Raffina ogni chunk
    refined_chunks = []
    for i, (start, end, chunk) in enumerate(chunks):
        print(f"[refine] Raffinamento chunk {i + 1}/{len(chunks)}...")
        refined = refine_chunk(provider, chunk, i, len(chunks))
        refined_chunks.append(refined)
    
    # Ricomponi (gestendo overlap)
    refined_content = refined_chunks[0] if refined_chunks else ""
    for i in range(1, len(refined_chunks)):
        refined_content = merge_chunks(refined_content, refined_chunks[i])

    
    # Post-processing avanzato usando il modulo postprocess
    print("[refine] Esecuzione post-processing avanzato...")
    # Salviamo temporaneamente per postprocess_report che lavora su file o stringhe
    # Ma postprocess_report prende un path.
    # Possiamo chiamare le funzioni interne di postprocess se le importiamo, 
    # oppure modificare postprocess_report per accettare stringa e ritornare stringa.
    # postprocess_report attualmente legge da file e scrive su file.
    
    # Facciamo così: scriviamo il refined_content su output_path (o temp) e poi chiamiamo postprocess_report
    if output_path is None:
        output_path = report_path
        
    if not dry_run:
        output_path.write_text(refined_content, encoding="utf-8")
        # Chiama postprocess pipeline sul file
        postprocess_report(
            report_path=output_path,
            output_path=output_path, # overwrite
            dry_run=False
        )
        # Rileggi il contenuto finale
        refined_content = output_path.read_text(encoding="utf-8")
    
    new_len = len(refined_content)
    print(f"[refine] Lunghezza: {original_len} → {new_len} chars")
    
    if dry_run:
        print("[refine] DRY RUN - nessuna modifica salvata")
        return refined_content
    
    # (File già salvato da postprocess_report)
    print(f"[refine] Salvato e processato: {output_path}")
    
    return refined_content


def post_process(content: str) -> str:
    """Post-processing finale dopo raffinamento LLM."""
    
    # Rimuovi ** orfani a fine riga
    content = re.sub(r'\*\*\s*$', '', content, flags=re.MULTILINE)
    
    # Rimuovi ** orfani a inizio riga
    content = re.sub(r'^\*\*\s+', '', content, flags=re.MULTILINE)
    
    # Rimuovi ** dentro parole
    for _ in range(3):
        content = re.sub(r'(\w)\*\*(\w)', r'\1\2', content)
    
    # Rimuovi header duplicati consecutivi
    lines = content.split('\n')
    result = []
    prev_line = None
    for line in lines:
        if line.strip().startswith('#') and line.strip() == (prev_line or "").strip():
            continue
        result.append(line)
        prev_line = line
    content = '\n'.join(result)
    
    # Rimuovi linee vuote eccessive (max 2 consecutive)
    content = re.sub(r'\n{4,}', '\n\n\n', content)
    
    return content


def main():
    parser = argparse.ArgumentParser(description="Raffina formattazione report meta-report")
    parser.add_argument("report", type=Path, help="Path al report da raffinare")
    parser.add_argument("--provider", "-p", default="ollama", 
                       choices=["ollama", "gemini", "openrouter"],
                       help="Provider LLM da usare")
    parser.add_argument("--output", "-o", type=Path, help="Path output (default: sovrascrive)")
    parser.add_argument("--dry-run", "-n", action="store_true",
                       help="Mostra modifiche senza salvare")
    
    args = parser.parse_args()
    
    refine_report(
        report_path=args.report,
        provider_name=args.provider,
        output_path=args.output,
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    main()
