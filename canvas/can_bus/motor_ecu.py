# CANVAS Project
# Module: CAN Bus
# File: motor_ecu.py
# Simulates Electric Motor ECU   torque control + regenerative braking

import can
import can
import random
from utils.can_codec import codec

class MotorECU(can.Listener):
    def __init__(self, bus):
        self.bus = bus
        self.running = True

        # Motor parameters (typical hybrid motor: 50kW, 207Nm)
        self.motor_rpm      = 0       # Motor RPM
        self.torque         = 0.0     # Motor torque (Nm)
        self.motor_temp     = 30.0    # Motor temperature ( C)
        self.regen_active   = False   # Regenerative braking active
        self.regen_power    = 0.0     # Regen power (kW)
        self.motor_mode     = 'IDLE'  # IDLE, DRIVE, REGEN, BOOST
        self.battery_soc    = 75.0    # Received from BMS
        self.vehicle_speed  = 0       # Received from Engine ECU
        self.brake_pressure = 0       # Received from ABS ECU

        # Motor limits
        self.MAX_TORQUE     = 207.0   # Nm
        self.MAX_RPM        = 6500    # RPM
        self.MAX_REGEN_KW   = 27.0    # kW

    def on_message_received(self, msg):
        """Handle incoming messages"""
        if not self.running: return
        
        if msg.arbitration_id == 0x500:
            decoded = codec.decode(0x500, msg.data)
            if decoded:
                self.battery_soc = decoded.get('SOC', 75.0)
                
        elif msg.arbitration_id == 0x100:
            decoded = codec.decode(0x100, msg.data)
            if decoded:
                self.vehicle_speed = decoded.get('Vehicle_Speed', 0)
                
        elif msg.arbitration_id == 0x201:
            decoded = codec.decode(0x201, msg.data)
            if decoded:
                self.brake_pressure = decoded.get('Brake_Pressure', 0)

    def simulate_motor_step(self):
        """Simulate motor behavior step"""
        if not self.running: return
        # Regenerative braking   when braking + speed > 0
        if self.brake_pressure > 30 and self.vehicle_speed > 5:
            self.regen_active  = True
            self.motor_mode    = 'REGEN'
            self.regen_power   = min(
                self.MAX_REGEN_KW,
                (self.brake_pressure / 80.0) * self.MAX_REGEN_KW
            )
            self.torque        = 0.0
            self.motor_rpm     = int(self.vehicle_speed * 40)
            print(f"[MOTOR ECU] [POW] Regen Braking -> "
                  f"Recovering {self.regen_power:.1f} kW")

        # Battery low   motor assists engine (BOOST mode)
        elif self.battery_soc > 20 and self.vehicle_speed > 0:
            self.regen_active  = False
            self.motor_mode    = 'DRIVE'
            self.torque        = random.uniform(50.0, self.MAX_TORQUE)
            self.motor_rpm     = min(
                self.MAX_RPM,
                int(self.vehicle_speed * 45)
            )
            self.regen_power   = 0.0

        # Battery critical   motor goes idle
        else:
            self.regen_active  = False
            self.motor_mode    = 'IDLE'
            self.torque        = 0.0
            self.motor_rpm     = 0
            self.regen_power   = 0.0

        # Motor heats up with torque
        self.motor_temp = 30.0 + (self.torque / self.MAX_TORQUE) * 40.0

    def send_motor_status_step(self):
        """Send CAN frame: Motor RPM + Torque + Mode step"""
        if not self.running: return
        mode_map   = {'IDLE': 0x00, 'DRIVE': 0x01,
                     'REGEN': 0x02, 'BOOST': 0x03}
        mode_byte  = mode_map.get(self.motor_mode, 0x00)

        msg = can.Message(
            arbitration_id=0x600,
            data=codec.encode(0x600, {
                'Motor_RPM': self.motor_rpm,
                'Motor_Torque': self.torque,
                'Motor_Mode': mode_byte,
                'Motor_Temp': self.motor_temp
            }),
            is_extended_id=False
        )
        self.bus.send(msg)
        print(f"[MOTOR ECU] Sent -> RPM:{self.motor_rpm} "
              f"Torque:{self.torque:.1f}Nm "
              f"Mode:{self.motor_mode} "
              f"Temp:{self.motor_temp:.1f} C")

    def start(self):
        print("[MOTOR ECU] Starting...")
        from core.scheduler import scheduler
        scheduler.register('MOTOR_SIM', 300, self.simulate_motor_step)
        scheduler.register('MOTOR_STATUS', 100, self.send_motor_status_step)

    def stop(self):
        self.running = False
        print("[MOTOR ECU] Stopped.")