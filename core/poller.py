import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
import json
import sqlite3
import time
import logging
from datetime import datetime, timezone
from requests.auth import HTTPBasicAuth
from urllib3.exceptions import InsecureRequestWarning
import urllib3

urllib3.disable_warnings(InsecureRequestWarning)
from openai import OpenAI
from dotenv import load_dotenv
import os

from paths import DB_PATH, DEVICE_HEALTH_JSON

load_dotenv(Path(__file__).parent.parent / ".env")
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# ─── CONFIG ───────────────────────────────────────────────────────────────────
BASE_URL         = os.getenv("DNAC_URL",      "https://10.10.20.85")
USERNAME         = os.getenv("DNAC_USER",     "administrator")
PASSWORD         = os.getenv("DNAC_PASS",     "Cisco1234!")
GROQ_API_KEY     = os.getenv("GROQ_API_KEY",  "")
DISCORD_WEBHOOK  = os.getenv("DISCORD_WEBHOOK", "")
POLL_INTERVAL    = 300
HEALTH_THRESHOLD = 30

# ─── LOGGING ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(Path(__file__).parent.parent / "poller.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# ─── GROQ CLIENT ──────────────────────────────────────────────────────────────
ai_client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

# ─── DATABASE ─────────────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS incidents (
            ticket_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            device_name     TEXT    NOT NULL,
            ip_address      TEXT    NOT NULL,
            status          TEXT    NOT NULL DEFAULT 'OPEN',
            raw_error_log   TEXT,
            ai_root_cause   TEXT,
            created_at      TIMESTAMP NOT NULL,
            resolved_at     TIMESTAMP,
            mttr_minutes    REAL
        )
    """)
    conn.commit()
    conn.close()

def get_open_ticket(device_name):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT ticket_id, created_at FROM incidents WHERE device_name=? AND status='OPEN'", (device_name,))
    row = c.fetchone()
    conn.close()
    return row

def open_ticket(device_name, ip_address, raw_error_log):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.now(timezone.utc).isoformat(sep=" ", timespec="seconds")
    c.execute("""
        INSERT INTO incidents (device_name, ip_address, status, raw_error_log, created_at)
        VALUES (?, ?, 'OPEN', ?, ?)
    """, (device_name, ip_address, json.dumps(raw_error_log), now))
    ticket_id = c.lastrowid
    conn.commit()
    conn.close()
    log.warning("TICKET OPENED | #%d | %s (%s)", ticket_id, device_name, ip_address)
    return ticket_id, now

def save_ai_explanation(ticket_id, explanation):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE incidents SET ai_root_cause=? WHERE ticket_id=?", (explanation, ticket_id))
    conn.commit()
    conn.close()

def resolve_ticket(ticket_id, created_at_str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.now(timezone.utc)
    resolved_at = now.isoformat(sep=" ", timespec="seconds")
    mttr = round((now - datetime.fromisoformat(created_at_str)).total_seconds() / 60, 2)
    c.execute("""
        UPDATE incidents SET status='RESOLVED', resolved_at=?, mttr_minutes=?
        WHERE ticket_id=?
    """, (resolved_at, mttr, ticket_id))
    conn.commit()
    conn.close()
    log.info("TICKET RESOLVED | #%d | MTTR: %.1f min", ticket_id, mttr)
    return mttr

# ─── GENAI ────────────────────────────────────────────────────────────────────
def run_ai_analysis(ticket_id, raw_error_log):
    log.info("Sending Ticket #%d to Groq...", ticket_id)
    prompt = f"""
You are a senior network engineer analyzing a network device alert.
Here is the raw telemetry data:
{json.dumps(raw_error_log, indent=2)}

Provide:
1. WHAT HAPPENED - plain English, 1-2 sentences
2. LIKELY CAUSE - 1-2 sentences
3. SEVERITY - one word: Critical / High / Medium / Low
4. SUGGESTED FIX - 2-3 bullet points

No markdown. Plain text only.
""".strip()
    try:
        response = ai_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a precise network engineering AI."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=300
        )
        explanation = response.choices[0].message.content.strip()
        save_ai_explanation(ticket_id, explanation)
        log.info("AI analysis saved for Ticket #%d", ticket_id)
        return explanation
    except Exception as e:
        log.error("GenAI error for Ticket #%d: %s", ticket_id, e)
        return None

# ─── DISCORD ──────────────────────────────────────────────────────────────────
def send_discord_alert(ticket_id, device_name, ip_address, ai_explanation, status="OPEN"):
    if not DISCORD_WEBHOOK:
        log.warning("No Discord webhook configured — skipping alert")
        return
    try:
        if status == "OPEN":
            message = (
                f"**NETWORK ALERT: Ticket #{ticket_id}**\n"
                f"**Device:** {device_name} ({ip_address})\n"
                f"**Status:** OPEN\n\n"
                f"**AI Analysis:**\n{ai_explanation or 'Analysis pending...'}"
            )
        else:
            message = (
                f"**RESOLVED: Ticket #{ticket_id}**\n"
                f"**Device:** {device_name} ({ip_address})\n"
                f"**Status:** RESOLVED"
            )
        resp = requests.post(DISCORD_WEBHOOK, json={"content": message}, timeout=10)
        if resp.status_code in [200, 204]:
            log.info("Discord alert sent for Ticket #%d", ticket_id)
        else:
            log.error("Discord failed: %s", resp.text)
    except Exception as e:
        log.error("Discord error: %s", e)

# ─── DNAC ─────────────────────────────────────────────────────────────────────
def get_token():
    resp = requests.post(
        f"{BASE_URL}/dna/system/api/v1/auth/token",
        auth=HTTPBasicAuth(USERNAME, PASSWORD),
        verify=False, timeout=15
    )
    resp.raise_for_status()
    log.info("Auth token refreshed")
    return resp.json()["Token"]

def fetch_and_save_device_health(headers):
    resp = requests.get(
        f"{BASE_URL}/dna/intent/api/v1/device-health",
        headers=headers, verify=False, timeout=15
    )
    resp.raise_for_status()
    data = resp.json()
    with open(DEVICE_HEALTH_JSON, "w") as f:
        json.dump(data, f, indent=4)
    return data.get("response", [])

# ─── STATE COMPARISON ─────────────────────────────────────────────────────────
def compare_and_act(devices, previous_state):
    current_state = {}
    for device in devices:
        name         = device.get("name", "unknown")
        ip           = device.get("ipAddress", "0.0.0.0")
        health       = device.get("overallHealth", -1)
        reachability = device.get("reachabilityHealth", "UNKNOWN")
        cpu          = device.get("cpuUtilization", 0)
        memory       = device.get("memoryUtilization", 0)

        is_unhealthy = (
            (health != -1 and health <= HEALTH_THRESHOLD) or
            (reachability not in ("REACHABLE", ""))
        )
        current_state[name] = {"ip": ip, "health": health, "reachability": reachability, "unhealthy": is_unhealthy}

        was_unhealthy   = previous_state.get(name, {}).get("unhealthy", False)
        open_ticket_row = get_open_ticket(name)

        if is_unhealthy and not was_unhealthy:
            raw_log = {
                "device_name": name, "ip_address": ip,
                "overallHealth": health, "reachabilityHealth": reachability,
                "cpuUtilization": cpu, "memoryUtilization": memory,
                "interfaceLinkErrHealth": device.get("interfaceLinkErrHealth"),
                "cpuHealth": device.get("cpuHealth"),
                "memoryUtilizationHealth": device.get("memoryUtilizationHealth"),
                "osVersion": device.get("osVersion"),
                "model": device.get("model"),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            ticket_id, _ = open_ticket(name, ip, raw_log)
            explanation  = run_ai_analysis(ticket_id, raw_log)
            send_discord_alert(ticket_id, name, ip, explanation, status="OPEN")

        elif not is_unhealthy and was_unhealthy and open_ticket_row:
            ticket_id, created_at = open_ticket_row
            resolve_ticket(ticket_id, created_at)
            send_discord_alert(ticket_id, name, ip, None, status="RESOLVED")

        else:
            log.info("%-6s | Health: %3s | CPU: %5.1f%% | %s",
                     name, health, cpu, "DEGRADED" if is_unhealthy else "HEALTHY")

    return current_state

# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    init_db()
    previous_state = {}
    last_auth = 0

    log.info("Intelli-Net POLLER STARTED — polling every %ds", POLL_INTERVAL)

    while True:
        try:
            if time.time() - last_auth > 3600:
                token = get_token()
                headers = {"X-Auth-Token": token, "Content-Type": "application/json"}
                last_auth = time.time()

            log.info("─" * 55)
            devices = fetch_and_save_device_health(headers)
            log.info("%d device(s) returned", len(devices))
            previous_state = compare_and_act(devices, previous_state)

        except requests.exceptions.ConnectionError:
            log.error("Cannot reach DNAC (VPN connected?) — retry in %ds", POLL_INTERVAL)
        except requests.exceptions.HTTPError as e:
            log.error("HTTP error: %s", e)
            last_auth = 0
        except Exception as e:
            log.exception("Unexpected error: %s", e)

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
