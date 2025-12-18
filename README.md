# PTOF Analysis Repository

This repository contains tools to discover, download, and analyze PTOF (Piano Triennale dell'Offerta Formativa) documents from Italian schools.

## Directory Structure

*   **`data/`**: Contains all input CSV files (school lists, candidates) and output reports (`risultati_analisi.csv`, `ptof_report.csv`).
*   **`scripts/`**: Executable scripts for specific tasks.
    *   `download.py`: Downloads PTOF PDFs from URLs listed in `data/candidati_ptof.csv`.
    *   `organize.py`: Validates, renames, and organizes downloaded PDFs into the `ptof/` directory.
*   **`ptof_pipeline/`**: The core Python package for analysis logic (scraping, text extraction, LLM analysis).
*   **`ptof_downloads/`**: Default download directory for raw files.
*   **`ptof/`**: Cleaned and organized directory for valid PTOF files.
*   **`legacy/`**: Archived scripts and older experiments.
*   **`tests/`**: Unit tests.

## Setup

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

### 1. Download PTOFs
To download PTOFs for schools identified in `data/candidati_ptof.csv`:

```bash
python scripts/download.py
```
*   Files are saved to `ptof_downloads/`.
*   Invalid PDFs are automatically skipped or re-downloaded.

### 2. Organize and Validate
To filter valid PTOFs and organize them into `ptof/`:

```bash
python scripts/organize.py
```
*   Reads metadata from `data/`.
*   Checks PDF content for PTOF keywords.
*   Copies valid files to `ptof/`.
*   Generates `data/ptof_report.csv`.

### 3. Run Analysis Pipeline
To run the full text analysis pipeline (requires Ollama):

```bash
python -m ptof_pipeline.pipeline
```
*   Reads `data/candidati_ptof.csv`.
*   Uses local files if available.
*   Outputs to `data/risultati_analisi.csv`.

## Legacy Files
Old scripts (`crawler_download.py`, `find_ptofs.py`, etc.) have been moved to `legacy/`. They are not required for the main workflow.
