from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal

import core.actions as actions


class ArrivalTimeDialog(QDialog):
    """Modeless dialog showing all picked arrival times."""

    pick_deleted = pyqtSignal(int)  # trace_index

    def __init__(self, parent, canvas):
        super().__init__(parent)
        self.setWindowTitle('Arrival Times')
        self.resize(520, 400)
        self._canvas = canvas
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        lo = QVBoxLayout()

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(['#', 'Trace', 'Offset (m)', 'Arrival Time (s)'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        lo.addWidget(self.table)

        btn_row = QHBoxLayout()
        self.refresh_btn = QPushButton('Refresh')
        self.refresh_btn.clicked.connect(self.refresh)
        self.delete_btn = QPushButton('Delete Row')
        self.delete_btn.clicked.connect(self._delete_selected)
        self.export_btn = QPushButton('Export .dat')
        self.export_btn.clicked.connect(self._export_dat)
        close_btn = QPushButton('Close')
        close_btn.clicked.connect(self.close)

        btn_row.addWidget(self.refresh_btn)
        btn_row.addWidget(self.delete_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.export_btn)
        btn_row.addWidget(close_btn)
        lo.addLayout(btn_row)

        self.setLayout(lo)

    def refresh(self):
        """Rebuild table from current canvas picks."""
        picks = actions.get_all_picks(self._canvas)
        self.table.setRowCount(len(picks))
        for row, (tidx, name, ptime) in enumerate(picks):
            idx_item = QTableWidgetItem(str(tidx + 1))
            idx_item.setFlags(idx_item.flags() & ~Qt.ItemIsEditable)
            idx_item.setData(Qt.UserRole, tidx)

            name_item = QTableWidgetItem(name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)

            offset_item = QTableWidgetItem('0.0')
            time_item = QTableWidgetItem(f'{ptime:.6f}')
            time_item.setFlags(time_item.flags() & ~Qt.ItemIsEditable)

            self.table.setItem(row, 0, idx_item)
            self.table.setItem(row, 1, name_item)
            self.table.setItem(row, 2, offset_item)
            self.table.setItem(row, 3, time_item)

    def add_pick(self, trace_index, trace_name, arrival_time):
        """Add or update a single pick in the table (called live while picking)."""
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.data(Qt.UserRole) == trace_index:
                self.table.item(row, 3).setText(f'{arrival_time:.6f}')
                return

        row = self.table.rowCount()
        self.table.insertRow(row)

        idx_item = QTableWidgetItem(str(trace_index + 1))
        idx_item.setFlags(idx_item.flags() & ~Qt.ItemIsEditable)
        idx_item.setData(Qt.UserRole, trace_index)

        name_item = QTableWidgetItem(trace_name)
        name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)

        offset_item = QTableWidgetItem('0.0')
        time_item = QTableWidgetItem(f'{arrival_time:.6f}')
        time_item.setFlags(time_item.flags() & ~Qt.ItemIsEditable)

        self.table.setItem(row, 0, idx_item)
        self.table.setItem(row, 1, name_item)
        self.table.setItem(row, 2, offset_item)
        self.table.setItem(row, 3, time_item)

    def _delete_selected(self):
        rows = sorted(set(idx.row() for idx in self.table.selectedIndexes()), reverse=True)
        for row in rows:
            item = self.table.item(row, 0)
            if item:
                tidx = item.data(Qt.UserRole)
                actions.clear_single_pick(self._canvas, tidx)
                self.pick_deleted.emit(tidx)
            self.table.removeRow(row)

    def _get_table_data(self):
        """Extract all rows as list of (trace_index, name, offset, time)."""
        data = []
        for row in range(self.table.rowCount()):
            tidx = self.table.item(row, 0).data(Qt.UserRole)
            name = self.table.item(row, 1).text()
            try:
                offset = float(self.table.item(row, 2).text())
            except ValueError:
                offset = 0.0
            time_val = float(self.table.item(row, 3).text())
            data.append((tidx, name, offset, time_val))
        return data

    def _export_dat(self):
        if self.table.rowCount() == 0:
            QMessageBox.information(self, 'Export', 'No arrival times to export.')
            return

        fnm, _ = QFileDialog.getSaveFileName(
            self, 'Export Arrival Times', 'arrivals.dat', 'DAT files (*.dat);;All files (*)'
        )
        if not fnm:
            return

        data = self._get_table_data()
        with open(fnm, 'w') as f:
            f.write('# TraceMax Arrival Time Data\n')
            f.write('# trace_index  trace_name  offset_m  arrival_time_s\n')
            for tidx, name, offset, time_val in data:
                f.write(f'{tidx + 1}  {name}  {offset:.4f}  {time_val:.6f}\n')

        QMessageBox.information(self, 'Export', f'Saved {len(data)} picks to\n{fnm}')
