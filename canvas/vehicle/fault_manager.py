# CANVAS Project
# Module: Vehicle
# File: fault_manager.py
# ECU interdependencies + fault propagation engine

import time
import threading
from vehicle.dtc_manager import dtc_manager

class FaultManager:
    def __init__(self, ethernet_bus):
        self.ethernet_bus = ethernet_bus
        self.running      = True

        # Override flags — set by fault manager
        # ECUs check these flags every cycle
        self.overrides = {
            'engine_cut_fuel'     : False,
            'force_hv_mode'       : False,
            'disable_motor'       : False,
            'force_regen'         : False,
            'emergency_stop'      : False,
            'hv_battery_disconnect': False,
            'transmission_hold'   : False,
            'abs_heightened'      : False,
            'adas_alert_level'    : 'NORMAL',
        }

        # Broadcast overrides to ethernet bus
        self.ethernet_bus['overrides'] = self.overrides

        # Previous state — to detect changes
        self._prev = {}

    def _set_override(self, key, value):
        """Set an override flag + broadcast"""
        if self.overrides.get(key) != value:
            self.overrides[key] = value
            self.ethernet_bus['overrides'] = (
                self.overrides.copy())
            status = "ON" if value else "OFF"
            print(f"[FAULT MGR] ⚡ Override: "
                  f"{key} → {status}")

    def _check_engine(self, state):
        """Engine ECU fault rules"""

        rpm   = state.get('engine_rpm', 0)
        temp  = state.get('engine_temp', 0)
        speed = state.get('vehicle_speed', 0)

        # Rule 1: Engine overspeed → force downshift
        if rpm > 4500:
            dtc_manager.set_fault('P0219')
            self._set_override('transmission_hold', True)
            print("[FAULT MGR] 🔴 Engine overspeed → "
                  "Forcing transmission downshift")
        else:
            self._set_override('transmission_hold', False)

        # Rule 2: Engine overtemp → switch to EV mode
        if temp >= 95:
            dtc_manager.set_fault('P0217')
            self._set_override('force_hv_mode', False)
            print("[FAULT MGR] 🌡️  Engine overtemp → "
                  "Switching to EV mode")

        # Rule 3: Engine overtemp critical → cut fuel
        if temp >= 105:
            self._set_override('engine_cut_fuel', True)
            self._set_override('emergency_stop', True)
            print("[FAULT MGR] 🚨 CRITICAL OVERHEAT → "
                  "Fuel cut + Emergency stop!")
        else:
            self._set_override('engine_cut_fuel', False)

    def _check_abs(self, state):
        """ABS ECU fault rules"""

        brake  = state.get('brake_pressure', 0)
        speed  = state.get('vehicle_speed', 0)
        wheels = [
            state.get('wheel_speed_fl', 0),
            state.get('wheel_speed_fr', 0),
            state.get('wheel_speed_rl', 0),
            state.get('wheel_speed_rr', 0),
        ]

        # Rule 1: Hard braking → activate regen
        if brake > 40 and speed > 10:
            self._set_override('force_regen', True)
            print("[FAULT MGR] ⚡ Hard braking → "
                  "Forcing regen braking")
        else:
            self._set_override('force_regen', False)

        # Rule 2: Wheel speed mismatch → ABS heightened
        if max(wheels) - min(wheels) > 15:
            dtc_manager.set_fault('C0035')
            self._set_override('abs_heightened', True)
            print("[FAULT MGR] ⚠️  Wheel mismatch → "
                  "ABS heightened sensitivity")
        else:
            self._set_override('abs_heightened', False)

        # Rule 3: Emergency brake
        if brake >= 70 and speed > 5:
            self._set_override('emergency_stop', True)
            self._set_override('adas_alert_level', 'CRITICAL')
            print("[FAULT MGR] 🚨 EMERGENCY BRAKE → "
                  "ADAS critical alert!")
        elif brake < 50:
            self._set_override('emergency_stop', False)
            self._set_override('adas_alert_level', 'NORMAL')

    def _check_battery(self, state):
        """BMS ECU fault rules"""

        soc          = state.get('battery_soc', 75)
        batt_state   = state.get('battery_state', 'NORMAL')
        batt_voltage = state.get('battery_voltage', 200)

        # Rule 1: Battery critical → force HV mode
        if soc <= 15:
            dtc_manager.set_fault('P1A00')
            self._set_override('force_hv_mode', True)
            self._set_override('disable_motor', True)
            print("[FAULT MGR] 🔋 Battery critical → "
                  "Force HV + Disable motor")

        elif soc <= 25:
            self._set_override('force_hv_mode', True)
            self._set_override('disable_motor', False)
            print("[FAULT MGR] 🔋 Battery low → "
                  "Force HV mode")
        else:
            self._set_override('force_hv_mode', False)
            self._set_override('disable_motor', False)

        # Rule 2: Battery critical state
        if batt_state == 'CRITICAL':
            dtc_manager.set_fault('P0A80')
            self._set_override('hv_battery_disconnect', True)
            print("[FAULT MGR] 🚨 HV Battery critical → "
                  "Disconnect HV system!")
        else:
            self._set_override(
                'hv_battery_disconnect', False)

        # Rule 3: Voltage too low
        if batt_voltage < 170:
            dtc_manager.set_fault('P0562')

    def _check_airbag(self, state):
        """Airbag ECU fault rules"""

        crash    = state.get('crash_detected', False)
        deployed = state.get('airbag_deployed', False)
        impact   = state.get('impact_force', 0)

        # Rule 1: Crash detected → engine cut + HV disconnect
        if crash and impact > 10:
            dtc_manager.set_fault('B0001')
            self._set_override('engine_cut_fuel', True)
            self._set_override('hv_battery_disconnect', True)
            self._set_override('emergency_stop', True)
            self._set_override('adas_alert_level', 'CRITICAL')
            print("[FAULT MGR] 💥 CRASH DETECTED → "
                  "Engine cut + HV disconnect + "
                  "Emergency stop!")

        # Rule 2: No seatbelt
        seatbelt = state.get('seatbelt_fl', True)
        if not seatbelt:
            dtc_manager.set_fault('B0051')

    def _check_tpms(self, state):
        """TPMS fault rules"""

        tyres = [
            state.get('tyre_pressure_fl', 33),
            state.get('tyre_pressure_fr', 33),
            state.get('tyre_pressure_rl', 33),
            state.get('tyre_pressure_rr', 33),
        ]

        # Rule 1: Any tyre below 26 PSI → DTC + ADAS alert
        if any(t < 26 and t > 0 for t in tyres):
            dtc_manager.set_fault('C0775')
            self._set_override(
                'adas_alert_level', 'WARNING')
            print("[FAULT MGR] 🔴 Tyre pressure low → "
                  "ADAS warning!")

        # Rule 2: Tyre blowout (< 15 PSI)
        if any(t < 15 and t > 0 for t in tyres):
            dtc_manager.set_fault('C0750')
            self._set_override('emergency_stop', True)
            self._set_override(
                'adas_alert_level', 'CRITICAL')
            print("[FAULT MGR] 🚨 TYRE BLOWOUT → "
                  "Emergency stop!")

    def _check_motor(self, state):
        """Motor ECU fault rules"""

        motor_mode = state.get('motor_mode', 'IDLE')
        torque     = state.get('motor_torque', 0)

        # Rule 1: Motor disabled override
        if self.overrides['disable_motor']:
            print("[FAULT MGR] 🔌 Motor disabled "
                  "by fault override")

        # Rule 2: Forced regen override
        if self.overrides['force_regen']:
            print("[FAULT MGR] ⚡ Regen forced "
                  "by braking event")

    def monitor(self):
        """Main monitoring loop — runs every 100ms"""
        while self.running:
            state = self.ethernet_bus.get(
                'vehicle_state', {})
            if not state:
                time.sleep(0.1)
                continue

            # Run all fault checks
            self._check_engine(state)
            self._check_abs(state)
            self._check_battery(state)
            self._check_airbag(state)
            self._check_tpms(state)
            self._check_motor(state)

            # Broadcast fault summary
            self.ethernet_bus['fault_summary'] = {
                'active_dtcs'  : len(
                    dtc_manager.get_active_dtcs()),
                'critical'     : dtc_manager.get_critical_count(),
                'warnings'     : dtc_manager.get_warning_count(),
                'overrides'    : self.overrides.copy(),
                'alert_level'  : self.overrides[
                    'adas_alert_level'],
            }

            time.sleep(0.1)

    def start(self):
        print("[FAULT MGR] Starting fault "
              "propagation engine...")
        t        = threading.Thread(
            target=self.monitor, daemon=True)
        t.start()

    def stop(self):
        self.running = False
        print("[FAULT MGR] Stopped.")