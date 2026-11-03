import sys
import subprocess
import time
import os
import shutil
import signal
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def run_both():
    is_cloud = bool(os.getenv("RENDER") or os.getenv("DYNO") or os.getenv("RAILWAY_STATIC_URL"))
    node_available = shutil.which("node") is not None
    port = os.getenv("PORT")

    # In cloud environments or if Node.js is missing, run Flask in unified mode
    if (is_cloud and port) or not node_available:
        print("================================================================")
        print(" Starting Smart Mess in Unified Fullstack Cloud Mode...")
        print(f" Port: {port or 5000}")
        print("================================================================")
        py_cmd = [sys.executable, str(BASE_DIR / "backend" / "app.py")]
        py_proc = subprocess.Popen(py_cmd, cwd=str(BASE_DIR))
        try:
            py_proc.wait()
        except KeyboardInterrupt:
            py_proc.terminate()
        return

    # Local development mode: Run both Python Flask (5000) and Node.js Express (3000)
    print("================================================================")
    print(" Starting Smart Mess Food Waste Prediction System (Dev Mode)...")
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
