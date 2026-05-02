# CANVAS Project
# Module: CAN Bus
# File: engine_ecu.py
# Engine ECU with real 10ms CAN cycle time

import can
import threading
from can_bus.can_timing import can_timing_monitor
from vehicle.dtc_manager import dtc_manager

class EngineECU:
    def __init__(self, bus, drive_cycle):
        self.bus     = bus
        self.dc      = drive_cycle
        self.running = True
        # Register with timing monitor
        self.timer_rpm  = can_timing_monitor.register('ENGINE')

    def send_rpm_speed(self):
        """Send RPM + Speed at real 10ms cycle time"""
        while self.running:
            rpm      = int(self.dc.rpm)
            speed    = int(self.dc.speed)
            rpm_high = (rpm >> 8) & 0xFF
            rpm_low  = rpm & 0xFF

            msg = can.Message(
                arbitration_id=0x100,
                data=[rpm_high, rpm_low, speed,
                      0x00, 0x00, 0x00, 0x00, 0x00],
                is_extended_id=False
            )
            try:
                self.bus.send(msg)
            except Exception as e:
                dtc_manager.set_fault('U0100')

            # Check for overspeed fault
            if rpm > 4500:
                dtc_manager.set_fault('P0219')

            # Check for overtemp fault
            if int(self.dc.engine_temp) >= 95:
                dtc_manager.set_fault('P0217')

            print(f"[ENGINE ECU] RPM:{rpm} "
                  f"Speed:{speed}km/h "
                  f"Phase:{self.dc.phase}")

            # Real 10ms cycle time
            self.timer_rpm.wait()

    def send_temp_throttle(self):
        """Send Temp + Throttle at 20ms cycle"""
        timer = can_timing_monitor.register('ENGINE_TEMP')
        while self.running:
            temp     = int(self.dc.engine_temp)
            throttle = int(self.dc.throttle)

            msg = can.Message(
                arbitration_id=0x101,
                data=[temp, throttle,
                      0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                is_extended_id=False
            )
            try:
                self.bus.send(msg)
            except Exception:
                pass

            print(f"[ENGINE ECU] Temp:{temp}°C "
                  f"Throttle:{throttle}%")
            timer.wait()

    def start(self):
        print("[ENGINE ECU] Starting "
              "(10ms CAN cycle)...")
        threads = [
            threading.Thread(target=self.send_rpm_speed),
            threading.Thread(target=self.send_temp_throttle),
        ]
        for t in threads:
            t.daemon = True
            t.start()

    def stop(self):
        self.running = False
        print("[ENGINE ECU] Stopped.")