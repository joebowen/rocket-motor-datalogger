#!/usr/bin/python3

import click
import logging
import json
import sys

from libraries.datalogging import DataLogger


logging.basicConfig(level=logging.INFO,
                    format='(%(threadName)-9s) %(message)s',)

logging.getLogger('matplotlib').setLevel(logging.WARNING)


def load_config(config_file_name='sensors.json'):
    with open(config_file_name) as config_file:
        config = json.load(config_file)

        for sensor_id, sensor in config.items():
            if sensor['sensor_type'] == 'loadcell':
                sensor['formula'] = lambda v: v
            if sensor['sensor_type'] == 'temp':
                sensor['formula'] = lambda v: (v - 1.25) / 0.005
            if sensor['sensor_type'] == 'pressure':
                sensor['formula'] = lambda v, max_psi: (v / 4) * max_psi
            else:
                Exception('Unknown sensor type')

        return config


def save_config(sensors, config_file_name='sensors.json'):
    for sensor_id, sensor in sensors.items():
        if 'formula' in sensor:
            del(sensor['formula'])

    with open(config_file_name, mode='w') as config_file:
        json.dump(sensors, config_file, indent=4, sort_keys=True)


def roundup(x, mod):
    return x if x % mod == 0 else x + mod - x % mod


@click.command()
@click.option('-f', '--freq', type=int, default=1000, help='Data Logging Frequency - Default: 1000 Hz')
@click.option('-l', '--loop', is_flag=True, help='Continue capturing logs in a loop')
@click.option('-g', '--graph', is_flag=True, help='Real time QT5 graph')
@click.option('-c', '--calibrate', is_flag=True, help='Use this mode to calibrate the channels')
@click.option('--config', type=str, default='sensors.json', help='Config file - Default: sensors.json')
@click.option('--maxruntime', type=int, default=0, help='Maximum Run Time (seconds) - Default: 0 (for continuous)')
@click.option('--debug', is_flag=True, help='Turn on debugging')
def main(freq, loop, graph, calibrate, config, maxruntime, debug):
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)

    sensors = load_config(config)

    if calibrate:
        freq = 200
        graph = True
        loop = False
        maxruntime = 0

    data_logger = DataLogger(freq, sensors, maxruntime, calibrate)
    while True:
        if graph:
            # No reason importing QT messes if it's not needed
            from libraries.qt_helper import QTHelper

            QTHelper(data_logger, calibrate)
            if not calibrate:
                data_logger.output_final_results()
        else:
            data_logger.start()
            data_logger.wait_for_datalogger()
            if not calibrate:
                data_logger.output_final_results()

        if not loop:
            break

    if calibrate:
        input('Remove any test weights from the stand and press enter.')
        maxruntime = 10  # seconds
        data_logger = DataLogger(freq, sensors, maxruntime, calibrate)
        data_logger.start()
        data_logger.wait_for_datalogger()

        test_data = data_logger.get_raw_data()

        current_temp_F = input("Enter the current sensor temp (F): ")
        current_temp_C = (float(current_temp_F) - 32) * (5 / 9)

        logging.info(f'Current temp: {int(current_temp_C)} C')

        for sensor_id, sensor in sensors.items():
            logging.info(f'\nSensor Name: {sensor["sensor_name"]}')

            if sensor['sensor_type'] == 'loadcell':
                loadcell_max_lbs = float(input("Enter the calibration mass (lbs): "))
                loadcell_max_newtons = loadcell_max_lbs * 4.448222

                logging.info(f'Load cell calibration mass : {int(loadcell_max_newtons)} N')

                # Get the min voltage for the sensor with no load on it, but throw out the initial and tail seconds
                min_no_load = test_data[sensor['sensor_name']].iloc[freq:-freq].min()
                current_load = 0
                sensor['linear_adj'] = current_load - min_no_load

                input('Place the test mass on the load cell and and push enter...')

                data_logger.start()
                data_logger.wait_for_datalogger()

                test_data2 = data_logger.get_data()

                # Get the mean voltage for the sensor with a load on it, but throw out the initial and tail seconds
                mean_load = test_data2[sensor['sensor_name']].iloc[freq:-freq].mean()

                logging.info(f'min_no_load: {min_no_load}')
                logging.info(f'mean_load: {mean_load}')

                sensor['scalar_adj'] = loadcell_max_newtons / (mean_load - min_no_load)

                # Add 50% to the max for wiggle room and then round up to the nearest 10 for clean charts
                sensor['max'] = roundup(loadcell_max_newtons * 1.5, 10)

                logging.info(f'New max value: {sensor["max"]}')

            if sensor['sensor_type'] == 'temp':
                # Get the mean voltage for the sensor with a load on it, but throw out the initial and tail seconds
                mean_measured_voltage = test_data[sensor['sensor_name']][freq:-freq].mean()

                logging.info(f'mean_measured_temp: {mean_measured_voltage}')

                current_temp_voltage = ((current_temp_C * 0.005) + 1.25) * sensor['opamp_mul']

                sensor['linear_adj'] = current_temp_voltage - mean_measured_voltage
                sensor['scalar_adj'] = 1

            if sensor['sensor_type'] == 'pressure':
                # Get the mean voltage for the sensor with a load on it, but throw out the initial and tail seconds
                mean_measured_pressure = test_data[sensor['sensor_name']][freq:-freq].mean()

                logging.info(f'mean_measured_pressure: {mean_measured_pressure}')

                current_pressure = 0
                sensor['linear_adj'] = current_pressure - mean_measured_pressure
                sensor['scalar_adj'] = 1

            logging.info(f'New linear_adj value: {sensor["linear_adj"]}')
            logging.info(f'New scalar_adj value: {sensor["scalar_adj"]}')

        if input('Do you want to write out these values (y/n)? ') == 'y':
            save_config(sensors, config)

    sys.exit()


if __name__ == '__main__':
    main()
