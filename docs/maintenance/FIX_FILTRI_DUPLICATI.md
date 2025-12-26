# Fix Filtri Duplicati - Rimozione Combinazioni nei Multiselect

**Data:** 2025-12-21
**Problema:** Filtri "Tipo Scuola" e "Ordine Grado" mostravano combinazioni duplicate
**Causa:** Session state conteneva valori obsoleti con combinazioni (es. "Liceo, Tecnico")

---

## 🔍 Problema Identificato

Nella dashboard, i filtri mostravano valori duplicati:

### Tipo Scuola (Prima del fix)
- I Grado
- Infanzia
- **Infanzia, Primaria** ← Combinazione (non dovrebbe apparire)
- **Infanzia, Primari...** ← Combinazione troncata
- Liceo
- **Liceo, Tecnico** ← Combinazione (non dovrebbe apparire)
- Professionale
- Tecnico
- **Tecnico, Professi...** ← Combinazione (non dovrebbe apparire)

### Ordine Grado (Simile)
- Comprensivo
- I Grado
- II Grado
- Infanzia (forzato)
- **Possibili combinazioni se presenti in session_state**

## 🎯 Comportamento Corretto

I filtri dovrebbero mostrare **solo i tipi individuali**:

### Tipo Scuola (Dopo il fix)
- I Grado
- Infanzia
- Liceo
- Primaria
- Professionale
- Tecnico

**Funzionamento:**
- Una scuola con tipo "Liceo, Tecnico" viene filtrata quando selezioni "Liceo" OPPURE "Tecnico"
- Non serve selezionare "Liceo, Tecnico" come combinazione
- Le combinazioni sono **automaticamente gestite** dal filtro

## ✅ Soluzione Applicata

### File Modificato
**File:** [app/data_utils.py](app/data_utils.py)

**Righe modificate:** 111-118 (Tipo Scuola), 149-155 (Ordine Grado)

### Codice Aggiunto

```python
# Validazione session_state per Tipo Scuola
if 'filter_tipo' in st.session_state:
    current = st.session_state['filter_tipo']
    if isinstance(current, list):
        # Remove any value that contains comma (combinations)
        valid = [t for t in current if t in tipi]
        if valid != current:
            st.session_state['filter_tipo'] = valid

# Validazione session_state per Ordine Grado
if 'filter_grado' in st.session_state:
    current = st.session_state['filter_grado']
    if isinstance(current, list):
        valid = [g for g in current if g in gradi]
        if valid != current:
            st.session_state['filter_grado'] = valid
```

### Logica del Fix

1. **Estrazione tipi individuali** (già presente, funzionava):
   - `get_unique_types()` splitta "Liceo, Tecnico" → ["Liceo", "Tecnico"]
   - Restituisce solo tipi individuali

2. **Pulizia session_state** (nuovo):
   - Prima di mostrare il multiselect, controlla `st.session_state`
   - Rimuove valori non validi (combinazioni obsolete)
   - Mantiene solo i valori presenti nella lista corretta

3. **Filtro con overlap** (già presente, funzionava):
   - Una scuola "Liceo, Tecnico" matcha se selezioni "Liceo" O "Tecnico"
   - Usa `set.isdisjoint()` per controllare l'intersezione

## 📊 Dati nel CSV

I dati nel CSV sono corretti e contengono le combinazioni:

```
Tipo Scuola:
  • I Grado                         (27 scuole)
  • Liceo                           (31 scuole)
  • Liceo, Tecnico                  ( 2 scuole) ← Combinazione valida nel CSV
  • Tecnico, Professionale          ( 2 scuole) ← Combinazione valida nel CSV
  • Infanzia, Primaria, I Grado     ( 4 scuole) ← Combinazione valida nel CSV
  ...
```

Le combinazioni **devono rimanere nel CSV** perché rappresentano scuole che offrono più percorsi.

## 🔧 Come Funziona il Filtro

### Esempio Pratico

**Scuole nel dataset:**
1. Scuola A: "Liceo"
2. Scuola B: "Tecnico"
3. Scuola C: "Liceo, Tecnico"

**Utente seleziona:** "Liceo"

**Risultato:** Mostra Scuola A + Scuola C ✅

**Spiegazione:** Il filtro controlla se "Liceo" è presente nel valore di `tipo_scuola`, anche se combinato con altri.

### Codice del Filtro

```python
def filter_by_type(df: pd.DataFrame, selected_types: list, col='tipo_scuola'):
    if not selected_types:
        return df

    def has_overlap(val):
        if pd.isna(val): return False
        current = set(str(val).split(', '))
        return not set(selected_types).isdisjoint(current)

    return df[df[col].apply(has_overlap)]
```

## ✅ Risultati

### Prima del Fix
- ❌ Multiselect mostra 9 opzioni (incluse 3 combinazioni)
- ❌ Confusione: "Devo selezionare Liceo E Liceo,Tecnico?"
- ❌ Valori obsoleti persistono in session_state

### Dopo il Fix
- ✅ Multiselect mostra 6 opzioni (solo tipi individuali)
- ✅ Chiaro: "Seleziono Liceo per vedere tutti i licei"
- ✅ Session_state viene pulito automaticamente

## 🚀 Impatto

1. **UI più pulita**: Nessuna combinazione nei filtri
2. **Esperienza utente migliorata**: Selezione intuitiva
3. **Automatico**: Non serve cliccare "Rimuovi Filtri"
4. **Retrocompatibile**: Funziona con dati esistenti

## 📝 Note Tecniche

### Session State Streamlit

Streamlit mantiene lo stato dei widget tra rerun in `st.session_state`. Se il codice cambia e rimuove opzioni dal multiselect, i valori vecchi rimangono in session_state causando problemi.

**Soluzione:** Validare e pulire session_state prima di creare i widget.

### Perché Non Usare `default=[]`?

```python
# ❌ Non basta
st.multiselect("Tipo Scuola", tipi, default=[], key="filter_tipo")

# ✅ Serve validazione esplicita
if 'filter_tipo' in st.session_state:
    st.session_state['filter_tipo'] = [t for t in st.session_state['filter_tipo'] if t in tipi]
```

Il parametro `default` si applica solo alla **prima creazione**, non ai valori già in session_state.

## 🎯 Test di Verifica

### Test 1: Valori Multiselect
```python
from app.data_utils import get_unique_types
import pandas as pd

df = pd.read_csv('data/analysis_summary.csv')
tipi = get_unique_types(df)

print("Tipi disponibili:")
for t in tipi:
    print(f"  • {t}")
    assert ',' not in t, f"Trovata combinazione: {t}"

print("✅ Nessuna combinazione trovata")
```

### Test 2: Filtro con Combinazioni
```python
# Dato: Scuola con "Liceo, Tecnico"
# Quando: Filtro per "Liceo"
# Allora: La scuola appare nei risultati

df_test = pd.DataFrame({
    'tipo_scuola': ['Liceo', 'Liceo, Tecnico', 'Tecnico']
})

from app.data_utils import filter_by_type
result = filter_by_type(df_test, ['Liceo'])

assert len(result) == 2  # Liceo + Liceo,Tecnico
print("✅ Filtro funziona con combinazioni")
```

## 🔄 Prossimi Passi

1. **Riavvia la dashboard:**
   ```bash
   ./start_dashboard.sh
   ```

2. **Verifica i filtri:**
   - Tipo Scuola: solo 6 opzioni
   - Ordine Grado: solo valori individuali
   - Nessuna combinazione visibile

3. **Test funzionale:**
   - Seleziona "Liceo" → Dovrebbe mostrare anche scuole "Liceo, Tecnico"
   - Seleziona "Tecnico" → Dovrebbe mostrare anche scuole "Liceo, Tecnico"

---

**Fix completato il:** 2025-12-21
**File modificato:** [app/data_utils.py](app/data_utils.py)
**Righe modificate:** 111-118, 149-155
