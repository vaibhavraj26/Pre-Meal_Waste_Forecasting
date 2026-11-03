import sys
import subprocess
import time
import os
import signal
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def run_both():
    print("================================================================")
    print(" Starting Smart Mess Food Waste Prediction System...")
    print(" Backend ML API:  http://localhost:5000")
    print(" Web Application: http://localhost:3000")
    print("================================================================")

    # 1. Start Python Flask Backend
    py_cmd = [sys.executable, str(BASE_DIR / "backend" / "app.py")]
    py_proc = subprocess.Popen(py_cmd, cwd=str(BASE_DIR))
    print(f"[*] Python Flask Backend started (PID {py_proc.pid})")

    # Give Python a brief moment to initialize
    time.sleep(2)

    # 2. Start Node.js Express Server
    node_cmd = ["node", str(BASE_DIR / "server" / "server.js")]
    node_proc = subprocess.Popen(node_cmd, cwd=str(BASE_DIR))
    print(f"[*] Node.js Web App started (PID {node_proc.pid})")
    print("================================================================")
    print(" Web Application is LIVE at: http://localhost:3000")
    print(" Press Ctrl+C to stop both servers.")
    print("================================================================")

    try:
        while True:
            time.sleep(1)
            if py_proc.poll() is not None:
                print("[!] Python backend terminated unexpectedly.")
                break
            if node_proc.poll() is not None:
                print("[!] Node web server terminated unexpectedly.")
                break
    except KeyboardInterrupt:
        print("\nStopping services...")
    finally:
        try:
            py_proc.terminate()
            node_proc.terminate()
        except Exception:
            pass
        print("Both services stopped.")

if __name__ == "__main__":
    run_both()
