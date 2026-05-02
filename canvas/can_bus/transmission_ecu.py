# CANVAS Project
# Module: CAN Bus
# File: transmission_ecu.py
# Transmission ECU — gear from DriveCycle

import can
import time
import threading

class TransmissionECU:
    def __init__(self, bus, drive_cycle):
        self.bus     = bus
        self.dc      = drive_cycle
        self.running = True

    def send_transmission_status(self):
        """Send CAN frame: Gear + Drive mode (ID: 0x400)"""
        while self.running:
            gear       = self.dc.gear
            mode_byte  = 0x03   # D = Drive
            shift_flag = 0x00

            msg = can.Message(
                arbitration_id=0x400,
                data=[gear, mode_byte, shift_flag,
                      0x00, 0x00, 0x00, 0x00, 0x00],
                is_extended_id=False
            )
            self.bus.send(msg)
            print(f"[TRANSMISSION ECU] Sent → "
                  f"Gear:{gear} Mode:D")
            time.sleep(0.1)

    def start(self):
        print("[TRANSMISSION ECU] Starting...")
        t        = threading.Thread(
            target=self.send_transmission_status)
        t.daemon = True
        t.start()

    def stop(self):
        self.running = False
        print("[TRANSMISSION ECU] Stopped.")