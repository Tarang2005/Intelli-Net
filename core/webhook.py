import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import sqlite3
import requests
from dotenv import load_dotenv
import os

from paths import DB_PATH

load_dotenv(Path(__file__).parent.parent / ".env")

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK", "")

def send_alert():
    conn   = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ticket_id, device_name, ip_address, ai_root_cause
        FROM incidents
        WHERE ai_root_cause IS NOT NULL
        ORDER BY ticket_id DESC LIMIT 1
    """)
    ticket = cursor.fetchone()
    conn.close()

    if not ticket:
        print("No analyzed tickets found. Run genai.py first!")
        return

    tid, device, ip, cause = ticket
    payload = {
        "content": (
            f"**NETWORK ALERT: Ticket #{tid}**\n"
            f"**Device:** {device} ({ip})\n"
            f"**Status:** OPEN\n\n"
            f"**AI Analysis:**\n{cause}"
        )
    }

    response = requests.post(DISCORD_WEBHOOK, json=payload, timeout=10)
    if response.status_code in [200, 204]:
        print(f"Alert for Ticket #{tid} sent to Discord!")
    else:
        print(f"Failed: {response.text}")

if __name__ == "__main__":
    send_alert()
