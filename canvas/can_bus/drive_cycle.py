# CANVAS Project
# Module: CAN Bus
# File: drive_cycle.py
# Master drive cycle — all ECUs follow this shared state

import time
import threading

class DriveCycle:
    def __init__(self):
        self.running = True

        # Current drive phase
        # Phases: IDLE, ACCELERATING, CITY, HIGHWAY, DECELERATING, STOPPED
        self.phase          = 'IDLE'
        self.phase_time     = 0        # seconds spent in current phase

        # Core vehicle state (smooth, realistic values)
        self.speed          = 0.0      # km/h
        self.rpm            = 800.0    # RPM
        self.throttle       = 0.0      # %
        self.brake_pressure = 0.0      # bar
        self.engine_temp    = 25.0     # °C — cold start
        self.gear           = 1        # current gear

        # Phase durations (seconds)
        self.PHASE_DURATIONS = {
            'IDLE'         : 10,
            'ACCELERATING' : 15,
            'CITY'         : 20,
            'HIGHWAY_ACCEL': 10,
            'HIGHWAY'      : 25,
            'HIGHWAY_DECEL': 10,
            'DECELERATING' : 10,
            'STOPPED'      : 5,
        }

        # Phase sequence
        self.PHASE_SEQUENCE = [
            'IDLE', 'ACCELERATING', 'CITY', 'HIGHWAY_ACCEL',
            'HIGHWAY', 'HIGHWAY_DECEL', 'DECELERATING', 'STOPPED'
        ]
        self.phase_index = 0

    def _next_phase(self):
        """Move to next phase in cycle"""
        self.phase_index = (
            self.phase_index + 1) % len(self.PHASE_SEQUENCE)
        self.phase      = self.PHASE_SEQUENCE[self.phase_index]
        self.phase_time = 0
        print(f"\n[DRIVE CYCLE] ── Phase: {self.phase} ──")

    def _update_idle(self):
        """Engine on, car stationary"""
        self.speed          = 0.0
        self.rpm            = 750 + (self.engine_temp / 90.0) * 50
        self.throttle       = 0.0
        self.brake_pressure = 0.0
        self.gear           = 1

    def _update_accelerating(self):
        """Gradual acceleration from 0 to 50 km/h"""
        progress      = min(1.0, self.phase_time /
                           self.PHASE_DURATIONS['ACCELERATING'])
        self.speed          = progress * 50.0
        self.rpm            = 800 + progress * 2200
        self.throttle       = 40 + progress * 40
        self.brake_pressure = 0.0
        # Gear shifts
        if self.speed < 20:   self.gear = 1
        elif self.speed < 35: self.gear = 2
        else:                 self.gear = 3

    def _update_city(self):
        """City driving — 40-60 km/h with mild variations"""
        import math
        # Gentle sine wave for natural speed variation
        wave            = math.sin(self.phase_time * 0.3) * 10
        self.speed          = max(30.0, min(65.0, 50.0 + wave))
        self.rpm            = 1200 + (self.speed / 60.0) * 800
        self.throttle       = 25 + abs(wave)
        self.brake_pressure = max(0, -wave * 1.5)
        self.gear           = 3 if self.speed < 45 else 4

    def _update_highway_accel(self):
        """Gradual acceleration from 50 to 110 km/h"""
        progress      = min(1.0, self.phase_time /
                           self.PHASE_DURATIONS['HIGHWAY_ACCEL'])
        self.speed          = 50.0 + progress * 60.0
        self.rpm            = 1500 + progress * 1500
        self.throttle       = 50 + progress * 30
        self.brake_pressure = 0.0
        if self.speed < 60:   self.gear = 3
        elif self.speed < 80: self.gear = 4
        elif self.speed < 100: self.gear = 5
        else:                  self.gear = 6

    def _update_highway(self):
        """Highway driving — 100-120 km/h steady"""
        import math
        wave            = math.sin(self.phase_time * 0.1) * 5
        self.speed          = max(95.0, min(120.0, 110.0 + wave))
        self.rpm            = 2000 + (self.speed / 120.0) * 800
        self.throttle       = 35 + abs(wave * 0.5)
        self.brake_pressure = 0.0
        self.gear           = 6

    def _update_highway_decel(self):
        """Gradual braking from 110 to 60 km/h"""
        progress            = min(1.0, self.phase_time /
                               self.PHASE_DURATIONS['HIGHWAY_DECEL'])
        self.speed          = 110.0 - progress * 50.0
        self.rpm            = 2500 - progress * 1000
        self.throttle       = 0.0
        self.brake_pressure = 10 + progress * 20
        if self.speed > 100:  self.gear = 6
        elif self.speed > 80: self.gear = 5
        elif self.speed > 60: self.gear = 4
        else:                 self.gear = 3

    def _update_decelerating(self):
        """Gradual braking from 60 km/h to 0"""
        progress            = min(1.0, self.phase_time /
                               self.PHASE_DURATIONS['DECELERATING'])
        self.speed          = max(0.0, 60.0 * (1.0 - progress))
        self.rpm            = max(800.0, 2000 * (1.0 - progress))
        self.throttle       = 0.0
        self.brake_pressure = 20 + progress * 40
        if self.speed < 10:   self.gear = 1
        elif self.speed < 25: self.gear = 2
        elif self.speed < 40: self.gear = 3
        else:                 self.gear = 4

    def _update_stopped(self):
        """Car fully stopped"""
        self.speed          = 0.0
        self.rpm            = 750.0
        self.throttle       = 0.0
        self.brake_pressure = 15.0
        self.gear           = 1

    def run(self):
        """Main drive cycle loop"""
        UPDATE_RATE = 0.1   # 100ms update rate

        while self.running:
            self.phase_time += UPDATE_RATE

            # Update values based on current phase
            if   self.phase == 'IDLE':         self._update_idle()
            elif self.phase == 'ACCELERATING': self._update_accelerating()
            elif self.phase == 'CITY':         self._update_city()
            elif self.phase == 'HIGHWAY_ACCEL':self._update_highway_accel()
            elif self.phase == 'HIGHWAY':      self._update_highway()
            elif self.phase == 'HIGHWAY_DECEL':self._update_highway_decel()
            elif self.phase == 'DECELERATING': self._update_decelerating()
            elif self.phase == 'STOPPED':      self._update_stopped()

            # Engine warms up gradually (cold start → 90°C)
            if self.speed > 0:
                self.engine_temp = min(
                    90.0, self.engine_temp + 0.05)
            else:
                self.engine_temp = max(
                    25.0, self.engine_temp - 0.01)

            # Move to next phase when duration expires
            if self.phase_time >= self.PHASE_DURATIONS[self.phase]:
                self._next_phase()

            time.sleep(UPDATE_RATE)

    def start(self):
        print("[DRIVE CYCLE] Starting full drive cycle simulation...")
        t        = threading.Thread(target=self.run)
        t.daemon = True
        t.start()

    def stop(self):
        self.running = False
        print("[DRIVE CYCLE] Stopped.")