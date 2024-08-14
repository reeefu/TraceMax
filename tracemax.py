#!/usr/bin/env python3

#---------------------------------
# Seismic Instrument Qt Application
#
# (c) 2022, Rosandi
#
# rosandi@geophys.unpad.ac.id
#

import sys
import os
import tempfile
import math
import json

from PyQt5.QtWidgets import *
from PyQt5.QtGui import QFont, QIntValidator, QDoubleValidator
from PyQt5.QtCore import Qt, QTimer, QUrl, QDate, QTime, QRect
from plotter import plotter
from datetime import datetime
from time import time,sleep
from importlib import import_module as drv
from seiswidgets import *
from threading import Thread
import matplotlib.pyplot as plt

try:
    from PyQt5.QtWebKitWidgets import QWebView as helpBrowser
    print('using WebKit for help browser')
except:
    try:
        from PyQt5.QtWebEngineWidgets import QWebEngineView as helpBrowser
        print('using WebEngine for help browser')
    except Exception as e:
        # FIXME: Use TextBrowser for the last alternative
        print('Can not find help browser. Requires WebKit or WebEngine')
        sys.exit()

config={
    'gui':{
        'filter': True,
        'low_freq':10.0,
        'high_freq': 30.0,
        'order': 2,
        'zoom':200,
        'threshold':0.0,
        'css': 'seismolog.css',
        'lang':'id',
        'winmode': 'max',
        'hold_init_screen': 1
        }
    }

restart=True
scrgeo=(1024,800)
basepath=os.path.dirname(os.path.realpath(__file__))
css=''
file_to_open=''

about='''
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

#------------ COMMAND LINE ARGUMENTS -------- 

# later arguments overide previous ones

for arg in sys.argv[1:]:
    if arg.find('gui=') == 0:
        # format: gui=key:value
        # example:
        # gui=fix:drawarea_y=24,drawarea_x=10
        sarg=arg.replace('gui=','').split(':')
        if(len(sarg)==2):
            config['gui'][sarg[0]]=sarg[1]

    elif os.path.exists(arg):
        file_to_open=arg

#-----------------------------------------------

if os.path.exists(config['gui']['css']):
    css=config['gui']['css']
elif os.path.exists(basepath+'/'+config['gui']['css']):
    css=basepath+'/'+config['gui']['css']

if css != '':
    with open(css) as c:
        css=c.read()

docurl=f"file://{basepath}/doc-{config['gui']['lang']}/index.html"

with open(f'{basepath}/strings.json') as fl:
    strings=json.load(fl)
    strings=strings[config['gui']['lang']]

# ----- Help browser:

class helpDialog(QDialog):
    def __init__(self, master, docfile):
        super(helpDialog, self).__init__(master)
        self.resize(900,600)
        self.docfile=docfile
        self.create()
        self.exec_()

    def create(self):
        self.lo=QVBoxLayout()
        self.web=helpBrowser(self)
        self.web.load(QUrl(self.docfile))
        self.closeBtn=QPushButton('&Close')
        self.closeBtn.clicked.connect(lambda: self.close())
        w=self.width()//3
        sty=f'padding:15px;margin-left:{w}px;margin-right:{w}px;margin-top:20px;'
        sty+='font-size:16px;font-weight:bold;color:teal;'
        self.closeBtn.setStyleSheet(sty)
        self.closeBtn.resize(200,40)
        self.lo.addWidget(self.web)
        self.lo.addWidget(self.closeBtn)
        self.setLayout(self.lo)

###### MAIN CLASS ######

class SeismoWin(QMainWindow):
    def __init__(self,w,h):
        global file_to_open
        super(SeismoWin, self).__init__()
        self.resize(min(1024,w),600) #FIXME: set in config
        self.setWindowTitle("SeismoLog Trace Editor")
        self.h_cmd = 160
        self.droprobot=False
        self.trigwifi=False

        # FIXME
        self.chn=[0]*12

        self.createWin(w,h)
        self.applyConfig()  # FIXME: pass config to plotter class
        self.show()

        if file_to_open != '':
            print('opening file:', file_to_open)
            self.open_data()
            file_to_open=''

    def applyConfig(self): # FIXME: send config to plotter
        g=config['gui']
        p=self.parea
        p.setThreshold(g['threshold'])
        p.enableFilter(g['filter'])
        p.filterStrength((g['low_freq'],g['high_freq']), g['order'])
        
        try:
            if config['trigger_url'] != '':
                self.droprobot=True
                rq.get(config['trigger_url']+'/status', timeout=5)
            
            if config['trigger_type'] == 'wifi':
                self.trigwifi=True
        except:
            self.droprobot=False
            self.trigwifi=False

    def restart_app(self):
        global restart
        restart=True
        self.close()
    
    def createActions(self):
        self.newAction = QAction(self)
        self.openAction = QAction(strings["open"], self)
        self.loadAction = QAction(strings["load"], self)
        self.saveAction = QAction(strings["save"], self)
        self.restAction = QAction(strings["restart"], self)
        self.closeAction = QAction(strings["close"], self)

        self.openAction.triggered.connect(self.open_data)
        self.loadAction.triggered.connect(self.load_cfg)
        self.saveAction.triggered.connect(self.save_data)
        self.restAction.triggered.connect(self.restart_app)
        self.closeAction.triggered.connect(lambda: self.close())

        self.stackTraces = QAction('&Stack', self)
        self.normTraces = QAction('&Normalize', self)
        self.stackTraces.triggered.connect(lambda: self.parea.stacktraces())
        self.normTraces.triggered.connect(lambda: self.parea.normalize())

        self.configSave = QAction(strings['savecfg'], self)

        self.helpAbout = QAction(strings['about'], self)
        self.helpUsage = QAction(strings['doc'], self)
        
        self.helpUsage.triggered.connect(lambda: helpDialog(self, docurl))
        self.helpAbout.triggered.connect(lambda: QMessageBox.about(self, 'SeisPlot', about))

    def createMenus(self):
        menubar=self.menuBar()
        self.createActions()
        
        filemenu=QMenu(strings['file'],self)
        filemenu.addAction(self.openAction)
        filemenu.addAction(self.loadAction)
        filemenu.addAction(self.saveAction)
        filemenu.addAction(self.restAction)
        filemenu.addAction(self.closeAction)

        setmenu=QMenu(strings['tools'], self)
        setmenu.addAction(self.stackTraces)
        setmenu.addAction(self.normTraces)
        setmenu.addAction(self.configSave)

        helpmenu=QMenu(strings['help'], self)
        helpmenu.addAction(self.helpUsage)
        helpmenu.addAction(self.helpAbout)
    
        menubar.addMenu(filemenu)
        menubar.addMenu(setmenu)
        menubar.addMenu(helpmenu)

    def createDrawArea(self):
        r=self.geometry()
        r.setX(0)
        
        r.setY(self.menuBar().height())
        self.plth=r.height()-self.h_cmd-self.menuBar().height()

        if 'fix' in config['gui']:
            # plot position correction
            # fix format: key:val,...
            
            pcor=config['gui']['fix'].split(',')
            
            for fs in pcor:
                if fs.find('drawarea_y=') == 0:
                    cy=int(fs.split('=')[1])
                    r.setY(r.y()-cy)
                    self.plth+=cy
                if fs.find('drawarea_x=') == 0:
                    cx=int(fs.split('=')[1])
                    r.setX(cx)

        r.setHeight(self.plth)

        self.parea=plotter(self,r)
        
        yhi=(r.height()-30)//len(self.chn)
        yof=0

        for c in range(len(self.chn)): #FIXME: plot geometry
            self.chn[c]=self.parea.addTrace([], 'channel-%02d'%c)
            yof+=yhi

        for c in range(len(self.chn)):
            self.parea.traces[c].zoom=config['gui']['zoom']

        self.parea.pick_function=self.pick

    def hf_tune(self):
        hf=self.hifreq.value()
        lf=self.lofreq.value()
        self.hfvalue.setText(f'{hf} Hz')
        self.parea.filterStrength((lf,hf))
        config['gui']['high_freq']=hf

    def lf_tune(self):
        hf=self.hifreq.value()
        lf=self.lofreq.value()
        self.lfvalue.setText(f'{lf} Hz')
        self.parea.filterStrength((lf,hf))
        config['gui']['low_freq']=lf

    def createButtonsProcessing(self):

        picfrm=QFrame()
        chofrm=QFrame()
        tunfrm=QFrame()
        btnfrm=QFrame()

        # ----- PICK BOX
        self.pickbox=statusText(picfrm,(10,0),(170,self.h_cmd-30))
        pick_clr=cmdButton(picfrm, 'CLEAR', (200,10), (60,30),self.clearpick) 
        pick_plt=cmdButton(picfrm, 'PLOT', (200,40), (60,30), self.plotpick)

        # ----- VIEW CONTROLS
        self.zoom=chkButton(chofrm, 'ZOOM', (0,5), (160,40), self.zoom_plot)
        self.autos=chkButton(chofrm, 'AUTOSCALE', (0,35), (160, 40), self.auto_scale)
        self.filt=chkButton(chofrm, 'FILTER', (0,65), (160,40), self.toggle_filter)
        self.fillplot=chkButton(chofrm, 'FILL TRACE', (0,95), (160,40), self.toggle_fillplot)
        self.autos.setChecked(True)
        self.filt.setChecked(True)
        self.fillplot.setChecked(True)

        # ----- TUNNING
        self.tracesel=bigLabel(tunfrm, 'Selected: None',(0,0,500,20))
        bigLabel(tunfrm, 'HIGH FREQ', (0,25,100,20))
        bigLabel(tunfrm, 'LOW FREQ', (0,45,100,20))

        self.hfvalue=bigLabel(tunfrm, '', (320,25,80,20))
        self.lfvalue=bigLabel(tunfrm, '', (320,45,80,20))

        self.hifreq=scroller(tunfrm, (110,30,200,20), (0,50,1), self.hf_tune)
        self.lofreq=scroller(tunfrm, (110,50,200,20), (0,50,1), self.lf_tune)

        self.hifreq.setValue(50)
        self.lofreq.setValue(0)

        # ----- Buttons

        selbtn=cmdButton(btnfrm, 'Select All', (0,10), (130,30), 
                         lambda:self.parea.selectAll())
        clrbtn=cmdButton(btnfrm, 'Clear Selection', (0,40), (130,30), 
                         lambda:self.parea.clearSelection())
        labbtn=cmdButton(btnfrm, 'Rearrange', (0,70), (130,30), 
                         lambda:self.parea.sequenceNames())
        labbtn=cmdButton(btnfrm, 'Normalize', (0,100), (130,30), 
                         lambda:self.parea.normalize())

        lout=QHBoxLayout()
        lout.addWidget(picfrm,2)
        lout.addWidget(chofrm,1)
        lout.addWidget(tunfrm,3)
        lout.addWidget(btnfrm,1)

        h=self.height()-self.h_cmd;
        self.procbox=QFrame(self)
        self.procbox.resize(self.width(),self.h_cmd)
        self.procbox.move(0,h)
        self.procbox.setLayout(lout)
        self.tunning=tunfrm
        self.tunning.setEnabled(False)

    def sync_info(self):
        p=self.parea.selected

        if len(p)==1:
            # FIXME: using the first selected trace
            self.tunning.setEnabled(True)
            lf=p[0].freq[0]
            hf=p[0].freq[1]
            self.lofreq.setValue(int(lf))
            self.hifreq.setValue(int(hf))

        else:
            self.tunning.setEnabled(False)


        if p:
            st="Selected: "
            for trc in p:
                st+=trc.name+' '
                if len(st)>36:
                    st+="..."
                    break
        else:
            st="Selected: none"

        self.tracesel.setText(st)

    def createButtons(self):
        self.createButtonsProcessing()

    def createWin(self,w,h):
        self.createMenus()
        self.createDrawArea()
        self.createButtons()
        
        ctrx=int((w-self.width())/2)
        ctry=int((h-self.height())/2)
        self.move(ctrx,ctry)
        if config['gui']['winmode'].find('max') == 0:
            self.showMaximized()

    def zoom_plot(self):
        self.parea.zoomAll(not self.zoom.isChecked())

    def toggle_filter(self):
        self.parea.enableFilter(self.filt.isChecked())

    def toggle_fillplot(self):
        self.parea.enableFillplot(self.fillplot.isChecked())

    def auto_scale(self):
        self.parea.autoScale(self.autos.isChecked())

    def show_info(self,msg):
        infoDialog(self,msg)

    def resizeEvent(self,event):
        # FIXME
        r=self.geometry()
        self.plth=r.height()-self.h_cmd-self.menuBar().height()-10
        self.parea.changeBox(self.width(),self.plth)
        self.procbox.resize(self.width(),self.h_cmd);
        self.procbox.move(0,self.height()-self.h_cmd);

    def pick(self,data):
        # Record picked data
        # This data will not be saved in file!
        ss=self.pickbox.toPlainText()
        if ss=='':
            ss+='trace(%02d) %0.6f'%(data[0]+1, data[1])
        else:
            ss+='\ntrace(%02d) %0.6f'%(data[0]+1, data[1])

        self.pickbox.setText(ss)
        m=self.pickbox.verticalScrollBar().maximum()
        self.pickbox.verticalScrollBar().setValue(m)

    def clearpick(self):
        self.pickbox.setText('')
        self.parea.clearpick()

    def plotpick(self):
        # plot pick points in the pick box, not from trace's pick data!

        pd=self.pickbox.toPlainText()
        if pd == '': return
        pd=pd.split('\n')
        tck=[]
        tlab=[]
        pck=[]
        for s in pd:
            s=s.strip()
            if s.find('trace(') == 0:
                s=s.split()
                try:
                    tlab.append(s[0].replace('trace(','').replace(')',''))
                    pck.append(float(s[1]))
                except:
                    pass
        for i in range(len(tlab)):
            tck.append(i)
        
        plt.xticks(tck,tlab)
        plt.ylabel('time')
        plt.xlabel('trace')
        plt.grid()
        plt.plot(pck,'*')
        plt.show()

    def save_data(self, fnm=''):
        if not fnm:
            fnm=QFileDialog.getSaveFileName(self, 'Save File', 'newfile.json')
            fnm=fnm[0]

        if(fnm):
            # Pick data is taken from traces
            dd=self.parea.getData()
            dd['config']=config
            with open(fnm,'w') as f:
                json.dump(dd,f)
    
    def combine_data(self,flst):
        '''
        Strategy:
        - take the shortest data
        - average time
        '''
        chdata={}
        chtime={}
        dlen=[]
        nm=0
        flst.sort()

        for fnm in flst:
            with open(fnm) as fl: data=json.load(fl)
            
            try:
                chtime[nm]=data['time']
            except:
                print(f'bad data file: {fnm}')
                continue

            nf=0
           
            while True:
                chan='channel-%02d'%nf
                try:
                    dd=data[chan]
                    chdata[chan+'_%02d'%nm]=dd
                    dlen.append(len(dd))
                except:
                    break

                nf+=1
            
            if nf: nm+=1
            
        dlen=min(dlen)

        timeaxis=[]
        dt=0

        for nm in chtime:
            dt+=(chtime[nm][dlen-1]-chtime[nm][0])

        dt/=len(chtime)*dlen

        for t in range(dlen):
            timeaxis.append(dt*t)

        savedata={'time':timeaxis}
        for chn in chdata:
            savedata[chn]=[]
            for i in range(dlen):
                savedata[chn].append(chdata[chn][i])

        fd,fname=tempfile.mkstemp()
        with os.fdopen(fd,'w') as cfl:
            json.dump(savedata,cfl)

        return fname

    def open_data(self):
        remove_after=False

        if file_to_open=='':
            fdlg=QFileDialog()
            fnm,ok=fdlg.getOpenFileNames(self, 'Open File', filter='*.json')
            if not ok: return

            if len(fnm)>1:
                fnm=self.combine_data(fnm)
                remove_after=True
            else:
                fnm=fnm[0]

        else:
            fnm=file_to_open

        if not os.path.exists(fnm): return
 
        with open(fnm) as fl:
            data=json.load(fl)
            chnfound=False

            # FIXME
            for key in data:
                if key.find('channel-') == 0:
                    if not len(data[key]): 
                        chfound=False
                        break
                    else:
                        chnfound=True
            
            if not chnfound:
                QMessageBox.about(self, 'Alert', f'File tidak memiliki data\n{fnm}')
                return

            self.parea.assignData(data, True, True)
            self.parea.arrangeTraces()
            self.parea.normalize()

        self.zoom_plot()

        nd=len(self.parea.timeaxis)
        tt=self.parea.timeaxis[nd-1]-self.parea.timeaxis[0]
        self.pickbox.setText('')

        if remove_after: 
            os.remove(fnm)

    def load_cfg(self):

        cnm=QFileDialog.getOpenFileName(self, 'Open Configuration', filter='*.json')
        cnm=cnm[0]
        
        if cnm:
            if read_cfg(cnm):
                self.restart_app()
            else:
                QMessageBox.information('failure', 'Invalid configuration file')

    def config_save(self):
        fnm=QFileDialog.getSaveFileName(self, 'Save Configuration', 
                'config.json', filter="*.json")
        fnm=fnm[0]
        if fnm:
            with open(fnm,'w') as cfg:
                json.dump(config,cfg)


class SeismoApp(QApplication):
    def __init__(self):
        global scrgeo, log_message
        super(SeismoApp, self).__init__(sys.argv)
        
        self.setApplicationName('SeismoLog Trace Editor')
        scrgeo=self.primaryScreen().size()

        if css != '': self.setStyleSheet(css)
        self.guiwin=SeismoWin(scrgeo.width(), scrgeo.height())

try:    
    while restart:
        restart=False
        SeismoApp().exec()
except Exception as e:
    print('SEISMOLOG EXECUTION ERROR')
    print(e)
    raise

