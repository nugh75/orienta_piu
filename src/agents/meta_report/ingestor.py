import argparse
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sentence_transformers import SentenceTransformer

from .db_manager import DatabaseManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
MAX_SEQ_LENGTH = 384
BATCH_SIZE = 32

# Chunking parameters tuned for the embedding model (384 tokens ≈ 1200 chars Italian)
CHUNK_MAX_CHARS = 1200
CHUNK_OVERLAP = 200
CHUNK_MIN_CHARS = 400

# Stub detection
STUB_MARKER = "Report narrativo non disponibile"
MIN_MD_SIZE = 500


class DataIngestor:
    """Ingests PTOF analysis results into PostgreSQL with hybrid RAG support.

    Three source layers:
      - analysis_note: structured notes from JSON ptof_section2 + activities
      - analysis_md:   narrative report MD from analysis_results/
      - raw_ptof:      original PTOF PDF→MD conversion from ptof_md/
    """

    def __init__(
        self,
        data_sources_dir: str = "analysis_results",
        ptof_md_dir: str = "ptof_md",
        csv_path: str = "data/analysis_summary.csv",
    ):
        self.data_sources_dir = Path(data_sources_dir)
        self.ptof_md_dir = Path(ptof_md_dir)
        self.csv_path = Path(csv_path)
        self.db = DatabaseManager()
        self.model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        self.model.max_seq_length = MAX_SEQ_LENGTH

    def run(
        self,
        limit: int = None,
        include_md: bool = False,
        include_raw: bool = False,
        incremental: bool = False,
    ):
        """Runs the ingestion process.

        Args:
            limit: Process at most N schools.
            include_md: Ingest analysis report MD files (layer "quadro").
            include_raw: Ingest raw PTOF MD files (layer "evidenza").
            incremental: Skip schools whose source files haven't changed.
        """
        self.db.init_schema()

        # Load CSV metadata
        logger.info("Loading CSV metadata...")
        if not self.csv_path.exists():
            logger.error(f"CSV not found: {self.csv_path}")
            return

        df = pd.read_csv(self.csv_path)
        schools_processed = 0
        schools_skipped = 0

        json_files = sorted(self.data_sources_dir.glob("*_PTOF_analysis.json"))
        if limit:
            json_files = json_files[:limit]

        logger.info(f"Found {len(json_files)} JSON files to process.")
        sources = ["analysis_note"]
        if include_md:
            sources.append("analysis_md")
        if include_raw:
            sources.append("raw_ptof")
        logger.info(f"Source layers: {sources}")

        for json_file in json_files:
            try:
                school_code = json_file.name.split("_")[0]
                skipped = self._process_school(
                    school_code, json_file, df,
                    include_md=include_md,
                    include_raw=include_raw,
                    incremental=incremental,
                )
                if skipped:
                    schools_skipped += 1
                else:
                    schools_processed += 1
                if (schools_processed + schools_skipped) % 50 == 0:
                    logger.info(
                        f"Progress: {schools_processed} ingested, "
                        f"{schools_skipped} skipped..."
                    )
            except Exception as e:
                logger.error(f"Error processing {json_file.name}: {e}")

        logger.info(
            f"Done. Ingested: {schools_processed}, Skipped: {schools_skipped}"
        )

    # ── Per-school processing ─────────────────────────────────────────

    def _process_school(
        self,
        school_code: str,
        json_path: Path,
        df_metadata: pd.DataFrame,
        include_md: bool,
        include_raw: bool,
        incremental: bool,
    ) -> bool:
        """Process all sources for one school. Returns True if skipped."""
        # Load JSON
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Get CSV metadata
        df_row = df_metadata[df_metadata["school_id"] == school_code]
        if df_row.empty:
            logger.warning(f"Metadata not found in CSV for {school_code}")
            return True

        row = df_row.iloc[0]

        # Upsert school record
        school_data = {
            "code": school_code,
            "region": row.get("regione", "ND"),
            "city": row.get("comune", "ND"),
            "type": row.get("tipo_scuola", "ND"),
            "grade": row.get("ordine_grado", "ND"),
            "s_norm": _safe_float(row.get("score_normativa")),
            "s_terr": _safe_float(row.get("score_territorio")),
            "s_met": _safe_float(row.get("score_metodologie")),
            "s_stru": _safe_float(row.get("score_strumenti")),
            "s_form": _safe_float(row.get("score_formazione")),
            "s_mon": _safe_float(row.get("score_monitoraggio")),
            "meta": _sanitize_text(json.dumps(data.get("metadata", {}))),
        }
        self.db.insert_school(school_data)

        skipped_all = True

        # --- Layer 1: JSON analysis notes + activities ---
        if not self._is_up_to_date(school_code, "analysis_note", json_path, incremental):
            self._ingest_json_notes(school_code, data, str(json_path))
            skipped_all = False

        # --- Layer 2: Analysis report MD (quadro) ---
        if include_md:
            md_path = self.data_sources_dir / f"{school_code}_PTOF_analysis.md"
            if md_path.exists():
                if not self._is_up_to_date(school_code, "analysis_md", md_path, incremental):
                    self._ingest_analysis_md(school_code, md_path)
                    skipped_all = False

        # --- Layer 3: Raw PTOF MD (evidenza/booster) ---
        if include_raw:
            raw_path = self.ptof_md_dir / f"{school_code}_ptof.md"
            if raw_path.exists():
                if not self._is_up_to_date(school_code, "raw_ptof", raw_path, incremental):
                    self._ingest_raw_ptof(school_code, raw_path)
                    skipped_all = False

        return skipped_all

    def _is_up_to_date(
        self, school_code: str, source_type: str, file_path: Path, incremental: bool
    ) -> bool:
        """Check if chunks for this source are already up-to-date."""
        if not incremental:
            return False

        last_ingested = self.db.get_ingestion_timestamp(school_code, source_type)
        if last_ingested is None:
            return False

        file_mtime = datetime.fromtimestamp(
            file_path.stat().st_mtime, tz=timezone.utc
        )
        # Make last_ingested tz-aware if it isn't
        if last_ingested.tzinfo is None:
            last_ingested = last_ingested.replace(tzinfo=timezone.utc)

        return file_mtime <= last_ingested

    # ── Layer 1: JSON notes ───────────────────────────────────────────

    def _ingest_json_notes(self, school_code: str, data: dict, source_file: str):
        """Ingest ptof_section2 notes and activities from JSON."""
        # Delete old chunks first
        self.db.delete_chunks_by_source(school_code, "analysis_note")
        self.db.delete_chunks_by_source(school_code, "activity")

        chunks = []

        # PTOF Section 2 Notes
        section2 = data.get("ptof_section2", {})
        if isinstance(section2, dict):
            for key, val in section2.items():
                if isinstance(val, dict):
                    note = val.get("note")
                    if note and isinstance(note, str) and len(note) > 30:
                        chunks.append(self._make_chunk(
                            school_code, key, note, "analysis_note", source_file
                        ))
                    for subkey, subval in val.items():
                        if isinstance(subval, dict) and "note" in subval:
                            note = subval.get("note")
                            if note and isinstance(note, str) and len(note) > 30:
                                chunks.append(self._make_chunk(
                                    school_code, f"{key}.{subkey}", note,
                                    "analysis_note", source_file
                                ))

        # Activities
        activities = data.get("activities_register", [])
        for act in activities:
            desc = act.get("descrizione_e_metodologia", "")
            title = act.get("titolo_attivita", "")
            full_text = f"TITOLO: {title}\nDESCRIZIONE: {desc}\nTARGET: {act.get('target', '')}"
            if len(full_text) > 50:
                chunks.append(self._make_chunk(
                    school_code, "activity", full_text, "activity", source_file
                ))

        self._embed_and_insert(chunks)

    # ── Layer 2: Analysis report MD ───────────────────────────────────

    def _ingest_analysis_md(self, school_code: str, md_path: Path):
        """Ingest the analysis narrative report MD (layer 'quadro')."""
        text = md_path.read_text(encoding="utf-8")

        # Skip stubs / truncated files
        if len(text) < MIN_MD_SIZE or STUB_MARKER in text:
            return

        self.db.delete_chunks_by_source(school_code, "analysis_md")

        # Split by ### headers (clean structure: Sintesi, Analisi, Forza, Debolezza, Gap, Conclusioni)
        from src.processing.text_chunker import split_by_headers, split_by_size

        sections = split_by_headers(text, min_level=2, max_level=3)
        chunks = []

        for header, content in sections:
            if len(content.strip()) < 50:
                continue
            # Sub-chunk large sections to fit embedding model
            if len(content) > CHUNK_MAX_CHARS:
                sub_chunks = split_by_size(content, CHUNK_MAX_CHARS, CHUNK_OVERLAP)
                for i, sc in enumerate(sub_chunks):
                    if len(sc.strip()) >= CHUNK_MIN_CHARS:
                        chunks.append(self._make_chunk(
                            school_code, f"analysis:{header}:{i}",
                            sc, "analysis_md", str(md_path)
                        ))
            else:
                chunks.append(self._make_chunk(
                    school_code, f"analysis:{header}",
                    content, "analysis_md", str(md_path)
                ))

        self._embed_and_insert(chunks)

    # ── Layer 3: Raw PTOF MD ──────────────────────────────────────────

    def _ingest_raw_ptof(self, school_code: str, raw_path: Path):
        """Ingest the raw PTOF PDF→MD conversion (layer 'evidenza/booster')."""
        text = raw_path.read_text(encoding="utf-8")

        if len(text) < 1000:
            return

        self.db.delete_chunks_by_source(school_code, "raw_ptof")

        # Pre-processing: remove PDF page headers and separators
        cleaned = _clean_raw_ptof(text)

        # Chunk with smart_split tuned for embedding model
        from src.processing.text_chunker import smart_split

        raw_chunks = smart_split(
            cleaned,
            max_chars=CHUNK_MAX_CHARS,
            overlap=CHUNK_OVERLAP,
            min_chunk=CHUNK_MIN_CHARS,
        )

        chunks = []
        for i, chunk_text in enumerate(raw_chunks):
            if len(chunk_text.strip()) >= CHUNK_MIN_CHARS:
                chunks.append(self._make_chunk(
                    school_code, f"raw:{i}",
                    chunk_text, "raw_ptof", str(raw_path)
                ))

        self._embed_and_insert(chunks)

    # ── Helpers ───────────────────────────────────────────────────────

    def _make_chunk(
        self, school_code: str, topic: str, content: str,
        source_type: str, source_file: str,
    ) -> dict:
        return {
            "school_code": school_code,
            "topic": topic,
            "content": _sanitize_text(content),
            "embedding": None,
            "source_type": source_type,
            "source_file": source_file,
        }

    def _embed_and_insert(self, chunks: list[dict]):
        """Generate embeddings in batch and insert into DB."""
        if not chunks:
            return

        texts = [c["content"] for c in chunks]
        embeddings = self.model.encode(texts, batch_size=BATCH_SIZE)
        for i, emb in enumerate(embeddings):
            chunks[i]["embedding"] = emb.tolist()

        self.db.insert_chunks(chunks)


def _safe_float(val, default=0.0) -> float:
    """Safely convert a value to float, handling NaN and None."""
    if val is None:
        return default
    try:
        import math
        f = float(val)
        return default if math.isnan(f) else f
    except (ValueError, TypeError):
        return default


def _sanitize_text(text: str) -> str:
    """Remove NUL (0x00) bytes that PostgreSQL cannot store in TEXT columns.
    
    These often come from PDF-to-MD conversion artifacts.
    """
    if '\x00' in text:
        text = text.replace('\x00', '')
    return text


def _clean_raw_ptof(text: str) -> str:
    """Remove PDF-to-MD noise: page headers, separators, excessive whitespace."""
    # Strip NUL bytes first (PDF conversion artifacts)
    text = _sanitize_text(text)
    # Remove "## Pagina N" headers (page-level noise from PDF conversion)
    text = re.sub(r'^## Pagina \d+\s*$', '', text, flags=re.MULTILINE)
    # Remove horizontal rule separators
    text = re.sub(r'^---+\s*$', '', text, flags=re.MULTILINE)
    # Remove standalone page numbers
    text = re.sub(r'^\s*\d{1,3}\s*$', '', text, flags=re.MULTILINE)
    # Collapse excessive blank lines (>2 → 2)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest PTOF data into PostgreSQL for RAG")
    parser.add_argument("--limit", type=int, help="Limit number of schools to process")
    parser.add_argument("--include-md", action="store_true",
                        help="Ingest analysis report MD files (layer quadro)")
    parser.add_argument("--include-raw", action="store_true",
                        help="Ingest raw PTOF MD files (layer evidenza)")
    parser.add_argument("--incremental", action="store_true",
                        help="Skip schools whose source files haven't changed")
    args = parser.parse_args()

    ingestor = DataIngestor()
    ingestor.run(
        limit=args.limit,
        include_md=args.include_md,
        include_raw=args.include_raw,
        incremental=args.incremental,
    )
