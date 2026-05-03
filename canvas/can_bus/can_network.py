# CANVAS Project
# Module: CAN Bus
# File: can_network.py
# CAN network with arbitration + timing + logger

import can
from can_bus.drive_cycle        import DriveCycle
from can_bus.can_timing         import can_timing_monitor
from can_bus.can_arbitration    import init_arbitration
from can_bus.can_logger         import init_logger
from can_bus.engine_ecu         import EngineECU
from can_bus.abs_ecu            import ABSECU
from can_bus.airbag_ecu         import AirbagECU
from can_bus.transmission_ecu   import TransmissionECU
from can_bus.bms_ecu            import BMSECU
from can_bus.motor_ecu          import MotorECU
from can_bus.hybrid_control_ecu import HybridControlECU
from can_bus.regen_brake_ecu    import RegenBrakeECU

class CANNetwork:
    def __init__(self, ethernet_bus=None):
        self.bus = can.Bus(
            interface='virtual',
            channel='CANVAS_CAN',
            receive_own_messages=True
        )
        self.drive_cycle = DriveCycle(ethernet_bus)
        print("[CAN NETWORK] Virtual CAN Bus created "
              "-> Channel: CANVAS_CAN")

    def start(self):
        # Start timing monitor
        can_timing_monitor.start()

        # Start arbitration engine
        self.arbitration = init_arbitration(self.bus)

        # Start CAN logger
        self.logger = init_logger(self.bus)

        # Start drive cycle
        self.drive_cycle.start()

        # Instantiate all ECUs
        self.engine_ecu       = EngineECU(
            self.bus, self.drive_cycle)
        self.abs_ecu          = ABSECU(
            self.bus, self.drive_cycle)
        self.airbag_ecu       = AirbagECU(self.bus)
        self.transmission_ecu = TransmissionECU(
            self.bus, self.drive_cycle)
        self.bms_ecu          = BMSECU(
            self.bus, self.drive_cycle)
        self.motor_ecu        = MotorECU(self.bus)
        self.hybrid_ctrl_ecu  = HybridControlECU(self.bus)
        self.regen_brake_ecu  = RegenBrakeECU(self.bus)

        # Start all ECUs
        self.engine_ecu.start()
        self.abs_ecu.start()
        self.airbag_ecu.start()
        self.transmission_ecu.start()
        self.bms_ecu.start()
        self.motor_ecu.start()
        self.hybrid_ctrl_ecu.start()
        self.regen_brake_ecu.start()

        # Start Notifier for RX
        self.notifier = can.Notifier(self.bus, [
            self.engine_ecu, self.abs_ecu, self.airbag_ecu,
            self.transmission_ecu, self.bms_ecu, self.motor_ecu,
            self.hybrid_ctrl_ecu, self.regen_brake_ecu
        ])

        # Start Deterministic Scheduler
        from core.scheduler import scheduler
        scheduler.start()

        print("[CAN NETWORK] All 8 ECUs online [OK]")
        print("[CAN NETWORK] Logger: ACTIVE")
        print("[CAN NETWORK] Arbitration: ACTIVE")
        print("-" * 60)

    def stop(self):
        can_timing_monitor.stop()
        self.drive_cycle.stop()
        self.logger.stop()
        self.notifier.stop()
        from core.scheduler import scheduler
        scheduler.stop()
        self.engine_ecu.stop()
        self.abs_ecu.stop()
        self.airbag_ecu.stop()
        self.transmission_ecu.stop()
        self.bms_ecu.stop()
        self.motor_ecu.stop()
        self.hybrid_ctrl_ecu.stop()
        self.regen_brake_ecu.stop()
        self.bus.shutdown()
        print("[CAN NETWORK] All ECUs stopped.")

    def get_bus(self):
        return can.Bus(
            interface='virtual',
            channel='CANVAS_CAN',
            receive_own_messages=True
        )

    def get_logger(self):
        return self.logger