from typing import Dict, Any, Optional
import pandas as pd

class PipelineState:
    """
    In-memory state manager to hold DataFrames and arbitrary artifacts
    between pipeline stages, removing the need for redundant disk I/O.
    """
    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._dataframes: Dict[str, pd.DataFrame] = {}

    def set_df(self, key: str, df: pd.DataFrame):
        """Store a DataFrame in memory."""
        if df is not None:
            self._dataframes[key] = df

    def get_df(self, key: str) -> Optional[pd.DataFrame]:
        """Retrieve a DataFrame from memory."""
        return self._dataframes.get(key)

    def set(self, key: str, val: Any):
        """Store arbitrary data."""
        self._data[key] = val

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)
        
    def clear(self):
        self._data.clear()
        self._dataframes.clear()
