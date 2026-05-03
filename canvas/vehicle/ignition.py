# CANVAS Project
# Module: Vehicle
# File: ignition.py
# Real car ignition sequence   ACC -> IGN -> CRANK -> RUN

import time
import threading
from vehicle.dtc_manager import dtc_manager

# -- Ignition States -------------------------------------------
IGN_OFF      = 'OFF'
IGN_ACC      = 'ACC'          # Accessories on
IGN_ON       = 'IGN_ON'       # Ignition on   ECUs wake up
IGN_CRANK    = 'CRANKING'     # Engine cranking
IGN_RUN      = 'RUNNING'      # Normal operation
IGN_SHUTDOWN = 'SHUTDOWN'     # Shutdown sequence

class IgnitionSystem:
    def __init__(self, ethernet_bus):
        self.ethernet_bus   = ethernet_bus
        self.state          = IGN_OFF
        self.running        = True

        # ECU ready flags   all False until ignition
        self.ecu_status = {
            'ENGINE'      : False,
            'ABS'         : False,
            'AIRBAG'      : False,
            'TRANSMISSION': False,
            'BMS'         : False,
            'MOTOR'       : False,
            'HYBRID_CTRL' : False,
            'REGEN_BRAKE' : False,
            'TPMS'        : False,
            'WINDOW_SEAT' : False,
            'GATEWAY'     : False,
            'ADAS'        : False,
        }

        # Ignition sequence timing (seconds)
        # Matches real hybrid vehicle boot times
        self.ECU_BOOT_TIMES = {
            'BMS'         : 0.3,   # Battery first
            'ENGINE'      : 0.5,
            'ABS'         : 0.6,
            'AIRBAG'      : 0.7,
            'TRANSMISSION': 0.8,
            'MOTOR'       : 0.9,
            'HYBRID_CTRL' : 1.1,
            'REGEN_BRAKE' : 1.2,
            'TPMS'        : 1.5,   # LIN   slower
            'WINDOW_SEAT' : 1.7,
            'GATEWAY'     : 1.8,
            'ADAS'        : 2.0,   # Last   needs all others
        }

    def _set_state(self, state):
        """Update ignition state + broadcast to dashboard"""
        self.state = state
        self.ethernet_bus['ignition_state'] = state
        print(f"\n[IGNITION] -- State: {state} --")

    def _boot_ecu(self, name, delay):
        """Simulate ECU waking up after delay"""
        time.sleep(delay)
        self.ecu_status[name] = True
        self.ethernet_bus['ecu_status'] = self.ecu_status.copy()
        print(f"[IGNITION] [OK] {name} ECU   Online")

    def run_sequence(self):
        """Full ignition sequence   exactly like a real car"""

        # -- Stage 1: OFF --------------------------------------
        self._set_state(IGN_OFF)
        print("[IGNITION] [KEY] Key inserted...")
        time.sleep(0.5)

        # -- Stage 2: ACC --------------------------------------
        self._set_state(IGN_ACC)
        print("[IGNITION] ACC ON   Radio, lights active")
        time.sleep(1.0)

        # -- Stage 3: IGN ON   ECUs start waking up ------------
        self._set_state(IGN_ON)
        print("[IGNITION] IGN ON   All ECUs initializing...")

        # Boot all ECUs in parallel with real timing
        boot_threads = []
        for ecu, delay in self.ECU_BOOT_TIMES.items():
            t = threading.Thread(
                target=self._boot_ecu,
                args=(ecu, delay),
                daemon=True
            )
            boot_threads.append(t)
            t.start()

        # Wait for all ECUs to boot
        for t in boot_threads:
            t.join()

        print("[IGNITION] All ECUs online [OK]")

        # -- Stage 4: Self Test --------------------------------
        print("\n[IGNITION] Running self-diagnostics...")
        self._run_self_test()
        time.sleep(0.5)

        # -- Stage 5: CRANK ------------------------------------
        self._set_state(IGN_CRANK)
        print("[IGNITION] [RUN] Engine cranking...")
        time.sleep(1.2)   # Real crank time ~1-2 seconds

        # -- Stage 6: RUN --------------------------------------
        self._set_state(IGN_RUN)
        print("[IGNITION] [CAR] Engine running   All systems GO!")
        print("[IGNITION] ==================================")

        # Broadcast ready state
        self.ethernet_bus['canvas_ready'] = True

    def _run_self_test(self):
        """Simulate real ECU self-diagnostic checks"""
        checks = [
            ('HV Battery voltage',   True,  None),
            ('CAN Bus communication',True,  None),
            ('ABS sensors',          True,  None),
            ('Airbag system',        True,  None),
            ('TPMS sensors',         True,  None),
            ('Motor system',         True,  None),
            ('Gateway ECU',          True,  None),
        ]

        all_passed = True
        for check, passed, dtc in checks:
            time.sleep(0.15)
            if passed:
                print(f"[SELF TEST] [OK] {check}   OK")
            else:
                print(f"[SELF TEST]   {check}   FAIL")
                if dtc:
                    dtc_manager.set_fault(dtc)
                all_passed = False

        if all_passed:
            print("[SELF TEST] All checks passed [OK]")
        else:
            print("[SELF TEST] [WARN]  Faults detected   "
                  "check DTC codes")

        self.ethernet_bus['self_test_passed'] = all_passed

    def shutdown_sequence(self):
        """Graceful shutdown   like turning off ignition"""
        self._set_state(IGN_SHUTDOWN)
        print("\n[IGNITION] [KEY] Shutdown sequence started...")

        # ECUs shut down in reverse order
        shutdown_order = list(
            reversed(list(self.ECU_BOOT_TIMES.keys())))

        for ecu in shutdown_order:
            time.sleep(0.1)
            self.ecu_status[ecu] = False
            self.ethernet_bus['ecu_status'] = (
                self.ecu_status.copy())
            print(f"[IGNITION] [ERROR] {ecu} ECU   Offline")

        self._set_state(IGN_OFF)
        self.ethernet_bus['canvas_ready'] = False
        print("[IGNITION] All systems offline. Goodbye! [BYE]")

    def start(self):
        """Run ignition sequence in background thread"""
        print("[IGNITION] Starting ignition sequence...")
        t        = threading.Thread(
            target=self.run_sequence, daemon=True)
        t.start()
        return t

    def stop(self):
        self.running = False
        self.shutdown_sequence()