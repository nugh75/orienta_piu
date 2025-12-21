import streamlit as st
import os
import time
from src.utils.backup_system import (
    create_backup, list_backups, restore_backup, 
    create_backup_zip, restore_from_zip, delete_backup
)

st.set_page_config(page_title="Backup e Ripristino", page_icon="🛡️", layout="wide")

st.title("🛡️ Centro Backup e Ripristino")
st.markdown("""
Qui puoi gestire i backup dei dati e delle analisi.
Puoi creare copie di sicurezza, ripristinare versioni precedenti o scaricare i dati per archivio.
""")

# --- Create & Upload Section ---
col_create, col_upload = st.columns([1, 1])

with col_create:
    st.subheader("💾 Nuovo Backup")
    st.markdown("Crea una copia istantanea dello stato attuale (CSV + JSON Analysis).")
    if st.button("Crea Backup Ora", type="primary"):
        try:
            path, count = create_backup(description="manual_user")
            st.success(f"✅ Backup creato con successo! ({count} files)")
            st.code(os.path.basename(path))
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"Errore durante la creazione del backup: {e}")

with col_upload:
    st.subheader("📥 Importa Backup (ZIP)")
    uploaded_file = st.file_uploader("Carica un file ZIP di backup", type="zip")
    if uploaded_file:
        if st.button("Importa Backup"):
            try:
                backup_name = restore_from_zip(uploaded_file)
                st.success(f"✅ Backup importato: {backup_name}")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Errore importazione: {e}")

st.markdown("---")

# --- Existing Backups List ---
st.subheader("🗄️ Storico Backup")

backups = list_backups()

if not backups:
    st.info("Nessun backup trovato.")
else:
    for backup_name in backups:
        with st.expander(f"📦 {backup_name}", expanded=False):
            c1, c2, c3 = st.columns([2, 2, 1])
            
            with c1:
                st.markdown(f"**Cartella:** `{backup_name}`")
                
            with c2:
                # Restore
                if st.button("🔄 Ripristina questo stato", key=f"rest_{backup_name}"):
                    with st.spinner("Ripristino in corso..."):
                        res = restore_backup(backup_name)
                    if res['success']:
                        st.success(f"✅ Ripristino completato! ({res['files_restored']} files)")
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error(f"❌ Errore ripristino: {res['error']}")
            
            with c3:
                # Download
                if st.button("⬇️ ZIP", key=f"zip_{backup_name}"):
                    zip_path = create_backup_zip(backup_name)
                    if zip_path:
                        with open(zip_path, "rb") as f:
                            st.download_button(
                                label="Scarica Ora",
                                data=f,
                                file_name=os.path.basename(zip_path),
                                mime="application/zip",
                                key=f"down_{backup_name}"
                            )
                        # Clean up zip after reading? 
                        # Streamlit reruns usually handle cleanup or we leave it.
                        # For now we leave the zip file.
                    else:
                        st.error("Errore creazione ZIP")
                
                # Delete
                if st.button("🗑️ Elimina", key=f"del_{backup_name}"):
                    if delete_backup(backup_name):
                        st.success("Cancellato.")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Errore cancellazione.")

st.sidebar.info("ℹ️ Il ripristino sovrascrive i dati attuali. Assicurati di fare prima un backup se necessario.")
