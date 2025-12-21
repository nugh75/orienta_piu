#!/usr/bin/env python3
import sys
import logging
import signal
from src.processing.bg_fixer import BackgroundFixer

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/background_debug.log"),
        # Use stdout handler to ensure user sees logs mixed with printing
        logging.StreamHandler(sys.stdout)
    ]
)
# Silence verbose request logs
logging.getLogger("urllib3").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

stop_requested = False

def signal_handler(sig, frame):
    global stop_requested
    if stop_requested:
        print("\n💀 Chiusura forzata!")
        sys.exit(1)
    
    print("\n🛑 Interruzione richiesta (Ctrl+C). Attendo fine operazione corrente...")
    stop_requested = True

def check_stop():
    return stop_requested

def main():
    signal.signal(signal.SIGINT, signal_handler)
    
    logger.info("🚀 Avvio Fixer CLI Interattivo")
    
    try:
        fixer = BackgroundFixer()
        flags = fixer.load_flags()
        
        if not flags:
            logger.info("✅ Nessuna anomalia pendente trovata.")
            return

        print(f"\n📋 PIANO DI CORREZIONE: {len(flags)} file con anomalie")
        print("-" * 60)
        for i, f in enumerate(flags):
            issues = len(f.get('flags', []))
            print(f"  [{i+1}] {f['file']} ({issues} issue{'s' if issues!=1 else ''})")
        print("-" * 60)
            
        print("\nOpzioni:")
        print("  [invio] -> Correggi TUTTO")
        print("  '1,3'   -> Correggi solo i file indicati (es. 1 e 3)")
        print("  'q'     -> Esci senza fare nulla")
        
        try:
            choice = input("\nScelta > ").strip().lower()
        except EOFError:
            return
        except KeyboardInterrupt:
            return
        
        if choice == 'q':
            logger.info("Operazione annullata dall'utente.")
            return
            
        target_files = None
        if choice and choice != 'all':
            try:
                indices = [int(x.strip()) - 1 for x in choice.split(',') if x.strip()]
                target_files = []
                for idx in indices:
                    if 0 <= idx < len(flags):
                        target_files.append(flags[idx]['file'])
                
                if not target_files:
                    logger.warning("⚠️ Nessun file valido selezionato.")
                    return
                logger.info(f"Selezionati {len(target_files)} file specifici.")
            except ValueError:
                logger.error("❌ Input non valido (usa numeri separati da virgola).")
                return

        # Run remediation
        def log_status(msg):
            # Avoid duplicating logs if they are already handled by logger in bg_fixer
            # But run_batch_fix mostly uses status_callback for user-facing progress
            logger.info(msg)
            
        fixer.run_batch_fix(
            status_callback=log_status,
            stop_check_callback=check_stop,
            target_files=target_files
        )
        
    except Exception as e:
        logger.error(f"Errore critico: {e}", exc_info=True)

if __name__ == "__main__":
    main()
