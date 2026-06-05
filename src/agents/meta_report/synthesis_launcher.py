#!/usr/bin/env python3
import sys
print("STARTING LAUNCHER...", flush=True)

import argparse
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from src.agents.meta_report.synthesis_skeleton import SynthesisSkeleton
    from src.agents.meta_report.synthesis_filler import SynthesisFiller
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def build_output_path(base_dir: Path, filters: dict) -> Path:
    """Build the output file path with progressive numbering for same-day reports."""
    output_dir = base_dir / "reports" / "synthesis"
    output_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y%m%d")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    parts = [timestamp, "Sintesi_PTOF"]

    ordine = filters.get("ordine_grado")
    if ordine:
        if isinstance(ordine, list):
            parts.append("_".join(o.replace(" ", "") for o in ordine))
        else:
            parts.append(ordine.replace(" ", ""))

    regione = filters.get("regione")
    if regione:
        parts.append(regione.replace(" ", "_"))

    # Calculate progressive number for today's reports
    import re as _re
    existing = list(output_dir.glob(f"{today}_*__Sintesi_PTOF*.md"))
    # Find max progressive number among existing files
    max_n = 0
    for f in existing:
        m = _re.search(r'_n(\d+)\.md$', f.name)
        if m:
            max_n = max(max_n, int(m.group(1)))
        else:
            # Files without _nX count as n1
            max_n = max(max_n, 1)
    next_n = max_n + 1 if existing else 1

    filename = "__".join(parts) + f"_n{next_n}.md"
    return output_dir / filename


def main() -> int:
    print("INSIDE MAIN")
    try:
        parser = argparse.ArgumentParser(
            description="Genera un report di sintesi narrativa cross-cutting dai PTOF analizzati.",
        )
        parser.add_argument(
            "--ordine-grado",
            nargs="+",
            default=["I Grado", "II Grado"],
            help="Ordine/grado scolastico da filtrare (default: I Grado, II Grado)",
        )
        parser.add_argument(
            "--regione",
            default=None,
            help="Filtra per regione (default: tutte)",
        )
        parser.add_argument(
            "--area-geografica",
            default=None,
            help="Filtra per area geografica (default: tutte)",
        )
        parser.add_argument(
            "--tipo-scuola",
            default=None,
            help="Filtra per tipo scuola (default: tutti)",
        )
        parser.add_argument(
            "--provider",
            default="ollama",
            choices=["ollama", "openrouter", "gemini"],
            help="LLM provider (default: ollama)",
        )
        parser.add_argument(
            "--model",
            default=None,
            help="Modello LLM specifico (default: dal provider)",
        )
        parser.add_argument(
            "--max-samples",
            type=int,
            default=30,
            help="Numero massimo di narrative da campionare (default: 30)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo aggregazione dati, nessuna chiamata LLM",
        )
        parser.add_argument(
            "--no-review",
            action="store_true",
            help="Salta il passaggio di revisione coerenza LLM",
        )
        parser.add_argument(
            "--verbose", "-v",
            action="store_true",
            help="Output di debug dettagliato",
        )

        args = parser.parse_args()
        setup_logging(args.verbose)
        logger = logging.getLogger("generate_synthesis")

        # Build filters
        filters = {}
        if args.ordine_grado:
            filters["ordine_grado"] = args.ordine_grado if len(args.ordine_grado) > 1 else args.ordine_grado[0]
        if args.regione:
            filters["regione"] = args.regione
        if args.area_geografica:
            filters["area_geografica"] = args.area_geografica
        if args.tipo_scuola:
            filters["tipo_scuola"] = args.tipo_scuola

        logger.info("Filtri: %s", filters)

        # ── Step 1: Build skeleton ───────────────────────────────────────────
        logger.info("=== Fase 1: Caricamento dati e costruzione skeleton ===")

        skeleton = SynthesisSkeleton(
            base_dir=PROJECT_ROOT,
            filters=filters,
            max_narrative_samples=args.max_samples,
        )
        skeleton.load_data()

        if skeleton.stats.get("n_schools", 0) == 0:
            logger.error("Nessuna scuola trovata con i filtri specificati.")
            return 1

        skeleton_text = skeleton.generate_skeleton()
        logger.info(
            "Skeleton generato: %d scuole, %d narrative campionate, %d caratteri",
            skeleton.stats["n_schools"],
            len(skeleton.narratives),
            len(skeleton_text),
        )

        # Print stats summary
        stats = skeleton.stats
        print(f"\n{'='*60}")
        print(f"  REPORT DI SINTESI PTOF — Preparazione Dati")
        print(f"{'='*60}")
        print(f"  Scuole nel campione:    {stats['n_schools']}")
        print(f"  Narrative campionate:   {len(skeleton.narratives)}")
        
        # ── Dry-run: save skeleton only ──────────────────────────────────────
        output_path = build_output_path(PROJECT_ROOT, filters)

        if args.dry_run:
            output_path = output_path.with_name(
                output_path.stem + "__SKELETON" + output_path.suffix
            )
            output_path.write_text(skeleton_text, encoding="utf-8")
            logger.info("Dry-run: skeleton salvato in %s", output_path)
            print(f"  Skeleton salvato: {output_path}")
            return 0

        # ── Step 2: Fill slots with LLM ────────────────────────────────────
        logger.info("=== Fase 2: Generazione narrativa con LLM ===")
        
        filler = SynthesisFiller(
            skeleton=skeleton,
            provider_name=args.provider,
            model=args.model,
        )
        
        final_text = filler.fill_all_slots(skeleton_text)

        # ── Step 2b: Coherence Review ────────────────────────────────────
        if not args.no_review:
            logger.info("=== Fase 2b: Revisione coerenza con LLM ===")
            print(f"\n  🔍 Revisione coerenza in corso...")
            
            try:
                final_text = filler.coherence_review(final_text)
                logger.info("Revisione coerenza completata: %d caratteri", len(final_text))
                print(f"  ✅ Revisione coerenza completata")
            except Exception as e:
                logger.warning("Revisione coerenza fallita (report originale conservato): %s", e)
                print(f"  ⚠️  Revisione coerenza saltata: {e}")
        else:
            logger.info("Revisione coerenza saltata (--no-review)")
            print(f"\n  ⏭️  Revisione coerenza saltata (--no-review)")

        # ── Inject provider/model metadata into markdown ─────────────────
        provider_name = filler.provider.name
        model_name = getattr(filler.provider, "model", "default")
        model_info_line = f"\n*Generato con: {provider_name} / {model_name}*\n"
        # Insert after the *Target Analisi: ...* line (or after the first heading)
        import re as _re
        _target_re = _re.compile(r'(\*Target\s+Analisi:[^\n]*\*)', _re.MULTILINE)
        if _target_re.search(final_text):
            final_text = _target_re.sub(r'\1' + model_info_line, final_text, count=1)
        else:
            # Fallback: insert after first heading
            _heading_re = _re.compile(r'^(#\s+.+)$', _re.MULTILINE)
            if _heading_re.search(final_text):
                final_text = _heading_re.sub(r'\1' + model_info_line, final_text, count=1)

        logger.info("Report completato: %d caratteri (provider=%s, model=%s)",
                     len(final_text), provider_name, model_name)
        
        # Save final report
        output_path.write_text(final_text, encoding="utf-8")
        logger.info("Report salvato in %s", output_path)
        print(f"  Report salvato: {output_path}")
        
        # ── Step 3: Convert to PDF ───────────────────────────────────────
        try:
            from src.utils.pdf_converter import convert_markdown_to_pdf
            pdf_path = output_path.with_suffix(".pdf")
            result, msg = convert_markdown_to_pdf(str(output_path), str(pdf_path))
            if result:
                logger.info("PDF generato: %s", result)
                print(f"  PDF generato: {result}")
            else:
                logger.warning("PDF conversion failed: %s", msg)
        except Exception as e:
            logger.warning("Could not convert to PDF: %s", e)
        
        return 0
    except Exception as e:
        print(f"CRASH IN MAIN: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"CRASH: {e}")
        import traceback
        traceback.print_exc()
