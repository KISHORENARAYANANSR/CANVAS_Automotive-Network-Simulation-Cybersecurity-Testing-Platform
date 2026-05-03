# CANVAS Project
# Module: Security & Gateway
# File: secure_gateway.py
# Bridges CAN + LIN -> Ethernet AND acts as an Intrusion Detection System (IDS)

import can
import time
import threading
import json
from vehicle.dtc_manager import dtc_manager

class SecureGatewayECU(can.Listener):
    def __init__(self, can_bus, lin_bus, ethernet_bus):
        super().__init__()
        self.can_bus      = can_bus
        self.lin_bus      = lin_bus
        self.ethernet_bus = ethernet_bus
        self.running      = True

        # IDS State
        self.msg_counts = {}
        self.last_speed = 0
        self.last_brake = 0
        self.security_alerts = []
        self.alert_counts = {} # {type: last_alert_time}

        # Translated data store
        self.vehicle_state = {
            'engine_rpm': 0, 'vehicle_speed': 0, 'engine_temp': 0, 'throttle': 0,
            'wheel_speed_fl': 0, 'wheel_speed_fr': 0, 'wheel_speed_rl': 0, 'wheel_speed_rr': 0, 'brake_pressure': 0,
            'crash_detected': False, 'airbag_deployed': False, 'impact_force': 0.0,
            'current_gear': 1, 'drive_mode': 'D', 'drive_phase': 'IDLE',
            'battery_soc': 75, 'battery_voltage': 200, 'battery_state': 'NORMAL',
            'motor_rpm': 0, 'motor_torque': 0, 'motor_mode': 'IDLE', 'regen_active': False,
            'hybrid_mode': 'IDLE', 'engine_active': False, 'motor_active': False,
            'regen_power': 0.0, 'energy_recovered': 0.0,
            'tyre_pressure_fl': 32.5, 'tyre_pressure_fr': 32.5, 'tyre_pressure_rl': 30.5, 'tyre_pressure_rr': 30.5, 'tyre_warning': False,
            'window_fl': 0, 'window_fr': 0, 'rain_detected': False, 'seat_driver_pos': 50,
        }

    # --- Intrusion Detection System (IDS) -------------------------

    def analyze_message(self, msg):
        """IDS: Analyze incoming CAN message for anomalies"""
        if not self.ethernet_bus.get('ids_active', True):
            return True
            
        aid = msg.arbitration_id
        now = time.perf_counter()
        
        # 1. Frequency Analysis (Flood Detection)
        if aid not in self.msg_counts:
            self.msg_counts[aid] = {'count': 0, 'start': now}
            
        stats = self.msg_counts[aid]
        stats['count'] += 1
        
        if now - stats['start'] > 1.0:
            freq = stats['count'] / (now - stats['start'])
            stats['count'] = 0
            stats['start'] = now
            
            # Normal rate is max 100Hz. If > 500Hz -> Flood!
            if freq > 500:
                self._trigger_alert('FLOOD', f"0x{aid:03X}", f"Message flood: {freq:.1f} msg/s")
                return False # Drop message

        # 2. Plausibility Check (Spoofing Detection)
        from utils.can_codec import codec
        
        if aid == 0x100: # Engine Speed
            decoded = codec.decode(0x100, msg.data)
            if decoded:
                speed = decoded.get('Vehicle_Speed', 0)
                # IDS Log: If speed jumps by > 50 km/h suddenly, it's spoofed
                if abs(speed - self.last_speed) > 50:
                    self._trigger_alert('SPOOF', '0x100', f"Speed Spoof: {self.last_speed} -> {speed} km/h")
                    # In a real car we'd return False here, but for simulation we allow it so user sees the effect
                self.last_speed = speed
                
        elif aid == 0x201: # Brake Pressure
            decoded = codec.decode(0x201, msg.data)
            if decoded:
                brake = decoded.get('Brake_Pressure', 0)
                if abs(brake - self.last_brake) > 80 and brake >= 100:
                    self._trigger_alert('SPOOF', '0x201', f"Brake Spoof: {self.last_brake} -> {brake} bar")
                    # allow for simulation visibility
                self.last_brake = brake

        return True # Message is clean

    def _trigger_alert(self, attack_type, target_id, message):
        # Alert Throttling: Max 1 alert per type per second to prevent flooding
        now = time.time()
        last_time = self.alert_counts.get(attack_type, 0)
        if now - last_time < 1.0:
            return

        self.alert_counts[attack_type] = now
        dtc_manager.set_fault('U0003') # Network Security Incident
        print(f"   [SECURE GATEWAY] IDS ALERT: {attack_type} - {target_id}: {message}")
        alert_item = {
            'alert_id': f"{now}_{len(self.security_alerts)}",
            'timestamp': time.strftime('%H:%M:%S'),
            'type': attack_type,
            'target_id': target_id,
            'msg': message,
            'severity': 'CRITICAL' if attack_type in ['FLOOD', 'SPOOF'] else 'WARNING'
        }
        self.security_alerts.append(alert_item)
        if len(self.security_alerts) > 50:
            self.security_alerts.pop(0)
        self.ethernet_bus['security_alerts'] = self.security_alerts[-10:] # Keep last 10
        
        # Emit real-time event
        from app import socketio
        socketio.emit('ids_alert', alert_item)

    # --- CAN Bus Listeners ----------------------------------------

    def on_message_received(self, msg):
        if not self.running:
            return

        # IDS Check before translation!
        if not self.analyze_message(msg):
            return # Discard malicious message

        # Translate using Codec
        from utils.can_codec import codec
        decoded = codec.decode(msg.arbitration_id, msg.data)
        if decoded:
            if msg.arbitration_id == 0x100:
                self.vehicle_state['engine_rpm']    = decoded.get('Engine_RPM', 0)
                self.vehicle_state['vehicle_speed'] = decoded.get('Vehicle_Speed', 0)
                phase_val = int(decoded.get('Drive_Phase', 0))
                phase_map = {0:'IDLE', 1:'ACCELERATING', 2:'CITY', 3:'HIGHWAY_ACCEL',
                             4:'HIGHWAY', 5:'HIGHWAY_DECEL', 6:'DECELERATING', 7:'STOPPED'}
                self.vehicle_state['drive_phase']   = phase_map.get(phase_val, 'IDLE')
            elif msg.arbitration_id == 0x101:
                self.vehicle_state['engine_temp']   = decoded.get('Engine_Temp', 0)
                self.vehicle_state['throttle']      = decoded.get('Throttle_Pos', 0)
            elif msg.arbitration_id == 0x200:
                self.vehicle_state['wheel_speed_fl'] = decoded.get('Wheel_Speed_FL', 0)
                self.vehicle_state['wheel_speed_fr'] = decoded.get('Wheel_Speed_FR', 0)
                self.vehicle_state['wheel_speed_rl'] = decoded.get('Wheel_Speed_RL', 0)
                self.vehicle_state['wheel_speed_rr'] = decoded.get('Wheel_Speed_RR', 0)
            elif msg.arbitration_id == 0x201:
                self.vehicle_state['brake_pressure'] = decoded.get('Brake_Pressure', 0)
            elif msg.arbitration_id == 0x300:
                self.vehicle_state['crash_detected'] = bool(decoded.get('Crash_Detected', 0))
                self.vehicle_state['airbag_deployed'] = bool(decoded.get('Airbag_Deployed', 0))
                self.vehicle_state['impact_force']   = decoded.get('Impact_G', 0)
            elif msg.arbitration_id == 0x400:
                self.vehicle_state['current_gear']  = decoded.get('Gear', 1)
                mode_val = int(decoded.get('Drive_Mode', 0x03))
                mode_map = {0x00:'P', 0x01:'R', 0x02:'N', 0x03:'D'}
                self.vehicle_state['drive_mode']    = mode_map.get(mode_val, 'D')
            elif msg.arbitration_id == 0x500:
                self.vehicle_state['battery_soc']     = decoded.get('SOC', 0)
                self.vehicle_state['battery_voltage'] = decoded.get('Voltage', 0)
                state_val = int(decoded.get('State', 0x00))
                state_map = {0x00:'NORMAL', 0x01:'CHARGING', 0x02:'WARNING', 0x03:'CRITICAL'}
                self.vehicle_state['battery_state']   = state_map.get(state_val, 'NORMAL')
            elif msg.arbitration_id == 0x600:
                self.vehicle_state['motor_rpm']     = decoded.get('Motor_RPM', 0)
                self.vehicle_state['motor_torque']  = decoded.get('Motor_Torque', 0)
                mmode_val = int(decoded.get('Motor_Mode', 0x00))
                mode_map = {0x00:'IDLE', 0x01:'DRIVE', 0x02:'REGEN', 0x03:'BOOST'}
                self.vehicle_state['motor_mode']    = mode_map.get(mmode_val, 'IDLE')
            elif msg.arbitration_id == 0x700:
                hmode_val = int(decoded.get('Hybrid_Mode', 0x00))
                mode_map = {0x00:'IDLE', 0x01:'EV', 0x02:'HV', 0x03:'BOOST', 0x04:'REGEN'}
                self.vehicle_state['hybrid_mode']   = mode_map.get(hmode_val, 'IDLE')
                self.vehicle_state['engine_active'] = bool(decoded.get('Engine_Active', 0))
                self.vehicle_state['motor_active']  = bool(decoded.get('Motor_Active', 0))
            elif msg.arbitration_id == 0x710:
                self.vehicle_state['regen_active']     = bool(decoded.get('Regen_Active', 0))
                self.vehicle_state['regen_power']      = decoded.get('Regen_Power', 0)
                self.vehicle_state['energy_recovered'] = decoded.get('Energy_Recovered', 0)

    # --- LIN Bus Listeners ----------------------------------------

    def listen_lin_bus(self):
        while self.running:
            if 'tpms' in self.lin_bus:
                tpms = self.lin_bus['tpms']
                self.vehicle_state['tyre_pressure_fl'] = tpms.get('pressure_fl', 0) / 10.0
                self.vehicle_state['tyre_pressure_fr'] = tpms.get('pressure_fr', 0) / 10.0
                self.vehicle_state['tyre_pressure_rl'] = tpms.get('pressure_rl', 0) / 10.0
                self.vehicle_state['tyre_pressure_rr'] = tpms.get('pressure_rr', 0) / 10.0
                self.vehicle_state['tyre_warning']     = bool(tpms.get('warning', 0))
            if 'window_seat' in self.lin_bus:
                ws = self.lin_bus['window_seat']
                self.vehicle_state['window_fl']       = ws.get('window_fl', 0)
                self.vehicle_state['window_fr']       = ws.get('window_fr', 0)
                self.vehicle_state['rain_detected']   = ws.get('rain_detected', False)
                self.vehicle_state['seat_driver_pos'] = ws.get('seat_driver_pos', 50)
            time.sleep(0.5)

    def publish_to_ethernet(self):
        while self.running:
            self.ethernet_bus['vehicle_state'] = self.vehicle_state.copy()
            time.sleep(0.1)

    def start(self):
        print("[SECURE GATEWAY] Starting with IDS Active...")
        threads = [
            threading.Thread(target=self.listen_lin_bus),
            threading.Thread(target=self.publish_to_ethernet),
        ]
        for t in threads:
            t.daemon = True
            t.start()

    def stop(self):
        self.running = False
        print("[SECURE GATEWAY] Stopped.")
