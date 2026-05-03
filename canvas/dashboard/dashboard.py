# CANVAS Project
# Module: Dashboard
# File: dashboard.py
# Premium Tesla/ADAS style dashboard   tkinter + matplotlib

import tkinter as tk
from tkinter import ttk
import threading
import time
import math
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.animation import FuncAnimation
from collections import deque
import matplotlib.gridspec as gridspec

# -- Color Palette -------------------------------------------------
CLR_BG          = '#020818'
CLR_PANEL       = '#040d24'
CLR_BORDER      = '#0a1f4e'
CLR_BLUE        = '#00aaff'
CLR_CYAN        = '#00eeff'
CLR_BLUE_DIM    = '#004488'
CLR_GREEN       = '#00ff99'
CLR_GREEN_DIM   = '#004433'
CLR_YELLOW      = '#ffcc00'
CLR_RED         = '#ff3355'
CLR_WHITE       = '#e8f4ff'
CLR_GRAY        = '#1a3a5c'
CLR_TEXT_DIM    = '#3a6a9c'

plt.rcParams.update({
    'figure.facecolor'  : CLR_BG,
    'axes.facecolor'    : CLR_PANEL,
    'axes.edgecolor'    : CLR_BORDER,
    'axes.labelcolor'   : CLR_TEXT_DIM,
    'xtick.color'       : CLR_TEXT_DIM,
    'ytick.color'       : CLR_TEXT_DIM,
    'text.color'        : CLR_WHITE,
    'grid.color'        : CLR_GRAY,
    'grid.alpha'        : 0.3,
    'font.family'       : 'monospace',
})

class Dashboard:
    def __init__(self, ethernet_bus):
        self.ethernet_bus = ethernet_bus
        self.running      = True

        # History buffers for live graphs (60 points = 6 seconds)
        self.history_len  = 60
        self.t_data       = deque(maxlen=self.history_len)
        self.speed_data   = deque(maxlen=self.history_len)
        self.rpm_data     = deque(maxlen=self.history_len)
        self.soc_data     = deque(maxlen=self.history_len)
        self.temp_data    = deque(maxlen=self.history_len)
        self.tick         = 0

        # Pre-fill with zeros
        for _ in range(self.history_len):
            self.t_data.append(self.tick)
            self.speed_data.append(0)
            self.rpm_data.append(0)
            self.soc_data.append(75)
            self.temp_data.append(25)

        self.root = tk.Tk()
        self.root.title("CANVAS   Hybrid Vehicle Network")
        self.root.geometry("1400x820")
        self.root.configure(bg=CLR_BG)
        self.root.resizable(False, False)

        self._build_ui()

    # -- UI Builder ------------------------------------------------

    def _build_ui(self):
        # -- Header ------------------------------------------------
        header = tk.Frame(self.root, bg=CLR_BG, height=50)
        header.pack(fill='x', padx=15, pady=(10, 0))

        tk.Label(
            header,
            text="   CANVAS",
            bg=CLR_BG, fg=CLR_CYAN,
            font=('Courier', 18, 'bold')
        ).pack(side='left')

        tk.Label(
            header,
            text="HYBRID VEHICLE NETWORK SIMULATOR",
            bg=CLR_BG, fg=CLR_TEXT_DIM,
            font=('Courier', 10)
        ).pack(side='left', padx=(10, 0), pady=(6, 0))

        # Live clock
        self.clock_label = tk.Label(
            header, text="",
            bg=CLR_BG, fg=CLR_BLUE,
            font=('Courier', 10)
        )
        self.clock_label.pack(side='right')

        # Phase indicator
        self.phase_label = tk.Label(
            header, text="* IDLE",
            bg=CLR_BG, fg=CLR_GREEN,
            font=('Courier', 11, 'bold')
        )
        self.phase_label.pack(side='right', padx=20)

        # Divider
        tk.Frame(self.root, bg=CLR_BORDER, height=1).pack(
            fill='x', padx=15, pady=5)

        # -- Main Layout -------------------------------------------
        main = tk.Frame(self.root, bg=CLR_BG)
        main.pack(fill='both', expand=True, padx=15, pady=5)

        # Left column   gauges
        left = tk.Frame(main, bg=CLR_BG, width=420)
        left.pack(side='left', fill='y', padx=(0, 10))
        left.pack_propagate(False)

        # Center column   graphs
        center = tk.Frame(main, bg=CLR_BG)
        center.pack(side='left', fill='both', expand=True)

        # Right column   status panels
        right = tk.Frame(main, bg=CLR_BG, width=280)
        right.pack(side='right', fill='y', padx=(10, 0))
        right.pack_propagate(False)

        self._build_gauges(left)
        self._build_graphs(center)
        self._build_status(right)

        # -- ADAS Warning Bar --------------------------------------
        tk.Frame(self.root, bg=CLR_BORDER, height=1).pack(
            fill='x', padx=15, pady=5)
        self._build_adas_bar()

    # -- Gauges ----------------------------------------------------

    def _build_gauges(self, parent):
        tk.Label(
            parent, text="INSTRUMENT CLUSTER",
            bg=CLR_BG, fg=CLR_TEXT_DIM,
            font=('Courier', 8)
        ).pack(anchor='w', pady=(0, 5))

        # Matplotlib figure for gauges
        self.gauge_fig = plt.Figure(figsize=(4.2, 5.5), dpi=95)
        self.gauge_fig.patch.set_facecolor(CLR_BG)

        gs = gridspec.GridSpec(
            2, 2, figure=self.gauge_fig,
            hspace=0.4, wspace=0.3
        )

        self.ax_speed = self.gauge_fig.add_subplot(gs[0, 0])
        self.ax_rpm   = self.gauge_fig.add_subplot(gs[0, 1])
        self.ax_soc   = self.gauge_fig.add_subplot(gs[1, 0])
        self.ax_temp  = self.gauge_fig.add_subplot(gs[1, 1])

        self._draw_gauge(self.ax_speed, 0,   'SPEED',  'km/h',  CLR_CYAN,   0,   140)
        self._draw_gauge(self.ax_rpm,   0,   'RPM',    'x1000', CLR_BLUE,   0,   5)
        self._draw_gauge(self.ax_soc,   75,  'BATTERY','%',     CLR_GREEN,  0,   100)
        self._draw_gauge(self.ax_temp,  25,  'TEMP',   ' C',    CLR_YELLOW, 20,  110)

        canvas = FigureCanvasTkAgg(self.gauge_fig, parent)
        canvas.get_tk_widget().pack(fill='both', expand=True)
        canvas.get_tk_widget().configure(bg=CLR_BG)
        self.gauge_canvas = canvas

    def _draw_gauge(self, ax, value, label, unit,
                    color, vmin, vmax):
        ax.set_facecolor(CLR_PANEL)
        ax.set_aspect('equal')
        ax.set_xlim(-1.3, 1.3)
        ax.set_ylim(-1.3, 1.1)
        ax.axis('off')

        # Outer ring
        ring = plt.Circle((0, 0), 1.05,
                           fill=False, color=CLR_BORDER,
                           linewidth=3)
        ax.add_patch(ring)

        # Background arc
        theta = [math.radians(a)
                 for a in range(220, -41, -1)]
        bx = [math.cos(t) for t in theta]
        by = [math.sin(t) for t in theta]
        ax.plot(bx, by, color=CLR_GRAY,
                linewidth=6, alpha=0.3, solid_capstyle='round')

        # Value arc
        pct = (value - vmin) / (vmax - vmin)
        end_angle = 220 - int(pct * 260)
        theta_v   = [math.radians(a)
                     for a in range(220, end_angle - 1, -1)]
        if theta_v:
            vx = [math.cos(t) for t in theta_v]
            vy = [math.sin(t) for t in theta_v]
            ax.plot(vx, vy, color=color,
                    linewidth=6, solid_capstyle='round')

        # Tick marks
        for i in range(11):
            angle  = math.radians(220 - i * 26)
            r1, r2 = 0.82, 0.72 if i % 5 == 0 else 0.78
            ax.plot(
                [r1 * math.cos(angle), r2 * math.cos(angle)],
                [r1 * math.sin(angle), r2 * math.sin(angle)],
                color=CLR_TEXT_DIM, linewidth=1.5
            )

        # Needle
        needle_angle = math.radians(220 - pct * 260)
        ax.plot(
            [0, 0.65 * math.cos(needle_angle)],
            [0, 0.65 * math.sin(needle_angle)],
            color=CLR_WHITE, linewidth=2,
            solid_capstyle='round'
        )

        # Center dot
        dot = plt.Circle((0, 0), 0.06,
                          color=color, zorder=5)
        ax.add_patch(dot)

        # Value text
        disp = f"{value/1000:.1f}" if unit == 'x1000' else str(int(value))
        ax.text(0, -0.35, disp,
                ha='center', va='center',
                color=CLR_WHITE,
                fontsize=16, fontweight='bold',
                fontfamily='monospace')

        # Label + unit
        ax.text(0, -0.65, label,
                ha='center', va='center',
                color=color, fontsize=7,
                fontfamily='monospace')
        ax.text(0, -0.85, unit,
                ha='center', va='center',
                color=CLR_TEXT_DIM, fontsize=6,
                fontfamily='monospace')

    def _refresh_gauge(self, ax, value, label, unit,
                       color, vmin, vmax):
        ax.cla()
        self._draw_gauge(ax, value, label, unit,
                         color, vmin, vmax)

    # -- Live Graphs -----------------------------------------------

    def _build_graphs(self, parent):
        tk.Label(
            parent, text="LIVE TELEMETRY",
            bg=CLR_BG, fg=CLR_TEXT_DIM,
            font=('Courier', 8)
        ).pack(anchor='w', pady=(0, 5))

        self.graph_fig = plt.Figure(figsize=(6.5, 5.5), dpi=95)
        self.graph_fig.patch.set_facecolor(CLR_BG)

        gs = gridspec.GridSpec(
            2, 2, figure=self.graph_fig,
            hspace=0.55, wspace=0.35
        )

        self.ax_g_speed = self.graph_fig.add_subplot(gs[0, 0])
        self.ax_g_rpm   = self.graph_fig.add_subplot(gs[0, 1])
        self.ax_g_soc   = self.graph_fig.add_subplot(gs[1, 0])
        self.ax_g_temp  = self.graph_fig.add_subplot(gs[1, 1])

        for ax, title, color in [
            (self.ax_g_speed, 'SPEED  km/h',  CLR_CYAN),
            (self.ax_g_rpm,   'RPM',          CLR_BLUE),
            (self.ax_g_soc,   'BATTERY  %',   CLR_GREEN),
            (self.ax_g_temp,  'ENGINE   C',   CLR_YELLOW),
        ]:
            ax.set_facecolor(CLR_PANEL)
            ax.set_title(title, color=color,
                         fontsize=7, fontfamily='monospace',
                         pad=4)
            ax.grid(True, alpha=0.2)
            ax.tick_params(labelsize=6)
            for spine in ax.spines.values():
                spine.set_edgecolor(CLR_BORDER)

        # Initial empty lines
        self.line_speed, = self.ax_g_speed.plot(
            [], [], color=CLR_CYAN, linewidth=1.5)
        self.line_rpm,   = self.ax_g_rpm.plot(
            [], [], color=CLR_BLUE, linewidth=1.5)
        self.line_soc,   = self.ax_g_soc.plot(
            [], [], color=CLR_GREEN, linewidth=1.5)
        self.line_temp,  = self.ax_g_temp.plot(
            [], [], color=CLR_YELLOW, linewidth=1.5)

        # Fill under lines
        self.fill_speed = None
        self.fill_rpm   = None
        self.fill_soc   = None
        self.fill_temp  = None

        canvas = FigureCanvasTkAgg(self.graph_fig, parent)
        canvas.get_tk_widget().pack(fill='both', expand=True)
        canvas.get_tk_widget().configure(bg=CLR_BG)
        self.graph_canvas = canvas

    def _update_graphs(self):
        t    = list(self.t_data)
        spd  = list(self.speed_data)
        rpm  = list(self.rpm_data)
        soc  = list(self.soc_data)
        temp = list(self.temp_data)

        for ax, line, fill_attr, ydata, color, ymax in [
            (self.ax_g_speed, self.line_speed,
             'fill_speed', spd,  CLR_CYAN,   140),
            (self.ax_g_rpm,   self.line_rpm,
             'fill_rpm',   rpm,  CLR_BLUE,   5000),
            (self.ax_g_soc,   self.line_soc,
             'fill_soc',   soc,  CLR_GREEN,  100),
            (self.ax_g_temp,  self.line_temp,
             'fill_temp',  temp, CLR_YELLOW, 110),
        ]:
            line.set_data(t, ydata)
            ax.set_xlim(min(t), max(t) + 1)
            ax.set_ylim(0, ymax)

            # Remove old fill
            old = getattr(self, fill_attr)
            if old:
                old.remove()

            # Add new fill
            new_fill = ax.fill_between(
                t, ydata, alpha=0.08, color=color)
            setattr(self, fill_attr, new_fill)

        self.graph_canvas.draw_idle()

    # -- Status Panels ---------------------------------------------

    def _build_status(self, parent):
        tk.Label(
            parent, text="ECU STATUS",
            bg=CLR_BG, fg=CLR_TEXT_DIM,
            font=('Courier', 8)
        ).pack(anchor='w', pady=(0, 5))

        # Status items
        self.status_vars = {}
        items = [
            ('hybrid_mode',    '[POW] HYBRID MODE',   CLR_GREEN),
            ('current_gear',   '   GEAR',          CLR_CYAN),
            ('drive_mode',     '[CAR] DRIVE MODE',     CLR_BLUE),
            ('motor_mode',     '  MOTOR MODE',     CLR_CYAN),
            ('motor_torque',   '  TORQUE (Nm)',    CLR_BLUE),
            ('regen_power',    '   REGEN (kW)',     CLR_GREEN),
            ('energy_recovered','[POW] RECOVERED (Wh)', CLR_GREEN),
            ('brake_pressure', '  BRAKE (bar)',    CLR_YELLOW),
            ('impact_force',   '  IMPACT (G)',     CLR_RED),
            ('tyre_pressure_fl','[ERROR] TYRE FL (PSI)', CLR_CYAN),
            ('tyre_pressure_fr','[ERROR] TYRE FR (PSI)', CLR_CYAN),
            ('window_fl',      '  WINDOW FL (%)', CLR_TEXT_DIM),
            ('rain_detected',  '   RAIN',          CLR_BLUE),
        ]

        for key, label, color in items:
            row = tk.Frame(
                parent, bg=CLR_PANEL,
                highlightbackground=CLR_BORDER,
                highlightthickness=1
            )
            row.pack(fill='x', pady=2, ipady=4)

            tk.Label(
                row, text=label,
                bg=CLR_PANEL, fg=CLR_TEXT_DIM,
                font=('Courier', 7),
                width=18, anchor='w'
            ).pack(side='left', padx=6)

            var = tk.Label(
                row, text='--',
                bg=CLR_PANEL, fg=color,
                font=('Courier', 9, 'bold'),
                anchor='e'
            )
            var.pack(side='right', padx=6)
            self.status_vars[key] = var

    # -- ADAS Warning Bar ------------------------------------------

    def _build_adas_bar(self):
        bar = tk.Frame(self.root, bg=CLR_BG)
        bar.pack(fill='x', padx=15, pady=(0, 10))

        tk.Label(
            bar, text="ADAS  ",
            bg=CLR_BG, fg=CLR_TEXT_DIM,
            font=('Courier', 8, 'bold')
        ).pack(side='left')

        self.adas_indicators = {}
        warnings = [
            ('collision_warning', '  COLLISION'),
            ('emergency_brake',   '  BRAKE'),
            ('overspeed_warning', '  OVERSPEED'),
            ('engine_overheat',   '  OVERHEAT'),
            ('battery_critical',  '  BATTERY'),
            ('tyre_warning',      '  TYRE'),
            ('airbag_alert',      '  AIRBAG'),
            ('regen_suggestion',  '  REGEN'),
        ]

        for key, label in warnings:
            lbl = tk.Label(
                bar, text=label,
                bg=CLR_BG, fg=CLR_GRAY,
                font=('Courier', 8, 'bold'),
                padx=8
            )
            lbl.pack(side='left')
            self.adas_indicators[key] = lbl

    # -- Update Loop -----------------------------------------------

    def update_loop(self):
        while self.running:
            try:
                s = self.ethernet_bus.get('vehicle_state', {})
                d = self.ethernet_bus.get('adas_decisions', {})

                if not s:
                    time.sleep(0.1)
                    continue

                speed = s.get('vehicle_speed', 0)
                rpm   = s.get('engine_rpm', 0)
                soc   = s.get('battery_soc', 75)
                temp  = s.get('engine_temp', 25)

                # Update history
                self.tick += 1
                self.t_data.append(self.tick)
                self.speed_data.append(speed)
                self.rpm_data.append(rpm)
                self.soc_data.append(soc)
                self.temp_data.append(temp)

                # Refresh gauges
                self._refresh_gauge(
                    self.ax_speed, speed,
                    'SPEED', 'km/h', CLR_CYAN, 0, 140)
                self._refresh_gauge(
                    self.ax_rpm, rpm / 1000,
                    'RPM', 'x1000', CLR_BLUE, 0, 5)
                self._refresh_gauge(
                    self.ax_soc, soc,
                    'BATTERY', '%', CLR_GREEN, 0, 100)
                self._refresh_gauge(
                    self.ax_temp, temp,
                    'TEMP', ' C', CLR_YELLOW, 20, 110)
                self.gauge_canvas.draw_idle()

                # Refresh graphs
                self._update_graphs()

                # Status panel
                for key, var in self.status_vars.items():
                    val = s.get(key, '--')
                    if isinstance(val, float):
                        var.config(text=f"{val:.1f}")
                    else:
                        var.config(text=str(val))

                # Phase label
                phase = s.get('hybrid_mode', 'IDLE')
                self.phase_label.config(
                    text=f"* {phase}",
                    fg=CLR_GREEN if phase == 'EV'
                    else CLR_YELLOW if phase == 'BOOST'
                    else CLR_CYAN
                )

                # Clock
                self.clock_label.config(
                    text=time.strftime('[TIME]  %H:%M:%S'))

                # ADAS warnings
                for key, lbl in self.adas_indicators.items():
                    active = d.get(key, False)
                    if key == 'regen_suggestion':
                        lbl.config(
                            fg=CLR_GREEN if active else CLR_GRAY)
                    else:
                        lbl.config(
                            fg=CLR_RED if active else CLR_GRAY)

            except Exception as e:
                print(f"[DASHBOARD] Error: {e}")

            time.sleep(0.5)

    def start(self):
        print("[DASHBOARD] Starting premium UI...")
        t        = threading.Thread(target=self.update_loop)
        t.daemon = True
        t.start()
        self.root.mainloop()
        self.running = False

    def stop(self):
        self.running = False
        try:
            self.root.destroy()
        except:
            pass
        print("[DASHBOARD] Stopped.")