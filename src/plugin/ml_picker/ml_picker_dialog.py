import os
import numpy as np

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLabel, QComboBox, QMessageBox,
    QGroupBox, QTabWidget, QWidget, QProgressBar,
    QCheckBox, QFileDialog, QSpinBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

from .ml_preprocess import preprocess_trace, WINDOW_LENGTH

_MODELS_DIR = os.path.join(os.path.dirname(__file__), 'models')


class _LSTMWorker(QThread):
    result_ready = pyqtSignal(list)
    error_raised = pyqtSignal(str)
    progress     = pyqtSignal(int)

    def __init__(self, traces, timeaxis, model_path, window_length, model_module='plugin.ml_picker.lstm_model'):
        super().__init__()
        self.traces        = traces
        self.timeaxis      = timeaxis
        self.model_path    = model_path
        self.window_length = window_length
        self.model_module  = model_module

    def run(self):
        try:
            import importlib
            mod = importlib.import_module(self.model_module)
            model, torch, device = mod.load_model(self.model_path)

            results = []
            n = len(self.traces)

            with torch.no_grad():
                for i, trc in enumerate(self.traces):
                    amplitude = np.asarray(trc.data, dtype=np.float64)
                    if len(amplitude) < 10:
                        results.append((i, None, None))
                        self.progress.emit(int((i + 1) / n * 100))
                        continue

                    trace_arr = preprocess_trace(amplitude, self.window_length)
                    x = (torch.tensor(trace_arr, dtype=torch.float32)
                         .unsqueeze(0).unsqueeze(-1).to(device))

                    pred_s, attn = model(x, return_attention=True)
                    pred_s = pred_s.item()
                    attn   = attn.squeeze(0).cpu().numpy()

                    results.append((i, pred_s, attn))
                    self.progress.emit(int((i + 1) / n * 100))

            self.result_ready.emit(results)

        except Exception as e:
            self.error_raised.emit(str(e))


class LSTMPickerTab(QWidget):

    def __init__(self, parent_dialog, title='BiLSTM', model_module='plugin.ml_picker.lstm_model', default_model_name='best_model_bilstm.pt'):
        super().__init__()
        self._dlg    = parent_dialog
        self._worker = None

        self.title        = title
        self.model_module = model_module
        self._model_path  = os.path.join(_MODELS_DIR, default_model_name)

        self._open_arrivals_after = False
        self._build_ui()

    def _build_ui(self):
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
        import matplotlib.pyplot as mpl
        mpl.style.use('default')

        main_lo = QVBoxLayout(self)

        # --- Parameters ---
        param_grp = QGroupBox('Parameters')
        form = QFormLayout()

        path_row = QHBoxLayout()
        self.model_path_lbl = QLabel(
            os.path.basename(self._model_path)
            if os.path.exists(self._model_path) else '(not found)'
        )
        browse_btn = QPushButton('Browse...')
        browse_btn.setFixedWidth(72)
        browse_btn.clicked.connect(self._browse_model)
        path_row.addWidget(self.model_path_lbl, stretch=1)
        path_row.addWidget(browse_btn)
        form.addRow('Model file:', path_row)

        self.window_spin = QSpinBox()
        self.window_spin.setRange(50, 2000)
        self.window_spin.setValue(WINDOW_LENGTH)
        self.window_spin.setSuffix(' samples')
        form.addRow('Window length:', self.window_spin)

        self.target_combo = QComboBox()
        self.target_combo.addItems(['All traces', 'Selected traces'])
        form.addRow('Apply to:', self.target_combo)

        self.preview_trace = QComboBox()
        form.addRow('Preview trace:', self.preview_trace)

        self.show_attn_chk = QCheckBox('Show attention weights')
        self.show_attn_chk.setChecked(True)
        form.addRow('', self.show_attn_chk)

        param_grp.setLayout(form)
        main_lo.addWidget(param_grp)

        # --- Matplotlib canvas ---
        self.fig, self.ax = mpl.subplots(2, 1, facecolor='#f4f6f9',
                                         gridspec_kw={'height_ratios': [3, 1]})
        self.mpl_canvas = FigureCanvasQTAgg(self.fig)
        main_lo.addWidget(self.mpl_canvas, stretch=1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_lo.addWidget(self.progress_bar)

        btn_lo = QHBoxLayout()
        preview_btn = QPushButton('Preview')
        preview_btn.clicked.connect(self._run_preview)
        self.apply_btn = QPushButton('Apply Picks')
        self.apply_btn.clicked.connect(self._run_picker)
        self.apply_arr_btn = QPushButton('Apply && Open Arrivals')
        self.apply_arr_btn.clicked.connect(self._run_and_open)
        close_btn = QPushButton('Close')
        close_btn.clicked.connect(lambda: self._dlg.close())

        btn_lo.addWidget(preview_btn)
        btn_lo.addWidget(self.apply_btn)
        btn_lo.addWidget(self.apply_arr_btn)
        btn_lo.addStretch()
        btn_lo.addWidget(close_btn)
        main_lo.addLayout(btn_lo)

    def populate_traces(self, traces):
        self.preview_trace.clear()
        for i, trc in enumerate(traces):
            self.preview_trace.addItem(f'{i}: {trc.name}', i)

    def _browse_model(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 'Select Model Checkpoint',
            os.path.dirname(self._model_path),
            'PyTorch model (*.pt *.pth);;All files (*)'
        )
        if path:
            self._model_path = path
            self.model_path_lbl.setText(os.path.basename(path))

    def _get_targets(self):
        canvas = self._dlg._canvas
        if self.target_combo.currentIndex() == 1 and canvas.selected:
            return canvas.selected
        return canvas.traces

    def _run_preview(self):
        canvas = self._dlg._canvas
        if not canvas.traces or not canvas.timeaxis:
            QMessageBox.information(self, 'Preview', 'Load a file first.')
            return
        if not os.path.exists(self._model_path):
            QMessageBox.warning(self, 'Model not found',
                                f'Model file not found:\n{self._model_path}')
            return

        idx = self.preview_trace.currentData()
        if idx is None or idx >= len(canvas.traces):
            return

        trc = canvas.traces[idx]

        try:
            import importlib
            mod = importlib.import_module(self.model_module)
            model, torch, device = mod.load_model(self._model_path)

            wl = self.window_spin.value()
            amplitude = np.asarray(trc.data, dtype=np.float64)
            trace_arr = preprocess_trace(amplitude, wl)

            with torch.no_grad():
                x = (torch.tensor(trace_arr, dtype=torch.float32)
                     .unsqueeze(0).unsqueeze(-1).to(device))
                pred_s, attn = model(x, return_attention=True)
                pred_s = pred_s.item()
                attn   = attn.squeeze(0).cpu().numpy()

            self._plot(trace_arr, attn, pred_s, trc.name)

        except Exception as e:
            QMessageBox.warning(self, 'Preview error', str(e))

    def _plot(self, trace_arr, attn, pred_s, name):
        wl = len(trace_arr)
        canvas = self._dlg._canvas

        ta = canvas.timeaxis
        if ta and len(ta) >= 2:
            total_dur = ta[-1] - ta[0]
            sr = len(ta) / total_dur if total_dur > 0 else 616.0
        else:
            sr = 616.0

        t_ms = np.arange(wl) / sr * 1000.0

        for ax in self.ax:
            ax.clear()
            ax.set_facecolor('#ffffff')

        self.ax[0].plot(t_ms, trace_arr, color='#0077cc', linewidth=0.6)
        self.ax[0].axvline(pred_s * 1000.0, color='#cc2222', linewidth=1.5,
                           linestyle='--', label=f'Pick: {pred_s*1000:.3f} ms')
        self.ax[0].set_ylabel('Amplitude (norm.)', fontsize=9, color='#2c5f7a')
        self.ax[0].set_title(f'{self.title} prediction: {name}', fontsize=10,
                             color='#2c3e50')
        self.ax[0].legend(fontsize=8)

        if self.show_attn_chk.isChecked() and attn is not None:
            self.ax[1].fill_between(t_ms, 0, attn, color='#F0A500', alpha=0.35,
                                    label='Attention')
            self.ax[1].set_ylabel('Attention weight', fontsize=8, color='#C07800')
            self.ax[1].tick_params(axis='y', labelsize=7, colors='#C07800')
            self.ax[1].set_ylim(0, attn.max() * 4 if attn.max() > 0 else 1)
            self.ax[1].legend(fontsize=7)

        self.ax[1].set_xlabel('Time (ms from trace start)', fontsize=9,
                              color='#2c5f7a')

        for ax in self.ax:
            ax.grid(True, color='#e0e8f0', linewidth=0.5, linestyle='--')
            ax.tick_params(colors='#667788')
            for spine in ax.spines.values():
                spine.set_edgecolor('#c8d0dc')

        self.fig.tight_layout()
        self.mpl_canvas.draw()

    def _run_picker(self, open_arrivals=False):
        canvas = self._dlg._canvas
        if not canvas.traces or not canvas.timeaxis:
            QMessageBox.information(self, f'{self.title} Picker', 'Load a file first.')
            return
        if not os.path.exists(self._model_path):
            QMessageBox.warning(self, 'Model not found',
                                f'Model file not found:\n{self._model_path}')
            return

        targets = self._get_targets()
        self._open_arrivals_after = open_arrivals

        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.apply_btn.setEnabled(False)
        self.apply_arr_btn.setEnabled(False)

        self._worker = _LSTMWorker(
            traces=targets,
            timeaxis=list(canvas.timeaxis),
            model_path=self._model_path,
            window_length=self.window_spin.value(),
            model_module=self.model_module
        )
        self._worker.progress.connect(self.progress_bar.setValue)
        self._worker.result_ready.connect(self._on_results)
        self._worker.error_raised.connect(self._on_error)
        self._worker.start()

    def _run_and_open(self):
        self._run_picker(open_arrivals=True)

    def _reset_buttons(self):
        self.progress_bar.setVisible(False)
        self.apply_btn.setEnabled(True)
        self.apply_arr_btn.setEnabled(True)

    def _on_error(self, msg):
        QMessageBox.warning(self, f'{self.title} Picker', msg)
        self._reset_buttons()

    def _on_results(self, results):
        canvas  = self._dlg._canvas
        ta      = canvas.timeaxis
        tmax    = ta[-1] - ta[0] if len(ta) >= 2 else 1.0
        n_samp  = len(ta)
        targets = self._get_targets()

        count = 0
        for local_idx, (_, pred_s, attn) in enumerate(results):
            if pred_s is None:
                continue

            trc = targets[local_idx]
            sample_idx = int(n_samp * pred_s / tmax) if tmax > 0 else 0
            sample_idx = max(0, min(sample_idx, n_samp - 1))

            trc.pickpoint = sample_idx
            trc.picktime  = pred_s
            count += 1

            if canvas.pick_function:
                tidx = canvas.traces.index(trc)
                canvas.pick_function((tidx, pred_s))

        if results and results[-1][1] is not None:
            last_trc = targets[len(results) - 1]
            amp = np.asarray(last_trc.data, dtype=np.float64)
            trace_arr = preprocess_trace(amp, self.window_spin.value())
            self._plot(trace_arr, results[-1][2], results[-1][1], last_trc.name)

        canvas.once = True
        canvas.repaint()
        self._reset_buttons()

        QMessageBox.information(self, f'{self.title} Picker',
                                f'Auto-picked {count} of {len(results)} traces.')

        if self._open_arrivals_after:
            self._dlg._win.show_arrival_dialog()


class MLPickerDialog(QDialog):

    def __init__(self, parent, canvas):
        super().__init__(parent)
        self.setWindowTitle('ML Auto-Picker')
        self.resize(900, 640)
        self._canvas = canvas
        self._win    = parent
        self._build_ui()
        self._populate_trace_lists()

    def _build_ui(self):
        main_lo = QVBoxLayout(self)

        self.tabs = QTabWidget()

        self.lstm_tab = LSTMPickerTab(
            self, title='BiLSTM',
            model_module='plugin.ml_picker.lstm_model',
            default_model_name='best_model_bilstm.pt'
        )
        self.tabs.addTab(self.lstm_tab, 'BiLSTM Picker')

        self.uni_lstm_tab = LSTMPickerTab(
            self, title='Uni-LSTM',
            model_module='plugin.ml_picker.lstm_model_unidirectional',
            default_model_name='best_model_unidirectional.pt'
        )
        self.tabs.addTab(self.uni_lstm_tab, 'Uni-LSTM Picker')

        placeholder = QWidget()
        ph_lo = QVBoxLayout(placeholder)
        ph_lo.setAlignment(Qt.AlignCenter)
        ph_lbl = QLabel('Transformer-based picker\n(not yet implemented)')
        ph_lbl.setAlignment(Qt.AlignCenter)
        ph_lo.addWidget(ph_lbl)
        self.tabs.addTab(placeholder, 'Transformer')

        main_lo.addWidget(self.tabs)

    def _populate_trace_lists(self):
        if self._canvas.traces:
            self.lstm_tab.populate_traces(self._canvas.traces)
            self.uni_lstm_tab.populate_traces(self._canvas.traces)
