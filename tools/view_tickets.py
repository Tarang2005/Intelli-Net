import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import sqlite3
from paths import DB_PATH

def print_table(rows, headers):
    widths = [max(len(str(r[i])) for r in ([headers] + list(rows))) for i in range(len(headers))]
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    print(fmt.format(*headers))
    print("  ".join("-" * w for w in widths))
    for row in rows:
        print(fmt.format(*[str(x) if x is not None else "—" for x in row]))

def main():
    filter_arg = sys.argv[1] if len(sys.argv) > 1 else "--all"
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if filter_arg == "--open":
        where = "WHERE status='OPEN'"
    elif filter_arg == "--resolved":
        where = "WHERE status='RESOLVED'"
    else:
        where = ""

    c.execute(f"""
        SELECT ticket_id, device_name, ip_address, status,
               created_at, resolved_at, mttr_minutes
        FROM incidents {where}
        ORDER BY ticket_id DESC
    """)
    rows = c.fetchall()
    conn.close()

    if not rows:
        print("No tickets found.")
        return

    headers = ["ID", "Device", "IP", "Status", "Created", "Resolved", "MTTR (min)"]
    print(f"\n{'─'*80}")
    print(f"  INCIDENT TICKETS  ({len(rows)} record(s)  |  filter: {filter_arg})")
    print(f"{'─'*80}\n")
    print_table(rows, headers)

    with sqlite3.connect(DB_PATH) as conn2:
        c2 = conn2.cursor()
        c2.execute("SELECT COUNT(*) FROM incidents WHERE status='OPEN'")
        open_c = c2.fetchone()[0]
        c2.execute("SELECT COUNT(*) FROM incidents WHERE status='RESOLVED'")
        res_c  = c2.fetchone()[0]
        c2.execute("SELECT AVG(mttr_minutes) FROM incidents WHERE mttr_minutes IS NOT NULL")
        avg    = c2.fetchone()[0]
    print(f"\n  Open: {open_c}  |  Resolved: {res_c}  |  Avg MTTR: {round(avg,1) if avg else '—'} min\n")

if __name__ == "__main__":
    main()
