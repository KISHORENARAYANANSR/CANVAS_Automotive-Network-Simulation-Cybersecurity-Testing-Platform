# CANVAS Project
# Module: LIN Bus
# File: window_seat_ecu.py
# Simulates Window + Seat ECU   body comfort electronics on LIN Bus

import time
import random
import threading

class WindowSeatECU:
    def __init__(self, lin_bus):
        self.lin_bus = lin_bus
        self.running = True

        # Window positions (0=fully closed, 100=fully open)
        self.window_fl = 0      # Front Left
        self.window_fr = 0      # Front Right
        self.window_rl = 0      # Rear Left
        self.window_rr = 0      # Rear Right

        # Window movement status
        self.window_fl_moving = False
        self.window_fr_moving = False
        self.window_rl_moving = False
        self.window_rr_moving = False

        # Seat positions (0=fully back, 100=fully forward)
        self.seat_driver_pos      = 50    # Driver seat position
        self.seat_passenger_pos   = 50    # Passenger seat position
        self.seat_driver_recline  = 45    # Driver recline angle
        self.seat_pass_recline    = 45    # Passenger recline angle

        # Mirror positions
        self.mirror_left_angle    = 0     # degrees
        self.mirror_right_angle   = 0     # degrees

        # Safety   auto close windows if rain detected
        self.rain_detected        = False

    def simulate_windows(self):
        """Simulate random window open/close commands"""
        while self.running:
            # Randomly open/close windows (simulates user pressing button)
            for tyre in ['fl', 'fr', 'rl', 'rr']:
                if random.random() < 0.05:   # 5% chance of movement
                    target = random.choice([0, 25, 50, 75, 100])
                    current = getattr(self, f'window_{tyre}')

                    if current < target:
                        new_pos = min(target, current + 10)
                        setattr(self, f'window_{tyre}_moving', True)
                    elif current > target:
                        new_pos = max(target, current - 10)
                        setattr(self, f'window_{tyre}_moving', True)
                    else:
                        new_pos = current
                        setattr(self, f'window_{tyre}_moving', False)

                    setattr(self, f'window_{tyre}', new_pos)
                    print(f"[WINDOW/SEAT ECU] Window {tyre.upper()} -> "
                          f"{new_pos}% open")

            # Simulate rain detection (1% chance)
            if random.random() < 0.01:
                self.rain_detected = True
                print("[WINDOW/SEAT ECU]     Rain detected -> "
                      "Auto closing all windows!")
                self.window_fl = 0
                self.window_fr = 0
                self.window_rl = 0
                self.window_rr = 0
            else:
                self.rain_detected = False

            time.sleep(1.0)

    def simulate_seats(self):
        """Simulate random seat adjustment commands"""
        while self.running:
            # Randomly adjust seat positions
            if random.random() < 0.03:
                self.seat_driver_pos = random.randint(30, 80)
                self.seat_driver_recline = random.randint(25, 60)
                print(f"[WINDOW/SEAT ECU] Driver Seat -> "
                      f"Pos:{self.seat_driver_pos}% "
                      f"Recline:{self.seat_driver_recline} ")

            if random.random() < 0.02:
                self.seat_passenger_pos = random.randint(30, 80)
                self.seat_pass_recline  = random.randint(25, 60)
                print(f"[WINDOW/SEAT ECU] Passenger Seat -> "
                      f"Pos:{self.seat_passenger_pos}% "
                      f"Recline:{self.seat_pass_recline} ")

            time.sleep(2.0)

    def send_lin_frame(self):
        """Send LIN Bus frame with window + seat data"""
        while self.running:
            frame = {
                'id'                  : 0x20,  # LIN Frame ID for Window/Seat
                'window_fl'           : self.window_fl,
                'window_fr'           : self.window_fr,
                'window_rl'           : self.window_rl,
                'window_rr'           : self.window_rr,
                'seat_driver_pos'     : self.seat_driver_pos,
                'seat_passenger_pos'  : self.seat_passenger_pos,
                'seat_driver_recline' : self.seat_driver_recline,
                'seat_pass_recline'   : self.seat_pass_recline,
                'mirror_left'         : self.mirror_left_angle,
                'mirror_right'        : self.mirror_right_angle,
                'rain_detected'       : self.rain_detected
            }

            # Publish to LIN bus (shared dict)
            self.lin_bus['window_seat'] = frame

            print(f"[WINDOW/SEAT ECU] LIN Sent -> "
                  f"Windows FL:{self.window_fl}% "
                  f"FR:{self.window_fr}% "
                  f"RL:{self.window_rl}% "
                  f"RR:{self.window_rr}% | "
                  f"Driver Seat:{self.seat_driver_pos}%")
            time.sleep(1.0)   # LIN bus   slower cycle time

    def start(self):
        print("[WINDOW/SEAT ECU] Starting...")
        threads = [
            threading.Thread(target=self.simulate_windows),
            threading.Thread(target=self.simulate_seats),
            threading.Thread(target=self.send_lin_frame),
        ]
        for t in threads:
            t.daemon = True
            t.start()

    def stop(self):
        self.running = False
        print("[WINDOW/SEAT ECU] Stopped.")