"""
Task Manager - Gestione centralizzata dei task.
"""

import json
import atexit
import logging
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from threading import Lock
from datetime import datetime

from ..models.task import Task, TaskStatus
from .process_runner import ProcessRunner
from .log_streamer import LogStreamer


logger = logging.getLogger(__name__)


class TaskManager:
    """
    Singleton per gestione centralizzata dei task.

    Gestisce:
    - Creazione e avvio task
    - Persistenza stato su file
    - Notifiche eventi per UI
    - Stop/kill task
    """

    _instance: Optional["TaskManager"] = None
    _lock = Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        state_file: Optional[Path] = None,
        logs_dir: Optional[Path] = None,
        base_dir: Optional[Path] = None
    ):
        if hasattr(self, '_initialized') and self._initialized:
            return

        # Default paths
        project_root = Path(__file__).parents[3]
        self.state_file = state_file or project_root / "data" / "taskrunner_state.json"
        self.logs_dir = logs_dir or project_root / "logs"
        self.base_dir = base_dir or project_root

        # Inizializza
        self.runner = ProcessRunner(self.base_dir, self.logs_dir)
        self.tasks: Dict[str, Task] = {}
        self.subscribers: List[Callable[[str, Task], None]] = []
        self._save_lock = Lock()

        # Carica stato precedente
        self._load_state()

        # Salva stato all'uscita
        atexit.register(self._save_state)

        self._initialized = True
        logger.info(f"TaskManager initialized. State file: {self.state_file}")

    def _load_state(self):
        """Carica stato persistente da JSON."""
        if not self.state_file.exists():
            logger.info("No previous state file found")
            return

        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for task_data in data.get("tasks", []):
                task = Task.from_dict(task_data)
                # Prova a recuperare task "running" da sessione precedente
                if task.status == TaskStatus.RUNNING:
                    # Verifica se il processo è ancora in esecuzione
                    if self.runner.recover_task(task):
                        logger.info(f"Task {task.id} recovered - still running")
                    else:
                        task.status = TaskStatus.FAILED
                        task.error_message = "Process terminated unexpectedly (previous session)"
                        task.finished_at = datetime.now()
                self.tasks[task.id] = task

            logger.info(f"Loaded {len(self.tasks)} tasks from state file")
        except Exception as e:
            logger.error(f"Error loading state: {e}")

    def _save_state(self):
        """Salva stato su file per persistenza."""
        with self._save_lock:
            try:
                data = {
                    "tasks": [t.to_dict() for t in self.tasks.values()],
                    "saved_at": datetime.now().isoformat()
                }
                self.state_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.state_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
                logger.debug("State saved successfully")
            except Exception as e:
                logger.error(f"Error saving state: {e}")

    def subscribe(self, callback: Callable[[str, Task], None]):
        """
        Registra subscriber per eventi task.

        Args:
            callback: Funzione chiamata con (event_type, task)
                     event_type: "created", "started", "output", "completed", "stopped"
        """
        self.subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[str, Task], None]):
        """Rimuove un subscriber."""
        if callback in self.subscribers:
            self.subscribers.remove(callback)

    def _notify(self, event: str, task: Task):
        """Notifica tutti i subscriber."""
        for callback in self.subscribers:
            try:
                callback(event, task)
            except Exception as e:
                logger.error(f"Error in subscriber callback: {e}")

    def create_task(self, command: str, variables: Optional[Dict[str, str]] = None) -> Task:
        """
        Crea un nuovo task (non lo avvia).

        Args:
            command: Nome del comando make (es. "strata-cycle")
            variables: Variabili make opzionali

        Returns:
            Task creato
        """
        task = Task(
            command=command,
            make_target=command,
            variables=variables or {}
        )
        self.tasks[task.id] = task
        self._save_state()
        self._notify("created", task)
        logger.info(f"Task created: {task.id} ({command})")
        return task

    def start_task(
        self,
        task_id: str,
        on_output: Optional[Callable[[str], None]] = None
    ) -> bool:
        """
        Avvia un task.

        Args:
            task_id: ID del task
            on_output: Callback opzionale per output live

        Returns:
            True se avviato, False se non trovato o già in esecuzione
        """
        task = self.tasks.get(task_id)
        if not task:
            logger.warning(f"Task not found: {task_id}")
            return False

        if task.status == TaskStatus.RUNNING:
            logger.warning(f"Task already running: {task_id}")
            return False

        def handle_output(line: str):
            self._notify("output", task)
            if on_output:
                on_output(line)

        def handle_complete(exit_code: int):
            self._save_state()
            self._notify("completed", task)

        try:
            self.runner.run_make_command(task, handle_output, handle_complete)
            self._save_state()
            self._notify("started", task)
            return True
        except Exception as e:
            logger.error(f"Failed to start task {task_id}: {e}")
            return False

    def stop_task(self, task_id: str, force: bool = False) -> bool:
        """
        Ferma un task.

        Args:
            task_id: ID del task
            force: Se True usa SIGKILL, altrimenti SIGTERM

        Returns:
            True se fermato, False se non trovato
        """
        task = self.tasks.get(task_id)
        if not task:
            return False

        result = self.runner.stop_task(task_id, graceful=not force)
        if result:
            task.status = TaskStatus.CANCELLED
            task.finished_at = datetime.now()
            self._save_state()
            self._notify("stopped", task)

        return result

    def get_task(self, task_id: str) -> Optional[Task]:
        """Ritorna un task per ID."""
        return self.tasks.get(task_id)

    def get_all_tasks(self) -> List[Task]:
        """Ritorna tutti i task."""
        return list(self.tasks.values())

    def get_active_tasks(self) -> List[Task]:
        """Ritorna task in esecuzione."""
        return [t for t in self.tasks.values() if t.status == TaskStatus.RUNNING]

    def get_recent_tasks(self, limit: int = 10) -> List[Task]:
        """Ritorna gli ultimi N task (ordinati per data creazione)."""
        sorted_tasks = sorted(
            self.tasks.values(),
            key=lambda t: t.created_at,
            reverse=True
        )
        return sorted_tasks[:limit]

    def get_task_output(self, task_id: str, tail_lines: int = 100) -> List[str]:
        """
        Legge ultime N righe dal log del task.

        Args:
            task_id: ID del task
            tail_lines: Numero di righe

        Returns:
            Lista delle righe
        """
        task = self.tasks.get(task_id)
        if not task or not task.log_file:
            return []

        return LogStreamer.tail(Path(task.log_file), lines=tail_lines)

    def delete_task(self, task_id: str) -> bool:
        """
        Elimina un task (solo se non in esecuzione).

        Args:
            task_id: ID del task

        Returns:
            True se eliminato
        """
        task = self.tasks.get(task_id)
        if not task:
            return False

        if task.status == TaskStatus.RUNNING:
            logger.warning(f"Cannot delete running task: {task_id}")
            return False

        del self.tasks[task_id]
        self._save_state()
        return True

    def clear_finished_tasks(self) -> int:
        """
        Rimuove tutti i task completati/falliti/cancellati.

        Returns:
            Numero di task rimossi
        """
        to_remove = [
            task_id for task_id, task in self.tasks.items()
            if task.is_finished
        ]
        for task_id in to_remove:
            del self.tasks[task_id]

        if to_remove:
            self._save_state()

        return len(to_remove)


# Singleton getter
def get_task_manager() -> TaskManager:
    """Ritorna l'istanza singleton del TaskManager."""
    return TaskManager()
