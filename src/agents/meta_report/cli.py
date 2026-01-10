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


def main():
    parser = argparse.ArgumentParser(description="Meta Report Generator - Best Practices from PTOF analyses")
    parser.add_argument("command", choices=["status", "school", "regional", "national", "thematic", "next", "batch"],
                       help="Command to execute")
    parser.add_argument("--code", "-c", help="School code for school report")
    parser.add_argument("--region", "-r", help="Region name for regional report")
    parser.add_argument("--dim", "-d", help="Dimension for thematic report")
    parser.add_argument("--provider", "-p", default="auto",
                       choices=["auto", "gemini", "openrouter", "ollama"],
                       help="LLM provider to use")
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
        else:
            print("Failed to generate report")
            sys.exit(1)

    elif args.command == "regional":
        if not args.region:
            print("Error: --region required for regional report")
            sys.exit(1)
        result = orchestrator.generate_regional(
            args.region,
            force=args.force,
            filters=filters,
            prompt_profile=args.prompt_profile
        )
        if result:
            print(f"Generated: {result}")
        else:
            print("Failed to generate report")
            sys.exit(1)

    elif args.command == "national":
        result = orchestrator.generate_national(
            force=args.force,
            filters=filters,
            prompt_profile=args.prompt_profile
        )
        if result:
            print(f"Generated: {result}")
        else:
            print("Failed to generate report")
            sys.exit(1)

    elif args.command == "thematic":
        if not args.dim:
            print("Error: --dim required for thematic report")
            print("Available: metodologie, progetti, inclusione, orientamento, partnership, pcto, openday, universita, visite, exalunni, certificazioni")
            sys.exit(1)
        result = orchestrator.generate_thematic(
            args.dim,
            force=args.force,
            filters=filters,
            prompt_profile=args.prompt_profile
        )
        if result:
            print(f"Generated: {result}")
        else:
            print("Failed to generate report")
            sys.exit(1)

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
