# CANVAS Project
# Module: CAN Bus
# File: airbag_ecu.py
# Simulates Airbag ECU   crash detection + airbag deployment status

import can
import random
from utils.can_codec import codec

class AirbagECU(can.Listener):
    def __init__(self, bus):
        self.bus = bus
        self.running = True
        self.impact_force = 0        # G-force from accelerometer
        self.airbag_deployed = False # Deployment status
        self.seatbelt_fl = True      # Front Left seatbelt
        self.seatbelt_fr = False     # Front Right seatbelt
        self.crash_detected = False  # Crash flag
        self.brake_pressure = 0      # Received from ABS ECU

    def on_message_received(self, msg):
        """Handle incoming messages immediately"""
        if not self.running: return
        if msg.arbitration_id == 0x201:
            decoded = codec.decode(0x201, msg.data)
            if decoded:
                self.brake_pressure = decoded.get('Brake_Pressure', 0)

    def simulate_crash_sensor_step(self):
        """Simulate accelerometer   occasional spike = crash"""
        if not self.running: return
        # Normal driving: low G-force
        self.impact_force = random.uniform(0.1, 1.5)

        # Simulate random crash event (1% chance)
        if random.random() < 0.01:
            self.impact_force = random.uniform(15.0, 40.0)
            self.crash_detected = True
            print("[AIRBAG ECU] [WARN]  CRASH DETECTED! Impact Force: "
                  f"{self.impact_force:.1f}G")

            # Deploy airbag if impact > 10G
            if self.impact_force > 10.0:
                self.airbag_deployed = True
                print("[AIRBAG ECU] [ERROR] AIRBAG DEPLOYED!")
        else:
            self.crash_detected = False
            self.airbag_deployed = False

    def send_airbag_status_step(self):
        """Send CAN frame: Airbag + crash status step"""
        if not self.running: return
        crash_flag   = 0x01 if self.crash_detected else 0x00
        deploy_flag  = 0x01 if self.airbag_deployed else 0x00
        belt_fl      = 0x01 if self.seatbelt_fl else 0x00
        belt_fr      = 0x01 if self.seatbelt_fr else 0x00
        impact       = min(255, int(self.impact_force * 10))

        msg = can.Message(
            arbitration_id=0x300,
            data=codec.encode(0x300, {
                'Crash_Detected': 1 if self.crash_detected else 0,
                'Airbag_Deployed': 1 if self.airbag_deployed else 0,
                'Seatbelt_FL': 1 if self.seatbelt_fl else 0,
                'Seatbelt_FR': 1 if self.seatbelt_fr else 0,
                'Impact_G': self.impact_force
            }),
            is_extended_id=False
        )
        self.bus.send(msg)
        print(f"[AIRBAG ECU] Sent -> Crash:{bool(crash_flag)} "
              f"Deployed:{bool(deploy_flag)} "
              f"Seatbelt FL:{bool(belt_fl)} FR:{bool(belt_fr)} "
              f"Impact:{self.impact_force:.1f}G")

    def start(self):
        print("[AIRBAG ECU] Starting...")
        from core.scheduler import scheduler
        scheduler.register('AIRBAG_SENSOR', 500, self.simulate_crash_sensor_step)
        scheduler.register('AIRBAG_STATUS', 200, self.send_airbag_status_step)

    def stop(self):
        self.running = False
        print("[AIRBAG ECU] Stopped.")