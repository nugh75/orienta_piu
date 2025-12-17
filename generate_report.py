from fpdf import FPDF
import pandas as pd
import datetime

class ReportPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Report Estrazione Statistica Scuole', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')

def create_pdf(sample_file, output_file):
    df = pd.read_csv(sample_file, sep=';', encoding='latin1')
    
    pdf = ReportPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # 1. Methodology
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "Metodologia di Estrazione", 0, 1)
    pdf.set_font("Arial", size=11)
    
    text = (
        f"Data di Estrazione: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        "Obiettivo: Selezionare un campione rappresentativo di 25 scuole.\n\n"
        "Fonte Dati: Le liste sono state prese dalla seconda estrazione INVALSI.\n\n"
        "Procedura:\n"
        "1. I dati sono stati aggregati da 6 liste regionali/scolastiche.\n"
        "2. Sono stati rimossi i duplicati basandosi sul codice plesso.\n"
        "3. La stratificazione e' stata effettuata utilizzando la variabile 'strato'.\n"
        "4. Campionamento Stratificato:\n"
        "   - Dimensione totale campione: 25 scuole.\n"
        "   - Criterio di allocazione: Minimo 1 scuola per strato per garantire copertura totale.\n"
        "   - I restanti posti sono stati assegnati proporzionalmente agli strati piu' numerosi.\n\n"
        "Strumenti Utilizzati:\n"
        "L'estrazione e' stata effettuata mediante uno script Python personalizzato basato sulla libreria pandas, "
        "garantendo riproducibilita' e accuratezza statistica."
    )
    pdf.multi_cell(0, 7, text)
    pdf.ln(5)
    
    # 2. Statistics
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "Statistiche del Campione", 0, 1)
    pdf.set_font("Arial", size=11)
    
    unique_strata = sorted(df['strato'].unique())
    strata_list = ", ".join(unique_strata)
    
    grade_counts = df['grado'].value_counts()
    grade_text = "\n".join([f"- {g}: {c}" for g, c in grade_counts.items()])

    stats_text = (
        f"Totale Scuole nel Campione: {len(df)}\n"
        f"Totale Strati Rappresentati: {len(unique_strata)}\n\n"
        "Distribuzione per Grado:\n"
        f"{grade_text}\n\n"
        "Dettaglio Strati Inclusi:\n"
        f"{strata_list}"
    )
    pdf.multi_cell(0, 7, stats_text)
    pdf.ln(5)

    # 3. List of Schools
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "Elenco Scuole Selezionate", 0, 1)
    pdf.ln(5)
    
    pdf.set_font("Arial", size=8)
    
    # Table Header
    cols = ['denominazionescuola', 'nome_comune', 'strato', 'grado', 'tel_segreteria', 'indirizzoemailscuola']
    # Total width ~ 190. Adjusted for A4.
    widths = [45, 22, 30, 25, 22, 45]
    
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(widths[0], 8, 'Scuola', 1, 0, 'C', 1)
    pdf.cell(widths[1], 8, 'Comune', 1, 0, 'C', 1)
    pdf.cell(widths[2], 8, 'Strato', 1, 0, 'C', 1)
    pdf.cell(widths[3], 8, 'Grado', 1, 0, 'C', 1)
    pdf.cell(widths[4], 8, 'Telefono', 1, 0, 'C', 1)
    pdf.cell(widths[5], 8, 'Email', 1, 1, 'C', 1)
    
    pdf.set_font("Arial", size=7)
    for index, row in df.iterrows():
        # Truncate strings if too long
        scuola = str(row['denominazionescuola'])[:25]
        comune = str(row['nome_comune'])[:15]
        strato = str(row['strato'])[:20]
        grado = str(row['grado'])
        tel = str(row['tel_segreteria'])[:15]
        email = str(row['indirizzoemailscuola'])[:25]
        
        pdf.cell(widths[0], 7, scuola, 1)
        pdf.cell(widths[1], 7, comune, 1)
        pdf.cell(widths[2], 7, strato, 1)
        pdf.cell(widths[3], 7, grado, 1)
        pdf.cell(widths[4], 7, tel, 1)
        pdf.cell(widths[5], 7, email, 1)
        pdf.ln()

    pdf.output(output_file)
    print(f"PDF generated: {output_file}")

if __name__ == "__main__":
    create_pdf('campione_scuole.csv', 'report_estrazione.pdf')
