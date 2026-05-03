# CANVAS Project
# Module: Gateway
# File: gateway_ecu.py
# Bridges CAN Bus + LIN Bus -> Automotive Ethernet (DoIP)

import can
import time
import threading
import json

class GatewayECU:
    def __init__(self, can_bus, lin_bus, ethernet_bus):
        self.can_bus      = can_bus       # CAN bus object
        self.lin_bus      = lin_bus       # LIN bus (shared dict)
        self.ethernet_bus = ethernet_bus  # Ethernet bus (shared dict)
        self.running      = True

        # Translated data store   gateway builds this from all networks
        self.vehicle_state = {
            # From CAN   Engine ECU
            'engine_rpm'        : 0,
            'vehicle_speed'     : 0,
            'engine_temp'       : 0,
            'throttle'          : 0,

            # From CAN   ABS ECU
            'wheel_speed_fl'    : 0,
            'wheel_speed_fr'    : 0,
            'wheel_speed_rl'    : 0,
            'wheel_speed_rr'    : 0,
            'brake_pressure'    : 0,

            # From CAN   Airbag ECU
            'crash_detected'    : False,
            'airbag_deployed'   : False,
            'impact_force'      : 0.0,

            # From CAN   Transmission ECU
            'current_gear'      : 1,
            'drive_mode'        : 'D',

            # From CAN   BMS ECU
            'battery_soc'       : 0,
            'battery_voltage'   : 0,
            'battery_state'     : 'NORMAL',

            # From CAN   Motor ECU
            'motor_rpm'         : 0,
            'motor_torque'      : 0,
            'motor_mode'        : 'IDLE',
            'regen_active'      : False,

            # From CAN   Hybrid Control ECU
            'hybrid_mode'       : 'IDLE',
            'engine_active'     : False,
            'motor_active'      : False,

            # From CAN   Regen Brake ECU
            'regen_power'       : 0.0,
            'energy_recovered'  : 0.0,

            # From LIN   TPMS ECU
            'tyre_pressure_fl'  : 0,
            'tyre_pressure_fr'  : 0,
            'tyre_pressure_rl'  : 0,
            'tyre_pressure_rr'  : 0,
            'tyre_warning'      : False,

            # From LIN   Window/Seat ECU
            'window_fl'         : 0,
            'window_fr'         : 0,
            'rain_detected'     : False,
            'seat_driver_pos'   : 50,
        }

    # --- CAN Bus Listeners ----------------------------------------

    def listen_can_bus(self):
        """Listen to all CAN messages and translate to vehicle state"""
        while self.running:
            msg = self.can_bus.recv(timeout=1.0)
            if not msg:
                continue

            # Engine ECU   RPM + Speed
            if msg.arbitration_id == 0x100:
                self.vehicle_state['engine_rpm']    = (
                    (msg.data[0] << 8) | msg.data[1])
                self.vehicle_state['vehicle_speed'] = msg.data[2]

            # Engine ECU   Temp + Throttle
            elif msg.arbitration_id == 0x101:
                self.vehicle_state['engine_temp']   = msg.data[0]
                self.vehicle_state['throttle']      = msg.data[1]

            # ABS ECU   Wheel speeds
            elif msg.arbitration_id == 0x200:
                self.vehicle_state['wheel_speed_fl'] = msg.data[0]
                self.vehicle_state['wheel_speed_fr'] = msg.data[1]
                self.vehicle_state['wheel_speed_rl'] = msg.data[2]
                self.vehicle_state['wheel_speed_rr'] = msg.data[3]

            # ABS ECU   Brake pressure
            elif msg.arbitration_id == 0x201:
                self.vehicle_state['brake_pressure'] = msg.data[0]

            # Airbag ECU
            elif msg.arbitration_id == 0x300:
                self.vehicle_state['crash_detected'] = bool(msg.data[0])
                self.vehicle_state['airbag_deployed'] = bool(msg.data[1])
                self.vehicle_state['impact_force']   = msg.data[4] / 10.0

            # Transmission ECU
            elif msg.arbitration_id == 0x400:
                self.vehicle_state['current_gear']  = msg.data[0]
                mode_map = {0x00:'P', 0x01:'R', 0x02:'N', 0x03:'D'}
                self.vehicle_state['drive_mode']    = mode_map.get(
                    msg.data[1], 'D')

            # BMS ECU   Battery status
            elif msg.arbitration_id == 0x500:
                self.vehicle_state['battery_soc']     = msg.data[0]
                self.vehicle_state['battery_voltage']  = (
                    (msg.data[1] << 8) | msg.data[2])
                state_map = {0x00:'NORMAL', 0x01:'CHARGING',
                             0x02:'WARNING', 0x03:'CRITICAL'}
                self.vehicle_state['battery_state']   = state_map.get(
                    msg.data[4], 'NORMAL')

            # Motor ECU
            elif msg.arbitration_id == 0x600:
                self.vehicle_state['motor_rpm']     = (
                    (msg.data[0] << 8) | msg.data[1])
                self.vehicle_state['motor_torque']  = msg.data[2]
                mode_map = {0x00:'IDLE', 0x01:'DRIVE',
                            0x02:'REGEN', 0x03:'BOOST'}
                self.vehicle_state['motor_mode']    = mode_map.get(
                    msg.data[4], 'IDLE')
                self.vehicle_state['regen_active']  = bool(msg.data[5])

            # Hybrid Control ECU
            elif msg.arbitration_id == 0x800:
                mode_map = {0x00:'IDLE', 0x01:'EV', 0x02:'HV',
                            0x03:'BOOST', 0x04:'REGEN'}
                self.vehicle_state['hybrid_mode']   = mode_map.get(
                    msg.data[0], 'IDLE')
                self.vehicle_state['engine_active'] = bool(msg.data[1])
                self.vehicle_state['motor_active']  = bool(msg.data[2])

            # Regen Brake ECU
            elif msg.arbitration_id == 0x900:
                self.vehicle_state['regen_power']      = msg.data[1] / 10.0
                self.vehicle_state['energy_recovered'] = (
                    (msg.data[2] << 8) | msg.data[3])

    # --- LIN Bus Listeners ----------------------------------------

    def listen_lin_bus(self):
        """Poll LIN bus dict and translate to vehicle state"""
        while self.running:
            # Read TPMS data
            if 'tpms' in self.lin_bus:
                tpms = self.lin_bus['tpms']
                self.vehicle_state['tyre_pressure_fl'] = (
                    tpms.get('pressure_fl', 0) / 10.0)
                self.vehicle_state['tyre_pressure_fr'] = (
                    tpms.get('pressure_fr', 0) / 10.0)
                self.vehicle_state['tyre_pressure_rl'] = (
                    tpms.get('pressure_rl', 0) / 10.0)
                self.vehicle_state['tyre_pressure_rr'] = (
                    tpms.get('pressure_rr', 0) / 10.0)
                self.vehicle_state['tyre_warning']     = bool(
                    tpms.get('warning', 0))

            # Read Window/Seat data
            if 'window_seat' in self.lin_bus:
                ws = self.lin_bus['window_seat']
                self.vehicle_state['window_fl']       = ws.get(
                    'window_fl', 0)
                self.vehicle_state['window_fr']       = ws.get(
                    'window_fr', 0)
                self.vehicle_state['rain_detected']   = ws.get(
                    'rain_detected', False)
                self.vehicle_state['seat_driver_pos'] = ws.get(
                    'seat_driver_pos', 50)

            time.sleep(0.5)

    # --- Ethernet Publisher ---------------------------------------

    def publish_to_ethernet(self):
        """Forward complete vehicle state to Ethernet bus for ADAS ECU"""
        while self.running:
            # Push entire translated vehicle state to ethernet bus
            self.ethernet_bus['vehicle_state'] = self.vehicle_state.copy()

            print(f"[GATEWAY ECU] [OK] Forwarded to Ethernet -> "
                  f"Speed:{self.vehicle_state['vehicle_speed']}km/h "
                  f"RPM:{self.vehicle_state['engine_rpm']} "
                  f"HybridMode:{self.vehicle_state['hybrid_mode']} "
                  f"SOC:{self.vehicle_state['battery_soc']}% "
                  f"TyreWarn:{self.vehicle_state['tyre_warning']}")
            time.sleep(0.1)

    def start(self):
        print("[GATEWAY ECU] Starting...")
        threads = [
            threading.Thread(target=self.listen_can_bus),
            threading.Thread(target=self.listen_lin_bus),
            threading.Thread(target=self.publish_to_ethernet),
        ]
        for t in threads:
            t.daemon = True
            t.start()

    def stop(self):
        self.running = False
        print("[GATEWAY ECU] Stopped.")