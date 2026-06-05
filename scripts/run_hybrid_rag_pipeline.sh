#!/usr/bin/env bash
# Pipeline RAG Ibrido Dual-Index: setup + ingestione + test report
# Uso: bash scripts/run_hybrid_rag_pipeline.sh [LIMIT]
# Esempio: bash scripts/run_hybrid_rag_pipeline.sh 5

set -euo pipefail

LIMIT="${1:-}"
LOGDIR="logs/hybrid_rag"
mkdir -p "$LOGDIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colori
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

step() { echo -e "\n${GREEN}═══ STEP $1: $2 ═══${NC}\n"; }
warn() { echo -e "${YELLOW}⚠  $1${NC}"; }
fail() { echo -e "${RED}✗  $1${NC}"; exit 1; }

LIMIT_FLAG=""
if [ -n "$LIMIT" ]; then
    LIMIT_FLAG="--limit $LIMIT"
    warn "Modalità test: LIMIT=$LIMIT scuole"
fi

# ─────────────────────────────────────────────
step 1 "Inizializzazione schema DB (nuove colonne + indici)"
# ─────────────────────────────────────────────
LOG1="$LOGDIR/${TIMESTAMP}_01_db_init.log"
echo "Log: $LOG1"

POSTGRES_PORT=5433 POSTGRES_PASSWORD=ptof_password \
    .venv/bin/python -c "
from src.agents.meta_report.db_manager import DatabaseManager
db = DatabaseManager()
db.init_schema()
print('Schema OK')
" 2>&1 | tee "$LOG1"

echo -e "${GREEN}✓ Schema aggiornato${NC}"

# ─────────────────────────────────────────────
step 2 "Ingestione completa (JSON notes + MD analisi + PTOF raw)"
# ─────────────────────────────────────────────
LOG2="$LOGDIR/${TIMESTAMP}_02_ingest_full.log"
echo "Log: $LOG2"

POSTGRES_PORT=5433 POSTGRES_PASSWORD=ptof_password \
    .venv/bin/python -m src.agents.meta_report.ingestor \
    --include-md --include-raw $LIMIT_FLAG \
    2>&1 | tee "$LOG2"

echo -e "${GREEN}✓ Ingestione completata${NC}"

# ─────────────────────────────────────────────
step 3 "Verifica chunk nel DB per source_type"
# ─────────────────────────────────────────────
LOG3="$LOGDIR/${TIMESTAMP}_03_verify_chunks.log"
echo "Log: $LOG3"

POSTGRES_PORT=5433 POSTGRES_PASSWORD=ptof_password \
    .venv/bin/python -c "
from src.agents.meta_report.db_manager import DatabaseManager
db = DatabaseManager()
with db.get_cursor() as cur:
    cur.execute('''
        SELECT source_type, COUNT(*) as cnt
        FROM narrative_chunks
        GROUP BY source_type
        ORDER BY cnt DESC
    ''')
    rows = cur.fetchall()
    print()
    print('  source_type        | chunk count')
    print('  -------------------|------------')
    for r in rows:
        print(f'  {str(r[0]):20s}| {r[1]}')

    cur.execute('SELECT COUNT(DISTINCT school_code) FROM narrative_chunks')
    total = cur.fetchone()[0]
    print(f'\n  Scuole totali nel DB: {total}')
    print()
" 2>&1 | tee "$LOG3"

echo -e "${GREEN}✓ Verifica completata${NC}"

# ─────────────────────────────────────────────
step 4 "Test ricerca semantica (layer quadro vs evidenza)"
# ─────────────────────────────────────────────
LOG4="$LOGDIR/${TIMESTAMP}_04_search_test.log"
echo "Log: $LOG4"

POSTGRES_PORT=5433 POSTGRES_PASSWORD=ptof_password \
    .venv/bin/python -c "
import logging; logging.basicConfig(level=logging.ERROR)
from src.agents.meta_report.db_manager import DatabaseManager
from sentence_transformers import SentenceTransformer

db = DatabaseManager()
model = SentenceTransformer('all-MiniLM-L6-v2')
emb = model.encode('formazione tutor orientamento').tolist()

print('\n--- LAYER QUADRO (analysis_md + analysis_note) ---')
res = db.search_similar_chunks(emb, source_types=['analysis_md', 'analysis_note'], limit=3)
for r in res:
    print(f'  [{r[\"source_type\"]}] {r[\"school_code\"]} ({r[\"city\"]}): {r[\"content\"][:120]}...')

print('\n--- LAYER EVIDENZA (raw_ptof) ---')
res = db.search_similar_chunks(emb, source_types=['raw_ptof'], limit=3)
for r in res:
    print(f'  [{r[\"source_type\"]}] {r[\"school_code\"]} ({r[\"city\"]}): {r[\"content\"][:120]}...')

print('\n--- ATTIVITA ---')
res = db.search_similar_chunks(emb, topic='activity', limit=3)
for r in res:
    print(f'  {r[\"school_code\"]}: {r[\"content\"][:120]}...')
print()
" 2>&1 | tee "$LOG4"

echo -e "${GREEN}✓ Ricerca OK${NC}"

# ─────────────────────────────────────────────
step 5 "Genera skeleton dry-run (verifica contesti con evidenze)"
# ─────────────────────────────────────────────
LOG5="$LOGDIR/${TIMESTAMP}_05_skeleton_dryrun.log"
echo "Log: $LOG5"

POSTGRES_PORT=5433 POSTGRES_PASSWORD=ptof_password \
    .venv/bin/python -m src.agents.meta_report.synthesis_launcher \
    --ordine-grado "I Grado" --dry-run \
    2>&1 | tee "$LOG5"

echo -e "${GREEN}✓ Skeleton generato${NC}"

# ─────────────────────────────────────────────
echo ""
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo -e "${GREEN}  Pipeline completata!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo ""
echo "Log salvati in: $LOGDIR/"
echo "Per generare il report completo:"
echo "  make report-grado1 PROVIDER=ollama"
echo ""
