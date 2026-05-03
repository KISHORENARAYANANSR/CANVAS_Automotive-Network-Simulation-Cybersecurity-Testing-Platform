# CANVAS Project
# Module: CAN Bus
# File: hybrid_control_ecu.py
# Brain of hybrid system   decides EV/HV/BOOST mode + power split

import can
import can
from utils.can_codec import codec

class HybridControlECU(can.Listener):
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
        self.EV_MAX_SPEED   = 40        # km/h   EV only below this
        self.SOC_EV_MIN     = 25.0      # %   minimum SOC for EV mode
        self.SOC_BOOST_MIN  = 50.0      # %   minimum SOC for BOOST mode

    def on_message_received(self, msg):
        if not self.running: return

        if msg.arbitration_id == 0x100:
            decoded = codec.decode(0x100, msg.data)
            if decoded:
                self.engine_rpm    = decoded.get('Engine_RPM', 0)
                self.vehicle_speed = decoded.get('Vehicle_Speed', 0)

        elif msg.arbitration_id == 0x101:
            decoded = codec.decode(0x101, msg.data)
            if decoded:
                self.throttle = decoded.get('Throttle_Pos', 0)

        elif msg.arbitration_id == 0x500:
            decoded = codec.decode(0x500, msg.data)
            if decoded:
                self.battery_soc = decoded.get('SOC', 75.0)

        elif msg.arbitration_id == 0x600:
            decoded = codec.decode(0x600, msg.data)
            if decoded:
                motor_mode       = decoded.get('Motor_Mode', 0x00)
                mode_map         = {0x00: 'IDLE', 0x01: 'DRIVE',
                                   0x02: 'REGEN', 0x03: 'BOOST'}
                self.motor_mode  = mode_map.get(motor_mode, 'IDLE')

        elif msg.arbitration_id == 0x201:
            decoded = codec.decode(0x201, msg.data)
            if decoded:
                self.brake_pressure = decoded.get('Brake_Pressure', 0)

    def decide_drive_mode_step(self):
        """Core hybrid logic step"""
        if not self.running: return

        # REGEN   braking detected or coasting (throttle 0) while moving
        if (self.brake_pressure > 5 or self.throttle == 0) and self.vehicle_speed > 5:
            self.drive_mode    = 'REGEN'
            self.engine_active = False
            self.motor_active  = True
            self.power_split   = 0
            print("[HYBRID CTRL] [POW] Mode: REGEN   Recovering energy")

        # BOOST   high speed + good battery + sudden high acceleration
        elif (self.throttle > 60 and self.battery_soc >= self.SOC_BOOST_MIN):
            self.drive_mode    = 'BOOST'
            self.engine_active = True
            self.motor_active  = True
            self.power_split   = 50
            print(f"[HYBRID CTRL] [BOOST] Mode: BOOST   "
                  f"Engine + Motor combined")

        # EV   low speed + enough battery
        elif (self.vehicle_speed <= self.EV_MAX_SPEED and
              self.battery_soc >= self.SOC_EV_MIN):
            self.drive_mode    = 'EV'
            self.engine_active = False
            self.motor_active  = True
            self.power_split   = 0
            print(f"[HYBRID CTRL] [BATT] Mode: EV   "
                  f"Speed:{self.vehicle_speed}km/h "
                  f"SOC:{self.battery_soc:.1f}%")

        # HV   high speed or low battery -> engine only
        elif (self.vehicle_speed > self.EV_MAX_SPEED or
              self.battery_soc < self.SOC_EV_MIN):
            self.drive_mode    = 'HV'
            self.engine_active = True
            self.motor_active  = False
            self.power_split   = 100
            print(f"[HYBRID CTRL] [GAS] Mode: HV   "
                  f"Engine only SOC:{self.battery_soc:.1f}%")

        # IDLE   vehicle stopped
        else:
            self.drive_mode    = 'IDLE'
            self.engine_active = False
            self.motor_active  = False
            self.power_split   = 0

    def send_hybrid_status_step(self):
        """Send CAN frame: Hybrid mode + power split step"""
        if not self.running: return
        mode_map       = {'IDLE': 0x00, 'EV': 0x01, 'HV': 0x02,
                         'BOOST': 0x03, 'REGEN': 0x04}
        mode_byte      = mode_map.get(self.drive_mode, 0x00)
        engine_flag    = 0x01 if self.engine_active else 0x00
        motor_flag     = 0x01 if self.motor_active else 0x00

        msg = can.Message(
            arbitration_id=0x700,
            data=codec.encode(0x700, {
                'Hybrid_Mode': mode_byte,
                'Engine_Active': engine_flag,
                'Motor_Active': motor_flag,
                'Power_Split': self.power_split
            }),
            is_extended_id=False
        )
        self.bus.send(msg)
        print(f"[HYBRID CTRL] Sent -> Mode:{self.drive_mode} "
              f"Engine:{self.engine_active} "
              f"Motor:{self.motor_active} "
              f"PowerSplit:{self.power_split}%")

    def start(self):
        print("[HYBRID CTRL ECU] Starting...")
        from core.scheduler import scheduler
        scheduler.register('HYBRID_LOGIC', 500, self.decide_drive_mode_step)
        scheduler.register('HYBRID_STATUS', 200, self.send_hybrid_status_step)

    def stop(self):
        self.running = False
        print("[HYBRID CTRL ECU] Stopped.")