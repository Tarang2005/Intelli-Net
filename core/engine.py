import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import subprocess
import time

ROOT = Path(__file__).parent.parent

def run_stage(script_path, description, arg=None):
    print(f"\n[Intelli-Net] >>> {description}...")
    cmd = [sys.executable, str(script_path)]
    if arg:
        cmd.append(arg)
    try:
        subprocess.run(cmd, check=True)
        print(f"Done.")
    except subprocess.CalledProcessError:
        print(f"Error executing {script_path.name}")
    except FileNotFoundError:
        print(f"Script not found: {script_path}")

def start_autonomous_demo():
    print("=" * 60)
    print("      Intelli-Net AUTONOMOUS PIPELINE ENGINE")
    print("=" * 60)

    run_stage(ROOT / "tools" / "simulate_failure.py", "Stage 1: Injecting sw2 CPU Anomaly", arg="2")

    print("\nSyncing Telemetry with Dashboard (5s)...")
    time.sleep(5)

    run_stage(ROOT / "core" / "genai.py", "Stage 2: Generating GenAI Root Cause Analysis")

    print("\nFinalizing Incident Archive (3s)...")
    time.sleep(3)

    run_stage(ROOT / "core" / "webhook.py", "Stage 3: Broadcasting Alert to Discord")

    print("\n" + "-" * 60)
    print("INCIDENT BROADCAST COMPLETE — Dashboard: RED / OPEN")
    print("-" * 60)

    input("\n[ACTION REQUIRED] Press Enter to execute Self-Healing...")

    run_stage(ROOT / "tools" / "manual_resolver.py", "Stage 4: Applying Remediation Logic", arg="all")

    print("\nSystem Healed — Dashboard: GREEN / RESOLVED")
    print("=" * 60)

if __name__ == "__main__":
    start_autonomous_demo()
