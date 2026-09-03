import os
import logging
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

class ComputeBackend:
    """Abstract base for pipeline compute abstractions."""
    def is_gpu(self) -> bool:
        return False
        
    def to_device(self, data):
        return data
        
    def to_host(self, data):
        return data

class CPUBackend(ComputeBackend):
    pass

class GPUBackend(ComputeBackend):
    def __init__(self):
        try:
            import cupy as cp
            import cudf
            self._cp = cp
            self._cudf = cudf
        except ImportError:
            raise RuntimeError("GPU requested but cupy/cudf not available.")
            
    def is_gpu(self) -> bool:
        return True
        
    def to_device(self, data):
        if isinstance(data, pd.DataFrame):
            return self._cudf.from_pandas(data)
        elif isinstance(data, np.ndarray):
            return self._cp.asarray(data)
        return data

    def to_host(self, data):
        if hasattr(data, "to_pandas"):
            return data.to_pandas()
        elif hasattr(data, "get"): # cupy array
            return data.get()
        return data

def get_compute_backend(device_pref: str = "auto") -> ComputeBackend:
    if device_pref == "gpu":
        try:
            return GPUBackend()
        except RuntimeError as e:
            logger.warning(f"Failed to init GPU backend: {e}")
            return CPUBackend()
    elif device_pref == "auto":
        try:
            return GPUBackend()
        except RuntimeError:
            return CPUBackend()
    else:
        return CPUBackend()
