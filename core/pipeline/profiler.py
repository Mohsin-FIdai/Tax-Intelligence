import time
import json
import tracemalloc
import logging
from typing import Dict, Any, List
from pathlib import Path

class PipelineProfiler:
    def __init__(self, log_file: Path = Path('pipeline_profile.json')):
        self.log_file = log_file
        self.stages: List[Dict[str, Any]] = []
        self._current_stage = None
        self._stage_start_time = 0
        self._stage_start_mem = 0
        
        # Make sure tracing is on
        if not tracemalloc.is_tracing():
            tracemalloc.start()

    def start_stage(self, stage_name: str):
        if self._current_stage is not None:
            self.end_stage()
        
        self._current_stage = stage_name
        self._stage_start_time = time.time()
        self._stage_start_mem = tracemalloc.get_traced_memory()[0] / (1024 * 1024)
        print(f"[{time.strftime('%H:%M:%S')}] {stage_name} START")

    def end_stage(self, rows_processed: int = 0, status: str = "SUCCESS"):
        if self._current_stage is None:
            return
            
        end_time = time.time()
        end_mem = tracemalloc.get_traced_memory()[0] / (1024 * 1024)
        duration = end_time - self._stage_start_time
        
        stage_data = {
            "stage_name": self._current_stage,
            "start_time": self._stage_start_time,
            "end_time": end_time,
            "duration_seconds": duration,
            "memory_before_mb": self._stage_start_mem,
            "memory_after_mb": end_mem,
            "memory_delta_mb": end_mem - self._stage_start_mem,
            "rows_processed": rows_processed,
            "status": status
        }
        
        self.stages.append(stage_data)
        
        print(f"[{time.strftime('%H:%M:%S')}] {self._current_stage} COMPLETE - {duration:.2f}s - {stage_data['memory_delta_mb']:.1f}MB")
        
        self._current_stage = None
        self.save_report()

    def save_report(self):
        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump(self.stages, f, indent=4)
