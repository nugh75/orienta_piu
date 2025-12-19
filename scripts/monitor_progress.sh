#!/bin/bash

# Check if ptof directory exists
if [ ! -d "ptof" ]; then
    echo "Directory 'ptof' does not exist yet."
    exit 1
fi

while true; do
    clear
    echo "========================================"
    echo "      PTOF DOWNLOAD MONITOR (REAL-TIME)"
    echo "========================================"
    echo ""
    
    # Count PDF files
    count=$(find ptof -maxdepth 1 -name "*.pdf" | wc -l)
    echo "📄 Total PDFs Downloaded: $count"
    echo ""
    
    echo "----------------------------------------"
    echo "🕒 Latest 5 Downloads:"
    
    # List latest 5 files, showing time and name
    # ls -lt sorts by time (newest first)
    ls -lt ptof/*.pdf | head -n 5 | awk '{print $6, $7, $8, $9}'
    
    echo "----------------------------------------"
    echo "Press [CTRL+C] to stop monitoring."
    
    sleep 2
done
