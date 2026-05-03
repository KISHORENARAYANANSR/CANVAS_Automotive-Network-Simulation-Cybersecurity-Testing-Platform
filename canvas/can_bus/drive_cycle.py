import can
import time
import threading
import math
import random

class DriveCycle:
    def __init__(self, ethernet_bus=None):
        self.running      = True
        self.ethernet_bus = ethernet_bus

        # Current drive phase
        self.phase          = 'IDLE'
        self.phase_id       = 0        
        self.phase_time     = 0        

        # Core vehicle state
        self.speed          = 0.0      
        self.rpm            = 800.0    
        self.throttle       = 0.0      
        self.brake_pressure = 0.0      
        self.engine_temp    = 25.0     
        self.gear           = 1        

        # Phase durations (seconds)
        self.PHASE_DURATIONS = {
            'IDLE'         : 5,        # 5s IDLE to allow ignition
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
        self.phase_index = (self.phase_index + 1) % len(self.PHASE_SEQUENCE)
        self.phase      = self.PHASE_SEQUENCE[self.phase_index]
        self.phase_id   = self.phase_index
        self.phase_time = 0
        print(f"\n[DRIVE CYCLE] -- New Phase: {self.phase} --")

    def run(self):
        """Main drive cycle loop"""
        UPDATE_RATE = 0.1
        while self.running:
            self.phase_time += UPDATE_RATE

            # -- Check for Overrides (Fault Manager) --
            if self.ethernet_bus:
                overrides = self.ethernet_bus.get('overrides', {})
                if overrides.get('emergency_stop') or overrides.get('disable_motor'):
                    # Force stop but STILL allow phase transition so we don't get stuck in IDLE forever
                    self.speed          = max(0.0, self.speed - 5.0)
                    self.rpm            = 800.0
                    self.throttle       = 0.0
                    self.brake_pressure = 40.0
                else:
                    # Normal update based on phase
                    if   self.phase == 'IDLE':          self._update_idle()
                    elif self.phase == 'ACCELERATING':  self._update_accelerating()
                    elif self.phase == 'CITY':          self._update_city()
                    elif self.phase == 'HIGHWAY_ACCEL': self._update_highway_accel()
                    elif self.phase == 'HIGHWAY':       self._update_highway()
                    elif self.phase == 'HIGHWAY_DECEL': self._update_highway_decel()
                    elif self.phase == 'DECELERATING':  self._update_decelerating()
                    elif self.phase == 'STOPPED':       self._update_stopped()

                # --- MANUAL OVERRIDES (TEST MODE) ---
                if 'manual_speed' in overrides:
                    self.speed = overrides['manual_speed']
                if 'manual_rpm' in overrides:
                    self.rpm = overrides['manual_rpm']
                if 'manual_brake' in overrides:
                    self.brake_pressure = overrides['manual_brake']

            # Engine warms up
            if self.speed > 0 or self.phase == 'IDLE':
                self.engine_temp = min(90.0, self.engine_temp + 0.05)
            else:
                self.engine_temp = max(25.0, self.engine_temp - 0.01)

            # Move to next phase when duration expires
            if self.phase_time >= self.PHASE_DURATIONS[self.phase]:
                self._next_phase()

            time.sleep(UPDATE_RATE)

    def _update_idle(self):
        self.speed = 0.0
        self.rpm = 750 + (self.engine_temp / 90.0) * 50
        self.throttle = 0.0
        self.brake_pressure = 0.0
        self.gear = 1

    def _update_accelerating(self):
        progress = min(1.0, self.phase_time / self.PHASE_DURATIONS['ACCELERATING'])
        self.speed = progress * 50.0
        self.rpm = 800 + progress * 2200
        self.throttle = 40 + progress * 40
        self.brake_pressure = 0.0
        if self.speed < 20: self.gear = 1
        elif self.speed < 35: self.gear = 2
        else: self.gear = 3

    def _update_city(self):
        wave = math.sin(self.phase_time * 0.3) * 10
        self.speed = max(30.0, min(65.0, 50.0 + wave))
        self.rpm = 1200 + (self.speed / 60.0) * 800
        self.throttle = 25 + abs(wave)
        self.brake_pressure = max(0, -wave * 1.5)
        self.gear = 3 if self.speed < 45 else 4

    def _update_highway_accel(self):
        progress = min(1.0, self.phase_time / self.PHASE_DURATIONS['HIGHWAY_ACCEL'])
        self.speed = 50.0 + progress * 60.0
        self.rpm = 1500 + progress * 1500
        self.throttle = 50 + progress * 30
        self.brake_pressure = 0.0
        if self.speed < 60: self.gear = 3
        elif self.speed < 80: self.gear = 4
        elif self.speed < 100: self.gear = 5
        else: self.gear = 6

    def _update_highway(self):
        wave = math.sin(self.phase_time * 0.2) * 5
        self.speed = max(90.0, min(120.0, 110.0 + wave))
        self.rpm = 2200 + wave * 50
        self.throttle = 60 + wave
        self.brake_pressure = 0.0
        self.gear = 6

    def _update_highway_decel(self):
        progress = min(1.0, self.phase_time / self.PHASE_DURATIONS['HIGHWAY_DECEL'])
        self.speed = 110.0 - progress * 50.0
        self.rpm = 3000 - progress * 1500
        self.throttle = 0.0
        self.brake_pressure = 20.0
        if self.speed > 80: self.gear = 6
        elif self.speed > 60: self.gear = 4
        else: self.gear = 3

    def _update_decelerating(self):
        progress = min(1.0, self.phase_time / self.PHASE_DURATIONS['DECELERATING'])
        self.speed = 60.0 - progress * 60.0
        self.rpm = 1500 - progress * 700
        self.throttle = 0.0
        self.brake_pressure = 30.0
        if self.speed > 30: self.gear = 2
        else: self.gear = 1

    def _update_stopped(self):
        self.speed = 0.0
        self.rpm = 800.0
        self.throttle = 0.0
        self.brake_pressure = 15.0
        self.gear = 1

    def start(self):
        print("[DRIVE CYCLE] Starting full drive cycle simulation...")
        t = threading.Thread(target=self.run)
        t.daemon = True
        t.start()

    def stop(self):
        self.running = False
        print("[DRIVE CYCLE] Stopped.")