###################################################################
#                                                                 #
#                    PLOT A LIVE GRAPH (PyQt5)                    #
#                  -----------------------------                  #
#            EMBED A MATPLOTLIB ANIMATION INSIDE YOUR             #
#            OWN GUI!                                             #
#                                                                 #
###################################################################

import sys
import threading
import numpy as np
import matplotlib

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from matplotlib.figure import Figure
from matplotlib.animation import TimedAnimation
from matplotlib.lines import Line2D
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

matplotlib.use("Qt5Agg")


class QTHelper:
    def __init__(self, data_logger, debug=False):
        app = QApplication(sys.argv)
        QApplication.setStyle(QStyleFactory.create('Plastique'))

        def data_send_loop(add_data_callback_func):
            # Setup the signal-slot mechanism.
            pyqt_callback = Communicate()
            pyqt_callback.data_signal.connect(add_data_callback_func)

            data_logger.start()
            data_logger.run(pyqt_callback)
            data_logger.output_data()

        CustomMainWindow(data_logger, data_send_loop, debug)
        sys.exit(app.exec_())


class CustomMainWindow(QMainWindow):
    def __init__(self, data_logger, data_send_loop, debug=False):
        super(CustomMainWindow, self).__init__()
        # Define the geometry of the main window
        self.setGeometry(300, 300, 2000, 1000)
        self.setWindowTitle("Load Cell Test")
        # Create FRAME_A
        self.FRAME_A = QFrame(self)
        self.FRAME_A.setStyleSheet("QWidget { background-color: %s }" % QColor(210, 210, 235, 255).name())
        self.LAYOUT_A = QGridLayout()
        self.FRAME_A.setLayout(self.LAYOUT_A)
        self.setCentralWidget(self.FRAME_A)
        # Place the matplotlib figure
        self.myFigs = list()
        for index in range(data_logger.nchan):
            self.myFigs.append(CustomFigCanvas())
            self.LAYOUT_A.addWidget(self.myFigs[index], *(index,1))

        self.data_logger = data_logger
        self.debug = debug

        # Add the callbackfunc to ..
        my_data_loop = threading.Thread(
            name='my_data_loop',
            target=data_send_loop,
            daemon=True,
            args=(self.add_data_callback_func,)
        )

        my_data_loop.start()
        self.show()

    def add_data_callback_func(self, values):
        for index, value in enumerate(values):
            self.myFigs[index].add_data(value)

    def closeEvent(self, event):
        self.data_logger.stop()
        self.data_logger.output_data()
        self.data_logger.reset(wait_for_reset=False)

        event.accept()


class CustomFigCanvas(FigureCanvas, TimedAnimation):
    def __init__(self):
        self.added_data = []
        # The data
        self.xlim = 3000
        self.n = np.linspace(0, self.xlim - 1, self.xlim)
        self.y = (self.n * 0.0) + 50
        # The window
        self.fig = Figure(figsize=(5, 5), dpi=100)
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
        self.ax1.set_ylim(-10.5, 10.5)
        FigureCanvas.__init__(self, self.fig)
        TimedAnimation.__init__(self, self.fig, interval=1, blit=True)

    def new_frame_seq(self):
        return iter(range(self.n.size))

    def _init_draw(self):
        lines = [self.line1, self.line1_tail, self.line1_head]
        for line in lines:
            line.set_data([], [])

    def add_data(self, value):
        self.added_data.append(value)

    def _step(self, *args):
        # Extends the _step() method for the TimedAnimation class.
        try:
            TimedAnimation._step(self, *args)
        except Exception:
            self.abc += 1
            print(str(self.abc))
            TimedAnimation._stop(self)
            pass

    def _draw_frame(self, framedata):
        margin = 2

        while len(self.added_data) > 0:
            self.y = np.roll(self.y, -1)
            self.y[-1] = self.added_data[0]
            del(self.added_data[0])

        self.line1.set_data(self.n[0: self.n.size - margin], self.y[0: self.n.size - margin])
        self.line1_tail.set_data(np.append(self.n[-10:-1 - margin], self.n[-1 - margin]), np.append(self.y[-10:-1 - margin], self.y[-1 - margin]))
        self.line1_head.set_data(self.n[-1 - margin], self.y[-1 - margin])
        self._drawn_artists = [self.line1, self.line1_tail, self.line1_head]


# You need to setup a signal slot mechanism, to
# send data to your GUI in a thread-safe way.
# Believe me, if you don't do this right, things
# go very very wrong..
class Communicate(QObject):
    data_signal = pyqtSignal(list)