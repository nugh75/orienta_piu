# Guida rapida: tmux + log viewer

## Installazione (Ubuntu/Debian)
- `sudo apt-get update && sudo apt-get install -y tmux lnav multitail`

## tmux: comandi essenziali
- Nuova sessione: `tmux new -s work`
- Rientra in una sessione: `tmux attach -t work`
- Lista sessioni: `tmux ls`
- Detach (senza chiudere): `Ctrl+b` poi `d`
- Dividi finestra in orizzontale: `Ctrl+b` poi `"` (doppio apice)
- Dividi in verticale: `Ctrl+b` poi `%`
- Cambia pannello: `Ctrl+b` poi frecce
- Chiudi pannello corrente: `exit` nel pannello o `Ctrl+d`

Layout suggerito per lavorare sui log:
1) Apri tmux: `tmux new -s logs`
2) Pannello sinistro: comandi (es. `make run`, `make dashboard`)
3) Pannello destro, diviso in due:
   - In alto: `make logs-live`
   - In basso: `make logs`

## Visualizzare i log
- `make logs` → apre lnav su `logs/` se installato; altrimenti usa il viewer interattivo Python (menu con selezione file e opzione follow).
- `make logs-live` → segue i log in tempo reale: prova lnav, altrimenti multitail, altrimenti `tail -F`.
- Lancia lnav direttamente: `lnav logs/`
  - Filtra: `:filter-in ERROR` (o `:filter-clear`)
  - Cerca: `/testo`, poi `n`/`N`
  - Cambia file/vista: `Tab` o `←/→`
  - Chiudi: `q`

## Esempi rapidi
- Sessione log completa:
  - `tmux new -s logs`
  - `Ctrl+b %` (split verticale)
  - Nel pannello sinistro: `make run`
  - Nel pannello destro: `Ctrl+b "` (split orizzontale)
    - In alto: `make logs-live`
    - In basso: `make logs`
- Solo log veloce senza tmux:
  - `make logs-live`
  - oppure `lnav logs/`
