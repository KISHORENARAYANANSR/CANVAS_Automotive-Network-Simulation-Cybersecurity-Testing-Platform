# CANVAS Project
# Module: CAN Bus
# File: bms_ecu.py
# BMS ECU   realistic SOC drain tied to DriveCycle

import can
import can
from utils.can_codec import codec

class BMSECU(can.Listener):
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

    def simulate_battery_step(self):
        """Realistic SOC drain based on drive phase step"""
        if not self.running: return
        drain_rates = {
            'IDLE'        : 0.001,
            'ACCELERATING': 0.03,
            'CITY'        : 0.015,
            'HIGHWAY'     : 0.02,
            'DECELERATING': -0.01,
            'STOPPED'     : 0.001,
        }
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

    def send_battery_status_step(self):
        """Send CAN frame: SOC + Voltage step"""
        if not self.running: return
        
        state_map = {'NORMAL': 0x00, 'CHARGING': 0x01, 'WARNING': 0x02, 'CRITICAL': 0x03}
        state_byte = state_map.get(self.charge_state, 0x00)

        msg = can.Message(
            arbitration_id=0x500,
            data=codec.encode(0x500, {
                'SOC': self.soc,
                'Voltage': self.voltage,
                'State': state_byte
            }),
            is_extended_id=False
        )
        self.bus.send(msg)
        print(f"[BMS ECU] Sent -> "
              f"SOC:{self.soc:.1f}% "
              f"Volt:{self.voltage:.1f}V "
              f"State:{self.charge_state}")

    def send_temperature_status_step(self):
        """Send CAN frame: Cell temperatures step"""
        if not self.running: return
        msg = can.Message(
            arbitration_id=0x501,
            data=codec.encode(0x501, {
                'Temp_Max': self.temp_max,
                'Temp_Min': self.temp_min
            }),
            is_extended_id=False
        )
        self.bus.send(msg)
        print(f"[BMS ECU] Sent -> "
              f"TempMax:{self.temp_max:.1f} C "
              f"TempMin:{self.temp_min:.1f} C")

    def on_message_received(self, msg):
        pass

    def start(self):
        print("[BMS ECU] Starting...")
        from core.scheduler import scheduler
        scheduler.register('BMS_SIM', 500, self.simulate_battery_step)
        scheduler.register('BMS_STATUS', 200, self.send_battery_status_step)
        scheduler.register('BMS_TEMP', 500, self.send_temperature_status_step)

    def stop(self):
        self.running = False
        print("[BMS ECU] Stopped.")