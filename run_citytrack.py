"""
CityTrack Single-Command Automated Launcher Script
Starts the FastAPI Backend, WebSockets, Frontend, and Live GPS Telemetry Simulator.
"""

import sys
import os
import time
import webbrowser
import threading
import subprocess

# Add backend directory to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
sys.path.insert(0, BACKEND_DIR)

def start_gps_simulator():
    """Runs the live vehicle position simulator after giving the server 3 seconds to spin up."""
    time.sleep(4)
    print("\n[INFO] Launching Live Vehicle GPS Simulator...")
    sim_script = os.path.join(BASE_DIR, "simulation", "gps_simulator.py")
    try:
        subprocess.run([sys.executable, sim_script], check=False)
    except Exception as e:
        print(f"[Notice] Simulator: {e}")

def main():
    print("================================================================")
    print("CityTrack - Realtime Small City Transit Platform")
    print("================================================================")
    print("1. Initializing Database & Seed Data...")
    print("2. Starting FastAPI Backend & WebSockets on http://localhost:8000")
    print("3. Serving Leaflet.js Passenger & Admin Map Dashboard...")
    print("================================================ launch \n")

    # Launch GPS simulator thread
    sim_thread = threading.Thread(target=start_gps_simulator, daemon=True)
    sim_thread.start()

    # Open web browser after 2 seconds
    threading.Thread(
        target=lambda: (time.sleep(2.5), webbrowser.open("http://localhost:8000")),
        daemon=True
    ).start()

    # Run Uvicorn Server
    import uvicorn
    from app.main import app
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

if __name__ == "__main__":
    main()
