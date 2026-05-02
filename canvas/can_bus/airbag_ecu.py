# CANVAS Project
# Module: CAN Bus
# File: airbag_ecu.py
# Simulates Airbag ECU — crash detection + airbag deployment status

import can
import time
import random
import threading

class AirbagECU:
    def __init__(self, bus):
        self.bus = bus
        self.running = True
        self.impact_force = 0        # G-force from accelerometer
        self.airbag_deployed = False # Deployment status
        self.seatbelt_fl = True      # Front Left seatbelt
        self.seatbelt_fr = False     # Front Right seatbelt
        self.crash_detected = False  # Crash flag
        self.brake_pressure = 0      # Received from ABS ECU

    def listen_abs_ecu(self):
        """Listen for ABS brake pressure (ID: 0x201)"""
        while self.running:
            msg = self.bus.recv(timeout=1.0)
            if msg and msg.arbitration_id == 0x201:
                self.brake_pressure = msg.data[0]

    def simulate_crash_sensor(self):
        """Simulate accelerometer — occasional spike = crash"""
        while self.running:
            # Normal driving: low G-force
            self.impact_force = random.uniform(0.1, 1.5)

            # Simulate random crash event (1% chance)
            if random.random() < 0.01:
                self.impact_force = random.uniform(15.0, 40.0)
                self.crash_detected = True
                print("[AIRBAG ECU] ⚠️  CRASH DETECTED! Impact Force: "
                      f"{self.impact_force:.1f}G")

                # Deploy airbag if impact > 10G
                if self.impact_force > 10.0:
                    self.airbag_deployed = True
                    print("[AIRBAG ECU] 🔴 AIRBAG DEPLOYED!")
            else:
                self.crash_detected = False
                self.airbag_deployed = False

            time.sleep(0.5)

    def send_airbag_status(self):
        """Send CAN frame: Airbag + crash status (ID: 0x300)"""
        while self.running:
            crash_flag   = 0x01 if self.crash_detected else 0x00
            deploy_flag  = 0x01 if self.airbag_deployed else 0x00
            belt_fl      = 0x01 if self.seatbelt_fl else 0x00
            belt_fr      = 0x01 if self.seatbelt_fr else 0x00
            impact       = min(255, int(self.impact_force * 10))

            msg = can.Message(
                arbitration_id=0x300,
                data=[crash_flag, deploy_flag, belt_fl, belt_fr,
                      impact, 0x00, 0x00, 0x00],
                is_extended_id=False
            )
            self.bus.send(msg)
            print(f"[AIRBAG ECU] Sent → Crash:{bool(crash_flag)} "
                  f"Deployed:{bool(deploy_flag)} "
                  f"Seatbelt FL:{bool(belt_fl)} FR:{bool(belt_fr)} "
                  f"Impact:{self.impact_force:.1f}G")
            time.sleep(0.2)

    def start(self):
        print("[AIRBAG ECU] Starting...")
        threads = [
            threading.Thread(target=self.listen_abs_ecu),
            threading.Thread(target=self.simulate_crash_sensor),
            threading.Thread(target=self.send_airbag_status),
        ]
        for t in threads:
            t.daemon = True
            t.start()

    def stop(self):
        self.running = False
        print("[AIRBAG ECU] Stopped.")