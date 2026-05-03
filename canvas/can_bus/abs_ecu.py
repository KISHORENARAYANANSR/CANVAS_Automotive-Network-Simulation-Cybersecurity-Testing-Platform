# CANVAS Project
# Module: CAN Bus
# File: abs_ecu.py
# ABS ECU with real 10ms CAN cycle time + DTC

import can
import random
from vehicle.dtc_manager import dtc_manager
from utils.can_codec import codec

class ABSECU(can.Listener):
    def __init__(self, bus, drive_cycle):
        self.bus     = bus
        self.dc      = drive_cycle
        self.running = True

    def send_wheel_data_step(self):
        """Send wheel speeds step"""
        if not self.running: return
        base = int(self.dc.speed)
        fl   = max(0, base + random.randint(-1, 1))
        fr   = max(0, base + random.randint(-1, 1))
        rl   = max(0, base + random.randint(-1, 1))
        rr   = max(0, base + random.randint(-1, 1))

        # Detect wheel speed mismatch   set DTC
        speeds = [fl, fr, rl, rr]
        if max(speeds) - min(speeds) > 15:
            dtc_manager.set_fault('C0035')

        msg = can.Message(
            arbitration_id=0x200,
            data=codec.encode(0x200, {
                'Wheel_Speed_FL': fl,
                'Wheel_Speed_FR': fr,
                'Wheel_Speed_RL': rl,
                'Wheel_Speed_RR': rr
            }),
            is_extended_id=False
        )
        try:
            self.bus.send(msg)
        except Exception:
            dtc_manager.set_fault('U0121')

        print(f"[ABS ECU] Wheels "
          f"FL:{fl} FR:{fr} "
          f"RL:{rl} RR:{rr} km/h")

    def send_brake_data_step(self):
        """Send brake pressure step"""
        if not self.running: return
        brake = int(self.dc.brake_pressure)
        msg   = can.Message(
            arbitration_id=0x201,
            data=codec.encode(0x201, {
                'Brake_Pressure': brake
            }),
            is_extended_id=False
        )
        try:
            self.bus.send(msg)
        except Exception:
            pass
        print(f"[ABS ECU] Brake:{brake} bar")

    def on_message_received(self, msg):
        pass

    def start(self):
        print("[ABS ECU] Starting (10ms CAN cycle)...")
        from core.scheduler import scheduler
        scheduler.register('ABS_WHEELS', 10, self.send_wheel_data_step)
        scheduler.register('ABS_BRAKE', 10, self.send_brake_data_step)

    def stop(self):
        self.running = False
        print("[ABS ECU] Stopped.")