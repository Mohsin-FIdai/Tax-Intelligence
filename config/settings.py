import os
from pathlib import Path

# "?"?"? Paths "?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed_v2"
RAW_UPLOADS_DIR = DATA_DIR / "raw_uploads"
MODELS_DIR = BASE_DIR / "models_store"
REPORTS_DIR = BASE_DIR / "reports"
CACHE_DIR = DATA_DIR / ".cache"

# Optional Pipeline / Compute settings
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "True").lower() in ("true", "1", "yes")
COMPUTE_DEVICE = os.getenv("COMPUTE_DEVICE", "auto").lower()
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 50000))
MAX_WORKERS = int(os.getenv("MAX_WORKERS", max(1, os.cpu_count() - 1)))

for d in [PROCESSED_DIR, RAW_UPLOADS_DIR, MODELS_DIR, REPORTS_DIR, CACHE_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# "?"?"? Entity Resolution Weights "?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?
ER_CNIC_WEIGHT = 70
ER_NAME_WEIGHT = 20
ER_FATHER_NAME_WEIGHT = 15
ER_PHONE_WEIGHT = 10
ER_ADDRESS_WEIGHT = 5
ER_NTN_WEIGHT = 35
ER_CITY_WEIGHT = 0

# "?"?"? Entity Resolution Thresholds "?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?
ER_CONFIDENCE_THRESHOLD = 70
ER_NAME_SIMILARITY_THRESHOLD = 0.85
ER_NAME_EXACT_THRESHOLD = 90
ER_NAME_PARTIAL_THRESHOLD = 70
ER_NAME_CONFLICT_THRESHOLD = 40

# Normalized decision thresholds (based on 0-100 normalized score of sum=155)
ER_MERGE_THRESHOLD = 50.0             # Replaces the impossible 85.0 for phone+name+address (which maxed at 35/155 = 22.5%)
ER_STRONG_MERGE_THRESHOLD = 60.0      # Replaces 75.0 for CNIC+Name (which maxed at 90/155 = 58%)
ER_REJECT_THRESHOLD = 15.0            # Replaces 30.0 (which was 30 unnormalized)

# "?"?"? ML Model Parameters "?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?
ISO_FOREST_PARAMS = {
    "n_estimators": 200,
    "contamination": 0.15,
    "max_features": 0.8,
    "random_state": 42,
}

XGBOOST_PARAMS = {
    "n_estimators": 200,
    "max_depth": 6,
    "learning_rate": 0.1,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "random_state": 42,
    "use_label_encoder": False,
    "eval_metric": "logloss",
}

RF_PARAMS = {
    "n_estimators": 200,
    "max_depth": 10,
    "random_state": 42,
}

# "?"?"? Risk Scoring Weights "?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?
NET_WORTH_WEIGHTS = {
    "vehicle": 1.0,
    "property": 1.0,
    "business": 0.8,
    "utility_lifestyle": 0.3,
    "travel": 0.2,
    "banking": 0.5,
}

DEVIATION_WEIGHTS = {
    "income_networth_gap": 0.30,
    "tax_gap": 0.25,
    "lifestyle_gap": 0.20,
    "anomaly_score": 0.15,
    "filing_penalty": 0.10,
}

# "?"?"? Risk Categories "?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?
RISK_CATEGORIES = {
    "A": {"range": (0, 20), "label": "Tax Compliant", "color": "#10b981", "emoji": ""},
    "B": {"range": (21, 40), "label": "Needs Review", "color": "#3b82f6", "emoji": ""},
    "C": {"range": (41, 60), "label": "Suspicious", "color": "#f59e0b", "emoji": ""},
    "D": {"range": (61, 80), "label": "Likely Tax Evader", "color": "#ea580c", "emoji": ""},
    "E": {"range": (81, 100), "label": "Confirmed Tax Deviation", "color": "#dc2626", "emoji": ""},
}

# "?"?"? Pakistani Data Constants "?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?
PROVINCES = {
    "Punjab": {"code": "3", "weight": 0.53},
    "Sindh": {"code": "4", "weight": 0.23},
    "KPK": {"code": "1", "weight": 0.12},
    "Balochistan": {"code": "5", "weight": 0.06},
    "Islamabad": {"code": "6", "weight": 0.04},
    "AJK": {"code": "7", "weight": 0.01},
    "GB": {"code": "7", "weight": 0.01},
}

CITIES_BY_PROVINCE = {
    "Punjab": ["Lahore", "Faisalabad", "Rawalpindi", "Gujranwala", "Multan",
               "Sargodha", "Sialkot", "Bahawalpur", "Sheikhupura", "Gujrat",
               "Sahiwal", "Jhelum", "Rahim Yar Khan", "Dera Ghazi Khan"],
    "Sindh": ["Karachi", "Hyderabad", "Sukkur", "Larkana", "Nawabshah",
              "Mirpur Khas", "Jacobabad", "Shikarpur", "Khairpur"],
    "KPK": ["Peshawar", "Mardan", "Mingora", "Kohat", "Abbottabad",
            "Dera Ismail Khan", "Swabi", "Mansehra", "Nowshera"],
    "Balochistan": ["Quetta", "Turbat", "Khuzdar", "Hub", "Chaman",
                    "Gwadar", "Sibi", "Loralai", "Zhob"],
    "Islamabad": ["Islamabad"],
    "AJK": ["Muzaffarabad", "Mirpur", "Rawalakot", "Kotli"],
    "GB": ["Gilgit", "Skardu", "Chilas", "Hunza"],
}

# "?"?"? UI Theme Constants "?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?"?
THEME = {
    "bg_primary": "#0a0a0f",
    "bg_secondary": "#12121a",
    "bg_card": "#1a1a2e",
    "bg_card_hover": "#22223a",
    "accent": "#00d4aa",
    "accent_secondary": "#4a9eff",
    "danger": "#ff3355",
    "warning": "#ffd000",
    "success": "#00d4aa",
    "text_primary": "#e8e8ed",
    "text_secondary": "#8888a0",
    "border": "#2a2a3e",
    "gradient_start": "#00d4aa",
    "gradient_end": "#4a9eff",
}

# --- Restored for ML Pipeline Compatibility ---
ANOMALY_RATE = 0.05
TAX_FILING_RATE = 0.1
