import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import sqlite3
from datetime import datetime, timezone

from paths import DB_PATH, DEVICE_HEALTH_JSON

HEALTHY_BASELINE = {
    "reachabilityHealth":      "REACHABLE",
    "overallHealth":           100,
    "cpuUtilization":          26.0,
    "cpuHealth":               100,
    "memoryUtilization":       67.0,
    "memoryUtilizationHealth": 100,
    "interfaceLinkErrHealth":  10
}

def get_open_tickets():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM incidents WHERE status='OPEN'")
    tickets = c.fetchall()
    conn.close()
    return tickets

def resolve_ticket_in_db(ticket_id, created_at_str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now      = datetime.now(timezone.utc)
    now_str  = now.isoformat(sep=" ", timespec="seconds")
    mttr     = round((now - datetime.fromisoformat(created_at_str)).total_seconds() / 60, 2)
    c.execute("""
        UPDATE incidents SET status='RESOLVED', resolved_at=?, mttr_minutes=?
        WHERE ticket_id=?
    """, (now_str, mttr, ticket_id))
    conn.commit()
    conn.close()
    return now_str, mttr

def heal_device_json(device_name):
    with open(DEVICE_HEALTH_JSON, "r") as f:
        data = json.load(f)
    for device in data["response"]:
        if device["name"] == device_name:
            print(f"🩹 Healing {device_name} in JSON...")
            for key, val in HEALTHY_BASELINE.items():
                if key in device:
                    device[key] = val
            break
    with open(DEVICE_HEALTH_JSON, "w") as f:
        json.dump(data, f, indent=4)

def main():
    print("\n" + "=" * 55)
    print("  Intelli-Net INCIDENT RESOLVER")
    print("=" * 55)

    tickets = get_open_tickets()
    if not tickets:
        print("\n✅ No open incidents. Network is healthy!")
        return

    print(f"\nFound {len(tickets)} Open Incident(s):")
    for t in tickets:
        print(f"  [#{t['ticket_id']}] {t['device_name']} | {t['created_at']}")

    # Support non-interactive mode: python manual_resolver.py <ticket_id|all>
    if len(sys.argv) > 1:
        choice = sys.argv[1].strip()
        print(f"\n🤖 Automated mode: resolving '{choice}'")
    else:
        choice = input("\nEnter Ticket ID to resolve (or 'all'): ").strip()

    if choice.lower() == "all":
        tickets_to_resolve = tickets
    else:
        target = next((t for t in tickets if str(t["ticket_id"]) == choice), None)
        if not target:
            print("Invalid Ticket ID.")
            return
        tickets_to_resolve = [target]

    for t in tickets_to_resolve:
        res_at, mttr = resolve_ticket_in_db(t["ticket_id"], t["created_at"])
        heal_device_json(t["device_name"])
        print(f"\n{'=' * 55}")
        print(f"  ✅ TICKET #{t['ticket_id']} RESOLVED")
        print(f"  Device : {t['device_name']}")
        print(f"  MTTR   : {mttr} minutes")
        print(f"{'=' * 55}")

    print("\n  ✅ Dashboard will now return to baseline.\n")

if __name__ == "__main__":
    main()
