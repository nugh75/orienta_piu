import logging
import json
import os
from datetime import datetime
from threading import Lock

class CostTracker:
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(CostTracker, cls).__new__(cls)
                cls._instance._init()
            return cls._instance
    
    def _init(self):
        self.logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
        os.makedirs(self.logs_dir, exist_ok=True)
        self.log_file = os.path.join(self.logs_dir, 'usage_costs.jsonl')
        self.logger = logging.getLogger('CostTracker')
        
    def log_usage(self, model, provider, usage, context="workflow"):
        """
        Log usage stats to JSONL file.
        usage dict expected: {'prompt_tokens': int, 'completion_tokens': int, 'total_tokens': int}
        """
        if not usage:
            return

        entry = {
            "timestamp": datetime.now().isoformat(),
            "provider": provider,
            "model": model,
            "context": context,
            "usage": usage,
            "cost": self._calculate_cost(model, provider, usage)
        }
        
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            self.logger.error(f"Failed to log usage: {e}")
            
    def _calculate_cost(self, model, provider, usage):
        # Basic pricing map (USD)
        # These are approximate and should be updated
        pricing = {
            "gpt-4o": {"in": 2.50, "out": 10.00},
            "gpt-4o-mini": {"in": 0.15, "out": 0.60},
            "claude-3.5-sonnet": {"in": 3.00, "out": 15.00},
            "gemini-1.5-pro": {"in": 1.25, "out": 5.00},
            "gemini-1.5-flash": {"in": 0.075, "out": 0.30},
            "gemini-2.0-flash-lite": {"in": 0.075, "out": 0.30}, 
            "gemini-2.0-flash": {"in": 0.10, "out": 0.40}, 
            "gemini-2.5-flash-lite": {"in": 0.075, "out": 0.30}, # Est
            "gemini-2.5-flash": {"in": 0.10, "out": 0.40}, # Est
            "qwen/qwen-2.5-72b-instruct": {"in": 0.12, "out": 0.39}, 
            "deepseek-chat": {"in": 0.14, "out": 0.28}, # V3
        }
        
        if provider == 'ollama':
            return 0.0
            
        model_norm = model.lower()
        price = None
        
        for k, v in pricing.items():
            if k in model_norm:
                price = v
                break
        
        if not price:
            return 0.0
            
        input_cost = (usage.get('prompt_tokens', 0) / 1_000_000) * price['in']
        output_cost = (usage.get('completion_tokens', 0) / 1_000_000) * price['out']
        return round(input_cost + output_cost, 6)

COST_TRACKER = CostTracker()
