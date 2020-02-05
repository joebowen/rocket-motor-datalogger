###################################################################
#                                                                 #
#                    PLOT A LIVE GRAPH (PyQt5)                    #
#                  -----------------------------                  #
#            EMBED A MATPLOTLIB ANIMATION INSIDE YOUR             #
#            OWN GUI!                                             #
#                                                                 #
###################################################################

import os
import time
import threading
import numpy as np
import pandas as pd
import matplotlib
import fcntl

from usb_20x import *

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from matplotlib import pyplot as plt
from matplotlib.figure import Figure
from matplotlib.animation import TimedAnimation
from matplotlib.lines import Line2D
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

matplotlib.use("Qt5Agg")


class CustomMainWindow(QMainWindow):
    def __init__(self):
        global nchan

        super(CustomMainWindow, self).__init__()
        # Define the geometry of the main window
        self.setGeometry(300, 300, 800, 400)
        self.setWindowTitle("Load Cell Test")
        # Create FRAME_A
        self.FRAME_A = QFrame(self)
        self.FRAME_A.setStyleSheet("QWidget { background-color: %s }" % QColor(210,210,235,255).name())
        self.LAYOUT_A = QGridLayout()
        self.FRAME_A.setLayout(self.LAYOUT_A)
        self.setCentralWidget(self.FRAME_A)
        # Place the matplotlib figure
        self.myFigs = list()
        for index in range(nchan):
            self.myFigs.append(CustomFigCanvas())
            self.LAYOUT_A.addWidget(self.myFigs[index], *(index,1))

        # Add the callbackfunc to ..
        myDataLoop = threading.Thread(name = 'myDataLoop', target = dataSendLoop, daemon = True, args = (self.addData_callbackFunc,))
        myDataLoop.start()
        self.show()

    def addData_callbackFunc(self, values):
        for index, value in enumerate(values):
            self.myFigs[index].addData(value)

    def closeEvent(self, event):
        global usb20x
        global data
        global column_names
        global nchan

        fcntl.fcntl(sys.stdin, fcntl.F_SETFL, flag)
        usb20x.AInScanStop()

        timestamp = time.time()

        data.to_csv(f'output_data/test-{timestamp}.csv', index_label='seconds')

        fig = plt.figure(figsize=(20, 20 * nchan))
        fig.suptitle('Rocket Motor Test', fontsize=50)
        axis = list()
        for index, column_name in enumerate(column_names):
            axis.append(fig.add_subplot(nchan, 1, index+1))
            axis[index].plot(data[column_name])

            axis[index].set_xlabel('Seconds')
            axis[index].set_ylabel('Voltage')
            axis[index].set_title(column_name)

        fig.savefig(f'output_data/test-{timestamp}.pdf', dpi=500)

        event.accept()


class CustomFigCanvas(FigureCanvas, TimedAnimation):
    def __init__(self):
        self.addedData = []
        # The data
        self.xlim = 3000
        self.n = np.linspace(0, self.xlim - 1, self.xlim)
        self.y = (self.n * 0.0) + 50
        # The window
        self.fig = Figure(figsize=(5,5), dpi=100)
        self.ax1 = self.fig.add_subplot(111)
        # self.ax1 settings
        self.ax1.set_xlabel('time')
        self.ax1.set_ylabel('voltage')
        self.line1 = Line2D([], [], color='blue')
        self.line1_tail = Line2D([], [], color='red', linewidth=2)
        self.line1_head = Line2D([], [], color='red', marker='o', markeredgecolor='r')
        self.ax1.add_line(self.line1)
        self.ax1.add_line(self.line1_tail)
        self.ax1.add_line(self.line1_head)
        self.ax1.set_xlim(0, self.xlim - 1)
        self.ax1.set_ylim(-5, 5)
        FigureCanvas.__init__(self, self.fig)
        TimedAnimation.__init__(self, self.fig, interval=1, blit=True)

    def new_frame_seq(self):
        return iter(range(self.n.size))

    def _init_draw(self):
        lines = [self.line1, self.line1_tail, self.line1_head]
        for l in lines:
            l.set_data([], [])

    def addData(self, value):
        self.addedData.append(value)

    def _step(self, *args):
        # Extends the _step() method for the TimedAnimation class.
        try:
            TimedAnimation._step(self, *args)
        except Exception as e:
            self.abc += 1
            print(str(self.abc))
            TimedAnimation._stop(self)
            pass

    def _draw_frame(self, framedata):
        margin = 2

        while len(self.addedData) > 0:
            self.y = np.roll(self.y, -1)
            self.y[-1] = self.addedData[0]
            del(self.addedData[0])

        self.line1.set_data(self.n[ 0 : self.n.size - margin ], self.y[ 0 : self.n.size - margin ])
        self.line1_tail.set_data(np.append(self.n[-10:-1 - margin], self.n[-1 - margin]), np.append(self.y[-10:-1 - margin], self.y[-1 - margin]))
        self.line1_head.set_data(self.n[-1 - margin], self.y[-1 - margin])
        self._drawn_artists = [self.line1, self.line1_tail, self.line1_head]


# You need to setup a signal slot mechanism, to
# send data to your GUI in a thread-safe way.
# Believe me, if you don't do this right, things
# go very very wrong..
class Communicate(QObject):
    data_signal = pyqtSignal(list)


def dataSendLoop(addData_callbackFunc):
    global data
    global usb20x
    global nchan
    global column_names

    # Setup the signal-slot mechanism.
    mySrc = Communicate()
    mySrc.data_signal.connect(addData_callbackFunc)

    start_time = time.time()

    while True:  # start_time > time.time() - runtime:
        raw_data = usb20x.AInScanRead(128)
        if raw_data and isinstance(raw_data, list):
            for index in range(int(len(raw_data) / nchan)):
                voltage = list()
                for chan_index in range(nchan):
                    voltage.append(usb20x.volts(raw_data[(index * nchan) + chan_index]))

                timestamp = time.time()
                temp_df = pd.DataFrame([voltage], columns=column_names, index=[timestamp - start_time])

                data = pd.concat([data, temp_df])

                mySrc.data_signal.emit(voltage)  # <- Here you emit a signal!


usb20x = usb_204()

frequency = 1000  # Hz
runtime = 10  # seconds

column_names = [
    'Load Cell',
    'Chamber Pressure',
    'Tank Pressure'
]

nchan = len(column_names) # Number of channels to measure

if frequency < 100:
    options = usb20x.IMMEDIATE_TRANSFER_MODE
else:
    options = 0x0

channels = 0
for i in range(nchan):
    channels |= (0x1 << i)

usb20x.AInScanStop()
usb20x.AInScanClearFIFO()
usb20x.AInScanStart(0, frequency, channels, options, 0, 0)
flag = fcntl.fcntl(sys.stdin, fcntl.F_GETFL)
fcntl.fcntl(sys.stdin, fcntl.F_SETFL, flag | os.O_NONBLOCK)

data = pd.DataFrame(columns=column_names)

if __name__== '__main__':
    app = QApplication(sys.argv)
    QApplication.setStyle(QStyleFactory.create('Plastique'))
    myGUI = CustomMainWindow()
    sys.exit(app.exec_())
