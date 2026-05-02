# CANVAS Project
# Module: Vehicle
# File: fault_injector.py
# Fault injection engine — FMEA testing simulator

import time
import threading
from vehicle.dtc_manager import dtc_manager

# ── Predefined fault scenarios ────────────────────────────────
FAULT_SCENARIOS = {

    'battery_failure': {
        'name'  : 'HV Battery Failure',
        'desc'  : 'Simulates complete HV battery pack failure',
        'dtcs'  : ['P0A80', 'P1A00', 'P1A05'],
        'overrides': {
            'disable_motor'        : True,
            'force_hv_mode'        : True,
            'hv_battery_disconnect': True,
        },
        'delay' : 0.5,
    },

    'engine_overheat': {
        'name'  : 'Engine Overheating',
        'desc'  : 'Simulates engine coolant system failure',
        'dtcs'  : ['P0217'],
        'overrides': {
            'engine_cut_fuel' : True,
            'emergency_stop'  : True,
        },
        'delay' : 0.3,
    },

    'abs_failure': {
        'name'  : 'ABS System Failure',
        'desc'  : 'Simulates all wheel speed sensor failures',
        'dtcs'  : ['C0035', 'C0040', 'C0045', 'C0050',
                   'C0110'],
        'overrides': {
            'abs_heightened'  : True,
            'adas_alert_level': 'CRITICAL',
        },
        'delay' : 0.2,
    },

    'tyre_blowout': {
        'name'  : 'Tyre Blowout',
        'desc'  : 'Simulates sudden front-left tyre blowout',
        'dtcs'  : ['C0750', 'C0775'],
        'overrides': {
            'emergency_stop'  : True,
            'adas_alert_level': 'CRITICAL',
            'abs_heightened'  : True,
        },
        'delay' : 0.1,
    },

    'crash_event': {
        'name'  : 'Collision Event',
        'desc'  : 'Simulates frontal collision + airbag deployment',
        'dtcs'  : ['B0001', 'B0002'],
        'overrides': {
            'engine_cut_fuel'      : True,
            'hv_battery_disconnect': True,
            'emergency_stop'       : True,
            'adas_alert_level'     : 'CRITICAL',
        },
        'delay' : 0.1,
    },

    'can_bus_fault': {
        'name'  : 'CAN Bus Communication Fault',
        'desc'  : 'Simulates CAN bus network failure',
        'dtcs'  : ['U0001', 'U0100', 'U0121'],
        'overrides': {
            'adas_alert_level': 'CRITICAL',
        },
        'delay' : 0.3,
    },

    'motor_failure': {
        'name'  : 'Electric Motor Failure',
        'desc'  : 'Simulates electric motor system fault',
        'dtcs'  : ['P0A00', 'P0A0F'],
        'overrides': {
            'disable_motor' : True,
            'force_hv_mode' : True,
        },
        'delay' : 0.4,
    },

    'full_emergency': {
        'name'  : 'Full Emergency',
        'desc'  : 'Simulates complete vehicle emergency',
        'dtcs'  : ['P0217', 'C0035', 'B0001',
                   'P1A00', 'C0775'],
        'overrides': {
            'engine_cut_fuel'      : True,
            'disable_motor'        : True,
            'hv_battery_disconnect': True,
            'emergency_stop'       : True,
            'abs_heightened'       : True,
            'adas_alert_level'     : 'CRITICAL',
        },
        'delay' : 0.2,
    },
}

class FaultInjector:
    def __init__(self, ethernet_bus):
        self.ethernet_bus   = ethernet_bus
        self.running        = True
        self.active_scenario = None
        self.injection_log  = []
        self.lock           = threading.Lock()

    def inject_dtc(self, code):
        """Inject a single DTC fault code"""
        dtc_manager.set_fault(code)
        entry = {
            'type'     : 'DTC',
            'code'     : code,
            'timestamp': time.strftime('%H:%M:%S'),
        }
        with self.lock:
            self.injection_log.append(entry)
        print(f"[FAULT INJECTOR] 💉 DTC Injected: {code}")
        self._broadcast_log()

    def inject_scenario(self, scenario_key):
        """Inject a full fault scenario"""
        if scenario_key not in FAULT_SCENARIOS:
            print(f"[FAULT INJECTOR] Unknown scenario: "
                  f"{scenario_key}")
            return

        scenario = FAULT_SCENARIOS[scenario_key]
        print(f"\n[FAULT INJECTOR] 🚨 Injecting scenario: "
              f"{scenario['name']}")
        print(f"[FAULT INJECTOR] {scenario['desc']}")

        # Run injection in background thread
        t = threading.Thread(
            target=self._run_scenario,
            args=(scenario_key, scenario),
            daemon=True
        )
        t.start()

    def _run_scenario(self, key, scenario):
        """Execute scenario injection sequence"""
        self.active_scenario = key

        # Inject all DTCs with delay
        for dtc in scenario['dtcs']:
            dtc_manager.set_fault(dtc)
            time.sleep(scenario['delay'])

        # Apply overrides
        overrides = self.ethernet_bus.get('overrides', {})
        for k, v in scenario['overrides'].items():
            overrides[k] = v
        self.ethernet_bus['overrides'] = overrides

        # Log the injection
        entry = {
            'type'     : 'SCENARIO',
            'scenario' : scenario['name'],
            'dtcs'     : scenario['dtcs'],
            'timestamp': time.strftime('%H:%M:%S'),
        }
        with self.lock:
            self.injection_log.append(entry)

        print(f"[FAULT INJECTOR] ✅ Scenario complete: "
              f"{scenario['name']}")
        self._broadcast_log()

        # Auto-reset after 30 seconds
        time.sleep(30)
        self.reset_scenario(key)

    def reset_scenario(self, scenario_key=None):
        """Reset a scenario or all scenarios"""
        if scenario_key and scenario_key in FAULT_SCENARIOS:
            scenario  = FAULT_SCENARIOS[scenario_key]
            overrides = self.ethernet_bus.get('overrides', {})

            # Reset overrides for this scenario
            for k in scenario['overrides']:
                overrides[k] = False
            overrides['adas_alert_level'] = 'NORMAL'
            self.ethernet_bus['overrides'] = overrides

            # Clear DTCs
            for dtc in scenario['dtcs']:
                dtc_manager.clear_fault(dtc)

            print(f"[FAULT INJECTOR] ✅ Reset: "
                  f"{scenario['name']}")

        self.active_scenario = None
        self._broadcast_log()

    def reset_all(self):
        """Reset everything"""
        dtc_manager.clear_all()
        overrides = {
            'engine_cut_fuel'      : False,
            'force_hv_mode'        : False,
            'disable_motor'        : False,
            'force_regen'          : False,
            'emergency_stop'       : False,
            'hv_battery_disconnect': False,
            'transmission_hold'    : False,
            'abs_heightened'       : False,
            'adas_alert_level'     : 'NORMAL',
        }
        self.ethernet_bus['overrides'] = overrides
        self.active_scenario           = None
        print("[FAULT INJECTOR] ✅ All faults reset")
        self._broadcast_log()

    def _broadcast_log(self):
        """Push injection log to ethernet bus"""
        with self.lock:
            self.ethernet_bus['injection_log'] = (
                self.injection_log[-10:])  # Last 10 entries
            self.ethernet_bus['active_scenario'] = (
                self.active_scenario)

    def get_scenarios(self):
        """Return all available scenarios"""
        return {
            k: {
                'name': v['name'],
                'desc': v['desc'],
                'dtcs': v['dtcs'],
            }
            for k, v in FAULT_SCENARIOS.items()
        }

    def stop(self):
        self.running = False
        print("[FAULT INJECTOR] Stopped.")


# ── Global injector instance ──────────────────────────────────
_injector = None

def init_injector(ethernet_bus):
    global _injector
    _injector = FaultInjector(ethernet_bus)
    return _injector

def get_injector():
    return _injector