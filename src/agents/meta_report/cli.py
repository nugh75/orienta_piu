#!/usr/bin/env python3
"""CLI for meta report generation."""

import argparse
import sys
import logging
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Setup logging
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / 'meta_report.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Load .env file
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from src.agents.meta_report.orchestrator import MetaReportOrchestrator


def _apply_refine(report_path, provider_name: str = "auto"):
    """Apply LLM-based refinement to a generated report."""
    from src.agents.meta_report.refine import refine_report
    print(f"Applying refinement to: {report_path}")
    try:
        refine_report(report_path, provider_name=provider_name if provider_name != "auto" else "ollama")
        print("Refinement complete.")
    except Exception as e:
        print(f"Warning: Refinement failed: {e}")


def main():
    parser = argparse.ArgumentParser(description="Meta Report Generator - Best Practices from PTOF analyses")
    parser.add_argument("command", choices=["status", "school", "skeleton", "next", "batch"],
                       help="Command to execute")
    parser.add_argument("--code", "-c", help="School code for school report")
    parser.add_argument("--region", "-r", help="Region name for regional report")
    parser.add_argument("--dim", "-d", help="Dimension for thematic report")
    parser.add_argument("--provider", "-p", default="auto",
                       choices=["auto", "gemini", "openrouter", "ollama"],
                       help="LLM provider to use")
    parser.add_argument("--provider-school", default="ollama",
                       choices=["ollama", "openrouter", "gemini"],
                       help="Provider for school-level analysis (skeleton mode)")
    parser.add_argument("--provider-synthesis", default="openrouter",
                       choices=["ollama", "openrouter", "gemini"],
                       help="Provider for synthesis calls (skeleton mode)")
    parser.add_argument("--model-school", default=None,
                       help="Model for school-level analysis (e.g., gemma3:27b)")
    parser.add_argument("--model-synthesis", default=None,
                       help="Model for synthesis (e.g., google/gemini-2.0-flash-lite-001)")
    parser.add_argument("--prompt-profile", default="overview",
                       choices=["overview", "innovative", "comparative", "impact", "operational"],
                       help="Prompt profile to use")
    parser.add_argument("--tipo-scuola", help="Filtro tipo scuola (comma-separated)")
    parser.add_argument("--ordine-grado", help="Filtro ordine/grado (comma-separated)")
    parser.add_argument("--provincia", help="Filtro provincia (comma-separated)")
    parser.add_argument("--area-geografica", help="Filtro area geografica (comma-separated)")
    parser.add_argument("--statale-paritaria", help="Filtro statale/paritaria (comma-separated)")
    parser.add_argument("--territorio", help="Filtro territorio (comma-separated)")
    parser.add_argument("--force", "-f", action="store_true",
                       help="Force regeneration even if report exists")
    parser.add_argument("--refine", action="store_true",
                       help="Apply LLM-based refinement after generation")
    parser.add_argument("--count", "-n", type=int, default=5,
                       help="Number of reports for batch command")

    args = parser.parse_args()

    try:
        orchestrator = MetaReportOrchestrator(provider_name=args.provider)
    except Exception as e:
        print(f"Error initializing: {e}")
        sys.exit(1)

    filters = {
        "tipo_scuola": args.tipo_scuola,
        "ordine_grado": args.ordine_grado,
        "regione": args.region,
        "provincia": args.provincia,
        "area_geografica": args.area_geografica,
        "statale_paritaria": args.statale_paritaria,
        "territorio": args.territorio,
    }

    if args.command == "status":
        orchestrator.print_status()

    elif args.command == "school":
        if not args.code:
            print("Error: --code required for school report")
            sys.exit(1)
        result = orchestrator.generate_school(
            args.code,
            force=args.force,
            prompt_profile=args.prompt_profile
        )
        if result:
            print(f"Generated: {result}")
            if args.refine:
                _apply_refine(result, args.provider)
        else:
            print("Failed to generate report")
            sys.exit(1)





    elif args.command == "skeleton":
        # Skeleton-first architecture with dual providers
        if not args.dim:
            print("Error: --dim required for skeleton report")
            sys.exit(1)
        
        from pathlib import Path
        from src.agents.meta_report.skeleton import SkeletonBuilder, load_activities_from_csv
        from src.agents.meta_report.slot_filler import SlotFiller, SlotFillerConfig
        
        # Load activities
        csv_path = PROJECT_ROOT / "data" / "attivita.csv"
        clean_filters = {k: v for k, v in filters.items() if v}
        activities = load_activities_from_csv(csv_path, clean_filters)
        
        if not activities:
            print(f"No activities found with filters: {clean_filters}")
            sys.exit(1)
        
        print(f"[skeleton] Loaded {len(activities)} activities")
        
        # Build skeleton
        builder = SkeletonBuilder(activities, clean_filters, args.dim)
        builder.build_structure()
        builder.compute_cross_links()
        
        print(f"[skeleton] Found {len(builder.schools)} schools, {len(builder.categories)} categories")
        
        # Determine output path - build suffix locally
        import re
        def build_filter_suffix(filters: dict) -> str:
            if not filters:
                return ""
            parts = []
            for key in sorted(filters.keys()):
                values = filters[key]
                if isinstance(values, str):
                    values = [values]
                if not values:
                    continue
                normalized_values = [re.sub(r"\\s+", "-", v.strip()) for v in values]
                value = "+".join(normalized_values)
                slug = re.sub(r"[^a-z0-9+-]+", "-", value.lower()).strip("-")
                parts.append(f"{key}={slug}")
            return f"__{'__'.join(parts)}" if parts else ""
        
        suffix = build_filter_suffix(clean_filters)
        output_dir = PROJECT_ROOT / "reports" / "meta" / "thematic"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        output_path = output_dir / f"{timestamp}__Tema_{args.dim}{suffix}_skeleton.md"
        
        # Configure slot filler
        region = args.region if args.region else "Italia"
        config = SlotFillerConfig(
            provider_school=args.provider_school,
            provider_synthesis=args.provider_synthesis,
            model_school=args.model_school,
            model_synthesis=args.model_synthesis,
            dim=args.dim,
            region=region,
        )
        
        print(f"[skeleton] Provider school: {args.provider_school} ({args.model_school or 'default'})")
        print(f"[skeleton] Provider synthesis: {args.provider_synthesis} ({args.model_synthesis or 'default'})")
        
        # Fill slots
        filler = SlotFiller(builder, config, output_path)
        result = filler.fill_all_slots()
        
        print(f"\nGenerated: {output_path}")
        print(f"Length: {len(result)} chars")



    elif args.command == "next":
        result = orchestrator.generate_next()
        if result:
            report_type, identifier, path = result
            print(f"Generated {report_type}: {identifier or 'national'}")
            print(f"Path: {path}")
        else:
            print("No pending reports")

    elif args.command == "batch":
        results = orchestrator.generate_batch(count=args.count)
        if results:
            print(f"Generated {len(results)} reports:")
            for report_type, identifier, path in results:
                print(f"  - {report_type}: {identifier or 'national'}")
        else:
            print("No reports generated")


if __name__ == "__main__":
    main()
