# Make - Quick Start

Elenco rapido dei comandi principali. Per la guida completa vedi
[MAKE_REFERENCE](MAKE_REFERENCE.md).

## Core commands

- make setup
- make run
- make workflow
- make dashboard
- make refresh
- make help
- make wizard

## Workflow tipici

### Analisi standard
```bash
make run
make dashboard
```

### Refresh dati
```bash
make csv
make dashboard
```

### Download + analisi
```bash
make download-sample
make workflow
```

## Catalogo buone pratiche
```bash
make activity-extract
make activity-extract-reset
make activity-extract-stats
```

## Note
- Per configurazioni modelli usa make config / make config-show.
- Per revisioni e manutenzione vedi MAKE_REFERENCE.
