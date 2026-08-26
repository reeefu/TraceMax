import numpy as np

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLabel, QDoubleSpinBox, QSpinBox,
    QComboBox, QMessageBox, QGroupBox
)
from PyQt5.QtCore import Qt

from core.autopick import sta_lta_ratio, pick_first_break, ms_to_samples


class STALTADialog(QDialog):
    """STA/LTA auto-picker configuration and preview dialog."""

    def __init__(self, parent, canvas):
        super().__init__(parent)
        self.setWindowTitle('STA/LTA Auto-Picker')
        self.resize(900, 600)
        self._canvas = canvas
        self._win = parent
        self._build_ui()

    def _build_ui(self):
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
        import matplotlib.pyplot as mpl
        mpl.style.use('default')

        main_lo = QVBoxLayout()

        # --- Parameters ---
        param_grp = QGroupBox('Parameters')
        form = QFormLayout()

        self.sta_spin = QDoubleSpinBox()
        self.sta_spin.setRange(0.1, 500.0)
        self.sta_spin.setValue(5.0)
        self.sta_spin.setSuffix(' ms')
        self.sta_spin.setDecimals(1)
        form.addRow('STA Window:', self.sta_spin)

        self.lta_spin = QDoubleSpinBox()
        self.lta_spin.setRange(1.0, 5000.0)
        self.lta_spin.setValue(50.0)
        self.lta_spin.setSuffix(' ms')
        self.lta_spin.setDecimals(1)
        form.addRow('LTA Window:', self.lta_spin)

        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(1.0, 100.0)
        self.threshold_spin.setValue(3.0)
        self.threshold_spin.setDecimals(2)
        form.addRow('Threshold:', self.threshold_spin)

        self.target_combo = QComboBox()
        self.target_combo.addItems(['All traces', 'Selected traces'])
        form.addRow('Apply to:', self.target_combo)

        self.preview_trace = QComboBox()
        self._populate_trace_list()
        form.addRow('Preview trace:', self.preview_trace)

        param_grp.setLayout(form)
        main_lo.addWidget(param_grp)

        # --- Matplotlib canvas ---
        self.fig, self.ax = mpl.subplots(2, 1, facecolor='#f4f6f9', sharex=True)
        self.mpl_canvas = FigureCanvasQTAgg(self.fig)
        main_lo.addWidget(self.mpl_canvas, stretch=1)

        # --- Buttons ---
        btn_lo = QHBoxLayout()
        preview_btn = QPushButton('Preview')
        preview_btn.clicked.connect(self._preview)
        apply_btn = QPushButton('Apply Picks')
        apply_btn.clicked.connect(self._apply)
        apply_arr_btn = QPushButton('Apply && Open Arrivals')
        apply_arr_btn.clicked.connect(self._apply_and_open)
        close_btn = QPushButton('Close')
        close_btn.clicked.connect(self.close)

        btn_lo.addWidget(preview_btn)
        btn_lo.addWidget(apply_btn)
        btn_lo.addWidget(apply_arr_btn)
        btn_lo.addStretch()
        btn_lo.addWidget(close_btn)
        main_lo.addLayout(btn_lo)

        self.setLayout(main_lo)

    def _populate_trace_list(self):
        self.preview_trace.clear()
        for i, trc in enumerate(self._canvas.traces):
            self.preview_trace.addItem(f'{i}: {trc.name}', i)

    def _get_targets(self):
        if self.target_combo.currentIndex() == 1 and self._canvas.selected:
            return self._canvas.selected
        return self._canvas.traces

    def _get_trace_data(self, trc):
        """Return the data to analyze (filtered if filter is on)."""
        if trc.filter and len(trc.vdata) > 25:
            return np.asarray(trc.vdata, dtype=float)
        return np.asarray(trc.data, dtype=float)

    def _preview(self):
        idx = self.preview_trace.currentData()
        if idx is None or idx >= len(self._canvas.traces):
            return

        trc = self._canvas.traces[idx]
        data = self._get_trace_data(trc)
        ta = np.asarray(self._canvas.timeaxis, dtype=float)

        if len(data) < 20 or len(ta) < 20:
            QMessageBox.information(self, 'Preview', 'Not enough data to preview.')
            return

        nsta = ms_to_samples(self.sta_spin.value(), ta)
        nlta = ms_to_samples(self.lta_spin.value(), ta)
        threshold = self.threshold_spin.value()

        ratio = sta_lta_ratio(data, nsta, nlta)
        t0 = ta[0]
        trel = ta - t0

        for ax in self.ax:
            ax.clear()
            ax.set_facecolor('#ffffff')

        # Top: waveform
        self.ax[0].plot(trel[:len(data)], data, color='#0077cc', linewidth=0.6)
        self.ax[0].set_ylabel('Amplitude', fontsize=9, color='#2c5f7a')
        self.ax[0].set_title(f'Waveform: {trc.name}', fontsize=10, color='#2c3e50')

        fb = pick_first_break(data, ta, nsta, nlta, threshold)
        if fb:
            self.ax[0].axvline(fb[1], color='#cc2222', linewidth=1.5, linestyle='--',
                               label=f'Pick: {fb[1]:.4f} s')
            self.ax[0].legend(fontsize=8)

        # Bottom: STA/LTA ratio
        self.ax[1].plot(trel[:len(ratio)], ratio, color='#228833', linewidth=0.7)
        self.ax[1].axhline(threshold, color='#cc2222', linewidth=1, linestyle='--',
                           label=f'Threshold: {threshold}')
        self.ax[1].set_ylabel('STA/LTA Ratio', fontsize=9, color='#2c5f7a')
        self.ax[1].set_xlabel('Time (s)', fontsize=9, color='#2c5f7a')
        self.ax[1].set_title('STA/LTA Ratio', fontsize=10, color='#2c3e50')
        self.ax[1].legend(fontsize=8)

        for ax in self.ax:
            ax.grid(True, color='#e0e8f0', linewidth=0.5, linestyle='--')
            ax.tick_params(colors='#667788')
            for spine in ax.spines.values():
                spine.set_edgecolor('#c8d0dc')

        self.fig.tight_layout()
        self.mpl_canvas.draw()

    def _apply(self):
        targets = self._get_targets()
        ta = self._canvas.timeaxis

        if not ta or len(ta) < 20:
            QMessageBox.information(self, 'STA/LTA', 'Load a file first.')
            return

        nsta = ms_to_samples(self.sta_spin.value(), ta)
        nlta = ms_to_samples(self.lta_spin.value(), ta)
        threshold = self.threshold_spin.value()

        count = 0
        for trc in targets:
            data = self._get_trace_data(trc)
            result = pick_first_break(data, ta, nsta, nlta, threshold)
            if result:
                trc.pickpoint = result[0]
                trc.picktime = result[1]
                count += 1

                if self._canvas.pick_function:
                    tidx = self._canvas.traces.index(trc)
                    self._canvas.pick_function((tidx, result[1]))

        self._canvas.once = True
        self._canvas.repaint()

        QMessageBox.information(self, 'STA/LTA',
                                f'Auto-picked {count} of {len(targets)} traces.')

    def _apply_and_open(self):
        self._apply()
        self._win.show_arrival_dialog()
