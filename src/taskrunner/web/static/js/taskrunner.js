/**
 * PTOF Task Runner - Frontend JavaScript
 */

class TaskRunner {
    constructor() {
        this.eventSource = null;
        this.taskStream = null;
        this.currentTaskId = null;
        this.selectedCommand = null;
        this.commands = {};
        
        // Base URL per API (gestisce reverse proxy)
        this.baseUrl = window.TASKRUNNER_BASE || '';

        // DOM elements
        this.elements = {
            commandList: document.getElementById('command-list'),
            taskList: document.getElementById('task-list'),
            commandForm: document.getElementById('command-form'),
            commandTitle: document.getElementById('command-title'),
            commandDescription: document.getElementById('command-description'),
            paramsForm: document.getElementById('params-form'),
            outputContainer: document.getElementById('output-container'),
            currentTaskId: document.getElementById('current-task-id'),
            connectionStatus: document.getElementById('connection-status'),
            activeCount: document.getElementById('active-count'),
            btnStart: document.getElementById('btn-start'),
            btnCancel: document.getElementById('btn-cancel'),
            btnStop: document.getElementById('btn-stop'),
            btnKill: document.getElementById('btn-kill'),
            btnClear: document.getElementById('btn-clear'),
            btnClearFinished: document.getElementById('btn-clear-finished'),
        };

        this.reconnectAttempts = 0;
        this.init();
    }

    async init() {
        // Carica comandi
        await this.loadCommands();

        // Carica task esistenti
        await this.loadTasks();

        // Connetti agli eventi globali
        this.connectGlobalEvents();

        // Verifica connessione ogni 10 secondi
        setInterval(() => {
            if (!this.eventSource || this.eventSource.readyState === EventSource.CLOSED) {
                console.log('Connessione SSE persa, riconnetto...');
                this.connectGlobalEvents();
            }
        }, 10000);

        // Event listeners
        this.elements.btnStart.addEventListener('click', () => this.startSelectedCommand());
        this.elements.btnCancel.addEventListener('click', () => this.hideCommandForm());
        this.elements.btnStop.addEventListener('click', () => this.stopCurrentTask(false));
        this.elements.btnKill.addEventListener('click', () => this.stopCurrentTask(true));
        this.elements.btnClear.addEventListener('click', () => this.clearOutput());
        this.elements.btnClearFinished.addEventListener('click', () => this.clearFinishedTasks());
    }

    async loadCommands() {
        try {
            const response = await fetch(`${this.baseUrl}/api/commands`);
            const data = await response.json();

            this.elements.commandList.innerHTML = '';

            for (const category of data.categories) {
                const categoryDiv = document.createElement('div');
                categoryDiv.className = 'category';

                const header = document.createElement('div');
                header.className = 'category-header';
                header.textContent = category.name;
                categoryDiv.appendChild(header);

                for (const cmd of category.commands) {
                    this.commands[cmd.name] = cmd;

                    const item = document.createElement('div');
                    item.className = 'command-item';
                    if (cmd.is_long_running) item.classList.add('long-running');
                    if (cmd.is_destructive) item.classList.add('destructive');

                    // Mostra nome leggibile con comando tra parentesi
                    const displayName = cmd.display_name || cmd.name;
                    item.innerHTML = `<span class="cmd-display-name">${displayName}</span><span class="cmd-name">(${cmd.name})</span>`;
                    item.addEventListener('click', () => this.selectCommand(cmd));
                    categoryDiv.appendChild(item);
                }

                this.elements.commandList.appendChild(categoryDiv);
            }
        } catch (error) {
            console.error('Failed to load commands:', error);
        }
    }

    async loadTasks() {
        try {
            const response = await fetch(`${this.baseUrl}/api/tasks`);
            const data = await response.json();

            this.updateActiveCount(data.active_count);
            this.renderTaskList(data.tasks);
        } catch (error) {
            console.error('Failed to load tasks:', error);
        }
    }

    renderTaskList(tasks) {
        this.elements.taskList.innerHTML = '';

        for (const task of tasks.slice(0, 10)) {
            const item = document.createElement('div');
            item.className = `task-item ${task.status}`;
            item.innerHTML = `
                <span class="task-id">${task.id}</span>
                <span class="task-command">${task.command}</span>
            `;
            item.addEventListener('click', () => this.selectTask(task.id));
            this.elements.taskList.appendChild(item);
        }
    }

    selectCommand(cmd) {
        this.selectedCommand = cmd;
        const displayName = cmd.display_name || cmd.name;
        this.elements.commandTitle.innerHTML = `${displayName} <small>(make ${cmd.name})</small>`;
        this.elements.commandDescription.textContent = cmd.description || '';

        // Genera form parametri con dropdown
        this.elements.paramsForm.innerHTML = '';
        const varInfo = cmd.variable_info || [];

        for (const info of varInfo) {
            const row = document.createElement('div');
            row.className = 'param-row';

            const label = document.createElement('label');
            label.setAttribute('for', `param-${info.name}`);
            label.textContent = `${info.label || info.name}:`;
            row.appendChild(label);

            // Se ci sono opzioni predefinite, usa un select
            if (info.options && info.options.length > 0) {
                const select = document.createElement('select');
                select.id = `param-${info.name}`;
                select.name = info.name;

                // Opzioni predefinite
                for (const opt of info.options) {
                    const option = document.createElement('option');
                    option.value = opt;
                    option.textContent = opt || '-- Seleziona --';
                    select.appendChild(option);
                }

                // Se permette custom, aggiungi opzione "Altro..."
                if (info.allow_custom) {
                    const customOpt = document.createElement('option');
                    customOpt.value = '__custom__';
                    customOpt.textContent = '✏️ Altro (personalizzato)...';
                    select.appendChild(customOpt);
                }

                row.appendChild(select);

                // Input nascosto per valore custom
                if (info.allow_custom) {
                    const customInput = document.createElement('input');
                    customInput.type = 'text';
                    customInput.id = `param-${info.name}-custom`;
                    customInput.className = 'custom-input hidden';
                    customInput.placeholder = `Valore personalizzato per ${info.label || info.name}`;
                    row.appendChild(customInput);

                    // Mostra input custom quando selezionato "Altro"
                    select.addEventListener('change', () => {
                        if (select.value === '__custom__') {
                            customInput.classList.remove('hidden');
                            customInput.focus();
                        } else {
                            customInput.classList.add('hidden');
                            customInput.value = '';
                        }
                    });
                }
            } else {
                // Nessuna opzione, usa input text
                const input = document.createElement('input');
                input.type = 'text';
                input.id = `param-${info.name}`;
                input.name = info.name;
                input.placeholder = `Valore per ${info.label || info.name}`;
                row.appendChild(input);
            }

            this.elements.paramsForm.appendChild(row);
        }

        this.elements.commandForm.classList.remove('hidden');
    }

    hideCommandForm() {
        this.elements.commandForm.classList.add('hidden');
        this.selectedCommand = null;
    }

    async startSelectedCommand() {
        if (!this.selectedCommand) return;

        // Raccogli variabili da select e input
        const variables = {};

        // Raccogli dai select
        const selects = this.elements.paramsForm.querySelectorAll('select');
        for (const select of selects) {
            let value = select.value;
            // Se è "custom", prendi il valore dall'input nascosto
            if (value === '__custom__') {
                const customInput = document.getElementById(`${select.id}-custom`);
                value = customInput ? customInput.value.trim() : '';
            }
            if (value && value !== '__custom__') {
                variables[select.name] = value;
            }
        }

        // Raccogli dagli input text normali (non custom)
        const inputs = this.elements.paramsForm.querySelectorAll('input:not(.custom-input)');
        for (const input of inputs) {
            if (input.value.trim()) {
                variables[input.name] = input.value.trim();
            }
        }

        try {
            const response = await fetch(`${this.baseUrl}/api/tasks`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    command: this.selectedCommand.name,
                    variables
                })
            });

            if (response.ok) {
                const task = await response.json();
                this.currentTaskId = task.id;
                this.elements.currentTaskId.textContent = `(${task.id})`;
                this.hideCommandForm();
                this.clearOutput();
                this.appendOutput(`>>> Avviato: make ${task.command}`, 'success');
                this.appendOutput('-'.repeat(50));

                // Connetti allo stream
                this.connectTaskStream(task.id);

                // Abilita pulsanti
                this.elements.btnStop.disabled = false;
                this.elements.btnKill.disabled = false;

                // Ricarica task list
                this.loadTasks();
            } else {
                const error = await response.json();
                this.appendOutput(`Errore: ${error.error}`, 'error');
            }
        } catch (error) {
            console.error('Failed to start task:', error);
            this.appendOutput(`Errore: ${error.message}`, 'error');
        }
    }

    selectTask(taskId) {
        this.currentTaskId = taskId;
        this.elements.currentTaskId.textContent = `(${taskId})`;
        this.clearOutput();
        this.connectTaskStream(taskId);
    }

    connectTaskStream(taskId) {
        // Chiudi stream precedente
        if (this.taskStream) {
            this.taskStream.close();
        }

        this.taskStream = new EventSource(`${this.baseUrl}/sse/tasks/${taskId}/stream`);

        this.taskStream.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);

                if (data.type === 'output') {
                    this.appendOutput(data.line);
                } else if (data.type === 'complete') {
                    const task = data.task;
                    if (task) {
                        const status = task.exit_code === 0 ? 'success' : 'error';
                        this.appendOutput('');
                        this.appendOutput(`>>> Task ${task.status} (exit: ${task.exit_code})`, status);
                    }
                    this.taskStream.close();
                    this.elements.btnStop.disabled = true;
                    this.elements.btnKill.disabled = true;
                    this.loadTasks();
                } else if (data.type === 'error') {
                    this.appendOutput(`Errore: ${data.message}`, 'error');
                }
            } catch (e) {
                console.error('Error parsing SSE data:', e);
            }
        };

        this.taskStream.onerror = () => {
            console.log('Task stream disconnected');
        };
    }

    connectGlobalEvents() {
        // Chiudi connessione precedente se esiste
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }

        this.eventSource = new EventSource(`${this.baseUrl}/sse/events`);

        this.eventSource.onopen = () => {
            this.elements.connectionStatus.textContent = 'Connesso';
            this.elements.connectionStatus.className = 'connected';
            this.reconnectAttempts = 0;
            // Ricarica stato attuale
            this.loadTasks();
        };

        this.eventSource.onerror = (e) => {
            this.elements.connectionStatus.textContent = 'Disconnesso';
            this.elements.connectionStatus.className = 'disconnected';

            // Chiudi connessione corrente
            if (this.eventSource) {
                this.eventSource.close();
                this.eventSource = null;
            }

            // Riconnetti con backoff (max 5 secondi)
            this.reconnectAttempts = (this.reconnectAttempts || 0) + 1;
            const delay = Math.min(1000 * this.reconnectAttempts, 5000);
            
            console.log(`Riconnessione SSE in ${delay/1000}s (tentativo ${this.reconnectAttempts})...`);
            setTimeout(() => {
                this.connectGlobalEvents();
            }, delay);
        };

        this.eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);

                if (data.type === 'init') {
                    this.updateActiveCount(data.active_count);
                } else if (data.type === 'started') {
                    this.updateActiveCount('+1');
                    this.loadTasks();
                } else if (data.type === 'completed' || data.type === 'stopped') {
                    this.updateActiveCount('-1');
                    this.loadTasks();
                }
            } catch (e) {
                // Ignora errori di parsing (es. heartbeat)
            }
        };
    }

    updateActiveCount(count) {
        if (typeof count === 'number') {
            this.elements.activeCount.textContent = `${count} task attivi`;
        }
    }

    async stopCurrentTask(force = false) {
        if (!this.currentTaskId) return;

        try {
            const response = await fetch(`${this.baseUrl}/api/tasks/${this.currentTaskId}/stop`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ force })
            });

            if (response.ok) {
                this.appendOutput(`>>> ${force ? 'Kill' : 'Stop'} richiesto`, 'info');
            }
        } catch (error) {
            console.error('Failed to stop task:', error);
        }
    }

    async clearFinishedTasks() {
        try {
            const response = await fetch(`${this.baseUrl}/api/tasks/clear`, { method: 'POST' });
            if (response.ok) {
                const data = await response.json();
                this.appendOutput(`>>> Rimossi ${data.removed} task completati`, 'info');
                this.loadTasks();
            }
        } catch (error) {
            console.error('Failed to clear tasks:', error);
        }
    }

    appendOutput(line, className = '') {
        const lineEl = document.createElement('div');
        lineEl.className = 'output-line';
        if (className) lineEl.classList.add(className);
        lineEl.textContent = line;
        this.elements.outputContainer.appendChild(lineEl);

        // Auto-scroll
        this.elements.outputContainer.scrollTop = this.elements.outputContainer.scrollHeight;
    }

    clearOutput() {
        this.elements.outputContainer.innerHTML = '';
    }
}

// Inizializza quando il DOM è pronto
document.addEventListener('DOMContentLoaded', () => {
    window.taskRunner = new TaskRunner();
});
