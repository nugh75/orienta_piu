import os
import logging
from contextlib import contextmanager

import psycopg2
from pgvector.psycopg2 import register_vector
from psycopg2.extensions import connection as PgConnection
from psycopg2.extras import DictCursor

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages connection to the PostgreSQL + pgvector database."""

    def __init__(self):
        self.host = os.getenv("POSTGRES_HOST", "localhost")
        self.port = os.getenv("POSTGRES_PORT", "5432")
        self.user = os.getenv("POSTGRES_USER", "ptof_user")
        self.password = os.getenv("POSTGRES_PASSWORD", "ptof_password")
        self.dbname = os.getenv("POSTGRES_DB", "ptof_data")
        
        # When running inside docker, hostname might be 'db'
        if os.path.exists("/.dockerenv"):
             self.host = "db"

    def get_connection_url(self) -> str:
        """Returns SQLAlchemy-compatible connection URL."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.dbname}"

    @contextmanager
    def get_cursor(self, autocommit: bool = False):
        """Yields a database cursor with automatic cleanup."""
        conn = None
        try:
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                dbname=self.dbname,
                connect_timeout=5
            )
            if autocommit:
                conn.autocommit = True
                
            # Enable pgvector extension support for this connection
            # We wrap this in a try-except to handle cases where the extension isn't installed yet
            try:
                register_vector(conn)
            except Exception as e:
                logger.debug("Could not register vector extension on connection (might not be installed yet): %s", e)

            with conn.cursor(cursor_factory=DictCursor) as cur:
                yield cur
                if not autocommit:
                    conn.commit()
        except Exception as e:
            if conn and not autocommit:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def init_schema(self) -> None:
        """Initializes the database schema."""
        logger.info("Initializing database schema...")
        
        with self.get_cursor(autocommit=True) as cur:
            # 1. Enable pgvector extension
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            logger.info("Extension 'vector' enabled.")

            # 2. Create schools table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS schools (
                    school_code VARCHAR(20) PRIMARY KEY,
                    region VARCHAR(50),
                    city VARCHAR(100),
                    school_type VARCHAR(100),
                    grade_level VARCHAR(50), -- 'I Grado', 'II Grado', etc.
                    cluster_id INTEGER,
                    archetype_label VARCHAR(100),
                    
                    -- Dimensons Scores
                    score_normativa FLOAT,
                    score_territorio FLOAT,
                    score_metodologie FLOAT,
                    score_strumenti FLOAT,
                    score_formazione FLOAT,
                    score_monitoraggio FLOAT,
                    
                    metadata JSONB
                );
            """)
            
            # 3. Create content chunks table for RAG
            # We use 384 dimensions for all-MiniLM-L6-v2 which is a good standard
            cur.execute("""
                CREATE TABLE IF NOT EXISTS narrative_chunks (
                    id SERIAL PRIMARY KEY,
                    school_code VARCHAR(20) REFERENCES schools(school_code),
                    section_topic VARCHAR(255), -- e.g. 'metodologie', 'territorio'
                    content TEXT,
                    embedding vector(384),
                    source_type VARCHAR(20) DEFAULT 'legacy',
                    source_file VARCHAR(255),
                    ingested_at TIMESTAMP DEFAULT NOW()
                );
            """)

            # 3b. Add columns to existing tables (safe migration for existing DBs)
            for col, typedef in [
                ("source_type", "VARCHAR(20) DEFAULT 'legacy'"),
                ("source_file", "VARCHAR(255)"),
                ("ingested_at", "TIMESTAMP DEFAULT NOW()"),
            ]:
                try:
                    cur.execute(f"ALTER TABLE narrative_chunks ADD COLUMN IF NOT EXISTS {col} {typedef};")
                except Exception:
                    pass  # Column already exists

            # 4. Create indexes
            # Partial indexes by source_type for efficient filtered retrieval
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_chunks_source_type
                ON narrative_chunks (source_type);
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_chunks_school_source
                ON narrative_chunks (school_code, source_type);
            """)

            # IVFFlat vector index — requires data to exist; safe to create, will be used if data present
            try:
                cur.execute("""
                    SELECT COUNT(*) FROM narrative_chunks;
                """)
                count = cur.fetchone()[0]
                if count >= 100:
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_chunks_embedding_ivfflat
                        ON narrative_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
                    """)
                    logger.info(f"IVFFlat index created/verified ({count} chunks).")
            except Exception as e:
                logger.debug(f"IVFFlat index skipped: {e}")

            logger.info("Schema initialized successfully.")

    def insert_school(self, data: dict) -> None:
        """Upsert a school record."""
        with self.get_cursor() as cur:
            cur.execute("""
                INSERT INTO schools (
                    school_code, region, city, school_type, grade_level,
                    score_normativa, score_territorio, score_metodologie,
                    score_strumenti, score_formazione, score_monitoraggio,
                    metadata
                ) VALUES (
                    %(code)s, %(region)s, %(city)s, %(type)s, %(grade)s,
                    %(s_norm)s, %(s_terr)s, %(s_met)s,
                    %(s_stru)s, %(s_form)s, %(s_mon)s,
                    %(meta)s
                )
                ON CONFLICT (school_code) DO UPDATE SET
                    region = EXCLUDED.region,
                    city = EXCLUDED.city,
                    school_type = EXCLUDED.school_type,
                    grade_level = EXCLUDED.grade_level,
                    score_normativa = EXCLUDED.score_normativa,
                    score_territorio = EXCLUDED.score_territorio,
                    score_metodologie = EXCLUDED.score_metodologie,
                    score_strumenti = EXCLUDED.score_strumenti,
                    score_formazione = EXCLUDED.score_formazione,
                    score_monitoraggio = EXCLUDED.score_monitoraggio,
                    metadata = EXCLUDED.metadata;
            """, data)

    def insert_chunks(self, chunks: list[dict]) -> None:
        """Bulk insert narrative chunks with source tracking."""
        if not chunks:
            return

        with self.get_cursor() as cur:
            args_list = [
                (
                    c['school_code'],
                    c['topic'],
                    c['content'],
                    c['embedding'],
                    c.get('source_type', 'legacy'),
                    c.get('source_file'),
                )
                for c in chunks
            ]

            cur.executemany("""
                INSERT INTO narrative_chunks
                    (school_code, section_topic, content, embedding, source_type, source_file)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, args_list)

    def delete_chunks_by_source(self, school_code: str, source_type: str) -> int:
        """Delete all chunks for a school+source_type. Returns count deleted."""
        with self.get_cursor() as cur:
            cur.execute(
                "DELETE FROM narrative_chunks WHERE school_code = %s AND source_type = %s",
                (school_code, source_type),
            )
            return cur.rowcount

    def get_ingestion_timestamp(self, school_code: str, source_type: str):
        """Get the latest ingestion timestamp for a school+source_type."""
        try:
            with self.get_cursor() as cur:
                cur.execute(
                    "SELECT MAX(ingested_at) FROM narrative_chunks WHERE school_code = %s AND source_type = %s",
                    (school_code, source_type),
                )
                row = cur.fetchone()
                return row[0] if row else None
        except Exception:
            return None

    def search_similar_chunks(self, query_embedding: list[float], topic: str = None, grade_level: str = None, school_codes: list[str] = None, source_types: list[str] = None, limit: int = 50) -> list[dict]:
        """Search for semantic neighbors with optional source_type filtering."""
        with self.get_cursor() as cur:
            query = """
                SELECT
                    n.content,
                    n.school_code,
                    s.region,
                    s.city,
                    s.school_type,
                    n.section_topic,
                    n.source_type,
                    (n.embedding <=> %s::vector) as distance
                FROM narrative_chunks n
                JOIN schools s ON n.school_code = s.school_code
                WHERE 1=1
            """
            params = [query_embedding]

            if topic:
                query += " AND n.section_topic = %s"
                params.append(topic)

            if grade_level:
                query += " AND s.grade_level ILIKE %s"
                params.append(f"%{grade_level}%")

            if school_codes:
                query += " AND n.school_code = ANY(%s)"
                params.append(school_codes)

            if source_types:
                query += " AND n.source_type = ANY(%s)"
                params.append(source_types)

            query += """
                ORDER BY distance ASC
                LIMIT %s;
            """
            params.append(limit)

            cur.execute(query, tuple(params))
            results = cur.fetchall()
            return [dict(row) for row in results]

    def get_all_school_embeddings(self) -> list[dict]:
        """Retrieves all embeddings grouped by school to compute cluster centers.
        
        Returns:
            List of dicts with keys: school_code, topic, embedding (as list of floats)
        """
        try:
            with self.get_cursor() as cur:
                # Cast to text to avoid proprietary binary format if adapter not set
                # But pgvector adapter usually handles it. Let's try explicit cast to be safe or rely on adapter.
                # Given I don't see adapter registration in snippet, I'll assume list format or string.
                # Actually, earlier I saw `import psycopg2` but not `pgvector`.
                # Let's just fetch. If it returns string, we parse it.
                query = """
                    SELECT school_code, section_topic, embedding
                    FROM narrative_chunks
                    WHERE embedding IS NOT NULL;
                """
                cur.execute(query)
                rows = cur.fetchall()
                
                results = []
                for row in rows:
                    emb = row[2]
                    # basic parsing if string
                    if isinstance(emb, str):
                        emb = [float(x) for x in emb.strip('[]').split(',')]
                        
                    results.append({
                        "school_code": row[0],
                        "topic": row[1],
                        "embedding": emb
                    })
                return results
        except Exception as e:
            logger.error(f"Error retrieving all embeddings: {e}")
            return []
