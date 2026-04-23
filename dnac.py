import requests
import json
from requests.auth import HTTPBasicAuth
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from paths import DEVICE_HEALTH_JSON, NETWORK_HEALTH_JSON, CLIENT_HEALTH_JSON, ISSUES_JSON
from dotenv import load_dotenv
import os

load_dotenv()

BASE_URL = os.getenv("DNAC_URL",  "https://10.10.20.85")
USERNAME = os.getenv("DNAC_USER", "administrator")
PASSWORD = os.getenv("DNAC_PASS", "Cisco1234!")

# Suppress SSL warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Step 1: Get token
auth_response = requests.post(
    f"{BASE_URL}/dna/system/api/v1/auth/token",
    auth=HTTPBasicAuth(USERNAME, PASSWORD),
    verify=False
)
token   = auth_response.json()["Token"]
headers = {"X-Auth-Token": token, "Content-Type": "application/json"}
print("Token acquired")

# Step 2: Define endpoints and output paths
endpoints = {
    "network_health": ("/dna/intent/api/v1/network-health", NETWORK_HEALTH_JSON),
    "device_health":  ("/dna/intent/api/v1/device-health",  DEVICE_HEALTH_JSON),
    "client_health":  ("/dna/intent/api/v1/client-health",  CLIENT_HEALTH_JSON),
    "issues":         ("/dna/intent/api/v1/issues",          ISSUES_JSON),
}

# Step 3: Fetch and save
for name, (path, filepath) in endpoints.items():
    response = requests.get(f"{BASE_URL}{path}", headers=headers, verify=False)
    data     = response.json()
    with open(filepath, "w") as f:
        json.dump(data, f, indent=4)
    print(f"Saved {filepath.name} — Status: {response.status_code}")
