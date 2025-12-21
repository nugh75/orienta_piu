#!/usr/bin/env python3
"""
Text Chunker for Long PTOF Documents

Provides intelligent text segmentation strategies for documents up to 300+ pages.
Supports splitting by markdown headers, fixed size with overlap, or smart combination.
"""
import re
from typing import List, Tuple

# Default configuration
DEFAULT_CHUNK_SIZE = 50000  # ~15-20 pages
DEFAULT_OVERLAP = 2000      # Context preservation
DEFAULT_MIN_CHUNK = 5000    # Avoid tiny chunks


def split_by_headers(text: str, min_level: int = 2, max_level: int = 3) -> List[Tuple[str, str]]:
    """
    Split text by markdown headers (## or ###).
    
    Args:
        text: Full markdown text
        min_level: Minimum header level (2 = ##)
        max_level: Maximum header level (3 = ###)
    
    Returns:
        List of (header_title, section_content) tuples
    """
    # Pattern for headers from min to max level
    header_pattern = r'^(#{' + str(min_level) + ',' + str(max_level) + r'})\s+(.+?)$'
    
    sections = []
    current_header = "INTRO"
    current_content = []
    
    for line in text.split('\n'):
        match = re.match(header_pattern, line, re.MULTILINE)
        if match:
            # Save previous section
            if current_content:
                sections.append((current_header, '\n'.join(current_content)))
            current_header = match.group(2).strip()
            current_content = [line]
        else:
            current_content.append(line)
    
    # Don't forget last section
    if current_content:
        sections.append((current_header, '\n'.join(current_content)))
    
    return sections


def split_by_size(text: str, max_chars: int = DEFAULT_CHUNK_SIZE, 
                  overlap: int = DEFAULT_OVERLAP) -> List[str]:
    """
    Split text into chunks of fixed size with overlap.
    
    Args:
        text: Full text to split
        max_chars: Maximum characters per chunk
        overlap: Overlap characters between chunks for context
    
    Returns:
        List of text chunks
    """
    if len(text) <= max_chars:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + max_chars
        
        if end >= len(text):
            # Last chunk
            chunks.append(text[start:])
            break
        
        # Try to find a good break point (paragraph, sentence, word)
        chunk = text[start:end]
        
        # Look for paragraph break in last 20% of chunk
        search_start = int(len(chunk) * 0.8)
        
        # Priority: paragraph > sentence > word
        para_break = chunk.rfind('\n\n', search_start)
        if para_break > search_start:
            end = start + para_break + 2
        else:
            sent_break = chunk.rfind('. ', search_start)
            if sent_break > search_start:
                end = start + sent_break + 2
            else:
                word_break = chunk.rfind(' ', search_start)
                if word_break > search_start:
                    end = start + word_break + 1
        
        chunks.append(text[start:end])
        start = end - overlap  # Apply overlap
    
    return chunks


def smart_split(text: str, max_chars: int = DEFAULT_CHUNK_SIZE,
                overlap: int = DEFAULT_OVERLAP,
                min_chunk: int = DEFAULT_MIN_CHUNK) -> List[str]:
    """
    Smart splitting: first by headers, then by size if sections are too large.
    Merges small sections together.
    
    Args:
        text: Full markdown text
        max_chars: Maximum characters per final chunk
        overlap: Overlap between size-split chunks
        min_chunk: Minimum chunk size (merge smaller ones)
    
    Returns:
        List of text chunks optimized for LLM processing
    """
    # Step 1: Split by headers
    sections = split_by_headers(text)
    
    if not sections:
        # No headers found, fall back to size split
        return split_by_size(text, max_chars, overlap)
    
    # Step 2: Process sections - merge small, split large
    chunks = []
    buffer = ""
    
    for header, content in sections:
        section_text = content if header == "INTRO" else f"## {header}\n{content}"
        
        if len(section_text) > max_chars:
            # Section too large - flush buffer first
            if buffer:
                chunks.append(buffer)
                buffer = ""
            # Split this section by size
            sub_chunks = split_by_size(section_text, max_chars, overlap)
            chunks.extend(sub_chunks)
        
        elif len(buffer) + len(section_text) > max_chars:
            # Adding this section would exceed limit - flush buffer
            if buffer:
                chunks.append(buffer)
            buffer = section_text
        
        elif len(buffer) + len(section_text) < min_chunk:
            # Still small, keep accumulating
            buffer += "\n\n" + section_text if buffer else section_text
        
        else:
            # Good size, add to buffer
            buffer += "\n\n" + section_text if buffer else section_text
    
    # Don't forget remaining buffer
    if buffer:
        chunks.append(buffer)
    
    return chunks


def estimate_tokens(text: str) -> int:
    """
    Estimate token count (rough approximation: 1 token ≈ 4 chars for Italian).
    """
    return len(text) // 4


def get_chunk_info(chunks: List[str]) -> dict:
    """
    Get statistics about chunks.
    """
    if not chunks:
        return {"count": 0}
    
    sizes = [len(c) for c in chunks]
    return {
        "count": len(chunks),
        "total_chars": sum(sizes),
        "avg_chars": sum(sizes) // len(chunks),
        "min_chars": min(sizes),
        "max_chars": max(sizes),
        "estimated_tokens": sum(estimate_tokens(c) for c in chunks)
    }


# Convenience function for processing
def chunk_document(text: str, strategy: str = "smart", 
                   max_chars: int = DEFAULT_CHUNK_SIZE) -> List[str]:
    """
    Main entry point for chunking documents.
    
    Args:
        text: Full document text
        strategy: "smart", "headers", or "size"
        max_chars: Maximum chars per chunk
    
    Returns:
        List of text chunks
    """
    if strategy == "headers":
        sections = split_by_headers(text)
        return [content for _, content in sections]
    elif strategy == "size":
        return split_by_size(text, max_chars)
    else:  # smart
        return smart_split(text, max_chars)


if __name__ == "__main__":
    # Test with sample text
    sample = "# Titolo\n\n" + "Lorem ipsum. " * 5000 + "\n\n## Sezione 1\n" + "Contenuto sezione 1. " * 3000
    
    print("Testing text chunker...")
    print(f"Sample size: {len(sample)} chars")
    
    chunks = smart_split(sample)
    info = get_chunk_info(chunks)
    
    print(f"Chunks: {info['count']}")
    print(f"Avg size: {info['avg_chars']} chars")
    print(f"Est tokens: {info['estimated_tokens']}")
