import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import sqlite3
from openai import OpenAI
from dotenv import load_dotenv
import os

from paths import DB_PATH

load_dotenv(Path(__file__).parent.parent / ".env")

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY", ""),
    base_url="https://api.groq.com/openai/v1"
)

def build_prompt(raw_error_log):
    return f"""
You are a senior network engineer analyzing a network device alert.
A device in our enterprise network has triggered an incident ticket.

Here is the raw telemetry data:
{json.dumps(raw_error_log, indent=2)}

Provide:
1. WHAT HAPPENED - plain English, 1-2 sentences
2. LIKELY CAUSE - 1-2 sentences
3. SEVERITY - one word: Critical / High / Medium / Low
4. SUGGESTED FIX - 2-3 bullet points

No markdown. Plain text only.
""".strip()

def analyze_ticket(raw_error_log):
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a precise network engineering AI."},
                {"role": "user", "content": build_prompt(raw_error_log)}
            ],
            temperature=0.1,
            max_tokens=300
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error processing telemetry: {e}"

if __name__ == "__main__":
    conn   = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ticket_id, device_name, raw_error_log
        FROM incidents
        WHERE ai_root_cause IS NULL
        ORDER BY ticket_id DESC LIMIT 1
    """)
    ticket = cursor.fetchone()

    if ticket:
        ticket_id, device_name, raw_log_json = ticket
        print(f"\n[Intelli-Net] Analyzing Ticket #{ticket_id} for {device_name}...")
        print("─" * 55)
        raw_error_log  = json.loads(raw_log_json)
        ai_explanation = analyze_ticket(raw_error_log)
        print(ai_explanation)
        cursor.execute("UPDATE incidents SET ai_root_cause=? WHERE ticket_id=?", (ai_explanation, ticket_id))
        conn.commit()
        print("─" * 55)
        print(f"Analysis saved for Ticket #{ticket_id}")
    else:
        print("\n[Intelli-Net] No new tickets needing analysis.")

    conn.close()
