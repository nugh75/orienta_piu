
## Aggiornamento 2025-12-23: Revert Fix

**Problema:** Il fix precedente ha introdotto un `TypeError` perché `st.button` e altri componenti non supportano il parametro `width="stretch"`.
**Azione:** Ripristinato `use_container_width=True` in tutti i file.

**Comando Eseguito:**
```bash
find app -name "*.py" -type f -exec sed -i '' 's/width="stretch"/use_container_width=True/g' {} \;
```
