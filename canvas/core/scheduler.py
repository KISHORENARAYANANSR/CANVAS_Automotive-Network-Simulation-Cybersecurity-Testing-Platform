import time
import threading

class DeterministicScheduler:
    def __init__(self):
        self.tasks = []
        self.running = False
        self.frozen = False
        self.jitter_stats = {
            'avg_ms': 0.0,
            'max_ms': 0.0,
            'count': 0
        }

    def register(self, name, interval_ms, func):
        self.tasks.append({
            'name': name,
            'interval': interval_ms / 1000.0,
            'func': func,
            'next_run': 0.0
        })

    def get_jitter_stats(self):
        return {
            'avg': self.jitter_stats['avg_ms'],
            'max': self.jitter_stats['max_ms']
        }

    def toggle_freeze(self):
        self.frozen = not self.frozen
        print(f"[SCHEDULER] Simulation {'FROZEN' if self.frozen else 'RESUMED'}")
        return self.frozen

    def start(self):
        if self.running: return
        self.running = True
        self.thread = threading.Thread(target=self._loop)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        self.running = False
        
    def clear_tasks(self):
        self.tasks.clear()
        self.jitter_stats = {
            'avg_ms': 0.0,
            'max_ms': 0.0,
            'count': 0
        }

    def _loop(self):
        print("[SCHEDULER] Started deterministic single-thread execution.")
        # Align starting point
        now = time.monotonic()
        for task in self.tasks:
            task['next_run'] = now + task['interval']

        while self.running:
            now = time.monotonic()
            
            # Find the task with the earliest next_run
            next_task = min(self.tasks, key=lambda x: x['next_run'])
            
            # Precise sleep until next task
            sleep_time = next_task['next_run'] - now
            if sleep_time > 0.0005:  # Sleep if more than 0.5ms remains
                time.sleep(sleep_time - 0.0002) # Sleep slightly less to wake up early
                now = time.monotonic()

            # Busy-wait for the final fraction for sub-millisecond precision
            while time.monotonic() < next_task['next_run']:
                pass
            
            actual_start = time.monotonic()
            
            # Calculate Jitter
            jitter_ms = (actual_start - next_task['next_run']) * 1000.0
            
            # Update Global Jitter Stats
            self.jitter_stats['max_ms'] = max(self.jitter_stats['max_ms'], jitter_ms)
            self.jitter_stats['count'] += 1
            # Rolling average
            self.jitter_stats['avg_ms'] = (self.jitter_stats['avg_ms'] * 0.99) + (jitter_ms * 0.01)
                
            # Execute task (ONLY IF NOT FROZEN)
            if not self.frozen:
                try:
                    next_task['func']()
                except Exception as e:
                    print(f"[SCHEDULER] Error in {next_task['name']}: {e}")
                
            # Schedule next run deterministically
            next_task['next_run'] += next_task['interval']
            
            # Catch up if fell significantly behind (> 100ms)
            if (time.monotonic() - next_task['next_run']) > 0.1:
                next_task['next_run'] = time.monotonic() + next_task['interval']
                
scheduler = DeterministicScheduler()
