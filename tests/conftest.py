import sys
import pytest
from unittest.mock import MagicMock, patch
import pandas as pd

sys.modules['torch'] = MagicMock()
sys.modules['transformers'] = MagicMock()
sys.modules['sentence_transformers'] = MagicMock()
sys.modules['faiss'] = MagicMock()

# Mock heavy IO services globally for the entire test session
patcher1 = patch('backend.services.data_service.DataService')
patcher2 = patch('backend.api.routes_resolution._init_raw_cache')
patcher3 = patch('backend.api.routes_resolution.get_resolution_reviews')
patcher4 = patch('backend.services.embedding_service.EmbeddingService')

MockDataService = patcher1.start()
patcher2.start()
patcher3.start()
patcher4.start()

instance = MockDataService.return_value
instance.is_loaded = True
instance.citizens_df = pd.DataFrame()
instance.get_stats.return_value = {'total_citizens': 0, 'total_flagged': 0}
