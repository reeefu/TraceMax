from PyQt5.QtWidgets import (
    QFrame, QGroupBox, QHBoxLayout, QVBoxLayout, QGridLayout,
    QSpinBox, QComboBox, QLineEdit, QLabel
)
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtCore import Qt

from widgets.seiswidgets import cmdButton, chkButton, bigLabel, statusText, scroller

FILT_MAX = 300  # maximum frequency slider value (Hz)


class ControlPanel(QFrame):

    def __init__(self, parent, height):
        super().__init__(parent)
        self._win = parent   # reference back to SeismoWin for callbacks
        self.h_cmd = height
        self._build()

    # ------------------------------------------------------------------
    # Public interface used by SeismoWin
    # ------------------------------------------------------------------

    def sync_filter_ui(self, lf, hf):
        """Update sliders and text boxes from external values."""
        self.lofreq.blockSignals(True);  self.lofreq.setValue(int(lf));  self.lofreq.blockSignals(False)
        self.hifreq.blockSignals(True);  self.hifreq.setValue(int(hf));  self.hifreq.blockSignals(False)
        self.lfvalue.setText(f'{lf:.2f} Hz')
        self.hfvalue.setText(f'{hf:.2f} Hz')
        self.lf_edit.setText(str(lf))
        self.hf_edit.setText(str(hf))

    def set_filter_enabled(self, enabled):
        self.tunning.setEnabled(enabled)

    def set_selected_label(self, text):
        self.tracesel.setText(text)

    def update_trace_zoom_label(self, text):
        """Update the trace zoom status label."""
        self.trace_zoom_label.setText(text)

    # ------------------------------------------------------------------
    # Internal build
    # ------------------------------------------------------------------

    def _build(self):
        lout = QHBoxLayout()
        lout.setSpacing(4)
        lout.setContentsMargins(4, 2, 4, 2)
        lout.addWidget(self._make_pick_group(), 3)
        lout.addWidget(self._make_view_group(), 1)
        lout.addWidget(self._make_filter_group(), 2)
        lout.addWidget(self._make_trace_zoom_group(), 1)
        self.setLayout(lout)

    def _make_pick_group(self):
        grp = QGroupBox('PICK')
        lo = QHBoxLayout()
        lo.setContentsMargins(4, 4, 4, 4)
        lo.setSpacing(6)

        # Left: data log
        frm = QFrame()
        self.pickbox = statusText(frm, (0, 0), (140, self.h_cmd - 36))
        lo.addWidget(frm, stretch=1)

        # Right: toggle + 3 action buttons with logo space above text
        def _make_pick_btn(parent, text, callback):
            """Create a button with logo placeholder space above the label."""
            btn_frame = QFrame()
            btn_lo = QVBoxLayout(btn_frame)
            btn_lo.setContentsMargins(2, 2, 2, 2)
            btn_lo.setSpacing(2)

            # Logo placeholder area
            logo_area = QFrame()
            logo_area.setMinimumSize(60, 40)
            logo_area.setStyleSheet(
                'background-color: #f0f3f7; border: 1px solid #d0d7e2; border-radius: 6px;'
            )
            btn_lo.addWidget(logo_area, stretch=1)

            # Button text
            btn = cmdButton(btn_frame, text, (0, 0), (110, 24), callback)
            btn.setMinimumWidth(100)
            btn_lo.addWidget(btn)
            return btn_frame

        # Toggle button for start/stop picking
        toggle_frame = QFrame()
        toggle_lo = QVBoxLayout(toggle_frame)
        toggle_lo.setContentsMargins(2, 2, 2, 2)
        toggle_lo.setSpacing(2)

        # Logo placeholder for toggle
        toggle_logo = QFrame()
        toggle_logo.setMinimumSize(60, 40)
        toggle_logo.setStyleSheet(
            'background-color: #f0f3f7; border: 1px solid #d0d7e2; border-radius: 6px;'
        )
        toggle_lo.addWidget(toggle_logo, stretch=1)

        self.pick_toggle_btn = cmdButton(toggle_frame, 'START PICK', (0, 0), (110, 24),
                                         self._win.toggle_picking)
        self.pick_toggle_btn.setMinimumWidth(100)
        toggle_lo.addWidget(self.pick_toggle_btn)

        lo.addWidget(toggle_frame)

        import_btn = _make_pick_btn(grp, 'IMPORT PICK', self._win.import_pick_dat)
        view_btn = _make_pick_btn(grp, 'VIEW DATA', self._win.show_arrival_dialog)
        clear_btn = _make_pick_btn(grp, 'CLEAR PLOT', self._win.clearpick)

        lo.addWidget(import_btn)
        lo.addWidget(view_btn)
        lo.addWidget(clear_btn)

        grp.setLayout(lo)
        return grp

    def _make_view_group(self):
        grp = QGroupBox('VIEW')
        grid = QGridLayout()
        grid.setContentsMargins(4, 2, 4, 2)
        grid.setSpacing(2)

        frm = QFrame()
        self.zoom_chk     = chkButton(frm, 'Zoom',       (0, 0), (90, 22), self._win.zoom_plot)
        self.autos_chk    = chkButton(frm, 'Autoscale',  (0, 0), (90, 22), self._win.auto_scale)
        self.filt_chk     = chkButton(frm, 'Filter',     (0, 0), (90, 22), self._win.toggle_filter)
        self.fillplot_chk = chkButton(frm, 'Fill Trace', (0, 0), (90, 22), self._win.toggle_fillplot)

        # All view options start unchecked (off)
        self.zoom_chk.setChecked(False)
        self.autos_chk.setChecked(False)
        self.filt_chk.setChecked(False)
        self.fillplot_chk.setChecked(False)

        grid.addWidget(self.zoom_chk, 0, 0)
        grid.addWidget(self.autos_chk, 0, 1)
        grid.addWidget(self.filt_chk, 1, 0)
        grid.addWidget(self.fillplot_chk, 1, 1)

        grp.setLayout(grid)
        return grp

    def _make_filter_group(self):
        grp = QGroupBox('FILTER \u2014 zero-phase (filtfilt)')
        frm = QFrame()

        # Row 0 (y=0): selected trace label
        self.tracesel = bigLabel(frm, 'Selected: None', (0, 0, 280, 16))

        # Row 1 (y=18): Low Hz — compact layout
        bigLabel(frm, 'Low Hz',  (0, 20, 40, 16))
        self.lofreq = scroller(frm, (42, 22, 80, 14), (0, FILT_MAX, 1), self._win.lf_tune)
        self.lf_edit = QLineEdit('0', frm)
        self.lf_edit.setGeometry(126, 20, 40, 16)
        self.lf_edit.setValidator(QDoubleValidator(0.0, float(FILT_MAX), 4))
        self.lf_edit.setToolTip('Low-cut frequency (Hz)')
        self.lf_edit.returnPressed.connect(lambda: (
            self.lofreq.blockSignals(True),
            self.lofreq.setValue(int(float(self.lf_edit.text() or 0))),
            self.lofreq.blockSignals(False),
            self._win.lf_tune()
        ))
        self.lfvalue = bigLabel(frm, '0 Hz',  (170, 20, 50, 16))

        # Row 2 (y=38): High Hz — compact layout
        bigLabel(frm, 'High Hz', (0, 40, 40, 16))
        self.hifreq = scroller(frm, (42, 42, 80, 14), (0, FILT_MAX, 1), self._win.hf_tune)
        self.hf_edit = QLineEdit('50', frm)
        self.hf_edit.setGeometry(126, 40, 40, 16)
        self.hf_edit.setValidator(QDoubleValidator(0.0, float(FILT_MAX), 4))
        self.hf_edit.setToolTip('High-cut frequency (Hz)')
        self.hf_edit.returnPressed.connect(lambda: (
            self.hifreq.blockSignals(True),
            self.hifreq.setValue(int(float(self.hf_edit.text() or 50))),
            self.hifreq.blockSignals(False),
            self._win.hf_tune()
        ))
        self.hfvalue = bigLabel(frm, '50 Hz', (170, 40, 50, 16))

        # Row 3 (y=58): Order | Type | Apply — all inline, compact
        bigLabel(frm, 'Order', (0, 60, 34, 16))
        self.filter_order = QSpinBox(frm)
        self.filter_order.setRange(1, 8)
        self.filter_order.setGeometry(36, 58, 36, 18)
        self.filter_order.setToolTip('Filter order (1\u20138)')

        bigLabel(frm, 'Type', (76, 60, 28, 16))
        self.filter_type = QComboBox(frm)
        self.filter_type.addItems(['Butterworth', 'Chebyshev I', 'Bessel'])
        self.filter_type.setGeometry(104, 58, 80, 18)
        self.filter_type.setToolTip('Filter family')

        apply_btn = cmdButton(frm, 'Apply', (188, 55), (60, 24), self._win._apply_filter)
        apply_btn.setMinimumWidth(50)

        self.lofreq.blockSignals(True);  self.lofreq.setValue(0);   self.lofreq.blockSignals(False)
        self.hifreq.blockSignals(True);  self.hifreq.setValue(50);  self.hifreq.blockSignals(False)
        self.filter_order.blockSignals(True); self.filter_order.setValue(2); self.filter_order.blockSignals(False)

        lo = QVBoxLayout()
        lo.setContentsMargins(4, 2, 4, 2)
        lo.addWidget(frm)
        grp.setLayout(lo)

        self.tunning = frm
        self.tunning.setEnabled(False)

        return grp

    def _make_trace_zoom_group(self):
        """Create the TRACE ZOOM group with view count buttons and scroll controls."""
        grp = QGroupBox('TRACE ZOOM')
        lo = QVBoxLayout()
        lo.setContentsMargins(4, 4, 4, 4)
        lo.setSpacing(4)

        # Status label showing current view
        self.trace_zoom_label = QLabel('All traces')
        self.trace_zoom_label.setAlignment(Qt.AlignCenter)
        self.trace_zoom_label.setStyleSheet(
            'font-size: 10px; color: #2c5f7a; font-weight: bold; '
            'background-color: #f0f3f7; border: 1px solid #d0d7e2; '
            'border-radius: 4px; padding: 2px;'
        )
        lo.addWidget(self.trace_zoom_label)

        # View count buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(3)

        btn_style = (
            'QPushButton { font-size: 11px; font-weight: bold; '
            'background: qlineargradient(x1:0,y1:0,x2:0,y2:1, '
            'stop:0 #ffffff, stop:1 #e8ecf1); '
            'border: 1px solid #b0bec5; border-radius: 4px; padding: 3px 6px; } '
            'QPushButton:hover { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, '
            'stop:0 #e3f2fd, stop:1 #bbdefb); border-color: #0097c4; } '
            'QPushButton:pressed { background: #0097c4; color: white; }'
        )

        btn_active_style = (
            'QPushButton { font-size: 11px; font-weight: bold; '
            'background: #0097c4; color: white; '
            'border: 1px solid #007a9e; border-radius: 4px; padding: 3px 6px; }'
        )

        self._trace_zoom_btn_style = btn_style
        self._trace_zoom_btn_active_style = btn_active_style

        self.zoom_all_btn = cmdButton(grp, 'All', (0, 0), (36, 22),
                                      lambda: self._win.set_trace_zoom(0))
        self.zoom_1_btn = cmdButton(grp, '1', (0, 0), (28, 22),
                                    lambda: self._win.set_trace_zoom(1))
        self.zoom_3_btn = cmdButton(grp, '3', (0, 0), (28, 22),
                                    lambda: self._win.set_trace_zoom(3))
        self.zoom_5_btn = cmdButton(grp, '5', (0, 0), (28, 22),
                                    lambda: self._win.set_trace_zoom(5))

        self._trace_zoom_btns = [self.zoom_all_btn, self.zoom_1_btn,
                                 self.zoom_3_btn, self.zoom_5_btn]

        for btn in self._trace_zoom_btns:
            btn.setStyleSheet(btn_style)
            btn_row.addWidget(btn)

        # Mark "All" as active initially
        self.zoom_all_btn.setStyleSheet(btn_active_style)

        lo.addLayout(btn_row)

        # Scroll buttons row
        scroll_row = QHBoxLayout()
        scroll_row.setSpacing(3)

        scroll_style = (
            'QPushButton { font-size: 13px; font-weight: bold; '
            'background: qlineargradient(x1:0,y1:0,x2:0,y2:1, '
            'stop:0 #ffffff, stop:1 #e8ecf1); '
            'border: 1px solid #b0bec5; border-radius: 4px; padding: 2px 8px; } '
            'QPushButton:hover { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, '
            'stop:0 #e3f2fd, stop:1 #bbdefb); border-color: #0097c4; } '
            'QPushButton:pressed { background: #0097c4; color: white; } '
            'QPushButton:disabled { background: #f5f5f5; color: #bdbdbd; '
            'border-color: #e0e0e0; }'
        )

        self.scroll_up_btn = cmdButton(grp, '\u25B2', (0, 0), (40, 24),
                                       self._win.trace_scroll_up)
        self.scroll_down_btn = cmdButton(grp, '\u25BC', (0, 0), (40, 24),
                                         self._win.trace_scroll_down)

        self.scroll_up_btn.setStyleSheet(scroll_style)
        self.scroll_down_btn.setStyleSheet(scroll_style)
        self.scroll_up_btn.setToolTip('Scroll traces up')
        self.scroll_down_btn.setToolTip('Scroll traces down')

        # Disabled initially (all traces shown)
        self.scroll_up_btn.setEnabled(False)
        self.scroll_down_btn.setEnabled(False)

        scroll_row.addWidget(self.scroll_up_btn)
        scroll_row.addWidget(self.scroll_down_btn)

        lo.addLayout(scroll_row)

        grp.setLayout(lo)
        return grp

    def set_trace_zoom_active(self, count):
        """Highlight the active trace zoom button. count=0 means All."""
        for btn in self._trace_zoom_btns:
            btn.setStyleSheet(self._trace_zoom_btn_style)
        if count == 0:
            self.zoom_all_btn.setStyleSheet(self._trace_zoom_btn_active_style)
        elif count == 1:
            self.zoom_1_btn.setStyleSheet(self._trace_zoom_btn_active_style)
        elif count == 3:
            self.zoom_3_btn.setStyleSheet(self._trace_zoom_btn_active_style)
        elif count == 5:
            self.zoom_5_btn.setStyleSheet(self._trace_zoom_btn_active_style)
