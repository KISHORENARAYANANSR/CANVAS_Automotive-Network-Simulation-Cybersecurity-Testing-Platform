# CANVAS Project
# Module: CAN Bus
# File: can_arbitration.py
# Real CAN bus arbitration + collision detection

import time
import threading
import queue
from vehicle.dtc_manager import dtc_manager

# Precise CAN Bit Calculation (Standard 11-bit ID)
# SOF(1) + ID(11) + RTR(1) + IDE(1) + r0(1) + DLC(4) + Data(8*DLC) + CRC(15) + DEL(1) + ACK(1) + DEL(1) + EOF(7) = 44 + 8*DLC
def calc_msg_bits(dlc):
    base_bits = 44 + (8 * dlc)
    stuff_bits = (34 + 8 * dlc - 1) // 4
    return base_bits + stuff_bits

# -- CAN Message Priority Table --------------------------------
# Lower arbitration ID = Higher priority
# This matches real CAN bus standard (ISO 11898)
ARBITRATION_PRIORITY = {
    0x100 : 1,    # Engine RPM/Speed       HIGHEST
    0x101 : 2,    # Engine Temp/Throttle
    0x200 : 3,    # ABS Wheel Speeds
    0x201 : 4,    # ABS Brake Pressure
    0x300 : 5,    # Airbag Status
    0x400 : 6,    # Transmission
    0x500 : 7,    # BMS Battery
    0x501 : 8,    # BMS Temperature
    0x600 : 9,    # Motor Status
    0x700 : 10,   # TPMS
    0x800 : 11,   # Hybrid Control
    0x900 : 12,   # Regen Brake
    0xA00 : 13,   # ADAS                LOWEST
}

class CANArbitration:
    """
    Simulates CAN bus arbitration.
    Multiple ECUs push messages to a shared queue.
    Arbitration picks highest priority message first.
    """

    def __init__(self, real_bus):
        self.real_bus        = real_bus
        self.running         = True
        self.lock            = threading.Lock()

        # Priority queue   lower number = processed first
        self.msg_queue       = queue.PriorityQueue()

        # Stats
        self.total_sent      = 0
        self.total_collisions = 0
        self.total_retries   = 0
        self.msg_counts      = {}
        self.total_bits_sent = 0
        
        # TEC / REC Counters
        self.tec = 0
        self.rec = 0
        self.bus_state = 'ERROR_ACTIVE' # ERROR_ACTIVE, ERROR_PASSIVE, BUS_OFF
        
        self.last_load_time  = time.perf_counter()
        self.bus_load_percent = 0.0

    def submit(self, msg, ecu_name='UNKNOWN'):
        """
        ECU submits a message for arbitration.
        Instead of sending directly to bus,
        message goes through arbitration first.
        """
        arb_id   = msg.arbitration_id
        priority = ARBITRATION_PRIORITY.get(arb_id, 99)

        # Push to priority queue
        # Tuple: (priority, timestamp, msg, ecu_name)
        self.msg_queue.put((
            priority,
            time.perf_counter(),
            msg,
            ecu_name
        ))

    def _process_queue(self):
        """
        Main arbitration loop  
        processes messages by priority
        """
        while self.running:
            if self.bus_state == 'BUS_OFF':
                # Clear queue, bus is halted
                try:
                    while True: self.msg_queue.get_nowait()
                except queue.Empty:
                    time.sleep(0.1)
                    continue
            try:
                # Get highest priority message
                priority, ts, msg, ecu = (
                    self.msg_queue.get(timeout=0.01))

                # Check for collision
                # (message waited too long = collision)
                wait_time = time.perf_counter() - ts
                if wait_time > 0.050:
                    # Message waited > 50ms = collision
                    self.total_collisions += 1
                    self.tec = min(260, self.tec + 8)
                    self._update_bus_state()

                    # Retry once (real CAN behavior)
                    if wait_time < 0.100 and self.bus_state != 'BUS_OFF':
                        self.total_retries += 1
                        self.msg_queue.put((
                            priority,
                            time.perf_counter(),
                            msg,
                            ecu
                        ))
                        continue
                    else:
                        # Drop message   bus overload
                        print(f"[ARBITRATION] [WARN]  Message dropped   Bus overload/Bus-Off [0x{msg.arbitration_id:X}]")
                        if self.total_collisions > 100:
                            dtc_manager.set_fault('U0001')
                        continue

                # Send to real CAN bus
                try:
                    self.real_bus._original_send(msg)
                    self.total_sent += 1
                    self.total_bits_sent += calc_msg_bits(msg.dlc)
                    
                    # Successful Tx decreases TEC
                    if self.tec > 0:
                        self.tec -= 1
                        self._update_bus_state()

                    # Track per-ID counts
                    aid = msg.arbitration_id
                    self.msg_counts[aid] = (
                        self.msg_counts.get(aid, 0) + 1)

                except Exception as e:
                    print(f"[ARBITRATION] Send error: {e}")
                    self.tec = min(260, self.tec + 8)
                    self._update_bus_state()
                    dtc_manager.set_fault('U0001')

            except queue.Empty:
                continue

    def _update_bus_state(self):
        """Update ERROR_ACTIVE, ERROR_PASSIVE, BUS_OFF based on TEC"""
        if self.tec > 255:
            if self.bus_state != 'BUS_OFF':
                self.bus_state = 'BUS_OFF'
                dtc_manager.set_fault('U0002') # CAN Bus Off
                print("[ARBITRATION] [CRIT] CAN Bus-Off condition reached! TEC > 255")
        elif self.tec > 127:
            if self.bus_state != 'ERROR_PASSIVE':
                self.bus_state = 'ERROR_PASSIVE'
        else:
            if self.bus_state != 'ERROR_ACTIVE':
                self.bus_state = 'ERROR_ACTIVE'

    def reset(self):
        """Manual bus reset - clear error counters and return to ERROR_ACTIVE"""
        with self.lock:
            self.tec = 0
            self.rec = 0
            self.bus_state = 'ERROR_ACTIVE'
            self.total_collisions = 0
            dtc_manager.clear_all() # Clear U0002 etc.
            print("[ARBITRATION] [OK] Bus Reset - Counters cleared, Bus ONLINE.")

    def print_stats(self):
        """Print arbitration statistics and calculate load periodically"""
        while self.running:
            time.sleep(5)
            # Calculate bus load
            now = time.perf_counter()
            dt = max(now - self.last_load_time, 0.001)
            bits_per_sec = self.total_bits_sent / dt
            # 500 kbps = 500,000 bits per second
            self.bus_load_percent = min(100.0, (bits_per_sec / 500000.0) * 100.0)
            
            # Reset counters for next window
            self.total_bits_sent = 0
            self.last_load_time = now

            print("\n[ARBITRATION] -- Bus Stats --")
            print(f"  Total Sent     : {self.total_sent}")
            print(f"  Collisions     : {self.total_collisions}")
            print(f"  Retries        : {self.total_retries}")
            print(f"  TEC            : {self.tec}")
            print(f"  State          : {self.bus_state}")
            print(f"  Bus Load       : {self.bus_load_percent:.1f}%")
            print("[ARBITRATION] -----------------\n")

    def _calc_bus_load(self):
        """Return the calculated load"""
        return self.bus_load_percent

    def start(self):
        print("[ARBITRATION] CAN Bus arbitration "
              "engine starting...")
        threads = [
            threading.Thread(
                target=self._process_queue,
                daemon=True),
            threading.Thread(
                target=self.print_stats,
                daemon=True),
        ]
        for t in threads:
            t.start()
        print("[ARBITRATION] [OK] Arbitration active "
              "  Priority based message routing")

    def stop(self):
        self.running = False
        print(f"[ARBITRATION] Stopped. "
              f"Total sent: {self.total_sent} "
              f"Collisions: {self.total_collisions}")


# -- Global arbitration instance -------------------------------
# All ECUs use this instead of bus.send() directly
_arbitration = None

def init_arbitration(real_bus):
    """Initialize global arbitration with real bus"""
    global _arbitration
    _arbitration = CANArbitration(real_bus)
    
    # Monkey-patch real_bus.send to route through arbitration
    if not hasattr(real_bus, '_original_send'):
        real_bus._original_send = real_bus.send
        real_bus.send = lambda msg: _arbitration.submit(msg, 'PATCHED')
        
    _arbitration.start()
    return _arbitration

def get_arbitration():
    """Get global arbitration instance"""
    return _arbitration