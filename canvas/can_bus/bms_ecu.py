# CANVAS Project
# Module: CAN Bus
# File: bms_ecu.py
# BMS ECU — realistic SOC drain tied to DriveCycle

import can
import time
import threading

class BMSECU:
    def __init__(self, bus, drive_cycle):
        self.bus          = bus
        self.dc           = drive_cycle
        self.running      = True
        self.soc          = 75.0      # Start at 75%
        self.voltage      = 201.6
        self.current      = 0.0
        self.temp_max     = 28.0
        self.temp_min     = 25.0
        self.cell_count   = 28
        self.charge_state = 'NORMAL'

    def simulate_battery(self):
        """Realistic SOC drain based on drive phase"""
        drain_rates = {
            'IDLE'        : 0.001,   # Very slow drain
            'ACCELERATING': 0.03,    # Heavy drain
            'CITY'        : 0.015,   # Moderate drain
            'HIGHWAY'     : 0.02,    # Steady drain
            'DECELERATING': -0.01,   # Regen charging
            'STOPPED'     : 0.001,   # Minimal drain
        }
        while self.running:
            phase       = self.dc.phase
            drain       = drain_rates.get(phase, 0.01)
            self.soc    = max(5.0, min(95.0, self.soc - drain))

            # Voltage follows SOC
            self.voltage  = 160.0 + (self.soc / 100.0) * 85.0

            # Current based on speed
            self.current  = (self.dc.speed / 120.0) * 60.0

            # Temp rises with load
            self.temp_max = 28.0 + (self.dc.speed / 120.0) * 17.0
            self.temp_min = self.temp_max - 2.0

            # State
            if self.soc <= 10.0:
                self.charge_state = 'CRITICAL'
            elif self.soc <= 20.0:
                self.charge_state = 'WARNING'
            elif phase == 'DECELERATING':
                self.charge_state = 'CHARGING'
            else:
                self.charge_state = 'NORMAL'

            time.sleep(0.5)

    def send_battery_status(self):
        """Send CAN frame: SOC + Voltage (ID: 0x500)"""
        while self.running:
            soc_byte   = int(self.soc) & 0xFF
            volt_high  = (int(self.voltage) >> 8) & 0xFF
            volt_low   = int(self.voltage) & 0xFF
            curr_byte  = min(255, int(abs(self.current))) & 0xFF
            state_map  = {
                'NORMAL'  : 0x00, 'CHARGING': 0x01,
                'WARNING' : 0x02, 'CRITICAL': 0x03
            }
            state_byte = state_map.get(self.charge_state, 0x00)

            msg = can.Message(
                arbitration_id=0x500,
                data=[soc_byte, volt_high, volt_low,
                      curr_byte, state_byte,
                      0x00, 0x00, 0x00],
                is_extended_id=False
            )
            self.bus.send(msg)
            print(f"[BMS ECU] Sent → "
                  f"SOC:{self.soc:.1f}% "
                  f"Volt:{self.voltage:.1f}V "
                  f"State:{self.charge_state}")
            time.sleep(0.2)

    def send_temperature_status(self):
        """Send CAN frame: Cell temperatures (ID: 0x501)"""
        while self.running:
            msg = can.Message(
                arbitration_id=0x501,
                data=[int(self.temp_max), int(self.temp_min),
                      self.cell_count,
                      0x00, 0x00, 0x00, 0x00, 0x00],
                is_extended_id=False
            )
            self.bus.send(msg)
            print(f"[BMS ECU] Sent → "
                  f"TempMax:{self.temp_max:.1f}°C "
                  f"TempMin:{self.temp_min:.1f}°C")
            time.sleep(0.5)

    def start(self):
        print("[BMS ECU] Starting...")
        threads = [
            threading.Thread(target=self.simulate_battery),
            threading.Thread(target=self.send_battery_status),
            threading.Thread(target=self.send_temperature_status),
        ]
        for t in threads:
            t.daemon = True
            t.start()

    def stop(self):
        self.running = False
        print("[BMS ECU] Stopped.")