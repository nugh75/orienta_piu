# Workflow Diagram

## Pipeline Overview

```mermaid
flowchart TD
    subgraph Input["📥 Input Phase"]
        PDF[("PTOF PDF Files<br/>ptof/")]
        CONVERT["convert_pdfs_to_md.py"]
        MD[("Markdown Files<br/>ptof_md/")]
    end

    subgraph Metadata["📋 Metadata Sources"]
        REGISTRY[("Official Registry<br/>metadata_enrichment.csv")]
        INVALSI[("INVALSI Data<br/>invalsi_unified.csv")]
    end

    subgraph Agents["🤖 3-Agent Pipeline"]
        ANALYST["🔍 Analyst<br/>(gemma3:27b)"]
        REVIEWER["⚖️ Reviewer<br/>(qwen3:32b)"]
        REFINER["✨ Refiner<br/>(gemma3:27b)"]
    end

    subgraph Output["📤 Output Phase"]
        JSON[("Analysis JSON<br/>analysis_results/")]
        REPORT[("MD Report<br/>analysis_results/")]
        CSV[("Summary CSV<br/>data/")]
        DASH["📊 Dashboard<br/>localhost:8501"]
    end

    PDF --> CONVERT --> MD
    MD --> ANALYST
    ANALYST --> |"Draft"| REVIEWER
    REVIEWER --> |"Critique"| REFINER
    REFINER --> JSON
    REFINER --> REPORT
    
    REGISTRY --> JSON
    INVALSI --> JSON
    
    JSON --> |"rebuild_csv.py"| CSV
    CSV --> DASH
```

## Agent Flow Detail

```mermaid
sequenceDiagram
    participant M as Markdown
    participant A as Analyst
    participant V as Reviewer
    participant R as Refiner
    participant O as Output

    M->>A: School Document
    A->>A: Extract Scores + Write Narrative
    A->>V: Draft JSON + Report
    V->>V: Red-Team Analysis
    
    alt Critique Found
        V->>R: Critique Points
        R->>R: Correct Scores + Rewrite
        R->>O: Final JSON + Report
    else Approved
        V->>O: Direct Approval
    end
    
    O->>O: Enrich Metadata from CSV
    O->>O: Rebuild Summary CSV
```

## Scoring Dimensions

| Code | Dimension | Sub-indicators |
|------|-----------|----------------|
| 2.1 | Sezione Dedicata | Presenza, Chiarezza |
| 2.2 | Partnership | Partner nominati, Count |
| 2.3 | Finalità | Attitudini, Interessi, Progetto Vita, Transizioni, Capacità |
| 2.4 | Obiettivi | Abbandono, Continuità, NEET, Lifelong |
| 2.5 | Governance | Coordinamento, Dialogo, Genitori, Monitoraggio, Inclusione |
| 2.6 | Didattica | Esperienza, Laboratoriale, Flessibilità, Interdisciplinare |
| 2.7 | Opportunità | Culturali, Espressive, Ricreative, Volontariato, Sport |
