# CANVAS Project
# Module: CAN Bus
# File: regen_brake_ecu.py
# Simulates Regenerative Brake ECU   energy recovery tracking

import can
import can
from utils.can_codec import codec

class RegenBrakeECU(can.Listener):
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

    def on_message_received(self, msg):
        if not self.running: return
        
        if msg.arbitration_id == 0x201:
            decoded = codec.decode(0x201, msg.data)
            if decoded:
                self.brake_pressure = decoded.get('Brake_Pressure', 0)
                
        elif msg.arbitration_id == 0x100:
            decoded = codec.decode(0x100, msg.data)
            if decoded:
                self.vehicle_speed = decoded.get('Vehicle_Speed', 0)
                
        elif msg.arbitration_id == 0x600:
            decoded = codec.decode(0x600, msg.data)
            if decoded:
                motor_mode = decoded.get('Motor_Mode', 0x00)
                mode_map        = {0x00: 'IDLE', 0x01: 'DRIVE',
                                  0x02: 'REGEN', 0x03: 'BOOST'}
                self.motor_mode = mode_map.get(motor_mode, 'IDLE')
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

    def calculate_energy_recovery_step(self):
        """Calculate cumulative energy recovered step"""
        if not self.running: return
        if self.regen_active and self.regen_power_kw > 0:
            # Energy (Wh) = Power (kW) * time (seconds) / 3600 * efficiency
            energy_this_cycle   = (self.regen_power_kw * 0.5 /
                                  3600.0 * 1000.0 * self.REGEN_EFFICIENCY)
            self.energy_recovered += energy_this_cycle
            self.session_savings  += energy_this_cycle
            self.regen_efficiency = self.REGEN_EFFICIENCY * 100.0

            print(f"[REGEN BRAKE ECU] [POW] Recovering -> "
                  f"Power:{self.regen_power_kw:.1f}kW "
                  f"Total:{self.energy_recovered:.2f}Wh "
                  f"Efficiency:{self.regen_efficiency:.0f}%")
        else:
            self.regen_efficiency = 0.0

    def send_regen_status_step(self):
        """Send CAN frame: Regen status + energy recovered step"""
        if not self.running: return
        regen_flag      = 0x01 if self.regen_active else 0x00

        msg = can.Message(
            arbitration_id=0x710,
            data=codec.encode(0x710, {
                'Regen_Active': regen_flag,
                'Regen_Power': self.regen_power_kw,
                'Energy_Recovered': self.energy_recovered
            }),
            is_extended_id=False
        )
        self.bus.send(msg)
        print(f"[REGEN BRAKE ECU] Sent -> "
              f"Active:{bool(regen_flag)} "
              f"Power:{self.regen_power_kw:.1f}kW "
              f"Recovered:{self.energy_recovered:.1f}Wh")

    def start(self):
        print("[REGEN BRAKE ECU] Starting...")
        from core.scheduler import scheduler
        scheduler.register('REGEN_CALC', 500, self.calculate_energy_recovery_step)
        scheduler.register('REGEN_STATUS', 200, self.send_regen_status_step)

    def stop(self):
        self.running = False
        print("[REGEN BRAKE ECU] Stopped.")