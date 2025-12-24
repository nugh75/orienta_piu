from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, Button, Input, Label, Select, Log, Static
from textual.worker import Worker, WorkerState
import subprocess
import os
import signal

class LIsteLauncher(App):
    CSS = """
    Screen {
        layout: grid;
        grid-size: 2;
        grid-columns: 30% 70%;
    }
    #sidebar {
        height: 100%;
        background: $panel;
        border-right: vkey $accent;
        padding: 1;
    }
    #main {
        height: 100%;
        padding: 1;
    }
    .section-title {
        text-align: center;
        text-style: bold;
        margin-top: 1;
        margin-bottom: 1;
        background: $accent;
        color: $text;
    }
    Button {
        width: 100%;
        margin-bottom: 1;
    }
    Log {
        border: solid $accent;
        height: 1fr;
    }
    #controls {
        height: auto;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        # Sidebar
        with Vertical(id="sidebar"):
            yield Label("⚙️ Configurazione", classes="section-title")
            yield Label("N. Scuole:")
            yield Input(value="5", id="n_schools")
            yield Label("Modello LLM:")
            yield Select.from_values([
                "meta-llama/llama-3.3-70b-instruct:free",
                "google/gemini-2.0-flash-exp:free",
                "mistralai/mistral-7b-instruct:free",
                "openai/gpt-4o-mini"
            ], value="meta-llama/llama-3.3-70b-instruct:free", id="model_select")
            
            yield Label("📥 Download", classes="section-title")
            yield Button("Download Sample (5)", id="btn_sample")
            yield Button("Download Stratificato", id="btn_strato")
            yield Button("Download Statali", id="btn_statali")
            
            yield Label("🤖 Analisi", classes="section-title")
            yield Button("Avvia Workflow", id="btn_run")
            yield Button("Review Scores", id="btn_review")
            yield Button("Backfill", id="btn_backfill")
            
            yield Label("📊 Dati", classes="section-title")
            yield Button("Rigenera CSV + Geo", id="btn_csv")
            yield Button("Avvia Dashboard", id="btn_dash")
            yield Button("Pulisci Cache", id="btn_clean")

        # Main Area
        with Vertical(id="main"):
            yield Label("🖥️ Console Output", classes="section-title")
            yield Log(id="console_log", highlight=True)
            with Horizontal(id="controls"):
                yield Button("🛑 STOP", id="btn_stop", variant="error", disabled=True)
                yield Button("🧹 Clear", id="btn_clear")

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        
        if btn_id == "btn_clear":
            self.query_one(Log).clear()
            return
            
        if btn_id == "btn_stop":
            self.stop_process()
            return

        # Command mapping
        n_val = self.query_one("#n_schools", Input).value
        model_val = self.query_one("#model_select", Select).value
        
        commands = {
            "btn_sample": ["make", "download-sample"],
            "btn_strato": ["make", "download-strato", f"N={n_val}"],
            "btn_statali": ["make", "download-statali"],
            "btn_run": ["make", "run"],
            "btn_review": ["make", "review-scores", f"MODEL={model_val}"],
            "btn_backfill": ["make", "backfill"],
            "btn_csv": ["make", "csv"],
            "btn_dash": ["make", "dashboard"],
            "btn_clean": ["make", "clean"]
        }
        
        if btn_id in commands:
            self.run_command(commands[btn_id])

    def run_command(self, cmd_list):
        log = self.query_one(Log)
        log.write(f"\n🚀 Running: {' '.join(cmd_list)}\n")
        self.query_one("#btn_stop").disabled = False
        self.run_worker(self._subprocess_worker_sync(cmd_list), exclusive=True, group="cmd", thread=True)

    def _subprocess_worker_sync(self, cmd_list):
        log = self.query_one(Log)
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        try:
            self.process = subprocess.Popen(
                cmd_list,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env,
                preexec_fn=os.setsid
            )
            
            while True:
                line = self.process.stdout.readline()
                if not line and self.process.poll() is not None:
                    break
                if line:
                    self.call_from_thread(log.write, line.strip())
            
            rc = self.process.poll()
            self.call_from_thread(log.write, f"\n✅ Process finished with code {rc}\n")
            
        except Exception as e:
            self.call_from_thread(log.write, f"\n❌ Error: {e}\n")
        finally:
            self.process = None
            self.call_from_thread(self.update_stop_button, True)

    def update_stop_button(self, disabled):
        self.query_one("#btn_stop").disabled = disabled

    def stop_process(self):
        if hasattr(self, 'process') and self.process:
            self.query_one(Log).write("\n🛑 Stopping process...\n")
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            except Exception as e:
                self.query_one(Log).write(f"Error stopping: {e}")

if __name__ == "__main__":
    app = LIsteLauncher()
    app.run()
