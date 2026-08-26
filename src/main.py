#!/usr/bin/env python3


import sys
import os


_SRC = os.path.dirname(os.path.abspath(__file__))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import config as cfg
cfg.parse_cli_args(sys.argv)
cfg.load_assets()


from PyQt5.QtWidgets import QApplication, QSplashScreen
from PyQt5.QtGui import (
    QPixmap, QPainter, QColor, QBrush, QLinearGradient, QFont, QIcon
)
from PyQt5.QtCore import Qt

from app.mainwindow import SeismoWin

cfg._restart_flag = False


def _build_splash_pixmap(logo_path):
    W, H = 600, 320
    pixmap = QPixmap(W, H)
    p = QPainter(pixmap)

    gradient = QLinearGradient(0, 0, 0, H)
    gradient.setColorAt(0.0, QColor(230, 240, 252))
    gradient.setColorAt(1.0, QColor(200, 220, 240))
    p.fillRect(0, 0, W, H, QBrush(gradient))

    if os.path.exists(logo_path):
        logo_px = QPixmap(logo_path)
        logo_px = logo_px.scaled(180, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        p.drawPixmap(30, (H - logo_px.height()) // 2, logo_px)

    p.setPen(QColor(0, 130, 180))
    p.drawLine(40, H - 60, W - 40, H - 60)

    tx = 230
    p.setFont(QFont('Arial', 24, QFont.Bold))
    p.setPen(QColor(0, 100, 160))
    p.drawText(tx, 90, W - tx - 20, 36, Qt.AlignLeft, 'SeismoLog')

    p.setFont(QFont('Arial', 13))
    p.setPen(QColor(50, 80, 120))
    p.drawText(tx, 132, W - tx - 20, 28, Qt.AlignLeft, 'Trace Editor')

    p.setFont(QFont('Arial', 9))
    p.setPen(QColor(100, 130, 160))
    p.drawText(tx, 168, W - tx - 20, 24, Qt.AlignLeft, 'Loading, please wait...')

    p.setPen(QColor(120, 150, 180))
    p.drawText(0, H - 50, W, 20, Qt.AlignCenter,
               '\u00a9 2026 Arief Ritonga  \u2022  Universitas Padjadjaran')

    p.end()
    return pixmap


class SeismoApp(QApplication):
    def __init__(self):
        super().__init__(sys.argv)
        self.setApplicationName('SeismoLog Trace Editor')

        screen = self.primaryScreen().size()

        if cfg.css:
            self.setStyleSheet(cfg.css)

        splash_pm = _build_splash_pixmap(cfg.LOGO_PATH)
        splash = QSplashScreen(splash_pm, Qt.WindowStaysOnTopHint)
        splash.show()
        self.processEvents()

        self.guiwin = SeismoWin(screen.width(), screen.height())
        splash.finish(self.guiwin)


def main():
    try:
        while True:
            cfg._restart_flag = False
            SeismoApp().exec()
            if not cfg._restart_flag:
                break
    except Exception as e:
        print('SEISMOLOG EXECUTION ERROR')
        print(e)
        raise


if __name__ == '__main__':
    main()
