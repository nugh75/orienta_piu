import os
import requests
import json
import logging

class LLMClient:
    def __init__(self, config):
        self.config = config
        self.active_preset = str(config.get("active_preset", "0"))
        self.presets = config.get("presets", {})
        
        # Get active preset config
        self.preset_config = self.presets.get(self.active_preset)
        
        if not self.preset_config:
             logging.warning(f"Preset {self.active_preset} not found, falling back to defaults")

    def generate(self, model, prompt, system_prompt=None, temperature=0.2, max_tokens=4096):
        # Handle mixed configuration where model is a dict
        if isinstance(model, dict):
            provider = model.get("provider", "ollama")
            model_name = model.get("model")
            # Create a temporary config context for this call
            call_config = model
        else:
            # Standard preset configuration
            provider = self.preset_config.get("type", "ollama") if self.preset_config else "ollama"
            model_name = model
            call_config = self.preset_config

        if provider == "ollama":
            return self._generate_ollama(model_name, prompt, system_prompt, temperature, max_tokens, call_config)
        elif provider == "openai":
            return self._generate_openai_compatible(model_name, prompt, system_prompt, temperature, max_tokens, call_config)
        else:
            logging.error(f"Unknown provider type: {provider}")
            return ""

    def _generate_ollama(self, model, prompt, system_prompt, temperature, max_tokens, config=None):
        # Use URL from specific config or preset or global default
        url = None
        if config:
            url = config.get("ollama_url")
        
        if not url and self.preset_config:
            url = self.preset_config.get("ollama_url")
            
        if not url:
            url = self.config.get("ollama_url", "http://localhost:11434/api/generate")
        
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"System: {system_prompt}\n\nUser: {prompt}"
            
        payload = {
            "model": model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_ctx": max_tokens * 4 
            }
        }
        
        try:
            response = requests.post(url, json=payload, timeout=300)
            response.raise_for_status()
            return response.json().get("response", "")
        except Exception as e:
            logging.error(f"Ollama error: {e}")
            return ""

    def _generate_openai_compatible(self, model, prompt, system_prompt, temperature, max_tokens, config=None):
        # Resolve config from specific call config or preset
        base_url = config.get("base_url") if config else None
        api_key_env = config.get("api_key_env") if config else None
        
        # Fallback to preset if not in specific config
        if not base_url and self.preset_config:
            base_url = self.preset_config.get("base_url")
        if not api_key_env and self.preset_config:
            api_key_env = self.preset_config.get("api_key_env")
            
        api_key = os.environ.get(api_key_env) if api_key_env else None
        
        if not api_key:
            logging.error(f"API Key for {api_key_env} not found in environment variables")
            return ""
            
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # OpenRouter specific headers
        if base_url and "openrouter" in base_url:
            headers["HTTP-Referer"] = "https://github.com/nugh75/LIste"
            headers["X-Title"] = "LIste PTOF Analysis"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            response = requests.post(base_url, headers=headers, json=payload, timeout=300)
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            logging.error(f"API error ({base_url}): {e}")
            if 'response' in locals():
                logging.error(f"Response: {response.text}")
            return ""
