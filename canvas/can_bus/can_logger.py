# CANVAS Project
# Module: CAN Bus
# File: can_logger.py
# Professional CAN bus traffic analyzer + logger

import can
import time
import threading
import csv
import os
from collections import defaultdict, deque
from vehicle.dtc_manager import dtc_manager

# ── CAN ID to ECU mapping ─────────────────────────────────────
CAN_ID_MAP = {
    0x100 : 'ENGINE',
    0x101 : 'ENGINE',
    0x200 : 'ABS',
    0x201 : 'ABS',
    0x300 : 'AIRBAG',
    0x400 : 'TRANSMISSION',
    0x500 : 'BMS',
    0x501 : 'BMS',
    0x600 : 'MOTOR',
    0x700 : 'TPMS',
    0x800 : 'HYBRID_CTRL',
    0x900 : 'REGEN_BRAKE',
    0xA00 : 'ADAS',
}

class CANLogger:
    def __init__(self, bus, log_dir='logs'):
        self.bus         = bus
        self.log_dir     = log_dir
        self.running     = True

        # ── Statistics ────────────────────────────────────────
        self.total_msgs       = 0
        self.total_errors     = 0
        self.msg_counts       = defaultdict(int)
        self.ecu_msg_counts   = defaultdict(int)
        self.ecu_byte_counts  = defaultdict(int)
        self.bus_load_history = deque(maxlen=60)
        self.msg_rate_history = deque(maxlen=60)

        # Per-second counters
        self._second_count    = 0
        self._second_bytes    = 0
        self._last_second     = time.time()

        # ── Log file setup ────────────────────────────────────
        os.makedirs(log_dir, exist_ok=True)
        self.log_file = os.path.join(
            log_dir,
            f"can_traffic_{time.strftime('%Y%m%d_%H%M%S')}.csv"
        )

        # Initialize CSV
        with open(self.log_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Timestamp', 'CAN_ID_Hex', 'CAN_ID_Dec',
                'ECU', 'DLC', 'Data_Hex',
                'Data_Bytes', 'Bus_Load_%'
            ])

        print(f"[CAN LOGGER] Log file: {self.log_file}")

        # ── Shared stats for dashboard ─────────────────────────
        self.stats = {
            'total_msgs'      : 0,
            'total_errors'    : 0,
            'msgs_per_sec'    : 0,
            'bus_load_pct'    : 0.0,
            'ecu_counts'      : {},
            'top_ids'         : [],
            'bus_load_history': [],
            'msg_rate_history': [],
            'log_file'        : self.log_file,
        }

        self.lock = threading.Lock()

    def _calc_bus_load(self, bytes_per_sec):
        """
        Calculate CAN bus load %.
        CAN 500kbps = 500,000 bits/sec
        Each message ~130 bits (header+data+stuffing)
        Max ~3846 msgs/sec at 500kbps
        """
        # Each byte = 8 bits + overhead (~30 bits per frame)
        bits_per_sec = bytes_per_sec * 8 + self._second_count * 30
        load         = (bits_per_sec / 500_000) * 100
        return min(100.0, round(load, 2))

    def _log_message(self, msg):
        """Log a single CAN message to CSV"""
        arb_id   = msg.arbitration_id
        ecu_name = CAN_ID_MAP.get(arb_id, 'UNKNOWN')
        data_hex = ' '.join(f'{b:02X}' for b in msg.data)
        bus_load = self.stats['bus_load_pct']

        with open(self.log_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                time.strftime('%H:%M:%S.') +
                f"{int((time.time() % 1) * 1000):03d}",
                f"0x{arb_id:03X}",
                arb_id,
                ecu_name,
                len(msg.data),
                data_hex,
                list(msg.data),
                bus_load,
            ])

    def _listen(self):
        """Listen to CAN bus + record all messages"""
        while self.running:
            try:
                msg = self.bus.recv(timeout=0.1)
                if msg is None:
                    continue

                arb_id   = msg.arbitration_id
                ecu_name = CAN_ID_MAP.get(arb_id, 'UNKNOWN')

                with self.lock:
                    self.total_msgs          += 1
                    self.msg_counts[arb_id]  += 1
                    self.ecu_msg_counts[ecu_name] += 1
                    self.ecu_byte_counts[ecu_name] += len(msg.data)
                    self._second_count       += 1
                    self._second_bytes       += len(msg.data)

                # Log to CSV (every 10th message to save space)
                if self.total_msgs % 10 == 0:
                    self._log_message(msg)

            except Exception as e:
                with self.lock:
                    self.total_errors += 1
                if self.total_errors > 50:
                    dtc_manager.set_fault('U0001')

    def _update_stats(self):
        """Update stats every second"""
        while self.running:
            time.sleep(1.0)
            with self.lock:
                now          = time.time()
                elapsed      = now - self._last_second
                msgs_sec     = self._second_count / max(elapsed, 0.1)
                bus_load     = self._calc_bus_load(
                    self._second_bytes)

                self.bus_load_history.append(bus_load)
                self.msg_rate_history.append(round(msgs_sec, 1))

                # Top 5 most active CAN IDs
                top_ids = sorted(
                    self.msg_counts.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5]

                # Update shared stats
                self.stats.update({
                    'total_msgs'      : self.total_msgs,
                    'total_errors'    : self.total_errors,
                    'msgs_per_sec'    : round(msgs_sec, 1),
                    'bus_load_pct'    : bus_load,
                    'ecu_counts'      : dict(self.ecu_msg_counts),
                    'top_ids'         : [
                        {
                            'id'    : f"0x{k:03X}",
                            'ecu'   : CAN_ID_MAP.get(k, '?'),
                            'count' : v
                        }
                        for k, v in top_ids
                    ],
                    'bus_load_history': list(self.bus_load_history),
                    'msg_rate_history': list(self.msg_rate_history),
                })

                print(f"[CAN LOGGER] "
                      f"Msgs/sec:{msgs_sec:.0f} "
                      f"Bus Load:{bus_load:.1f}% "
                      f"Total:{self.total_msgs} "
                      f"Errors:{self.total_errors}")

                # Reset per-second counters
                self._second_count = 0
                self._second_bytes = 0
                self._last_second  = now

    def get_stats(self):
        """Return current stats for dashboard"""
        with self.lock:
            return self.stats.copy()

    def start(self):
        print("[CAN LOGGER] Starting traffic analyzer...")
        threads = [
            threading.Thread(
                target=self._listen, daemon=True),
            threading.Thread(
                target=self._update_stats, daemon=True),
        ]
        for t in threads:
            t.start()
        print(f"[CAN LOGGER] ✅ Logging to {self.log_file}")

    def stop(self):
        self.running = False
        print(f"[CAN LOGGER] Stopped. "
              f"Total messages logged: {self.total_msgs}")


# ── Global logger instance ────────────────────────────────────
_can_logger = None

def init_logger(bus):
    global _can_logger
    _can_logger = CANLogger(bus)
    _can_logger.start()
    return _can_logger

def get_logger():
    return _can_logger