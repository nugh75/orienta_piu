/**
 * PTOF Settings - Preset Management
 */

class PresetManager {
  constructor() {
    this.baseUrl = window.location.pathname.startsWith('/taskrunner') ? '/taskrunner' : '';
    this.presets = {};
    this.currentPresetId = null;

    this.elements = {
      presetList: document.getElementById('preset-list'),
      form: document.getElementById('preset-form'),
      editorTitle: document.getElementById('editor-title'),
      btnNew: document.getElementById('btn-new-preset'),
      btnSave: document.getElementById('btn-save'),
      btnDelete: document.getElementById('btn-delete'),
      emptyState: document.getElementById('empty-state'),
      
      // Fields
      id: document.getElementById('preset-id'),
      name: document.getElementById('name'),
      description: document.getElementById('description'),
      type: document.getElementById('type'),
      envSettings: document.getElementById('env-settings'),
      
      roleDisplayFields: {
        analyst: document.getElementById('model_analyst'),
        reviewer: document.getElementById('model_reviewer'),
        refiner: document.getElementById('model_refiner'),
        synthesizer: document.getElementById('model_synthesizer'),
      }
    };

    this.init();
  }

  async init() {
    this.elements.btnNew.addEventListener('click', () => this.createNew());
    this.elements.form.addEventListener('submit', (e) => this.saveCurrent(e));
    this.elements.btnDelete.addEventListener('click', () => this.deleteCurrent());
    this.elements.type.addEventListener('change', () => this.updateEnvDisplay());

    await this.loadPresets();
  }

  async loadPresets() {
    try {
      const response = await fetch(`${this.baseUrl}/api/presets`);
      const data = await response.json();
      this.presets = data;
      this.renderList();
    } catch (error) {
      console.error('Failed to load presets:', error);
      alert('Error loading presets');
    }
  }

  renderList() {
    this.elements.presetList.innerHTML = '';
    
    // Sort by ID
    const sortedIds = Object.keys(this.presets).sort((a, b) => parseInt(a) - parseInt(b));

    for (const id of sortedIds) {
      const p = this.presets[id];
      const item = document.createElement('div');
      item.className = 'preset-item';
      if (id === this.currentPresetId) item.classList.add('active');
      
      item.innerHTML = `
        <span class="preset-item-name">${id} - ${p.name || 'Untitled'}</span>
        <span class="preset-item-type">${p.type || 'Unknown'}</span>
      `;
      
      item.addEventListener('click', () => this.selectPreset(id));
      this.elements.presetList.appendChild(item);
    }
  }

  selectPreset(id) {
    this.currentPresetId = id;
    this.renderList(); // Update active state
    
    const p = this.presets[id];
    if (!p) return;

    // Show form, hide empty state
    this.elements.form.classList.remove('hidden');
    this.elements.emptyState.classList.add('hidden');
    this.elements.editorTitle.textContent = `Edit Preset: ${p.name}`;
    this.elements.btnDelete.disabled = false;

    // Populate fields
    this.elements.id.value = id;
    this.elements.name.value = p.name || '';
    this.elements.description.value = p.description || '';
    this.elements.type.value = p.type || 'ollama';

    // Env vars
    document.getElementById('ollama_url').value = p.ollama_url || '';
    document.getElementById('base_url').value = p.base_url || '';
    document.getElementById('api_key_env').value = p.api_key_env || 'OPENAI_API_KEY';

    // Models
    const models = p.models || {};
    // Handle simplified format (just strings) or complex (dicts)
    // We only support simple editing here for now. If it's a dict, we try to extract 'model' key or json stringify
    const extractModel = (val) => {
       if (typeof val === 'object' && val !== null) return val.model || JSON.stringify(val);
       return val || '';
    };

    this.elements.roleDisplayFields.analyst.value = extractModel(models.analyst);
    this.elements.roleDisplayFields.reviewer.value = extractModel(models.reviewer);
    this.elements.roleDisplayFields.refiner.value = extractModel(models.refiner);
    this.elements.roleDisplayFields.synthesizer.value = extractModel(models.synthesizer);

    this.updateEnvDisplay();
  }

  createNew() {
    this.currentPresetId = null;
    this.renderList();

    this.elements.form.classList.remove('hidden');
    this.elements.emptyState.classList.add('hidden');
    this.elements.editorTitle.textContent = 'New Preset';
    this.elements.btnDelete.disabled = true;

    this.elements.form.reset();
    this.elements.id.value = '';
    this.elements.type.value = 'ollama';
    this.updateEnvDisplay();
  }

  updateEnvDisplay() {
    const type = this.elements.type.value;
    const envDiv = this.elements.envSettings;
    
    // Simple logic: show all, let user decide. Or optimize?
    // Let's just show everything but maybe visually deemphasize irrelevant ones?
    // Actually, based on type we can hide:
    const ollamaField = document.getElementById('ollama_url').parentElement;
    const cloudFields = document.getElementById('base_url').parentElement.parentElement; // Wrapper needed? No.
    
    // Easier: just always show them, user is advanced enough.
  }

  async saveCurrent(e) {
    e.preventDefault();
    
    const id = this.elements.id.value;
    const isNew = !id;

    // Build payload
    const payload = {
      name: this.elements.name.value,
      description: this.elements.description.value,
      type: this.elements.type.value,
      models: {
        analyst: this.elements.roleDisplayFields.analyst.value,
        reviewer: this.elements.roleDisplayFields.reviewer.value,
        refiner: this.elements.roleDisplayFields.refiner.value,
        synthesizer: this.elements.roleDisplayFields.synthesizer.value,
      }
    };

    // Optional fields
    const ollamaUrl = document.getElementById('ollama_url').value;
    if (ollamaUrl) payload.ollama_url = ollamaUrl;

    const baseUrl = document.getElementById('base_url').value;
    if (baseUrl) payload.base_url = baseUrl;
    
    const apiKeyEnv = document.getElementById('api_key_env').value;
    if (apiKeyEnv) payload.api_key_env = apiKeyEnv;

    try {
      let url = `${this.baseUrl}/api/presets`;
      let method = 'POST';
      
      if (!isNew) {
        url += `/${id}`;
        method = 'PUT';
      }

      const response = await fetch(url, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (response.ok) {
        const result = await response.json();
        // If new, get the new ID
        if (isNew && result.id) {
          this.currentPresetId = result.id;
        }
        await this.loadPresets();
        this.selectPreset(this.currentPresetId); // re-select to refresh
        alert('Saved successfully');
      } else {
        alert('Error saving preset');
      }
    } catch (error) {
      console.error(error);
      alert('Error saving preset');
    }
  }

  async deleteCurrent() {
    if (!this.currentPresetId) return;
    if (!confirm('Are you sure you want to delete this preset?')) return;

    try {
      const response = await fetch(`${this.baseUrl}/api/presets/${this.currentPresetId}`, {
        method: 'DELETE'
      });

      if (response.ok) {
        this.currentPresetId = null;
        this.elements.form.classList.add('hidden');
        this.elements.emptyState.classList.remove('hidden');
        await this.loadPresets();
      } else {
        alert('Error deleting preset');
      }
    } catch (error) {
      console.error(error);
      alert('Error deleting preset');
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
    new PresetManager();
});
