import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import sqlite3
from paths import DB_PATH

def clear_database():
    try:
        conn   = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM incidents")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='incidents'")
        conn.commit()
        conn.close()
        print("🗑️  Database cleared! Next ticket will be #1.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    clear_database()
