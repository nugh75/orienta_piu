# Dependency Tree (High-Level)

This document summarizes direct imports and file dependencies. It is a high-level map,
not an exhaustive module graph.

Legend:
- "->" indicates a direct import or direct file usage
- Paths are repo-relative unless noted

## Entry Points

workflow_notebook.py
  -> src.validation.ptof_validator
  -> src.processing.convert_pdfs_to_md
  -> src.utils.analysis_registry
  -> src.utils.school_database
  -> src.data.rebuild_csv
  -> data: analysis_results/, ptof_md/, ptof_inbox/, ptof_processed/, data/analysis_summary.csv

app/agentic_pipeline.py
  -> src.llm.client
  -> src.processing.text_chunker
  -> src.processing.cloud_review
  -> src.utils.file_utils
  -> src.utils.constants
  -> src.utils.school_code_parser
  -> src.utils.config_loader
  -> config: config/pipeline_config.json, config/prompts.md
  -> data: data/metadata_enrichment.csv, analysis_results/, ptof_md/

app/Home.py and app/pages/*
  -> app/data_utils.py
  -> src.utils.backup_system (data management page)
  -> data: data/analysis_summary.csv, analysis_results/

launcher.py
  -> src/utils/list_models.py

launcher_web.py
  -> config: config/pipeline_config.json
  -> data: data/processes.json, data/processes_archive.json
  -> external: OpenRouter API (requests)

run_reviewer.py
  -> src.processing.bg_reviewer
  -> config: config/prompts.md

reproduce_issue.py
  -> src.processing.background_reviewer (module name referenced by script)

fix_truncated_reports.py
  -> src/processing/ollama_report_reviewer.py (subprocess)

check_truncated.py / restore_from_backup.py / recover_files.py
  -> analysis_results/

## Core Packages (src/)

src/processing
  -> src.utils (file_utils, analysis_registry, constants, school_database)
  -> src.validation (non_ptof_reviewer)
  -> config: config/prompts.md
  -> data: data/metadata_enrichment.csv, data/comuni_italiani.json

src/validation
  -> src.utils.config_loader
  -> config: config/prompts.md
  -> data: data/ptof_validator_allowlist.txt, data/validation_registry.json

src/llm
  -> external: Ollama / OpenRouter / OpenAI-compatible HTTP APIs (requests)

src/utils
  -> data: data/comuni_italiani.json
  -> config: config/prompts.md

src/agents
  -> analysis_results/
  -> data/analysis_summary.csv
  -> reports/
