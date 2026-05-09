import eventlet
eventlet.monkey_patch()

import os
import sys
import threading

# Add the canvas directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'canvas')))

from app import app, socketio, broadcast_loop
import sim_manager

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting server on port {port}...")
    
    # Start the broadcast loop immediately
    threading.Thread(target=broadcast_loop, daemon=True).start()
    
    # Initialize the app with the offline state, but don't start the simulation
    socketio.run(app, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)
