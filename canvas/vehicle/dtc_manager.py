# CANVAS Project
# Module: Vehicle
# File: dtc_manager.py
# Real OBD-II Diagnostic Trouble Code manager

import time
import threading
from collections import OrderedDict

# -- Real OBD-II DTC Database ----------------------------------
DTC_DATABASE = {

    # -- Powertrain (P codes) ----------------------------------
    'P0217' : {
        'desc'     : 'Engine Coolant Over Temperature',
        'system'   : 'ENGINE',
        'severity' : 'CRITICAL',
        'action'   : 'Reduce engine load immediately'
    },
    'P0219' : {
        'desc'     : 'Engine Overspeed Condition',
        'system'   : 'ENGINE',
        'severity' : 'WARNING',
        'action'   : 'Reduce throttle input'
    },
    'P0562' : {
        'desc'     : 'System Voltage Low',
        'system'   : 'ENGINE',
        'severity' : 'WARNING',
        'action'   : 'Check battery and alternator'
    },
    'P0700' : {
        'desc'     : 'Transmission Control System Fault',
        'system'   : 'TRANSMISSION',
        'severity' : 'WARNING',
        'action'   : 'Check transmission ECU'
    },
    'P0715' : {
        'desc'     : 'Input Shaft Speed Sensor Circuit',
        'system'   : 'TRANSMISSION',
        'severity' : 'WARNING',
        'action'   : 'Check transmission speed sensor'
    },

    # -- Hybrid/EV (P0A codes) ---------------------------------
    'P0A00' : {
        'desc'     : 'Drive Motor A Performance',
        'system'   : 'MOTOR',
        'severity' : 'CRITICAL',
        'action'   : 'Inspect electric motor system'
    },
    'P0A0F' : {
        'desc'     : 'Drive Motor A Over Temperature',
        'system'   : 'MOTOR',
        'severity' : 'CRITICAL',
        'action'   : 'Allow motor to cool down'
    },
    'P0A80' : {
        'desc'     : 'Replace Hybrid Battery Pack',
        'system'   : 'BATTERY',
        'severity' : 'CRITICAL',
        'action'   : 'HV battery replacement required'
    },
    'P1A00' : {
        'desc'     : 'HV Battery State of Charge Low',
        'system'   : 'BATTERY',
        'severity' : 'WARNING',
        'action'   : 'Charge HV battery immediately'
    },
    'P1A05' : {
        'desc'     : 'HV Battery Over Temperature',
        'system'   : 'BATTERY',
        'severity' : 'CRITICAL',
        'action'   : 'Stop vehicle, inspect battery cooling'
    },
    'P1A10' : {
        'desc'     : 'HV Battery Current Sensor Fault',
        'system'   : 'BATTERY',
        'severity' : 'WARNING',
        'action'   : 'Check BMS current sensor'
    },

    # -- Chassis (C codes) -------------------------------------
    'C0035' : {
        'desc'     : 'Left Front Wheel Speed Sensor Circuit',
        'system'   : 'ABS',
        'severity' : 'WARNING',
        'action'   : 'Inspect wheel speed sensor wiring'
    },
    'C0040' : {
        'desc'     : 'Right Front Wheel Speed Sensor Circuit',
        'system'   : 'ABS',
        'severity' : 'WARNING',
        'action'   : 'Inspect wheel speed sensor wiring'
    },
    'C0045' : {
        'desc'     : 'Left Rear Wheel Speed Sensor Circuit',
        'system'   : 'ABS',
        'severity' : 'WARNING',
        'action'   : 'Inspect wheel speed sensor wiring'
    },
    'C0050' : {
        'desc'     : 'Right Rear Wheel Speed Sensor Circuit',
        'system'   : 'ABS',
        'severity' : 'WARNING',
        'action'   : 'Inspect wheel speed sensor wiring'
    },
    'C0110' : {
        'desc'     : 'ABS Motor Circuit Malfunction',
        'system'   : 'ABS',
        'severity' : 'CRITICAL',
        'action'   : 'Inspect ABS motor and wiring'
    },
    'C0750' : {
        'desc'     : 'Tyre Pressure Monitor Sensor A Circuit',
        'system'   : 'TPMS',
        'severity' : 'WARNING',
        'action'   : 'Check tyre pressure and TPMS sensor'
    },
    'C0775' : {
        'desc'     : 'Tyre Pressure Low   All Tyres',
        'system'   : 'TPMS',
        'severity' : 'WARNING',
        'action'   : 'Inflate tyres to recommended pressure'
    },

    # -- Body (B codes) ----------------------------------------
    'B0001' : {
        'desc'     : 'Driver Frontal Stage 1 Deployment',
        'system'   : 'AIRBAG',
        'severity' : 'CRITICAL',
        'action'   : 'Vehicle involved in collision'
    },
    'B0002' : {
        'desc'     : 'Passenger Frontal Stage 1 Deployment',
        'system'   : 'AIRBAG',
        'severity' : 'CRITICAL',
        'action'   : 'Vehicle involved in collision'
    },
    'B0051' : {
        'desc'     : 'Driver Seatbelt Not Fastened',
        'system'   : 'AIRBAG',
        'severity' : 'INFO',
        'action'   : 'Fasten seatbelt'
    },

    # -- Network (U codes) -------------------------------------
    'U0001' : {
        'desc'     : 'High Speed CAN Communication Bus',
        'system'   : 'NETWORK',
        'severity' : 'CRITICAL',
        'action'   : 'Check CAN bus wiring and termination'
    },
    'U0100' : {
        'desc'     : 'Lost Communication with ECM/PCM',
        'system'   : 'NETWORK',
        'severity' : 'CRITICAL',
        'action'   : 'Check Engine ECU connection'
    },
    'U0121' : {
        'desc'     : 'Lost Communication with ABS Control Module',
        'system'   : 'NETWORK',
        'severity' : 'CRITICAL',
        'action'   : 'Check ABS ECU connection'
    },
    'U0140' : {
        'desc'     : 'Lost Communication with Body Control Module',
        'system'   : 'NETWORK',
        'severity' : 'WARNING',
        'action'   : 'Check BCM connection'
    },
}

# -- Severity colors for dashboard ----------------------------
SEVERITY_COLOR = {
    'CRITICAL' : '#ff2244',
    'WARNING'  : '#ffcc00',
    'INFO'     : '#00b4ff',
}

class DTCManager:
    def __init__(self):
        self.lock          = threading.Lock()
        # Active DTCs   OrderedDict preserves insertion order
        self.active_dtcs   = OrderedDict()
        # Full history including cleared codes
        self.dtc_history   = []
        self.running       = True

    def set_fault(self, code):
        """Log a DTC fault   called by any ECU"""
        if code not in DTC_DATABASE:
            print(f"[DTC] Unknown code: {code}")
            return

        with self.lock:
            if code not in self.active_dtcs:
                entry = {
                    'code'      : code,
                    'desc'      : DTC_DATABASE[code]['desc'],
                    'system'    : DTC_DATABASE[code]['system'],
                    'severity'  : DTC_DATABASE[code]['severity'],
                    'action'    : DTC_DATABASE[code]['action'],
                    'timestamp' : time.strftime('%H:%M:%S'),
                    'count'     : 1,
                    'active'    : True,
                }
                self.active_dtcs[code] = entry
                self.dtc_history.append(entry.copy())

                sev   = DTC_DATABASE[code]['severity']
                desc  = DTC_DATABASE[code]['desc']
                print(f"[DTC] [ERROR] FAULT SET   "
                      f"[{code}] {desc} "
                      f"({sev})")
            else:
                # Increment occurrence count
                self.active_dtcs[code]['count'] += 1

    def clear_fault(self, code):
        """Clear a specific DTC   like OBD scanner"""
        with self.lock:
            if code in self.active_dtcs:
                self.active_dtcs[code]['active'] = False
                del self.active_dtcs[code]
                print(f"[DTC] [OK] FAULT CLEARED [{code}]")

    def clear_all(self):
        """Clear all DTCs   like full OBD reset"""
        with self.lock:
            count = len(self.active_dtcs)
            self.active_dtcs.clear()
            print(f"[DTC] [OK] All {count} fault(s) cleared")

    def get_active_dtcs(self):
        """Return list of active DTCs for dashboard"""
        with self.lock:
            return list(self.active_dtcs.values())

    def get_critical_count(self):
        """Return count of critical faults"""
        with self.lock:
            return sum(
                1 for d in self.active_dtcs.values()
                if d['severity'] == 'CRITICAL'
            )

    def get_warning_count(self):
        """Return count of warning faults"""
        with self.lock:
            return sum(
                1 for d in self.active_dtcs.values()
                if d['severity'] == 'WARNING'
            )

    def has_fault(self, code):
        """Check if specific fault is active"""
        with self.lock:
            return code in self.active_dtcs

    def stop(self):
        self.running = False
        print("[DTC MANAGER] Stopped.")


# -- Global DTC Manager instance -------------------------------
# Shared across all ECUs
dtc_manager = DTCManager()