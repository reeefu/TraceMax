import os

from PyQt5.QtWidgets import (
    QMainWindow, QAction, QMenu, QMessageBox, QStatusBar, QFileDialog
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QRect

from core.plotter import plotter
from app.toolbar import ControlPanel
from app.dialogs import helpDialog, FFTDialog, infoDialog
from app.arrival_dialog import ArrivalTimeDialog
from app.stalta_dialog import STALTADialog
from app.hagiwara_dialog import HagiwaraDialog
from fileio.fileio import open_data, save_data, combine_data
from plugin import discover_plugins
import config as cfg


about = '''
<p align="center">
<h1>SeismoLog Trace Editor</h1>
<br>
</p>
<br><br>
Geophysics Department,
Universitas Padjadjaran
<br><br>
(c) 2022, Rosandi<br>
'''


class SeismoWin(QMainWindow):

    H_CMD = 120   # height of the top control panel

    def __init__(self, w, h):
        super().__init__()
        self.resize(min(1024, w), 600)
        self.setWindowTitle('SeismoLog Trace Editor')
        self.h_cmd = self.H_CMD
        self.droprobot = False
        self.trigwifi = False

        # thread-load temporaries
        self._load_data = None
        self._load_error = None
        self._load_timer = None
        self._pending_file = ''
        self._remove_after_load = False

        self.chn = [0] * 12
        self._arrival_dialog = None
        self._plugins = []

        self._build_window(w, h)
        self._apply_config()

        if os.path.exists(cfg.LOGO_PATH):
            self.setWindowIcon(QIcon(cfg.LOGO_PATH))

        self.show()

        if cfg.file_to_open:
            print('opening file:', cfg.file_to_open)
            open_data(self, cfg.file_to_open)
            cfg.file_to_open = ''

    # ------------------------------------------------------------------
    # Public interface used by plotter / toolbar callbacks
    # ------------------------------------------------------------------

    def sync_info(self):
        """Sync filter sliders and selection label to selected trace."""
        p = self.parea.selected
        panel = self.panel
        has_traces = bool(self.parea.traces and self.parea.timeaxis)

        if len(p) == 1:
            panel.set_filter_enabled(True)
            panel.sync_filter_ui(p[0].freq[0], p[0].freq[1])
        else:
            # Enable filter for all traces even when none selected
            panel.set_filter_enabled(has_traces)

        if p:
            st = 'Selected: '
            for trc in p:
                st += trc.name + ' '
                if len(st) > 36:
                    st += '...'
                    break
        else:
            st = 'Selected: All traces' if has_traces else 'Selected: none'

        panel.set_selected_label(st)

    def show_info(self, msg):
        infoDialog(self, msg)

    def _set_status(self, msg):
        if hasattr(self, 'status_bar'):
            self.status_bar.showMessage(msg)

    # ------------------------------------------------------------------
    # Filter callbacks (called by ControlPanel sliders/buttons)
    # ------------------------------------------------------------------

    def hf_tune(self):
        v = self.panel.hifreq.value()
        self.panel.hfvalue.setText(f'{v} Hz')
        self.panel.hf_edit.blockSignals(True)
        self.panel.hf_edit.setText(str(v))
        self.panel.hf_edit.blockSignals(False)

    def lf_tune(self):
        v = self.panel.lofreq.value()
        self.panel.lfvalue.setText(f'{v} Hz')
        self.panel.lf_edit.blockSignals(True)
        self.panel.lf_edit.setText(str(v))
        self.panel.lf_edit.blockSignals(False)

    def _apply_filter(self):
        panel = self.panel
        try:
            lf = float(panel.lf_edit.text())
        except ValueError:
            lf = float(panel.lofreq.value())
        try:
            hf = float(panel.hf_edit.text())
        except ValueError:
            hf = float(panel.hifreq.value())

        order = panel.filter_order.value()
        ftype = ['butter', 'cheby1', 'bessel'][panel.filter_type.currentIndex()]

        panel.sync_filter_ui(lf, hf)

        self.parea.filterStrength((lf, hf), order=order, ftype=ftype)

        targets = self.parea.selected if self.parea.selected else self.parea.traces
        for trc in targets:
            trc.filter = True
            trc.dirty = True

        self.parea.once = True
        self.parea.repaint()

        cfg.config['gui']['high_freq'] = hf
        cfg.config['gui']['low_freq'] = lf

    # ------------------------------------------------------------------
    # View callbacks (called by ControlPanel checkboxes)
    # ------------------------------------------------------------------

    def zoom_plot(self):
        self.parea.zoomAll(not self.panel.zoom_chk.isChecked())

    def toggle_filter(self):
        self.parea.enableFilter(self.panel.filt_chk.isChecked())

    def toggle_fillplot(self):
        self.parea.enableFillplot(self.panel.fillplot_chk.isChecked())

    def auto_scale(self):
        self.parea.autoScale(self.panel.autos_chk.isChecked())

    # ------------------------------------------------------------------
    # Pick callbacks
    # ------------------------------------------------------------------

    def toggle_picking(self):
        """Toggle pick mode on/off — shows/hides the red indicator line."""
        picking = not self.parea.show_indicator
        self.parea.show_indicator = picking
        self.parea.once = True
        self.parea.repaint()

        # Update the toggle button text
        if hasattr(self.panel, 'pick_toggle_btn'):
            self.panel.pick_toggle_btn.setText('STOP PICK' if picking else 'START PICK')
            self.panel.pick_toggle_btn.setStyleSheet(
                'background-color: #cc4444; color: #ffffff; border: 1px solid #aa2222;'
                'border-radius: 8px; padding: 6px 10px; font-size: 12px; font-weight: bold;'
                if picking else ''
            )

    def pick(self, data):
        ss = self.panel.pickbox.toPlainText()
        line = 'trace(%02d) %0.6f' % (data[0] + 1, data[1])
        self.panel.pickbox.setText((ss + '\n' if ss else '') + line)
        m = self.panel.pickbox.verticalScrollBar().maximum()
        self.panel.pickbox.verticalScrollBar().setValue(m)

        if self._arrival_dialog and self._arrival_dialog.isVisible():
            trc = self.parea.traces[data[0]]
            self._arrival_dialog.add_pick(data[0], trc.name, data[1])

    def clearpick(self):
        self.panel.pickbox.setText('')
        self.parea.clearpick()

    def import_pick_dat(self):
        """Import picks from a .dat file and apply them to loaded traces."""
        if not self.parea.traces or not self.parea.timeaxis:
            QMessageBox.information(self, 'Import Pick', 'Load a file first.')
            return

        fnm, _ = QFileDialog.getOpenFileName(
            self, 'Import Pick Data', '', 'DAT files (*.dat);;All files (*)'
        )
        if not fnm:
            return

        # Parse the .dat file
        imported = []
        try:
            with open(fnm, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    parts = line.split()
                    if len(parts) < 4:
                        continue
                    try:
                        trace_idx = int(parts[0]) - 1  # 1-based in file
                        trace_name = parts[1]
                        offset = float(parts[2])
                        arrival_time = float(parts[3])
                        imported.append((trace_idx, trace_name, offset, arrival_time))
                    except (ValueError, IndexError):
                        continue
        except Exception as e:
            QMessageBox.warning(self, 'Import Pick', f'Failed to read file:\n{e}')
            return

        if not imported:
            QMessageBox.information(self, 'Import Pick', 'No valid pick data found in file.')
            return

        # Build a name-to-index map for loaded traces
        name_map = {trc.name: i for i, trc in enumerate(self.parea.traces)}
        n_traces = len(self.parea.traces)
        timeaxis = self.parea.timeaxis
        tmax = timeaxis[-1] - timeaxis[0]
        n_samples = len(timeaxis)

        applied = 0
        for tidx, tname, offset, arrival_time in imported:
            # Match by name first, then fall back to index
            match_idx = name_map.get(tname, None)
            if match_idx is None and 0 <= tidx < n_traces:
                match_idx = tidx

            if match_idx is None:
                continue

            # Compute sample index from arrival time
            sample_idx = int(n_samples * arrival_time / tmax) if tmax > 0 else 0
            sample_idx = max(0, min(sample_idx, n_samples - 1))

            trc = self.parea.traces[match_idx]
            trc.pickpoint = sample_idx
            trc.picktime = arrival_time
            applied += 1

            # Update pickbox log
            ss = self.panel.pickbox.toPlainText()
            line = 'trace(%02d) %0.6f' % (match_idx + 1, arrival_time)
            self.panel.pickbox.setText((ss + '\n' if ss else '') + line)

            # Update arrival dialog if open
            if self._arrival_dialog and self._arrival_dialog.isVisible():
                self._arrival_dialog.add_pick(match_idx, trc.name, arrival_time)

        self.parea.once = True
        self.parea.repaint()

        QMessageBox.information(
            self, 'Import Pick',
            f'Applied {applied} of {len(imported)} picks from:\n{os.path.basename(fnm)}'
        )

    # ------------------------------------------------------------------
    # Trace zoom / scroll callbacks
    # ------------------------------------------------------------------

    def set_trace_zoom(self, count):
        """Set trace zoom level: 0=all, 1/3/5=show N traces."""
        lt = len(self.parea.traces)
        if count > 0 and count >= lt:
            count = 0  # not enough traces to zoom, show all

        self.parea.set_trace_view(count, self.parea.trace_view_offset)
        self.panel.set_trace_zoom_active(count)
        self._update_trace_zoom_ui()

    def trace_scroll_up(self):
        """Scroll visible traces up (show earlier traces)."""
        p = self.parea
        if p.trace_view_count <= 0:
            return
        new_offset = max(0, p.trace_view_offset - 1)
        p.set_trace_view(p.trace_view_count, new_offset)
        self._update_trace_zoom_ui()

    def trace_scroll_down(self):
        """Scroll visible traces down (show later traces)."""
        p = self.parea
        if p.trace_view_count <= 0:
            return
        lt = len(p.traces)
        max_offset = lt - p.trace_view_count
        new_offset = min(max_offset, p.trace_view_offset + 1)
        p.set_trace_view(p.trace_view_count, new_offset)
        self._update_trace_zoom_ui()

    def _update_trace_zoom_ui(self):
        """Update zoom label and scroll button enabled state."""
        p = self.parea
        lt = len(p.traces)
        count = p.trace_view_count

        if count <= 0 or count >= lt:
            self.panel.update_trace_zoom_label('All traces')
            self.panel.scroll_up_btn.setEnabled(False)
            self.panel.scroll_down_btn.setEnabled(False)
        else:
            first = p.trace_view_offset + 1
            last = min(p.trace_view_offset + count, lt)
            self.panel.update_trace_zoom_label(f'{first}-{last} of {lt}')
            self.panel.scroll_up_btn.setEnabled(p.trace_view_offset > 0)
            self.panel.scroll_down_btn.setEnabled(p.trace_view_offset + count < lt)

    # ------------------------------------------------------------------
    # File menu actions
    # ------------------------------------------------------------------

    def open_data(self):
        open_data(self, cfg.file_to_open)

    def save_data(self, fnm=''):
        save_data(self, cfg.config, fnm)

    def load_cfg_action(self):
        cnm, _ = QFileDialog.getOpenFileName(self, 'Open Configuration', filter='*.json')
        if cnm:
            if cfg.load_config(cnm):
                self.restart_app()
            else:
                QMessageBox.information(self, 'failure', 'Invalid configuration file')

    def config_save(self):
        fnm, _ = QFileDialog.getSaveFileName(self, 'Save Configuration',
                                              'config.json', filter='*.json')
        if fnm:
            cfg.save_config(fnm)

    def restart_app(self):
        import config as cfg_mod
        cfg_mod._restart_flag = True
        self.close()

    # ------------------------------------------------------------------
    # Tools menu actions
    # ------------------------------------------------------------------

    def show_fft(self):
        if not self.parea.traces or not self.parea.timeaxis:
            QMessageBox.information(self, 'FFT', 'Load a file first.')
            return
        targets = self.parea.selected if self.parea.selected else self.parea.traces
        FFTDialog(self, targets, self.parea.timeaxis).exec_()

    def show_arrival_dialog(self):
        if not self.parea.traces or not self.parea.timeaxis:
            QMessageBox.information(self, 'Arrivals', 'Load a file first.')
            return
        if self._arrival_dialog and self._arrival_dialog.isVisible():
            self._arrival_dialog.refresh()
            self._arrival_dialog.raise_()
            return
        self._arrival_dialog = ArrivalTimeDialog(self, self.parea)
        self._arrival_dialog.show()

    def show_stalta(self):
        if not self.parea.traces or not self.parea.timeaxis:
            QMessageBox.information(self, 'STA/LTA', 'Load a file first.')
            return
        STALTADialog(self, self.parea).exec_()

    def show_hagiwara(self):
        HagiwaraDialog(self, self.parea).exec_()



    # ------------------------------------------------------------------
    # Window construction
    # ------------------------------------------------------------------

    def _build_window(self, w, h):
        self._create_menus()
        self._create_panel()
        self._create_draw_area()

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage('No file loaded')

        ctrx = int((w - self.width()) / 2)
        ctry = int((h - self.height()) / 2)
        self.move(ctrx, ctry)

        if cfg.config['gui']['winmode'].startswith('max'):
            self.showMaximized()

    def _apply_config(self):
        g = cfg.config['gui']
        p = self.parea
        p.setThreshold(g['threshold'])
        p.enableFilter(g['filter'])
        p.filterStrength((g['low_freq'], g['high_freq']), g['order'])

    def _create_menus(self):
        s = cfg.strings
        menubar = self.menuBar()

        # --- File ---
        self.openAction  = QAction(s.get('open',    '&Open'), self)
        self.loadAction  = QAction(s.get('load',    '&Open Configuration'), self)
        self.saveAction  = QAction(s.get('save',    '&Save'), self)
        self.restAction  = QAction(s.get('restart', '&Restart'), self)
        self.closeAction = QAction(s.get('close',   '&Close'), self)

        self.openAction.triggered.connect(self.open_data)
        self.loadAction.triggered.connect(self.load_cfg_action)
        self.saveAction.triggered.connect(self.save_data)
        self.restAction.triggered.connect(self.restart_app)
        self.closeAction.triggered.connect(self.close)

        filemenu = QMenu(s.get('file', '&File'), self)
        for a in [self.openAction, self.loadAction, self.saveAction,
                  self.restAction, self.closeAction]:
            filemenu.addAction(a)

        # --- Tools ---
        self.stackAction = QAction('&Stack', self)
        self.normAction  = QAction('&Normalize', self)
        self.fftAction   = QAction('&FFT Spectrum', self)
        self.arrivalAction = QAction('&Arrival Times', self)
        self.staltaAction = QAction('&STA/LTA Picker', self)
        self.hagiwaraAction = QAction('&Hagiwara Analysis', self)
        self.cfgSaveAction = QAction(s.get('savecfg', '&Save Configuration'), self)

        self.stackAction.triggered.connect(lambda: self.parea.stacktraces())
        self.normAction.triggered.connect(lambda: self.parea.normalize())
        self.fftAction.triggered.connect(self.show_fft)
        self.arrivalAction.triggered.connect(self.show_arrival_dialog)
        self.staltaAction.triggered.connect(self.show_stalta)
        self.hagiwaraAction.triggered.connect(self.show_hagiwara)
        self.cfgSaveAction.triggered.connect(self.config_save)

        toolsmenu = QMenu(s.get('tools', '&Tools'), self)
        for a in [self.stackAction, self.normAction, self.cfgSaveAction]:
            toolsmenu.addAction(a)
        toolsmenu.addSeparator()
        toolsmenu.addAction(self.fftAction)
        toolsmenu.addAction(self.arrivalAction)
        toolsmenu.addAction(self.staltaAction)
        toolsmenu.addAction(self.hagiwaraAction)

        # --- Help ---
        self.helpUsage = QAction(s.get('doc',   '&Usage Instruction'), self)
        self.helpAbout = QAction(s.get('about', '&About'), self)
        self.helpUsage.triggered.connect(lambda: helpDialog(self, cfg.doc_url))
        self.helpAbout.triggered.connect(lambda: QMessageBox.about(self, 'SeisPlot', about))

        helpmenu = QMenu(s.get('help', '&Help'), self)
        helpmenu.addAction(self.helpUsage)
        helpmenu.addAction(self.helpAbout)

        menubar.addMenu(filemenu)
        menubar.addMenu(toolsmenu)

        # --- Plugins (dynamically discovered) ---
        self._plugins = discover_plugins()
        plugin_menus = {}  # cache menus by name
        for pi in self._plugins:
            try:
                result = pi['register'](self)
                if result and 'actions' in result:
                    menu_name = result.get('menu_name', 'Plugins')
                    if menu_name not in plugin_menus:
                        plugin_menus[menu_name] = QMenu(f'&{menu_name}', self)
                    for action in result['actions']:
                        plugin_menus[menu_name].addAction(action)
            except Exception as e:
                print(f'[plugin] failed to register {pi["name"]}: {e}')
        for pm in plugin_menus.values():
            menubar.addMenu(pm)

        menubar.addMenu(helpmenu)

    def _create_draw_area(self):
        r = self.geometry()
        menu_h = self.menuBar().height()
        panel_bottom = menu_h + self.h_cmd
        r.setX(0)
        r.setY(panel_bottom)
        plth = r.height() - panel_bottom

        if 'fix' in cfg.config['gui']:
            for fs in cfg.config['gui']['fix'].split(','):
                if fs.startswith('drawarea_y='):
                    cy = int(fs.split('=')[1])
                    r.setY(r.y() - cy)
                    plth += cy
                if fs.startswith('drawarea_x='):
                    cx = int(fs.split('=')[1])
                    r.setX(cx)

        r.setHeight(plth)
        self.parea = plotter(self, r)

        yhi = (r.height() - 30) // len(self.chn)
        for c in range(len(self.chn)):
            self.chn[c] = self.parea.addTrace([], 'Trace %02d' % c)

        for c in range(len(self.chn)):
            self.parea.traces[c].zoom = cfg.config['gui']['zoom']

        self.parea.pick_function = self.pick

    def _create_panel(self):
        self.panel = ControlPanel(self, self.h_cmd)
        menu_h = self.menuBar().height()
        self.panel.resize(self.width(), self.h_cmd)
        self.panel.move(0, menu_h)

        # expose pickbox at window level for backward compat with fileio
        self.pickbox = self.panel.pickbox

    # ------------------------------------------------------------------
    # Resize
    # ------------------------------------------------------------------

    def resizeEvent(self, event):
        menu_h = self.menuBar().height()
        panel_bottom = menu_h + self.h_cmd
        self.panel.resize(self.width(), self.h_cmd)
        self.panel.move(0, menu_h)
        plth = self.height() - panel_bottom - 10
        self.parea.changeBox(self.width(), plth)
        self.parea.move(0, panel_bottom)
