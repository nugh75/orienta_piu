#!/usr/bin/env python3
import sys
import logging
import signal
from src.processing.bg_reviewer import BackgroundReviewer

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/background_debug.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

stop_requested = False

def signal_handler(sig, frame):
    global stop_requested
    if stop_requested:
        logger.info("💀 Chiusura forzata! Uscita immediata.")
        sys.exit(1)
    
    logger.info("🛑 Interruzione richiesta (Ctrl+C). Attendo fine operazione corrente...")
    stop_requested = True

def check_stop():
    return stop_requested

def main():
    signal.signal(signal.SIGINT, signal_handler)
    
    logger.info("🚀 Avvio Rilevamento Anomalie (Reviewer CLI)")
    logger.info("Usa Ctrl+C per fermare il processo.")
    
    try:
        reviewer = BackgroundReviewer()
        
        def log_status(msg):
            logger.info(msg)
            
        count = reviewer.run_batch_review(
            status_callback=log_status,
            stop_check_callback=check_stop
        )
        
        logger.info(f"Processo terminato. File segnati con anomalie: {count}")
        
    except Exception as e:
        logger.error(f"Errore critico: {e}", exc_info=True)

if __name__ == "__main__":
    main()
