#!/usr/bin/env python3
import customtkinter as ctk
import subprocess
import threading
import queue
import os
import sys
import signal
import time

# Configuration
ctk.set_appearance_mode("Dark")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

class LIsteApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window setup
        self.title("LIste Control Panel")
        self.geometry("1100x700")

        # Grid layout (2 columns: Sidebar, Main)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # State variables
        self.process = None
        self.queue = queue.Queue()
        self.is_running = False
        
        # --- SIDEBAR ---
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(10, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="LIste\nControl Panel", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # Settings: N Schools
        self.n_schools_label = ctk.CTkLabel(self.sidebar_frame, text="N. Scuole (per strato):", anchor="w")
        self.n_schools_label.grid(row=1, column=0, padx=20, pady=(10, 0), sticky="w")
        self.n_schools_entry = ctk.CTkEntry(self.sidebar_frame)
        self.n_schools_entry.grid(row=2, column=0, padx=20, pady=(0, 10))
        self.n_schools_entry.insert(0, "5")

        # Settings: Model
        self.model_label = ctk.CTkLabel(self.sidebar_frame, text="Modello LLM:", anchor="w")
        self.model_label.grid(row=3, column=0, padx=20, pady=(10, 0), sticky="w")
        self.model_option = ctk.CTkOptionMenu(self.sidebar_frame, values=[
            "meta-llama/llama-3.3-70b-instruct:free",
            "google/gemini-2.0-flash-exp:free",
            "mistralai/mistral-7b-instruct:free",
            "openai/gpt-4o-mini"
        ])
        self.model_option.grid(row=4, column=0, padx=20, pady=(0, 10))

        # Settings: API Key (Optional visual placeholder)
        self.api_label = ctk.CTkLabel(self.sidebar_frame, text="API Key (opzionale):", anchor="w")
        self.api_label.grid(row=5, column=0, padx=20, pady=(10, 0), sticky="w")
        self.api_entry = ctk.CTkEntry(self.sidebar_frame, show="*")
        self.api_entry.grid(row=6, column=0, padx=20, pady=(0, 10))
        
        # Save Config Button (Mock)
        self.save_btn = ctk.CTkButton(self.sidebar_frame, text="Salva Config", command=self.save_config)
        self.save_btn.grid(row=7, column=0, padx=20, pady=20)

        # --- MAIN AREA ---
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_rowconfigure(3, weight=1) # Console expands
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(2, weight=1)

        # Section 1: Download
        self.create_section_frame("📥 Download PTOF", 0, [
            ("Download Sample (5/strato)", lambda: self.run_command(["make", "download-sample"])),
            ("Download Stratificato (N)", lambda: self.run_command(["make", "download-strato", f"N={self.n_schools_entry.get()}"])),
            ("Download Statali", lambda: self.run_command(["make", "download-statali"]))
        ])

        # Section 2: Analisi
        self.create_section_frame("🤖 Analisi & AI", 1, [
            ("Avvia Workflow Completo", lambda: self.run_command(["make", "run"])),
            ("Review Scores (LLM)", lambda: self.run_command(["make", "review-scores", f"MODEL={self.model_option.get()}"])),
            ("Backfill Metadati", lambda: self.run_command(["make", "backfill"]))
        ])

        # Section 3: Dashboard & Dati
        self.create_section_frame("📊 Dashboard & Dati", 2, [
            ("Rigenera CSV + Geo", lambda: self.run_command(["make", "csv"])),
            ("Avvia Dashboard", lambda: self.run_command(["make", "dashboard"])),
            ("Pulisce Cache", lambda: self.run_command(["make", "clean"]))
        ])

        # --- CONSOLE ---
        self.console_label = ctk.CTkLabel(self.main_frame, text="Console Output:", font=ctk.CTkFont(size=14, weight="bold"))
        self.console_label.grid(row=2, column=0, sticky="w", pady=(20, 5))

        self.console_textbox = ctk.CTkTextbox(self.main_frame, width=800, height=300, font=("Courier", 12))
        self.console_textbox.grid(row=3, column=0, columnspan=3, sticky="nsew")
        
        # Control Buttons (Stop/Clear)
        self.controls_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.controls_frame.grid(row=4, column=0, columnspan=3, sticky="ew", pady=10)
        
        self.stop_btn = ctk.CTkButton(self.controls_frame, text="🛑 STOP", fg_color="red", hover_color="darkred", command=self.stop_process, state="disabled")
        self.stop_btn.pack(side="right", padx=10)
        
        self.clear_btn = ctk.CTkButton(self.controls_frame, text="🧹 Pulisci Console", fg_color="gray", hover_color="darkgray", command=self.clear_console)
        self.clear_btn.pack(side="right")

        # Start queue checker
        self.after(100, self.check_queue)

    def create_section_frame(self, title, col_idx, buttons):
        frame = ctk.CTkFrame(self.main_frame)
        frame.grid(row=0, column=col_idx, sticky="nsew", padx=10, pady=10)
        
        label = ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(size=16, weight="bold"))
        label.pack(pady=10, padx=10)
        
        for btn_text, btn_cmd in buttons:
            btn = ctk.CTkButton(frame, text=btn_text, command=btn_cmd)
            btn.pack(pady=5, padx=10, fill="x")

    def save_config(self):
        # Mock save
        self.log_message("Configurazione salvata (simulazione).")

    def log_message(self, msg):
        self.console_textbox.insert("end", str(msg) + "\n")
        self.console_textbox.see("end")

    def clear_console(self):
        self.console_textbox.delete("1.0", "end")

    def run_command(self, command_list):
        if self.is_running:
            self.log_message("⚠️ Un processo è già in esecuzione. Attendere o premere STOP.")
            return

        self.is_running = True
        self.stop_btn.configure(state="normal")
        self.log_message(f"\n🚀 Esecuzione: {' '.join(command_list)}\n" + "-"*40)

        # Start thread
        thread = threading.Thread(target=self._execute_thread, args=(command_list,))
        thread.daemon = True
        thread.start()

    def _execute_thread(self, command_list):
        try:
            # Use unbuffered output for real-time logging
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            
            self.process = subprocess.Popen(
                command_list,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                env=env,
                preexec_fn=os.setsid # Create new process group for clean kill
            )

            for line in self.process.stdout:
                self.queue.put(line)

            self.process.wait()
            return_code = self.process.returncode
            self.queue.put(f"\n✅ Processo terminato con codice: {return_code}\n")

        except Exception as e:
            self.queue.put(f"\n❌ Errore esecuzione: {str(e)}\n")
        finally:
            self.process = None
            self.queue.put("DONE")

    def check_queue(self):
        try:
            while True:
                msg = self.queue.get_nowait()
                if msg == "DONE":
                    self.is_running = False
                    self.stop_btn.configure(state="disabled")
                else:
                    self.console_textbox.insert("end", msg)
                    self.console_textbox.see("end")
        except queue.Empty:
            pass
        
        self.after(100, self.check_queue)

    def stop_process(self):
        if self.process:
            self.log_message("\n🛑 Invio segnale di stop...")
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            except Exception as e:
                self.log_message(f"Errore nello stop: {e}")

if __name__ == "__main__":
    app = LIsteApp()
    app.mainloop()
