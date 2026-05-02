# CANVAS Project — main.py

import time
import threading
import webbrowser

from can_bus.can_network     import CANNetwork
from lin_bus.tpms_ecu        import TPMSECU
from lin_bus.window_seat_ecu import WindowSeatECU
from gateway.gateway_ecu     import GatewayECU
from ethernet.adas_ecu       import ADASECU
from vehicle.ignition        import IgnitionSystem
from vehicle.fault_manager   import FaultManager
from vehicle.fault_injector  import init_injector
from app                     import start_server

def open_browser():
    """Wait 2 seconds then open browser automatically"""
    time.sleep(2)
    webbrowser.open('http://localhost:5000')
    print("[CANVAS] Browser opened → http://localhost:5000")

def main():
    print("=" * 60)
    print("       CANVAS — Hybrid Vehicle Network Simulator")
    print("       CAN Bus | LIN Bus | Automotive Ethernet")
    print("=" * 60)

    lin_bus      = {}
    ethernet_bus = {}

    # ── CAN Bus ───────────────────────────────────────────────
    print("\n[CANVAS] Starting CAN Bus layer...")
    can_network = CANNetwork()
    can_network.start()

    # ── LIN Bus ───────────────────────────────────────────────
    print("\n[CANVAS] Starting LIN Bus layer...")
    tpms_ecu        = TPMSECU(lin_bus)
    window_seat_ecu = WindowSeatECU(lin_bus)
    tpms_ecu.start()
    window_seat_ecu.start()

    # ── Gateway ───────────────────────────────────────────────
    print("\n[CANVAS] Starting Gateway ECU...")
    gateway = GatewayECU(
        can_bus      = can_network.get_bus(),
        lin_bus      = lin_bus,
        ethernet_bus = ethernet_bus
    )
    gateway.start()

    # ── ADAS ──────────────────────────────────────────────────
    print("\n[CANVAS] Starting ADAS ECU...")
    adas = ADASECU(ethernet_bus)
    adas.start()

    # ── Fault Manager ─────────────────────────────────────────
    print("\n[CANVAS] Starting Fault Manager...")
    fault_mgr = FaultManager(ethernet_bus)
    fault_mgr.start()

    # ── Fault Injector ────────────────────────────────────────
    print("\n[CANVAS] Starting Fault Injector...")
    injector = init_injector(ethernet_bus)

    # ── Ignition in background ────────────────────────────────
    print("\n[CANVAS] Starting ignition sequence...")
    ignition = IgnitionSystem(ethernet_bus)
    ignition.start()
    time.sleep(0.5)

    # ── Auto open browser ─────────────────────────────────────
    browser_thread = threading.Thread(
        target=open_browser, daemon=True)
    browser_thread.start()

    # ── Dashboard ─────────────────────────────────────────────
    print("\n[CANVAS] Launching Mercedes HMI Dashboard...")
    print("=" * 60)
    print("  Browser will open automatically...")
    print("  Or manually go to → http://localhost:5000")
    print("  Press Ctrl+C to shut down CANVAS.")
    print("=" * 60 + "\n")

    try:
        start_server(ethernet_bus, can_network)
    except KeyboardInterrupt:
        print("\n[CANVAS] Shutdown signal received...")
    finally:
        ignition.stop()
        fault_mgr.stop()
        injector.stop()
        adas.stop()
        gateway.stop()
        tpms_ecu.stop()
        window_seat_ecu.stop()
        can_network.stop()
        print("[CANVAS] All systems stopped. 👋")

if __name__ == "__main__":
    main()