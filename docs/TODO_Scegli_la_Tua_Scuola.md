# TODO: Sezione per Genitori e Studenti

## Concept

Creare una **nuova pagina dedicata** chiamata **"🎓 Scegli la Tua Scuola"** pensata specificamente per famiglie e studenti. La prospettiva è completamente diversa da quella delle scuole: non miglioramento interno, ma **scelta informata**.

---

## Struttura della Pagina

### Step 1: "Dimmi cosa cerchi"
Un wizard guidato con domande semplici (non tecniche):

1. **Dove abiti?** → Selezione regione/provincia
2. **Che tipo di scuola cerchi?** → Liceo, Tecnico, Professionale
3. **Cosa ti interessa di più?** → Scelta multipla:
   - 🎯 Orientamento universitario forte
   - 💼 Preparazione al mondo del lavoro (stage, PCTO)
   - 🔬 Laboratori e attività pratiche
   - 🌍 Progetti internazionali e lingue
   - 🎭 Attività extracurriculari (teatro, musica, sport)
   - 💻 Tecnologia e innovazione
   - 🤝 Attenzione all'inclusione

### Step 2: "Ecco le scuole per te"
Lista delle scuole filtrate e ordinate per compatibilità con le preferenze espresse:

- **Card per ogni scuola** con:
  - Nome e posizione
  - "Indice di Orientamento" tradotto in stelle (★★★★☆) invece di numeri
  - Tag colorati con i punti di forza (es. "STEM", "Lingue", "Stage aziendali")
  - Pulsante "Confronta" per aggiungere al confronto

### Step 3: "Confronta le tue scuole preferite"
Confronto visivo di 2-3 scuole selezionate:

- **Tabella comparativa semplificata** (no gergo tecnico):
  - "Preparazione al futuro" (invece di "Didattica Orientativa")
  - "Collaborazioni con aziende/università" (invece di "Opportunità")
  - "Organizzazione e progetti" (invece di "Governance")

- **Grafico radar semplificato** con etichette comprensibili

- **Pro e contro** di ogni scuola evidenziati

- **"Cosa dicono i dati"** → Breve sintesi testuale generata automaticamente

---

## Integrazione nella Home

Nella Home, aggiungere un **box dedicato** sopra o accanto al contenuto esistente:

```
┌─────────────────────────────────────────────────────────┐
│  🎓 Sei un genitore o uno studente?                     │
│                                                          │
│  Stai scegliendo la scuola superiore? Usa il nostro     │
│  strumento per confrontare le scuole della tua zona     │
│  e trovare quella più adatta a te.                      │
│                                                          │
│  [🔍 Trova la scuola giusta per te]                     │
└─────────────────────────────────────────────────────────┘
```

---

## Principi di Design

1. **Linguaggio semplice**: Niente "Indice RO", "dimensioni", "maturity". Traduzioni user-friendly
2. **Wizard guidato**: Passo dopo passo, non form complessi
3. **Visivo**: Stelle, icone, colori invece di numeri
4. **Mobile-first**: Molti genitori useranno il telefono
5. **Rassicurante**: Tono positivo, focus sui punti di forza

---

## File da creare/modificare

| File | Azione |
|------|--------|
| `app/pages/11_🎓_Scegli_la_Tua_Scuola.py` | Nuova pagina dedicata |
| `app/Home.py` | Aggiungere box per genitori/studenti |
| `app/match_engine.py` | Aggiungere funzione `match_for_families()` |

---

## Domande aperte

Prima di procedere all'implementazione:

1. **Va bene una pagina dedicata** oppure preferisci solo una sezione nella Home?
2. **Il wizard con le domande** ti sembra adatto o preferisci un approccio diverso (es. filtri classici)?
3. **Vuoi aggiungere altri criteri** di scelta oltre a quelli proposti?

---

## Status: IN ATTESA DI APPROVAZIONE
