# Mappa Documentazione

Questa mappa e il punto di ingresso per la documentazione del progetto.
Aggiornala quando si spostano o si aggiungono documenti.

## Percorsi consigliati

### Avvio rapido (operativo)
- [README](../README.md)
- [Workflow](operations/WORKFLOW_README.md)
- [Makefile reference](reference/MAKE_REFERENCE.md)
- [Make quick start](reference/MAKE_COMMANDS.md)
- [Dashboard](dashboard/DASHBOARD_README.md)
- [Log & tmux (rapida)](LOGS_TMUX.md)

### Analisi e metodologia
- [Documentazione analisi](analysis/DOCUMENTAZIONE_ANALISI.md)
- [Piano refactoring metadati](analysis/PIANO_REFACTORING_METADATI.md)

### Architettura e dati
- [Directory structure](architecture/DIRECTORY_STRUCTURE.md)
- [Workflow diagram](architecture/workflow_diagram.md)
- [Dependency tree](architecture/DEPENDENCY_TREE.md)

### Manutenzione e troubleshooting
- [Troubleshooting](operations/TROUBLESHOOTING.md)
- maintenance/DEPRECATION_FIX.md
- maintenance/DEPRECATION_FIX_UPDATE.md
- maintenance/FIX_AREA_GEOGRAFICA.md
- maintenance/FIX_FILTRI_DUPLICATI.md
- maintenance/NOTEBOOK_FIX.md
- maintenance/NOTEBOOK_UPDATE.md

### Roadmap e pianificazione
- roadmap/TODO.md
- roadmap/TODO_Scegli_la_Tua_Scuola.md
- roadmap/DEPLOY_WSL_AUTOSTART.md

### Outreach e download
- [Outreach](outreach/ptof_outreach.md)
- [Outreach module](../src/outreach/README.md)
- [Downloader](../src/downloaders/README.md)

### Esempi e asset
- CLI_Examples.ipynb
- DOCUMENTAZIONE_ANALISI.pdf
- report_estrazione.pdf
- VTIC82500A_analysis.pdf
- Analisi Report Estrazione Statistica Scuole.docx

## Mappa repository (cartelle principali)

- app/                         Dashboard Streamlit
- src/                         Pipeline, utility, moduli
- ptof_inbox/                  PDF da analizzare
- ptof_processed/              PDF archiviati per batch
- ptof_md/                     Markdown estratti
- analysis_results/            JSON + report MD per scuola
- data/                        Dataset, registry, config
- logs/                        Log runtime
- reports/                     Output legacy o manuali
