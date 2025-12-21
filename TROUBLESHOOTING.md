# Troubleshooting Dashboard Streamlit

## Diagnosi Rapida

### Test Automatico

Esegui il test completo per verificare lo stato del sistema:

```bash
python3 << 'EOF'
import sys, os, pandas as pd

print("🔍 TEST DASHBOARD STREAMLIT\n")

# Test 1: Moduli
modules = ['streamlit', 'plotly', 'pandas', 'numpy']
print("1. Moduli Python:")
for mod in modules:
    try:
        __import__(mod)
        print(f"   ✅ {mod}")
    except:
        print(f"   ❌ {mod} - INSTALLA CON: pip install {mod}")

# Test 2: File
print("\n2. File Essenziali:")
files = ['data/analysis_summary.csv', 'app/Home.py', 'app/data_utils.py']
for f in files:
    print(f"   {'✅' if os.path.exists(f) else '❌'} {f}")

# Test 3: Dati
print("\n3. Dati CSV:")
try:
    df = pd.read_csv('data/analysis_summary.csv')
    print(f"   ✅ {len(df)} scuole, {len(df.columns)} colonne")
except Exception as e:
    print(f"   ❌ {e}")

print("\n" + "="*50)
EOF
```

---

## Problemi Comuni

### 1. ImportError: No module named 'streamlit'

**Soluzione:**
```bash
pip install streamlit plotly pandas numpy
```

### 2. FileNotFoundError: data/analysis_summary.csv

**Causa:** CSV non generato o eliminato

**Soluzione:**
```bash
python3 -c "from src.data.data_manager import update_index_safe; update_index_safe()"
```

### 3. Dashboard si avvia ma mostra "Nessun dato disponibile"

**Causa:** CSV vuoto o filtri troppo restrittivi

**Soluzioni:**
1. Verifica il CSV:
```bash
wc -l data/analysis_summary.csv  # Dovrebbe mostrare > 1 riga
head -5 data/analysis_summary.csv  # Mostra prime righe
```

2. Rimuovi i filtri dalla sidebar (pulsante "🗑️ Rimuovi Filtri")

3. Rigenera l'indice:
```bash
python3 -c "from src.data.data_manager import update_index_safe; update_index_safe()"
streamlit cache clear
```

### 4. Port 8501 already in use

**Causa:** Altra istanza di Streamlit in esecuzione

**Soluzioni:**

Opzione A - Cambia porta:
```bash
streamlit run app/Home.py --server.port=8502
```

Opzione B - Termina processo esistente:
```bash
# macOS/Linux
lsof -ti:8501 | xargs kill -9

# Oppure trova e termina manualmente
ps aux | grep streamlit
kill <PID>
```

### 5. ModuleNotFoundError: No module named 'app.data_utils'

**Causa:** Path Python non include la directory del progetto

**Soluzione:**
```bash
# Assicurati di essere nella directory root del progetto
cd /path/to/LIste
streamlit run app/Home.py
```

### 6. Errori di import circolari

**Soluzione:**
Riavvia Streamlit e pulisci la cache:
```bash
streamlit cache clear
streamlit run app/Home.py
```

### 7. ValueError: could not convert string to float

**Causa:** Dati 'ND' o non numerici nelle colonne numeriche

**Soluzione:** Il codice già gestisce questo con `pd.to_numeric(..., errors='coerce')`, ma se persiste:

```bash
# Verifica il CSV
python3 -c "
import pandas as pd
df = pd.read_csv('data/analysis_summary.csv')
print(df['ptof_orientamento_maturity_index'].value_counts(dropna=False))
"
```

Se ci sono valori strani, rigenera:
```bash
python3 -c "from src.data.data_manager import update_index_safe; update_index_safe()"
```

### 8. Dashboard lenta o non risponde

**Soluzioni:**

1. Installa Watchdog per file watching ottimizzato:
```bash
pip install watchdog
```

2. Disabilita auto-update nel codice (già fatto, verificare comunque)

3. Riduci i dati visualizzati con i filtri

4. Riavvia con modalità development disabilitata:
```bash
streamlit run app/Home.py --server.runOnSave=false
```

### 9. Grafici Plotly non si visualizzano

**Causa:** Versione Plotly incompatibile o browser cache

**Soluzioni:**

1. Aggiorna Plotly:
```bash
pip install --upgrade plotly
```

2. Pulisci cache browser (CTRL+SHIFT+R)

3. Verifica versione:
```bash
python -c "import plotly; print(plotly.__version__)"  # Dovrebbe essere >= 5.0
```

### 10. Errore: "Session state has no attribute..."

**Causa:** Session state non inizializzato correttamente

**Soluzione:**
Ricarica la pagina (CTRL+R) o riavvia Streamlit

---

## Comandi Utili di Debug

### Verifica Ambiente
```bash
# Versioni installate
python --version
pip list | grep streamlit
pip list | grep plotly

# Path Python
python -c "import sys; print('\n'.join(sys.path))"
```

### Verifica File
```bash
# Dimensione CSV
ls -lh data/analysis_summary.csv

# Prime righe
head -10 data/analysis_summary.csv

# Conta colonne
head -1 data/analysis_summary.csv | tr ',' '\n' | wc -l
```

### Log di Debug
```bash
# Avvia con log dettagliati
streamlit run app/Home.py --logger.level=debug --server.fileWatcherType=none
```

### Pulizia Cache
```bash
# Pulisci cache Streamlit
rm -rf ~/.streamlit/cache

# O dal codice
python -c "import streamlit; streamlit.cache_data.clear()"
```

---

## Verifica Integrità Sistema

Script completo di verifica:

```bash
python3 << 'VERIFY'
#!/usr/bin/env python3
import os, sys, pandas as pd, json

def check_system():
    issues = []

    # 1. Verifica moduli
    for mod in ['streamlit', 'plotly', 'pandas', 'numpy']:
        try:
            __import__(mod)
        except ImportError:
            issues.append(f"Modulo mancante: {mod}")

    # 2. Verifica file
    required_files = [
        'app/Home.py',
        'app/data_utils.py',
        'src/data/data_manager.py',
        'data/analysis_summary.csv'
    ]
    for f in required_files:
        if not os.path.exists(f):
            issues.append(f"File mancante: {f}")

    # 3. Verifica CSV
    try:
        df = pd.read_csv('data/analysis_summary.csv')
        if len(df) == 0:
            issues.append("CSV vuoto")

        required_cols = ['school_id', 'denominazione', 'ptof_orientamento_maturity_index']
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            issues.append(f"Colonne CSV mancanti: {missing}")

    except Exception as e:
        issues.append(f"Errore CSV: {e}")

    # 4. Verifica JSON
    json_files = [f for f in os.listdir('analysis_results') if f.endswith('.json')]
    if len(json_files) == 0:
        issues.append("Nessun file JSON di analisi trovato")

    # Report
    print("="*60)
    print("REPORT INTEGRITÀ SISTEMA")
    print("="*60)

    if not issues:
        print("\n✅ SISTEMA OK - Nessun problema rilevato\n")
        print("Per avviare la dashboard:")
        print("  ./start_dashboard.sh")
        print("  oppure: streamlit run app/Home.py")
    else:
        print(f"\n❌ PROBLEMI RILEVATI ({len(issues)}):\n")
        for i, issue in enumerate(issues, 1):
            print(f"{i}. {issue}")
        print("\nSegui le soluzioni in TROUBLESHOOTING.md")

    print("="*60)

check_system()
VERIFY
```

---

## Contatti e Supporto

Se i problemi persistono:

1. Verifica di avere l'ultima versione del codice
2. Controlla i log in `logs/workflow_ptof.log`
3. Consulta [DASHBOARD_README.md](DASHBOARD_README.md) per dettagli sulla dashboard
4. Esegui lo script di verifica integrità sopra riportato

---

**Ultimo aggiornamento:** 2025-12-21
**Versione Dashboard:** 1.0 (Streamlit 1.44.1)
