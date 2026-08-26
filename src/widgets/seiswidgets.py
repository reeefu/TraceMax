#!/usr/bin/env python3

from PyQt5.QtWidgets import (
    QPushButton, QCheckBox, QLabel, QTextEdit, QSlider,
    QScrollArea, QWidget, QVBoxLayout
)
from PyQt5.QtCore import Qt


class cmdButton(QPushButton):
    def __init__(self, master, text, pos, sz, act=None):
        super().__init__(text, master)
        self.resize(sz[0], sz[1])
        self.move(pos[0], pos[1])
        self.setObjectName('cmdButton')
        if act is not None:
            self.clicked.connect(act)


class chkButton(QCheckBox):
    def __init__(self, master, text, pos, sz, act=None):
        super().__init__(text, master)
        self.resize(sz[0], sz[1])
        self.move(pos[0], pos[1])
        self.setObjectName('bigCheck')
        if act is not None:
            self.clicked.connect(act)


class bigLabel(QLabel):
    def __init__(self, master, text, pos):
        super().__init__(master)
        self.setText(text)
        self.move(pos[0], pos[1])
        self.setObjectName('bigLabel')
        if len(pos) > 2:
            self.resize(pos[2], pos[3])


class statusText(QTextEdit):
    def __init__(self, master, pos, sz):
        super().__init__(master)
        self.move(pos[0], pos[1])
        self.resize(sz[0], sz[1])


class scroller(QSlider):
    def __init__(self, master, geo, lim=(0, 100, 1), proc=None):
        super().__init__(Qt.Horizontal, master)
        self.resize(geo[2], geo[3])
        self.move(geo[0], geo[1])
        self.setObjectName('scroll')
        self.setMinimum(lim[0])
        self.setMaximum(lim[1])
        self.setSingleStep(lim[2])
        if proc is not None:
            self.valueChanged.connect(proc)


class scrollLabel(QScrollArea):
    def __init__(self, text, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWidgetResizable(True)
        content = QWidget(self)
        self.setWidget(content)
        lay = QVBoxLayout(content)
        self.label = QLabel(content)
        self.label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.label.setWordWrap(True)
        lay.addWidget(self.label)
        self.label.setText(text)

    def setText(self, text):
        self.label.setText(text)
