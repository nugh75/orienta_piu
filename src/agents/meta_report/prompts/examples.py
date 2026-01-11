"""Few-shot examples for meta report prompts.

Fase 2.1: Aggiunta di esempi concreti per guidare l'output del modello.

Ogni tipo di report ha:
- "good": Esempio di output corretto e desiderato
- "bad": Pattern da evitare (opzionale)
"""

EXAMPLES: dict[str, dict[str, str]] = {
    "school": {
        "good": """
## Contesto

L'**IIS Leonardo da Vinci** (RMIS09400V) è un istituto tecnico situato nel
territorio metropolitano di Roma. Con un'offerta formativa che spazia
dall'indirizzo informatico a quello meccanico, la scuola serve un bacino
d'utenza eterogeneo caratterizzato da significativa mobilità studentesca.

## Punti di Forza

L'istituto si distingue per un sistema di **PCTO strutturato** che coinvolge
oltre 40 aziende partner, tra cui **Accenture** e **Engineering SpA**.
Il percorso "Impresa Formativa Simulata" permette agli studenti delle classi
quarte di simulare la gestione di un'azienda, sviluppando competenze
imprenditoriali concrete. Particolarmente efficace risulta il **laboratorio
di orientamento** attivato per le classi terze, dove esperti esterni
accompagnano gli studenti nella costruzione del proprio progetto formativo.

## Aree di Sviluppo

La scuola potrebbe potenziare il coinvolgimento delle famiglie nelle attività
di orientamento, attualmente limitato agli incontri informativi di inizio anno.
Sarebbe inoltre utile strutturare un sistema di monitoraggio degli esiti
post-diploma per valutare l'efficacia dei percorsi proposti.

## Conclusioni

L'IIS Leonardo da Vinci presenta un profilo orientativo solido, con particolare
eccellenza nei PCTO e nelle partnership aziendali. Il consolidamento del
rapporto con le famiglie e l'attivazione di un sistema di follow-up
rappresentano le principali aree di crescita.
""",
        "bad": """
EVITARE:
- Elenchi puntati lunghi senza contesto narrativo
- Codici inventati (es. XXXX99999Z)
- Frasi generiche come "La scuola eccelle in tutto"
- Blocchi di codice ```
- Toni eccessivamente celebrativi
"""
    },

    "regional": {
        "good": """
## Panorama Regionale: Lombardia

La Lombardia presenta un tessuto scolastico articolato con 342 istituti
secondari di II grado analizzati. La distribuzione territoriale evidenzia
una concentrazione del 45% nell'area metropolitana milanese, seguita da
Brescia (18%) e Bergamo (12%).

### Confronto tra Province

**Milano** si distingue per l'intensità delle partnership con il settore
terziario: il **Liceo Berchet** (MIPC01000C) collabora stabilmente con
Bocconi e Politecnico, mentre l'**IIS Lagrange** (MIIS02300X) ha
formalizzato accordi con 15 studi professionali per i PCTO.

**Brescia** eccelle invece nei percorsi tecnico-industriali. L'**ITI Castelli**
(BSIS00300C) ha sviluppato il progetto "Fabbrica 4.0" in collaborazione con
Beretta e Iveco, coinvolgendo annualmente 200 studenti in esperienze
aziendali strutturate.

Le province di **Mantova** e **Cremona** mostrano un orientamento prevalentemente
agricolo, con progetti territoriali che valorizzano le filiere locali.

### Scuole di Riferimento

1. **IIS Lagrange** (MIIS02300X) - Milano: eccellenza PCTO settore servizi
2. **ITI Castelli** (BSIS00300C) - Brescia: innovazione industria 4.0
3. **Liceo Banfi** (LCPS02000T) - Lecco: modello di orientamento universitario

### Trend e Innovazioni

Emerge una crescente attenzione alla **digitalizzazione** dei processi
orientativi, con 45 scuole che hanno attivato piattaforme di self-assessment.
Il tema della **sostenibilità** sta guidando nuove partnership con aziende
green, particolarmente nelle province di Bergamo e Varese.

### Raccomandazioni Regionali

1. Creare una rete regionale per la condivisione delle best practice PCTO
2. Potenziare i percorsi di orientamento per le aree non metropolitane
""",
    },

    "national": {
        "good": """
## Quadro Generale

L'analisi di 1.247 PTOF evidenzia un panorama dell'orientamento scolastico
italiano caratterizzato da significative differenze territoriali. Il punteggio
medio nazionale si attesta a 4.2/7, con una distribuzione che vede il Nord
(4.8) superare Centro (4.1) e Sud (3.7).

### Analisi Territoriale

Il **Nord-Est** emerge come area di eccellenza, trainato dal modello veneto
di integrazione scuola-lavoro. L'**Emilia-Romagna** si distingue per la
capillarità delle reti territoriali, con il 78% delle scuole coinvolte in
protocolli con enti locali.

Il **Centro** presenta una situazione polarizzata: il Lazio beneficia della
concentrazione di università e centri di ricerca, mentre Umbria e Marche
mostrano ritardi nell'attivazione di percorsi strutturati.

Il **Sud** evidenzia il divario più marcato, con punte di eccellenza
(Campania, Puglia costiera) che coesistono con aree di criticità.

### Best Practices Nazionali

1. **IIS Aldini Valeriani** (BOIS01900X) - Bologna: modello integrato orientamento-PCTO
2. **Liceo Galilei** (RMPS12000X) - Roma: piattaforma digitale di self-assessment
3. **ITI Marconi** (NAIS00700R) - Napoli: rete alumni per mentoring
4. **IIS Fermi** (TOPS01000B) - Torino: laboratori esperienziali con aziende

### Raccomandazioni Sistemiche

1. Istituire un osservatorio nazionale sull'orientamento con indicatori standardizzati
2. Finanziare progetti di recupero per le aree con punteggio inferiore a 3.5
3. Promuovere la formazione dei docenti referenti con crediti formativi dedicati
""",
    },

    "thematic": {
        "good": """
### PCTO e Partnership Aziendali

L'analisi delle 127 scuole campione evidenzia tre approcci prevalenti
nell'organizzazione dei PCTO. Il primo modello, adottato dal **Liceo Galilei**
(RMPS12000X) e dall'**IIS Marconi** (TOPS01000B), integra percorsi in azienda
con moduli di preparazione in aula, dedicando almeno 20 ore alla riflessione
sulle competenze acquisite.

Il secondo approccio privilegia le collaborazioni con il terzo settore.
L'**IIS Aldini Valeriani** (BOIS01900X) ha strutturato un programma triennale
con cooperative sociali del territorio, permettendo agli studenti di
sperimentare contesti lavorativi ad alto impatto sociale. Analogamente,
il **Liceo Fermi** (NAIS00700R) di Napoli coinvolge associazioni culturali
per percorsi nel settore dei beni culturali.

Il terzo modello, diffuso principalmente nel Nord-Est, punta sulla
**specializzazione settoriale**. L'**ITI Marzotto** (VIIS00200X) di Vicenza
ha creato un ecosistema formativo con 35 aziende del distretto tessile,
offrendo percorsi che vanno dalla progettazione alla logistica.

La distribuzione geografica mostra una concentrazione del 62% dei PCTO
strutturati nel Nord Italia, con Lombardia e Veneto che insieme rappresentano
il 41% delle esperienze censite. Il Centro-Sud evidenzia potenzialità
inespresse, con casi di eccellenza che meriterebbero maggiore visibilità.
""",
        "bad": """
EVITARE:
- "Molte scuole fanno PCTO" (troppo generico)
- Citare scuole senza codice meccanografico
- Creare cluster con nomi delle categorie amministrative
- Elenchi puntati lunghi al posto della narrazione
- Confronti valoriali tra territori senza dati
"""
    },

    "thematic_group_chunk": {
        "good": """
Nel campione analizzato emergono esperienze significative di orientamento
laboratoriale. Il **Liceo Scientifico Volta** (MIPC00500E) di Milano ha
attivato un percorso di "Scienza in pratica" che coinvolge le classi terze
in attività sperimentali presso i laboratori universitari del Politecnico.
L'iniziativa si caratterizza per la co-progettazione tra docenti liceali
e ricercatori, con una particolare attenzione alle discipline STEM.

Nella stessa direzione si muove l'**IIS Fermi** (TOIS01200L) di Torino,
che ha sviluppato un laboratorio di robotica educativa aperto anche agli
studenti delle scuole medie del territorio, creando così un ponte di
continuità verticale. Le attività si svolgono in orario extracurricolare
e coinvolgono circa 80 studenti per anno scolastico.

Il pattern comune a queste esperienze riguarda l'integrazione tra
dimensione laboratoriale e orientamento alle scelte future, con particolare
enfasi sulla metodologia del learning by doing. Le scuole del campione
lombardo e piemontese mostrano una maggiore propensione a questo approccio.
""",
    },

    "thematic_summary_merge": {
        "good": """
L'analisi trasversale dei temi evidenzia una crescente integrazione tra
orientamento e didattica laboratoriale, particolarmente sviluppata nel
Nord Italia. Le esperienze più mature combinano attività pratiche con
momenti di riflessione metacognitiva, permettendo agli studenti di
collegare le competenze acquisite al proprio progetto formativo.

Sul piano territoriale, Lombardia, Veneto ed Emilia-Romagna concentrano
il 58% delle pratiche innovative censite, con una particolare specializzazione
nei settori tecnico-industriale e dei servizi. Il Centro mostra dinamiche
interessanti nel Lazio, trainato dalla prossimità con poli universitari,
mentre il Sud presenta eccellenze puntuali che meriterebbero maggiore
sistematizzazione attraverso reti regionali strutturate.

La formazione docenti emerge come fattore discriminante: le scuole con
programmi strutturati di aggiornamento sui temi dell'orientamento mostrano
punteggi mediamente superiori del 22% rispetto a quelle senza percorsi dedicati.
""",
    },
}


def get_example(report_type: str, example_type: str = "good") -> str:
    """Get example for a specific report type.

    Args:
        report_type: Type of report (school, regional, national, thematic, etc.)
        example_type: "good" for positive examples, "bad" for anti-patterns

    Returns:
        Example text or empty string if not found
    """
    return EXAMPLES.get(report_type, {}).get(example_type, "")


def get_example_block(report_type: str) -> str:
    """Get formatted example block for inclusion in prompts.

    Args:
        report_type: Type of report

    Returns:
        Formatted example block or empty string
    """
    good = get_example(report_type, "good")
    bad = get_example(report_type, "bad")

    if not good:
        return ""

    block = f"\n\nESEMPIO DI OUTPUT CORRETTO:\n{good.strip()}"

    if bad:
        block += f"\n\nDA EVITARE:\n{bad.strip()}"

    return block
