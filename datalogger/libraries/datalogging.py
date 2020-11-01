import os
import random
import queue
import threading

import pandas as pd
from scipy import integrate

from usb1 import USBError
from datalogger.mccUSB import OverrunError as mccOverrunError

from datalogger.usb_20x import *
from matplotlib import pyplot as plt

data_queue = queue.Queue(50)
exit_flag = queue.Queue(1)


def roundup(x, mod):
    return x if x % mod == 0 else x + mod - x % mod


def rounddown(x, mod):
    return x if x % mod == 0 else (x + 1) - mod - (x + 1) % mod


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
                            logging.debug('Stopping due to stop flag trigger going low...')
                            self.data_logger.stop()

                    except USBError as e:
                        if e.value == -7 or e.value == -4:  # or e.value == -9:
                            # Normal, the device is probably waiting for a trigger
                            logging.info(f'USB Timeout occurred, probably waiting for trigger')
                            time.sleep(random.random())
                        else:
                            raise
                    except mccOverrunError:
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

                    if self.maxruntime and self.data_logger.timestamp > self.maxruntime:
                        self.data_logger.stop()

                time.sleep(0.001)

        except (KeyboardInterrupt, SystemExit):
            self.data_logger.stop()


class DataLogger:
    def __init__(self, frequency, sensors, maxruntime=0,  raw_voltage=False):
        self.usb20x = usb_204()

        self.raw_voltage = raw_voltage

        self.batch_exp = self._calc_batch_exp(frequency)
        self.sensors = sensors

        self.sensor_names = [None] * len(self.sensors)
        for sensor_id, sensor in self.sensors.items():
            self.sensor_names[sensor['channel']] = sensor['sensor_name']

        logging.debug(f'Sensor Names: {self.sensor_names}')

        self.nchan = len(self.sensors)  # Number of channels to measure
        self.frequency = frequency
        self.sample_time = 1 / frequency

        self.timestamp_label = datetime.now().strftime('%y-%b-%d_%H:%M:%S')
        self.restart_timestamp = perf_counter()
        self.timestamp = 0
        self.transfer_count = 0
        self.maxruntime = maxruntime
        self.qt_queue = None
        self.qt_exit_queue = None

        self.exit_flag = exit_flag

        self.p = None
        self.c = None

        self.started = False

        self.data = pd.DataFrame(columns=self.sensor_names)
        self.raw_data = pd.DataFrame(columns=self.sensor_names)

        self.channels = 0
        for i in range(self.nchan):
            self.channels |= (0x1 << i)

        if self.frequency < 100:
            self.options = self.usb20x.IMMEDIATE_TRANSFER_MODE
        else:
            self.options = self.usb20x.STALL_ON_OVERRUN

    @staticmethod
    def _calc_batch_exp(frequency):
        for x in range(20):
            if 2**x > frequency:
                return x

        return 20

    def start(self, qt_queue=None, qt_exit_queue=None):
        self._reset()

        logging.info('Starting USB_204')

        logging.info('Turn on the green switch when ready to start logging...')
        while not self.usb20x.DPort():
            time.sleep(random.random())

        self.usb20x.AInScanStart(0, self.frequency * self.nchan, self.channels, self.options, self.usb20x.NO_TRIGGER, self.usb20x.LEVEL_HIGH)

        if self.maxruntime:
            logging.info(f'Collecting data for {self.maxruntime} seconds...')
        else:
            logging.info('Collecting data until green switch is turned off or code is exited...')

        self.timestamp_label = datetime.now().strftime('%y-%b-%d %H:%M:%S')
        self.restart_timestamp = perf_counter()
        self.timestamp = 0
        self.transfer_count = 0

        self.data = pd.DataFrame(columns=self.sensor_names)
        self.raw_data = pd.DataFrame(columns=self.sensor_names)

        self.qt_queue = qt_queue
        self.qt_exit_queue = qt_exit_queue

        # To write out the column headers
        self.output_to_csv(write_mode='w')

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

        self.started = True

    def wait_for_datalogger(self):
        try:
            self.c.join()
        except (KeyboardInterrupt, SystemExit):
            self.stop()

    def collect_data(self):
        raw_data = None
        if self.usb20x.Status() == self.usb20x.AIN_SCAN_RUNNING:
            raw_data = self.usb20x.AInScanRead(2**self.batch_exp)
        elif self.usb20x.Status() == self.usb20x.AIN_SCAN_RUNNING + self.usb20x.AIN_SCAN_OVERRUN:
            logging.info('Scan Overrun.  Forced to reset (cross fingers and hope timing is ok)!!!')
            self._reset()
        else:
            logging.info(f'Not running... Status: {self.usb20x.Status()}')

        return raw_data

    def process_data(self, raw_input_data):
        if raw_input_data and isinstance(raw_input_data, list):
            df_index = []
            df_temp = []
            for index in range(int(len(raw_input_data) / self.nchan)):
                voltage = []
                for chan_index in range(self.nchan):
                    voltage.append(self.usb20x.volts(raw_input_data[(index * self.nchan) + chan_index]))

                self.timestamp += self.sample_time

                df_index.append(self.timestamp)
                df_temp.append(voltage)

            logging.debug(f'Sample Voltages: {df_temp[0]}')

            temp_df = pd.DataFrame(df_temp, columns=self.sensor_names, index=df_index)
            raw_temp_df = pd.DataFrame(df_temp, columns=self.sensor_names, index=df_index)

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
                if self.raw_voltage:
                    self.qt_queue.put(raw_temp_df)
                else:
                    self.qt_queue.put(temp_df)

            self.data = pd.concat([self.data, temp_df])
            self.raw_data = pd.concat([self.raw_data, raw_temp_df])

            self.output_to_csv()

        self.transfer_count += 1

        logging.debug(f'{self.transfer_count}: Got {len(raw_input_data) / self.nchan} data points  -  Recorded time: {int(self.timestamp)} seconds')

    def print_debug_info(self):
        time_since_restart = perf_counter() - self.restart_timestamp

        logging.debug(f'Time since last restart: {int(time_since_restart)} seconds or {int(time_since_restart / 60)} minutes')
        logging.debug(f'Recorded time: {int(self.timestamp)} seconds or {int(self.timestamp / 60)} minutes')
        logging.debug(f'Time since last restart minus recorded time: {int(time_since_restart - (self.timestamp))} seconds')
        logging.debug(f'Number of bulk transfers: {self.transfer_count}')

    def _reset(self):
        if not exit_flag.full():
            exit_flag.put(True)

        self.print_debug_info()

        while not data_queue.empty():
            data_queue.get()

        if self.qt_queue:
            while not self.qt_queue.empty():
                self.qt_queue.get()

        self.usb20x.AInScanStop()
        self.usb20x.AInScanClearFIFO()

        logging.info(f'Restarting USB_204...')

        try:
            self.usb20x.Reset()
        except:
            pass

        sleep_delay = .1

        reset_in_progress = True

        while reset_in_progress:
            try:
                self.usb20x = usb_204()
                logging.debug(f'Status: {self.usb20x.Status()}')
                self.usb20x.AInScanStop()
                self.usb20x.AInScanClearFIFO()
                reset_in_progress = False
            except:
                time.sleep(sleep_delay)
                sleep_delay += .1
                if sleep_delay > 5:
                    raise

    def stop(self):
        if not self.started:
            return

        self.started = False

        logging.info('Stopping logging')

        if self.qt_exit_queue and not self.qt_exit_queue.full():
            self.qt_exit_queue.put(True)

        if not exit_flag.full():
            exit_flag.put(True)

        self.usb20x.AInScanStop()

    def get_data(self):
        df = pd.read_csv(f'output_data/{self.timestamp_label}/converted_data.csv', index_col=0)

        return df

    def get_raw_data(self):
        df = pd.read_csv(f'output_data/{self.timestamp_label}/raw_data.csv', index_col=0)

        return df

    def output_to_csv(self, write_mode='a'):
        if not os.path.exists(f'output_data/{self.timestamp_label}'):
            os.makedirs(f'output_data/{self.timestamp_label}')

        header = False
        if write_mode == 'w':
            header = True

        self.data.to_csv(
            f'output_data/{self.timestamp_label}/converted_data.csv',
            index_label='seconds',
            mode=write_mode,
            header=header,
            chunksize=10000
        )

        # Reset data to be appended next time
        self.data = pd.DataFrame(columns=self.sensor_names)

        self.raw_data.to_csv(
            f'output_data/{self.timestamp_label}/raw_data.csv',
            index_label='seconds',
            mode=write_mode,
            header=header,
            chunksize=10000
        )

        # Reset raw_data to be appended next time
        self.raw_data = pd.DataFrame(columns=self.sensor_names)

    def _detect_starting_timestamp(self, df):
        # Discard the 1st second in case it's a 'dirty' signal
        starting_min = df['Load Cell'].iloc[self.frequency:2 * self.frequency].min()

        # Discard the 1st and last second in case it's a 'dirty' signal
        test_max = df['Load Cell'].iloc[self.frequency:-self.frequency].max()

        test_threshold = ((test_max - starting_min) * .10) + starting_min

        try:
            start_timestamp = df.loc[df['Load Cell'] > test_threshold].iloc[0].name
        except IndexError:
            start_timestamp = df.iloc[0].name

        return start_timestamp

    def _detect_ending_timestamp(self, df):
        # Discard the last second in case it's a 'dirty' signal
        ending_min = df['Load Cell'].iloc[-2 * self.frequency:-self.frequency].min()

        # Discard the 1st and last second in case it's a 'dirty' signal
        test_max = df['Load Cell'].iloc[self.frequency:-self.frequency].max()

        test_threshold = ((test_max - ending_min) * .05) + ending_min

        start_timestamp = self._detect_starting_timestamp(df)

        reduced_df = df.loc[df.index > start_timestamp + .01]

        try:
            end_timestamp = reduced_df.loc[reduced_df['Load Cell'] > test_threshold].iloc[-1].name
        except IndexError:
            end_timestamp = df.iloc[-1].name

        return end_timestamp

    def _zero_load_cell(self, df):
        # Discard the 1st second in case it's a 'dirty' signal
        starting_min = df['Load Cell'].iloc[self.frequency:2 * self.frequency].min()

        df['Load Cell'] = df['Load Cell'].apply(
            lambda v, linear_adj: v - linear_adj,
            linear_adj=starting_min
        )

        return df

    def _clean_up_test_data(self, df):
        start_timestamp = self._detect_starting_timestamp(df) - 5
        end_timestamp = self._detect_ending_timestamp(df) + 5

        df_zeroed = self._zero_load_cell(df)

        df_reduced = df_zeroed.loc[df_zeroed.index > start_timestamp]
        df_cleaned = df_reduced.loc[df_reduced.index < end_timestamp]

        df_cleaned.index = df_cleaned.index.map(
            lambda v: round(v - start_timestamp, 4)
        )

        return df_cleaned

    def _get_motor_impulse(self, df):
        return integrate.trapz(df['Load Cell'], dx=self.sample_time)

    @staticmethod
    def _impulse_letter(impulse):
        motor_codes = [
            ('1/8A', 0.3125),
            ('1/4A', 0.625),
            ('1/2A', 1.25),
            ('A', 2.5),
            ('B', 5),
            ('C', 10),
            ('D', 20),
            ('E', 40),
            ('F', 80),
            ('G', 160),
            ('H', 320),
            ('I', 640),
            ('J', 1280),
            ('K', 2560),
            ('L', 5120),
            ('M', 10240),
            ('N', 20480),
            ('O', 40960)
        ]

        motor_codes.reverse()

        for index, (code, max_impulse) in enumerate(motor_codes):
            if impulse > max_impulse:
                return motor_codes[index - 1][0]

        return '+P'

    def _avg_thrust(self, df):
        start_timestamp = self._detect_starting_timestamp(df)
        end_timestamp = self._detect_ending_timestamp(df)

        df_reduced = df.loc[df.index > start_timestamp]
        df_cleaned = df_reduced.loc[df_reduced.index < end_timestamp]

        return df_cleaned['Load Cell'].mean()

    def _burn_time(self, df):
        start_timestamp = self._detect_starting_timestamp(df)
        end_timestamp = self._detect_ending_timestamp(df)

        return end_timestamp - start_timestamp

    def output_final_results(self):
        df = self.get_data()

        df_clean = self._clean_up_test_data(df)

        impulse = self._get_motor_impulse(df_clean)
        impulse_letter = self._impulse_letter(impulse)
        average_thrust = self._avg_thrust(df_clean)
        burn_time = self._burn_time(df_clean)
        start_timestamp = self._detect_starting_timestamp(df_clean)
        end_timestamp = self._detect_ending_timestamp(df_clean)

        stats = f"""
        Motor: {impulse_letter}{int(average_thrust)}  
        Impulse: {impulse:.2f} Ns  
        Average Thrust: {average_thrust:.2f} N  
        Burn Time: {burn_time:.1f} s  
        Start Time: {start_timestamp:.1f} s  
        End Time: {end_timestamp:.1f} s  
        """

        print(stats)

        with open(f'output_data/{self.timestamp_label}/stats.txt', 'w') as f:
            f.write(stats)

        for sensor_id, sensor in self.sensors.items():
            fig = plt.figure()
            fig.suptitle(f'Rocket Motor Test - {self.timestamp_label} - {sensor["sensor_name"]}')

            subplot = fig.add_subplot(1, 1, 1)

            subplot.plot(df_clean[sensor['sensor_name']], linewidth=0.5)

            if sensor['sensor_name'] == 'Load Cell':
                fig.text(1, 1, stats, horizontalalignment='right', verticalalignment='top', transform=subplot.transAxes)

            subplot.set_xlabel('Seconds')
            subplot.set_ylabel(sensor['units'])
            subplot_max = roundup(df_clean[sensor['sensor_name']].max(), 10)
            subplot_min = rounddown(df_clean[sensor['sensor_name']].min(), 10)

            if pd.isnull(subplot_min):
                subplot_min = sensor['min']

            if pd.isnull(subplot_max):
                subplot_max = sensor['max']

            logging.debug(f'subplot_min: {subplot_min}')
            logging.debug(f'subplot_max: {subplot_max}')

            if sensor['sensor_name'] == 'Load Cell':
                subplot_min = -1

            if subplot_min == subplot_max:
                subplot_max += 10

            subplot.set_ylim([subplot_min, subplot_max])

            fig.savefig(f'output_data/{self.timestamp_label}/{sensor["sensor_name"]}.pdf', dpi=5000, orientation='landscape', bbox_inches='tight')

        plt.close('all')

        df_clean.to_csv(
            f'output_data/{self.timestamp_label}/processed_data.csv',
            index_label='seconds',
            mode='w',
            header=True,
            chunksize=10000
        )
