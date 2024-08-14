#---------------------------------
# Seismic Instrument Qt Application
#
# Trace Editor
#
# (c) 2022, Rosandi
#
# rosandi@geophys.unpad.ac.id
#

from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtWidgets import (
        QFrame, 
        QDialog, 
        QScrollBar, 
        QLabel, 
        QPushButton, 
        QCheckBox,
        QToolTip
)
from PyQt5.QtGui import QPainter, QColor, QFont, QPainterPath, QPen, QBrush, QPixmap, QPolygon
from strace import trace
import numpy as np

color_map=['red','darkRed','magenta','darkMagenta','green','darkGreen']

class plotter(QFrame):

    def __init__(self, master, geo=None, name='',):
        super(plotter,self).__init__(master)

        if geo:
            r=geo
        else:
            r=master.geometry()

        self.master=master
        self.move(r.x(),r.y())
        self.resize(r.width(),r.height())
        self.setStyleSheet('background-color: white;')
        self.traces=[]
        self.timeaxis=[]
        self.selected=[] # selected trace
        self.zoomall=False
        self.mx=0
        self.my=0
        self.running=False
        self.once=True
        self.pick_function=None
        self.indicator=(self.width()//2, 0)
        self.show_indicator=True
        self.scrimg=QPixmap(self.width(), self.height())
        self.btn_decay=False
        self.drag=False
        self.roll=False
        self.setMouseTracking(True)
        self.onblock=False
        self.block={}
        self.nstack=0
        self.minbwidth=2

    def arrangeTraces(self):
        lt=len(self.traces)
        dw=self.height()-30 # 30 reserved for label
        pw=dw/lt
        for trc in range(len(self.traces)):
            self.traces[trc].setPosition((0,(trc*pw), self.width(), pw))

    def addTrace(self, data, name):
        if name == '':
            name='trace-%02d'%len(traces)

        tid=len(self.traces)

        self.traces.append(
            trace(self,data,geo=(0,0,self.width(),0),name=name,
            color=QColor(color_map[tid%len(color_map)]))
        )

        self.arrangeTraces()
        self.repaint()
        return tid # trace id

    def updateTrace(self, tid, data, repaint=False):
        self.traces[tid].data=data
        if repaint:
            self.repaint()

    def trimdata(self, off):
        if len(self.timeaxis) == 0: 
            return

        off-=self.timeaxis[0]

        while self.timeaxis[0] < off:
            self.timeaxis.pop(0)
            for t in self.traces:
                t.data.pop(0)

        n=len(self.timeaxis)
        for i in range(n):
            self.timeaxis[i]-self.timeaxis[0]

        for t in self.traces:
            t.dirty=True
            t.tmax=self.timeaxis[n-1]

    def append(self, taxis, val): # append a single data to each trace
        self.timeaxis.append(taxis)
        for t in range(len(self.traces)):
            self.traces[t].data.append(val[t])
            self.traces[t].dirty=True
            self.traces[t].tmax=taxis-self.timeaxis[0]

        if self.roll:
            # FIXME: roll in the zoom width
            pass

    def getTimeLimit(self):
        # reduced by first data time
        if self.timeaxis == [] or self.traces[0].data == []:
            self.plotlimit=(0,0)
            return (0,0)

        t=self.plotlimit
        t0=self.timeaxis[0]
        return (self.timeaxis[t[0]]-t0, self.timeaxis[t[1]-1]-t0)

    def sequenceNames(_):
        for i in range(len(_.traces)):
            trc=_.traces[i]
            trc.name='channel-%02d'%i

        _.clearSelection()
        _.master.sync_info()
        _.once=True
        _.repaint()

    def getData(_):
        '''
        rename data to 'channel-XX' sorted by trace position

        format,
            time: array(data_length)
            channel-XX: array(data_length), ...
            scale: array(channel_num)
            filter: array(channel_num)

        '''

        dd={}
        dd['time']=_.timeaxis
        scl=[]
        flt=[]
        ofs=[]
        ptm=[]

        for i in range(len(_.traces)):
            trc=_.traces[i]
            trc.name='channel-%02d'%i
            dd[trc.name]=trc.data
            scl.append(trc.scale)
            flt.append(trc.freq)
            ofs.append(trc.voffset)
            ptm.append((i,trc.picktime))

        dd['scale']=scl
        dd['offset']=ofs
        dd['filter']=flt
        dd['pick']=ptm

        _.once=True
        _.repaint()

        return dd

    def assignData(self,data, stretch=False, auto=False):
        
        found=False
        if 'time' in data:
            self.clear()
            self.timeaxis=data['time']
            self.plotlimit=(0,len(data['time']))
        else:
            return
       
        self.traces=[]
        for key in data:
            if key.find('channel-') == 0: # FIXME
                self.addTrace(data[key], name=key)
                self.plotlimit=(0,0)
                found=True

        if not found:
            self.clear()
        else:
            # FIXME: these two lines are not needed
            self.setStretch(stretch)
            self.autoScale(auto)

            for trc in self.traces:
                trc.tmax=self.timeaxis[len(self.timeaxis)-1]-self.timeaxis[0]

            if 'scale' in data:
                for i in range(len(data['scale'])):
                    self.traces[i].scale=data['scale'][i]

            if 'filter' in data:
                for i in range(len(data['filter'])):
                    order=2
                    if(len(data['filter'][i])==3): 
                        order=data['filter'][i][2]

                    self.traces[i].freq=(data['filter'][i][0], data['filter'][i][1],order)

        self.once=True
        self.repaint()

    def setScales(self,scales):
        if self.selected:
            for i in range(len(self.traces)):
                if self.traces[i].selected:
                    self.traces[i].scale=scales[i]
        else:
            for i in range(len(self.traces)):
                self.traces[i].scale=scales[i]

        self.once=True
        self.repaint()

    def autoScale(_,scl):
        for trc in _.traces:
            trc.autoscale=scl

        _.once=True
        _.repaint()

    def magnify(_,mag):
        if _.selected:
            for trc in _.selected:
                trc.scale*=mag
        _.once=True
        _.repaint()

    def normalize(_):
        # normalize time axis: start from 0
        tmax=_.timeaxis[-1]-_.timeaxis[0]
        ln=len(_.timeaxis)

        _.timeaxis=np.linspace(0,tmax,ln).tolist()

        if _.selected:
            for trc in _.selected:
                trc.normalize()
        else:
            for trc in _.traces:
                trc.normalize()

    def adjustViewOffset(_, ofs):
        # do not alter the data offset
        if _.selected:
            for trc in _.selected:
                trc.voffset+=ofs

        _.once=True
        _.repaint()

    def getScales(self):
        scales=[]
        for trc in self.traces:
            scales.append(trc.scale)
        return scales
   
    def setThreshold(self, thr):
        for trc in self.traces:
            trc.threshold=thr

    def changeBox(self,width, height):
        self.setGeometry(self.x(),self.y(),width,height)
        self.scrimg=QPixmap(width,height) 
        #self.scrimg.scaled(width,height,Qt.IgnoreAspectRatio)
        self.once=True
        self.arrangeTraces()

        #for trc in self.traces:
        #    trc.dim=(width,height/len(self.traces))

    def run(self, stat):
        self.running=stat

    def enableFilter(self, ef):
        for trc in self.traces:
            trc.filter=ef
            trc.dirty=True
            #print('update trace filter', trc.name)

        if self.timeaxis:
            self.normalize()

        self.once=True
        self.repaint()

    def enableFillplot(_,ef):
        for trc in _.traces:
            trc.fillarea=ef
        _.once=True
        _.repaint()

    def filterStrength(self, freq, order=2):
        freq=(freq[0],freq[1],order)
        if self.selected:
            for trc in self.traces:
                if trc.selected:
                    trc.freq=freq
                    trc.dirty=True
        else:
            for trc in self.traces:
                trc.freq
                trc.dirty=True

        self.once=True
        self.repaint()

    def adjustFrequency(self, hilo, finc):
        for trc in self.selected:
            ff=trc.freq

            if hilo=='low':
                nf=ff[0]+finc
                fa=ff
                if nf>0 and nf<50: 
                    if abs(nf-ff[1])>self.minbwidth:
                        fa=(nf,ff[1],ff[2])

            elif hilo=='high':
                nf=ff[1]+finc
                fa=ff
                if nf>0 and nf<50:
                    if abs(nf-ff[0])>self.minbwidth:
                        fa=(ff[0],nf,ff[2])

            # ffprint(trc.name,fa)
            trc.dirty=True
            trc.freq=fa

        self.once=True
        self.repaint()
        self.master.sync_info()

    def getFilterSettings(self):
        fset=[]
        for trc in self.traces:
            fset.append((trc.freq[0],trc.freq[1],trc.filtorder))
        return fset

    def setStretch(self, st):
        for trc in self.traces:
            trc.stretch=st
            trc.dirty=True

    def paintEvent(self, event):
        p=QPainter(self.scrimg)

        if self.running or self.once:
            p.eraseRect(self.rect())

            for trc in self.traces:
                trc.dim=(self.width()-trc.pos[0], trc.dim[1])
                # if plt.name=='channel-01': plt.selected=True
                trc.axis(p)
                trc.plot(p)

            self.once=False

        tt=self.getTimeLimit()
        pc=QPainter(self)
        pc.drawPixmap(0,0,self.scrimg)
        pc.setPen(QPen(Qt.black, 1, Qt.SolidLine))
        pc.drawText(2, self.height()-20, 120, 30, Qt.AlignLeft, '<%0.3f'%tt[0])
        pc.drawText(self.width()-82, self.height()-20, 80, 30, Qt.AlignRight, '%0.3f>'%tt[1])
        
        indi=self.indicator[0]
        
        if self.show_indicator:
            pc.setPen(QPen(Qt.red, 2, Qt.DashLine))
            pc.drawLine(indi, 0, indi, self.height())

            if self.drag:
                pts=[QPoint(0,5), QPoint(10, 0), QPoint(30,0), 
                        QPoint(40,5), QPoint(30,10), QPoint(10,10)]
                din=QPolygon(pts)
                din.translate(indi-20,3)
                pc.setPen(QPen(Qt.red, 1, Qt.SolidLine))
                pc.setBrush(QBrush(Qt.yellow, Qt.SolidPattern))
                pc.drawPolygon(din)

            if self.timeaxis != []:
                ix=0
                if not indi == 0:
                    ix=self.getTimeLimit()
                    ix=ix[0]+(ix[1]-ix[0])*indi/self.width()

                #pc.setFont(QFont('Decorative', 12))
                pc.setFont(QFont('Arial', 12))
                pc.setPen(QPen(Qt.red, 1, Qt.SolidLine))
                if indi<self.width()//2:
                    pc.drawText(indi, self.height()-20,120,50,
                            Qt.AlignLeft, '<%0.6f'%ix)
                else:
                    pc.drawText(indi-120, self.height()-20,120,50,
                            Qt.AlignRight, '%0.6f>'%ix)

        # --- draw block area
        if self.onblock:
            pc.setPen(QPen(Qt.red, 1, Qt.NoPen))
            pc.setBrush(QBrush(QColor(100, 100, 100, 100), Qt.SolidPattern))
            w=indi-self.block['begin']
            pc.drawRect(self.block['begin'], 0, w, self.height())
        elif 'end' in self.block:
            pc.setPen(QPen(Qt.red, 1, Qt.NoPen))
            pc.setBrush(QBrush(QColor(100, 100, 100, 100), Qt.SolidPattern))
            w=self.block['end']-self.block['begin']
            pc.drawRect(self.block['begin'], 0, w, self.height())

    def setZoom(self,zz):
        # zz is the number of data in a zoom view
        for trc in self.traces:
            trc.zoomall=False
            trc.zoom=zz

    def zoomAll(_,z):
        _.zoomall=z
        for trc in _.traces: 
            trc.zoomall=_.zoomall

        _.once=True
        _.repaint()

    def autoPan(_,pan):
        for trc in _.traces:
            trc.autopan=pan

    def clear(_):
        _.autoPan(True)
        _.timeaxis=[]
        _.nstack=0
        for c in range(len(_.traces)):
            _.traces[c].data=[]
            _.traces[c].plotlimit=(0,0)
        _.once=True
        _.repaint()
    
    def clearpick(_):
        for trc in _.traces:
            trc.pickpoint=-1
        _.once=True
        _.repaint()

    def pick(_):
        lt=len(_.traces)
        dw=_.height()-30 # 30 reserved for label
        pw=dw/lt

        ix=int(_.indicator[1]/pw)
        # FIXME: on zoom & pan condition?
        iy=_.getTimeLimit()
        tp=iy[0]+(iy[1]-iy[0])*_.indicator[0]/_.width()

        if ix>=lt:
            ix=lt-1
        
        tt=int(len(_.timeaxis)*tp/(_.timeaxis[-1] - _.timeaxis[0]))
        _.traces[ix].pickpoint=tt
        _.traces[ix].picktime=tp

        if _.pick_function != None:
            _.pick_function((ix,tp))

        _.once=True
        _.repaint()

    def getrange(_):
        if 'end' in _.block:
            bb=_.block
            a=min(bb['begin'],bb['end'])
            b=max(bb['begin'],bb['end'])
            tx=_.timeaxis
            ltx=_.plotlimit[1] - _.plotlimit[0]

            ia=ltx*a//_.width()
            ib=ltx*b//_.width()

            return ia,ib

        else:
            return 0, 0

    def showinfo(_):
        if not _.selected:
            _.seltrace()

        tinfo='<h1>Trace Information</h1>'
        tinfo+=f'Data length: {len(_.timeaxis)}<br>'
        ta,tb=_.timeaxis[0],_.timeaxis[-1]
        tinfo+=f'Time range: %0.2f seconds (%0.2f, %0.2f)<br>'%(tb-ta,ta,tb)
        for trc in _.selected:
            tinfo+=f'<br><b>{trc.name}</b>'
            tinfo+='<table width="100%" style="margin-left:10px">'
            tinfo+='<tr><td width="30%">'
            tinfo+='data range </td><td> (%0.4f, %0.4f)</td></tr>'%(trc.datarange[0],trc.datarange[1])
            tinfo+='<tr><td>view scale</td><td> %0.2f</td></tr>'%trc.scale
            tinfo+='<tr><td>view offset</td><td> %0.2f pixels</td></tr>'%trc.voffset
            tinfo+='<tr><td>filter</td><td> (%0.1fHz %0.1fHz order:%d)</td></tr>'%(trc.freq[0],trc.freq[1],trc.freq[2])
            tinfo+='</table><br>'
            
        _.master.show_info(tinfo)

# ----- ACTIONS:
    def muteblock(_):
       
        ia,ib=_.getrange()

        if _.selected:
            for trc in _.selected:
                for t in range(ia,ib+1):
                    trc.data[t]=0.0
                    trc.dirty=True
        else:
            for trc in _.traces:
                # print(trc.name, "muted",(ia,ib),len(trc.data))
                for t in range(ia,ib+1):
                    trc.data[t]=0.0
                    trc.dirty=True

        _.normalize()
        _.once=True
        _.repaint()

    def cutblock(_):
        ia,ib=_.getrange()
        nc=ib-ia

        # time is contiguous: cut end
        _.timeaxis=_.timeaxis[:-nc]
        tmax = _.timeaxis[-1] - _.timeaxis[0]

        for trc in _.traces:
            for i in range(ib-ia):
                trc.data.pop(ia)
            trc.dirty=True
            trc.tmax=tmax

        _.once=True
        _.repaint()

    def moveup(_):
        if _.selected:
            nt=len(_.traces)
            tmp=[None]*nt
            tid=[]

            for t in range(nt):
                if _.traces[t].selected:
                    tid.append(t)
            
            if tid[0] == 0:
                return

            for t in tid:
                tmp[t-1]=_.traces[t]
                _.traces[t]=None

            for t in range(nt):
                if _.traces[t] == None: continue
                for r in range(nt):
                    if tmp[r] != None: continue
                    tmp[r] = _.traces[t]
                    break

            _.traces=tmp
            _.arrangeTraces()
            _.once=True
            _.repaint()

    def movedown(_):
        if _.selected:
            nt=len(_.traces)
            tmp=[None]*nt
            tid=[]

            for t in range(nt):
                if _.traces[t].selected:
                    tid.append(t)
            
            if tid[-1] == nt-1:
                return

            for t in tid:
                tmp[t+1]=_.traces[t]
                _.traces[t]=None

            for t in range(nt):
                if _.traces[t] == None: continue
                for r in range(nt):
                    if tmp[r] != None: continue
                    tmp[r] = _.traces[t]
                    break

            _.traces=tmp
            _.arrangeTraces()
            _.once=True
            _.repaint()
            
    def deltrace(_):
        if _.selected:
            idtodel=[]

            for t in range(len(_.traces)):
                if _.traces[t].selected:
                    idtodel.append(t)

            idtodel.sort(reverse=True)

            for i in idtodel:
                if len(_.traces)>1:
                    _.traces.pop(i)
        
            _.arrangeTraces()
            _.once=True
            _.repaint()

    def seltrace(_):
        for trc in _.traces:
            iy=_.indicator[1]
            if iy > trc.pos[1] and iy < trc.pos[1]+trc.dim[1]:
                trc.selected=not trc.selected

        _.selected=[]
        for trc in _.traces:
            if trc.selected:
                _.selected.append(trc)

        _.once=True
        _.repaint()
        _.master.sync_info()

    def stacktraces(_):
        data=[0]*len(_.timeaxis)
        tid=[]

        for i in range(len(_.traces)):
            if _.traces[i].selected:
                tid.append(i)

        if len(tid)<2: return

        for t in tid:
            dt=_.traces[t].data
            for i in range(len(dt)):
                data[i]+=dt[i]

        for i in range(len(data)):
            data[i]/=len(tid)

        tid.sort(reverse=True)
        for i in tid[:-1]:
            _.traces.pop(i)

        tid=tid[-1]
        _.traces[tid].data=data
        _.traces[tid].name='stack-%02d'%_.nstack
        _.traces[tid].dirty=True

        _.arrangeTraces()
        _.once=True
        _.repaint()
        _.nstack+=1

    def clearSelection(_):
        for trc in _.selected:
            trc.selected=False

        _.selected=[]
        _.master.sync_info()
        _.once=True
        _.repaint()
    
    def selectAll(_):
        for trc in _.traces:
            trc.selected=True

        _.selected=[]
        for trc in _.traces:
            _.selected.append(trc)

        _.once=True
        _.repaint()

# ---- EVENTS:
    def mouseDoubleClickEvent(self,ev):
        self.seltrace()

    def _decay_ends(self):
        self.btn_decay=False
    
    def mousePressEvent(self,ev):
        self.mx=ev.x()
        self.my=ev.y()
        
        if ev.buttons() == Qt.LeftButton:
            if self.drag:
                self.drag=False
                self.once=True
                self.repaint()
            else:
                self.btn_decay = True
                QTimer().singleShot(500, self._decay_ends)

    def mouseMoveEvent(self,ev):
        
        self.setFocus()
        self.indicator=(ev.x(), ev.y())
       
        if self.btn_decay or ev.buttons() == Qt.RightButton:
            self.drag = True

        if self.drag:
            self.once=True
            if ev.x()!=self.mx:
                dx=ev.x()-self.mx
                self.mx=ev.x()
                for trc in self.traces:
                    trc.panshift(dx)

        self.repaint()

    def keyPressEvent(_,ev):
        if ev.key() == Qt.Key_B:
            if _.onblock:
                _.block['end']=_.indicator[0]
                _.onblock=False
            else:
                _.block={}
                _.block['begin']=_.indicator[0]
                _.onblock=True
            _.once=True
            _.repaint()

        elif ev.key() == Qt.Key_Home or ev.key() == Qt.Key_0:
            if _.onblock:
                _.block['end'] = 0
                _.onblock=False
                _.once=True
                _.repaint()

        elif ev.key() == Qt.Key_End or ev.key() == Qt.Key_9:
            if _.onblock:
                _.block['end']=_.width()-1
                _.onblock=False
                _.once=True
                _.repaint()

        elif ev.key() == Qt.Key_Q:
            _.onblock=False
            _.block={}
            _.once=True
            _.repaint()

        elif ev.key() == Qt.Key_Escape:
            _.onblock=False
            _.block={}
            _.clearSelection()

        elif ev.key() == Qt.Key_M:
            _.muteblock()

        elif ev.key() == Qt.Key_C:
            _.cutblock()

        elif ev.key() == Qt.Key_P:
            _.pick()

        elif ev.key() == Qt.Key_D:
            _.deltrace()

        elif ev.key() == Qt.Key_Space:
            _.seltrace()

        elif ev.key() == Qt.Key_Up:
            _.moveup()

        elif ev.key() == Qt.Key_Down:
            _.movedown()

        elif ev.key() == Qt.Key_I:
            _.showinfo()

        elif ev.key() == Qt.Key_Plus:
            _.magnify(1.2)

        elif ev.key() == Qt.Key_Equal:
            _.magnify(1.2)

        elif ev.key() == Qt.Key_Minus:
            _.magnify(1/1.2)

        elif ev.key() == Qt.Key_H:
            _.adjustViewOffset(1)

        elif ev.key() == Qt.Key_J:
            _.adjustViewOffset(-1)

        elif ev.key() == Qt.Key_BracketLeft:
            _.adjustFrequency('low',-1)

        elif ev.key() == Qt.Key_BracketRight:
            _.adjustFrequency('low',1)

        elif ev.key() == Qt.Key_BraceLeft:
            _.adjustFrequency('high',-1)

        elif ev.key() == Qt.Key_BraceRight:
            _.adjustFrequency('high',1)

