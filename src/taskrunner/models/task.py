"""
Modello Task per il Task Runner.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict
import uuid


class TaskStatus(Enum):
    """Stati possibili di un task."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """Rappresenta un task in esecuzione o completato."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    command: str = ""                    # es: "strata-cycle"
    make_target: str = ""                # es: "strata-cycle" (target make)
    variables: Dict[str, str] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    pid: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    exit_code: Optional[int] = None
    log_file: Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self) -> dict:
        """Serializza il task in un dizionario JSON-compatibile."""
        return {
            "id": self.id,
            "command": self.command,
            "make_target": self.make_target,
            "variables": self.variables,
            "status": self.status.value,
            "pid": self.pid,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "exit_code": self.exit_code,
            "log_file": self.log_file,
            "error_message": self.error_message
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        """Deserializza un task da dizionario."""
        task = cls()
        task.id = data.get("id", task.id)
        task.command = data.get("command", "")
        task.make_target = data.get("make_target", "")
        task.variables = data.get("variables", {})
        task.status = TaskStatus(data.get("status", "pending"))
        task.pid = data.get("pid")
        task.exit_code = data.get("exit_code")
        task.log_file = data.get("log_file")
        task.error_message = data.get("error_message")

        # Parse datetime
        if data.get("created_at"):
            task.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("started_at"):
            task.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("finished_at"):
            task.finished_at = datetime.fromisoformat(data["finished_at"])

        return task

    @property
    def duration(self) -> Optional[float]:
        """Durata del task in secondi."""
        if not self.started_at:
            return None
        end = self.finished_at or datetime.now()
        return (end - self.started_at).total_seconds()

    @property
    def is_running(self) -> bool:
        return self.status == TaskStatus.RUNNING

    @property
    def is_finished(self) -> bool:
        return self.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)

    def get_command_string(self) -> str:
        """Ritorna il comando make completo con variabili."""
        parts = ["make", self.make_target]
        for key, value in self.variables.items():
            if value:
                parts.append(f"{key}={value}")
        return " ".join(parts)
