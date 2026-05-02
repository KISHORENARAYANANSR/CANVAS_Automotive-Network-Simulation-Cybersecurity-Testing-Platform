# CANVAS Project
# Module: CAN Bus
# File: hybrid_control_ecu.py
# Brain of hybrid system — decides EV/HV/BOOST mode + power split

import can
import time
import threading

class HybridControlECU:
    def __init__(self, bus):
        self.bus = bus
        self.running = True

        # Hybrid drive modes
        self.drive_mode     = 'EV'      # EV, HV, BOOST, REGEN, IDLE
        self.power_split    = 0         # % of power from engine (0=full EV, 100=full HV)
        self.engine_active  = False     # Is petrol engine running?
        self.motor_active   = True      # Is electric motor running?

        # Data received from other ECUs
        self.battery_soc    = 75.0      # From BMS
        self.vehicle_speed  = 0         # From Engine ECU
        self.engine_rpm     = 800       # From Engine ECU
        self.throttle       = 0         # From Engine ECU (0x101)
        self.motor_mode     = 'IDLE'    # From Motor ECU
        self.brake_pressure = 0         # From ABS ECU

        # Thresholds for mode switching
        self.EV_MAX_SPEED   = 40        # km/h — EV only below this
        self.SOC_EV_MIN     = 25.0      # % — minimum SOC for EV mode
        self.SOC_BOOST_MIN  = 50.0      # % — minimum SOC for BOOST mode

    def listen_engine_ecu(self):
        """Listen for Engine ECU RPM + Speed (ID: 0x100)"""
        while self.running:
            msg = self.bus.recv(timeout=1.0)
            if msg and msg.arbitration_id == 0x100:
                self.engine_rpm    = (msg.data[0] << 8) | msg.data[1]
                self.vehicle_speed = msg.data[2]

    def listen_engine_ecu_aux(self):
        """Listen for Engine Temp + Throttle (ID: 0x101)"""
        while self.running:
            msg = self.bus.recv(timeout=1.0)
            if msg and msg.arbitration_id == 0x101:
                self.throttle = msg.data[1]

    def listen_bms(self):
        """Listen for BMS SOC (ID: 0x500)"""
        while self.running:
            msg = self.bus.recv(timeout=1.0)
            if msg and msg.arbitration_id == 0x500:
                self.battery_soc = msg.data[0]

    def listen_motor_ecu(self):
        """Listen for Motor mode (ID: 0x600)"""
        while self.running:
            msg = self.bus.recv(timeout=1.0)
            if msg and msg.arbitration_id == 0x600:
                mode_map         = {0x00: 'IDLE', 0x01: 'DRIVE',
                                   0x02: 'REGEN', 0x03: 'BOOST'}
                self.motor_mode  = mode_map.get(msg.data[4], 'IDLE')

    def listen_abs_ecu(self):
        """Listen for brake pressure (ID: 0x201)"""
        while self.running:
            msg = self.bus.recv(timeout=1.0)
            if msg and msg.arbitration_id == 0x201:
                self.brake_pressure = msg.data[0]

    def decide_drive_mode(self):
        """Core hybrid logic — decides which mode to run in"""
        while self.running:

            # REGEN — braking detected or coasting (throttle 0) while moving
            if (self.brake_pressure > 5 or self.throttle == 0) and self.vehicle_speed > 5:
                self.drive_mode    = 'REGEN'
                self.engine_active = False
                self.motor_active  = True
                self.power_split   = 0
                print("[HYBRID CTRL] ⚡ Mode: REGEN — Recovering energy")

            # BOOST — high speed + good battery + sudden high acceleration
            elif (self.throttle > 60 and self.battery_soc >= self.SOC_BOOST_MIN):
                self.drive_mode    = 'BOOST'
                self.engine_active = True
                self.motor_active  = True
                self.power_split   = 50
                print(f"[HYBRID CTRL] 🚀 Mode: BOOST — "
                      f"Engine + Motor combined")

            # EV — low speed + enough battery
            elif (self.vehicle_speed <= self.EV_MAX_SPEED and
                  self.battery_soc >= self.SOC_EV_MIN):
                self.drive_mode    = 'EV'
                self.engine_active = False
                self.motor_active  = True
                self.power_split   = 0
                print(f"[HYBRID CTRL] 🔋 Mode: EV — "
                      f"Speed:{self.vehicle_speed}km/h "
                      f"SOC:{self.battery_soc:.1f}%")

            # HV — high speed or low battery → engine only
            elif (self.vehicle_speed > self.EV_MAX_SPEED or
                  self.battery_soc < self.SOC_EV_MIN):
                self.drive_mode    = 'HV'
                self.engine_active = True
                self.motor_active  = False
                self.power_split   = 100
                print(f"[HYBRID CTRL] ⛽ Mode: HV — "
                      f"Engine only SOC:{self.battery_soc:.1f}%")

            # IDLE — vehicle stopped
            else:
                self.drive_mode    = 'IDLE'
                self.engine_active = False
                self.motor_active  = False
                self.power_split   = 0

            time.sleep(0.5)

    def send_hybrid_status(self):
        """Send CAN frame: Hybrid mode + power split (ID: 0x800)"""
        while self.running:
            mode_map       = {'IDLE': 0x00, 'EV': 0x01, 'HV': 0x02,
                             'BOOST': 0x03, 'REGEN': 0x04}
            mode_byte      = mode_map.get(self.drive_mode, 0x00)
            engine_flag    = 0x01 if self.engine_active else 0x00
            motor_flag     = 0x01 if self.motor_active else 0x00

            msg = can.Message(
                arbitration_id=0x800,
                data=[mode_byte, engine_flag, motor_flag,
                      self.power_split, 0x00, 0x00, 0x00, 0x00],
                is_extended_id=False
            )
            self.bus.send(msg)
            print(f"[HYBRID CTRL] Sent → Mode:{self.drive_mode} "
                  f"Engine:{self.engine_active} "
                  f"Motor:{self.motor_active} "
                  f"PowerSplit:{self.power_split}%")
            time.sleep(0.2)

    def start(self):
        print("[HYBRID CTRL ECU] Starting...")
        threads = [
            threading.Thread(target=self.listen_engine_ecu),
            threading.Thread(target=self.listen_engine_ecu_aux),
            threading.Thread(target=self.listen_bms),
            threading.Thread(target=self.listen_motor_ecu),
            threading.Thread(target=self.listen_abs_ecu),
            threading.Thread(target=self.decide_drive_mode),
            threading.Thread(target=self.send_hybrid_status),
        ]
        for t in threads:
            t.daemon = True
            t.start()

    def stop(self):
        self.running = False
        print("[HYBRID CTRL ECU] Stopped.")