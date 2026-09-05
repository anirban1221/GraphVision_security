import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "ieee-fraud-detection"
STATIC_DIR = BASE_DIR / "backend" / "static"

TEST_TRANSACTION_PATH = DATA_DIR / "test_transaction.csv"
TEST_IDENTITY_PATH = DATA_DIR / "test_identity.csv"
SENTINEL_MODEL_PATH = BASE_DIR / "sentinel_xgb.json"

# Server Configuration
HOST = "0.0.0.0"
PORT = 8000
APP_NAME = "GraphVision Security"

# Replay & Window Constants
DEFAULT_STREAM_SPEED = 2.0
DEFAULT_BUFFER_SIZE = 50000

# Window Constants
WINDOW_5M = 300
WINDOW_30M = 1800
WINDOW_24H = 86400

# Policy Decision Thresholds
THRESHOLD_APPROVE = 0.35
THRESHOLD_REVIEW = 0.65

SPIKE_RATIO_ALERT = 3.0
