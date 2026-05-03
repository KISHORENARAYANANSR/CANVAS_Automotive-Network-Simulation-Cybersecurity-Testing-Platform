# CANVAS Project
# Module: CAN Bus
# File: engine_ecu.py
# Engine ECU with real 10ms CAN cycle time

import can
from vehicle.dtc_manager import dtc_manager
from utils.can_codec import codec

class EngineECU(can.Listener):
    def __init__(self, bus, drive_cycle):
        self.bus     = bus
        self.dc      = drive_cycle
        self.running = True

    def send_rpm_speed_step(self):
        """Send RPM + Speed step"""
        if not self.running: return
        rpm      = int(self.dc.rpm)
        speed    = int(self.dc.speed)
        phase_map = {
            'IDLE': 0, 'ACCELERATING': 1, 'CITY': 2, 'HIGHWAY_ACCEL': 3,
            'HIGHWAY': 4, 'HIGHWAY_DECEL': 5, 'DECELERATING': 6, 'STOPPED': 7
        }
        phase_byte = phase_map.get(self.dc.phase, 0)

        msg = can.Message(
            arbitration_id=0x100,
            data=codec.encode(0x100, {
                'Engine_RPM': rpm,
                'Vehicle_Speed': speed,
                'Drive_Phase': phase_byte
            }),
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

    def send_temp_throttle_step(self):
        """Send Temp + Throttle step"""
        if not self.running: return
        temp     = int(self.dc.engine_temp)
        throttle = int(self.dc.throttle)

        msg = can.Message(
            arbitration_id=0x101,
            data=codec.encode(0x101, {
                'Engine_Temp': temp,
                'Throttle_Pos': throttle
            }),
            is_extended_id=False
        )
        try:
            self.bus.send(msg)
        except Exception:
            pass

        print(f"[ENGINE ECU] Temp:{temp} C "
              f"Throttle:{throttle}%")

    def on_message_received(self, msg):
        pass

    def start(self):
        print("[ENGINE ECU] Starting (10ms CAN cycle)...")
        from core.scheduler import scheduler
        scheduler.register('ENGINE_RPM', 10, self.send_rpm_speed_step)
        scheduler.register('ENGINE_TEMP', 20, self.send_temp_throttle_step)

    def stop(self):
        self.running = False
        print("[ENGINE ECU] Stopped.")