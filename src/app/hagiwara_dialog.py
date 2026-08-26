import os
import json
import numpy as np
from scipy.interpolate import CubicSpline

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
    QPushButton, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog, QMessageBox, QGroupBox,
    QSpinBox, QDoubleSpinBox, QTabWidget, QWidget, QComboBox,
    QCheckBox, QSplitter, QTextEdit
)
from PyQt5.QtCore import Qt

from core.refraction import (
    slope_intercept_analysis, hagiwara_analysis, linear_regression,
    find_crossover_kneepoint, hagiwara_two_direction
)


class HagiwaraDialog(QDialog):
    """Hagiwara refraction analysis dialog with single and two-direction modes."""

    def __init__(self, parent, canvas):
        super().__init__(parent)
        self.setWindowTitle('Seismic Refraction Analysis \u2014 Hagiwara Method')
        self.resize(1100, 780)
        self._canvas = canvas
        self._win = parent
        self._result = None
        self._result_2dir = None
        self._tt_click_cid = None
        self._tt_offsets = None
        self._tt_times = None
        self._tt_positions = None
        self._tt_tap = None
        self._tt_tbp = None
        self._knee_artists_fwd = []  # transient forward knee marker
        self._knee_artists_bwd = []  # transient backward knee marker
        self._build_ui()

    def _build_ui(self):
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
        import matplotlib.pyplot as mpl
        mpl.style.use('default')

        main_lo = QVBoxLayout()

        # --- Mode selector ---
        mode_lo = QHBoxLayout()
        mode_lo.addWidget(QLabel('<b>Analysis Mode:</b>'))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(['Single Direction', 'Two Directions (TAP/TBP)'])
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode_lo.addWidget(self.mode_combo)
        mode_lo.addStretch()
        main_lo.addLayout(mode_lo)

        # --- Tabs ---
        self.tabs = QTabWidget()

        # ==================== TAB 1: Data Input ====================
        data_tab = QWidget()
        data_lo = QVBoxLayout(data_tab)

        # Spacing / offset controls
        offset_grp = QGroupBox('Geophone Offset Configuration')
        offset_lo = QHBoxLayout()

        self.use_spacing_chk = QCheckBox('Use uniform spacing')
        self.use_spacing_chk.setChecked(True)
        self.use_spacing_chk.toggled.connect(self._on_spacing_toggled)
        offset_lo.addWidget(self.use_spacing_chk)

        offset_lo.addWidget(QLabel('Spacing:'))
        self.spacing_spin = QDoubleSpinBox()
        self.spacing_spin.setRange(0.1, 10000.0)
        self.spacing_spin.setValue(2.0)
        self.spacing_spin.setSuffix(' m')
        self.spacing_spin.setDecimals(2)
        offset_lo.addWidget(self.spacing_spin)

        offset_lo.addStretch()

        # Crossover method
        offset_lo.addWidget(QLabel('Crossover method:'))
        self.method_combo = QComboBox()
        self.method_combo.addItems(['Auto (Knee-Point)', 'Auto (MSE)', 'Manual'])
        offset_lo.addWidget(self.method_combo)

        # Single-direction manual index
        self.manual_label = QLabel('Manual index:')
        offset_lo.addWidget(self.manual_label)
        self.cross_spin = QSpinBox()
        self.cross_spin.setRange(0, 999)
        self.cross_spin.setValue(0)
        self.cross_spin.setToolTip('Only used when crossover method is "Manual"')
        self.cross_spin.setEnabled(False)
        offset_lo.addWidget(self.cross_spin)

        # Two-direction manual indices (hidden by default)
        self.manual_fwd_label = QLabel('Fwd index:')
        offset_lo.addWidget(self.manual_fwd_label)
        self.cross_fwd_spin = QSpinBox()
        self.cross_fwd_spin.setRange(0, 999)
        self.cross_fwd_spin.setValue(0)
        self.cross_fwd_spin.setToolTip('Manual crossover index for forward (TAP) shot')
        self.cross_fwd_spin.setEnabled(False)
        offset_lo.addWidget(self.cross_fwd_spin)

        self.manual_bwd_label = QLabel('Bwd index:')
        offset_lo.addWidget(self.manual_bwd_label)
        self.cross_bwd_spin = QSpinBox()
        self.cross_bwd_spin.setRange(0, 999)
        self.cross_bwd_spin.setValue(0)
        self.cross_bwd_spin.setToolTip('Manual crossover index for backward (TBP) shot')
        self.cross_bwd_spin.setEnabled(False)
        offset_lo.addWidget(self.cross_bwd_spin)

        # Initially show single-direction controls, hide two-direction controls
        self.manual_fwd_label.hide()
        self.cross_fwd_spin.hide()
        self.manual_bwd_label.hide()
        self.cross_bwd_spin.hide()

        self.method_combo.currentIndexChanged.connect(self._on_method_changed)

        offset_grp.setLayout(offset_lo)
        data_lo.addWidget(offset_grp)

        # --- Single direction table ---
        self.single_widget = QWidget()
        single_lo = QVBoxLayout(self.single_widget)
        single_lo.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(
            ['Trace', 'Offset (m)', 'Arrival Time (s)', 'Elevation (°)']
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        single_lo.addWidget(self.table)

        single_btn_lo = QHBoxLayout()
        load_picks_btn = QPushButton('Load from Picks')
        load_picks_btn.clicked.connect(self._load_from_picks)
        load_file_btn = QPushButton('Load .dat File')
        load_file_btn.clicked.connect(self._load_dat)
        add_row_btn = QPushButton('Add Row')
        add_row_btn.clicked.connect(self._add_row)
        del_row_btn = QPushButton('Delete Row')
        del_row_btn.clicked.connect(self._del_row)

        single_btn_lo.addWidget(load_picks_btn)
        single_btn_lo.addWidget(load_file_btn)
        single_btn_lo.addWidget(add_row_btn)
        single_btn_lo.addWidget(del_row_btn)
        single_btn_lo.addStretch()
        single_lo.addLayout(single_btn_lo)

        data_lo.addWidget(self.single_widget)

        # --- Two-direction tables ---
        self.two_dir_widget = QWidget()
        two_dir_lo = QVBoxLayout(self.two_dir_widget)
        two_dir_lo.setContentsMargins(0, 0, 0, 0)

        tables_lo = QHBoxLayout()

        # Forward (TAP) table
        fwd_grp = QGroupBox('Forward Shot (TAP)')
        fwd_lo = QVBoxLayout()
        self.tap_table = QTableWidget()
        self.tap_table.setColumnCount(3)
        self.tap_table.setHorizontalHeaderLabels(['Trace', 'Arrival Time (s)', 'Elevation (°)'])
        self.tap_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        fwd_lo.addWidget(self.tap_table)
        fwd_grp.setLayout(fwd_lo)
        tables_lo.addWidget(fwd_grp)

        # Backward (TBP) table
        bwd_grp = QGroupBox('Backward Shot (TBP)')
        bwd_lo = QVBoxLayout()
        self.tbp_table = QTableWidget()
        self.tbp_table.setColumnCount(3)
        self.tbp_table.setHorizontalHeaderLabels(['Trace', 'Arrival Time (s)', 'Elevation (°)'])
        self.tbp_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        bwd_lo.addWidget(self.tbp_table)
        bwd_grp.setLayout(bwd_lo)
        tables_lo.addWidget(bwd_grp)

        two_dir_lo.addLayout(tables_lo)

        two_btn_lo = QHBoxLayout()
        load_tap_btn = QPushButton('Load TAP Picks')
        load_tap_btn.clicked.connect(self._load_tap_picks)
        load_tbp_btn = QPushButton('Load TBP Picks')
        load_tbp_btn.clicked.connect(self._load_tbp_picks)
        load_tap_dat_btn = QPushButton('Load TAP .dat')
        load_tap_dat_btn.clicked.connect(lambda: self._load_dat_into_table(self.tap_table, 'TAP'))
        load_tbp_dat_btn = QPushButton('Load TBP .dat')
        load_tbp_dat_btn.clicked.connect(lambda: self._load_dat_into_table(self.tbp_table, 'TBP'))
        load_tap_json = QPushButton('Load TAP JSON')
        load_tap_json.clicked.connect(self._load_tap_json)
        load_tbp_json = QPushButton('Load TBP JSON')
        load_tbp_json.clicked.connect(self._load_tbp_json)
        add_tap_row = QPushButton('Add TAP Row')
        add_tap_row.clicked.connect(lambda: self._add_table_row(self.tap_table))
        add_tbp_row = QPushButton('Add TBP Row')
        add_tbp_row.clicked.connect(lambda: self._add_table_row(self.tbp_table))

        two_btn_lo.addWidget(load_tap_btn)
        two_btn_lo.addWidget(load_tbp_btn)
        two_btn_lo.addWidget(load_tap_dat_btn)
        two_btn_lo.addWidget(load_tbp_dat_btn)
        two_btn_lo.addWidget(load_tap_json)
        two_btn_lo.addWidget(load_tbp_json)
        two_btn_lo.addWidget(add_tap_row)
        two_btn_lo.addWidget(add_tbp_row)
        two_btn_lo.addStretch()
        two_dir_lo.addLayout(two_btn_lo)

        data_lo.addWidget(self.two_dir_widget)
        self.two_dir_widget.hide()  # Hidden by default (single mode)

        self.tabs.addTab(data_tab, 'Data')

        # ==================== TAB 2: Travel-Time Curve ====================
        tt_tab = QWidget()
        tt_lo = QVBoxLayout(tt_tab)
        self.fig_tt, self.ax_tt = mpl.subplots(facecolor='#f4f6f9')
        self.canvas_tt = FigureCanvasQTAgg(self.fig_tt)
        tt_lo.addWidget(self.canvas_tt)
        self.tt_info = QLabel('')
        self.tt_info.setWordWrap(True)
        self.tt_info.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        tt_lo.addWidget(self.tt_info)
        self.tt_click_label = QLabel('\U0001f4a1 Click on a data point to set the knee-point')
        self.tt_click_label.setStyleSheet('color: #667788; font-style: italic; padding: 4px;')
        tt_lo.addWidget(self.tt_click_label)
        self.tabs.addTab(tt_tab, 'Travel-Time Curve')

        # ==================== TAB 3: Knee-Point Analysis ====================
        knee_tab = QWidget()
        knee_lo = QVBoxLayout(knee_tab)
        self.fig_knee, self.ax_knee = mpl.subplots(1, 2, facecolor='#f4f6f9',
                                                     figsize=(10, 4))
        self.canvas_knee = FigureCanvasQTAgg(self.fig_knee)
        knee_lo.addWidget(self.canvas_knee)
        self.knee_info = QLabel('')
        self.knee_info.setWordWrap(True)
        self.knee_info.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        knee_lo.addWidget(self.knee_info)
        self.tabs.addTab(knee_tab, 'Knee-Point Analysis')

        # ==================== TAB 4: Hagiwara Results ====================
        hag_tab = QWidget()
        hag_lo = QVBoxLayout(hag_tab)
        self.fig_hag, self.ax_hag = mpl.subplots(1, 2, facecolor='#f4f6f9',
                                                   figsize=(10, 4))
        self.canvas_hag = FigureCanvasQTAgg(self.fig_hag)
        hag_lo.addWidget(self.canvas_hag)
        self.hag_info = QLabel('')
        self.hag_info.setWordWrap(True)
        self.hag_info.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        hag_lo.addWidget(self.hag_info)
        self.tabs.addTab(hag_tab, 'Hagiwara Analysis')

        main_lo.addWidget(self.tabs)

        # --- Bottom buttons ---
        btn_lo = QHBoxLayout()
        analyze_btn = QPushButton('Calculate')
        analyze_btn.clicked.connect(self._analyze)
        export_btn = QPushButton('Export Results')
        export_btn.clicked.connect(self._export)
        close_btn = QPushButton('Close')
        close_btn.clicked.connect(self.close)
        btn_lo.addWidget(analyze_btn)
        btn_lo.addWidget(export_btn)
        export_png_btn = QPushButton('Export PNG')
        export_png_btn.clicked.connect(self._export_png)
        btn_lo.addWidget(export_png_btn)
        btn_lo.addStretch()
        btn_lo.addWidget(close_btn)
        main_lo.addLayout(btn_lo)

        self.setLayout(main_lo)

    # ------------------------------------------------------------------
    # Mode / method change handlers
    # ------------------------------------------------------------------

    def _on_mode_changed(self, idx):
        if idx == 0:  # Single direction
            self.single_widget.show()
            self.two_dir_widget.hide()
            # Show single manual controls, hide two-dir manual controls
            self.manual_label.show()
            self.cross_spin.show()
            self.manual_fwd_label.hide()
            self.cross_fwd_spin.hide()
            self.manual_bwd_label.hide()
            self.cross_bwd_spin.hide()
        else:  # Two directions
            self.single_widget.hide()
            self.two_dir_widget.show()
            # Show two-dir manual controls, hide single manual controls
            self.manual_label.hide()
            self.cross_spin.hide()
            self.manual_fwd_label.show()
            self.cross_fwd_spin.show()
            self.manual_bwd_label.show()
            self.cross_bwd_spin.show()
        # Re-apply method state for enable/disable
        self._on_method_changed(self.method_combo.currentIndex())

    def _on_method_changed(self, idx):
        is_manual = (idx == 2)
        mode = self.mode_combo.currentIndex()
        if mode == 0:  # Single direction
            self.cross_spin.setEnabled(is_manual)
            self.cross_fwd_spin.setEnabled(False)
            self.cross_bwd_spin.setEnabled(False)
        else:  # Two directions
            self.cross_spin.setEnabled(False)
            self.cross_fwd_spin.setEnabled(is_manual)
            self.cross_bwd_spin.setEnabled(is_manual)

    def _on_spacing_toggled(self, checked):
        self.spacing_spin.setEnabled(checked)
        # When using uniform spacing, the offset column in single-mode table
        # will be auto-filled on analyze

    # ------------------------------------------------------------------
    # Data loading — Single direction
    # ------------------------------------------------------------------

    def _load_from_picks(self):
        """Load arrival times from current canvas picks."""
        import core.actions as actions
        picks = actions.get_all_picks(self._canvas)
        if not picks:
            QMessageBox.information(self, 'Load', 'No picks found. Pick arrival times first.')
            return

        self.table.setRowCount(len(picks))
        spacing = self.spacing_spin.value()
        for row, (tidx, name, ptime) in enumerate(picks):
            name_item = QTableWidgetItem(name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)

            if self.use_spacing_chk.isChecked():
                offset_val = row * spacing
            else:
                offset_val = 0.0
            offset_item = QTableWidgetItem(f'{offset_val:.2f}')
            time_item = QTableWidgetItem(f'{ptime:.6f}')

            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, offset_item)
            self.table.setItem(row, 2, time_item)
            self.table.setItem(row, 3, QTableWidgetItem('0.0'))

    def _load_dat(self):
        """Load from a .dat file (space-delimited: index name offset time)."""
        fnm, _ = QFileDialog.getOpenFileName(
            self, 'Open Arrival Data', '', 'DAT files (*.dat);;All files (*)'
        )
        if not fnm:
            return

        rows = []
        with open(fnm) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split()
                if len(parts) >= 4:
                    rows.append((parts[1], parts[2], parts[3]))
                elif len(parts) >= 3:
                    rows.append((parts[0], parts[1], parts[2]))

        self.table.setRowCount(len(rows))
        for row, (name, offset, time_val) in enumerate(rows):
            name_item = QTableWidgetItem(name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, QTableWidgetItem(offset))
            self.table.setItem(row, 2, QTableWidgetItem(time_val))
            self.table.setItem(row, 3, QTableWidgetItem('0.0'))

    def _add_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        name_item = QTableWidgetItem(f'point-{row:02d}')
        self.table.setItem(row, 0, name_item)
        spacing = self.spacing_spin.value()
        offset_val = row * spacing if self.use_spacing_chk.isChecked() else 0.0
        self.table.setItem(row, 1, QTableWidgetItem(f'{offset_val:.2f}'))
        self.table.setItem(row, 2, QTableWidgetItem('0.0'))
        self.table.setItem(row, 3, QTableWidgetItem('0.0'))

    def _del_row(self):
        rows = sorted(set(idx.row() for idx in self.table.selectedIndexes()), reverse=True)
        for row in rows:
            self.table.removeRow(row)

    def _get_data(self):
        """Extract (names, offsets, times, elevations) from single-direction table."""
        names, offsets, times, elevations = [], [], [], []
        spacing = self.spacing_spin.value()
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 0)
            off_item = self.table.item(row, 1)
            time_item = self.table.item(row, 2)
            elev_item = self.table.item(row, 3)
            if not all([name_item, off_item, time_item]):
                continue
            try:
                names.append(name_item.text())
                if self.use_spacing_chk.isChecked():
                    offsets.append(row * spacing)
                else:
                    offsets.append(float(off_item.text()))
                times.append(float(time_item.text()))
                elev = float(elev_item.text()) if elev_item else 0.0
                elevations.append(elev)
            except ValueError:
                continue
        return names, np.array(offsets), np.array(times), np.array(elevations)

    # ------------------------------------------------------------------
    # Data loading — Two directions (TAP/TBP)
    # ------------------------------------------------------------------

    def _load_tap_picks(self):
        """Load forward shot picks from canvas into TAP table."""
        self._load_picks_into_table(self.tap_table)

    def _load_tbp_picks(self):
        """Load backward shot picks from canvas into TBP table."""
        self._load_picks_into_table(self.tbp_table)

    def _load_picks_into_table(self, table):
        import core.actions as actions
        picks = actions.get_all_picks(self._canvas)
        if not picks:
            QMessageBox.information(self, 'Load', 'No picks found. Pick arrival times first.')
            return

        table.setRowCount(len(picks))
        for row, (tidx, name, ptime) in enumerate(picks):
            name_item = QTableWidgetItem(name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            time_item = QTableWidgetItem(f'{ptime:.6f}')
            table.setItem(row, 0, name_item)
            table.setItem(row, 1, time_item)
            table.setItem(row, 2, QTableWidgetItem('0.0'))

    def _load_tap_json(self):
        self._load_json_into_table(self.tap_table, 'TAP')

    def _load_tbp_json(self):
        self._load_json_into_table(self.tbp_table, 'TBP')

    def _load_json_into_table(self, table, label):
        """Load arrival times from JSON file (plugin format)."""
        fnm, _ = QFileDialog.getOpenFileName(
            self, f'Open {label} JSON', '', 'JSON files (*.json);;All files (*)'
        )
        if not fnm:
            return

        try:
            with open(fnm) as f:
                data = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to load JSON:\n{e}')
            return

        if 'pick' not in data:
            QMessageBox.warning(self, 'Warning', 'No "pick" key found in JSON file.')
            return

        picks = np.array(data['pick'], dtype=np.double)
        if picks.ndim == 2:
            times = picks[:, 1] if picks.shape[1] >= 2 else picks[:, 0]
        else:
            times = picks

        table.setRowCount(len(times))
        for row, t in enumerate(times):
            name_item = QTableWidgetItem(f'{label}-{row:02d}')
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            time_item = QTableWidgetItem(f'{float(t):.6f}')
            table.setItem(row, 0, name_item)
            table.setItem(row, 1, time_item)
            table.setItem(row, 2, QTableWidgetItem('0.0'))

    def _load_dat_into_table(self, table, label):
        """Load arrival times from a .dat file (same format as picking export) into a TAP/TBP table."""
        fnm, _ = QFileDialog.getOpenFileName(
            self, f'Open {label} DAT File', '', 'DAT files (*.dat);;All files (*)'
        )
        if not fnm:
            return

        rows = []
        with open(fnm) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split()
                # Support picking export format: trace_index trace_name offset_m arrival_time_s
                if len(parts) >= 4:
                    rows.append((parts[1], parts[3]))
                # Support simpler format: trace_name arrival_time_s
                elif len(parts) >= 2:
                    rows.append((parts[0], parts[-1]))

        if not rows:
            QMessageBox.warning(self, 'Load', f'No data found in {label} .dat file.')
            return

        table.setRowCount(len(rows))
        for row, (name, time_val) in enumerate(rows):
            name_item = QTableWidgetItem(name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            time_item = QTableWidgetItem(time_val)
            table.setItem(row, 0, name_item)
            table.setItem(row, 1, time_item)
            table.setItem(row, 2, QTableWidgetItem('0.0'))

    def _add_table_row(self, table):
        row = table.rowCount()
        table.insertRow(row)
        name_item = QTableWidgetItem(f'point-{row:02d}')
        table.setItem(row, 0, name_item)
        table.setItem(row, 1, QTableWidgetItem('0.0'))
        table.setItem(row, 2, QTableWidgetItem('0.0'))

    def _get_two_dir_data(self):
        """Extract TAP and TBP times and elevations from the two-direction tables."""
        tap_times = []
        tbp_times = []
        elevations = []

        for row in range(self.tap_table.rowCount()):
            item = self.tap_table.item(row, 1)
            elev_item = self.tap_table.item(row, 2)
            if item:
                try:
                    tap_times.append(float(item.text()))
                    elev = float(elev_item.text()) if elev_item else 0.0
                    elevations.append(elev)
                except ValueError:
                    continue

        for row in range(self.tbp_table.rowCount()):
            item = self.tbp_table.item(row, 1)
            if item:
                try:
                    tbp_times.append(float(item.text()))
                except ValueError:
                    continue

        return np.array(tap_times), np.array(tbp_times), np.array(elevations)

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def _analyze(self):
        mode = self.mode_combo.currentIndex()

        if mode == 0:
            self._analyze_single()
        else:
            self._analyze_two_dir()

    def _analyze_single(self):
        names, offsets, times, elevations = self._get_data()

        if len(offsets) < 3:
            QMessageBox.information(self, 'Analysis',
                                    'Need at least 3 data points to analyze.')
            return

        if np.ptp(offsets) < 1e-10:
            QMessageBox.warning(
                self, 'Missing Offsets',
                'All offsets are 0.0 — the Hagiwara method requires source-receiver '
                'distances (in metres).\n\n'
                'Please enable "Use uniform spacing" and set the spacing value, '
                'or edit the "Offset (m)" column in the Data tab.'
            )
            self.tabs.setCurrentIndex(0)
            return

        # Sort by offset
        order = np.argsort(offsets)
        offsets = offsets[order]
        times = times[order]
        names = [names[i] for i in order]

        # Determine crossover method
        method_idx = self.method_combo.currentIndex()
        if method_idx == 2:  # Manual
            cross_idx = self.cross_spin.value()
            cross_idx = cross_idx if cross_idx > 0 else None
            method = 'kneepoint'
        else:
            cross_idx = None
            method = 'kneepoint' if method_idx == 0 else 'mse'

        # Slope-intercept analysis
        si = slope_intercept_analysis(offsets, times, cross_idx, method=method)
        self._plot_travel_time(offsets, times, names, si)

        # Knee-point visualization
        if method == 'kneepoint' and cross_idx is None:
            _, kp_residuals = find_crossover_kneepoint(offsets, times)
            self._plot_kneepoint_single(offsets, times, si, kp_residuals)
        else:
            self._clear_kneepoint()

        # Hagiwara analysis
        hag = hagiwara_analysis(offsets, times, cross_idx, method=method)
        self._result = hag
        self._result_2dir = None
        self._plot_hagiwara(offsets, times, hag, elevations)

        self.tabs.setCurrentIndex(1)

    def _analyze_two_dir(self):
        tap_times, tbp_times, elevations = self._get_two_dir_data()

        if len(tap_times) < 3 or len(tbp_times) < 3:
            QMessageBox.information(
                self, 'Analysis',
                'Need at least 3 data points in both TAP and TBP to analyze.'
            )
            return

        if len(tap_times) != len(tbp_times):
            QMessageBox.warning(
                self, 'Data Mismatch',
                f'TAP has {len(tap_times)} points, TBP has {len(tbp_times)} points.\n'
                'Both directions should have the same number of geophones.'
            )
            return

        spacing = self.spacing_spin.value()

        # Determine crossover method
        method_idx = self.method_combo.currentIndex()
        if method_idx == 2:  # Manual
            cross_fwd = self.cross_fwd_spin.value()
            cross_fwd = cross_fwd if cross_fwd > 0 else None
            cross_bwd = self.cross_bwd_spin.value()
            cross_bwd = cross_bwd if cross_bwd > 0 else None
            method = 'kneepoint'  # fallback if manual index is 0
        else:
            cross_fwd = None
            cross_bwd = None
            method = 'kneepoint' if method_idx == 0 else 'mse'

        # Run two-direction analysis
        res = hagiwara_two_direction(tap_times, tbp_times, None, spacing,
                                     method=method,
                                     cross_idx_forward=cross_fwd,
                                     cross_idx_backward=cross_bwd)
        self._result_2dir = res
        self._result = None

        # Plot travel-time curve (two directions)
        self._plot_travel_time_2dir(res)

        # Plot knee-point analysis (both directions)
        self._plot_kneepoint_2dir(res)

        # Plot Hagiwara results
        self._plot_hagiwara_2dir(res, elevations)

        self.tabs.setCurrentIndex(1)

    # ------------------------------------------------------------------
    # Plotting — Single direction
    # ------------------------------------------------------------------

    def _plot_travel_time(self, offsets, times, names, si):
        ax = self.ax_tt
        ax.clear()
        ax.set_facecolor('#ffffff')

        ax.scatter(offsets, times * 1000, color='#0077cc', s=40, zorder=5, label='Picks')

        # Direct wave fit line
        s1, i1, r2_1 = si['direct']
        cidx = si['crossover_idx']
        x_direct = np.linspace(offsets[0], offsets[cidx], 100)
        ax.plot(x_direct, (s1 * x_direct + i1) * 1000,
                color='#228833', linewidth=2, linestyle='--',
                label=f'Direct: V={si["v_direct"]:.1f} m/s, R\u00b2={r2_1:.4f}')

        # Refracted wave fit line
        if si['refracted'] is not None:
            s2, i2, r2_2 = si['refracted']
            x_refr = np.linspace(offsets[cidx], offsets[-1], 100)
            ax.plot(x_refr, (s2 * x_refr + i2) * 1000,
                    color='#cc2222', linewidth=2, linestyle='--',
                    label=f'Refracted: V={si["v_refracted"]:.1f} m/s, R\u00b2={r2_2:.4f}')

            ax.axvline(si['crossover_distance'], color='#888888',
                       linestyle=':', linewidth=1,
                       label=f'Crossover: {si["crossover_distance"]:.1f} m')

        ax.set_xlabel('Offset (m)', fontsize=10, color='#2c5f7a')
        ax.set_ylabel('Arrival Time (ms)', fontsize=10, color='#2c5f7a')
        ax.set_title('Travel-Time Curve \u2014 Slope-Intercept Analysis', fontsize=11, color='#2c3e50')
        ax.legend(fontsize=8, loc='upper left')
        ax.tick_params(colors='#667788')
        for spine in ax.spines.values():
            spine.set_edgecolor('#c8d0dc')
        ax.grid(True, color='#e0e8f0', linewidth=0.5, linestyle='--')

        self.fig_tt.tight_layout()
        self.canvas_tt.draw()

        # Info text
        info = f'<b>Direct Wave:</b> V1 = {si["v_direct"]:.2f} m/s, '
        info += f'slope = {s1:.6f} s/m, R\u00b2 = {r2_1:.4f}<br>'
        if si['refracted']:
            s2, i2, r2_2 = si['refracted']
            info += f'<b>Refracted Wave:</b> V2 = {si["v_refracted"]:.2f} m/s, '
            info += f'slope = {s2:.6f} s/m, R\u00b2 = {r2_2:.4f}<br>'
            info += f'<b>Crossover Distance:</b> {si["crossover_distance"]:.2f} m '
            info += f'(index {si["crossover_idx"]})<br>'
        else:
            info += '<b>No refracted wave segment detected.</b><br>'
        self.tt_info.setText(info)

        # Store data for interactive knee-point selection
        self._tt_offsets = offsets
        self._tt_times = times

        # Connect click handler
        if self._tt_click_cid is not None:
            self.canvas_tt.mpl_disconnect(self._tt_click_cid)
        self._tt_click_cid = self.canvas_tt.mpl_connect(
            'button_press_event', self._on_tt_click_single
        )
        self.tt_click_label.setText(
            '\U0001f4a1 Click on a data point to set the knee-point')

    def _plot_kneepoint_single(self, offsets, times, si, kp_residuals):
        """Plot knee-point residual analysis for single direction."""
        for ax in self.ax_knee:
            ax.clear()
            ax.set_facecolor('#ffffff')

        if not kp_residuals or len(kp_residuals) < 2:
            for ax in self.ax_knee:
                ax.text(0.5, 0.5, 'Knee-point analysis not available.',
                        ha='center', va='center', fontsize=11, color='#888')
                ax.set_title('Knee-Point', fontsize=10)
            self.fig_knee.tight_layout()
            self.canvas_knee.draw()
            self.knee_info.setText('')
            return

        res = np.array(kp_residuals)
        cidx = si['crossover_idx']

        # Left plot: detrended residual curve
        ax1 = self.ax_knee[0]
        x_idx = np.arange(3, 3 + len(res))
        ax1.plot(x_idx, res, '-o', color='#0077cc', markersize=4, linewidth=1.5,
                 label='Detrended Residuals')

        # Mark knee point
        knee_local = np.argmin(res)
        knee_geophone = knee_local + 3
        ax1.plot(knee_geophone, res[knee_local], 's', color='#cc2222',
                 markersize=10, zorder=5, label=f'Knee point (index {cidx})')
        ax1.axvline(knee_geophone, color='#cc2222', linestyle=':', linewidth=1, alpha=0.5)

        ax1.set_xlabel('Number of Points in Fit', fontsize=9, color='#2c5f7a')
        ax1.set_ylabel('Detrended Residual', fontsize=9, color='#2c5f7a')
        ax1.set_title('Knee-Point Detection \u2014 Residual Curve', fontsize=10, color='#2c3e50')
        ax1.legend(fontsize=8)
        ax1.tick_params(colors='#667788')
        for spine in ax1.spines.values():
            spine.set_edgecolor('#c8d0dc')
        ax1.grid(True, color='#e0e8f0', linewidth=0.5, linestyle='--')

        # Right plot: travel-time with classification
        ax2 = self.ax_knee[1]
        ax2.scatter(offsets[:cidx + 1], times[:cidx + 1] * 1000,
                    color='#228833', s=50, zorder=5, label='Direct Wave', marker='o')
        if cidx < len(offsets) - 1:
            ax2.scatter(offsets[cidx:], times[cidx:] * 1000,
                        color='#cc2222', s=50, zorder=5, label='Refracted Wave', marker='^')

        ax2.axvline(offsets[cidx], color='#888888', linestyle=':', linewidth=1.5,
                    label=f'Knee @ {offsets[cidx]:.1f} m')

        ax2.set_xlabel('Offset (m)', fontsize=9, color='#2c5f7a')
        ax2.set_ylabel('Arrival Time (ms)', fontsize=9, color='#2c5f7a')
        ax2.set_title('Wave Classification by Knee-Point', fontsize=10, color='#2c3e50')
        ax2.legend(fontsize=8)
        ax2.tick_params(colors='#667788')
        for spine in ax2.spines.values():
            spine.set_edgecolor('#c8d0dc')
        ax2.grid(True, color='#e0e8f0', linewidth=0.5, linestyle='--')

        self.fig_knee.tight_layout()
        self.canvas_knee.draw()

        info = f'<b>Knee-Point Index:</b> {cidx} '
        info += f'(offset = {offsets[cidx]:.2f} m)<br>'
        info += f'<b>Direct wave points:</b> 0 to {cidx} ({cidx + 1} points)<br>'
        info += f'<b>Refracted wave points:</b> {cidx} to {len(offsets) - 1} '
        info += f'({len(offsets) - cidx} points)<br>'
        self.knee_info.setText(info)

    def _clear_kneepoint(self):
        for ax in self.ax_knee:
            ax.clear()
            ax.set_facecolor('#ffffff')
            ax.text(0.5, 0.5, 'Knee-point analysis only available\nwith Auto (Knee-Point) method.',
                    ha='center', va='center', fontsize=11, color='#888888',
                    transform=ax.transAxes)
        self.fig_knee.tight_layout()
        self.canvas_knee.draw()
        self.knee_info.setText('')

    def _plot_hagiwara(self, offsets, times, hag, elevations=None):
        for ax in self.ax_hag:
            ax.clear()
            ax.set_facecolor('#ffffff')

        # Left plot: travel-time with fitted lines
        ax1 = self.ax_hag[0]
        ax1.scatter(offsets, times * 1000, color='#0077cc', s=30, zorder=5)

        si = hag['slope_intercept']
        s1, i1, _ = si['direct']
        cidx = si['crossover_idx']
        x_d = np.linspace(offsets[0], offsets[cidx], 100)
        ax1.plot(x_d, (s1 * x_d + i1) * 1000, color='#228833', linewidth=2,
                 label=f'V1={hag["v1"]:.0f} m/s')

        if si['refracted']:
            s2, i2, _ = si['refracted']
            x_r = np.linspace(offsets[cidx], offsets[-1], 100)
            ax1.plot(x_r, (s2 * x_r + i2) * 1000, color='#cc2222', linewidth=2,
                     label=f'V2={hag["v2"]:.0f} m/s')

        ax1.set_xlabel('Offset (m)', fontsize=9, color='#2c5f7a')
        ax1.set_ylabel('Time (ms)', fontsize=9, color='#2c5f7a')
        ax1.set_title('Travel-Time Curve', fontsize=10, color='#2c3e50')
        ax1.legend(fontsize=8)
        ax1.tick_params(colors='#667788')
        for spine in ax1.spines.values():
            spine.set_edgecolor('#c8d0dc')
        ax1.grid(True, color='#e0e8f0', linewidth=0.5, linestyle='--')

        # Right plot: depth profile (subsurface cross-section)
        ax2 = self.ax_hag[1]
        if hag['h1'] is not None and hag['depth_profile']:
            dp = hag['depth_profile']
            dp_x = np.array([p[0] for p in dp])
            dp_z = np.array([p[1] for p in dp])

            # Compute surface heights from elevation angles (degrees)
            if elevations is not None and len(elevations) == len(offsets) and np.any(elevations != 0):
                surface = self._compute_surface_heights(offsets, elevations)
                surf_at_dp = np.interp(dp_x, offsets, surface)
            else:
                surf_at_dp = np.zeros(len(dp_x))

            # Interface elevation = surface_height - depth
            iface_elev = surf_at_dp - dp_z

            # Smooth curves using CubicSpline
            smooth_x = np.linspace(dp_x[0], dp_x[-1], 200)
            if len(dp_x) >= 4:
                cs_iface = CubicSpline(dp_x, iface_elev)
                smooth_iface = cs_iface(smooth_x)
            elif len(dp_x) >= 2:
                smooth_iface = np.interp(smooth_x, dp_x, iface_elev)
            else:
                smooth_x = dp_x
                smooth_iface = iface_elev

            # Smooth surface
            if np.any(surf_at_dp != 0) and len(dp_x) >= 4:
                cs_surf = CubicSpline(dp_x, surf_at_dp)
                smooth_surf = cs_surf(smooth_x)
            elif np.any(surf_at_dp != 0) and len(dp_x) >= 2:
                smooth_surf = np.interp(smooth_x, dp_x, surf_at_dp)
            else:
                smooth_surf = np.zeros(len(smooth_x))

            y_top = max(float(np.max(smooth_surf)), 0) + 0.5
            y_bottom = min(float(np.min(smooth_iface)), -hag['h1']) - hag['h1'] * 0.4

            # Fill layers
            ax2.fill_between(smooth_x, smooth_surf, smooth_iface,
                             color='#d4e6f1', alpha=0.4, label='_nolegend_')
            ax2.fill_between(smooth_x, smooth_iface, y_bottom,
                             color='#f5e6cc', alpha=0.4, label='_nolegend_')

            # Plot smooth interface curve
            ax2.plot(smooth_x, smooth_iface, color='#cc2222', linewidth=2,
                     label='Interface')
            # Plot data points on interface
            ax2.plot(dp_x, iface_elev, 'o', color='#cc2222', markersize=4,
                     zorder=5, label='_nolegend_')
            # Plot h1 reference line
            avg_surf = float(np.mean(surf_at_dp))
            ax2.axhline(avg_surf - hag['h1'], color='#228833', linestyle='--',
                        linewidth=1.5, label=f'h1 = {hag["h1"]:.2f} m')
            # Plot surface
            ax2.plot(smooth_x, smooth_surf, color='#444444', linewidth=1.5,
                     label='Surface')

            # Layer labels
            mid_x = (dp_x[0] + dp_x[-1]) / 2
            avg_iface = float(np.mean(smooth_iface))
            avg_s = float(np.mean(smooth_surf))
            ax2.text(mid_x, (avg_s + avg_iface) / 2,
                     f'Layer 1\nV1 = {hag["v1"]:.0f} m/s',
                     ha='center', va='center', fontsize=9, color='#228833',
                     bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
            layer2_y = avg_iface + (y_bottom - avg_iface) * 0.4
            ax2.text(mid_x, layer2_y,
                     f'Layer 2\nV2 = {hag["v2"]:.0f} m/s',
                     ha='center', va='center', fontsize=9, color='#cc2222',
                     bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

            ax2.set_ylim(y_bottom, y_top)
            ax2.set_xlim(dp_x[0], dp_x[-1])
            ax2.set_xlabel('Offset (m)', fontsize=9, color='#2c5f7a')
            ax2.set_ylabel('Elevation (m)', fontsize=9, color='#2c5f7a')
            ax2.set_title('Subsurface Model (Hagiwara)', fontsize=10, color='#2c3e50')
            ax2.legend(fontsize=8, loc='lower right')
            ax2.tick_params(colors='#667788')
            for spine in ax2.spines.values():
                spine.set_edgecolor('#c8d0dc')
            ax2.grid(True, color='#e0e8f0', linewidth=0.5, linestyle='--')
        else:
            ax2.text(0.5, 0.5, 'Cannot compute depth model.\nV2 must be > V1.',
                     ha='center', va='center', fontsize=11, color='#cc2222',
                     transform=ax2.transAxes)
            ax2.set_title('Subsurface Model', fontsize=10)

        self.fig_hag.tight_layout()
        self.canvas_hag.draw()

        # Info text
        info = '<b>Hagiwara Analysis Results:</b><br>'
        info += f'V1 (Layer 1 velocity): {hag["v1"]:.2f} m/s<br>'
        if hag['v2']:
            info += f'V2 (Layer 2 velocity): {hag["v2"]:.2f} m/s<br>'
        if hag['h1'] is not None:
            info += f'h1 (Layer 1 thickness): {hag["h1"]:.2f} m<br>'
        if hag['intercept_time'] is not None:
            info += f'Intercept time (ti): {hag["intercept_time"] * 1000:.4f} ms<br>'
        if hag['critical_angle_deg'] is not None:
            info += f'Critical angle (ic): {hag["critical_angle_deg"]:.2f}\u00b0<br>'
        info += f'Crossover distance: {hag["crossover_distance"]:.2f} m<br>'
        self.hag_info.setText(info)

    # ------------------------------------------------------------------
    # Plotting — Two directions
    # ------------------------------------------------------------------

    def _plot_travel_time_2dir(self, res):
        ax = self.ax_tt
        ax.clear()
        ax.set_facecolor('#ffffff')
        # ax.clear() destroys old artists — reset refs to avoid stale Remove() errors
        self._knee_artists_fwd = []
        self._knee_artists_bwd = []

        pos = np.array(res['positions'])
        tap = np.array(res['tap'])
        tbp = np.array(res['tbp'])
        tbp_flipped = np.flip(tbp)

        # Plot data points
        ax.plot(pos[1:], tap[1:] * 1000, '*', color='#0077cc', markersize=8,
                label='TAP (forward)')
        ax.plot(pos[1:], tbp_flipped[1:] * 1000, '.', color='#cc6600', markersize=8,
                label='TBP (backward)')

        # Direct wave fits
        ka = res['knee_forward']
        kb = res['knee_backward']
        nd = len(pos)

        koefa = res['forward_coeff']
        koefb = res['backward_coeff']
        t_ap = np.polyval(koefa, pos)
        t_bp = np.polyval(koefb, pos)

        ax.plot(pos[1:ka + 1], t_ap[1:ka + 1] * 1000, color='#228833', linewidth=2,
                label=f'Direct fwd (V={abs(1.0 / koefa[0]):.0f} m/s)' if abs(koefa[0]) > 1e-15 else 'Direct fwd')
        ax.plot(pos[nd - kb:], np.flip(t_bp[:kb]) * 1000, color='#cc2222', linewidth=2,
                label=f'Direct bwd (V={abs(1.0 / koefb[0]):.0f} m/s)' if abs(koefb[0]) > 1e-15 else 'Direct bwd')

        # Refraction lines
        if res['refraction_forward_coeff'] != [0, 0]:
            koefha = res['refraction_forward_coeff']
            koefhb = res['refraction_backward_coeff']

            hx_start = ka + 1   # ka in refraction.py = kac + 1
            hx_end = nd - kb - 1  # kb in refraction.py = kbc + 1
            if hx_start < hx_end:
                hx = pos[hx_start:hx_end]
                hap = res['refraction_tap']
                hbp = res['refraction_tbp']

                ax.plot(hx, np.array(hap) * 1000, 's', color='#228833',
                        markersize=5, label="T'ap (fwd refraction)")
                ax.plot(hx, np.array(hbp) * 1000, 's', color='#cc2222',
                        markersize=5, label="T'bp (bwd refraction)")

                th_ap = np.polyval(koefha, pos)
                th_bp = np.polyval(koefhb, pos)
                ax.plot(pos[1:], th_ap[1:] * 1000, '--', color='#228833',
                        linewidth=1, alpha=0.6)
                ax.plot(pos[1:], th_bp[1:] * 1000, '--', color='#cc2222',
                        linewidth=1, alpha=0.6)

        ax.set_xlabel('Position (m)', fontsize=10, color='#2c5f7a')
        ax.set_ylabel('Arrival Time (ms)', fontsize=10, color='#2c5f7a')
        ax.set_title('Travel-Time Curve \u2014 Two-Direction Analysis', fontsize=11, color='#2c3e50')
        ax.legend(fontsize=7, loc='upper left')
        ax.tick_params(colors='#667788')
        for spine in ax.spines.values():
            spine.set_edgecolor('#c8d0dc')
        ax.grid(True, color='#e0e8f0', linewidth=0.5, linestyle='--')

        self.fig_tt.tight_layout()
        self.canvas_tt.draw()

        # Info
        info = f'<b>Forward (TAP):</b> V1_fwd = {abs(1.0 / koefa[0]):.2f} m/s, '
        info += f'knee at index {ka}<br>'
        info += f'<b>Backward (TBP):</b> V1_bwd = {abs(1.0 / koefb[0]):.2f} m/s, '
        info += f'knee at index {kb}<br>'
        info += f'<b>Average V1:</b> {res["v1"]:.2f} m/s<br>'
        info += f'<b>V2 (harmonic mean):</b> {res["v2"]:.2f} m/s<br>'
        self.tt_info.setText(info)

        # Store data for interactive knee-point selection
        self._tt_positions = pos
        self._tt_tap = tap
        self._tt_tbp = tbp_flipped

        # Connect click handler
        if self._tt_click_cid is not None:
            self.canvas_tt.mpl_disconnect(self._tt_click_cid)
        self._tt_click_cid = self.canvas_tt.mpl_connect(
            'button_press_event', self._on_tt_click_2dir
        )
        self.tt_click_label.setText(
            '\U0001f4a1 Click on a data point to set the knee-point')

    def _plot_kneepoint_2dir(self, res):
        """Plot knee-point residual analysis for both directions."""
        for ax in self.ax_knee:
            ax.clear()
            ax.set_facecolor('#ffffff')

        res_fwd = res.get('knee_residuals_forward', [])
        res_bwd = res.get('knee_residuals_backward', [])

        # Left: Forward knee-point
        ax1 = self.ax_knee[0]
        if res_fwd and len(res_fwd) >= 2:
            fwd = np.array(res_fwd)
            x_idx = np.arange(3, 3 + len(fwd))
            ax1.plot(x_idx, fwd, '-o', color='#0077cc', markersize=4, linewidth=1.5,
                     label='Detrended Residuals')
            knee_local = np.argmin(fwd)
            ax1.plot(knee_local + 3, fwd[knee_local], 's', color='#cc2222',
                     markersize=10, zorder=5,
                     label=f'Knee (index {res["knee_forward"]})')
            ax1.axvline(knee_local + 3, color='#cc2222', linestyle=':', linewidth=1, alpha=0.5)
            ax1.legend(fontsize=8)
        else:
            ax1.text(0.5, 0.5, 'No forward residuals', ha='center', va='center',
                     fontsize=11, color='#888')

        ax1.set_xlabel('Points in Fit', fontsize=9, color='#2c5f7a')
        ax1.set_ylabel('Detrended Residual', fontsize=9, color='#2c5f7a')
        ax1.set_title('Forward (TAP) Knee-Point', fontsize=10, color='#2c3e50')
        ax1.tick_params(colors='#667788')
        for spine in ax1.spines.values():
            spine.set_edgecolor('#c8d0dc')
        ax1.grid(True, color='#e0e8f0', linewidth=0.5, linestyle='--')

        # Right: Backward knee-point
        ax2 = self.ax_knee[1]
        if res_bwd and len(res_bwd) >= 2:
            bwd = np.array(res_bwd)
            x_idx = np.arange(3, 3 + len(bwd))
            ax2.plot(x_idx, bwd, '-o', color='#cc6600', markersize=4, linewidth=1.5,
                     label='Detrended Residuals')
            knee_local = np.argmin(bwd)
            ax2.plot(knee_local + 3, bwd[knee_local], 's', color='#cc2222',
                     markersize=10, zorder=5,
                     label=f'Knee (index {res["knee_backward"]})')
            ax2.axvline(knee_local + 3, color='#cc2222', linestyle=':', linewidth=1, alpha=0.5)
            ax2.legend(fontsize=8)
        else:
            ax2.text(0.5, 0.5, 'No backward residuals', ha='center', va='center',
                     fontsize=11, color='#888')

        ax2.set_xlabel('Points in Fit', fontsize=9, color='#2c5f7a')
        ax2.set_ylabel('Detrended Residual', fontsize=9, color='#2c5f7a')
        ax2.set_title('Backward (TBP) Knee-Point', fontsize=10, color='#2c3e50')
        ax2.tick_params(colors='#667788')
        for spine in ax2.spines.values():
            spine.set_edgecolor('#c8d0dc')
        ax2.grid(True, color='#e0e8f0', linewidth=0.5, linestyle='--')

        self.fig_knee.tight_layout()
        self.canvas_knee.draw()

        info = f'<b>Forward knee:</b> index {res["knee_forward"]}<br>'
        info += f'<b>Backward knee:</b> index {res["knee_backward"]}<br>'
        self.knee_info.setText(info)

    def _plot_hagiwara_2dir(self, res, elevations=None):
        for ax in self.ax_hag:
            ax.clear()
            ax.set_facecolor('#ffffff')

        v1 = res['v1']
        v2 = res['v2']
        xx = res.get('distance', [])
        hh = res.get('depth', [])

        # Left: travel-time with all fits
        ax1 = self.ax_hag[0]
        pos = np.array(res['positions'])
        tap = np.array(res['tap'])
        tbp = np.array(res['tbp'])
        tbp_flipped = np.flip(tbp)

        ax1.plot(pos[1:], tap[1:] * 1000, '*', color='#0077cc', markersize=6)
        ax1.plot(pos[1:], tbp_flipped[1:] * 1000, '.', color='#cc6600', markersize=6)

        ax1.set_xlabel('Position (m)', fontsize=9, color='#2c5f7a')
        ax1.set_ylabel('Time (ms)', fontsize=9, color='#2c5f7a')
        ax1.set_title(f'V1={v1:.0f} m/s, V2={v2:.0f} m/s', fontsize=10, color='#2c3e50')
        ax1.tick_params(colors='#667788')
        for spine in ax1.spines.values():
            spine.set_edgecolor('#c8d0dc')
        ax1.grid(True, color='#e0e8f0', linewidth=0.5, linestyle='--')

        # Right: depth profile (subsurface cross-section)
        ax2 = self.ax_hag[1]
        if xx and hh and len(xx) > 2:
            inner_xx = np.array(xx[1:-1], dtype=float)
            inner_hh = np.array(hh[1:-1], dtype=float)

            # Compute surface heights from elevation angles (degrees)
            if elevations is not None and len(elevations) > 0 and np.any(elevations != 0):
                # Pad elevations with 0 for the source position (prepended by refraction code)
                elev_full = np.insert(elevations, 0, 0.0) if len(elevations) < len(pos) else elevations
                surface = self._compute_surface_heights(pos, elev_full)
                offa = res.get('offset_forward', 0.0)
                pos_shifted = pos - offa
                surf_at_inner = np.interp(inner_xx, pos_shifted, surface)
            else:
                surf_at_inner = np.zeros(len(inner_xx))

            # Interface elevation = surface_height - depth
            iface_elev = surf_at_inner - inner_hh

            # Smooth curves using CubicSpline
            smooth_x = np.linspace(inner_xx[0], inner_xx[-1], 200)
            if len(inner_xx) >= 4:
                cs_iface = CubicSpline(inner_xx, iface_elev)
                smooth_iface = cs_iface(smooth_x)
            elif len(inner_xx) >= 2:
                smooth_iface = np.interp(smooth_x, inner_xx, iface_elev)
            else:
                smooth_x = inner_xx
                smooth_iface = iface_elev

            # Smooth surface
            if np.any(surf_at_inner != 0) and len(inner_xx) >= 4:
                cs_surf = CubicSpline(inner_xx, surf_at_inner)
                smooth_surf = cs_surf(smooth_x)
            elif np.any(surf_at_inner != 0) and len(inner_xx) >= 2:
                smooth_surf = np.interp(smooth_x, inner_xx, surf_at_inner)
            else:
                smooth_surf = np.zeros(len(smooth_x))

            avg_depth = float(np.mean(inner_hh))
            y_top = max(float(np.max(smooth_surf)), 0) + 0.5
            y_bottom = min(float(np.min(smooth_iface)), -avg_depth) - avg_depth * 0.4

            # Fill layers
            ax2.fill_between(smooth_x, smooth_surf, smooth_iface,
                             color='#d4e6f1', alpha=0.4, label='_nolegend_')
            ax2.fill_between(smooth_x, smooth_iface, y_bottom,
                             color='#f5e6cc', alpha=0.4, label='_nolegend_')

            # Plot smooth interface curve
            ax2.plot(smooth_x, smooth_iface, color='#cc2222',
                     linewidth=2, label='Interface')
            # Plot data points
            ax2.plot(inner_xx, iface_elev, 'o', color='#cc2222',
                     markersize=4, zorder=5, label='_nolegend_')
            # Plot surface
            ax2.plot(smooth_x, smooth_surf, color='#444444', linewidth=1.5,
                     label='Surface')

            if v1 > 0 and v2 > 0:
                mid_x = float(np.mean(inner_xx))
                avg_iface = float(np.mean(smooth_iface))
                avg_s = float(np.mean(smooth_surf))
                # Layer 1 label
                ax2.text(mid_x, (avg_s + avg_iface) / 2,
                         f'Layer 1\nV1 = {v1:.0f} m/s',
                         ha='center', va='center', fontsize=9, color='#228833',
                         bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
                # Layer 2 label
                layer2_y = avg_iface + (y_bottom - avg_iface) * 0.4
                ax2.text(mid_x, layer2_y,
                         f'Layer 2\nV2 = {v2:.0f} m/s',
                         ha='center', va='center', fontsize=9, color='#cc2222',
                         bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

            ax2.set_ylim(y_bottom, y_top)
            ax2.set_xlim(min(xx), max(xx))
            ax2.set_xlabel('Distance (m)', fontsize=9, color='#2c5f7a')
            ax2.set_ylabel('Elevation (m)', fontsize=9, color='#2c5f7a')
            ax2.set_title('Subsurface Model', fontsize=10, color='#2c3e50')
            ax2.legend(fontsize=8, loc='lower right')
            ax2.tick_params(colors='#667788')
            for spine in ax2.spines.values():
                spine.set_edgecolor('#c8d0dc')
            ax2.grid(True, color='#e0e8f0', linewidth=0.5, linestyle='--')
        else:
            error_msg = res.get('error', 'Cannot compute depth model.')
            ax2.text(0.5, 0.5, error_msg,
                     ha='center', va='center', fontsize=11, color='#cc2222',
                     transform=ax2.transAxes)
            ax2.set_title('Subsurface Model', fontsize=10)

        self.fig_hag.tight_layout()
        self.canvas_hag.draw()

        # Info
        info = '<b>Two-Direction Hagiwara Results:</b><br>'
        info += f'V1 (Layer 1, average): {v1:.2f} m/s<br>'
        info += f'V2 (Layer 2, harmonic mean): {v2:.2f} m/s<br>'
        if v1 > 0 and v2 > v1:
            cosi = res.get('cosine', 0)
            if cosi > 0:
                ic_deg = np.degrees(np.arccos(cosi))
                info += f'Critical angle: {ic_deg:.2f}\u00b0<br>'
        info += f'TAP knee index: {res["knee_forward"]}<br>'
        info += f'TBP knee index: {res["knee_backward"]}<br>'
        info += f'T_AB (total travel time): {res["tab"] * 1000:.4f} ms<br>'

        if xx and hh and len(hh) > 2:
            avg_depth = np.mean(hh[1:-1])
            info += f'Average layer 1 thickness: {avg_depth:.2f} m<br>'

        self.hag_info.setText(info)

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_surface_heights(offsets, elevations_deg):
        """Compute cumulative surface height profile from slope angles (degrees).

        Each elevations_deg[i] is the slope angle (degrees from horizontal)
        of the terrain arriving at point i from point i-1.
        A value of 0\u00b0 means flat terrain. Default is all zeros.

        Returns an array of heights (m) with heights[0] = 0.
        """
        offsets = np.asarray(offsets, dtype=float)
        elevations_deg = np.asarray(elevations_deg, dtype=float)
        n = min(len(offsets), len(elevations_deg))
        heights = np.zeros(n)
        for i in range(1, n):
            dx = offsets[i] - offsets[i - 1]
            slope_rad = np.radians(elevations_deg[i])
            heights[i] = heights[i - 1] + dx * np.tan(slope_rad)
        return heights

    def _on_tt_click_single(self, event):
        """Handle click on travel-time chart to select knee-point (single dir)."""
        if event.inaxes != self.ax_tt or event.button != 1:
            return
        if self._tt_offsets is None or self._tt_times is None:
            return

        offsets = self._tt_offsets
        times_ms = self._tt_times * 1000

        # Normalize to axes range for distance calculation
        x_range = np.ptp(offsets) if np.ptp(offsets) > 0 else 1.0
        y_range = np.ptp(times_ms) if np.ptp(times_ms) > 0 else 1.0

        dx = (offsets - event.xdata) / x_range
        dy = (times_ms - event.ydata) / y_range
        dists = dx ** 2 + dy ** 2
        nearest = int(np.argmin(dists))

        # Update controls
        self.method_combo.setCurrentIndex(2)  # Manual
        self.cross_spin.setValue(nearest)

        # Visual feedback: clear previous forward marker then highlight selected point
        for artist in self._knee_artists_fwd:
            artist.remove()
        self._knee_artists_fwd.clear()
        marker, = self.ax_tt.plot(offsets[nearest], times_ms[nearest], 'o',
                                  color='#ff4444', markersize=14, markerfacecolor='none',
                                  markeredgewidth=2.5, zorder=10)
        vline = self.ax_tt.axvline(offsets[nearest], color='#ff4444', linestyle='--',
                                   linewidth=1.5, alpha=0.6, zorder=8)
        self._knee_artists_fwd = [marker, vline]
        self.tt_click_label.setText(
            f'\u2705 Knee-point set to index {nearest} '
            f'(offset = {offsets[nearest]:.2f} m). '
            f'Press "Calculate" to update results.')
        self.canvas_tt.draw()

    def _on_tt_click_2dir(self, event):
        """Handle click on travel-time chart to select knee-point (two-dir)."""
        if event.inaxes != self.ax_tt or event.button != 1:
            return
        if self._tt_positions is None:
            return

        pos = self._tt_positions
        tap = self._tt_tap
        tbp = self._tt_tbp

        # Data as plotted: pos[1:] vs tap[1:]*1000, tbp[1:]*1000 (flipped)
        pos_data = pos[1:]
        tap_ms = tap[1:] * 1000
        tbp_ms = tbp[1:] * 1000

        x_range = np.ptp(pos_data) if np.ptp(pos_data) > 0 else 1.0
        all_times = np.concatenate([tap_ms, tbp_ms])
        y_range = np.ptp(all_times) if np.ptp(all_times) > 0 else 1.0

        # Distance to TAP points
        dx_t = (pos_data - event.xdata) / x_range
        dy_t = (tap_ms - event.ydata) / y_range
        dists_tap = dx_t ** 2 + dy_t ** 2

        # Distance to TBP points
        dx_b = (pos_data - event.xdata) / x_range
        dy_b = (tbp_ms - event.ydata) / y_range
        dists_tbp = dx_b ** 2 + dy_b ** 2

        nearest_tap = int(np.argmin(dists_tap))
        nearest_tbp = int(np.argmin(dists_tbp))

        self.method_combo.setCurrentIndex(2)  # Manual

        if dists_tap[nearest_tap] <= dists_tbp[nearest_tbp]:
            self.cross_fwd_spin.setValue(nearest_tap)
            direction = 'Forward (TAP)'
            idx = nearest_tap
            x_val = pos_data[nearest_tap]
            y_val = tap_ms[nearest_tap]
            # Clear only the forward marker
            for artist in self._knee_artists_fwd:
                artist.remove()
            self._knee_artists_fwd.clear()
            marker, = self.ax_tt.plot(x_val, y_val, 'o',
                                      color='#228833', markersize=14, markerfacecolor='none',
                                      markeredgewidth=2.5, zorder=10)
            vline = self.ax_tt.axvline(x_val, color='#228833', linestyle='--',
                                       linewidth=1.5, alpha=0.6, zorder=8)
            self._knee_artists_fwd = [marker, vline]
        else:
            # TBP is stored flipped; convert to backward index (from far end)
            n = len(pos_data) - 1
            bwd_idx = n - nearest_tbp
            self.cross_bwd_spin.setValue(bwd_idx)
            direction = 'Backward (TBP)'
            idx = nearest_tbp
            x_val = pos_data[nearest_tbp]
            y_val = tbp_ms[nearest_tbp]
            # Clear only the backward marker
            for artist in self._knee_artists_bwd:
                artist.remove()
            self._knee_artists_bwd.clear()
            marker, = self.ax_tt.plot(x_val, y_val, 'o',
                                      color='#ff4444', markersize=14, markerfacecolor='none',
                                      markeredgewidth=2.5, zorder=10)
            vline = self.ax_tt.axvline(x_val, color='#ff4444', linestyle='--',
                                       linewidth=1.5, alpha=0.6, zorder=8)
            self._knee_artists_bwd = [marker, vline]
        self.tt_click_label.setText(
            f'\u2705 {direction} knee-point set to index {idx} '
            f'(position = {x_val:.2f} m). '
            f'Press "Calculate" to update results.')
        self.canvas_tt.draw()

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def _export(self):
        if self._result is None and self._result_2dir is None:
            QMessageBox.information(self, 'Export', 'Run analysis first.')
            return

        fnm, _ = QFileDialog.getSaveFileName(
            self, 'Export Results', 'hagiwara_results.dat',
            'DAT files (*.dat);;JSON files (*.json);;All files (*)'
        )
        if not fnm:
            return

        if fnm.endswith('.json'):
            self._export_json(fnm)
        else:
            self._export_dat(fnm)

    def _export_dat(self, fnm):
        with open(fnm, 'w') as f:
            f.write('# TraceMax Hagiwara Refraction Analysis Results\n')
            f.write('#\n')

            if self._result_2dir:
                res = self._result_2dir
                f.write(f'# Mode: Two-Direction (TAP/TBP)\n')
                f.write(f'# V1 (m/s): {res["v1"]:.4f}\n')
                f.write(f'# V2 (m/s): {res["v2"]:.4f}\n')
                f.write(f'# Cosine: {res["cosine"]:.6f}\n')
                f.write(f'# Forward knee index: {res["knee_forward"]}\n')
                f.write(f'# Backward knee index: {res["knee_backward"]}\n')
                f.write(f'# T_AB (s): {res["tab"]:.6f}\n')
                f.write('#\n')
                xx = res.get('distance', [])
                hh = res.get('depth', [])
                if xx and hh:
                    f.write('# Depth profile:\n')
                    f.write('# distance_m  depth_m\n')
                    for x, h in zip(xx, hh):
                        f.write(f'{x:.4f}  {h:.4f}\n')
            else:
                hag = self._result
                si = hag['slope_intercept']
                f.write(f'# Mode: Single Direction\n')
                f.write(f'# V1 (m/s): {hag["v1"]:.4f}\n')
                if hag['v2']:
                    f.write(f'# V2 (m/s): {hag["v2"]:.4f}\n')
                if hag['h1'] is not None:
                    f.write(f'# h1 (m):   {hag["h1"]:.4f}\n')
                if hag['intercept_time'] is not None:
                    f.write(f'# ti (s):   {hag["intercept_time"]:.6f}\n')
                if hag['critical_angle_deg'] is not None:
                    f.write(f'# ic (deg): {hag["critical_angle_deg"]:.4f}\n')
                f.write(f'# Crossover distance (m): {hag["crossover_distance"]:.4f}\n')
                f.write('#\n')

                s1, i1, r2_1 = si['direct']
                f.write(f'# Direct:    slope={s1:.8f}  intercept={i1:.8f}  R2={r2_1:.6f}\n')
                if si['refracted']:
                    s2, i2, r2_2 = si['refracted']
                    f.write(f'# Refracted: slope={s2:.8f}  intercept={i2:.8f}  R2={r2_2:.6f}\n')

                f.write('#\n')
                if hag['depth_profile']:
                    f.write('# Depth profile:\n')
                    f.write('# offset_m  depth_m\n')
                    for off, depth in hag['depth_profile']:
                        f.write(f'{off:.4f}  {depth:.4f}\n')

        QMessageBox.information(self, 'Export', f'Results saved to\n{fnm}')

    def _export_json(self, fnm):
        if self._result_2dir:
            data = self._result_2dir
        else:
            hag = self._result
            data = {
                'v1': hag['v1'],
                'v2': hag['v2'],
                'h1': hag['h1'],
                'crossover_distance': hag['crossover_distance'],
                'intercept_time': hag['intercept_time'],
                'critical_angle_deg': hag['critical_angle_deg'],
                'depth_profile': hag['depth_profile'],
            }

        with open(fnm, 'w') as f:
            json.dump(data, f, indent=2, default=str)

    def _export_png(self):
        """Export all current figures to PNG files."""
        if self._result is None and self._result_2dir is None:
            QMessageBox.information(self, 'Export PNG', 'Run analysis first.')
            return

        fnm, _ = QFileDialog.getSaveFileName(
            self, 'Export Figures to PNG', 'hagiwara',
            'PNG files (*.png);;All files (*)'
        )
        if not fnm:
            return

        # Strip extension — we'll add suffixes
        base = os.path.splitext(fnm)[0]
        saved = []

        # Travel-time curve
        try:
            path = f'{base}_travel_time.png'
            self.fig_tt.savefig(path, dpi=200, bbox_inches='tight',
                                facecolor='#f4f6f9')
            saved.append(path)
        except Exception:
            pass

        # Knee-point analysis
        try:
            path = f'{base}_kneepoint.png'
            self.fig_knee.savefig(path, dpi=200, bbox_inches='tight',
                                  facecolor='#f4f6f9')
            saved.append(path)
        except Exception:
            pass

        # Hagiwara results (travel-time + subsurface model)
        try:
            path = f'{base}_hagiwara.png'
            self.fig_hag.savefig(path, dpi=200, bbox_inches='tight',
                                 facecolor='#f4f6f9')
            saved.append(path)
        except Exception:
            pass

        if saved:
            names = '\n'.join(os.path.basename(s) for s in saved)
            QMessageBox.information(
                self, 'Export PNG',
                f'Saved {len(saved)} figure(s):\n{names}'
            )
        else:
            QMessageBox.warning(self, 'Export PNG', 'No figures could be saved.')
