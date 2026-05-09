import threading
import time
import traceback

from can_bus.can_network     import CANNetwork
from lin_bus.tpms_ecu        import TPMSECU
from lin_bus.window_seat_ecu import WindowSeatECU
from gateway.secure_gateway  import SecureGatewayECU
from ethernet.adas_ecu       import ADASECU
from vehicle.ignition        import IgnitionSystem
from vehicle.fault_manager   import FaultManager
from vehicle.fault_injector  import init_injector
from security.attack_simulator import AttackSimulator
from can_bus.can_logger      import init_logger

import app as app_module

class SimulationManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.is_running = False
        self.is_initializing = False

        self.lin_bus = {}
        self.ethernet_bus = {}

        self.can_network = None
        self.tpms_ecu = None
        self.window_seat_ecu = None
        self.gateway = None
        self.adas = None
        self.fault_mgr = None
        self.injector = None
        self.attacker = None
        self.ignition = None

    def start_all(self):
        with self.lock:
            if self.is_running or self.is_initializing:
                return False
            self.is_initializing = True

        try:
            print("[SIM MANAGER] Starting all components...")
            self.lin_bus.clear()
            self.ethernet_bus.clear()

            self.can_network = CANNetwork(self.ethernet_bus)
            self.can_network.start()

            self.tpms_ecu = TPMSECU(self.lin_bus)
            self.window_seat_ecu = WindowSeatECU(self.lin_bus)
            self.tpms_ecu.start()
            self.window_seat_ecu.start()

            self.gateway = SecureGatewayECU(
                can_bus=self.can_network.get_bus(),
                lin_bus=self.lin_bus,
                ethernet_bus=self.ethernet_bus
            )
            self.can_network.notifier.add_listener(self.gateway)
            self.gateway.start()

            self.adas = ADASECU(self.ethernet_bus)
            self.adas.start()

            self.fault_mgr = FaultManager(self.ethernet_bus)
            self.fault_mgr.start()

            self.injector = init_injector(self.ethernet_bus)

            init_logger(self.can_network.get_bus())

            self.attacker = AttackSimulator(self.can_network.get_bus(), self.ethernet_bus)
            self.attacker.start()

            self.ignition = IgnitionSystem(self.ethernet_bus)
            self.ignition.start()

            app_module.set_ethernet_bus(self.ethernet_bus)
            app_module.set_can_network(self.can_network)

            with self.lock:
                self.is_running = True
                self.is_initializing = False
                app_module.SIMULATION_STATE = "RUNNING"
            print("[SIM MANAGER] All components started.")
            return True

        except Exception as e:
            print(f"[SIM MANAGER] CRASH DURING STARTUP: {e}")
            traceback.print_exc()
            self._force_stop()
            with self.lock:
                self.is_initializing = False
                app_module.SIMULATION_STATE = "OFFLINE"
            # Emit error to frontend
            app_module.socketio.emit('simulation_error', {'msg': str(e)})
            return False

    def stop_all(self):
        with self.lock:
            if not self.is_running and not self.is_initializing:
                return False
        
        print("[SIM MANAGER] Stopping all components...")
        self._force_stop()

        with self.lock:
            self.is_running = False
            self.is_initializing = False
            app_module.SIMULATION_STATE = "OFFLINE"
        
        print("[SIM MANAGER] All components stopped.")
        return True

    def _force_stop(self):
        # Attempt to stop everything cleanly
        try:
            if self.ignition: self.ignition.stop()
            if self.fault_mgr: self.fault_mgr.stop()
            if self.injector: self.injector.stop()
            if self.attacker: self.attacker.stop()
            if self.adas: self.adas.stop()
            if self.gateway: self.gateway.stop()
            if self.tpms_ecu: self.tpms_ecu.stop()
            if self.window_seat_ecu: self.window_seat_ecu.stop()
            if self.can_network: self.can_network.stop()
        except Exception as e:
            print(f"[SIM MANAGER] Error during shutdown: {e}")

        # Clear references to allow garbage collection
        self.can_network = None
        self.tpms_ecu = None
        self.window_seat_ecu = None
        self.gateway = None
        self.adas = None
        self.fault_mgr = None
        self.injector = None
        self.attacker = None
        self.ignition = None

sim_manager_instance = SimulationManager()

def start_simulation_async():
    # Start simulation in a background thread to unblock the API request
    def run():
        sim_manager_instance.start_all()
    threading.Thread(target=run, daemon=True).start()

def stop_simulation_async():
    def run():
        sim_manager_instance.stop_all()
    threading.Thread(target=run, daemon=True).start()
