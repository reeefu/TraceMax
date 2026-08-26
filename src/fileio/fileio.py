import os
import json
import tempfile
import threading

from PyQt5.QtWidgets import (
    QFileDialog, QProgressDialog, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer


def open_data(window, file_to_open=''):
    """Open one or more JSON data files and load into the plotter.

    Args:
        window: SeismoWin instance (provides parea, _set_status, etc.)
        file_to_open: pre-selected file path (from CLI); empty means show dialog.
    """
    remove_after = False

    if file_to_open == '':
        fdlg = QFileDialog()
        fnm, ok = fdlg.getOpenFileNames(window, 'Open File', filter='*.json')
        if not ok:
            return
        if len(fnm) > 1:
            fnm = combine_data(fnm)
            remove_after = True
        else:
            fnm = fnm[0]
    else:
        fnm = file_to_open

    if not os.path.exists(fnm):
        return

    window._load_data = None
    window._load_error = None
    window._pending_file = fnm
    window._remove_after_load = remove_after

    prog = QProgressDialog('Loading file\u2026', None, 0, 0, window)
    prog.setWindowTitle('Please wait')
    prog.setWindowModality(Qt.WindowModal)
    prog.setMinimumDuration(0)
    prog.setValue(0)
    prog.show()

    def _loader():
        try:
            with open(fnm) as fl:
                window._load_data = json.load(fl)
        except Exception as e:
            window._load_error = str(e)

    t = threading.Thread(target=_loader, daemon=True)
    t.start()

    def _check():
        if t.is_alive():
            QTimer().singleShot(50, _check)
            return
        prog.close()
        if window._load_error:
            QMessageBox.critical(window, 'Load Error', window._load_error)
            return
        apply_loaded_data(window)

    QTimer().singleShot(50, _check)


def apply_loaded_data(window):
    """Called on main thread after background load completes."""
    data = window._load_data
    fnm = window._pending_file
    remove_after = window._remove_after_load

    chnfound = any(
        k.startswith('channel-') and len(data[k]) > 0
        for k in data
    )

    if not chnfound:
        QMessageBox.about(window, 'Alert', f'File contains no data\n{fnm}')
        return

    window.parea.assignData(data, True, True)
    window.parea.arrangeTraces()
    window.parea.normalize()
    window.zoom_plot()

    nd = len(window.parea.timeaxis)
    tt = window.parea.timeaxis[nd - 1] - window.parea.timeaxis[0]
    window.pickbox.setText('')

    fname = os.path.basename(fnm)
    window._set_status(f'{fname}  \u2014  {nd} samples  |  {tt:.3f} s')
    window.setWindowTitle(f'SeismoLog Trace Editor \u2014 {fname}')

    if remove_after:
        os.remove(fnm)


def save_data(window, config, fnm=''):
    """Save trace data + config to a JSON file."""
    if not fnm:
        fnm, _ = QFileDialog.getSaveFileName(window, 'Save File', 'newfile.json')

    if fnm:
        dd = window.parea.getData()
        dd['config'] = config
        with open(fnm, 'w') as f:
            json.dump(dd, f)



def combine_data(flst):
    """Merge multiple JSON data files into one temp file.

    Strategy: take the shortest data, average the time axis.
    Returns the path to the temp file.
    """
    chdata = {}
    chtime = {}
    dlen = []
    nm = 0
    flst = sorted(flst)

    for fnm in flst:
        with open(fnm) as fl:
            data = json.load(fl)

        try:
            chtime[nm] = data['time']
        except Exception:
            print(f'bad data file: {fnm}')
            continue

        nf = 0
        while True:
            chan = 'channel-%02d' % nf
            try:
                dd = data[chan]
                chdata[chan + '_%02d' % nm] = dd
                dlen.append(len(dd))
            except Exception:
                break
            nf += 1

        if nf:
            nm += 1

    dlen = min(dlen)

    dt = sum(
        chtime[n][dlen - 1] - chtime[n][0]
        for n in chtime
    ) / (len(chtime) * dlen)

    timeaxis = [dt * t for t in range(dlen)]
    savedata = {'time': timeaxis}
    for chn in chdata:
        savedata[chn] = chdata[chn][:dlen]

    fd, fname = tempfile.mkstemp()
    with os.fdopen(fd, 'w') as cfl:
        json.dump(savedata, cfl)

    return fname
