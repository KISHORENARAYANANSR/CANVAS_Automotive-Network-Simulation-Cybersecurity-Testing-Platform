# CANVAS Project
# Module: CAN Bus
# File: can_timing.py
# Real automotive CAN cycle time controller

import time
import threading

# -- Real CAN Cycle Times (milliseconds) -----------------------
# Source: Automotive CAN bus standards (ISO 11898)
# Lower cycle time = higher priority = safety critical

CAN_CYCLE_TIMES = {
    # Safety critical   10ms (100Hz)
    'ENGINE'       : 0.010,
    'ABS'          : 0.010,
    'MOTOR'        : 0.010,

    # Powertrain   20ms (50Hz)
    'AIRBAG'       : 0.020,
    'TRANSMISSION' : 0.020,
    'REGEN_BRAKE'  : 0.020,

    # Hybrid system   50ms (20Hz)
    'HYBRID_CTRL'  : 0.050,

    # Battery   100ms (10Hz)
    'BMS'          : 0.100,

    # Body/Comfort   1000ms (1Hz)
    'TPMS'         : 1.000,
    'WINDOW_SEAT'  : 1.000,

    # Gateway/ADAS   100ms
    'GATEWAY'      : 0.100,
    'ADAS'         : 0.100,
}

# -- CAN Message Priority (Arbitration IDs) --------------------
# Lower ID = Higher priority on real CAN bus
CAN_PRIORITY = {
    0x100 : 'ENGINE_RPM_SPEED',      # Highest priority
    0x101 : 'ENGINE_TEMP_THROTTLE',
    0x200 : 'ABS_WHEEL_SPEEDS',
    0x201 : 'ABS_BRAKE_PRESSURE',
    0x300 : 'AIRBAG_STATUS',
    0x400 : 'TRANSMISSION_STATUS',
    0x500 : 'BMS_BATTERY_STATUS',
    0x501 : 'BMS_TEMPERATURE',
    0x600 : 'MOTOR_STATUS',
    0x700 : 'TPMS_STATUS',
    0x800 : 'HYBRID_CTRL_STATUS',
    0x900 : 'REGEN_BRAKE_STATUS',
    0xA00 : 'ADAS_DECISIONS',        # Lowest priority
}

class CANTimer:
    """Precise cycle timer for a single ECU"""

    def __init__(self, ecu_name):
        self.ecu_name    = ecu_name
        self.cycle_time  = CAN_CYCLE_TIMES.get(
            ecu_name, 0.100)
        self.last_tick   = time.perf_counter()
        self.tick_count  = 0
        self.missed      = 0

    def wait(self):
        """Wait until next cycle time   precise timing"""
        now      = time.perf_counter()
        elapsed  = now - self.last_tick
        sleep_t  = self.cycle_time - elapsed

        if sleep_t > 0:
            time.sleep(sleep_t)
        else:
            # Missed cycle   log it
            self.missed += 1

        self.last_tick  = time.perf_counter()
        self.tick_count += 1

    def get_stats(self):
        """Return timing statistics"""
        return {
            'ecu'        : self.ecu_name,
            'cycle_ms'   : self.cycle_time * 1000,
            'ticks'      : self.tick_count,
            'missed'     : self.missed,
            'miss_rate'  : (self.missed / max(1,
                           self.tick_count)) * 100
        }


class CANTimingMonitor:
    """Monitors all ECU cycle times   like a real CAN analyzer"""

    def __init__(self):
        self.timers   = {}
        self.running  = True
        self.lock     = threading.Lock()

    def register(self, ecu_name):
        """Register an ECU for timing monitoring"""
        with self.lock:
            self.timers[ecu_name] = CANTimer(ecu_name)
            print(f"[CAN TIMING] Registered {ecu_name} "
                  f"-> {CAN_CYCLE_TIMES.get(ecu_name, 0.1)*1000:.0f}ms cycle")
        return self.timers[ecu_name]

    def print_stats(self):
        """Print timing stats for all ECUs"""
        while self.running:
            time.sleep(10)
            print("\n[CAN TIMING] -- Cycle Time Report --")
            with self.lock:
                for name, timer in self.timers.items():
                    s = timer.get_stats()
                    print(f"  {s['ecu']:<16} "
                          f"Cycle:{s['cycle_ms']:.0f}ms  "
                          f"Ticks:{s['ticks']}  "
                          f"Missed:{s['missed']}  "
                          f"MissRate:{s['miss_rate']:.1f}%")
            print("[CAN TIMING] -------------------------\n")

    def start(self):
        print("[CAN TIMING] Monitor started...")
        t        = threading.Thread(
            target=self.print_stats, daemon=True)
        t.start()

    def stop(self):
        self.running = False
        print("[CAN TIMING] Monitor stopped.")


# -- Global timing monitor instance ---------------------------
can_timing_monitor = CANTimingMonitor()