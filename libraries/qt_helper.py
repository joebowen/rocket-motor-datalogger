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
import queue
import time
import logging

import pandas as pd

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from matplotlib.figure import Figure
from matplotlib.animation import TimedAnimation
from matplotlib.lines import Line2D
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

matplotlib.use("Qt5Agg")

qt_queue = queue.Queue(10)
qt_exit_queue = queue.Queue(1)


def data_send_loop(add_data_callback_func, app):
    # Setup the signal-slot mechanism.
    pyqt_callback = Communicate()
    pyqt_callback.data_signal.connect(add_data_callback_func)

    while qt_exit_queue.empty():
        for x in range(100):
            if not qt_queue.empty():
                voltages = qt_queue.get()
                pyqt_callback.data_signal.emit(voltages)  # <- Here you emit a signal when using pyqt!
            else:
                time.sleep(.1)
                break

        time.sleep(.01)

    logging.debug('Stopping QT')
    app.exit()


class QTHelper:
    def __init__(self, data_logger, calibration=False):
        app = QApplication(sys.argv)
        QApplication.setStyle(QStyleFactory.create('Plastique'))

        data_logger.start(qt_queue, qt_exit_queue)

        self.window = CustomMainWindow(app, data_logger, calibration)

        app.exec_()


class CustomMainWindow(QMainWindow):
    def __init__(self, app, data_logger, calibration=False):
        super(CustomMainWindow, self).__init__()

        self.app = app
        self.sensors = data_logger.sensors
        self.data_logger = data_logger

        # Define the geometry of the main window
        self.setGeometry(0, 0, 3000, 2000)
        self.setWindowTitle("Load Cell Test")
        # Create FRAME_A
        self.FRAME_A = QFrame(self)
        self.FRAME_A.setStyleSheet("QWidget { background-color: %s }" % QColor(210, 210, 235, 255).name())
        self.LAYOUT_A = QGridLayout()
        self.FRAME_A.setLayout(self.LAYOUT_A)
        self.setCentralWidget(self.FRAME_A)
        # Place the matplotlib figure
        self.myFigs = dict()
        for index, sensor_name in enumerate(self.sensors.keys()):
            self.myFigs[sensor_name] = CustomFigCanvas(
                self.sensors[sensor_name]['sensor_name'],
                self.sensors[sensor_name]['units'],
                self.sensors[sensor_name]['min'],
                self.sensors[sensor_name]['max'],
                calibration,
                data_logger.frequency
            )

            self.LAYOUT_A.addWidget(self.myFigs[sensor_name], *(index, 1))

        # Add the callbackfunc to ..
        my_data_loop = threading.Thread(
            name='my_data_loop',
            target=data_send_loop,
            daemon=True,
            args=(self.add_data_callback_func, app,)
        )
        my_data_loop.start()
        self.show()

    def add_data_callback_func(self, df):
        for sensor_id, sensor in self.sensors.items():
            df[sensor['sensor_name']].apply(sensor['formula'], **sensor['input'])

            for value in df[sensor['sensor_name']]:
                self.myFigs[sensor_id].add_data(value)

    def closeEvent(self, event):
        logging.debug('Stopping due to closing QT window...')
        self.data_logger.stop()
        event.accept()


class CustomFigCanvas(FigureCanvas, TimedAnimation):
    def __init__(self, sensor_name, sensor_units, sensor_min, sensor_max, calibration, frequency):
        self.added_data = []
        # The data
        self.xlim = (2 * 60) * frequency  # Chart the past 2 minutes regardless of the frequency
        self.n = np.linspace(0, self.xlim - 1, self.xlim)
        self.y = (self.n * 0.0) + 50
        # The window
        self.fig = Figure(figsize=(5, 5), dpi=75)
        self.ax1 = self.fig.add_subplot(111)
        # self.ax1 settings
        self.ax1.set_title(sensor_name)
        self.ax1.set_xlabel('datapoints')
        self.line1 = Line2D([], [], color='blue', linewidth=2)
        self.line1_tail = Line2D([], [], color='red', linewidth=2)
        self.line1_head = Line2D([], [], color='red', marker='o', markeredgecolor='r')
        self.ax1.add_line(self.line1)
        self.ax1.add_line(self.line1_tail)
        self.ax1.add_line(self.line1_head)
        self.ax1.set_xlim(0, self.xlim - 1)

        if calibration:
            self.ax1.set_ylim(-12, 12)
            self.ax1.set_ylabel('V')
            self.ax1.yaxis.set_label_position("right")
            self.ax1.yaxis.tick_right()
        else:
            wiggle_room = (sensor_max - sensor_min) * .10

            self.ax1.set_ylim(sensor_min - wiggle_room, sensor_max + wiggle_room)
            self.ax1.set_ylabel(sensor_units)
            self.ax1.yaxis.set_label_position("right")
            self.ax1.yaxis.tick_right()

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
    data_signal = pyqtSignal(pd.DataFrame)
