# CANVAS Project
# Module: CAN Bus
# File: motor_ecu.py
# Simulates Electric Motor ECU — torque control + regenerative braking

import can
import time
import random
import threading

class MotorECU:
    def __init__(self, bus):
        self.bus = bus
        self.running = True

        # Motor parameters (typical hybrid motor: 50kW, 207Nm)
        self.motor_rpm      = 0       # Motor RPM
        self.torque         = 0.0     # Motor torque (Nm)
        self.motor_temp     = 30.0    # Motor temperature (°C)
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

    def listen_bms(self):
        """Listen for BMS SOC (ID: 0x500)"""
        while self.running:
            msg = self.bus.recv(timeout=1.0)
            if msg and msg.arbitration_id == 0x500:
                self.battery_soc = msg.data[0]

    def listen_engine_ecu(self):
        """Listen for Engine ECU speed (ID: 0x100)"""
        while self.running:
            msg = self.bus.recv(timeout=1.0)
            if msg and msg.arbitration_id == 0x100:
                self.vehicle_speed = msg.data[2]

    def listen_abs_ecu(self):
        """Listen for ABS brake pressure (ID: 0x201)"""
        while self.running:
            msg = self.bus.recv(timeout=1.0)
            if msg and msg.arbitration_id == 0x201:
                self.brake_pressure = msg.data[0]

    def simulate_motor(self):
        """Simulate motor behavior based on driving conditions"""
        while self.running:
            # Regenerative braking — when braking + speed > 0
            if self.brake_pressure > 30 and self.vehicle_speed > 5:
                self.regen_active  = True
                self.motor_mode    = 'REGEN'
                self.regen_power   = min(
                    self.MAX_REGEN_KW,
                    (self.brake_pressure / 80.0) * self.MAX_REGEN_KW
                )
                self.torque        = 0.0
                self.motor_rpm     = int(self.vehicle_speed * 40)
                print(f"[MOTOR ECU] ⚡ Regen Braking → "
                      f"Recovering {self.regen_power:.1f} kW")

            # Battery low — motor assists engine (BOOST mode)
            elif self.battery_soc > 20 and self.vehicle_speed > 0:
                self.regen_active  = False
                self.motor_mode    = 'DRIVE'
                self.torque        = random.uniform(50.0, self.MAX_TORQUE)
                self.motor_rpm     = min(
                    self.MAX_RPM,
                    int(self.vehicle_speed * 45)
                )
                self.regen_power   = 0.0

            # Battery critical — motor goes idle
            else:
                self.regen_active  = False
                self.motor_mode    = 'IDLE'
                self.torque        = 0.0
                self.motor_rpm     = 0
                self.regen_power   = 0.0

            # Motor heats up with torque
            self.motor_temp = 30.0 + (self.torque / self.MAX_TORQUE) * 40.0
            time.sleep(0.3)

    def send_motor_status(self):
        """Send CAN frame: Motor RPM + Torque + Mode (ID: 0x600)"""
        while self.running:
            rpm_high   = (self.motor_rpm >> 8) & 0xFF
            rpm_low    = self.motor_rpm & 0xFF
            torque_val = min(255, int(self.torque)) & 0xFF
            temp_val   = min(255, int(self.motor_temp)) & 0xFF
            mode_map   = {'IDLE': 0x00, 'DRIVE': 0x01,
                         'REGEN': 0x02, 'BOOST': 0x03}
            mode_byte  = mode_map.get(self.motor_mode, 0x00)
            regen_flag = 0x01 if self.regen_active else 0x00

            msg = can.Message(
                arbitration_id=0x600,
                data=[rpm_high, rpm_low, torque_val,
                      temp_val, mode_byte, regen_flag, 0x00, 0x00],
                is_extended_id=False
            )
            self.bus.send(msg)
            print(f"[MOTOR ECU] Sent → RPM:{self.motor_rpm} "
                  f"Torque:{self.torque:.1f}Nm "
                  f"Mode:{self.motor_mode} "
                  f"Temp:{self.motor_temp:.1f}°C")
            time.sleep(0.1)

    def start(self):
        print("[MOTOR ECU] Starting...")
        threads = [
            threading.Thread(target=self.listen_bms),
            threading.Thread(target=self.listen_engine_ecu),
            threading.Thread(target=self.listen_abs_ecu),
            threading.Thread(target=self.simulate_motor),
            threading.Thread(target=self.send_motor_status),
        ]
        for t in threads:
            t.daemon = True
            t.start()

    def stop(self):
        self.running = False
        print("[MOTOR ECU] Stopped.")