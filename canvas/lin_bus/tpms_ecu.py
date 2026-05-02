# CANVAS Project
# Module: LIN Bus
# File: tpms_ecu.py
# Simulates TPMS ECU — tyre pressure + temp monitoring on LIN Bus

import time
import random
import threading

class TPMSECU:
    def __init__(self, lin_bus):
        self.lin_bus = lin_bus
        self.running = True

        # Tyre pressure (PSI) — normal range: 32-35 PSI
        self.pressure_fl = 33.0    # Front Left
        self.pressure_fr = 33.0    # Front Right
        self.pressure_rl = 32.0    # Rear Left
        self.pressure_rr = 32.0    # Rear Right

        # Tyre temperature (°C)
        self.temp_fl = 28.0
        self.temp_fr = 28.0
        self.temp_rl = 27.0
        self.temp_rr = 27.0

        # Warning flags
        self.warning_fl = False
        self.warning_fr = False
        self.warning_rl = False
        self.warning_rr = False

        # Thresholds
        self.PRESSURE_MIN = 28.0   # PSI
        self.PRESSURE_MAX = 38.0   # PSI
        self.TEMP_MAX     = 80.0   # °C

    def simulate_tyres(self):
        """Simulate gradual pressure and temp changes"""
        while self.running:
            # Pressure slowly drops over time (natural leakage)
            self.pressure_fl -= random.uniform(0.0, 0.02)
            self.pressure_fr -= random.uniform(0.0, 0.02)
            self.pressure_rl -= random.uniform(0.0, 0.02)
            self.pressure_rr -= random.uniform(0.0, 0.02)

            # Simulate random puncture (0.5% chance)
            if random.random() < 0.005:
                tyre = random.choice(['fl', 'fr', 'rl', 'rr'])
                setattr(self, f'pressure_{tyre}',
                        random.uniform(15.0, 22.0))
                print(f"[TPMS ECU] 🔴 PUNCTURE DETECTED — "
                      f"Tyre: {tyre.upper()}!")

            # Temperature rises with speed/friction
            self.temp_fl += random.uniform(-0.1, 0.3)
            self.temp_fr += random.uniform(-0.1, 0.3)
            self.temp_rl += random.uniform(-0.1, 0.3)
            self.temp_rr += random.uniform(-0.1, 0.3)

            # Clamp temperatures
            for tyre in ['fl', 'fr', 'rl', 'rr']:
                temp = getattr(self, f'temp_{tyre}')
                setattr(self, f'temp_{tyre}', max(20.0, min(90.0, temp)))

            # Check warnings
            self.warning_fl = not (self.PRESSURE_MIN <=
                                   self.pressure_fl <= self.PRESSURE_MAX)
            self.warning_fr = not (self.PRESSURE_MIN <=
                                   self.pressure_fr <= self.PRESSURE_MAX)
            self.warning_rl = not (self.PRESSURE_MIN <=
                                   self.pressure_rl <= self.PRESSURE_MAX)
            self.warning_rr = not (self.PRESSURE_MIN <=
                                   self.pressure_rr <= self.PRESSURE_MAX)

            if any([self.warning_fl, self.warning_fr,
                    self.warning_rl, self.warning_rr]):
                print(f"[TPMS ECU] ⚠️  TYRE WARNING → "
                      f"FL:{self.pressure_fl:.1f} "
                      f"FR:{self.pressure_fr:.1f} "
                      f"RL:{self.pressure_rl:.1f} "
                      f"RR:{self.pressure_rr:.1f} PSI")
            time.sleep(0.5)

    def send_lin_frame(self):
        """Send LIN Bus frame with tyre data"""
        while self.running:
            # LIN frame structure:
            # [Frame ID] [Pressure FL] [Pressure FR]
            # [Pressure RL] [Pressure RR] [Temp FL] [Checksum]
            frame = {
                'id'          : 0x10,   # LIN Frame ID for TPMS
                'pressure_fl' : int(self.pressure_fl * 10),
                'pressure_fr' : int(self.pressure_fr * 10),
                'pressure_rl' : int(self.pressure_rl * 10),
                'pressure_rr' : int(self.pressure_rr * 10),
                'temp_fl'     : int(self.temp_fl),
                'temp_fr'     : int(self.temp_fr),
                'warning'     : (self.warning_fl << 3 |
                                self.warning_fr << 2 |
                                self.warning_rl << 1 |
                                self.warning_rr)
            }

            # Publish to LIN bus (shared dict — simulated LIN)
            self.lin_bus['tpms'] = frame

            print(f"[TPMS ECU] LIN Sent → "
                  f"FL:{self.pressure_fl:.1f} "
                  f"FR:{self.pressure_fr:.1f} "
                  f"RL:{self.pressure_rl:.1f} "
                  f"RR:{self.pressure_rr:.1f} PSI | "
                  f"Temp FL:{self.temp_fl:.1f}°C")
            time.sleep(1.0)   # LIN is slower than CAN

    def start(self):
        print("[TPMS ECU] Starting...")
        threads = [
            threading.Thread(target=self.simulate_tyres),
            threading.Thread(target=self.send_lin_frame),
        ]
        for t in threads:
            t.daemon = True
            t.start()

    def stop(self):
        self.running = False
        print("[TPMS ECU] Stopped.")