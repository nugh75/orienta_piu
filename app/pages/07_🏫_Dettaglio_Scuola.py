# 🏫 Dettaglio Scuola - Analisi singola scuola

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import json
import glob

st.set_page_config(page_title="Dettaglio Scuola", page_icon="🏫", layout="wide")

# CSS per il selectbox delle scuole - testo più piccolo e non troncato
st.markdown("""
<style>
    /* Selectbox opzioni - testo più piccolo */
    div[data-baseweb="select"] > div {
        font-size: 0.85rem !important;
    }
    
    /* Dropdown menu opzioni */
    div[data-baseweb="popover"] li {
        font-size: 0.8rem !important;
        white-space: normal !important;
        word-wrap: break-word !important;
    }
    
    /* Input selezionato nel selectbox */
    div[data-baseweb="select"] span {
        font-size: 0.85rem !important;
        white-space: normal !important;
        overflow: visible !important;
        text-overflow: clip !important;
    }
    
    /* Metriche info generali - font più piccolo */
    div[data-testid="stMetric"] {
        padding: 8px !important;
    }
    div[data-testid="stMetric"] label {
        font-size: 0.75rem !important;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        font-size: 0.95rem !important;
    }
</style>
""", unsafe_allow_html=True)

SUMMARY_FILE = 'data/analysis_summary.csv'

LABEL_MAP = {
    'mean_finalita': 'Media Finalità',
    'mean_obiettivi': 'Media Obiettivi', 
    'mean_governance': 'Media Governance',
    'mean_didattica_orientativa': 'Media Didattica',
    'mean_opportunita': 'Media Opportunità',
}

def get_label(col):
    return LABEL_MAP.get(col, col.replace('_', ' ').title())

@st.cache_data(ttl=60)
def load_data():
    if os.path.exists(SUMMARY_FILE):
        return pd.read_csv(SUMMARY_FILE)
    return pd.DataFrame()

df = load_data()

st.title("🏫 Dettaglio Scuola")

with st.expander("📖 Come leggere questa pagina", expanded=False):
    st.markdown("""
    ### 🎯 Scopo della Pagina
    Questa pagina fornisce un'**analisi approfondita** di una singola scuola, mostrando tutti i dettagli dell'analisi del PTOF.
    
    ### 📊 Sezioni Disponibili
    
    **📋 Informazioni Generali**
    - Dati anagrafici della scuola (codice, tipo, comune, regione)
    - **Indice RO**: Punteggio complessivo di Robustezza dell'Orientamento (scala 1-7)
      - 1-2: Insufficiente | 3-4: Sufficiente | 5-6: Buono | 7: Eccellente
    
    **🕸️ Profilo Radar**
    - Mostra il **profilo multidimensionale** della scuola
    - Ogni vertice rappresenta una delle 5 dimensioni valutate:
      - **Finalità**: Chiarezza degli obiettivi di orientamento
      - **Obiettivi**: Specificità e misurabilità dei traguardi
      - **Governance**: Organizzazione e responsabilità
      - **Didattica**: Metodologie orientative applicate
      - **Opportunità**: Connessioni con territorio e mondo del lavoro
    - Più il profilo è ampio e regolare, migliore è la qualità
    
    **📈 Punteggi Dettagliati**
    - Barre orizzontali che mostrano il punteggio per ogni dimensione
    - Permettono un confronto immediato tra le aree
    
    **📖 Report Completo**
    - Testo descrittivo generato dall'analisi AI del PTOF
    - Contiene osservazioni qualitative e raccomandazioni
    
    **🏆 Posizione in Classifica**
    - **Percentile**: Indica la posizione relativa (es: 80° = supera l'80% delle scuole)
    - Confronto con la media nazionale e del proprio tipo
    """)

if df.empty:
    st.warning("Nessun dato disponibile")
    st.stop()

# School selector with search
school_options_all = df['denominazione'].dropna().unique().tolist()

# Search box
search_query = st.text_input("🔍 Cerca (codice, nome, comune)", placeholder="es: MIIS08900V o Milano", key="search_detail")

# Filter based on search
if search_query:
    search_upper = search_query.upper()
    filtered_df = df[
        df['school_id'].str.upper().str.contains(search_upper, na=False) |
        df['denominazione'].str.upper().str.contains(search_upper, na=False) |
        df['comune'].astype(str).str.upper().str.contains(search_upper, na=False)
    ]
    school_options = filtered_df['denominazione'].dropna().unique().tolist()
    st.caption(f"Trovate: {len(school_options)} scuole")
else:
    school_options = school_options_all

if not school_options:
    st.warning("Nessuna scuola trovata con questo filtro")
    st.stop()

# Navigazione tra scuole
if 'selected_school_name' not in st.session_state:
    st.session_state.selected_school_name = school_options[0]
elif st.session_state.selected_school_name not in school_options:
    # Se la scuola selezionata non è più nelle opzioni (es. cambio filtro), resetta
    st.session_state.selected_school_name = school_options[0]

current_index = school_options.index(st.session_state.selected_school_name)

def prev_school():
    new_index = (current_index - 1) % len(school_options)
    st.session_state.selected_school_name = school_options[new_index]

def next_school():
    new_index = (current_index + 1) % len(school_options)
    st.session_state.selected_school_name = school_options[new_index]

col_prev, col_sel, col_next = st.columns([1, 10, 1])

with col_prev:
    st.write("") # Spacer per allineamento verticale
    st.write("")
    st.button("⬅️", on_click=prev_school, help="Scuola precedente", use_container_width=True)

with col_sel:
    selected_school = st.selectbox("Seleziona Scuola", school_options, key="selected_school_name")

with col_next:
    st.write("") # Spacer per allineamento verticale
    st.write("")
    st.button("➡️", on_click=next_school, help="Scuola successiva", use_container_width=True)

if selected_school:
    school_data = df[df['denominazione'] == selected_school].iloc[0]
    
    # Metadata
    st.subheader("📋 Informazioni Generali")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Codice", school_data.get('school_id', 'N/D'))
    with col2:
        st.metric("Tipo", school_data.get('tipo_scuola', 'N/D'))
    with col3:
        st.metric("Area", school_data.get('area_geografica', 'N/D'))
    with col4:
        idx = school_data.get('ptof_orientamento_maturity_index', 0)
        st.metric("Indice RO", f"{idx:.2f}/7" if pd.notna(idx) else "N/D", help="Indice di Robustezza dell'Orientamento")
    
    # Seconda riga di metadati
    col5, col6, col7, col8 = st.columns(4)
    with col5:
        regione = school_data.get('regione', 'N/D')
        st.metric("Regione", regione if regione and regione != 'ND' else 'N/D')
    with col6:
        provincia = school_data.get('provincia', 'N/D')
        st.metric("Provincia", provincia if provincia and provincia != 'ND' else 'N/D')
    with col7:
        comune = school_data.get('comune', 'N/D')
        st.metric("Comune", comune if comune and comune != 'ND' else 'N/D')
    with col8:
        statale = school_data.get('statale_paritaria', 'N/D')
        st.metric("Stato", statale if statale and statale != 'ND' else 'N/D')
    
    # Contatti (se disponibili)
    email = school_data.get('email', '')
    pec = school_data.get('pec', '')
    website = school_data.get('website', '')
    indirizzo = school_data.get('indirizzo', '')
    cap = school_data.get('cap', '')
    
    has_contacts = any(v and v != 'ND' for v in [email, pec, website, indirizzo])
    if has_contacts:
        with st.expander("📧 Contatti e Indirizzo", expanded=False):
            if indirizzo and indirizzo != 'ND':
                addr = f"{indirizzo}"
                if cap and cap != 'ND':
                    addr += f" - {cap}"
                comune_val = school_data.get('comune', '')
                if comune_val and comune_val != 'ND':
                    addr += f" {comune_val}"
                st.write(f"📍 **Indirizzo:** {addr}")
            if email and email != 'ND' and isinstance(email, str):
                st.write(f"📧 **Email:** {email}")
            if pec and pec != 'ND' and isinstance(pec, str):
                st.write(f"📨 **PEC:** {pec}")
            if website and website != 'ND' and isinstance(website, str):
                st.write(f"🌐 **Sito Web:** [{website}]({website if website.startswith('http') else 'https://' + website})")
    
    st.info("""
💡 **A cosa serve**: Fornisce una panoramica della scuola con i dati identificativi e il punteggio complessivo.

🔍 **Cosa rileva**: L'**Indice RO** (Robustezza Orientamento) è il punteggio principale (scala 1-7). Valori 1-2 = insufficiente, 3-4 = sufficiente, 5-6 = buono, 7 = eccellente.

🎯 **Implicazioni**: Un punteggio alto indica un PTOF con orientamento ben strutturato. I contatti permettono di approfondire direttamente con la scuola.
""")
    
    st.markdown("---")

    # MD Report Viewer (Moved here)
    school_id = school_data.get('school_id')
    if school_id:
        md_files = glob.glob(f'analysis_results/*{school_id}*_analysis.md')
        if md_files:
            st.markdown("### 📝 Report Analisi Completo")
            with open(md_files[0], 'r') as f:
                st.markdown(f.read())
    
    st.markdown("---")
    
    # Radar Chart
    st.subheader("🕸️ Profilo Radar")
    radar_cols = ['mean_finalita', 'mean_obiettivi', 'mean_governance', 'mean_didattica_orientativa', 'mean_opportunita']
    if all(c in df.columns for c in radar_cols):
        school_vals = [school_data.get(c, 0) if pd.notna(school_data.get(c)) else 0 for c in radar_cols]
        avg_vals = [df[c].mean() for c in radar_cols]
        labels = ['Finalità', 'Obiettivi', 'Governance', 'Didattica', 'Opportunità']
        
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=school_vals + [school_vals[0]], theta=labels + [labels[0]],
                                       fill='toself', name=selected_school[:25], 
                                       line_color='#1f77b4', marker=dict(color='#1f77b4')))
        fig.add_trace(go.Scatterpolar(r=avg_vals + [avg_vals[0]], theta=labels + [labels[0]],
                                       fill='toself', name='Media Campione', opacity=0.5, 
                                       line_color='#ff7f0e', marker=dict(color='#ff7f0e')))
        fig.update_layout(polar=dict(radialaxis=dict(range=[0, 7])), showlegend=True)
        st.plotly_chart(fig, use_container_width=True)
        
        st.info("""
💡 **A cosa serve**: Mostra il "profilo" della scuola sulle 5 dimensioni dell'orientamento, confrontato con la media nazionale.

🔍 **Cosa rileva**: L'area blu è la scuola, quella arancione è la media del campione. Dove il blu "esce" dall'arancione, la scuola eccelle. Dove è "dentro", c'è margine di miglioramento.

🎯 **Implicazioni**: Identifica rapidamente punti di forza (da valorizzare nella comunicazione) e aree critiche (dove investire in formazione o risorse).
""")
    
    st.markdown("---")
    
    # Detailed scores bar chart
    st.subheader("📊 Punteggi Dettagliati")
    score_cols = [c for c in df.columns if '_score' in c]
    if score_cols:
        scores = {get_label(c): school_data.get(c, 0) for c in score_cols if pd.notna(school_data.get(c))}
        if scores:
            score_df = pd.DataFrame({'Dimensione': list(scores.keys()), 'Punteggio': list(scores.values())})
            score_df = score_df.sort_values('Punteggio', ascending=True)
            
            fig = px.bar(score_df, x='Punteggio', y='Dimensione', orientation='h',
                        color='Punteggio', color_continuous_scale='RdYlGn',
                        range_x=[0, 7], range_color=[1, 7])
            fig.update_layout(height=600)
            st.plotly_chart(fig, use_container_width=True)
            
            st.info("""
💡 **A cosa serve**: Mostra il punteggio di ogni singolo indicatore valutato nel PTOF.

🔍 **Cosa rileva**: Ogni barra è un indicatore specifico. Verde = punteggio alto (buono), Rosso = punteggio basso (critico). Le barre più corte indicano le aree prioritarie.

🎯 **Implicazioni**: Usa questa vista per identificare esattamente QUALI aspetti migliorare nel PTOF. Gli indicatori in rosso sono le priorità di intervento concrete.
""")
    
    st.markdown("---")
    
    # Load JSON for detailed data
    st.subheader("📄 Dettaglio dal Report")
    school_id = school_data.get('school_id', '')
    json_files = glob.glob(f'analysis_results/*{school_id}*_analysis.json')
    
    if json_files:
        try:
            with open(json_files[0], 'r') as f:
                json_data = json.load(f)
            
            sec2 = json_data.get('ptof_section2', {})
            
            # Partnership
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### 🤝 Partnership")
                partnerships = sec2.get('2_2_partnership', {})
                partners = partnerships.get('partner_nominati', [])
                if partners:
                    st.write(f"**Numero Partner:** {len(partners)}")
                    for p in partners:
                        st.write(f"- {p}")
                else:
                    st.write("Nessuna partnership nominata")
            
            # Section 2.1
            with col2:
                st.markdown("### 📋 Sezione Orientamento")
                s21 = sec2.get('2_1_ptof_orientamento_sezione_dedicata', {})
                has_sez = "✅ Sì" if s21.get('has_sezione_dedicata') else "❌ No"
                st.write(f"**Sezione dedicata:** {has_sez}")
                st.write(f"**Punteggio:** {s21.get('score', 'N/D')}/7")
                if s21.get('note'):
                    st.caption(s21.get('note'))
            
            st.markdown("---")
            
            # Finalità detail
            st.markdown("### 🎯 Finalità (dettaglio)")
            finalita = sec2.get('2_3_finalita', {})
            for key, val in finalita.items():
                if isinstance(val, dict):
                    score = val.get('score', 0)
                    st.write(f"**{get_label(key)}:** {score}/7")
            
        except Exception as e:
            st.error(f"Errore caricamento JSON: {e}")
    else:
        st.info("Report JSON non ancora disponibile per questa scuola")
    
    # Position in ranking
    st.subheader("📈 Posizione in Classifica")
    if 'ptof_orientamento_maturity_index' in df.columns:
        df_sorted = df.sort_values('ptof_orientamento_maturity_index', ascending=False).reset_index(drop=True)
        df_sorted.index = df_sorted.index + 1
        position = df_sorted[df_sorted['denominazione'] == selected_school].index[0]
        total = len(df_sorted)
        
        percentile = (total - position) / total * 100
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Posizione", f"#{position}")
        with col2:
            st.metric("Su totale", f"{total} scuole")
        with col3:
            st.metric("Percentile", f"{percentile:.0f}°")
        
        st.info("""
💡 **A cosa serve**: Indica la posizione della scuola nella classifica nazionale e il confronto con le altre.

🔍 **Cosa rileva**: Il percentile indica quante scuole questa supera. Es: 75° percentile = supera il 75% degli istituti analizzati. Più è alto, meglio è.

🎯 **Implicazioni**: Un dato utile per la comunicazione esterna ("Siamo nel top 20%"). Permette anche di fissare obiettivi concreti ("Vogliamo passare dal 60° al 75° percentile").
""")
    
    st.markdown("---")
    
    # === EXPORT PDF SCHEDA SCUOLA ===
    st.subheader("📥 Esporta Scheda Scuola")
    
    # Prepare data for PDF
    def generate_school_pdf(school_data, radar_cols, df):
        """Generate PDF report for a single school"""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from io import BytesIO
            
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, 
                                    rightMargin=2*cm, leftMargin=2*cm,
                                    topMargin=2*cm, bottomMargin=2*cm)
            
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], 
                                         fontSize=18, spaceAfter=12, textColor=colors.HexColor('#2c3e50'))
            heading_style = ParagraphStyle('CustomHeading', parent=styles['Heading2'],
                                           fontSize=14, spaceAfter=8, textColor=colors.HexColor('#34495e'))
            normal_style = styles['Normal']
            
            story = []
            
            # Title
            story.append(Paragraph(f"📋 Scheda Scuola", title_style))
            story.append(Paragraph(f"<b>{school_data.get('denominazione', 'N/D')}</b>", heading_style))
            story.append(Spacer(1, 12))
            
            # Info table
            info_data = [
                ['Codice Meccanografico', str(school_data.get('school_id', 'N/D'))],
                ['Tipo Scuola', str(school_data.get('tipo_scuola', 'N/D'))],
                ['Regione', str(school_data.get('regione', 'N/D'))],
                ['Provincia', str(school_data.get('provincia', 'N/D'))],
                ['Comune', str(school_data.get('comune', 'N/D'))],
                ['Statale/Paritaria', str(school_data.get('statale_paritaria', 'N/D'))],
            ]
            
            info_table = Table(info_data, colWidths=[6*cm, 10*cm])
            info_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2c3e50')),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(info_table)
            story.append(Spacer(1, 20))
            
            # Main score
            idx = school_data.get('ptof_orientamento_maturity_index', 0)
            idx_str = f"{idx:.2f}/7" if pd.notna(idx) else "N/D"
            story.append(Paragraph(f"<b>Indice Robustezza Orientamento (RO):</b> {idx_str}", heading_style))
            story.append(Spacer(1, 12))
            
            # Dimension scores
            story.append(Paragraph("Punteggi per Dimensione", heading_style))
            
            dim_labels = ['Finalità', 'Obiettivi', 'Governance', 'Didattica Orientativa', 'Opportunità']
            dim_data = [['Dimensione', 'Punteggio']]
            
            for col, label in zip(radar_cols, dim_labels):
                val = school_data.get(col, 0)
                val_str = f"{val:.2f}/7" if pd.notna(val) else "N/D"
                dim_data.append([label, val_str])
            
            dim_table = Table(dim_data, colWidths=[8*cm, 4*cm])
            dim_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(dim_table)
            story.append(Spacer(1, 20))
            
            # Ranking
            df_sorted_pdf = df.sort_values('ptof_orientamento_maturity_index', ascending=False).reset_index(drop=True)
            df_sorted_pdf.index = df_sorted_pdf.index + 1
            pos = df_sorted_pdf[df_sorted_pdf['denominazione'] == school_data.get('denominazione')].index[0]
            tot = len(df_sorted_pdf)
            pct = (tot - pos) / tot * 100
            
            story.append(Paragraph("Posizione in Classifica Nazionale", heading_style))
            rank_data = [
                ['Posizione', f"#{pos} su {tot} scuole"],
                ['Percentile', f"{pct:.0f}° (supera il {pct:.0f}% delle scuole)"],
            ]
            rank_table = Table(rank_data, colWidths=[6*cm, 10*cm])
            rank_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(rank_table)
            story.append(Spacer(1, 20))
            
            # Footer
            from datetime import datetime
            story.append(Spacer(1, 30))
            story.append(Paragraph(f"<i>Report generato il {datetime.now().strftime('%d/%m/%Y %H:%M')}</i>", normal_style))
            story.append(Paragraph("<i>Dashboard PTOF - Analisi Robustezza Orientamento</i>", normal_style))
            
            doc.build(story)
            buffer.seek(0)
            return buffer.getvalue()
            
        except ImportError:
            return None
        except Exception as e:
            st.error(f"Errore generazione PDF: {e}")
            return None
    
    try:
        pdf_bytes = generate_school_pdf(school_data, radar_cols, df)
        
        if pdf_bytes:
            col_pdf1, col_pdf2 = st.columns([1, 2])
            with col_pdf1:
                st.download_button(
                    label="📥 Scarica Scheda PDF",
                    data=pdf_bytes,
                    file_name=f"scheda_{school_data.get('school_id', 'scuola')}.pdf",
                    mime="application/pdf",
                    help="Scarica la scheda completa della scuola in formato PDF"
                )
            with col_pdf2:
                st.caption("La scheda PDF include: dati anagrafici, punteggi per dimensione, posizione in classifica.")
        else:
            st.warning("⚠️ Per generare PDF installa reportlab: `pip install reportlab`")
            
    except Exception as e:
        st.warning(f"Export PDF non disponibile: {e}")
        st.caption("Installa reportlab: `pip install reportlab`")
    
    st.markdown("---")
    
    # PDF Viewer
    st.subheader("📄 Documento PTOF Originale")
    school_id = school_data.get('school_id', '')

    pdf_path = None
    search_dirs = ["ptof_processed", "ptof_inbox"]
    try:
        from app.data_utils import find_pdf_for_school
        pdf_path = find_pdf_for_school(school_id, base_dirs=search_dirs)
    except Exception:
        pdf_patterns = []
        for base_dir in search_dirs:
            pdf_patterns.extend([
                os.path.join(base_dir, f"*{school_id}*.pdf"),
                os.path.join(base_dir, f"{school_id}*.pdf"),
                os.path.join(base_dir, f"*_{school_id}_*.pdf"),
                os.path.join(base_dir, "**", f"*{school_id}*.pdf"),
            ])
        pdf_files = []
        for pattern in pdf_patterns:
            pdf_files.extend(glob.glob(pattern, recursive=True))

        if not pdf_files:
            for base_dir in search_dirs:
                all_pdfs = glob.glob(os.path.join(base_dir, "**", "*.pdf"), recursive=True)
                for pdf in all_pdfs:
                    pdf_name = os.path.basename(pdf).upper()
                    if school_id.upper() in pdf_name:
                        pdf_files.append(pdf)
                        break
                if pdf_files:
                    break

        if pdf_files:
            pdf_path = sorted(set(pdf_files))[0]

    if pdf_path:
        st.success(f"📎 PDF trovato: `{os.path.basename(pdf_path)}`")
        
        try:
            import base64
            
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
            
            base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
            
            # Embed PDF using iframe
            pdf_display = f'''
                <iframe src="data:application/pdf;base64,{base64_pdf}" 
                        width="100%" height="800" type="application/pdf">
                </iframe>
            '''
            st.markdown(pdf_display, unsafe_allow_html=True)
            
            # Also provide download button
            st.download_button(
                label="📥 Scarica PDF",
                data=pdf_bytes,
                file_name=os.path.basename(pdf_path),
                mime="application/pdf"
            )
            
        except Exception as e:
            st.warning(f"Impossibile visualizzare il PDF inline: {e}")
            st.info("Usa il pulsante download per scaricare il file.")
            
            with open(pdf_path, "rb") as f:
                st.download_button(
                    label="📥 Scarica PDF",
                    data=f.read(),
                    file_name=os.path.basename(pdf_path),
                    mime="application/pdf"
                )
    else:
        st.info(f"📂 PDF non trovato per {school_id}. Verifica che il file sia in `ptof/` o `ptof_processed/`.")
        st.caption("Cartelle cercate: ptof/, ptof_processed/, ptof_inbox/")
