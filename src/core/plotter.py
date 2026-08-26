from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtWidgets import QFrame, QToolTip
from PyQt5.QtGui import (
    QPainter, QColor, QFont, QPainterPath, QPen, QBrush, QPixmap, QPolygon
)

from core.trace_model import trace
import core.actions as actions
import numpy as np

color_map = ['red', 'darkRed', 'magenta', 'darkMagenta', 'green', 'darkGreen']


class plotter(QFrame):

    def __init__(self, master, geo=None, name=''):
        super(plotter, self).__init__(master)

        r = geo if geo else master.geometry()

        self.master = master
        self.move(r.x(), r.y())
        self.resize(r.width(), r.height())
        self.setStyleSheet('background-color: #ffffff;')

        self.traces = []
        self.timeaxis = []
        self.selected = []
        self.zoomall = False
        self.mx = 0
        self.my = 0
        self.running = False
        self.once = True
        self.pick_function = None
        self.indicator = (self.width() // 2, 0)
        self.show_indicator = False
        self.scrimg = QPixmap(self.width(), self.height())
        self.btn_decay = False
        self.drag = False
        self.roll = False
        self.setMouseTracking(True)
        self.onblock = False
        self.block = {}
        self.nstack = 0
        self.minbwidth = 2
        self.plotlimit = (0, 0)
        self._repaint_pending = False

        # Trace zoom/scroll state
        self.trace_view_count = 0    # 0 = show all, 1/3/5 = show N traces
        self.trace_view_offset = 0   # index of first visible trace

    # ------------------------------------------------------------------
    # Trace management
    # ------------------------------------------------------------------

    def arrangeTraces(self):
        lt = len(self.traces)
        if lt == 0:
            return

        if self.trace_view_count > 0 and self.trace_view_count < lt:
            # Only visible traces get real screen space
            visible_count = min(self.trace_view_count, lt)
            dw = self.height() - 30
            pw = dw / visible_count
            for i, trc in enumerate(self.traces):
                if i >= self.trace_view_offset and i < self.trace_view_offset + visible_count:
                    slot = i - self.trace_view_offset
                    trc.setPosition((0, slot * pw, self.width(), pw))
                    trc._visible = True
                else:
                    # Move off-screen
                    trc.setPosition((0, -9999, self.width(), 0))
                    trc._visible = False
        else:
            # Show all traces
            dw = self.height() - 30
            pw = dw / lt
            for i, trc in enumerate(self.traces):
                trc.setPosition((0, i * pw, self.width(), pw))
                trc._visible = True

    def get_visible_traces(self):
        """Return list of currently visible traces."""
        return [trc for trc in self.traces if getattr(trc, '_visible', True)]

    def set_trace_view(self, count, offset=0):
        """Set the trace zoom level and scroll offset.
        
        Args:
            count: Number of traces to show (0 = all)
            offset: Index of the first visible trace
        """
        lt = len(self.traces)
        self.trace_view_count = count
        if count > 0 and count < lt:
            self.trace_view_offset = max(0, min(offset, lt - count))
        else:
            self.trace_view_offset = 0
        self.arrangeTraces()
        self.once = True
        self.repaint()

    def addTrace(self, data, name):
        if not name:
            name = 'trace-%02d' % len(self.traces)

        tid = len(self.traces)
        self.traces.append(
            trace(self, data, geo=(0, 0, self.width(), 0), name=name,
                  color=QColor(color_map[tid % len(color_map)]))
        )
        self.arrangeTraces()
        self.repaint()
        return tid

    def updateTrace(self, tid, data, repaint=False):
        self.traces[tid].data = data
        if repaint:
            self.repaint()

    def changeBox(self, width, height):
        self.setGeometry(self.x(), self.y(), width, height)
        self.scrimg = QPixmap(width, height)
        self.once = True
        self.arrangeTraces()

    def run(self, stat):
        self.running = stat

    def _request_repaint(self):
        """Coalesce multiple repaint requests into a single paint cycle."""
        self.once = True
        if not self._repaint_pending:
            self._repaint_pending = True
            QTimer.singleShot(0, self._do_repaint)

    def _do_repaint(self):
        self._repaint_pending = False
        self.repaint()

    # ------------------------------------------------------------------
    # View helpers
    # ------------------------------------------------------------------

    def getTimeLimit(self):
        if not self.timeaxis or not self.traces[0].data:
            self.plotlimit = (0, 0)
            return (0, 0)
        t = self.plotlimit
        t0 = self.timeaxis[0]
        return (self.timeaxis[t[0]] - t0, self.timeaxis[t[1] - 1] - t0)

    def getData(self):
        dd = {'time': self.timeaxis}
        scl, flt, ofs, ptm = [], [], [], []
        for i, trc in enumerate(self.traces):
            key = 'channel-%02d' % i
            # Convert numpy arrays to plain lists for JSON serialization
            if hasattr(trc.data, 'tolist'):
                dd[key] = trc.data.tolist()
            else:
                dd[key] = list(trc.data)
            scl.append(trc.scale)
            flt.append(list(trc.freq))
            ofs.append(trc.voffset)
            ptm.append((i, trc.picktime))
        dd['scale'] = scl
        dd['offset'] = ofs
        dd['filter'] = flt
        dd['pick'] = ptm
        self.once = True
        self.repaint()
        return dd

    def assignData(self, data, stretch=False, auto=False):
        if 'time' not in data:
            return
        self.clear()
        self.timeaxis = data['time']
        self.plotlimit = (0, len(data['time']))

        self.traces = []
        found = False
        for key in data:
            if key.startswith('channel-'):
                # Extract channel number for display-friendly name
                ch_num = key.replace('channel-', '')
                #display_name = f'Trace {ch_num}'
                display_name = f''
                self.addTrace(data[key], name=display_name)
                self.plotlimit = (0, 0)
                found = True

        if not found:
            self.clear()
            return

        self.setStretch(stretch)
        self.autoScale(auto)

        for trc in self.traces:
            trc.tmax = self.timeaxis[-1] - self.timeaxis[0]

        if 'scale' in data:
            for i, s in enumerate(data['scale']):
                self.traces[i].scale = s

        if 'filter' in data:
            for i, f in enumerate(data['filter']):
                order = f[2] if len(f) >= 3 else 2
                self.traces[i].freq = (f[0], f[1], order)

        self.once = True
        self.repaint()

    def clear(self):
        self.autoPan(True)
        self.timeaxis = []
        self.nstack = 0
        for trc in self.traces:
            trc.data = []
            trc.plotlimit = (0, 0)
        self.once = True
        self.repaint()

    def normalize(self):
        if not self.timeaxis:
            return
        tmax = self.timeaxis[-1] - self.timeaxis[0]
        ln = len(self.timeaxis)
        self.timeaxis = np.linspace(0, tmax, ln).tolist()
        targets = self.selected if self.selected else self.traces
        for trc in targets:
            trc.normalize()

    def setStretch(self, st):
        for trc in self.traces:
            trc.stretch = st
            trc.dirty = True

    def autoScale(self, scl):
        for trc in self.traces:
            trc.autoscale = scl
        self.once = True
        self.repaint()

    def autoPan(self, pan):
        for trc in self.traces:
            trc.autopan = pan

    def zoomAll(self, z):
        self.zoomall = z
        for trc in self.traces:
            trc.zoomall = z
        self.once = True
        self.repaint()

    def setZoom(self, zz):
        for trc in self.traces:
            trc.zoomall = False
            trc.zoom = zz

    def magnify(self, mag):
        for trc in self.selected:
            trc.scale *= mag
        self.once = True
        self.repaint()

    def setThreshold(self, thr):
        for trc in self.traces:
            trc.threshold = thr

    def enableFilter(self, ef):
        for trc in self.traces:
            trc.filter = ef
            trc.dirty = True
        if self.timeaxis:
            self.normalize()
        self.once = True
        self.repaint()

    def enableFillplot(self, ef):
        for trc in self.traces:
            trc.fillarea = ef
        self.once = True
        self.repaint()

    def filterStrength(self, freq, order=2, ftype=None):
        targets = [t for t in self.traces if t.selected] if self.selected else self.traces
        for trc in targets:
            ft = ftype if ftype is not None else (trc.freq[3] if len(trc.freq) >= 4 else 'butter')
            trc.freq = (freq[0], freq[1], order, ft)
            trc.dirty = True
        self.once = True
        self.repaint()

    def adjustFrequency(self, hilo, finc):
        for trc in self.selected:
            ff = trc.freq
            if hilo == 'low':
                nf = ff[0] + finc
                if nf > 0 and nf < 50 and abs(nf - ff[1]) > self.minbwidth:
                    trc.freq = (nf, ff[1], ff[2])
            elif hilo == 'high':
                nf = ff[1] + finc
                if nf > 0 and nf < 50 and abs(nf - ff[0]) > self.minbwidth:
                    trc.freq = (ff[0], nf, ff[2])
            trc.dirty = True
        self.once = True
        self.repaint()
        self.master.sync_info()

    def adjustViewOffset(self, ofs):
        for trc in self.selected:
            trc.voffset += ofs
        self.once = True
        self.repaint()

    def setScales(self, scales):
        targets = [t for t in self.traces if t.selected] if self.selected else self.traces
        for i, trc in enumerate(targets):
            trc.scale = scales[i]
        self.once = True
        self.repaint()

    def getScales(self):
        return [trc.scale for trc in self.traces]

    def getFilterSettings(self):
        return [(trc.freq[0], trc.freq[1], trc.freq[2]) for trc in self.traces]

    def trimdata(self, off):
        if not self.timeaxis:
            return
        off -= self.timeaxis[0]
        while self.timeaxis[0] < off:
            self.timeaxis.pop(0)
            for t in self.traces:
                t.data.pop(0)
        n = len(self.timeaxis)
        for t in self.traces:
            t.dirty = True
            t.tmax = self.timeaxis[n - 1]

    def append(self, taxis, val):
        self.timeaxis.append(taxis)
        for i, trc in enumerate(self.traces):
            trc.data.append(val[i])
            trc.dirty = True
            trc.tmax = taxis - self.timeaxis[0]

    def showinfo(self):
        if not self.selected:
            actions.select_trace(self)

        tinfo = '<h1>Trace Information</h1>'
        tinfo += f'Data length: {len(self.timeaxis)}<br>'
        ta, tb = self.timeaxis[0], self.timeaxis[-1]
        tinfo += f'Time range: %0.2f seconds (%0.2f, %0.2f)<br>' % (tb - ta, ta, tb)
        for trc in self.selected:
            tinfo += f'<br><b>{trc.name}</b>'
            tinfo += '<table width="100%" style="margin-left:10px">'
            tinfo += '<tr><td width="30%">data range </td><td> (%0.4f, %0.4f)</td></tr>' % (trc.datarange[0], trc.datarange[1])
            tinfo += '<tr><td>view scale</td><td> %0.2f</td></tr>' % trc.scale
            tinfo += '<tr><td>view offset</td><td> %0.2f pixels</td></tr>' % trc.voffset
            tinfo += '<tr><td>filter</td><td> (%0.1fHz %0.1fHz order:%d)</td></tr>' % (trc.freq[0], trc.freq[1], trc.freq[2])
            tinfo += '</table><br>'
        self.master.show_info(tinfo)

    # ------------------------------------------------------------------
    # Action delegates — thin wrappers so existing callers still work
    # ------------------------------------------------------------------

    def seltrace(self):            actions.select_trace(self)
    def selectAll(self):           actions.select_all(self)
    def clearSelection(self):      actions.clear_selection(self)
    def moveup(self):              actions.move_up(self)
    def movedown(self):            actions.move_down(self)
    def deltrace(self):            actions.delete_trace(self)
    def sequenceNames(self):       actions.sequence_names(self)
    def muteblock(self):           actions.mute_block(self)
    def cutblock(self):            actions.cut_block(self)
    def stacktraces(self):         actions.stack_traces(self)
    def pick(self):                actions.pick(self)
    def clearpick(self):           actions.clear_pick(self)

    def getrange(self):
        return actions._get_block_range(self)

    # ------------------------------------------------------------------
    # Rendering helpers (private)
    # ------------------------------------------------------------------

    @staticmethod
    def _decimate_envelope(samples, pixel_width):
        """Max-min envelope decimation: preserves peaks. Numpy-vectorized."""
        arr = np.asarray(samples, dtype=float)
        n = len(arr)
        if n <= pixel_width:
            return arr

        # Trim to exact multiple of pixel_width for reshape
        usable = (n // pixel_width) * pixel_width
        reshaped = arr[:usable].reshape(pixel_width, -1)
        mins = reshaped.min(axis=1)
        maxs = reshaped.max(axis=1)

        # Interleave: put the larger-magnitude value first per bucket
        out = np.empty(pixel_width * 2, dtype=float)
        abs_min_bigger = np.abs(mins) >= np.abs(maxs)
        out[0::2] = np.where(abs_min_bigger, mins, maxs)
        out[1::2] = np.where(abs_min_bigger, maxs, mins)
        return out

    def _draw_trace(self, p, trc):
        """Render a single trace onto painter `p`."""
        from PyQt5.QtGui import QPainterPath, QPen, QBrush, QFont

        if not trc.data:
            return

        if trc.dirty:
            trc.vdata = trc.filtering() if trc.filter and len(trc.data) > 25 else trc.data
            trc.dirty = False

        xmax = len(trc.vdata)

        if trc.zoomall:
            zo, ofs = xmax, 0
        else:
            zo = trc.zoom
            if zo >= xmax:
                zo = xmax
            ofs = (xmax - zo) if trc.autopan else trc.xpan
            ofs = max(0, min(ofs, xmax - zo))

        self.plotlimit = (ofs, ofs + zo)

        vdata_arr = np.asarray(trc.vdata, dtype=float)
        raw = vdata_arr[ofs:min(ofs + zo, xmax)] * trc.scale
        pixel_w = max(1, int(trc.dim[0]))
        dview = self._decimate_envelope(raw, pixel_w) if len(raw) > pixel_w else raw
        dview = np.asarray(dview, dtype=float)

        if trc.autoscale and len(dview) > 0:
            mn_v, mx_v = dview.min(), dview.max()
            amp = abs(mx_v - mn_v) > trc.threshold
            if amp and mn_v < mx_v:
                sc = 0.5 * trc.dim[1] / max(abs(mx_v), abs(mn_v))
                dview = dview * sc

        x = trc.pos[0]
        if trc.stretch or trc.zoom < zo:
            dx = float(trc.dim[0]) / zo
        else:
            dx = float(trc.dim[0]) / trc.zoom

        yzero = int(trc.base)
        line = QPainterPath()

        sign = 1 if trc.invert else -1

        if trc.fillarea:
            line.moveTo(x, yzero)
            line.lineTo(x, yzero + sign * dview[0] - trc.voffset)
        else:
            line.moveTo(x, yzero + sign * dview[0] - trc.voffset)

        for d in range(1, len(dview)):
            line.lineTo(x, yzero + sign * dview[d] - trc.voffset)
            x += dx

        if trc.fillarea:
            line.lineTo(x, yzero)
            p.setBrush(QBrush(trc.color, Qt.SolidPattern))

        p.setPen(QPen(trc.color, 2, Qt.SolidLine))
        p.setRenderHint(QPainter.Antialiasing)
        p.drawPath(line)

        if trc.pickpoint >= trc.xpan:
            dp = int(trc.pickpoint * dx)
            p.setPen(QPen(Qt.black, 1, Qt.NoPen))
            pcl = QColor(trc.color)
            pcl.setAlpha(60)
            p.setBrush(QBrush(pcl, Qt.SolidPattern))
            p.drawEllipse(dp - 10, yzero - 10, 20, 20)
            p.setPen(QPen(Qt.black, 1, Qt.SolidLine))
            p.drawLine(dp, yzero - 10, dp, yzero + 10)

        # p.setPen(QPen(Qt.black, 1, Qt.SolidLine))
        # p.setFont(QFont('Arial', 12))
        # p.drawText(5, yzero, 100, int(trc.dim[1]), Qt.AlignTop, trc.name)
        trc.xpan = ofs

    def _draw_axis(self, p, trc):
        """Draw background highlight and baseline for a trace."""
        px, py = int(trc.pos[0]), int(trc.pos[1])
        pw, ph = int(trc.dim[0]), int(trc.dim[1])
        base = int(trc.base)
        p.save()
        if trc.selected:
            p.setPen(QPen(QColor(247, 220, 111, 100), 1, Qt.DashLine))
            p.setBrush(QBrush(QColor(252, 243, 207), Qt.SolidPattern))
            p.drawRect(px, py, pw, ph)
        elif trc.highlight:
            p.setPen(QPen(QColor(253, 254, 254, 100), 1, Qt.DashLine))
            p.setBrush(QBrush(QColor(252, 243, 207), Qt.SolidPattern))
            p.drawRect(px, py, pw, ph)
        p.restore()
        p.setPen(QPen(Qt.gray, 1, Qt.DashLine))
        p.drawLine(px, base, px + pw, base)

    # ------------------------------------------------------------------
    # Paint event
    # ------------------------------------------------------------------

    def paintEvent(self, event):
        p = QPainter(self.scrimg)

        if self.running or self.once:
            p.eraseRect(self.rect())
            for trc in self.traces:
                if not getattr(trc, '_visible', True):
                    continue
                trc.dim = (self.width() - trc.pos[0], trc.dim[1])
                self._draw_axis(p, trc)
                self._draw_trace(p, trc)
            self.once = False

        tt = self.getTimeLimit()
        pc = QPainter(self)
        pc.drawPixmap(0, 0, self.scrimg)
        pc.setPen(QPen(QColor('#2c5f7a'), 1, Qt.SolidLine))
        pc.setFont(QFont('Segoe UI', 10))
        pc.drawText(2, self.height() - 20, 120, 30, Qt.AlignLeft, '<%0.3f' % tt[0])
        pc.drawText(self.width() - 82, self.height() - 20, 80, 30, Qt.AlignRight, '%0.3f>' % tt[1])

        indi = self.indicator[0]

        if self.show_indicator:
            pc.setPen(QPen(QColor('#cc2222'), 2, Qt.DashLine))
            pc.drawLine(indi, 0, indi, self.height())

            if self.drag:
                pts = [QPoint(0, 5), QPoint(10, 0), QPoint(30, 0),
                       QPoint(40, 5), QPoint(30, 10), QPoint(10, 10)]
                din = QPolygon(pts)
                din.translate(indi - 20, 3)
                pc.setPen(QPen(QColor('#cc2222'), 1, Qt.SolidLine))
                pc.setBrush(QBrush(QColor('#ffdd44'), Qt.SolidPattern))
                pc.drawPolygon(din)

            if self.timeaxis:
                ix = 0
                if indi != 0:
                    ix = self.getTimeLimit()
                    ix = ix[0] + (ix[1] - ix[0]) * indi / self.width()
                pc.setFont(QFont('Segoe UI', 10))
                pc.setPen(QPen(QColor('#aa1111'), 1, Qt.SolidLine))
                if indi < self.width() // 2:
                    pc.drawText(indi, self.height() - 20, 120, 50, Qt.AlignLeft, '<%0.6f' % ix)
                else:
                    pc.drawText(indi - 120, self.height() - 20, 120, 50, Qt.AlignRight, '%0.6f>' % ix)

        if self.onblock:
            pc.setPen(QPen(Qt.red, 1, Qt.NoPen))
            pc.setBrush(QBrush(QColor(100, 100, 100, 100), Qt.SolidPattern))
            w = indi - self.block['begin']
            pc.drawRect(self.block['begin'], 0, w, self.height())
        elif 'end' in self.block:
            pc.setPen(QPen(Qt.red, 1, Qt.NoPen))
            pc.setBrush(QBrush(QColor(100, 100, 100, 100), Qt.SolidPattern))
            w = self.block['end'] - self.block['begin']
            pc.drawRect(self.block['begin'], 0, w, self.height())

    # ------------------------------------------------------------------
    # Mouse events
    # ------------------------------------------------------------------

    def mouseDoubleClickEvent(self, ev):
        self.seltrace()

    def _decay_ends(self):
        self.btn_decay = False

    def mousePressEvent(self, ev):
        self.mx = ev.x()
        self.my = ev.y()
        if ev.buttons() == Qt.LeftButton:
            if self.drag:
                self.drag = False
                self.once = True
                self.repaint()
            else:
                self.btn_decay = True
                QTimer().singleShot(500, self._decay_ends)

    def mouseMoveEvent(self, ev):
        self.setFocus()
        self.indicator = (ev.x(), ev.y())
        if self.btn_decay or ev.buttons() == Qt.RightButton:
            self.drag = True
        if self.drag:
            self.once = True
            if ev.x() != self.mx:
                dx = ev.x() - self.mx
                self.mx = ev.x()
                for trc in self.traces:
                    trc.panshift(dx)
        self.repaint()

    def wheelEvent(self, ev):
        """Scroll through traces when trace zoom is active."""
        if self.trace_view_count > 0 and self.trace_view_count < len(self.traces):
            delta = ev.angleDelta().y()
            if delta > 0:
                self.master.trace_scroll_up()
            elif delta < 0:
                self.master.trace_scroll_down()
            ev.accept()
        else:
            super().wheelEvent(ev)

    # ------------------------------------------------------------------
    # Keyboard events
    # ------------------------------------------------------------------

    def keyPressEvent(self, ev):
        k = ev.key()
        if k == Qt.Key_B:
            if self.onblock:
                self.block['end'] = self.indicator[0]
                self.onblock = False
            else:
                self.block = {'begin': self.indicator[0]}
                self.onblock = True
            self.once = True; self.repaint()

        elif k in (Qt.Key_Home, Qt.Key_0):
            if self.onblock:
                self.block['end'] = 0
                self.onblock = False
                self.once = True; self.repaint()

        elif k in (Qt.Key_End, Qt.Key_9):
            if self.onblock:
                self.block['end'] = self.width() - 1
                self.onblock = False
                self.once = True; self.repaint()

        elif k == Qt.Key_Q:
            self.onblock = False; self.block = {}
            self.once = True; self.repaint()

        elif k == Qt.Key_Escape:
            self.onblock = False; self.block = {}
            self.clearSelection()

        elif k == Qt.Key_M:   self.muteblock()
        elif k == Qt.Key_C:   self.cutblock()
        elif k == Qt.Key_P:
            if self.show_indicator:
                self.pick()
        elif k == Qt.Key_D:   self.deltrace()
        elif k == Qt.Key_Space: self.seltrace()
        elif k == Qt.Key_Up:  self.moveup()
        elif k == Qt.Key_Down: self.movedown()
        elif k == Qt.Key_I:   self.showinfo()
        elif k in (Qt.Key_Plus, Qt.Key_Equal): self.magnify(1.2)
        elif k == Qt.Key_Minus: self.magnify(1 / 1.2)
        elif k == Qt.Key_H:   self.adjustViewOffset(1)
        elif k == Qt.Key_J:   self.adjustViewOffset(-1)
        elif k == Qt.Key_BracketLeft:  self.adjustFrequency('low', -1)
        elif k == Qt.Key_BracketRight: self.adjustFrequency('low', 1)
        elif k == Qt.Key_BraceLeft:    self.adjustFrequency('high', -1)
        elif k == Qt.Key_BraceRight:   self.adjustFrequency('high', 1)
