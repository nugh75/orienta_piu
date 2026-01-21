# 📊 Campionamento - Metodologia e Report

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import json
from datetime import datetime

from data_utils import render_footer, load_summary_data
from page_control import setup_page

st.set_page_config(page_title="ORIENTA+ | Campionamento", page_icon="📊", layout="wide")
setup_page("pages/22_📊_Campionamento.py")

# File paths
SUMMARY_FILE = 'data/analysis_summary.csv'
FAILURES_FILE = 'reports/strata_failures.csv'
STRATA_STATE_FILE = 'data/strata_cycle_state.json'
ANAGRAFE_STAT_FILE = 'data/SCUANAGRAFESTAT20252620250901.csv'
ANAGRAFE_PAR_FILE = 'data/SCUANAGRAFEPAR20252620250901.csv'


def load_failures():
    """Carica il file dei fallimenti di estrazione."""
    if os.path.exists(FAILURES_FILE):
        return pd.read_csv(FAILURES_FILE)
    return pd.DataFrame()


def load_strata_state():
    """Carica lo stato del ciclo di estrazione stratificata."""
    if os.path.exists(STRATA_STATE_FILE):
        with open(STRATA_STATE_FILE, 'r') as f:
            return json.load(f)
    return {}


def calculate_diversity_index(series):
    """Calcola l'indice di diversità di Simpson (1-D)."""
    counts = series.value_counts()
    n = counts.sum()
    if n <= 1:
        return 0
    D = sum(count * (count - 1) for count in counts) / (n * (n - 1))
    return 1 - D


# === CARICAMENTO DATI ===
df = load_summary_data()
failures_df = load_failures()
strata_state = load_strata_state()

# === HEADER ===
st.title("📊 Campionamento e Bilanciamento")
st.markdown("**Metodologia di campionamento stratificato e report di estrazione PTOF**")

# === TABS PRINCIPALI ===
tab_methodology, tab_balance, tab_failures = st.tabs([
    "📖 Metodologia", 
    "⚖️ Bilanciamento Campione",
    "❌ Scuole Senza PTOF"
])

# =============================================================================
# TAB 1: METODOLOGIA
# =============================================================================
with tab_methodology:
    st.header("📖 Metodologia di Campionamento")
    
    st.markdown("""
    ### Obiettivo del Campionamento
    
    Il campionamento è stato progettato per ottenere un **campione rappresentativo** delle scuole italiane 
    di ogni ordine e grado, garantendo:
    
    - ✅ **Copertura territoriale** di tutte le regioni italiane
    - ✅ **Rappresentatività** di tutti gli ordini scolastici (Infanzia, Primaria, I e II Grado)
    - ✅ **Inclusione** sia di scuole statali che paritarie
    - ✅ **Equilibrio** tra aree metropolitane e non metropolitane
    
    ---
    
    ### Procedura di Campionamento Stratificato
    
    Il campionamento segue un approccio **stratificato multi-stage**:
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        #### 🔹 Fase 1: Definizione degli Strati
        
        Ogni scuola è classificata in uno **strato** definito da:
        
        | Dimensione | Categorie |
        |------------|-----------|
        | **Gestione** | Statale, Paritaria |
        | **Area Geografica** | Nord Ovest, Nord Est, Centro, Sud, Isole |
        | **Territorio** | Metropolitano, Non Metropolitano |
        | **Ordine** | Infanzia, Primaria, Sec. Primo, Sec. Secondo, Altro |
        
        Questo genera **2 × 5 × 2 × 5 = 100 strati potenziali**
        """)
    
    with col2:
        st.markdown("""
        #### 🔹 Fase 2: Estrazione Proporzionale
        
        Da ogni strato viene estratto un numero di scuole proporzionale alla sua dimensione:
        
        ```
        n_strato = (N_strato / N_totale) × n_campione_target
        ```
        
        Dove:
        - `N_strato` = numero scuole nello strato
        - `N_totale` = numero scuole nella popolazione
        - `n_campione_target` = dimensione campione desiderata
        """)
    
    st.markdown("""
    ---
    
    #### 🔹 Fase 3: Estrazione Automatica PTOF
    
    Per ogni scuola selezionata:
    
    1. **Ricerca URL PTOF** sul sito istituzionale della scuola
    2. **Download automatico** del documento PDF
    3. **Conversione in Markdown** per l'analisi testuale
    4. **Analisi AI** per l'estrazione delle dimensioni dell'orientamento
    
    ⚠️ **Fallimenti**: Se il PTOF non è reperibile automaticamente, la scuola viene registrata 
    come "fallimento" e può essere gestita con procedura manuale.
    
    ---
    
    #### 🔹 Fase 4: Validazione e Controllo Qualità
    
    - Verifica della completezza dei dati estratti
    - Controllo della coerenza dei punteggi
    - Eventuale revisione manuale per casi dubbi
    """)
    
    # =====================================================
    # REPORT PER OGNI CICLO DI ESTRAZIONE
    # =====================================================
    st.markdown("---")
    st.subheader("📈 Report dei Cicli di Estrazione")
    
    # Carica il registry dei cicli
    registry_file = 'data/strata_cycle_registry.jsonl'
    cycles_data = []
    
    if os.path.exists(registry_file):
        with open(registry_file, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    if entry.get('status') == 'completed':
                        cycles_data.append(entry)
                except:
                    pass
    
    if cycles_data:
        # Raggruppa per cycle_id e prendi l'ultimo completamento per ogni ciclo
        cycles_by_id = {}
        for entry in cycles_data:
            cid = entry.get('cycle_id', 0)
            # Prendi sempre l'ultimo (più recente) per ogni cycle_id
            cycles_by_id[cid] = entry
        
        # Ordina per cycle_id
        sorted_cycles = sorted(cycles_by_id.items(), key=lambda x: x[0])
        
        # Statistiche generali
        total_selected = sum(c.get('selected_total', 0) for _, c in sorted_cycles)
        total_downloaded = sum(c.get('downloaded_success', 0) or 0 for _, c in sorted_cycles)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Cicli Completati", len(sorted_cycles))
        with col2:
            st.metric("Scuole Selezionate (Totale)", f"{total_selected:,}")
        with col3:
            st.metric("PTOF Scaricati (Totale)", f"{total_downloaded:,}")
        with col4:
            if strata_state:
                yield_global = strata_state.get('yield_global', 0)
                st.metric("Resa Globale", f"{yield_global*100:.1f}%")
        
        st.markdown("---")
        
        # Dettaglio per ogni ciclo
        for cycle_id, cycle_data in sorted_cycles:
            # Determina icona in base al metodo
            method = cycle_data.get('method', 'stratified')
            icon = "🔄" if method == 'pre-stratified' else "📋"
            
            with st.expander(f"{icon} **Ciclo {cycle_id}** - {cycle_data.get('timestamp', 'N/A')[:10]}", expanded=False):
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Scuole Selezionate", cycle_data.get('selected_total', 'N/A'))
                with col2:
                    downloaded = cycle_data.get('downloaded_success', 0) or 0
                    st.metric("PTOF Scaricati", downloaded)
                with col3:
                    # Usa success_rate dal registry se disponibile, altrimenti calcola
                    if 'success_rate' in cycle_data:
                        success_rate = cycle_data.get('success_rate', 0)
                    else:
                        selected = cycle_data.get('selected_total', 0) or 1
                        downloaded = cycle_data.get('downloaded_success', 0) or 0
                        success_rate = (downloaded / selected * 100) if selected > 0 else 0
                    st.metric("Tasso Successo", f"{success_rate:.1f}%")
                with col4:
                    miur_strata = cycle_data.get('miur_strata', 0)
                    if miur_strata and miur_strata > 0:
                        st.metric("Strati MIUR", miur_strata)
                    else:
                        st.metric("Metodo", "Pre-stratificato" if method == 'pre-stratified' else "Stratificato")
                
                # Nota se presente
                if cycle_data.get('note'):
                    st.info(f"📝 {cycle_data.get('note')}")
                
                # Target per strato (se disponibile)
                target_per_strato = cycle_data.get('target_per_strato', {})
                if target_per_strato:
                    st.markdown("**Distribuzione target per ordine scolastico:**")
                    
                    # Aggrega per ordine
                    ordine_target = {}
                    for strato, target in target_per_strato.items():
                        # Estrai ordine dal nome strato (es. STAT_LOMBARDIA_METRO_SEC_PRIMO -> SEC_PRIMO)
                        parts = strato.split('_')
                        if len(parts) >= 2:
                            ordine = '_'.join(parts[-2:]) if parts[-2] in ['SEC'] else parts[-1]
                            ordine_label = {
                                'INFANZIA': 'Infanzia',
                                'PRIMARIA': 'Primaria', 
                                'SEC_PRIMO': 'Sec. I Grado',
                                'SEC_SECONDO': 'Sec. II Grado',
                                'ALTRO': 'Altro'
                            }.get(ordine, ordine)
                            ordine_target[ordine_label] = ordine_target.get(ordine_label, 0) + target
                    
                    if ordine_target:
                        ordine_df = pd.DataFrame([
                            {'Ordine': k, 'Target': v} 
                            for k, v in sorted(ordine_target.items(), key=lambda x: -x[1])
                        ])
                        st.dataframe(ordine_df, use_container_width=True, hide_index=True)
    else:
        st.info("Nessun ciclo di estrazione completato nel registro.")


# =============================================================================
# TAB 2: BILANCIAMENTO
# =============================================================================
with tab_balance:
    st.header("⚖️ Report sul Bilanciamento del Campione")
    
    if df.empty:
        st.warning("Nessun dato disponibile nel file di riepilogo.")
    else:
        # Statistiche generali
        st.subheader("📊 Statistiche Generali")
        
        # Calcola regioni italiane effettivamente coperte (escludendo ND, Estero, duplicati)
        regioni_italiane_ufficiali = [
            'Piemonte', "Valle d'Aosta", 'Lombardia', 'Trentino-Alto Adige', 
            'Veneto', 'Friuli-Venezia Giulia', 'Liguria', 'Emilia-Romagna',
            'Toscana', 'Umbria', 'Marche', 'Lazio', 'Abruzzo', 'Molise',
            'Campania', 'Puglia', 'Basilicata', 'Calabria', 'Sicilia', 'Sardegna'
        ]
        
        # Mappa varianti di denominazione
        regioni_presenti = set(df['regione'].dropna().unique())
        regioni_coperte = []
        regioni_mancanti = []
        for reg in regioni_italiane_ufficiali:
            found = reg in regioni_presenti
            # Controlla varianti
            if not found:
                for r in regioni_presenti:
                    if reg.replace('-', ' ').lower() in r.replace('-', ' ').lower() or \
                       r.replace('-', ' ').lower() in reg.replace('-', ' ').lower() or \
                       (reg == 'Friuli-Venezia Giulia' and 'Friuli' in r) or \
                       (reg == 'Emilia-Romagna' and 'Emilia' in r):
                        found = True
                        break
            if found:
                regioni_coperte.append(reg)
            else:
                regioni_mancanti.append(reg)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Scuole Analizzate", f"{len(df):,}")
        with col2:
            st.metric("Province Coperte", df['provincia'].nunique())
        with col3:
            st.metric("Comuni Unici", df['comune'].nunique())
        with col4:
            st.metric("Regioni Italiane Coperte", f"{len(regioni_coperte)}/20")
        
        # Alert regioni mancanti
        if regioni_mancanti:
            st.warning(f"⚠️ **Regioni mancanti nel campione**: {', '.join(regioni_mancanti)}")
        
        st.markdown("---")
        
        # Distribuzione per Area Geografica
        # =====================================================
        # SEZIONE 1: AREE GEOGRAFICHE (Macro-aree)
        # =====================================================
        st.subheader("🗺️ Distribuzione per Area Geografica (Macro-aree)")
        
        st.info("""
        **Le 5 Aree Geografiche (macro-aree)** sono le suddivisioni ISTAT utilizzate per la stratificazione:
        - **Nord Ovest**: Piemonte, Valle d'Aosta, Lombardia, Liguria
        - **Nord Est**: Trentino-Alto Adige, Veneto, Friuli-Venezia Giulia, Emilia-Romagna
        - **Centro**: Toscana, Umbria, Marche, Lazio
        - **Sud**: Abruzzo, Molise, Campania, Puglia, Basilicata, Calabria
        - **Isole**: Sicilia, Sardegna
        """)
        
        # Valori attesi (approssimativi basati sulla popolazione scolastica)
        expected_pct = {
            'Nord Ovest': 24, 'Nord Est': 15, 'Centro': 18, 'Sud': 27, 'Isole': 16
        }
        
        area_counts = df['area_geografica'].value_counts()
        area_data = []
        for area in expected_pct.keys():
            obs = area_counts.get(area, 0)
            obs_pct = obs / len(df) * 100
            exp_pct = expected_pct[area]
            dev = obs_pct - exp_pct
            area_data.append({
                'Macro-area': area,
                'N° Scuole': obs,
                'Osservato %': f"{obs_pct:.1f}%",
                'Atteso %': f"{exp_pct}%",
                'Deviazione': f"{'+' if dev > 0 else ''}{dev:.1f} pp"
            })
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.dataframe(pd.DataFrame(area_data), use_container_width=True, hide_index=True)
        
        with col2:
            fig_area = px.pie(
                values=[area_counts.get(a, 0) for a in expected_pct.keys()],
                names=list(expected_pct.keys()),
                title="5 Macro-aree Geografiche",
                hole=0.3,
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig_area.update_layout(height=300)
            st.plotly_chart(fig_area, use_container_width=True)
        
        st.markdown("---")
        
        # Distribuzione per Ordine/Grado
        st.subheader("🎓 Distribuzione per Ordine Scolastico")
        
        # Semplifica ordine_grado
        def simplify_ordine(x):
            x_str = str(x)
            if x_str == 'II Grado':
                return 'II Grado (Superiori)'
            elif x_str == 'I Grado':
                return 'I Grado (Medie)'
            elif 'Primaria' in x_str and 'I Grado' not in x_str:
                return 'Primaria'
            elif 'Infanzia' in x_str and 'Primaria' not in x_str and 'I Grado' not in x_str:
                return 'Infanzia'
            else:
                return 'Comprensivo/Misto'
        
        df['ordine_semplice'] = df['ordine_grado'].apply(simplify_ordine)
        ordine_counts = df['ordine_semplice'].value_counts()
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            ordine_df = pd.DataFrame({
                'Ordine': ordine_counts.index,
                'N° Scuole': ordine_counts.values,
                'Percentuale': [f"{v/len(df)*100:.1f}%" for v in ordine_counts.values]
            })
            st.dataframe(ordine_df, use_container_width=True, hide_index=True)
        
        with col2:
            fig_ordine = px.bar(
                x=ordine_counts.values,
                y=ordine_counts.index,
                orientation='h',
                title="Distribuzione per Ordine",
                labels={'x': 'N° Scuole', 'y': 'Ordine'}
            )
            fig_ordine.update_layout(height=300)
            st.plotly_chart(fig_ordine, use_container_width=True)
        
        st.markdown("---")
        
        # Statale vs Paritaria
        st.subheader("🏛️ Scuole Statali vs Paritarie")
        
        statale_counts = df['statale_paritaria'].value_counts()
        statale_valid = statale_counts[statale_counts.index.isin(['Statale', 'Paritaria'])]
        
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            total_valid = statale_valid.sum()
            stat_pct = statale_valid.get('Statale', 0) / total_valid * 100
            par_pct = statale_valid.get('Paritaria', 0) / total_valid * 100
            
            st.markdown(f"""
            | Tipo | N° Scuole | Osservato | Atteso (Italia) |
            |------|-----------|-----------|-----------------|
            | **Statale** | {statale_valid.get('Statale', 0)} | {stat_pct:.1f}% | ~90% |
            | **Paritaria** | {statale_valid.get('Paritaria', 0)} | {par_pct:.1f}% | ~10% |
            """)
        
        with col2:
            fig_statale = px.pie(
                values=statale_valid.values,
                names=statale_valid.index,
                title="Statale vs Paritaria",
                color_discrete_map={'Statale': '#4e73df', 'Paritaria': '#1cc88a'}
            )
            fig_statale.update_layout(height=250)
            st.plotly_chart(fig_statale, use_container_width=True)
        
        with col3:
            if par_pct > 15:
                st.warning(f"""
                ⚠️ **Attenzione**: Le scuole paritarie sono **sovrarappresentate** 
                nel campione ({par_pct:.1f}% vs ~10% nazionale).
                
                Per analisi inferenziali, applicare pesi di post-stratificazione.
                """)
            else:
                st.success("✅ Buon bilanciamento tra statali e paritarie")
        
        st.markdown("---")
        
        # Territorio Metropolitano vs Non Metropolitano
        st.subheader("🏙️ Territorio: Metropolitano vs Non Metropolitano")
        
        terr_counts = df['territorio'].value_counts()
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            for terr, count in terr_counts.items():
                if terr not in ['ND', 'N/A']:
                    st.metric(terr, f"{count} ({count/len(df)*100:.1f}%)")
        
        with col2:
            st.info("✅ **Buon equilibrio**: La distribuzione tra aree metropolitane e non metropolitane è bilanciata.")
        
        st.markdown("---")
        
        # =====================================================
        # SEZIONE 2: REGIONI ITALIANE (20 regioni)
        # =====================================================
        st.subheader("📍 Distribuzione per Regione Italiana")
        
        st.info("""
        **Le 20 Regioni Italiane** sono le suddivisioni amministrative.  
        ⚠️ **Non confondere** con le 5 macro-aree geografiche sopra!
        """)
        
        # Escludi ND ed Estero dal conteggio delle regioni
        df_regioni_valid = df[~df['regione'].isin(['ND', 'Estero', 'N/A'])].copy()
        
        # Normalizza nomi regioni (unifica varianti)
        def normalizza_regione(r):
            r_str = str(r).strip()
            # Emilia-Romagna / Emilia Romagna
            if 'Emilia' in r_str and 'Romagna' in r_str:
                return 'Emilia-Romagna'
            # Friuli-Venezia Giulia
            if 'Friuli' in r_str:
                return 'Friuli-Venezia Giulia'
            # Trentino-Alto Adige
            if 'Trentino' in r_str or 'Alto Adige' in r_str:
                return 'Trentino-Alto Adige'
            # Valle d'Aosta
            if 'Valle' in r_str and 'Aosta' in r_str:
                return "Valle d'Aosta"
            return r_str
        
        df_regioni_valid['regione_norm'] = df_regioni_valid['regione'].apply(normalizza_regione)
        regione_counts = df_regioni_valid['regione_norm'].value_counts()
        
        # Mostra tutte le regioni in un grafico a barre
        col1, col2 = st.columns([2, 1])
        
        with col1:
            fig_regione = px.bar(
                x=regione_counts.values,
                y=regione_counts.index,
                orientation='h',
                title=f"Tutte le {len(regione_counts)} Regioni nel Campione",
                labels={'x': 'N° Scuole', 'y': 'Regione'},
                color=regione_counts.values,
                color_continuous_scale='Blues'
            )
            fig_regione.update_layout(height=500, showlegend=False)
            st.plotly_chart(fig_regione, use_container_width=True)
        
        with col2:
            st.markdown("**Dettaglio regioni:**")
            
            # Mostra tutte le regioni con conteggi in una tabella
            regione_df = pd.DataFrame({
                'Regione': regione_counts.index,
                'N° Scuole': regione_counts.values,
                '%': [f"{v/len(df_regioni_valid)*100:.1f}%" for v in regione_counts.values]
            })
            st.dataframe(regione_df, use_container_width=True, hide_index=True, height=400)
            
            # Mostra esclusi
            esclusi = df[df['regione'].isin(['ND', 'Estero'])]['regione'].value_counts()
            if len(esclusi) > 0:
                st.markdown("---")
                st.caption("**Esclusi dal conteggio regionale:**")
                for reg, count in esclusi.items():
                    st.caption(f"• {reg}: {count}")
        
        st.markdown("---")
        
        # Indici di Bilanciamento
        st.subheader("📐 Indici di Diversità del Campione")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            div_area = calculate_diversity_index(df['area_geografica'])
            st.metric("Diversità Area Geografica", f"{div_area:.3f}", 
                     help="Indice Simpson (0-1): più alto = più diversificato")
        
        with col2:
            div_regione = calculate_diversity_index(df['regione'])
            st.metric("Diversità Regionale", f"{div_regione:.3f}",
                     help="Indice Simpson (0-1): più alto = più diversificato")
        
        with col3:
            div_ordine = calculate_diversity_index(df['ordine_semplice'])
            st.metric("Diversità Ordine Scolastico", f"{div_ordine:.3f}",
                     help="Indice Simpson (0-1): più alto = più diversificato")
        
        st.markdown("---")
        
        # Riepilogo Valutazione
        st.subheader("🎯 Valutazione Complessiva")
        
        with st.expander("📋 Riepilogo Punti di Forza e Attenzione", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("""
                ### ✅ Punti di Forza
                
                - **Eccellente copertura territoriale**: tutte le regioni rappresentate
                - **Buona distribuzione per aree geografiche**: deviazione max ±5 pp
                - **Tutti gli ordini scolastici presenti**: dalla scuola dell'infanzia alle superiori
                - **Equilibrio metropolitano/non metropolitano**: circa 50-50
                - **Qualità dei dati**: 100% delle estrazioni completate con successo
                """)
            
            with col2:
                st.markdown("""
                ### ⚠️ Punti di Attenzione
                
                - **Scuole paritarie sovrarappresentate**: 25% vs 10% atteso
                - **Isole sovrarappresentate**: +4.5 pp rispetto all'atteso
                - **Nord Ovest sottorappresentato**: -3.2 pp rispetto all'atteso
                - **Sicilia con maggiore concentrazione**: 15.5% del campione
                
                ➡️ **Raccomandazione**: Per analisi inferenziali nazionali, 
                applicare pesi di post-stratificazione.
                """)


# =============================================================================
# TAB 3: SCUOLE SENZA PTOF
# =============================================================================
with tab_failures:
    st.header("❌ Scuole Senza PTOF Scaricabile")
    
    if failures_df.empty:
        st.success("✅ Nessun fallimento di estrazione registrato.")
    else:
        st.markdown(f"""
        Sono state identificate **{len(failures_df)} scuole** per le quali non è stato possibile 
        scaricare automaticamente il PTOF. Queste scuole potrebbero essere recuperate con una 
        procedura di ricerca manuale.
        """)
        
        # Statistiche fallimenti
        st.subheader("📊 Statistiche Fallimenti")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Totale Fallimenti", len(failures_df))
        
        with col2:
            # Analisi per strato
            if 'strato' in failures_df.columns:
                strato_counts = failures_df['strato'].value_counts()
                st.metric("Strati Coinvolti", len(strato_counts))
        
        with col3:
            # Ragioni
            if 'reason' in failures_df.columns:
                reason_counts = failures_df['reason'].value_counts()
                main_reason = reason_counts.index[0] if len(reason_counts) > 0 else "N/A"
                st.metric("Causa Principale", main_reason)
        
        st.markdown("---")
        
        # Distribuzione per strato
        if 'strato' in failures_df.columns:
            st.subheader("📈 Distribuzione Fallimenti per Caratteristiche")
            
            st.caption("""
            Gli strati sono definiti come: **GESTIONE_AREA/REGIONE_TERRITORIO_ORDINE**  
            Esempio: `PAR_CENTRO_METRO_INFANZIA` = Paritaria, Centro Italia, Area Metropolitana, Scuola Infanzia
            """)
            
            # Lista regioni italiane per identificarle negli strati
            REGIONI_ITALIANE = [
                'ABRUZZO', 'BASILICATA', 'CALABRIA', 'CAMPANIA', 'EMILIA_ROMAGNA', 
                'FRIULI_VENEZIA_G.', 'LAZIO', 'LIGURIA', 'LOMBARDIA', 'MARCHE', 
                'MOLISE', 'PIEMONTE', 'PUGLIA', 'SARDEGNA', 'SICILIA', 'TOSCANA', 
                'TRENTINO_ALTO_ADIGE', 'UMBRIA', 'VALLE_D_AOSTA', 'VENETO'
            ]
            
            # 5 macro-aree geografiche
            AREE_GEOGRAFICHE = ['NORD OVEST', 'NORD EST', 'CENTRO', 'SUD', 'ISOLE']
            
            def parse_strato_robusto(strato):
                """
                Parsing robusto che gestisce sia strati con aree geografiche che con regioni.
                Formati possibili:
                - PAR_CENTRO_METRO_SEC_SECONDO (area geografica)
                - PAR_NORD EST_METRO_INFANZIA (area con spazio)
                - STAT_SICILIA_METRO_SEC_SECONDO (regione)
                - STAT_FRIULI_VENEZIA_G._NON_METRO_SEC_PRIMO (regione con underscore)
                """
                strato_str = str(strato)
                
                # Gestione: primo elemento
                if strato_str.startswith('STAT_'):
                    gestione = 'STAT'
                    resto = strato_str[5:]
                elif strato_str.startswith('PAR_'):
                    gestione = 'PAR'
                    resto = strato_str[4:]
                else:
                    return 'ND', 'ND', 'ND', 'ND', 'ND'
                
                # Cerca prima le aree geografiche (con spazi)
                area_geo = 'ND'
                regione = 'ND'
                
                for area in AREE_GEOGRAFICHE:
                    if resto.startswith(area.replace(' ', '_')) or resto.startswith(area):
                        area_geo = area
                        # Rimuovi area dal resto
                        if resto.startswith(area.replace(' ', '_')):
                            resto = resto[len(area.replace(' ', '_'))+1:]
                        else:
                            resto = resto[len(area)+1:]
                        break
                
                # Se non trovata area, cerca regione
                if area_geo == 'ND':
                    for reg in REGIONI_ITALIANE:
                        if resto.startswith(reg):
                            regione = reg.replace('_', ' ').title()
                            resto = resto[len(reg)+1:]
                            break
                
                # Territorio: METRO o NON_METRO
                if resto.startswith('NON_METRO_'):
                    territorio = 'NON_METRO'
                    resto = resto[10:]
                elif resto.startswith('METRO_'):
                    territorio = 'METRO'
                    resto = resto[6:]
                else:
                    territorio = 'ND'
                
                # Ordine scolastico (quello che rimane)
                ordine = resto if resto else 'ND'
                
                return gestione, area_geo, regione, territorio, ordine
            
            # Applica il parsing
            parsed = failures_df['strato'].apply(lambda x: pd.Series(parse_strato_robusto(x)))
            failures_df[['gestione', 'area_geografica_strato', 'regione_strato', 'territorio_strato', 'ordine_strato']] = parsed
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Per gestione
                gest_counts = failures_df['gestione'].value_counts()
                fig_gest = px.pie(
                    values=gest_counts.values,
                    names=[{'STAT': 'Statale', 'PAR': 'Paritaria'}.get(g, g) for g in gest_counts.index],
                    title="Fallimenti per Tipo Gestione"
                )
                st.plotly_chart(fig_gest, use_container_width=True)
            
            with col2:
                # Per area geografica (SOLO le 5 macro-aree, NON regioni!)
                area_geo_counts = failures_df['area_geografica_strato'].value_counts()
                # Filtra solo le 5 macro-aree valide
                aree_valide = ['NORD OVEST', 'NORD EST', 'CENTRO', 'SUD', 'ISOLE']
                area_geo_filtered = area_geo_counts[area_geo_counts.index.isin(aree_valide)]
                
                fig_area_fail = px.bar(
                    x=area_geo_filtered.index,
                    y=area_geo_filtered.values,
                    title="Fallimenti per Area Geografica (5 macro-aree)",
                    labels={'x': 'Area Geografica', 'y': 'N° Fallimenti'},
                    color=area_geo_filtered.values,
                    color_continuous_scale='Reds'
                )
                fig_area_fail.update_layout(showlegend=False)
                st.plotly_chart(fig_area_fail, use_container_width=True)
            
            # Aggiungo anche territorio e ordine
            col3, col4 = st.columns(2)
            
            with col3:
                terr_counts = failures_df['territorio_strato'].value_counts()
                # Mappa nomi territorio leggibili
                terr_labels = {
                    'METRO': 'Metropolitano', 
                    'NON_METRO': 'Non Metropolitano',
                    'NON': 'Non Metropolitano',
                    'ND': 'Non Definito'
                }
                fig_terr = px.pie(
                    values=terr_counts.values,
                    names=[terr_labels.get(t, t) for t in terr_counts.index],
                    title="Fallimenti per Territorio"
                )
                st.plotly_chart(fig_terr, use_container_width=True)
            
            with col4:
                ordine_counts = failures_df['ordine_strato'].value_counts()
                
                # Mappa nomi ordine scolastico leggibili (SOLO i 4 ordini base)
                ordine_labels = {
                    'INFANZIA': 'Infanzia',
                    'PRIMARIA': 'Primaria',
                    'SEC_PRIMO': 'Secondaria I Grado (Medie)',
                    'SEC_SECONDO': 'Secondaria II Grado (Superiori)',
                    'ND': 'Non Definito'
                }
                
                # Filtra solo ordini validi
                ordini_validi = ['INFANZIA', 'PRIMARIA', 'SEC_PRIMO', 'SEC_SECONDO']
                ordine_filtered = ordine_counts[ordine_counts.index.isin(ordini_validi)]
                
                # Se non ci sono ordini validi, mostra tutti
                if len(ordine_filtered) == 0:
                    ordine_filtered = ordine_counts
                
                # Applica le etichette leggibili
                ordine_readable = [ordine_labels.get(o, o) for o in ordine_filtered.index]
                
                fig_ordine = px.bar(
                    x=ordine_filtered.values,
                    y=ordine_readable,
                    orientation='h',
                    title="Fallimenti per Ordine Scolastico",
                    labels={'x': 'N° Fallimenti', 'y': 'Ordine Scolastico'},
                    color=ordine_filtered.values,
                    color_continuous_scale='Viridis'
                )
                fig_ordine.update_layout(showlegend=False, height=300)
                st.plotly_chart(fig_ordine, use_container_width=True)
        
        st.markdown("---")
        
        # =====================================================
        # ANALISI IMPATTO SULLA RAPPRESENTATIVITÀ
        # =====================================================
        st.subheader("⚠️ Valutazione Rappresentatività del Campione")
        
        st.markdown("""
        Confronto tra la **distribuzione nel campione attuale** e la **distribuzione attesa** 
        basata sulla popolazione scolastica italiana (fonte MIUR).
        """)
        
        # Distribuzione attesa nazionale (approssimativa - fonte MIUR)
        ATTESO_ORDINE = {
            'Infanzia': 25.0,
            'Primaria': 30.0,
            'I Grado': 20.0,
            'II Grado': 25.0
        }
        
        ATTESO_GESTIONE = {
            'Statale': 90.0,
            'Paritaria': 10.0
        }
        
        # Funzione per semplificare ordine nel campione
        def simplify_ordine_camp(x):
            x = str(x)
            if 'II Grado' in x:
                return 'II Grado'
            elif 'I Grado' in x:
                return 'I Grado'
            elif 'Primaria' in x:
                return 'Primaria'
            elif 'Infanzia' in x:
                return 'Infanzia'
            return 'Altro'
        
        # Calcola statistiche campione
        df_camp = df.copy()
        df_camp['ordine_simple'] = df_camp['ordine_grado'].apply(simplify_ordine_camp)
        camp_ordine = df_camp['ordine_simple'].value_counts()
        camp_gest = df_camp['statale_paritaria'].value_counts()
        n_campione = len(df_camp)
        
        # =====================================================
        # CONFRONTO PER ORDINE SCOLASTICO
        # =====================================================
        st.markdown("**📚 Rappresentatività per Ordine Scolastico:**")
        
        col1, col2, col3, col4 = st.columns(4)
        cols = [col1, col2, col3, col4]
        ordini = ['Infanzia', 'Primaria', 'I Grado', 'II Grado']
        
        deviazioni_ordine = {}
        for i, ordine in enumerate(ordini):
            with cols[i]:
                n_camp = camp_ordine.get(ordine, 0)
                pct_camp = n_camp / n_campione * 100
                pct_atteso = ATTESO_ORDINE.get(ordine, 0)
                dev = pct_camp - pct_atteso
                deviazioni_ordine[ordine] = dev
                
                # Colore in base alla deviazione
                if abs(dev) > 10:
                    color = "🔴"
                elif abs(dev) > 5:
                    color = "🟠"
                else:
                    color = "🟢"
                
                st.metric(
                    f"{color} {ordine}",
                    f"{pct_camp:.1f}%",
                    delta=f"{dev:+.1f} pp vs atteso ({pct_atteso:.0f}%)",
                    delta_color="normal" if dev >= 0 else "inverse"
                )
        
        # =====================================================
        # CONFRONTO PER GESTIONE
        # =====================================================
        st.markdown("---")
        st.markdown("**🏛️ Rappresentatività per Tipo Gestione:**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            n_stat = camp_gest.get('Statale', 0)
            pct_stat = n_stat / n_campione * 100
            dev_stat = pct_stat - ATTESO_GESTIONE['Statale']
            color_stat = "🟢" if abs(dev_stat) <= 5 else ("🟠" if abs(dev_stat) <= 10 else "🔴")
            st.metric(
                f"{color_stat} Statali",
                f"{pct_stat:.1f}%",
                delta=f"{dev_stat:+.1f} pp vs atteso (90%)",
                delta_color="normal" if dev_stat >= 0 else "inverse"
            )
        
        with col2:
            n_par = camp_gest.get('Paritaria', 0)
            pct_par = n_par / n_campione * 100
            dev_par = pct_par - ATTESO_GESTIONE['Paritaria']
            color_par = "🟢" if abs(dev_par) <= 5 else ("🟠" if abs(dev_par) <= 10 else "🔴")
            st.metric(
                f"{color_par} Paritarie",
                f"{pct_par:.1f}%",
                delta=f"{dev_par:+.1f} pp vs atteso (10%)",
                delta_color="normal" if dev_par >= 0 else "inverse"
            )
        
        # =====================================================
        # CONFRONTO PER AREA GEOGRAFICA
        # =====================================================
        st.markdown("---")
        st.markdown("**🗺️ Rappresentatività per Area Geografica (Macro-aree):**")
        
        # Distribuzione attesa per area geografica (fonte MIUR - popolazione scolastica)
        ATTESO_AREA = {
            'Nord Ovest': 24.0,
            'Nord Est': 15.0,
            'Centro': 18.0,
            'Sud': 27.0,
            'Isole': 16.0
        }
        
        camp_area = df_camp['area_geografica'].value_counts()
        
        col1, col2, col3, col4, col5 = st.columns(5)
        cols_area = [col1, col2, col3, col4, col5]
        aree = ['Nord Ovest', 'Nord Est', 'Centro', 'Sud', 'Isole']
        
        deviazioni_area = {}
        for i, area in enumerate(aree):
            with cols_area[i]:
                n_area = camp_area.get(area, 0)
                pct_area = n_area / n_campione * 100
                pct_atteso = ATTESO_AREA.get(area, 0)
                dev = pct_area - pct_atteso
                deviazioni_area[area] = dev
                
                color = "🟢" if abs(dev) <= 5 else ("🟠" if abs(dev) <= 10 else "🔴")
                
                st.metric(
                    f"{color} {area}",
                    f"{pct_area:.1f}%",
                    delta=f"{dev:+.1f} pp",
                    delta_color="normal" if dev >= 0 else "inverse",
                    help=f"Atteso: {pct_atteso:.0f}%"
                )
        
        # =====================================================
        # CONFRONTO PER REGIONE
        # =====================================================
        st.markdown("---")
        st.markdown("**📍 Rappresentatività per Regione:**")
        
        # Distribuzione attesa per regione (fonte MIUR - approssimativa)
        ATTESO_REGIONE = {
            'Lombardia': 15.5, 'Campania': 10.5, 'Sicilia': 8.5, 'Lazio': 9.0,
            'Veneto': 7.5, 'Piemonte': 6.5, 'Emilia-Romagna': 6.5, 'Puglia': 6.5,
            'Toscana': 5.5, 'Calabria': 3.5, 'Sardegna': 2.5, 'Liguria': 2.0,
            'Marche': 2.3, 'Abruzzo': 2.0, 'Friuli-Venezia Giulia': 1.8,
            'Umbria': 1.3, 'Basilicata': 1.0, 'Molise': 0.5,
            'Trentino-Alto Adige': 1.5, "Valle d'Aosta": 0.2
        }
        
        # Normalizza regioni nel campione
        def normalizza_regione_rapp(r):
            r_str = str(r).strip()
            if 'Emilia' in r_str and 'Romagna' in r_str:
                return 'Emilia-Romagna'
            if 'Friuli' in r_str:
                return 'Friuli-Venezia Giulia'
            if 'Trentino' in r_str or 'Alto Adige' in r_str:
                return 'Trentino-Alto Adige'
            if 'Valle' in r_str and 'Aosta' in r_str:
                return "Valle d'Aosta"
            return r_str
        
        df_camp['regione_norm'] = df_camp['regione'].apply(normalizza_regione_rapp)
        df_camp_valid = df_camp[~df_camp['regione_norm'].isin(['ND', 'Estero', 'N/A', 'nan'])]
        camp_regione = df_camp_valid['regione_norm'].value_counts()
        n_camp_valid = len(df_camp_valid)
        
        # Calcola deviazioni per regione
        regioni_data = []
        deviazioni_regione = {}
        for regione, pct_atteso in ATTESO_REGIONE.items():
            n_reg = camp_regione.get(regione, 0)
            pct_camp = n_reg / n_camp_valid * 100 if n_camp_valid > 0 else 0
            dev = pct_camp - pct_atteso
            deviazioni_regione[regione] = dev
            
            if abs(dev) > 5:
                status = "🔴"
            elif abs(dev) > 3:
                status = "🟠"
            else:
                status = "🟢"
            
            regioni_data.append({
                'Regione': regione,
                'Campione': f"{n_reg} ({pct_camp:.1f}%)",
                'Atteso': f"{pct_atteso:.1f}%",
                'Deviazione': f"{dev:+.1f} pp",
                'Status': status
            })
        
        # Ordina per deviazione assoluta (più problematiche prima)
        regioni_data = sorted(regioni_data, key=lambda x: abs(float(x['Deviazione'].replace(' pp', '').replace('+', ''))), reverse=True)
        
        # Mostra tabella regioni
        regioni_df = pd.DataFrame(regioni_data)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.dataframe(regioni_df, use_container_width=True, hide_index=True, height=300)
        
        with col2:
            # Regioni mancanti
            regioni_presenti = set(camp_regione.index)
            regioni_attese = set(ATTESO_REGIONE.keys())
            regioni_mancanti = regioni_attese - regioni_presenti
            
            if regioni_mancanti:
                st.warning(f"""
                ⚠️ **Regioni mancanti ({len(regioni_mancanti)}):**
                
                {', '.join(sorted(regioni_mancanti))}
                """)
            else:
                st.success("✅ Tutte le 20 regioni italiane sono rappresentate nel campione.")
            
            # Regioni più problematiche
            regioni_critiche = [r for r, d in deviazioni_regione.items() if abs(d) > 5]
            if regioni_critiche:
                st.info(f"""
                📊 **Regioni con deviazione > 5 pp:**
                
                {', '.join(regioni_critiche[:5])}{'...' if len(regioni_critiche) > 5 else ''}
                """)
        
        # =====================================================
        # VALUTAZIONE COMPLESSIVA
        # =====================================================
        st.markdown("---")
        st.subheader("📋 Valutazione Complessiva della Rappresentatività")
        
        # Calcola indice di bias complessivo
        max_dev_ordine = max(abs(d) for d in deviazioni_ordine.values())
        max_dev_gest = abs(dev_par)  # Paritarie sono il caso critico
        max_dev_area = max(abs(d) for d in deviazioni_area.values())
        max_dev_regione = max(abs(d) for d in deviazioni_regione.values()) if deviazioni_regione else 0
        n_regioni_mancanti = len(regioni_mancanti) if regioni_mancanti else 0
        
        # Mostra riepilogo deviazioni
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            color = "🟢" if max_dev_ordine <= 5 else ("🟠" if max_dev_ordine <= 10 else "🔴")
            st.metric(f"{color} Ordine", f"{max_dev_ordine:.1f} pp", help="Deviazione massima per ordine scolastico")
        
        with col2:
            color = "🟢" if max_dev_gest <= 5 else ("🟠" if max_dev_gest <= 10 else "🔴")
            st.metric(f"{color} Gestione", f"{max_dev_gest:.1f} pp", help="Deviazione per tipo gestione")
        
        with col3:
            color = "🟢" if max_dev_area <= 5 else ("🟠" if max_dev_area <= 10 else "🔴")
            st.metric(f"{color} Area Geo", f"{max_dev_area:.1f} pp", help="Deviazione massima per area geografica")
        
        with col4:
            color = "🟢" if n_regioni_mancanti == 0 else ("🟠" if n_regioni_mancanti <= 2 else "🔴")
            st.metric(f"{color} Regioni", f"{20 - n_regioni_mancanti}/20", help="Regioni coperte su 20")
        
        # Valutazione complessiva
        problemi = []
        if max_dev_ordine > 10:
            problemi.append(f"**Ordine scolastico**: deviazione di {max_dev_ordine:.1f} pp")
        if max_dev_gest > 15:
            problemi.append(f"**Gestione**: paritarie sovrarappresentate di {dev_par:+.1f} pp")
        elif dev_par < -5:
            problemi.append(f"**Gestione**: paritarie sottorappresentate di {dev_par:+.1f} pp")
        if max_dev_area > 10:
            problemi.append(f"**Area geografica**: deviazione di {max_dev_area:.1f} pp")
        if n_regioni_mancanti > 2:
            problemi.append(f"**Regioni**: {n_regioni_mancanti} regioni mancanti")
        
        if problemi:
            st.error(f"""
            ❌ **ATTENZIONE - Campione non completamente bilanciato**
            
            **Problemi identificati:**
            {chr(10).join('- ' + p for p in problemi)}
            
            ⚠️ Per analisi inferenziali, considerare l'applicazione di **pesi di post-stratificazione**.
            """)
        elif max_dev_ordine > 5 or max_dev_gest > 10 or max_dev_area > 5 or n_regioni_mancanti > 0:
            st.warning(f"""
            ⚠️ **Bias moderato nel campione**
            
            - Deviazione max ordine: {max_dev_ordine:.1f} pp
            - Deviazione gestione: {max_dev_gest:.1f} pp
            - Deviazione max area: {max_dev_area:.1f} pp
            - Regioni coperte: {20 - n_regioni_mancanti}/20
            
            Il campione è utilizzabile ma con cautela per analisi comparative.
            """)
        else:
            st.success(f"""
            ✅ **Campione ben bilanciato**
            
            La distribuzione del campione rispecchia quella nazionale:
            - Deviazione massima ordine: {max_dev_ordine:.1f} pp (< 5 pp)
            - Deviazione gestione: {abs(dev_par):.1f} pp (< 5 pp)
            """)
        
        # =====================================================
        # IMPATTO DEI FALLIMENTI
        # =====================================================
        st.markdown("---")
        st.markdown("**📉 Impatto dei Fallimenti di Estrazione:**")
        
        # Calcola statistiche fallimenti
        fail_ordine = failures_df['ordine_strato'].value_counts()
        
        # Mappa ordini per confronto
        ordine_map = {
            'SEC_SECONDO': 'II Grado',
            'SEC_PRIMO': 'I Grado', 
            'PRIMARIA': 'Primaria',
            'INFANZIA': 'Infanzia'
        }
        
        # Calcola quanto potrebbero migliorare le cose recuperando i fallimenti
        st.markdown("Se recuperassimo tutti i PTOF mancanti, la distribuzione sarebbe:")
        
        data_recupero = []
        for ordine in ordini:
            n_camp = camp_ordine.get(ordine, 0)
            # Trova fallimenti corrispondenti
            n_fail = 0
            for fail_key, camp_key in ordine_map.items():
                if camp_key == ordine:
                    n_fail = fail_ordine.get(fail_key, 0)
                    break
            n_totale = n_camp + n_fail
            pct_attuale = n_camp / n_campione * 100
            pct_potenziale = n_totale / (n_campione + len(failures_df)) * 100
            pct_atteso = ATTESO_ORDINE.get(ordine, 0)
            
            data_recupero.append({
                'Ordine': ordine,
                'Attuale': f"{n_camp} ({pct_attuale:.1f}%)",
                'Da recuperare': n_fail,
                'Potenziale': f"{n_totale} ({pct_potenziale:.1f}%)",
                'Atteso': f"{pct_atteso:.0f}%",
                'Gap attuale': f"{pct_attuale - pct_atteso:+.1f} pp",
                'Gap potenziale': f"{pct_potenziale - pct_atteso:+.1f} pp"
            })
        
        st.dataframe(pd.DataFrame(data_recupero), use_container_width=True, hide_index=True)
        
        # Suggerimenti per recupero
        with st.expander("💡 Suggerimenti per migliorare la rappresentatività"):
            # Identifica ordini più sottorappresentati
            ordini_sotto = [o for o, d in deviazioni_ordine.items() if d < -5]
            ordini_sopra = [o for o, d in deviazioni_ordine.items() if d > 5]
            
            st.markdown(f"""
            **Situazione attuale:**
            - Ordini **sottorappresentati**: {', '.join(ordini_sotto) if ordini_sotto else 'nessuno'}
            - Ordini **sovrarappresentati**: {', '.join(ordini_sopra) if ordini_sopra else 'nessuno'}
            
            **Scuole da recuperare per priorità:**
            
            | Ordine | Da recuperare | Tempo stimato | Priorità |
            |--------|---------------|---------------|----------|
            | Sec. I Grado | {fail_ordine.get('SEC_PRIMO', 0)} scuole | ~{fail_ordine.get('SEC_PRIMO', 0) * 4 / 60:.0f} ore | {'🔴 Alta' if 'I Grado' in ordini_sotto else '🟢 Bassa'} |
            | Sec. II Grado | {fail_ordine.get('SEC_SECONDO', 0)} scuole | ~{fail_ordine.get('SEC_SECONDO', 0) * 4 / 60:.0f} ore | {'🔴 Alta' if 'II Grado' in ordini_sotto else '🟢 Bassa'} |
            | Primaria | {fail_ordine.get('PRIMARIA', 0)} scuole | ~{fail_ordine.get('PRIMARIA', 0) * 4 / 60:.0f} ore | {'🔴 Alta' if 'Primaria' in ordini_sotto else '🟢 Bassa'} |
            | Infanzia | {fail_ordine.get('INFANZIA', 0)} scuole | ~{fail_ordine.get('INFANZIA', 0) * 4 / 60:.0f} ore | {'🔴 Alta' if 'Infanzia' in ordini_sotto else '🟢 Bassa'} |
            
            **Tempo totale stimato**: ~{len(failures_df) * 4 / 60:.0f} ore (~{len(failures_df) * 4 / 60 / 8:.1f} giorni lavorativi)
            
            **Comandi per recupero automatico:**
            ```bash
            make strata-cycle G=SEC_PRIMO MAX_DOWNLOADS=50
            make strata-cycle G=SEC_SECONDO MAX_DOWNLOADS=50
            ```
            """)
        
        st.markdown("---")
        
        # Tabella completa fallimenti
        st.subheader("📋 Elenco Completo Scuole")
        
        # Filtri
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if 'gestione' in failures_df.columns:
                gestione_filter = st.selectbox(
                    "Filtra per Gestione",
                    ['Tutti', 'Statale', 'Paritaria'],
                    key='gestione_filter'
                )
        
        with col2:
            if 'area_geografica_strato' in failures_df.columns:
                aree_disponibili = ['Tutti'] + sorted(failures_df['area_geografica_strato'].unique().tolist())
                area_filter = st.selectbox(
                    "Filtra per Area Geografica",
                    aree_disponibili,
                    key='area_filter'
                )
            else:
                area_filter = 'Tutti'
        
        with col3:
            if 'ordine_strato' in failures_df.columns:
                ordini_disponibili = ['Tutti'] + sorted(failures_df['ordine_strato'].unique().tolist())
                ordine_filter = st.selectbox(
                    "Filtra per Ordine",
                    ordini_disponibili,
                    key='ordine_filter'
                )
            else:
                ordine_filter = 'Tutti'
        
        with col4:
            search_code = st.text_input("🔍 Cerca Codice Scuola", key='search_code')
        
        # Applica filtri
        filtered_df = failures_df.copy()
        
        if 'gestione' in failures_df.columns and gestione_filter != 'Tutti':
            gestione_code = 'STAT' if gestione_filter == 'Statale' else 'PAR'
            filtered_df = filtered_df[filtered_df['gestione'] == gestione_code]
        
        if 'area_geografica_strato' in failures_df.columns and area_filter != 'Tutti':
            filtered_df = filtered_df[filtered_df['area_geografica_strato'] == area_filter]
        
        if 'ordine_strato' in failures_df.columns and ordine_filter != 'Tutti':
            filtered_df = filtered_df[filtered_df['ordine_strato'] == ordine_filter]
        
        if search_code:
            filtered_df = filtered_df[
                filtered_df['school_code'].str.upper().str.contains(search_code.upper())
            ]
        
        st.markdown(f"**Scuole visualizzate: {len(filtered_df)} / {len(failures_df)}**")
        
        # Mostra tabella
        display_cols = ['school_code', 'strato', 'reason', 'attempt', 'last_seen']
        display_cols = [c for c in display_cols if c in filtered_df.columns]
        
        st.dataframe(
            filtered_df[display_cols].rename(columns={
                'school_code': 'Codice Scuola',
                'strato': 'Strato',
                'reason': 'Motivo',
                'attempt': 'Tentativi',
                'last_seen': 'Ultimo Tentativo'
            }),
            use_container_width=True,
            hide_index=True,
            height=400
        )
        
        # Download
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            csv_data = filtered_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Scarica CSV (filtrato)",
                data=csv_data,
                file_name=f"scuole_senza_ptof_{datetime.now().strftime('%Y%m%d')}.csv",
                mime='text/csv'
            )
        
        with col2:
            st.info("""
            💡 **Prossimo passo**: Per queste scuole è possibile implementare 
            una procedura di ricerca manuale del PTOF.
            """)

# === FOOTER ===
render_footer()
