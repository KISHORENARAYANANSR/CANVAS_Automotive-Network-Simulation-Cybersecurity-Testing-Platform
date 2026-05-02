# CANVAS Project
# Module: CAN Bus
# File: abs_ecu.py
# ABS ECU with real 10ms CAN cycle time + DTC

import can
import random
import threading
from can_bus.can_timing  import can_timing_monitor
from vehicle.dtc_manager import dtc_manager

class ABSECU:
    def __init__(self, bus, drive_cycle):
        self.bus     = bus
        self.dc      = drive_cycle
        self.running = True

    def send_wheel_data(self):
        """Send wheel speeds at real 10ms cycle"""
        timer = can_timing_monitor.register('ABS')
        while self.running:
            base = int(self.dc.speed)
            fl   = max(0, base + random.randint(-1, 1))
            fr   = max(0, base + random.randint(-1, 1))
            rl   = max(0, base + random.randint(-1, 1))
            rr   = max(0, base + random.randint(-1, 1))

            # Detect wheel speed mismatch — set DTC
            speeds = [fl, fr, rl, rr]
            if max(speeds) - min(speeds) > 15:
                dtc_manager.set_fault('C0035')

            msg = can.Message(
                arbitration_id=0x200,
                data=[fl, fr, rl, rr,
                      0x00, 0x00, 0x00, 0x00],
                is_extended_id=False
            )
            try:
                self.bus.send(msg)
            except Exception:
                dtc_manager.set_fault('U0121')

            print(f"[ABS ECU] Wheels "
                  f"FL:{fl} FR:{fr} "
                  f"RL:{rl} RR:{rr} km/h")
            timer.wait()

    def send_brake_data(self):
        """Send brake pressure at 10ms cycle"""
        timer = can_timing_monitor.register('ABS_BRAKE')
        while self.running:
            brake = int(self.dc.brake_pressure)
            msg   = can.Message(
                arbitration_id=0x201,
                data=[brake, 0x00, 0x00, 0x00,
                      0x00, 0x00, 0x00, 0x00],
                is_extended_id=False
            )
            try:
                self.bus.send(msg)
            except Exception:
                pass
            print(f"[ABS ECU] Brake:{brake} bar")
            timer.wait()

    def start(self):
        print("[ABS ECU] Starting "
              "(10ms CAN cycle)...")
        threads = [
            threading.Thread(target=self.send_wheel_data),
            threading.Thread(target=self.send_brake_data),
        ]
        for t in threads:
            t.daemon = True
            t.start()

    def stop(self):
        self.running = False
        print("[ABS ECU] Stopped.")