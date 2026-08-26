import numpy as np

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QMessageBox, QScrollArea, QWidget
)
from PyQt5.QtCore import Qt, QUrl

try:
    from PyQt5.QtWebKitWidgets import QWebView as _Browser
except ImportError:
    try:
        from PyQt5.QtWebEngineWidgets import QWebEngineView as _Browser
    except ImportError:
        _Browser = None


# ---------------------------------------------------------------------------
# Help browser
# ---------------------------------------------------------------------------

class helpDialog(QDialog):
    def __init__(self, master, docfile):
        super().__init__(master)
        self.resize(900, 600)
        self.docfile = docfile
        self._build()
        self.exec_()

    def _build(self):
        if _Browser is None:
            QMessageBox.critical(self, 'Help', 'No web browser backend found.')
            return
        lo = QVBoxLayout()
        web = _Browser(self)
        web.load(QUrl(self.docfile))
        close_btn = QPushButton('&Close')
        close_btn.clicked.connect(self.close)
        w = self.width() // 3
        close_btn.setStyleSheet(
            f'padding:15px;margin-left:{w}px;margin-right:{w}px;margin-top:20px;'
            'font-size:16px;font-weight:bold;color:teal;'
        )
        lo.addWidget(web)
        lo.addWidget(close_btn)
        self.setLayout(lo)


# ---------------------------------------------------------------------------
# FFT spectrum dialog
# ---------------------------------------------------------------------------

class FFTDialog(QDialog):
    """Shows the frequency spectrum (FFT) of one or more selected traces."""

    def __init__(self, master, traces, timeaxis):
        super().__init__(master)
        self.setWindowTitle('FFT \u2014 Frequency Spectrum')
        self.resize(900, 560)
        self._traces = traces
        self._timeaxis = timeaxis
        self._log_mode = False
        self._build_ui()
        self._plot()

    def _build_ui(self):
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
        import matplotlib.pyplot as mpl
        mpl.style.use('default')

        self.fig, self.ax = mpl.subplots(facecolor='#f4f6f9')
        self.ax.set_facecolor('#ffffff')
        self.canvas = FigureCanvasQTAgg(self.fig)

        self.log_btn = QPushButton('Log Scale')
        self.log_btn.setCheckable(True)
        self.log_btn.toggled.connect(self._toggle_log)
        self.log_btn.setFixedWidth(110)

        close_btn = QPushButton('Close')
        close_btn.clicked.connect(self.close)
        close_btn.setFixedWidth(90)

        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel('Frequency spectrum of selected trace(s)'))
        ctrl.addStretch()
        ctrl.addWidget(self.log_btn)
        ctrl.addWidget(close_btn)

        lo = QVBoxLayout()
        lo.addWidget(self.canvas)
        lo.addLayout(ctrl)
        self.setLayout(lo)

        self.setStyleSheet(
            'background-color:#f4f6f9; color:#2c3e50;'
            'QPushButton{background:#0099cc;color:#ffffff;'
            'border:1px solid #007aaa;border-radius:5px;padding:4px 10px;}'
            'QPushButton:hover{background:#007aaa;}'
            'QLabel{color:#2c5f7a;}'
        )

    def _plot(self):
        self.ax.clear()
        self.ax.set_facecolor('#ffffff')

        ta = self._timeaxis
        if len(ta) < 4:
            self.ax.text(0.5, 0.5, 'Not enough data', ha='center',
                         color='#cc2222', transform=self.ax.transAxes)
            self.canvas.draw()
            return

        dt = (ta[-1] - ta[0]) / max(len(ta) - 1, 1)
        fs = 1.0 / dt if dt > 0 else 1.0
        nyq = fs / 2.0

        colors = ['#0077cc', '#cc2222', '#228833', '#cc8800', '#7722cc', '#cc5500']

        all_freqs = None
        for idx, trc in enumerate(self._traces):
            data = np.asarray(trc.vdata if len(trc.vdata) else trc.data, dtype=float)
            n = len(data)
            if n < 8:
                continue
            data -= data.mean()
            window = np.hanning(n)
            spectrum = np.abs(np.fft.rfft(data * window)) * 2.0 / n
            freqs = np.fft.rfftfreq(n, d=dt)

            clr = colors[idx % len(colors)]
            self.ax.plot(freqs, spectrum, color=clr, linewidth=0.9,
                         alpha=0.85, label=trc.name)

            if len(spectrum) > 5:
                for pk in np.argsort(spectrum)[-3:][::-1]:
                    if freqs[pk] < 1e-3:
                        continue
                    self.ax.axvline(freqs[pk], color=clr, linestyle='--',
                                    linewidth=0.6, alpha=0.4)
                    self.ax.annotate(
                        f'{freqs[pk]:.2f} Hz',
                        xy=(freqs[pk], spectrum[pk]),
                        xytext=(4, 4), textcoords='offset points',
                        fontsize=7, color=clr, alpha=0.85
                    )
            all_freqs = freqs

        if all_freqs is not None:
            self.ax.axvline(nyq, color='#aaaaaa', linestyle=':', linewidth=0.8)
            self.ax.text(nyq, self.ax.get_ylim()[1] * 0.95,
                         f' Nyquist\n {nyq:.1f} Hz', color='#aaaaaa', fontsize=7)

        self.ax.set_xlabel('Frequency (Hz)', fontsize=10, color='#2c5f7a')
        self.ax.set_ylabel('Amplitude', fontsize=10, color='#2c5f7a')
        self.ax.set_title('FFT Spectrum', fontsize=11, color='#2c3e50', pad=8)
        self.ax.tick_params(colors='#667788')
        for spine in self.ax.spines.values():
            spine.set_edgecolor('#c8d0dc')
        self.ax.grid(True, color='#e0e8f0', linewidth=0.5, linestyle='--')
        if len(self._traces) > 1:
            self.ax.legend(fontsize=8, facecolor='#f4f6f9',
                           edgecolor='#c8d0dc', labelcolor='#2c3e50')
        if self._log_mode:
            self.ax.set_yscale('log')

        self.fig.tight_layout()
        self.canvas.draw()

    def _toggle_log(self, checked):
        self._log_mode = checked
        self.log_btn.setText('Linear Scale' if checked else 'Log Scale')
        self._plot()


# ---------------------------------------------------------------------------
# Generic info dialog
# ---------------------------------------------------------------------------

class infoDialog(QDialog):
    def __init__(self, master, msg):
        super().__init__(master)
        self.resize(400, 400)
        lo = QVBoxLayout()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget(scroll)
        scroll.setWidget(content)
        inner = QVBoxLayout(content)
        lbl = QLabel(content)
        lbl.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        lbl.setWordWrap(True)
        lbl.setText(msg)
        inner.addWidget(lbl)
        close_btn = QPushButton('&Close')
        close_btn.clicked.connect(self.close)
        lo.addWidget(scroll)
        lo.addWidget(close_btn)
        self.setLayout(lo)
        self.exec_()
