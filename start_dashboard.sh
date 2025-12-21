#!/bin/bash

# Script di avvio Dashboard PTOF
# Autore: Sistema di Analisi PTOF
# Data: 2025-12-21

echo "🚀 Avvio Dashboard Analisi PTOF..."
echo ""

# Verifica dipendenze
echo "🔍 Verifica dipendenze..."
python3 -c "import streamlit; import plotly; import pandas" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Errore: Dipendenze mancanti!"
    echo "   Esegui: pip install streamlit plotly pandas"
    exit 1
fi
echo "✅ Dipendenze OK"

# Verifica file dati
if [ ! -f "data/analysis_summary.csv" ]; then
    echo "⚠️  File data/analysis_summary.csv non trovato"
    echo "   Generazione indice in corso..."
    python3 -c "from src.data.data_manager import update_index_safe; update_index_safe()"
fi

# Avvia Streamlit
echo ""
echo "✅ Avvio dashboard su http://localhost:8501"
echo ""
echo "📌 Premi CTRL+C per terminare"
echo "================================================"
echo ""

streamlit run app/Home.py
