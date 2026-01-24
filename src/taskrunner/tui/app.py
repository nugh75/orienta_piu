"""
TUI principale per PTOF Task Runner con Textual.
"""

import sys
from pathlib import Path
from typing import Optional

try:
    from textual.app import App, ComposeResult
    from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
    from textual.widgets import Header, Footer, Static, ListView, ListItem, RichLog, Button, Input, Label
    from textual.binding import Binding
    from textual.screen import ModalScreen
    from textual import on
    from rich.text import Text
except ImportError:
    print("Textual non installato. Esegui: pip install textual rich")
    sys.exit(1)

# Aggiungi path progetto
PROJECT_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from src.taskrunner.core.task_manager import TaskManager, get_task_manager
from src.taskrunner.core.command_registry import CommandRegistry
from src.taskrunner.models.task import Task, TaskStatus


class ParameterScreen(ModalScreen):
    """Screen modale per inserire parametri del comando."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "submit", "Submit"),
    ]

    def __init__(self, command_name: str, variables: list):
        super().__init__()
        self.command_name = command_name
        self.variables = variables
        self.inputs = {}

    def compose(self) -> ComposeResult:
        with Vertical(id="param-dialog"):
            yield Label(f"Parametri per: {self.command_name}", id="param-title")
            for var in self.variables:
                with Horizontal(classes="param-row"):
                    yield Label(f"{var}:", classes="param-label")
                    inp = Input(placeholder=f"Valore per {var}", id=f"input-{var}")
                    self.inputs[var] = inp
                    yield inp
            with Horizontal(id="param-buttons"):
                yield Button("Avvia", variant="primary", id="btn-submit")
                yield Button("Annulla", variant="default", id="btn-cancel")

    @on(Button.Pressed, "#btn-submit")
    def on_submit(self):
        variables = {}
        for var, inp in self.inputs.items():
            if inp.value:
                variables[var] = inp.value
        self.dismiss(variables)

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel(self):
        self.dismiss(None)

    def action_cancel(self):
        self.dismiss(None)

    def action_submit(self):
        self.on_submit()


class TaskRunnerTUI(App):
    """TUI principale per PTOF Task Runner."""

    CSS = """
    #main-container {
        layout: horizontal;
        height: 100%;
    }

    #left-panel {
        width: 35%;
        border: solid green;
        padding: 0 1;
    }

    #right-panel {
        width: 65%;
        border: solid blue;
        padding: 0 1;
    }

    .panel-title {
        text-style: bold;
        background: $surface;
        padding: 0 1;
        margin-bottom: 1;
    }

    #command-list {
        height: 100%;
    }

    #output-log {
        height: 100%;
        scrollbar-gutter: stable;
    }

    .category-header {
        text-style: bold;
        color: $text-muted;
        padding: 0 1;
    }

    .command-item {
        padding: 0 2;
    }

    .command-item:hover {
        background: $boost;
    }

    .command-item.--highlight {
        background: $accent;
    }

    #status-bar {
        dock: bottom;
        height: 1;
        background: $surface;
        padding: 0 1;
    }

    #param-dialog {
        width: 60;
        height: auto;
        padding: 1 2;
        background: $surface;
        border: solid $primary;
    }

    #param-title {
        text-style: bold;
        margin-bottom: 1;
    }

    .param-row {
        height: 3;
        margin-bottom: 1;
    }

    .param-label {
        width: 20;
    }

    #param-buttons {
        margin-top: 1;
        height: 3;
    }

    #param-buttons Button {
        margin-right: 1;
    }

    .long-running {
        color: $warning;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "run_selected", "Run"),
        Binding("s", "stop_task", "Stop"),
        Binding("k", "kill_task", "Kill"),
        Binding("c", "clear_log", "Clear Log"),
        Binding("t", "show_tasks", "Tasks"),
        Binding("?", "show_help", "Help"),
    ]

    def __init__(self):
        super().__init__()
        self.task_manager = get_task_manager()
        self.registry = CommandRegistry()
        self.selected_command: Optional[str] = None
        self.current_task: Optional[Task] = None
        self._command_items = {}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Horizontal(id="main-container"):
            with Vertical(id="left-panel"):
                yield Static("COMANDI MAKE", classes="panel-title")
                yield ListView(id="command-list")

            with Vertical(id="right-panel"):
                yield Static("OUTPUT", classes="panel-title")
                yield RichLog(id="output-log", highlight=True, markup=True, wrap=True)

        yield Static("Pronto. Seleziona un comando e premi [R] per avviare.", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        """Popola lista comandi al mount."""
        command_list = self.query_one("#command-list", ListView)

        for category in self.registry.get_categories():
            # Header categoria
            header = ListItem(Static(f"[bold cyan]{category}[/bold cyan]"))
            header.disabled = True
            command_list.append(header)

            # Comandi della categoria
            for cmd in self.registry.get_by_category(category):
                label = f"  {cmd.name}"
                if cmd.is_long_running:
                    label = f"  [yellow]{cmd.name}[/yellow]"
                item = ListItem(Static(label), id=f"cmd-{cmd.name}")
                self._command_items[cmd.name] = item
                command_list.append(item)

        # Subscribe agli eventi del task manager
        self.task_manager.subscribe(self._on_task_event)

        # Mostra task attivi
        self._update_status()

    def _on_task_event(self, event: str, task: Task):
        """Handler per eventi task."""
        # Usa call_from_thread per thread safety
        self.call_from_thread(self._handle_task_event, event, task)

    def _handle_task_event(self, event: str, task: Task):
        """Handler thread-safe per eventi task."""
        output_log = self.query_one("#output-log", RichLog)

        if event == "started":
            output_log.write(f"[green]>>> Task {task.id} avviato: {task.command}[/green]")
            self._update_status()

        elif event == "output":
            # Leggi ultima riga
            lines = self.task_manager.get_task_output(task.id, tail_lines=1)
            for line in lines:
                output_log.write(line)

        elif event == "completed":
            if task.exit_code == 0:
                output_log.write(f"[green]>>> Task {task.id} completato con successo[/green]")
            else:
                output_log.write(f"[red]>>> Task {task.id} fallito (exit: {task.exit_code})[/red]")
            self._update_status()

        elif event == "stopped":
            output_log.write(f"[yellow]>>> Task {task.id} fermato[/yellow]")
            self._update_status()

    def _update_status(self):
        """Aggiorna la barra di stato."""
        status_bar = self.query_one("#status-bar", Static)
        active = self.task_manager.get_active_tasks()

        if not active:
            if self.selected_command:
                status_bar.update(f"Selezionato: {self.selected_command} | [R] Avvia")
            else:
                status_bar.update("Seleziona un comando e premi [R] per avviare")
        else:
            names = ", ".join(t.command for t in active[:3])
            status_bar.update(f"[green]{len(active)} task attivi:[/green] {names} | [S] Stop [K] Kill")

    @on(ListView.Selected, "#command-list")
    def on_command_selected(self, event: ListView.Selected):
        """Quando un comando viene selezionato."""
        item_id = event.item.id
        if item_id and item_id.startswith("cmd-"):
            self.selected_command = item_id[4:]
            self._update_status()

    def action_run_selected(self) -> None:
        """Avvia il comando selezionato."""
        if not self.selected_command:
            self.notify("Seleziona prima un comando", severity="warning")
            return

        command = self.registry.get_command(self.selected_command)
        if not command:
            return

        if command.variables:
            # Mostra dialog per parametri
            def on_params(variables):
                if variables is not None:
                    self._start_task(self.selected_command, variables)

            self.push_screen(ParameterScreen(command.name, command.variables), on_params)
        else:
            self._start_task(self.selected_command, {})

    def _start_task(self, command: str, variables: dict):
        """Avvia effettivamente il task."""
        output_log = self.query_one("#output-log", RichLog)
        output_log.clear()

        cmd_str = f"make {command}"
        for k, v in variables.items():
            if v:
                cmd_str += f" {k}={v}"

        output_log.write(f"[bold green]>>> Avvio: {cmd_str}[/bold green]")
        output_log.write("-" * 50)

        task = self.task_manager.create_task(command, variables)
        self.current_task = task

        def on_output(line: str):
            self.call_from_thread(output_log.write, line)

        self.task_manager.start_task(task.id, on_output=on_output)
        self.notify(f"Task {task.id} avviato")

    def action_stop_task(self) -> None:
        """Stop graceful del task corrente."""
        if self.current_task and self.current_task.is_running:
            self.task_manager.stop_task(self.current_task.id, force=False)
            self.notify("Stop richiesto (graceful)")
        else:
            # Ferma il primo task attivo
            active = self.task_manager.get_active_tasks()
            if active:
                self.task_manager.stop_task(active[0].id, force=False)
                self.notify(f"Stop task {active[0].id}")
            else:
                self.notify("Nessun task attivo", severity="warning")

    def action_kill_task(self) -> None:
        """Kill forzato del task corrente."""
        if self.current_task and self.current_task.is_running:
            self.task_manager.stop_task(self.current_task.id, force=True)
            self.notify("Kill forzato inviato")
        else:
            active = self.task_manager.get_active_tasks()
            if active:
                self.task_manager.stop_task(active[0].id, force=True)
                self.notify(f"Kill task {active[0].id}")
            else:
                self.notify("Nessun task attivo", severity="warning")

    def action_clear_log(self) -> None:
        """Pulisce il log output."""
        output_log = self.query_one("#output-log", RichLog)
        output_log.clear()

    def action_show_tasks(self) -> None:
        """Mostra tutti i task."""
        output_log = self.query_one("#output-log", RichLog)
        output_log.clear()
        output_log.write("[bold]Task recenti:[/bold]")
        output_log.write("-" * 50)

        for task in self.task_manager.get_recent_tasks(20):
            status_color = {
                TaskStatus.RUNNING: "green",
                TaskStatus.COMPLETED: "blue",
                TaskStatus.FAILED: "red",
                TaskStatus.CANCELLED: "yellow",
                TaskStatus.PENDING: "dim",
            }.get(task.status, "white")

            line = f"[{status_color}]{task.id}[/{status_color}] {task.command} - {task.status.value}"
            if task.duration:
                line += f" ({task.duration:.1f}s)"
            output_log.write(line)

    def action_show_help(self) -> None:
        """Mostra help."""
        output_log = self.query_one("#output-log", RichLog)
        output_log.clear()
        output_log.write("[bold]PTOF Task Runner - Help[/bold]")
        output_log.write("-" * 50)
        output_log.write("")
        output_log.write("[bold]Keybindings:[/bold]")
        output_log.write("  [R] - Avvia comando selezionato")
        output_log.write("  [S] - Stop graceful (SIGTERM)")
        output_log.write("  [K] - Kill forzato (SIGKILL)")
        output_log.write("  [C] - Pulisci log")
        output_log.write("  [T] - Mostra task recenti")
        output_log.write("  [Q] - Esci")
        output_log.write("")
        output_log.write("[bold]Comandi evidenziati in giallo sono long-running.[/bold]")


def main():
    """Entry point per la TUI."""
    app = TaskRunnerTUI()
    app.run()


if __name__ == "__main__":
    main()
