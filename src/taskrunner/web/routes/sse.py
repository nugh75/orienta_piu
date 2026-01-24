"""
Server-Sent Events per streaming output live.
"""

from flask import Blueprint, Response, request
from pathlib import Path
import sys
import json
import time
import queue
import threading

PROJECT_ROOT = Path(__file__).parents[4]
sys.path.insert(0, str(PROJECT_ROOT))

from src.taskrunner.core.task_manager import get_task_manager
from src.taskrunner.core.log_streamer import LogStreamer
from src.taskrunner.models.task import TaskStatus

sse_bp = Blueprint('sse', __name__)


@sse_bp.route('/tasks/<task_id>/stream')
def stream_task_output(task_id):
    """SSE endpoint per streaming output live di un task."""

    def generate():
        manager = get_task_manager()
        task = manager.get_task(task_id)

        if not task:
            yield f"data: {json.dumps({'type': 'error', 'message': 'Task not found'})}\n\n"
            return

        # Invia stato iniziale
        yield f"data: {json.dumps({'type': 'init', 'task': task.to_dict()})}\n\n"

        # Se non ha log file, aspetta che venga creato
        max_wait = 10
        waited = 0
        while not task.log_file and waited < max_wait:
            time.sleep(0.5)
            waited += 0.5
            task = manager.get_task(task_id)
            if not task:
                return

        if not task.log_file:
            yield f"data: {json.dumps({'type': 'error', 'message': 'No log file'})}\n\n"
            return

        log_path = Path(task.log_file)

        # Invia output esistente
        if log_path.exists():
            existing = LogStreamer.tail(log_path, lines=100)
            for line in existing:
                yield f"data: {json.dumps({'type': 'output', 'line': line})}\n\n"

        # Stream nuove righe
        streamer = LogStreamer(log_path, poll_interval=0.2)
        last_line_count = LogStreamer.get_line_count(log_path)

        try:
            while True:
                # Controlla se task è ancora attivo
                task = manager.get_task(task_id)
                if not task or task.status not in (TaskStatus.RUNNING, TaskStatus.PENDING):
                    yield f"data: {json.dumps({'type': 'complete', 'task': task.to_dict() if task else None})}\n\n"
                    break

                # Leggi nuove righe
                current_count = LogStreamer.get_line_count(log_path)
                if current_count > last_line_count:
                    new_lines = LogStreamer.tail(log_path, lines=current_count - last_line_count)
                    for line in new_lines:
                        yield f"data: {json.dumps({'type': 'output', 'line': line})}\n\n"
                    last_line_count = current_count

                time.sleep(0.2)

        except GeneratorExit:
            streamer.stop()

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
            'Access-Control-Allow-Origin': '*'
        }
    )


@sse_bp.route('/events')
def global_events():
    """SSE per eventi globali (nuovo task, completamento, etc.)."""

    def generate():
        manager = get_task_manager()
        event_queue = queue.Queue()

        def on_event(event_type, task):
            try:
                event_queue.put({
                    'type': event_type,
                    'task': task.to_dict()
                }, block=False)
            except queue.Full:
                pass

        manager.subscribe(on_event)

        # Invia stato iniziale
        active = manager.get_active_tasks()
        yield f"data: {json.dumps({'type': 'init', 'active_count': len(active)})}\n\n"

        try:
            heartbeat_counter = 0
            while True:
                try:
                    event = event_queue.get(timeout=0.5)
                    yield f"data: {json.dumps(event)}\n\n"
                    heartbeat_counter = 0
                except queue.Empty:
                    # Heartbeat ogni 0.5 secondi per mantenere connessione SSH attiva
                    heartbeat_counter += 1
                    if heartbeat_counter >= 2:  # ogni secondo circa
                        yield f": heartbeat {time.time()}\n\n"
                        heartbeat_counter = 0

        except GeneratorExit:
            manager.unsubscribe(on_event)

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
            'Access-Control-Allow-Origin': '*'
        }
    )
