from PyQt5.QtWidgets import QAction, QMessageBox

PLUGIN_NAME = 'ML Auto-Picker'
PLUGIN_MENU = 'ML'


def register(mainwindow):
    """Register the ML Auto-Picker plugin.

    Creates a QAction for the BiLSTM Auto-Picker and returns menu
    metadata so the main application can wire it into the menu bar.

    Args:
        mainwindow: The application's main QMainWindow instance.

    Returns:
        dict with ``menu_name`` (str) and ``actions`` (list[QAction]).
    """
    action = QAction('&BiLSTM Auto-Picker', mainwindow)
    action.triggered.connect(lambda: _show_ml_picker(mainwindow))

    return {'menu_name': PLUGIN_MENU, 'actions': [action]}


def _show_ml_picker(mainwindow):
    """Show the ML Picker dialog, checking for PyTorch first."""
    try:
        import torch  # noqa: F401
    except ImportError:
        QMessageBox.critical(
            mainwindow,
            'PyTorch not available',
            'PyTorch is required for the ML Auto-Picker.\n\n'
            'Install it with:  pip install torch',
        )
        return

    canvas = getattr(mainwindow, 'parea', None)
    if canvas is None or not canvas.traces or not canvas.timeaxis:
        QMessageBox.information(
            mainwindow, 'ML Auto-Picker', 'Load a file first.'
        )
        return

    from .ml_picker_dialog import MLPickerDialog

    # Reuse existing dialog if open
    dlg = getattr(mainwindow, '_ml_picker_dialog', None)
    if dlg and dlg.isVisible():
        dlg._populate_trace_lists()
        dlg.raise_()
        return

    mainwindow._ml_picker_dialog = MLPickerDialog(mainwindow, canvas)
    mainwindow._ml_picker_dialog.show()

