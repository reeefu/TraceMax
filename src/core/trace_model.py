from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
import scipy.signal as sg
import numpy as np


class trace:
    def __init__(self, master, dat, geo=None, name='', color=None):
        self.name = name

        if geo is None:
            r = master.geometry()
            geo = (r.x(), r.y(), r.width(), r.height())

        self.setPosition(geo)

        self.scale = 1.0
        self.basescale = 1.0
        self.zoom = 500
        self.xpan = 0
        self.master = master
        self.datarange = (0, 0)
        self.tmax = 0
        self.data = dat
        self.vdata = dat
        self.zoomall = True
        self.invert = False
        self.autoscale = False
        self.threshold = 0
        self.autopan = True
        self.filter = False
        self.dirty = True
        self.stretch = False
        self.freq = (8.0, 25.0, 2)  # (low_hz, high_hz, order)
        self.selected = False
        self.highlight = False
        self.fillarea = False
        self.voffset = 0
        self.pickpoint = -1   # array index; negative means no pick
        self.picktime = 0.0

        self.color = color if color is not None else QColor(Qt.red)

    # ------------------------------------------------------------------
    # Pick
    # ------------------------------------------------------------------
    def set_pick(self, sample_index, time_value):
        """Set the pick point on this trace."""
        self.pickpoint = sample_index
        self.picktime = time_value

    # ------------------------------------------------------------------
    # Geometry
    # ------------------------------------------------------------------
    def setPosition(self, geo):
        self.pos = (geo[0], geo[1])   # x, y
        self.dim = (geo[2], geo[3])   # width, height
        self.base = geo[1] + geo[3] // 2

    # ------------------------------------------------------------------
    # Panning
    # ------------------------------------------------------------------
    def panshift(self, dx):
        self.xpan -= dx
        maxpan = len(self.data) - self.zoom
        self.autopan = False

        if self.xpan >= maxpan:
            self.xpan = maxpan
            self.autopan = True

        if self.xpan < 0:
            self.xpan = 0

    # ------------------------------------------------------------------
    # DSP — filtering
    # ------------------------------------------------------------------
    def filtering(self):
        """Apply digital filter to self.data.

        self.freq = (low_hz, high_hz, order[, filter_type])
        filter_type: 'butter' | 'cheby1' | 'bessel'  (default: 'butter')

        Mode:
          low_hz == 0        → lowpass  at high_hz
          high_hz >= nyquist → highpass at low_hz
          otherwise          → bandpass between low_hz and high_hz
        """
        vd = self.data
        if not self.tmax or len(self.data) < 20:
            return vd

        nyq = 0.5 * len(self.data) / self.tmax

        fl = min(self.freq[0], self.freq[1])
        fh = max(self.freq[0], self.freq[1])
        order = int(self.freq[2]) if len(self.freq) >= 3 else 2
        ftype = self.freq[3] if len(self.freq) >= 4 else 'butter'

        if abs(fh - fl) < 0.5 and fh > 0 and fl > 0:
            return vd  # band too narrow

        try:
            def _design(btype, Wn):
                if ftype == 'cheby1':
                    return sg.cheby1(order, 1.0, Wn, btype=btype, analog=False)
                elif ftype == 'bessel':
                    return sg.bessel(order, Wn, btype=btype, analog=False, norm='phase')
                else:
                    return sg.butter(order, Wn, btype=btype, analog=False)

            if fl <= 0:
                wb = min(fh / nyq, 0.999)
                b, a = _design('low', wb)
            elif fh >= nyq or fh <= 0:
                wa = max(fl / nyq, 0.001)
                b, a = _design('high', wa)
            else:
                wa = max(fl / nyq, 0.001)
                wb = min(fh / nyq, 0.999)
                if wa >= wb:
                    return vd
                b, a = _design('band', (wa, wb))

            vd = sg.filtfilt(b, a, self.data)

        except Exception as e:
            print(f'[filter error] {self.name}: {e}')
            vd = self.data

        return vd

    # ------------------------------------------------------------------
    # DSP — normalization
    # ------------------------------------------------------------------
    def normalize(self):
        """Remove DC offset, compute amplitude scale so trace fills its lane."""
        nd = len(self.data)
        if not nd:
            return

        avg = sum(self.data) / nd
        dmi = min(self.data)
        dma = max(self.data)
        self.datarange = (dmi - avg, dma - avg)

        for i in range(nd):
            self.data[i] -= avg

        ma = max(self.data)
        mi = min(self.data)

        amp = abs(ma - mi) > self.threshold

        if amp and mi < ma:
            ma = abs(ma)
            mi = abs(mi)
            self.scale = 0.5 * self.dim[1] / max(mi, ma)
        else:
            print(f'{self.name}: amplitude less than threshold')
            self.scale = 1.0

        self.dirty = True
        self.basescale = self.scale
