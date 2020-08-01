import os
import fcntl
import logging
import random
import queue
import threading

import pandas as pd

from usb1 import USBError
from mccUSB import OverrunError as mccOverrunError

from usb_20x import *
from matplotlib import pyplot as plt

q = queue.Queue(10)
exit_flag = queue.Queue(1)


class ProducerThread(threading.Thread):
    def __init__(self, data_logger, group=None, target=None, name=None, args=(), kwargs=None, verbose=None):
        super(ProducerThread, self).__init__()
        self.target = target
        self.name = name
        self.data_logger = data_logger

    def run(self):
        try:
            while exit_flag.empty():
                if not q.full():
                    try:
                        item = self.data_logger.collect_data()
                        if item:
                            q.put(item)
                            logging.debug(f'Putting 1 item in queue')

                        stop_flag = self.data_logger.usb20x.DPort()
                        logging.debug(f'Stop Flag: {stop_flag}')

                        if not stop_flag:
                            logging.info('Stopping due to stop flag trigger going low...')
                            self.data_logger.stop()
                            exit_flag.put(True)

                    except USBError as e:
                        if e.value == -7:
                            # Normal, the device is probably waiting for a trigger
                            logging.debug(f'USB Timeout occurred, probably waiting for trigger')

                            time.sleep(random.random())
                        else:
                            raise
                    except mccOverrunError:
                        self.data_logger.output_data()
                        self.data_logger.reset(wait_for_reset=True)

                    time.sleep(random.random())

        except (KeyboardInterrupt, SystemExit):
            self.data_logger.stop()
            exit_flag.put(True)


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
            while exit_flag.empty():
                if not q.empty():
                    item = q.get()
                    self.data_logger.process_data(item, self.pyqt_callback)

                if self.maxruntime and ((perf_counter() - self.start_timestamp) / 60) > self.maxruntime:
                    sys.exit()

        except (KeyboardInterrupt, SystemExit):
            self.data_logger.stop()
            exit_flag.put(True)


class DataLogger:
    def __init__(self, frequency, column_names, batch_exp=12, maxruntime=0, pdf_flag=False):
        self.usb20x = usb_204()

        self.batch_exp = batch_exp
        self.column_names = column_names

        self.nchan = len(self.column_names)  # Number of channels to measure
        self.frequency = frequency

        self.timestamp_label = datetime.now().strftime('%y-%b-%d_%H:%M:%S')
        self.restart_timestamp = perf_counter()
        self.start_timestamp = perf_counter()
        self.timestamp = 0
        self.transfer_count = 0
        self.maxruntime = maxruntime
        self.pdf_flag = pdf_flag

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
        self.usb20x.AInScanStart(0, self.frequency * self.nchan, self.channels, self.options, self.usb20x.TRIGGER, self.usb20x.LEVEL_HIGH)

        self.timestamp_label = datetime.now().strftime('%y-%b-%d %H:%M:%S')
        self.restart_timestamp = perf_counter()
        self.timestamp = 0
        self.transfer_count = 0

        self.data = pd.DataFrame(columns=self.column_names)

        logging.info('Started USB_204')

    def run(self, pyqt_callback=None):
        logging.info('Running data logging...')

        p = ProducerThread(name='producer', data_logger=self)
        p.daemon = True

        c = ConsumerThread(
            name='consumer',
            pyqt_callback=pyqt_callback,
            data_logger=self,
            maxruntime=self.maxruntime,
            start_timestamp=self.start_timestamp
        )
        c.daemon = True

        if not exit_flag.empty():
            exit_flag.get()

        try:
            logging.info('Waiting for trigger...')
            p.start()
            time.sleep(2)
            c.start()
            time.sleep(2)

            c.join()
        except (KeyboardInterrupt, SystemExit):
            logging.info('Stopping logging')
            exit_flag.put(True)

        c.join()
        p.join()

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

            self.output_to_csv()

        self.transfer_count += 1

        seconds_behind = int(perf_counter() - self.restart_timestamp - (self.timestamp))
        logging.info(f'{self.transfer_count}: Got {int(len(raw_data) / self.nchan)} data points  -  (currently {seconds_behind} seconds behind)  -  Recorded time: {int(self.timestamp)} seconds')

    def print_debug_info(self):
        time_since_restart = perf_counter() - self.restart_timestamp

        logging.debug(f'Time since last restart: {int(time_since_restart)} seconds or {int(time_since_restart / 60)} minutes')
        logging.debug(f'Recorded time: {int(self.timestamp)} seconds or {int(self.timestamp / 60)} minutes')
        logging.debug(f'Time since last restart minus recorded time: {int(time_since_restart - (self.timestamp))} seconds')
        logging.debug(f'Number of bulk transfers: {self.transfer_count}')

    def reset(self, wait_for_reset=True):
        self.print_debug_info()

        self.usb20x.Reset()

        sleep_delay = .1

        reset_in_progress = True

        logging.info(f'Restarting USB_204...')
        while reset_in_progress and wait_for_reset:
            try:
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

        if self.pdf_flag:
            self.output_to_pdf()

    def output_to_csv(self):
        if not os.path.exists(f'output_data/{self.timestamp_label}'):
            os.makedirs(f'output_data/{self.timestamp_label}')

        self.data.to_csv(
            f'output_data/{self.timestamp_label}/data.csv',
            index_label='seconds',
            mode='a',
            header=False,
            chunksize=10000
        )

        # Reset data to be appended next time
        self.data = pd.DataFrame(columns=self.column_names)

    def output_to_pdf(self):
        df = pd.read_csv(
            f'output_data/{self.timestamp_label}/data.csv',
            names=self.column_names
        )

        for index, column_name in enumerate(self.column_names):
            fig = plt.figure()
            fig.suptitle(f'Rocket Motor Test - {self.timestamp_label}')

            subplot = fig.add_subplot(1, 1, 1)
            subplot.plot(df[column_name])

            subplot.set_xlabel('Seconds')
            subplot.set_ylabel('Voltage')
            subplot.set_title(column_name)
            subplot.set_ylim([-12, 12])

            fig.tight_layout()
            fig.savefig(f'output_data/{self.timestamp_label}/{column_name}.pdf', dpi=1000, orientation='landscape', bbox_inches='tight')
