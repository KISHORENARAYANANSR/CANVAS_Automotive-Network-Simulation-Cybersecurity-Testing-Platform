# CANVAS Project
# Module: CAN Bus
# File: regen_brake_ecu.py
# Simulates Regenerative Brake ECU — energy recovery tracking

import can
import time
import threading

class RegenBrakeECU:
    def __init__(self, bus):
        self.bus = bus
        self.running = True

        # Regen parameters
        self.regen_active       = False   # Is regen braking happening?
        self.regen_power_kw     = 0.0     # Current regen power (kW)
        self.energy_recovered   = 0.0     # Total energy recovered (Wh)
        self.regen_efficiency   = 0.0     # Efficiency % of energy recovery
        self.brake_pressure     = 0       # From ABS ECU
        self.vehicle_speed      = 0       # From Engine ECU
        self.motor_mode         = 'IDLE'  # From Motor ECU
        self.session_savings    = 0.0     # Total Wh saved this session

        # Regen constants
        self.MAX_REGEN_KW       = 27.0    # Max regen power (kW)
        self.REGEN_EFFICIENCY   = 0.85    # 85% conversion efficiency

    def listen_abs_ecu(self):
        """Listen for brake pressure (ID: 0x201)"""
        while self.running:
            msg = self.bus.recv(timeout=1.0)
            if msg and msg.arbitration_id == 0x201:
                self.brake_pressure = msg.data[0]

    def listen_engine_ecu(self):
        """Listen for vehicle speed (ID: 0x100)"""
        while self.running:
            msg = self.bus.recv(timeout=1.0)
            if msg and msg.arbitration_id == 0x100:
                self.vehicle_speed = msg.data[2]

    def listen_motor_ecu(self):
        """Listen for motor regen status (ID: 0x600)"""
        while self.running:
            msg = self.bus.recv(timeout=1.0)
            if msg and msg.arbitration_id == 0x600:
                mode_map        = {0x00: 'IDLE', 0x01: 'DRIVE',
                                  0x02: 'REGEN', 0x03: 'BOOST'}
                self.motor_mode = mode_map.get(msg.data[4], 'IDLE')
                self.regen_active = (self.motor_mode == 'REGEN')

                # Extract regen power from motor data
                if self.regen_active:
                    if self.brake_pressure > 0:
                        self.regen_power_kw = min(
                            self.MAX_REGEN_KW,
                            (self.brake_pressure / 80.0) * self.MAX_REGEN_KW
                        )
                    else:
                        # Coasting regen (simulated engine braking)
                        self.regen_power_kw = min(
                            self.MAX_REGEN_KW,
                            10.0 + (self.vehicle_speed / 120.0) * 10.0
                        )
                else:
                    self.regen_power_kw = 0.0

    def calculate_energy_recovery(self):
        """Calculate cumulative energy recovered"""
        while self.running:
            if self.regen_active and self.regen_power_kw > 0:
                # Energy (Wh) = Power (kW) * time (seconds) / 3600 * efficiency
                energy_this_cycle   = (self.regen_power_kw * 0.5 /
                                      3600.0 * 1000.0 * self.REGEN_EFFICIENCY)
                self.energy_recovered += energy_this_cycle
                self.session_savings  += energy_this_cycle
                self.regen_efficiency = self.REGEN_EFFICIENCY * 100.0

                print(f"[REGEN BRAKE ECU] ⚡ Recovering → "
                      f"Power:{self.regen_power_kw:.1f}kW "
                      f"Total:{self.energy_recovered:.2f}Wh "
                      f"Efficiency:{self.regen_efficiency:.0f}%")
            else:
                self.regen_efficiency = 0.0

            time.sleep(0.5)

    def send_regen_status(self):
        """Send CAN frame: Regen status + energy recovered (ID: 0x900)"""
        while self.running:
            regen_flag      = 0x01 if self.regen_active else 0x00
            power_byte      = min(255, int(self.regen_power_kw * 10)) & 0xFF
            energy_high     = (int(self.energy_recovered) >> 8) & 0xFF
            energy_low      = int(self.energy_recovered) & 0xFF
            efficiency_byte = int(self.regen_efficiency) & 0xFF

            msg = can.Message(
                arbitration_id=0x900,
                data=[regen_flag, power_byte, energy_high,
                      energy_low, efficiency_byte, 0x00, 0x00, 0x00],
                is_extended_id=False
            )
            self.bus.send(msg)
            print(f"[REGEN BRAKE ECU] Sent → "
                  f"Active:{bool(regen_flag)} "
                  f"Power:{self.regen_power_kw:.1f}kW "
                  f"Recovered:{self.energy_recovered:.1f}Wh")
            time.sleep(0.2)

    def start(self):
        print("[REGEN BRAKE ECU] Starting...")
        threads = [
            threading.Thread(target=self.listen_abs_ecu),
            threading.Thread(target=self.listen_engine_ecu),
            threading.Thread(target=self.listen_motor_ecu),
            threading.Thread(target=self.calculate_energy_recovery),
            threading.Thread(target=self.send_regen_status),
        ]
        for t in threads:
            t.daemon = True
            t.start()

    def stop(self):
        self.running = False
        print("[REGEN BRAKE ECU] Stopped.")