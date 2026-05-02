# CANVAS Project
# File: app.py

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import threading
import time
import os

app      = Flask(__name__)
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='threading',
    logger=False,
    engineio_logger=False
)

_ethernet_bus = {}
_can_network  = None

def set_ethernet_bus(bus):
    global _ethernet_bus
    _ethernet_bus = bus

def set_can_network(network):
    global _can_network
    _can_network = network

def broadcast_loop():
    while True:
        try:
            from vehicle.dtc_manager    import dtc_manager
            from can_bus.can_logger     import get_logger
            from vehicle.fault_injector import get_injector

            state     = _ethernet_bus.get('vehicle_state', {})
            decisions = _ethernet_bus.get('adas_decisions', {})
            dtcs      = dtc_manager.get_active_dtcs()
            logger    = get_logger()
            injector  = get_injector()
            log_stats = logger.get_stats() if logger else {}

            # Merge ignition + ecu_status into state
            state['ignition_state'] = _ethernet_bus.get(
                'ignition_state', 'OFF')
            state['ecu_status']     = _ethernet_bus.get(
                'ecu_status', {})

            if state:
                with app.app_context():
                    socketio.emit('vehicle_update', {
                        'state'          : state,
                        'decisions'      : decisions,
                        'dtcs'           : dtcs,
                        'critical'       : dtc_manager.get_critical_count(),
                        'warnings'       : dtc_manager.get_warning_count(),
                        'log_stats'      : log_stats,
                        'injection_log'  : _ethernet_bus.get(
                            'injection_log', []),
                        'active_scenario': _ethernet_bus.get(
                            'active_scenario', None),
                    })
        except Exception as e:
            print(f"[SERVER] Broadcast error: {e}")
        time.sleep(0.1)

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/api/inject_fault', methods=['POST'])
def inject_fault():
    try:
        data = request.get_json()
        code = data.get('code', '')
        from vehicle.dtc_manager import dtc_manager
        dtc_manager.set_fault(code)
        return jsonify({'status': 'ok', 'code': code})
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)})

@app.route('/api/clear_faults', methods=['POST'])
def clear_faults():
    try:
        from vehicle.dtc_manager    import dtc_manager
        from vehicle.fault_injector import get_injector
        dtc_manager.clear_all()
        inj = get_injector()
        if inj:
            inj.reset_all()
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)})

@app.route('/api/inject_scenario', methods=['POST'])
def inject_scenario():
    try:
        data     = request.get_json()
        scenario = data.get('scenario', '')
        from vehicle.fault_injector import get_injector
        inj = get_injector()
        if inj:
            inj.inject_scenario(scenario)
        return jsonify({'status': 'ok', 'scenario': scenario})
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)})

@app.route('/api/reset_scenario', methods=['POST'])
def reset_scenario():
    try:
        from vehicle.fault_injector import get_injector
        inj = get_injector()
        if inj:
            inj.reset_all()
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)})

@app.route('/api/generate_report', methods=['POST'])
def generate_report():
    try:
        from reports.report_generator import ReportGenerator
        from can_bus.can_logger       import get_logger
        from vehicle.dtc_manager      import dtc_manager
        gen    = ReportGenerator(
            _ethernet_bus, get_logger(), dtc_manager)
        path   = gen.generate()
        # Get just filename for display
        fname  = os.path.basename(path)
        return jsonify({
            'status' : 'ok',
            'path'   : path,
            'fname'  : fname
        })
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)})

@app.route('/api/scenarios', methods=['GET'])
def get_scenarios():
    try:
        from vehicle.fault_injector import get_injector
        inj = get_injector()
        return jsonify(inj.get_scenarios() if inj else {})
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)})
@app.route('/api/download_report/<fname>')
def download_report(fname):
    from flask import send_from_directory
    return send_from_directory('reports', fname)

@app.route('/report/view')
def view_report():
    """Serve the latest report for browser viewing + print to PDF"""
    try:
        import glob
        files = glob.glob('reports/CANVAS_Report_*.html')
        if not files:
            return "No report generated yet.", 404
        latest = max(files, key=os.path.getctime)
        with open(latest, 'r', encoding='utf-8') as f:
            content = f.read()
        # Inject print button at top
        print_btn = '''
        <div style="position:fixed;top:16px;right:16px;z-index:9999">
          <button onclick="window.print()"
            style="background:#2563eb;color:#fff;border:none;
            padding:10px 20px;border-radius:8px;font-size:14px;
            font-weight:700;cursor:pointer;
            box-shadow:0 4px 12px rgba(37,99,235,0.4)">
            🖨️ Save as PDF
          </button>
          <style>
            @media print {
              button { display: none !important; }
              body { background: white !important; }
            }
          </style>
        </div>
        '''
        content = content.replace('<body>', '<body>' + print_btn)
        return content
    except Exception as e:
        return f"Error: {e}", 500

def start_server(bus, network=None):
    set_ethernet_bus(bus)
    if network:
        set_can_network(network)
    t = threading.Thread(
        target=broadcast_loop, daemon=True)
    t.start()
    print("[SERVER] Flask server starting...")
    socketio.run(
        app,
        host='0.0.0.0',
        port=5000,
        allow_unsafe_werkzeug=True
    )

