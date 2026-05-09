# CANVAS Project   main.py

import time
import threading
import webbrowser
import os
import sys

# Add the current directory to Python path if run from here
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import app, socketio, broadcast_loop
import sim_manager

def open_browser():
    """Wait 2 seconds then open browser automatically"""
    time.sleep(2)
    webbrowser.open('http://localhost:5000')
    print("[CANVAS] Browser opened -> http://localhost:5000")

def main():
    print("=" * 60)
    print("       CANVAS   Hybrid Vehicle Network Simulator")
    print("       CAN Bus | LIN Bus | Automotive Ethernet")
    print("=" * 60)
    
    # -- Auto open browser -------------------------------------
    browser_thread = threading.Thread(
        target=open_browser, daemon=True)
    browser_thread.start()

    # -- Dashboard ---------------------------------------------
    print("\n[CANVAS] Launching Mercedes HMI Dashboard...")
    print("=" * 60)
    print("  Browser will open automatically...")
    print("  Or manually go to -> http://localhost:5000")
    print("  Click 'START SIMULATION' in the dashboard to begin.")
    print("  Press Ctrl+C to shut down CANVAS.")
    print("=" * 60 + "\n")

    # Start the broadcast loop
    threading.Thread(target=broadcast_loop, daemon=True).start()

    try:
        socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
    except KeyboardInterrupt:
        print("\n[CANVAS] Shutdown signal received...")
    finally:
        sim_manager.sim_manager_instance.stop_all()
        print("[CANVAS] All systems stopped. [BYE]")

if __name__ == "__main__":
    main()