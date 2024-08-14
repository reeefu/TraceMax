from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QPainter, QColor, QFont, QPainterPath, QPen, QBrush, QPixmap, QPolygon
import scipy.signal as sg

class trace:
    def __init__(self, master, dat, geo=None, name='',color=None):
        self.name=name
        
        if geo == None:
            r=master.geometry()
            geo=(r.x(),r.y(),r.width(), r.height())
        
        self.setPosition(geo)

        self.scale=1.0
        self.basescale=1.0
        self.zoom=500
        self.xpan=0
        self.master=master
        self.datarange=(0,0)
        self.tmax=0
        self.data=dat
        self.vdata=dat
        self.zoomall=True
        self.invert=False
        self.autoscale=False
        self.threshold=0
        self.autopan=True
        self.filter=True
        self.dirty=True
        self.stretch=False
        self.freq=(8.0,25.0,2) # in Hz: (lf, hf, order)
        self.selected=False
        self.highlight=False
        self.fillarea=True
        self.voffset=0
        self.pickpoint=-1  # pick array index. negative: no pick
        self.picktime=0.0

        if not color is None:
            self.color=color
        else:
            self.color=Qt.red

    def setPosition(self,geo):
        self.pos=(geo[0],geo[1]) # position: x,y
        self.dim=(geo[2],geo[3]) # dimension: width, height
        self.base=geo[1]+geo[3]//2

    def panshift(self, dx):
        self.xpan-=dx
        maxpan=len(self.data)-self.zoom
        self.autopan=False

        if self.xpan>=maxpan:
            self.xpan=maxpan
            self.autopan=True

        if self.xpan<0:
            self.xpan=0

    def filtering(self):
        vd=self.data
        if self.tmax:
            fm=0.5*len(self.data)/self.tmax
            
            fl=min(self.freq[0],self.freq[1])
            fh=max(self.freq[0],self.freq[1])

            try:
                wa=fl/fm
                wb=fh/fm
                if wa==0: wa=0.001
                if wb>=1: wb=0.999
                order=2
                if len(self.freq)==3: order=self.freq[2]
                butt=sg.butter(order, (wa, wb), btype='band', analog=False)
                vd=sg.filtfilt(butt[0], butt[1], self.data)
            except Exception as e:
                print(e)  #FIXME
                vd=self.data

        return vd

    def normalize(self):
        '''
        normalize 
        - scale and set the base scale
        - remove offset in data by average
        '''
        
        mi=1e8
        ma=-1e8
        avg=0.0
        dmi=1e12
        dma=-1e12

        nd=len(self.data)
        if not nd:
            return

        for i in range(nd): 
            avg+=self.data[i]
            if dmi>self.data[i]: dmi=self.data[i]
            if dma<self.data[i]: dma=self.data[i]

        avg/=nd
        self.datarange=(dmi-avg,dma-avg)
        
        # normalize offset
        for i in range(nd): self.data[i]-=avg

        for m in self.data:
            if ma<m:
                ma=m
            if mi>m:
                mi=m

        amp=(abs(ma-mi)>self.threshold)
        
        if amp and mi<ma:
            ma=abs(ma)
            mi=abs(mi)
            self.scale=0.5*self.dim[1]/max(mi,ma)
            
        else:
            print(f'{self.name}: amplitude less than threshold')
            self.scale=1.0

        self.dirty=True
        self.basescale=self.scale

    def axis(self,p):
        px=int(self.pos[0])
        py=int(self.pos[1])
        pw=int(self.dim[0])
        ph=int(self.dim[1])
        base=int(self.base)

        p.save()
        
        if self.selected:
            p.setPen(QPen(QColor(247, 220, 111,100), 1, Qt.DashLine))
            p.setBrush(QBrush(QColor(252, 243, 207),Qt.SolidPattern))
            p.drawRect(px, py, pw, ph)

        elif self.highlight:
            p.setPen(QPen(QColor(253, 254, 254,100), 1, Qt.DashLine))
            p.setBrush(QBrush(QColor(252, 243, 207),Qt.SolidPattern))
            p.drawRect(px, py, pw, ph)

        p.restore()

        p.setPen(QPen(Qt.gray, 1, Qt.DashLine))
        p.drawLine(px, base, px+pw, base)

    def plot(self,p):

        if self.data == []: 
            return None
        
        if self.dirty:

            if self.filter and len(self.data)>25: # FIXME
                self.vdata=self.filtering()
            else:
                self.vdata = self.data

            self.dirty=False

        xmax=len(self.vdata)
        
        # zoom all if data_number > zoom_mumber
        if self.zoomall:
            zo=xmax
            ofs=0
        else:
            zo=self.zoom
            if zo>=xmax: zo=xmax
            
            if self.autopan:
               ofs=xmax-zo
            else:
                ofs=self.xpan

            if ofs<0: ofs=0
            if ofs>(xmax-zo): ofs=xmax-zo

        # FIXME: master should calculate this
        self.master.plotlimit=(ofs,ofs+zo)

        dview=[]
        for d in range(ofs, ofs+zo):
            if d > xmax:
                break
            dview.append(self.vdata[d]*self.scale)

        # DEBUG
        # self.autoscale=False

        if self.autoscale:
            mi=1e8
            ma=-1e8
            for m in dview:
                if ma<m:
                    ma=m
                if mi>m:
                    mi=m
            
            amp=(abs(ma-mi)>self.threshold)

            if amp and mi<ma:
                ma=abs(ma)
                mi=abs(mi)
                sc=0.5*self.dim[1]/max(mi,ma)
                for i in range(len(dview)):
                    dview[i]*=sc

        x=self.pos[0]

        if self.stretch or self.zoom<zo:
            dx=(float(self.dim[0])/zo)
        else:
            dx=float(self.dim[0])/self.zoom
        
        yzero=int(self.base)
        # print(self.name,self.base, self.voffset)

        line=QPainterPath()

        if self.fillarea: line.moveTo(x,yzero)

        if self.invert:
            if self.fillarea:
                line.lineTo(x,yzero+dview[0]-self.voffset)
            else:
                line.moveTo(x,yzero+dview[0]-self.voffset)

            for d in range(1,len(dview)):
                line.lineTo(x,yzero+dview[d]-self.voffset)
                x+=dx

        else:
            if self.fillarea:
                line.lineTo(x,yzero-dview[0]-self.voffset)
            else:
                line.moveTo(x,yzero-dview[0]-self.voffset)

            for d in range(1,len(dview)):
                line.lineTo(x,yzero-dview[d]-self.voffset)
                x+=dx
        
        if self.fillarea: 
            line.lineTo(x,yzero)
            p.setBrush(QBrush(self.color,Qt.SolidPattern))

        p.setPen(QPen(self.color, 2, Qt.SolidLine))
        p.setRenderHint(QPainter.Antialiasing)
        p.drawPath(line)

        if self.pickpoint>=self.xpan:
            dp=int(self.pickpoint*dx)
            p.setPen(QPen(Qt.black, 1, Qt.NoPen))
            pcl=QColor(self.color)
            pcl.setAlpha(60)
            p.setBrush(QBrush(pcl, Qt.SolidPattern))
            p.drawEllipse(dp-10, yzero-10, 20, 20)
            p.setPen(QPen(Qt.black, 1, Qt.SolidLine))
            p.drawLine(dp,yzero-10,dp,yzero+10)

        p.setPen(QPen(Qt.black, 1, Qt.SolidLine))
        p.setFont(QFont('Arial', 12))
        p.drawText(5, yzero, 100, int(self.dim[1]), Qt.AlignTop, self.name)

        self.xpan=ofs

 
