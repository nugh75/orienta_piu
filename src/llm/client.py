import os
import requests
import json
import logging
import time

def _normalize_model_name(model):
    if not model:
        return ""
    name = str(model).strip().lower()
    if "/" in name:
        name = name.split("/")[-1]
    if ":" in name:
        name = name.split(":")[0]
    return name

def _uses_max_completion_tokens(model):
    name = _normalize_model_name(model)
    return name.startswith("gpt-5") or name.startswith("o1") or name.startswith("o3")

def _supports_temperature(model):
    name = _normalize_model_name(model)
    if not name:
        return True
    return not (name.startswith("gpt-5") or name.startswith("o1") or name.startswith("o3"))

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
        
        retry_max = int(os.environ.get("PTOF_OLLAMA_RETRY_MAX", "-1"))
        retry_base_wait = int(os.environ.get("PTOF_OLLAMA_RETRY_WAIT", "10"))
        retry_max_wait = int(os.environ.get("PTOF_OLLAMA_RETRY_MAX_WAIT", "300"))

        attempt = 0
        while True:
            try:
                response = requests.post(url, json=payload, timeout=300)
                response.raise_for_status()
                data = response.json()
                
                # Log usage (Ollama style)
                try:
                    prompt_eval_count = data.get("prompt_eval_count", 0)
                    eval_count = data.get("eval_count", 0)
                    if prompt_eval_count or eval_count:
                        usage = {
                            "prompt_tokens": prompt_eval_count,
                            "completion_tokens": eval_count,
                            "total_tokens": prompt_eval_count + eval_count
                        }
                        from src.llm.cost_tracker import COST_TRACKER
                        COST_TRACKER.log_usage(model, "ollama", usage)
                except ImportError:
                    pass
                except Exception as e:
                    logging.warning(f"Error logging Ollama usage: {e}")

                return data.get("response", "")
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                attempt += 1
                if retry_max >= 0 and attempt > retry_max:
                    logging.error(f"Ollama error: {e} (max retries reached)")
                    return ""
                wait_time = min(retry_base_wait * (2 ** (attempt - 1)), retry_max_wait)
                retry_label = f"{attempt}" if retry_max < 0 else f"{attempt}/{retry_max}"
                logging.error(f"Ollama error: {e} (retry {retry_label} in {wait_time}s)")
                time.sleep(wait_time)
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
        }
        if _supports_temperature(model):
            payload["temperature"] = temperature
        
        # Supporto per modelli nuovi (o1, o3, gpt-5) che usano max_completion_tokens
        if _uses_max_completion_tokens(model):
            payload["max_completion_tokens"] = max_tokens
        else:
            payload["max_tokens"] = max_tokens
        
        try:
            response = requests.post(base_url, headers=headers, json=payload, timeout=300)
            response.raise_for_status()
            data = response.json()
            
            # Log usage
            usage = data.get('usage')
            if usage:
                try:
                    from src.llm.cost_tracker import COST_TRACKER
                    provider_tag = "openrouter" if "openrouter" in str(base_url) else "openai"
                    COST_TRACKER.log_usage(model, provider_tag, usage)
                    
                    # Immediate Feedback
                    cost = COST_TRACKER._calculate_cost(model, provider_tag, usage)
                    if cost > 0:
                        logging.info(f"💰 [Usage] {usage.get('total_tokens', 0)} toks | Cost: ${cost:.6f}")
                except ImportError:
                    pass
                except Exception as e:
                    logging.warning(f"Error logging cost: {e}")

            content = data['choices'][0]['message']['content']
            if not content:
                choice = data['choices'][0]
                finish_reason = choice.get('finish_reason')
                logging.warning(f"⚠️ [OpenRouter] Empty content received. Finish reason: {finish_reason}")
                logging.warning(f"Full choice obj: {choice}")
                
            return content
        except Exception as e:
            logging.error(f"API error ({base_url}): {e}")
            if 'response' in locals():
                 logging.error(f"Response text: {response.text}")
            return ""
