#!/usr/bin/env python3
"""
Centralized configuration for the PTOF analysis system.
All paths and settings should be imported from here.

Environment variables can be used to override defaults:
- OLLAMA_URL: URL of the Ollama API server
- BASE_DIR: Base directory for the project (defaults to parent of this file's directory)
"""
import os
from pathlib import Path

# ============================================================================
# BASE PATHS
# ============================================================================

# Base directory (project root)
BASE_DIR = Path(os.environ.get('PTOF_BASE_DIR', Path(__file__).parent.parent))

# Data directories
DATA_DIR = BASE_DIR / 'data'
PTOF_INBOX_DIR = BASE_DIR / 'ptof_inbox'
PTOF_MD_DIR = BASE_DIR / 'ptof_md'
PTOF_PROCESSED_DIR = BASE_DIR / 'ptof_processed'
ANALYSIS_RESULTS_DIR = BASE_DIR / 'analysis_results'
CONFIG_DIR = BASE_DIR / 'config'

# ============================================================================
# DATA FILES
# ============================================================================

# MIUR School Database CSVs
SCUOLA_STATALE_CSV = DATA_DIR / 'SCUANAGRAFESTAT20252620250901.csv'
SCUOLA_PARITARIA_CSV = DATA_DIR / 'SCUANAGRAFEPAR20252620250901.csv'

# Enrichment data
METADATA_ENRICHMENT_CSV = DATA_DIR / 'metadata_enrichment.csv'
COMUNI_ITALIANI_JSON = DATA_DIR / 'comuni_italiani.json'

# Output files
ANALYSIS_SUMMARY_CSV = DATA_DIR / 'analysis_summary.csv'

# Config files
REGION_MAP_JSON = CONFIG_DIR / 'region_map.json'
PROMPTS_FILE = CONFIG_DIR / 'prompts.md'

# ============================================================================
# LLM CONFIGURATION
# ============================================================================

# Ollama API
OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://192.168.129.14:11434/api/generate')
OLLAMA_TIMEOUT = int(os.environ.get('OLLAMA_TIMEOUT', '300'))

# Model names
MODEL_ANALYST = os.environ.get('MODEL_ANALYST', 'gemma3:27b')
MODEL_REVIEWER = os.environ.get('MODEL_REVIEWER', 'qwen3:32b')
MODEL_REFINER = os.environ.get('MODEL_REFINER', 'gemma3:27b')
MODEL_SYNTHESIZER = os.environ.get('MODEL_SYNTHESIZER', 'gemma3:27b')

# ============================================================================
# DOCUMENT PROCESSING
# ============================================================================

# Chunking configuration for long documents
CHUNK_SIZE = int(os.environ.get('CHUNK_SIZE', '40000'))
LONG_DOC_THRESHOLD = int(os.environ.get('LONG_DOC_THRESHOLD', '60000'))

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def ensure_directories():
    """Create all required directories if they don't exist."""
    for d in [DATA_DIR, PTOF_INBOX_DIR, PTOF_MD_DIR, PTOF_PROCESSED_DIR, ANALYSIS_RESULTS_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def get_path(name: str) -> Path:
    """
    Get a path by name for easier access.

    Args:
        name: One of 'data', 'inbox', 'md', 'processed', 'results', 'config'

    Returns:
        Path object for the requested directory
    """
    paths = {
        'data': DATA_DIR,
        'inbox': PTOF_INBOX_DIR,
        'md': PTOF_MD_DIR,
        'processed': PTOF_PROCESSED_DIR,
        'results': ANALYSIS_RESULTS_DIR,
        'config': CONFIG_DIR,
        'base': BASE_DIR,
    }
    return paths.get(name, BASE_DIR)
