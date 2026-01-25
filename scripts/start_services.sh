#!/bin/bash
# Script di avvio per Docker container
# Avvia sia Streamlit che il Task Runner Flask

set -e

echo "🚀 Avvio servizi ORIENTA+..."

# Avvia Task Runner Flask in background sulla porta 5001
echo "   📡 Task Runner su porta 5001"
# Avvia Task Runner Flask in background sulla porta 5000 (con kill preventivo)
echo "   📡 Task Runner su porta 5000"
python scripts/run_app.py --port 5000 &
TASKRUNNER_PID=$!

# Attendi che il Task Runner sia pronto
sleep 2
if ! kill -0 $TASKRUNNER_PID 2>/dev/null; then
    echo "❌ Task Runner non avviato correttamente"
    exit 1
fi
echo "   ✅ Task Runner avviato (PID: $TASKRUNNER_PID)"

# Avvia Streamlit in foreground
echo "   🌐 Streamlit Dashboard su porta 8587"
exec streamlit run app/Home.py \
    --server.port=8587 \
    --server.address=0.0.0.0 \
    --server.baseUrlPath="" \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false
