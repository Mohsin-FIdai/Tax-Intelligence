"""
Test configuration — mocks heavy ML dependencies so the test suite
runs instantly in CI without torch, faiss, or sentence-transformers.
"""
import sys
from unittest.mock import MagicMock, patch

import pytest
import pandas as pd

# ---------------------------------------------------------------------------
# 1.  Inject MagicMock modules for every heavy ML package *and* their
#     known sub-modules BEFORE any project code is imported.  This lets
#     `import torch`, `import faiss`, `from faiss.loader import …`, etc.
#     succeed even when the real packages are not installed (CI).
# ---------------------------------------------------------------------------
_MOCK_PACKAGES = [
    "torch", "torch.cuda", "torch.nn", "torch.utils",
    "transformers",
    "sentence_transformers",
    "faiss", "faiss.loader", "faiss.swigfaiss", "faiss.swigfaiss_avx2",
]
for _pkg in _MOCK_PACKAGES:
    sys.modules.setdefault(_pkg, MagicMock())

# ---------------------------------------------------------------------------
# 2.  Patch heavy IO singletons at the module level so that importing
#     `backend.main` never touches the filesystem or real models.
# ---------------------------------------------------------------------------
patcher1 = patch("backend.services.data_service.DataService")
patcher2 = patch("backend.api.routes_resolution._init_raw_cache")
patcher3 = patch("backend.api.routes_resolution.get_resolution_reviews")
patcher4 = patch("backend.services.embedding_service.EmbeddingService")

MockDataService = patcher1.start()
patcher2.start()
patcher3.start()
patcher4.start()

instance = MockDataService.return_value
instance.is_loaded = True
instance.citizens_df = pd.DataFrame()
instance.get_stats.return_value = {"total_citizens": 0, "total_flagged": 0}
