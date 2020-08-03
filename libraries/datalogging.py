import os
import random
import queue
import threading

import pandas as pd

from usb1 import USBError
from mccUSB import OverrunError as mccOverrunError

from usb_20x import *
from matplotlib import pyplot as plt

data_queue = queue.Queue(10)
exit_flag = queue.Queue(1)


class ProducerThread(threading.Thread):
    def __init__(self, data_logger, group=None, target=None, name=None, args=(), kwargs=None, verbose=None, daemon=True):
        super(ProducerThread, self).__init__()
        self.target = target
        self.name = name
        self.data_logger = data_logger

    def run(self):
        try:
            while exit_flag.empty():
                if not data_queue.full():
                    try:
                        item = self.data_logger.collect_data()
                        if item:
                            data_queue.put(item)
                            logging.debug(f'Putting 1 item in queue')

                        stop_flag = self.data_logger.usb20x.DPort()
                        logging.debug(f'Stop Flag: {stop_flag}')

                        if not stop_flag:
                            logging.info('Stopping due to stop flag trigger going low...')
                            self.data_logger.stop()

                    except USBError as e:
                        if e.value == -7:
                            # Normal, the device is probably waiting for a trigger
                            logging.debug(f'USB Timeout occurred, probably waiting for trigger')
                            time.sleep(random.random())
                        else:
                            raise
                    except mccOverrunError:
                        self.data_logger.output_data()
                        self.data_logger.stop()

                    time.sleep(random.random())

        except (KeyboardInterrupt, SystemExit):
            self.data_logger.stop()


class ConsumerThread(threading.Thread):
    def __init__(self, data_logger, maxruntime, group=None, target=None, name=None, args=(), kwargs=None, verbose=None, daemon=True):
        super(ConsumerThread, self).__init__()
        self.target = target
        self.name = name
        self.data_logger = data_logger
        self.maxruntime = maxruntime

    def run(self):
        try:
            while exit_flag.empty():
                if not data_queue.empty():
                    item = data_queue.get()
                    self.data_logger.process_data(item)

                    if self.maxruntime and (self.data_logger.timestamp / 60) > self.maxruntime:
                        self.data_logger.stop()

                time.sleep(0.001)

        except (KeyboardInterrupt, SystemExit):
            self.data_logger.stop()


class DataLogger:
    def __init__(self, frequency, sensors, batch_exp=12, maxruntime=0, pdf_flag=False, calibration=False):
        self.usb20x = usb_204()

        self.calibration = calibration

        self.batch_exp = batch_exp
        self.sensors = sensors

        self.sensor_names = [None] * len(self.sensors)
        for sensor_id, sensor in self.sensors.items():
            self.sensor_names[sensor['channel']] = sensor['sensor_name']

        logging.debug(f'Sensor Names: {self.sensor_names}')

        self.nchan = len(self.sensors)  # Number of channels to measure
        self.frequency = frequency

        self.timestamp_label = datetime.now().strftime('%y-%b-%d_%H:%M:%S')
        self.restart_timestamp = perf_counter()
        self.timestamp = 0
        self.transfer_count = 0
        self.maxruntime = maxruntime
        self.pdf_flag = pdf_flag
        self.qt_queue = None

        self.exit_flag = exit_flag

        self.p = None
        self.c = None

        self.data = pd.DataFrame(columns=self.sensor_names)

        self.channels = 0
        for i in range(self.nchan):
            self.channels |= (0x1 << i)

        if self.frequency < 100:
            self.options = self.usb20x.IMMEDIATE_TRANSFER_MODE
        else:
            self.options = self.usb20x.STALL_ON_OVERRUN

    def start(self, qt_queue=None):
        self.usb20x = usb_204()

        self.usb20x.AInScanStop()
        self.usb20x.AInScanClearFIFO()

        logging.info('Turn on the green switch when ready to start logging...')
        while not self.usb20x.DPort():
            time.sleep(random.random())

        self.usb20x.AInScanStart(0, self.frequency * self.nchan, self.channels, self.options, self.usb20x.NO_TRIGGER, self.usb20x.LEVEL_HIGH)

        if self.maxruntime:
            logging.info(f'Collecting data for {self.maxruntime:.2} minutes...')
        else:
            logging.info('Collecting data until green switch is turned off or code is exited...')

        self.timestamp_label = datetime.now().strftime('%y-%b-%d %H:%M:%S')
        self.restart_timestamp = perf_counter()
        self.timestamp = 0
        self.transfer_count = 0

        self.data = pd.DataFrame(columns=self.sensor_names)

        self.qt_queue = qt_queue

        # To write out the column headers
        self.output_to_csv(write_mode='w')

        logging.info('Starting USB_204')

    def run(self):
        logging.info('Running data logging...')

        self.p = ProducerThread(
            name='producer',
            daemon=True,
            data_logger=self
        )

        self.c = ConsumerThread(
            name='consumer',
            daemon=True,
            data_logger=self,
            maxruntime=self.maxruntime
        )

        while not exit_flag.empty():
            exit_flag.get()

        self.p.start()
        self.c.start()

    def wait_for_datalogger(self):
        try:
            self.c.join()
        except (KeyboardInterrupt, SystemExit):
            self.stop()

    def collect_data(self):
        raw_data = self.usb20x.AInScanRead(2**self.batch_exp)

        return raw_data

    def process_data(self, raw_data):
        if raw_data and isinstance(raw_data, list):
            df_index = []
            df_temp = []
            for index in range(int(len(raw_data) / self.nchan)):
                voltage = []
                for chan_index in range(self.nchan):
                    voltage.append(self.usb20x.volts(raw_data[(index * self.nchan) + chan_index]))

                self.timestamp += (1 / self.frequency)

                df_index.append(self.timestamp)
                df_temp.append(voltage)

            logging.debug(f'Sample Voltages: {df_temp[0]}')

            temp_df = pd.DataFrame(df_temp, columns=self.sensor_names, index=df_index)

            if not self.calibration:
                for sensor_id, sensor in self.sensors.items():
                    temp_df[sensor['sensor_name']] = temp_df[sensor['sensor_name']].apply(
                        lambda v, linear_adj, opamp_mul: (v + linear_adj) / opamp_mul,
                        linear_adj=sensor['linear_adj'],
                        opamp_mul=sensor['opamp_mul']
                    )

                    temp_df[sensor['sensor_name']] = temp_df[sensor['sensor_name']].apply(
                        sensor['formula'],
                        **sensor['input']
                    )

                    temp_df[sensor['sensor_name']] = temp_df[sensor['sensor_name']].apply(
                        lambda v, scalar_adj: v * scalar_adj,
                        scalar_adj=sensor['scalar_adj']
                    )

            logging.debug(f'Sample transformed measurements:\n{temp_df.iloc[0]}')

            if self.qt_queue:
                self.qt_queue.put(temp_df)

            self.data = pd.concat([self.data, temp_df])

            self.output_to_csv()

        self.transfer_count += 1

        logging.debug(f'{self.transfer_count}: Got {len(raw_data) / self.nchan} data points  -  Recorded time: {int(self.timestamp)} seconds')

    def print_debug_info(self):
        time_since_restart = perf_counter() - self.restart_timestamp

        logging.debug(f'Time since last restart: {int(time_since_restart)} seconds or {int(time_since_restart / 60)} minutes')
        logging.debug(f'Recorded time: {int(self.timestamp)} seconds or {int(self.timestamp / 60)} minutes')
        logging.debug(f'Time since last restart minus recorded time: {int(time_since_restart - (self.timestamp))} seconds')
        logging.debug(f'Number of bulk transfers: {self.transfer_count}')

    def reset(self):
        self.print_debug_info()

        while not data_queue.empty():
            data_queue.get()

        if self.qt_queue:
            while not self.qt_queue.empty():
                self.qt_queue.get()

        self.usb20x.Reset()

        sleep_delay = .1

        reset_in_progress = True

        logging.info(f'Restarting USB_204...')
        while reset_in_progress:
            try:
                self.usb20x = usb_204()
                logging.debug(f'Status: {self.usb20x.Status()}')
                reset_in_progress = False
            except:
                time.sleep(sleep_delay)
                sleep_delay += .1
                if sleep_delay > 5:
                    raise

    def stop(self):
        logging.info('Stopping logging')

        if not exit_flag.full():
            exit_flag.put(True)
        self.usb20x.AInScanStop()

    def output_data(self):
        self.output_to_csv()

        if self.pdf_flag:
            self.output_to_pdf()

    def get_data(self):
        df = pd.read_csv(f'output_data/{self.timestamp_label}/data.csv')

        return df

    def output_to_csv(self, write_mode='a'):
        if not os.path.exists(f'output_data/{self.timestamp_label}'):
            os.makedirs(f'output_data/{self.timestamp_label}')

        header = False
        if write_mode == 'w':
            header = True

        self.data.to_csv(
            f'output_data/{self.timestamp_label}/data.csv',
            index_label='seconds',
            mode=write_mode,
            header=header,
            chunksize=10000
        )

        # Reset data to be appended next time
        self.data = pd.DataFrame(columns=self.sensor_names)

    def output_to_pdf(self):
        df = pd.read_csv(f'output_data/{self.timestamp_label}/data.csv')

        for sensor_id, sensor in self.sensors.items():
            fig = plt.figure()
            fig.suptitle(f'Rocket Motor Test - {self.timestamp_label} - {sensor["sensor_name"]}')

            subplot = fig.add_subplot(1, 1, 1)

            subplot.plot(df[sensor['sensor_name']], linewidth=0.5)

            subplot.set_xlabel('Seconds')
            subplot.set_ylabel(sensor['units'])
            subplot.set_ylim([sensor['min'], sensor['max']])

            fig.savefig(f'output_data/{self.timestamp_label}/{sensor["sensor_name"]}.pdf', dpi=1000, orientation='landscape', bbox_inches='tight')
