from pathlib import Path

# Project root = wherever this file lives
ROOT = Path(__file__).parent

DB_PATH              = ROOT / "incidents.db"
DEVICE_HEALTH_JSON   = ROOT / "data" / "device_health.json"
NETWORK_HEALTH_JSON  = ROOT / "data" / "network_health.json"
CLIENT_HEALTH_JSON   = ROOT / "data" / "client_health.json"
ISSUES_JSON          = ROOT / "data" / "issues.json"
SIMULATED_JSON       = ROOT / "data" / "device_health_simulated.json"
