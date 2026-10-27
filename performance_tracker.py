import os
import json
import time
from pathlib import Path

class PerformanceTracker:
    def __init__(self, history_file="logs/performance_history.json"):
        self.history_file = history_file
        self.history = self._load_history()

    def _load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_history(self):
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        try:
            with open(self.history_file, "w") as f:
                json.dump(self.history, f, indent=4)
        except Exception:
            pass

    def record_duration(self, task_name, duration):
        """Records the duration of a specific task."""
        if task_name not in self.history:
            self.history[task_name] = []
        
        self.history[task_name].append(duration)
        
        # Keep only last 20 records for moving average
        if len(self.history[task_name]) > 20:
            self.history[task_name].pop(0)
            
        self._save_history()

    def get_estimate(self, task_name, default=5.0):
        """Returns the average duration for a task based on history."""
        if task_name in self.history and self.history[task_name]:
            durations = self.history[task_name]
            return sum(durations) / len(durations)
        return default

# Global instance
tracker = PerformanceTracker()
