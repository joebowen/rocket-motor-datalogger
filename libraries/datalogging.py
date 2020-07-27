import os
import fcntl

from time import perf_counter

import pandas as pd

from mccUSB import OverrunError as mccOverrunError

from usb_20x import *
from matplotlib import pyplot as plt


class DataLogger:
    def __init__(self, frequency, column_names, batch_exp=10, debug=False):
        self.debug = debug

        self.usb20x = usb_204()

        self.batch_exp = batch_exp
        self.frequency = frequency
        self.column_names = column_names

        self.nchan = len(self.column_names)  # Number of channels to measure

        self.start_timestamp = perf_counter()
        self.timestamp = 0
        self.transfer_count = 0

        self.data = pd.DataFrame(columns=column_names)

        self.channels = 0
        for i in range(self.nchan):
            self.channels |= (0x1 << i)

        if self.frequency < 100:
            self.options = self.usb20x.IMMEDIATE_TRANSFER_MODE
        else:
            self.options = self.usb20x.STALL_ON_OVERRUN

        self.flag = fcntl.fcntl(sys.stdin, fcntl.F_GETFL)
        fcntl.fcntl(sys.stdin, fcntl.F_SETFL, self.flag | os.O_NONBLOCK)

    def start(self):
        self.usb20x = usb_204()

        self.usb20x.AInScanStop()
        self.usb20x.AInScanClearFIFO()
        self.usb20x.AInScanStart(0, self.frequency, self.channels, self.options, 0, 0)

        self.start_timestamp = perf_counter()
        self.timestamp = 0
        self.transfer_count = 0

        self.data = pd.DataFrame(columns=self.column_names)

        print('Started USB_204')

    def run(self, pyqt_callback=None):
        print('Running data logging...')
        try:
            while True:
                try:
                    self.collect_data(pyqt_callback)
                except mccOverrunError:
                    self.output_data()
                    self.usb20x.AInScanStop()
                    self.usb20x.AInScanClearFIFO()
                    self.usb20x.BulkFlush()
                    raise
                    # self.reset()
        except KeyboardInterrupt:
            pass

    def collect_data(self, pyqt_callback=None):
        raw_data = self.usb20x.AInScanRead(2**self.batch_exp)

        if raw_data and isinstance(raw_data, list):
            df_index = []
            df_temp = []
            for index in range(int(len(raw_data) / self.nchan)):
                voltage = list()
                for chan_index in range(self.nchan):
                    voltage.append(self.usb20x.volts(raw_data[(index * self.nchan) + chan_index]))

                self.timestamp += 1

                df_index.append(self.timestamp / self.frequency)
                df_temp.append(voltage)

                if pyqt_callback:
                    pyqt_callback.data_signal.emit(voltage)  # <- Here you emit a signal when using pyqt!

            temp_df = pd.DataFrame(df_temp, columns=self.column_names, index=df_index)

            self.data = pd.concat([self.data, temp_df])

        self.transfer_count += 1

        if self.debug:
            print(f'{self.transfer_count}: Got {int(len(raw_data) / self.nchan)} data points')

    def reset(self, wait_for_reset=True):
        time_since_restart = perf_counter() - self.start_timestamp

        print(f'Time since last restart: {int(time_since_restart)} seconds or {int(time_since_restart / 60)} minutes')
        print(f'Recorded time: {int(self.timestamp / self.frequency)} seconds or {int(self.timestamp / self.frequency / 60)} minutes')
        print(f'Time since last restart minus recorded time: {int(time_since_restart - (self.timestamp / self.frequency))} seconds')
        print(f'Number of bulk transfers: {self.transfer_count}')

        self.usb20x.Reset()

        sleep_delay = .1

        reset_in_progress = True

        while reset_in_progress and wait_for_reset:
            try:
                print(f'Restarting USB_204...')
                self.start()
                reset_in_progress = False
            except:
                time.sleep(sleep_delay)
                sleep_delay += .1
                if sleep_delay > 5:
                    raise

    def stop(self):
        fcntl.fcntl(sys.stdin, fcntl.F_SETFL, self.flag)
        self.usb20x.AInScanStop()

    def output_data(self):
        run_timestamp = time.time()

        self.data.to_csv(f'output_data/test-{run_timestamp}.csv', index_label='seconds')

        fig = plt.figure(figsize=(20, 20 * self.nchan))
        fig.suptitle('Rocket Motor Test', fontsize=50)
        axis = list()
        for index, column_name in enumerate(self.column_names):
            axis.append(fig.add_subplot(self.nchan, 1, index + 1))
            axis[index].plot(self.data[column_name])

            axis[index].set_xlabel('Seconds')
            axis[index].set_ylabel('Voltage')
            axis[index].set_title(column_name)
            axis[index].set_ylim([-12, 12])

        fig.savefig(f'output_data/test-{run_timestamp}.pdf', dpi=500)
