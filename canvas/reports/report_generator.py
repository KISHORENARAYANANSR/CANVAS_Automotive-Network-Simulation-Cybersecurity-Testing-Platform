# CANVAS Project
# Module: Reports
# File: report_generator.py
# AUTOSAR SWC report generator

import os
import time
from vehicle.dtc_manager import dtc_manager

class ReportGenerator:
    def __init__(self, ethernet_bus, can_logger, dtc_mgr):
        self.ethernet_bus = ethernet_bus
        self.can_logger   = can_logger
        self.dtc_mgr      = dtc_mgr
        self.report_dir   = 'reports'
        os.makedirs(self.report_dir, exist_ok=True)

    def generate(self):
      """Generate full AUTOSAR SWC report as PDF"""
      state     = self.ethernet_bus.get('vehicle_state', {})
      log_stats = self.can_logger.get_stats() \
        if self.can_logger else {}
      dtcs      = self.dtc_mgr.get_active_dtcs()
      timestamp = time.strftime('%Y%m%d_%H%M%S')

      os.makedirs(self.report_dir, exist_ok=True)

      html_file = os.path.join(
        self.report_dir,
        f'CANVAS_Report_{timestamp}.html'
      )
      pdf_file = os.path.join(
        self.report_dir,
        f'CANVAS_Report_{timestamp}.pdf'
      )

      html = self._build_html(state, log_stats, dtcs)

      # Save HTML with UTF-8
      with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html)

      print(f"[REPORT] [OK] HTML report generated: {html_file}")
      return html_file

    def _build_html(self, state, log_stats, dtcs):
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')

        # -- SWC Architecture Data -----------------------------
        swc_data = [
            {
                'name'    : 'EngineECU',
                'type'    : 'AtomicSWC',
                'bus'     : 'CAN',
                'cycle'   : '10ms',
                'priority': 'HIGHEST',
                'inputs'  : ['DriveCycle.RPM',
                             'DriveCycle.Speed',
                             'DriveCycle.Temp'],
                'outputs' : ['CAN[0x100]: RPM, Speed',
                             'CAN[0x101]: Temp, Throttle'],
                'dtcs'    : ['P0217', 'P0219'],
            },
            {
                'name'    : 'ABSECU',
                'type'    : 'AtomicSWC',
                'bus'     : 'CAN',
                'cycle'   : '10ms',
                'priority': 'HIGH',
                'inputs'  : ['DriveCycle.Speed',
                             'DriveCycle.BrakePressure'],
                'outputs' : ['CAN[0x200]: WheelSpeeds',
                             'CAN[0x201]: BrakePressure'],
                'dtcs'    : ['C0035', 'C0040',
                             'C0045', 'C0050'],
            },
            {
                'name'    : 'AirbagECU',
                'type'    : 'AtomicSWC',
                'bus'     : 'CAN',
                'cycle'   : '20ms',
                'priority': 'HIGH',
                'inputs'  : ['AccelerometerSensor',
                             'CAN[0x201]: BrakePressure'],
                'outputs' : ['CAN[0x300]: CrashStatus',
                             'CAN[0x300]: DeploymentFlag'],
                'dtcs'    : ['B0001', 'B0002', 'B0051'],
            },
            {
                'name'    : 'TransmissionECU',
                'type'    : 'AtomicSWC',
                'bus'     : 'CAN',
                'cycle'   : '20ms',
                'priority': 'MEDIUM',
                'inputs'  : ['DriveCycle.Speed',
                             'DriveCycle.RPM'],
                'outputs' : ['CAN[0x400]: Gear',
                             'CAN[0x400]: DriveMode'],
                'dtcs'    : ['P0700', 'P0715'],
            },
            {
                'name'    : 'BMSECU',
                'type'    : 'AtomicSWC',
                'bus'     : 'CAN',
                'cycle'   : '100ms',
                'priority': 'MEDIUM',
                'inputs'  : ['HVBatterySensors',
                             'DriveCycle.Phase'],
                'outputs' : ['CAN[0x500]: SOC, Voltage',
                             'CAN[0x501]: Temperature'],
                'dtcs'    : ['P0A80', 'P1A00',
                             'P1A05', 'P1A10'],
            },
            {
                'name'    : 'MotorECU',
                'type'    : 'AtomicSWC',
                'bus'     : 'CAN',
                'cycle'   : '10ms',
                'priority': 'HIGH',
                'inputs'  : ['CAN[0x500]: SOC',
                             'CAN[0x100]: Speed',
                             'CAN[0x201]: Brake'],
                'outputs' : ['CAN[0x600]: RPM, Torque',
                             'CAN[0x600]: MotorMode'],
                'dtcs'    : ['P0A00', 'P0A0F'],
            },
            {
                'name'    : 'HybridControlECU',
                'type'    : 'CompositionSWC',
                'bus'     : 'CAN',
                'cycle'   : '50ms',
                'priority': 'HIGH',
                'inputs'  : ['CAN[0x100]: Speed',
                             'CAN[0x500]: SOC',
                             'CAN[0x600]: MotorMode',
                             'CAN[0x201]: Brake'],
                'outputs' : ['CAN[0x800]: HybridMode',
                             'CAN[0x800]: PowerSplit'],
                'dtcs'    : [],
            },
            {
                'name'    : 'RegenBrakeECU',
                'type'    : 'AtomicSWC',
                'bus'     : 'CAN',
                'cycle'   : '20ms',
                'priority': 'MEDIUM',
                'inputs'  : ['CAN[0x201]: Brake',
                             'CAN[0x600]: RegenActive',
                             'CAN[0x100]: Speed'],
                'outputs' : ['CAN[0x900]: RegenPower',
                             'CAN[0x900]: EnergyRecovered'],
                'dtcs'    : [],
            },
            {
                'name'    : 'TPMSECU',
                'type'    : 'AtomicSWC',
                'bus'     : 'LIN',
                'cycle'   : '1000ms',
                'priority': 'LOW',
                'inputs'  : ['TyrePressureSensors (x4)',
                             'TyreTemperatureSensors (x4)'],
                'outputs' : ['LIN[0x10]: Pressures',
                             'LIN[0x10]: Temperatures'],
                'dtcs'    : ['C0750', 'C0775'],
            },
            {
                'name'    : 'WindowSeatECU',
                'type'    : 'AtomicSWC',
                'bus'     : 'LIN',
                'cycle'   : '1000ms',
                'priority': 'LOW',
                'inputs'  : ['WindowSwitches',
                             'SeatPositionSensors',
                             'RainSensor'],
                'outputs' : ['LIN[0x20]: WindowPositions',
                             'LIN[0x20]: SeatPositions'],
                'dtcs'    : [],
            },
            {
                'name'    : 'GatewayECU',
                'type'    : 'CompositionSWC',
                'bus'     : 'CAN+LIN+Ethernet',
                'cycle'   : '100ms',
                'priority': 'HIGH',
                'inputs'  : ['All CAN Messages',
                             'All LIN Frames'],
                'outputs' : ['Ethernet: VehicleState',
                             'Ethernet: FaultSummary'],
                'dtcs'    : ['U0001', 'U0100', 'U0140'],
            },
            {
                'name'    : 'ADASECU',
                'type'    : 'CompositionSWC',
                'bus'     : 'Ethernet',
                'cycle'   : '100ms',
                'priority': 'HIGHEST',
                'inputs'  : ['Ethernet: VehicleState'],
                'outputs' : ['Ethernet: ADASDecisions',
                             'Dashboard: Warnings'],
                'dtcs'    : [],
            },
        ]

        # -- Build SWC rows ------------------------------------
        swc_rows = ''
        for swc in swc_data:
            bus_color = {
                'CAN'             : '#00b4ff',
                'LIN'             : '#00cc77',
                'Ethernet'        : '#ffcc00',
                'CAN+LIN+Ethernet': '#ff9900',
            }.get(swc['bus'], '#4a6a8a')

            inputs_html  = ''.join(
                f'<div class="io-item in">{i}</div>'
                for i in swc['inputs'])
            outputs_html = ''.join(
                f'<div class="io-item out">{o}</div>'
                for o in swc['outputs'])
            dtcs_html    = ''.join(
                f'<span class="dtc-tag">{d}</span>'
                for d in swc['dtcs']) or \
                '<span style="color:#3a6a9c">None</span>'

            swc_rows += f'''
            <tr>
                <td><strong style="color:#eaf4ff">
                    {swc["name"]}</strong>
                    <div style="font-size:10px;
                    color:#3a6a9c">{swc["type"]}</div>
                </td>
                <td><span class="bus-badge"
                    style="border-color:{bus_color};
                    color:{bus_color}">
                    {swc["bus"]}</span>
                </td>
                <td style="color:#ffcc00;
                    font-family:monospace">
                    {swc["cycle"]}
                </td>
                <td>{inputs_html}</td>
                <td>{outputs_html}</td>
                <td>{dtcs_html}</td>
            </tr>'''

        # -- DTC rows ------------------------------------------
        if dtcs:
            dtc_rows = ''
            for d in dtcs:
                sev_color = {
                    'CRITICAL': '#ff2244',
                    'WARNING' : '#ffcc00',
                    'INFO'    : '#00b4ff',
                }.get(d['severity'], '#4a6a8a')
                dtc_rows += f'''
                <tr>
                    <td style="color:{sev_color};
                        font-family:monospace;
                        font-weight:700">
                        {d["code"]}
                    </td>
                    <td style="color:#eaf4ff">
                        {d["desc"]}
                    </td>
                    <td><span class="bus-badge"
                        style="border-color:{sev_color};
                        color:{sev_color}">
                        {d["severity"]}
                        </span>
                    </td>
                    <td style="color:#4a6a8a">
                        {d["system"]}
                    </td>
                    <td style="color:#3a6a9c;font-size:11px">
                        {d["action"]}
                    </td>
                    <td style="color:#4a6a8a;
                        font-family:monospace">
                        {d["timestamp"]}
                    </td>
                </tr>'''
        else:
            dtc_rows = '''
            <tr><td colspan="6"
                style="text-align:center;
                color:#3a6a9c;padding:20px">
                [DONE] No active faults
            </td></tr>'''

        # -- ECU stats rows ------------------------------------
        ecu_counts = log_stats.get('ecu_counts', {})
        total_msgs = max(1, log_stats.get('total_msgs', 1))
        ecu_rows   = ''
        for ecu, count in sorted(
                ecu_counts.items(),
                key=lambda x: x[1],
                reverse=True):
            pct      = (count / total_msgs) * 100
            bar_w    = min(100, pct * 2)
            ecu_rows += f'''
            <tr>
                <td style="color:#eaf4ff;
                    font-family:monospace">
                    {ecu}
                </td>
                <td style="color:#00b4ff;
                    font-family:monospace">
                    {count:,}
                </td>
                <td>
                    <div style="background:#0d2040;
                        border-radius:3px;
                        height:6px;width:150px">
                        <div style="background:
                            linear-gradient(90deg,
                            #00b4ff,#00eeff);
                            width:{bar_w}%;
                            height:100%;
                            border-radius:3px">
                        </div>
                    </div>
                </td>
                <td style="color:#4a6a8a">
                    {pct:.1f}%
                </td>
            </tr>'''

        # -- Top CAN IDs ---------------------------------------
        top_ids      = log_stats.get('top_ids', [])
        top_ids_rows = ''
        for item in top_ids:
            top_ids_rows += f'''
            <tr>
                <td style="color:#00eeff;
                    font-family:monospace">
                    {item["id"]}
                </td>
                <td style="color:#eaf4ff">
                    {item["ecu"]}
                </td>
                <td style="color:#00b4ff;
                    font-family:monospace">
                    {item["count"]:,}
                </td>
            </tr>'''

        return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>CANVAS   AUTOSAR SWC Report</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;600;700&family=Orbitron:wght@400;700&display=swap');
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    background:#020818; color:#eaf4ff;
    font-family:'Rajdhani',sans-serif;
    padding:30px; line-height:1.5;
  }}
  .header {{
    border-bottom:2px solid #0d2040;
    padding-bottom:20px; margin-bottom:30px;
    display:flex; justify-content:space-between;
    align-items:flex-end;
  }}
  .title {{
    font-family:'Orbitron',monospace;
    font-size:24px; font-weight:700;
    color:#00eeff; letter-spacing:4px;
  }}
  .subtitle {{
    font-size:11px; color:#3a6a9c;
    letter-spacing:3px; margin-top:4px;
  }}
  .meta {{
    text-align:right; font-size:11px;
    color:#4a6a8a; font-family:monospace;
  }}
  .section {{
    margin-bottom:20px;
    background:linear-gradient(135deg,
      rgba(10,22,40,0.97),rgba(7,14,26,0.97));
    border:1px solid #0d2040;
    border-radius:10px; overflow:hidden;
    page-break-inside: avoid;
  }}
  .section-header {{
    background:rgba(0,180,255,0.05);
    padding:12px 20px;
    border-bottom:1px solid #0d2040;
    font-family:'Orbitron',monospace;
    font-size:10px; letter-spacing:3px;
    color:#00b4ff;
  }}
  .section-body {{ padding:20px; }}
  table {{
    width:100%; border-collapse:collapse;
    font-size:12px;
  }}
  th {{
    text-align:left; padding:8px 12px;
    background:rgba(0,180,255,0.05);
    color:#3a6a9c; font-family:monospace;
    font-size:10px; letter-spacing:2px;
    border-bottom:1px solid #0d2040;
  }}
  td {{
    padding:8px 12px;
    border-bottom:1px solid rgba(13,32,64,0.5);
    vertical-align:top;
  }}
  tr:hover td {{
    background:rgba(0,180,255,0.03);
  }}
  .bus-badge {{
    padding:2px 8px; border-radius:10px;
    border:1px solid; font-size:10px;
    font-family:monospace; letter-spacing:1px;
  }}
  .io-item {{
    font-size:10px; font-family:monospace;
    padding:2px 0; color:#4a6a8a;
  }}
  .io-item.in::before  {{ content:'  '; color:#00cc77; }}
  .io-item.out::before {{ content:'-> '; color:#00b4ff; }}
  .dtc-tag {{
    display:inline-block; margin:2px;
    padding:1px 6px; border-radius:4px;
    background:rgba(255,34,68,0.1);
    border:1px solid rgba(255,34,68,0.3);
    color:#ff2244; font-size:10px;
    font-family:monospace;
  }}
  .stat-grid {{
    display:grid;
    grid-template-columns:repeat(4,1fr);
    gap:12px; margin-bottom:20px;
  }}
  .stat-card {{
    background:rgba(13,32,64,0.4);
    border:1px solid #0d2040;
    border-radius:8px; padding:12px;
    text-align:center;
  }}
  .stat-val {{
    font-family:'Orbitron',monospace;
    font-size:22px; font-weight:700;
    color:#00eeff;
  }}
  .stat-lbl {{
    font-size:9px; color:#3a6a9c;
    letter-spacing:2px; margin-top:4px;
  }}
  .footer {{
    text-align:center; margin-top:30px;
    padding-top:20px;
    border-top:1px solid #0d2040;
    color:#3a6a9c; font-size:11px;
    font-family:monospace; letter-spacing:2px;
  }}
</style>
</head>
<body>

<div class="header">
  <div>
    <div class="title">CANVAS</div>
    <div class="subtitle">
      AUTOSAR SOFTWARE COMPONENT ARCHITECTURE REPORT
    </div>
  </div>
  <div class="meta">
    Generated: {timestamp}<br>
    Vehicle: Hybrid Car Simulation<br>
    Networks: CAN   LIN   Ethernet (DoIP)<br>
    Total ECUs: 12
  </div>
</div>

<!-- -- Summary Stats -- -->
<div class="section">
  <div class="section-header">
    SYSTEM SUMMARY
  </div>
  <div class="section-body">
    <div class="stat-grid">
      <div class="stat-card">
        <div class="stat-val">
          {log_stats.get("total_msgs", 0):,}
        </div>
        <div class="stat-lbl">TOTAL CAN MSGS</div>
      </div>
      <div class="stat-card">
        <div class="stat-val"
             style="color:{
               '#ff2244' if log_stats.get(
                 'bus_load_pct', 0) > 70
               else '#00cc77'}">
          {log_stats.get("bus_load_pct", 0):.1f}%
        </div>
        <div class="stat-lbl">BUS LOAD</div>
      </div>
      <div class="stat-card">
        <div class="stat-val"
             style="color:{
               '#ff2244' if len(dtcs) > 0
               else '#00cc77'}">
          {len(dtcs)}
        </div>
        <div class="stat-lbl">ACTIVE DTCS</div>
      </div>
      <div class="stat-card">
        <div class="stat-val">
          {log_stats.get("msgs_per_sec", 0):.0f}
        </div>
        <div class="stat-lbl">MSGS / SEC</div>
      </div>
    </div>
  </div>
</div>

<!-- -- SWC Architecture -- -->
<div class="section">
  <div class="section-header">
    AUTOSAR SOFTWARE COMPONENT (SWC) ARCHITECTURE
  </div>
  <div class="section-body">
    <table>
      <tr>
        <th>SWC NAME</th>
        <th>BUS</th>
        <th>CYCLE</th>
        <th>INPUTS (R-Ports)</th>
        <th>OUTPUTS (P-Ports)</th>
        <th>DTC CODES</th>
      </tr>
      {swc_rows}
    </table>
  </div>
</div>

<!-- -- CAN Bus Statistics -- -->
<div class="section">
  <div class="section-header">
    CAN BUS TRAFFIC ANALYSIS
  </div>
  <div class="section-body">
    <div style="display:grid;
         grid-template-columns:1fr 1fr;gap:20px">
      <div>
        <div style="font-size:10px;color:#3a6a9c;
             letter-spacing:2px;margin-bottom:10px">
          MESSAGE COUNT PER ECU
        </div>
        <table>
          <tr>
            <th>ECU</th><th>MESSAGES</th>
            <th>LOAD BAR</th><th>% SHARE</th>
          </tr>
          {ecu_rows}
        </table>
      </div>
      <div>
        <div style="font-size:10px;color:#3a6a9c;
             letter-spacing:2px;margin-bottom:10px">
          TOP 5 MOST ACTIVE CAN IDs
        </div>
        <table>
          <tr>
            <th>CAN ID</th>
            <th>ECU</th>
            <th>COUNT</th>
          </tr>
          {top_ids_rows}
        </table>
        <div style="margin-top:16px;padding:12px;
             background:rgba(13,32,64,0.4);
             border-radius:8px;font-size:11px">
          <div style="color:#3a6a9c;
               letter-spacing:2px;font-size:10px;
               margin-bottom:8px">
            BUS PARAMETERS
          </div>
          <div style="display:grid;
               grid-template-columns:1fr 1fr;
               gap:6px;font-family:monospace">
            <span style="color:#4a6a8a">
              Protocol:</span>
            <span style="color:#eaf4ff">
              CAN 2.0B</span>
            <span style="color:#4a6a8a">
              Speed:</span>
            <span style="color:#eaf4ff">
              500 kbps</span>
            <span style="color:#4a6a8a">
              Max Frame:</span>
            <span style="color:#eaf4ff">
              8 bytes</span>
            <span style="color:#4a6a8a">
              Termination:</span>
            <span style="color:#eaf4ff">
              120    2</span>
            <span style="color:#4a6a8a">
              Total Errors:</span>
            <span style="color:{
              '#ff2244'
              if log_stats.get('total_errors',0) > 0
              else '#00cc77'}">
              {log_stats.get('total_errors', 0)}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- -- DTC Fault Report -- -->
<div class="section">
  <div class="section-header">
    OBD-II DIAGNOSTIC TROUBLE CODE (DTC) REPORT
  </div>
  <div class="section-body">
    <table>
      <tr>
        <th>CODE</th>
        <th>DESCRIPTION</th>
        <th>SEVERITY</th>
        <th>SYSTEM</th>
        <th>RECOMMENDED ACTION</th>
        <th>TIMESTAMP</th>
      </tr>
      {dtc_rows}
    </table>
  </div>
</div>

<!-- -- Network Architecture -- -->
<div class="section">
  <div class="section-header">
    IN-VEHICLE NETWORK ARCHITECTURE
  </div>
  <div class="section-body">
    <div style="font-family:monospace;font-size:12px;
         line-height:2;color:#4a6a8a;
         background:rgba(13,32,64,0.3);
         padding:20px;border-radius:8px">
      <span style="color:#00cc77">LIN Bus (1kbps)</span>
      &nbsp;&nbsp;&nbsp;&nbsp;
      <span style="color:#00b4ff">
        CAN Bus (500kbps)
      </span>
      &nbsp;&nbsp;&nbsp;&nbsp;
      <span style="color:#ffcc00">
        Automotive Ethernet (100Mbps)
      </span><br><br>

      <span style="color:#00cc77">
         - TPMS ECU ----------------------------- 
      </span><br>
      <span style="color:#00cc77">
         - Window/Seat ECU ---------------------- 
      </span>
      &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
      <span style="color:#ff9900">
          GATEWAY ECU
      </span><br>
      <span style="color:#00b4ff">
         - Engine ECU --------------------------- 
      </span><br>
      <span style="color:#00b4ff">
         - ABS ECU ------------------------------ 
      </span>
      &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
      <span style="color:#ff9900">
        --- bridges --- 
      </span>
      <span style="color:#ffcc00">
        ADAS ECU
      </span><br>
      <span style="color:#00b4ff">
         - Airbag ECU --------------------------- 
      </span><br>
      <span style="color:#00b4ff">
         - Transmission ECU --------------------- 
      </span>
      &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
      <span style="color:#ffcc00">
        Dashboard
      </span><br>
      <span style="color:#00b4ff">
         - BMS ECU ------------------------------ 
      </span><br>
      <span style="color:#00b4ff">
         - Motor ECU ---------------------------- 
      </span><br>
      <span style="color:#00b4ff">
         - Hybrid Control ECU ------------------- 
      </span><br>
      <span style="color:#00b4ff">
         - Regen Brake ECU ---------------------- 
      </span>
    </div>
  </div>
</div>

<div class="footer">
  CANVAS   Hybrid Vehicle Network Simulator &nbsp; &nbsp;
  Generated {timestamp} &nbsp; &nbsp;
  CAN   LIN   Ethernet (DoIP) &nbsp; &nbsp;
  AUTOSAR Compliant Architecture
</div>

</body>
</html>'''