# CANVAS Project
# Module: Ethernet
# File: adas_ecu.py
# ADAS ECU — safety decision engine running on Automotive Ethernet

import time
import threading

class ADASECU:
    def __init__(self, ethernet_bus):
        self.ethernet_bus = ethernet_bus
        self.running      = True

        # ADAS warning flags
        self.collision_warning    = False
        self.emergency_brake      = False
        self.lane_departure       = False
        self.battery_critical     = False
        self.tyre_warning         = False
        self.overspeed_warning    = False
        self.engine_overheat      = False
        self.airbag_alert         = False
        self.regen_suggestion     = False

        # ADAS thresholds
        self.SPEED_LIMIT          = 120    # km/h
        self.BRAKE_EMERGENCY      = 70     # bar — emergency brake threshold
        self.ENGINE_TEMP_MAX      = 95     # °C
        self.SOC_CRITICAL         = 15     # %
        self.TYRE_PRESSURE_MIN    = 26.0   # PSI

        # Decision log
        self.decisions = []

    def analyze_vehicle_state(self):
        """Core ADAS logic — continuously analyze vehicle state"""
        while self.running:
            if 'vehicle_state' not in self.ethernet_bus:
                time.sleep(0.1)
                continue

            state = self.ethernet_bus['vehicle_state']

            # ── Collision + Emergency Brake ──────────────────────
            if (state['brake_pressure'] >= self.BRAKE_EMERGENCY and
                    state['vehicle_speed'] > 10):
                self.emergency_brake   = True
                self.collision_warning = True
                self._log("🚨 EMERGENCY BRAKE TRIGGERED — "
                         f"Brake:{state['brake_pressure']}bar "
                         f"Speed:{state['vehicle_speed']}km/h")
            else:
                self.emergency_brake   = False
                self.collision_warning = False

            # ── Overspeed Warning ────────────────────────────────
            if state['vehicle_speed'] > self.SPEED_LIMIT:
                self.overspeed_warning = True
                self._log(f"⚠️  OVERSPEED — "
                         f"{state['vehicle_speed']}km/h "
                         f"Limit:{self.SPEED_LIMIT}km/h")
            else:
                self.overspeed_warning = False

            # ── Engine Overheat ──────────────────────────────────
            if state['engine_temp'] >= self.ENGINE_TEMP_MAX:
                self.engine_overheat = True
                self._log(f"🌡️  ENGINE OVERHEAT — "
                         f"Temp:{state['engine_temp']}°C")
            else:
                self.engine_overheat = False

            # ── Battery Critical ─────────────────────────────────
            if state['battery_soc'] <= self.SOC_CRITICAL:
                self.battery_critical = True
                self._log(f"🔋 BATTERY CRITICAL — "
                         f"SOC:{state['battery_soc']}%")
            else:
                self.battery_critical = False

            # ── Tyre Pressure Warning ────────────────────────────
            tyres = [
                state['tyre_pressure_fl'],
                state['tyre_pressure_fr'],
                state['tyre_pressure_rl'],
                state['tyre_pressure_rr']
            ]
            if any(t < self.TYRE_PRESSURE_MIN and t > 0 for t in tyres):
                self.tyre_warning = True
                self._log(f"🔴 TYRE PRESSURE LOW — "
                         f"FL:{state['tyre_pressure_fl']:.1f} "
                         f"FR:{state['tyre_pressure_fr']:.1f} "
                         f"RL:{state['tyre_pressure_rl']:.1f} "
                         f"RR:{state['tyre_pressure_rr']:.1f} PSI")
            else:
                self.tyre_warning = False

            # ── Airbag Alert ─────────────────────────────────────
            if state['crash_detected']:
                self.airbag_alert = True
                self._log(f"💥 CRASH DETECTED — "
                         f"Impact:{state['impact_force']}G "
                         f"Airbag:{state['airbag_deployed']}")
            else:
                self.airbag_alert = False

            # ── Regen Braking Suggestion ─────────────────────────
            if (state['vehicle_speed'] > 20 and
                    state['brake_pressure'] > 10 and
                    not state['regen_active'] and
                    state['battery_soc'] < 90):
                self.regen_suggestion = True
                self._log("⚡ REGEN SUGGESTION — "
                         "Regenerative braking available")
            else:
                self.regen_suggestion = False

            # Publish ADAS decisions back to ethernet bus
            self.ethernet_bus['adas_decisions'] = {
                'collision_warning' : self.collision_warning,
                'emergency_brake'   : self.emergency_brake,
                'overspeed_warning' : self.overspeed_warning,
                'engine_overheat'   : self.engine_overheat,
                'battery_critical'  : self.battery_critical,
                'tyre_warning'      : self.tyre_warning,
                'airbag_alert'      : self.airbag_alert,
                'regen_suggestion'  : self.regen_suggestion,
            }

            time.sleep(0.1)

    def _log(self, message):
        """Log ADAS decisions with timestamp"""
        timestamp = time.strftime('%H:%M:%S')
        entry     = f"[{timestamp}] [ADAS ECU] {message}"
        self.decisions.append(entry)
        print(entry)

    def print_status(self):
        """Periodically print full ADAS status"""
        while self.running:
            print("\n" + "="*60)
            print("           ADAS ECU — SYSTEM STATUS")
            print("="*60)
            print(f"  Collision Warning  : {self.collision_warning}")
            print(f"  Emergency Brake    : {self.emergency_brake}")
            print(f"  Overspeed Warning  : {self.overspeed_warning}")
            print(f"  Engine Overheat    : {self.engine_overheat}")
            print(f"  Battery Critical   : {self.battery_critical}")
            print(f"  Tyre Warning       : {self.tyre_warning}")
            print(f"  Airbag Alert       : {self.airbag_alert}")
            print(f"  Regen Suggestion   : {self.regen_suggestion}")
            print("="*60 + "\n")
            time.sleep(5.0)

    def start(self):
        print("[ADAS ECU] Starting...")
        threads = [
            threading.Thread(target=self.analyze_vehicle_state),
            threading.Thread(target=self.print_status),
        ]
        for t in threads:
            t.daemon = True
            t.start()

    def stop(self):
        self.running = False
        print("[ADAS ECU] Stopped.")