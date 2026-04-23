import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import sqlite3
from datetime import datetime, timezone

from paths import DB_PATH, DEVICE_HEALTH_JSON, SIMULATED_JSON

FAILURE_SCENARIOS = {
    "1": {
        "label": "Device Critical: sw1 unreachable (Total Network Drop)",
        "device": "sw1",
        "changes": {
            "reachabilityHealth": "UNREACHABLE",
            "overallHealth": 0,
            "cpuHealth": 0,
            "cpuUtilization": 0.0,
            "memoryUtilizationHealth": 0.0,
        }
    },
    "2": {
        "label": "Performance Critical: sw2 CPU Spike (95%)",
        "device": "sw2",
        "changes": {
            "cpuUtilization": 95.0,
            "cpuHealth": 5,
            "overallHealth": 10,
        }
    },
    "3": {
        "label": "Alert: sw3 Process Loop (CPU at 88%)",
        "device": "sw3",
        "changes": {
            "cpuUtilization": 88.0,
            "cpuHealth": 15,
            "overallHealth": 20,
        }
    },
    "4": {
        "label": "High Load: sw4 Traffic Congestion (CPU at 92%)",
        "device": "sw4",
        "changes": {
            "cpuUtilization": 92.0,
            "cpuHealth": 8,
            "overallHealth": 12,
        }
    },
}

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

def open_ticket(device_name, ip_address, raw_error_log):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.now(timezone.utc).isoformat(sep=" ", timespec="seconds")
    c.execute("""
        INSERT INTO incidents (device_name, ip_address, status, raw_error_log, created_at)
        VALUES (?, ?, 'OPEN', ?, ?)
    """, (device_name, ip_address, json.dumps(raw_error_log, indent=2), now))
    ticket_id = c.lastrowid
    conn.commit()
    conn.close()
    return ticket_id, now

def main():
    print("\n" + "=" * 55)
    print("   Intelli-Net FAILURE SIMULATOR")
    print("=" * 55)

    if len(sys.argv) > 1:
        choice = sys.argv[1]
        print(f"🤖 Automated Trigger: Choice [{choice}]")
    else:
        print("\nPick a failure scenario:\n")
        for key, s in FAILURE_SCENARIOS.items():
            print(f"   [{key}] {s['label']}")
        print()
        choice = input("Enter choice (1-4): ").strip()

    if choice not in FAILURE_SCENARIOS:
        print("❌ Invalid choice.")
        return

    scenario      = FAILURE_SCENARIOS[choice]
    target_device = scenario["device"]

    with open(DEVICE_HEALTH_JSON, "r") as f:
        data = json.load(f)

    target = next((d for d in data["response"] if d["name"] == target_device), None)
    if not target:
        print(f"❌ Device {target_device} not found.")
        return

    print(f"\n🔧 Injecting: {scenario['label']}")
    for key, val in scenario["changes"].items():
        target[key] = val

    raw_error_log = {
        "device_name":      target["name"],
        "ip_address":       target["ipAddress"],
        "overallHealth":    target["overallHealth"],
        "reachabilityHealth": target["reachabilityHealth"],
        "cpuUtilization":   target.get("cpuUtilization", 26.0),
        "memoryUtilization": target.get("memoryUtilization", 67.0),
        "cpuHealth":        target.get("cpuHealth", 100),
        "osVersion":        target.get("osVersion", "17.12.1prd9"),
        "timestamp":        datetime.now(timezone.utc).isoformat()
    }

    init_db()
    ticket_id, created_at = open_ticket(target["name"], target["ipAddress"], raw_error_log)

    print(f"\n{'=' * 55}")
    print(f"   🎫 TICKET CREATED: #{ticket_id}")
    print(f"   STATE: {target['name']} -> CRITICAL")
    print(f"{'=' * 55}\n")

    # Save modified JSON for dashboard to pick up
    with open(DEVICE_HEALTH_JSON, "w") as f:
        json.dump(data, f, indent=4)
    with open(SIMULATED_JSON, "w") as f:
        json.dump(data, f, indent=4)

    print(f"   ✅ Logged to incidents.db")
    print(f"   ✅ device_health.json updated for dashboard\n")

if __name__ == "__main__":
    main()
