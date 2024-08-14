#!/usr/bin/env python3

#---------------------------------
# Seismic Instrument Qt Application
#
# (c) 2022, Rosandi
#
# rosandi@geophys.unpad.ac.id
#

from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt

class cmdButton(QPushButton):
    def __init__(self,master,text,pos,sz,act=None):
        super(cmdButton,self).__init__(text,master)
        self.resize(sz[0],sz[1])
        self.move(pos[0],pos[1])
        self.setObjectName('cmdButton')
        
        if (act != None):
            self.clicked.connect(act)

class chkButton(QCheckBox):
    def __init__(self,master,text,pos,sz,act=None):
        super(chkButton,self).__init__(text,master)
        self.resize(sz[0],sz[1])
        self.move(pos[0],pos[1])
        self.setObjectName('bigCheck')

        if (act != None):
            self.clicked.connect(act)

class bigLabel(QLabel):
    def __init__(self,master,text,pos):
        super(bigLabel, self).__init__(master)
        self.setText(text)
        self.move(pos[0],pos[1])
        self.setObjectName('bigLabel')
        if len(pos)>2:
            self.resize(pos[2],pos[3])

class statusText(QTextEdit):
    def __init__(self, master, pos, sz):
        super(statusText, self).__init__(master)
        self.move(pos[0],pos[1])
        self.resize(sz[0],sz[1])


class scroller(QSlider):

    def __init__(self, master, geo, lim=(0,100,1), proc=None):
        super(scroller,self).__init__(Qt.Horizontal,master)
        self.resize(geo[2],geo[3])
        self.move(geo[0],geo[1])
        self.setObjectName('scroll')
        self.setMinimum(lim[0])
        self.setMaximum(lim[1])
        self.setSingleStep(lim[2])
        if proc != None:
            self.valueChanged.connect(proc)

class scrollLabel(QScrollArea):
    def __init__(self, text, *args, **kwargs):
        QScrollArea.__init__(self, *args, **kwargs)
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


class infoDialog(QDialog):
    def __init__(self, master, msg):
        super(infoDialog, self).__init__(master)
        self.resize(400,400)
        self.create(msg)
        self.exec_()

    def create(self,msg):
        lo=QVBoxLayout()
        info=scrollLabel(msg)
        closeBtn=QPushButton('&Close')
        closeBtn.clicked.connect(lambda: self.close())
        lo.addWidget(info)
        lo.addWidget(closeBtn)
        self.setLayout(lo)


