import hashlib
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any, Union
import pandas as pd

from config.settings import CACHE_DIR, CACHE_ENABLED

class CacheManager:
    def __init__(self, cache_enabled: bool = CACHE_ENABLED):
        self.cache_dir = CACHE_DIR
        self.cache_enabled = cache_enabled
        self.metadata_file = self.cache_dir / "cache_manifest.json"
        self._manifest = self._load_manifest()

    def _load_manifest(self) -> Dict[str, Any]:
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_manifest(self):
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self._manifest, f, indent=4)

    @staticmethod
    def _compute_hash(files: list[Path]) -> str:
        """Compute SHA-256 over file contents and paths."""
        sha = hashlib.sha256()
        for f in sorted(files):
            if f.exists():
                sha.update(str(f.name).encode('utf-8'))
                sha.update(str(f.stat().st_mtime).encode('utf-8'))
                sha.update(str(f.stat().st_size).encode('utf-8'))
        return sha.hexdigest()

    def get_stage_cache(self, stage_name: str, input_files: list[Path]) -> Optional[Any]:
        if not self.cache_enabled:
            return None
            
        current_hash = self._compute_hash(input_files)
        entry = self._manifest.get(stage_name)
        
        if entry and entry.get("hash") == current_hash:
            cache_file = self.cache_dir / f"{stage_name}.pkl"
            if cache_file.exists():
                try:
                    return pd.read_pickle(cache_file)
                except Exception:
                    return None
        return None

    def set_stage_cache(self, stage_name: str, input_files: list[Path], data: Any):
        if not self.cache_enabled:
            return
            
        current_hash = self._compute_hash(input_files)
        cache_file = self.cache_dir / f"{stage_name}.pkl"
        
        try:
            if isinstance(data, pd.DataFrame):
                data.to_pickle(cache_file)
            elif isinstance(data, dict):
                pd.to_pickle(data, cache_file)
            else:
                return # Cannot cache arbitrary non-pickleable types right now
                
            self._manifest[stage_name] = {
                "hash": current_hash,
                "timestamp": time.time()
            }
            self._save_manifest()
        except Exception as e:
            print(f"Failed to cache {stage_name}: {e}")

