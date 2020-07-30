import os
import fcntl
import logging
import random
import queue
import threading

import pandas as pd

from mccUSB import OverrunError as mccOverrunError

from usb_20x import *
from matplotlib import pyplot as plt


logging.basicConfig(level=logging.DEBUG,
                    format='(%(threadName)-9s) %(message)s',)

q = queue.Queue(10)


class ProducerThread(threading.Thread):
    def __init__(self, data_logger, group=None, target=None, name=None, args=(), kwargs=None, verbose=None):
        super(ProducerThread, self).__init__()
        self.target = target
        self.name = name
        self.data_logger = data_logger

    def run(self):
        while True:
            if not q.full():
                try:
                    item = self.data_logger.collect_data()
                    if item:
                        q.put(item)
                        logging.debug('Putting 1 item in queue')
                except mccOverrunError:
                    self.data_logger.reset()

                time.sleep(random.random())
        return


class ConsumerThread(threading.Thread):
    def __init__(self, data_logger, maxruntime, start_timestamp, group=None, target=None, name=None, args=(), kwargs=None, verbose=None, pyqt_callback=None):
        super(ConsumerThread, self).__init__()
        self.target = target
        self.name = name
        self.pyqt_callback = pyqt_callback
        self.data_logger = data_logger
        self.maxruntime = maxruntime
        self.start_timestamp = start_timestamp

    def run(self):
        try:
            while True:
                if not q.empty():
                    item = q.get()
                    self.data_logger.process_data(item, self.pyqt_callback)

                if self.maxruntime and ((perf_counter() - self.start_timestamp) / 60) > self.maxruntime:
                    self.data_logger.reset(wait_for_reset=False)
                    break

        except KeyboardInterrupt:
            self.data_logger.reset(wait_for_reset=False)


class DataLogger:
    def __init__(self, frequency, column_names, batch_exp=12, debug=False, maxruntime=0):
        self.debug = debug

        self.usb20x = usb_204()

        self.batch_exp = batch_exp
        self.column_names = column_names

        self.nchan = len(self.column_names)  # Number of channels to measure
        self.frequency = frequency

        self.restart_timestamp = perf_counter()
        self.start_timestamp = perf_counter()
        self.timestamp = 0
        self.transfer_count = 0
        self.maxruntime = maxruntime

        self.data = pd.DataFrame(columns=column_names)
        self.all_data = pd.DataFrame(columns=column_names)

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
        self.usb20x.AInScanStart(0, self.frequency * self.nchan, self.channels, self.options, 0, 0)

        self.restart_timestamp = perf_counter()
        self.timestamp = 0
        self.transfer_count = 0

        self.data = pd.DataFrame(columns=self.column_names)

        logging.debug('Started USB_204')

    def run(self, pyqt_callback=None):
        logging.debug('Running data logging...')

        p = ProducerThread(name='producer', data_logger=self)
        p.daemon = True

        c = ConsumerThread(
            name='consumer',
            pyqt_callback=pyqt_callback,
            data_logger=self,
            maxruntime=self.maxruntime,
            start_timestamp=self.start_timestamp
        )

        p.start()
        time.sleep(2)
        c.start()
        time.sleep(2)

        c.join()

        logging.debug('Stopping logging')

    def collect_data(self):
        raw_data = self.usb20x.AInScanRead(2**self.batch_exp, logging)

        return raw_data

    def process_data(self, raw_data, pyqt_callback=None):
        if raw_data and isinstance(raw_data, list):
            df_index = []
            df_temp = []
            for index in range(int(len(raw_data) / self.nchan)):
                voltage = list()
                for chan_index in range(self.nchan):
                    voltage.append(self.usb20x.volts(raw_data[(index * self.nchan) + chan_index]))

                self.timestamp += (1 / self.frequency)

                df_index.append(self.timestamp)
                df_temp.append(voltage)

                if pyqt_callback:
                    pyqt_callback.data_signal.emit(voltage)  # <- Here you emit a signal when using pyqt!

            temp_df = pd.DataFrame(df_temp, columns=self.column_names, index=df_index)

            self.data = pd.concat([self.data, temp_df])

            self.output_data()

        self.transfer_count += 1

        if self.debug:
            seconds_behind = int(perf_counter() - self.restart_timestamp - (self.timestamp))
            logging.debug(f'{self.transfer_count}: Got {int(len(raw_data) / self.nchan)} data points  -  (currently {seconds_behind} seconds behind)  -  Recorded time: {int(self.timestamp)} seconds')

    def print_debug_info(self):
        time_since_restart = perf_counter() - self.restart_timestamp

        logging.debug(f'Time since last restart: {int(time_since_restart)} seconds or {int(time_since_restart / 60)} minutes')
        logging.debug(f'Recorded time: {int(self.timestamp)} seconds or {int(self.timestamp / 60)} minutes')
        logging.debug(f'Time since last restart minus recorded time: {int(time_since_restart - (self.timestamp))} seconds')
        logging.debug(f'Number of bulk transfers: {self.transfer_count}')

    def reset(self, wait_for_reset=True):
        if self.debug:
            self.print_debug_info()

        self.usb20x.Reset()

        sleep_delay = .1

        reset_in_progress = True

        while reset_in_progress and wait_for_reset:
            try:
                logging.debug(f'Restarting USB_204...')
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
        self.output_to_csv()
        self.output_to_pdf()

    def output_to_csv(self):
        self.data.to_csv(
            f'output_data/test-{self.restart_timestamp}.csv',
            index_label='seconds',
            mode='a',
            header=False,
            chunksize=10000
        )

        self.all_data = pd.concat([self.all_data, self.data])

        # Reset data to be appended next time
        self.data = pd.DataFrame(columns=self.column_names)

    def output_to_pdf(self):
        fig = plt.figure(figsize=(20, 20 * self.nchan))
        fig.suptitle('Rocket Motor Test', fontsize=50)
        axis = list()
        for index, column_name in enumerate(self.column_names):
            axis.append(fig.add_subplot(self.nchan, 1, index + 1))
            axis[index].plot(self.all_data[column_name])

            axis[index].set_xlabel('Seconds')
            axis[index].set_ylabel('Voltage')
            axis[index].set_title(column_name)
            axis[index].set_ylim([-12, 12])

        fig.savefig(f'output_data/test-{self.restart_timestamp}.pdf', dpi=500)
