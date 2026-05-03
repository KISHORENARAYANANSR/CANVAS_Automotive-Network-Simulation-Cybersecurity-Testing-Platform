# CANVAS Project
# Module: CAN Bus
# File: transmission_ecu.py
# Transmission ECU   gear from DriveCycle

import can
import can
from utils.can_codec import codec

class TransmissionECU(can.Listener):
    def __init__(self, bus, drive_cycle):
        self.bus     = bus
        self.dc      = drive_cycle
        self.running = True

    def send_transmission_status_step(self):
        """Send CAN frame: Gear + Drive mode step"""
        if not self.running: return
        gear       = self.dc.gear
        mode_byte  = 0x03   # D = Drive
        shift_flag = 0x00

        msg = can.Message(
            arbitration_id=0x400,
            data=codec.encode(0x400, {
                'Gear': gear,
                'Drive_Mode': mode_byte
            }),
            is_extended_id=False
        )
        self.bus.send(msg)
        print(f"[TRANSMISSION ECU] Sent -> "
              f"Gear:{gear} Mode:D")

    def on_message_received(self, msg):
        pass

    def start(self):
        print("[TRANSMISSION ECU] Starting...")
        from core.scheduler import scheduler
        scheduler.register('TRANSMISSION_STATUS', 100, self.send_transmission_status_step)

    def stop(self):
        self.running = False
        print("[TRANSMISSION ECU] Stopped.")