"""
Process Runner - Esegue comandi make in modo indipendente dalla web UI.

I processi vengono eseguiti in modo completamente staccato:
- Output va direttamente su file
- Processo sopravvive anche se la web UI crasha
- Lo stato viene recuperato al riavvio
"""

import subprocess
import threading
import signal
import os
import time
import json
from pathlib import Path
from typing import Callable, Dict, Optional
from datetime import datetime
import logging

from ..models.task import Task, TaskStatus


logger = logging.getLogger(__name__)


class ProcessRunner:
    """Esegue comandi make in background, indipendenti dalla web UI."""

    def __init__(self, base_dir: Path, logs_dir: Path):
        self.base_dir = base_dir
        self.logs_dir = logs_dir
        self.active_processes: Dict[str, subprocess.Popen] = {}
        self._monitor_threads: Dict[str, threading.Thread] = {}
        self._pid_file_dir = logs_dir / "taskrunner" / "pids"
        self._pid_file_dir.mkdir(parents=True, exist_ok=True)

    def _get_pid_file(self, task_id: str) -> Path:
        """Ritorna il path del file PID per un task."""
        return self._pid_file_dir / f"{task_id}.pid"

    def _save_pid(self, task_id: str, pid: int, pgid: int):
        """Salva PID e PGID su file per recupero."""
        pid_file = self._get_pid_file(task_id)
        with open(pid_file, 'w') as f:
            json.dump({"pid": pid, "pgid": pgid, "started": datetime.now().isoformat()}, f)

    def _load_pid(self, task_id: str) -> Optional[Dict]:
        """Carica PID da file."""
        pid_file = self._get_pid_file(task_id)
        if pid_file.exists():
            try:
                with open(pid_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return None

    def _remove_pid_file(self, task_id: str):
        """Rimuove il file PID."""
        pid_file = self._get_pid_file(task_id)
        pid_file.unlink(missing_ok=True)

    def _is_process_running(self, pid: int) -> bool:
        """Verifica se un processo è in esecuzione."""
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False

    def run_make_command(
        self,
        task: Task,
        on_output: Optional[Callable[[str], None]] = None,
        on_complete: Optional[Callable[[int], None]] = None
    ) -> subprocess.Popen:
        """
        Esegue un comando make in modo completamente indipendente.

        Il processo:
        - Scrive direttamente su file (no PIPE)
        - Viene eseguito in un nuovo session/process group
        - Sopravvive al crash della web UI
        - Lo stato può essere recuperato tramite file PID

        Args:
            task: Task da eseguire
            on_output: Callback per output (usato solo per monitoring)
            on_complete: Callback chiamato al completamento

        Returns:
            Il processo Popen avviato
        """
        # Costruisci comando
        cmd = ["make", task.make_target]
        
        # Aggiungi YES=1 automaticamente per comandi con conferma interattiva
        COMMANDS_WITH_CONFIRM = ["workflow", "activity-extract", "strata-cycle", "sync-sampling"]
        if task.make_target in COMMANDS_WITH_CONFIRM:
            cmd.append("YES=1")
        
        for key, value in task.variables.items():
            if value:
                cmd.append(f"{key}={value}")

        logger.info(f"Starting task {task.id}: {' '.join(cmd)}")

        # Crea directory log se non esiste
        task_logs_dir = self.logs_dir / "taskrunner" / "tasks"
        task_logs_dir.mkdir(parents=True, exist_ok=True)

        # File di log per persistenza
        log_path = task_logs_dir / f"{task.id}.log"
        task.log_file = str(log_path)

        # Scrivi header sul file di log
        with open(log_path, "w", encoding="utf-8") as f:
            header = f"=== Task: {task.id} ===\n"
            header += f"Command: {' '.join(cmd)}\n"
            header += f"Started: {datetime.now().isoformat()}\n"
            header += "=" * 50 + "\n\n"
            f.write(header)

        # Apri file per output (append mode per il processo)
        log_file = open(log_path, "a", encoding="utf-8", buffering=1)

        try:
            # Avvia processo COMPLETAMENTE STACCATO
            # - stdout/stderr vanno direttamente su file
            # - start_new_session=True crea nuovo session leader
            # - Il processo sopravvive alla morte del parent
            process = subprocess.Popen(
                cmd,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,  # No input
                cwd=self.base_dir,
                start_new_session=True,  # Crea nuova sessione (più robusto di setsid)
            )
        except Exception as e:
            log_file.write(f"\nERROR: Failed to start process: {e}\n")
            log_file.close()
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            if on_complete:
                on_complete(-1)
            raise

        task.pid = process.pid
        task.started_at = datetime.now()
        task.status = TaskStatus.RUNNING
        
        # Salva PID su file per recupero dopo crash
        try:
            pgid = os.getpgid(process.pid)
        except:
            pgid = process.pid
        self._save_pid(task.id, process.pid, pgid)
        
        self.active_processes[task.id] = process

        # Thread di monitoring (non daemon - ma non blocca nulla di critico)
        # Questo thread monitora il processo e aggiorna lo stato
        def monitor_process():
            try:
                # Aspetta che il processo termini
                exit_code = process.wait()
                
                # Scrivi footer
                with open(log_path, "a", encoding="utf-8") as f:
                    footer = f"\n{'=' * 50}\n"
                    footer += f"Finished: {datetime.now().isoformat()}\n"
                    footer += f"Exit code: {exit_code}\n"
                    f.write(footer)

                # Aggiorna task
                task.exit_code = exit_code
                task.finished_at = datetime.now()
                task.status = TaskStatus.COMPLETED if exit_code == 0 else TaskStatus.FAILED

                logger.info(f"Task {task.id} finished with exit code {exit_code}")

                # Callback completamento
                if on_complete:
                    try:
                        on_complete(exit_code)
                    except:
                        pass

            except Exception as e:
                logger.error(f"Error monitoring task {task.id}: {e}")
                task.status = TaskStatus.FAILED
                task.error_message = str(e)
            finally:
                # Cleanup
                self.active_processes.pop(task.id, None)
                self._monitor_threads.pop(task.id, None)
                self._remove_pid_file(task.id)
                try:
                    log_file.close()
                except:
                    pass

        # Thread NON daemon per monitoring
        thread = threading.Thread(target=monitor_process, name=f"monitor-{task.id}")
        thread.start()
        self._monitor_threads[task.id] = thread

        return process

    def recover_task(self, task: Task) -> bool:
        """
        Tenta di recuperare un task dopo un restart della web UI.
        
        Returns:
            True se il processo è ancora in esecuzione, False altrimenti
        """
        pid_info = self._load_pid(task.id)
        if not pid_info:
            return False
        
        pid = pid_info.get("pid")
        if not pid:
            return False
        
        if self._is_process_running(pid):
            task.pid = pid
            task.status = TaskStatus.RUNNING
            logger.info(f"Recovered running task {task.id} with PID {pid}")
            
            # Avvia thread di monitoring per questo processo
            self._start_recovery_monitor(task, pid, pid_info.get("pgid", pid))
            return True
        else:
            # Processo non più in esecuzione
            self._remove_pid_file(task.id)
            return False

    def _start_recovery_monitor(self, task: Task, pid: int, pgid: int):
        """Avvia un monitor per un processo recuperato."""
        
        def monitor():
            try:
                # Polling per verificare se il processo è ancora attivo
                while self._is_process_running(pid):
                    time.sleep(1)
                
                # Processo terminato - leggi exit code dal log
                if task.log_file and Path(task.log_file).exists():
                    # Prova a leggere l'exit code dal footer del log
                    try:
                        with open(task.log_file, 'r') as f:
                            content = f.read()
                            if "Exit code:" in content:
                                lines = content.split('\n')
                                for line in reversed(lines):
                                    if line.startswith("Exit code:"):
                                        exit_code = int(line.split(':')[1].strip())
                                        task.exit_code = exit_code
                                        task.status = TaskStatus.COMPLETED if exit_code == 0 else TaskStatus.FAILED
                                        break
                    except:
                        pass
                
                if task.status == TaskStatus.RUNNING:
                    # Non siamo riusciti a leggere l'exit code
                    task.status = TaskStatus.COMPLETED
                    task.exit_code = 0
                
                task.finished_at = datetime.now()
                logger.info(f"Recovered task {task.id} finished")
                
            except Exception as e:
                logger.error(f"Error in recovery monitor for {task.id}: {e}")
            finally:
                self._remove_pid_file(task.id)
                self.active_processes.pop(task.id, None)
                self._monitor_threads.pop(task.id, None)

        thread = threading.Thread(target=monitor, name=f"recover-{task.id}")
        thread.start()
        self._monitor_threads[task.id] = thread

    def stop_task(self, task_id: str, graceful: bool = True) -> bool:
        """
        Ferma un task in esecuzione.

        Args:
            task_id: ID del task
            graceful: Se True invia SIGTERM, altrimenti SIGKILL

        Returns:
            True se il task è stato fermato, False se non trovato
        """
        # Prima prova con il processo in memoria
        if task_id in self.active_processes:
            process = self.active_processes[task_id]
            try:
                pgid = os.getpgid(process.pid)
                sig = signal.SIGTERM if graceful else signal.SIGKILL
                os.killpg(pgid, sig)
                logger.info(f"Sent {sig.name} to task {task_id} (pgid={pgid})")
                return True
            except ProcessLookupError:
                logger.warning(f"Process for task {task_id} not found")
                self.active_processes.pop(task_id, None)
                return False
            except Exception as e:
                logger.error(f"Error stopping task {task_id}: {e}")
                return False
        
        # Prova con il file PID (per processi recuperati)
        pid_info = self._load_pid(task_id)
        if pid_info:
            pid = pid_info.get("pid")
            pgid = pid_info.get("pgid", pid)
            try:
                sig = signal.SIGTERM if graceful else signal.SIGKILL
                os.killpg(pgid, sig)
                logger.info(f"Sent {sig.name} to recovered task {task_id} (pgid={pgid})")
                return True
            except ProcessLookupError:
                self._remove_pid_file(task_id)
                return False
            except Exception as e:
                logger.error(f"Error stopping recovered task {task_id}: {e}")
                return False
        
        return False

    def is_running(self, task_id: str) -> bool:
        """Verifica se un task è in esecuzione."""
        if task_id in self.active_processes:
            return True
        
        # Controlla anche il file PID
        pid_info = self._load_pid(task_id)
        if pid_info:
            return self._is_process_running(pid_info.get("pid", 0))
        
        return False

    def get_active_count(self) -> int:
        """Ritorna il numero di task attivi."""
        return len(self.active_processes)

    def stop_all(self, graceful: bool = True):
        """Ferma tutti i task attivi."""
        for task_id in list(self.active_processes.keys()):
            self.stop_task(task_id, graceful=graceful)
