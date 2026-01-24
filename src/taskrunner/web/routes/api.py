"""
API REST per Task Runner.
"""

from flask import Blueprint, jsonify, request
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parents[4]
sys.path.insert(0, str(PROJECT_ROOT))

from src.taskrunner.core.task_manager import get_task_manager
from src.taskrunner.core.command_registry import CommandRegistry, VARIABLE_OPTIONS

api_bp = Blueprint('api', __name__)


@api_bp.route('/commands', methods=['GET'])
def list_commands():
    """Lista comandi disponibili raggruppati per categoria."""
    registry = CommandRegistry()
    categories = []

    for cat in registry.get_categories():
        commands = []
        for cmd in registry.get_by_category(cat):
            # Costruisci info variabili con opzioni
            var_info = []
            for var in cmd.variables:
                var_data = {"name": var}
                if var in VARIABLE_OPTIONS:
                    opts = VARIABLE_OPTIONS[var]
                    var_data["label"] = opts.get("label", var)
                    var_data["options"] = opts.get("options", [])
                    var_data["allow_custom"] = opts.get("allow_custom", True)
                else:
                    var_data["label"] = var
                    var_data["options"] = []
                    var_data["allow_custom"] = True
                var_info.append(var_data)

            commands.append({
                "name": cmd.name,
                "description": cmd.description,
                "variables": cmd.variables,
                "variable_info": var_info,
                "is_long_running": cmd.is_long_running,
                "is_destructive": cmd.is_destructive,
            })
        categories.append({
            "name": cat,
            "commands": commands
        })

    return jsonify({"categories": categories})


@api_bp.route('/tasks', methods=['GET'])
def list_tasks():
    """Lista tutti i task."""
    manager = get_task_manager()
    tasks = [t.to_dict() for t in manager.get_recent_tasks(50)]
    active_count = len(manager.get_active_tasks())
    return jsonify({
        "tasks": tasks,
        "active_count": active_count
    })


@api_bp.route('/tasks', methods=['POST'])
def create_task():
    """Crea e avvia un nuovo task."""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    command = data.get('command')
    if not command:
        return jsonify({"error": "Command is required"}), 400

    variables = data.get('variables', {})

    manager = get_task_manager()
    task = manager.create_task(command, variables)
    success = manager.start_task(task.id)

    if success:
        return jsonify(task.to_dict()), 201
    else:
        return jsonify({"error": "Failed to start task"}), 500


@api_bp.route('/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    """Dettaglio di un task."""
    manager = get_task_manager()
    task = manager.get_task(task_id)

    if not task:
        return jsonify({"error": "Task not found"}), 404

    return jsonify(task.to_dict())


@api_bp.route('/tasks/<task_id>/stop', methods=['POST'])
def stop_task(task_id):
    """Ferma un task."""
    data = request.json or {}
    force = data.get('force', False)

    manager = get_task_manager()
    success = manager.stop_task(task_id, force=force)

    if success:
        task = manager.get_task(task_id)
        return jsonify({"success": True, "task": task.to_dict() if task else None})
    else:
        return jsonify({"success": False, "error": "Task not found or not running"}), 404


@api_bp.route('/tasks/<task_id>/output', methods=['GET'])
def get_output(task_id):
    """Ultime N righe di output."""
    lines = int(request.args.get('lines', 100))
    manager = get_task_manager()
    output = manager.get_task_output(task_id, tail_lines=lines)
    return jsonify({"output": output})


@api_bp.route('/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    """Elimina un task."""
    manager = get_task_manager()
    success = manager.delete_task(task_id)

    if success:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": "Task not found or running"}), 404


@api_bp.route('/tasks/clear', methods=['POST'])
def clear_finished():
    """Rimuove task completati."""
    manager = get_task_manager()
    count = manager.clear_finished_tasks()
    return jsonify({"removed": count})
