#!/usr/bin/python3
import click
import logging
import json

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


@click.command()
@click.option('--freq', type=int, default=1000, help='Data Logging Frequency - Default: 1000 Hz')
@click.option('--maxruntime', type=int, default=0, help='Maximum Run Time (minutes) - Default: 0 (for continuous)')
@click.option('--batch-exp', type=int, default=11, help='Data Read Batch Exponent - Default: 11 (ie. 2^11 records per batch)')
@click.option('--debug', is_flag=True, help='Set for more debugging')
@click.option('--nopdf', is_flag=False, default=True, help='Output PDF Chart')
@click.option('--onetrigger', is_flag=True, help='Only log one event. If not set, it will loop')
@click.option('--realtimegraph', is_flag=True, help='Real time QT5 graph')
@click.option('--opamp_cal', is_flag=True, help='Use this mode to assist with calibrating the op-amp variable resistors')
@click.option('--scaling_cal', is_flag=True, help='Use this mode to auto calibrate the channels and determine the appropriate linear_adj and scalar_adj')
@click.option('--config', type=str, default='sensors.json', help='Config file')
def main(freq, maxruntime, batch_exp, debug, nopdf, onetrigger, realtimegraph, opamp_cal, scaling_cal, config):
    sensors = load_config(config)

    calibration = False

    if scaling_cal:
        freq = 200
        realtimegraph = False
        batch_exp = 8
        onetrigger = True
        nopdf = True
        maxruntime = 20/60  # 20 seconds
        calibration = True

    if opamp_cal:
        freq = 500
        realtimegraph = True
        batch_exp = 9
        onetrigger = True
        nopdf = True
        maxruntime = 0
        calibration = True

    if debug:
        logging.getLogger().setLevel(logging.DEBUG)

    data_logger = DataLogger(freq, sensors, batch_exp, maxruntime, nopdf, calibration)
    while True:
        if realtimegraph:
            # No reason importing QT messes if it's not needed
            from libraries.qt_helper import QTHelper

            QTHelper(data_logger, calibration)
            data_logger.output_data()
        else:
            data_logger.start()
            data_logger.run()
            data_logger.wait_for_datalogger()
            data_logger.output_data()

        if onetrigger:
            break

        data_logger.reset()

    if scaling_cal:
        test_data = data_logger.get_data()
        for sensor_id, sensor in sensors.items():
            logging.info(f'\nSensor Name: {sensor["sensor_name"]}')

            if sensor['sensor_type'] == 'loadcell':
                loadcell_max_lbs = float(input("Enter the calibration mass (lbs): "))
                loadcell_max_newtons = loadcell_max_lbs * 4.448222

                logging.info(f'Load cell calibration mass : {int(loadcell_max_newtons)} N')

                def roundup(x):
                    return x if x % 100 == 0 else x + 100 - x % 100

                # Get the min voltage for the sensor with no load on it, but throw out the initial and tail data
                min_no_load = test_data[sensor['sensor_name']][2048:-1048].min()
                current_load = 0
                sensor['linear_adj'] = current_load - min_no_load

                input('Place the test mass on the load cell and and push enter...')

                data_logger.start()
                data_logger.run()
                data_logger.wait_for_datalogger()
                data_logger.output_data()

                test_data2 = data_logger.get_data()

                # Get the mean voltage for the sensor with a load on it, but throw out the initial and tail data
                mean_load = test_data2[sensor['sensor_name']][2048:-1024].mean()

                logging.info(f'min_no_load: {min_no_load}')
                logging.info(f'mean_load: {mean_load}')

                sensor['scalar_adj'] = loadcell_max_newtons / (mean_load - min_no_load)

                # Add 50% to the max for wiggle room and then round up to the nearest 100 for clean charts
                sensor['max'] = roundup(loadcell_max_newtons * 1.5)

                logging.info(f'New max value: {sensor["max"]}')

            if sensor['sensor_type'] == 'temp':
                # Get the mean voltage for the sensor with a load on it, but throw out the initial and tail data
                mean_measured_voltage = test_data[sensor['sensor_name']][2048:-1024].mean()

                logging.info(f'mean_measured_temp: {mean_measured_voltage}')

                current_temp_F = float(input("Enter the current sensor temp (F): "))
                current_temp_C = (current_temp_F - 32) * (5/9)

                logging.info(f'Current temp: {int(current_temp_C)} C')

                current_temp_voltage = ((current_temp_C * 0.005) + 1.25) * sensor['opamp_mul']

                sensor['linear_adj'] = current_temp_voltage - mean_measured_voltage
                sensor['scalar_adj'] = 1

            if sensor['sensor_type'] == 'pressure':
                # Get the mean voltage for the sensor with a load on it, but throw out the initial and tail data
                mean_measured_pressure = test_data[sensor['sensor_name']][2048:-1024].mean()

                logging.info(f'mean_measured_pressure: {mean_measured_pressure}')

                current_pressure = 0
                sensor['linear_adj'] = current_pressure - mean_measured_pressure
                sensor['scalar_adj'] = 1

            logging.info(f'New linear_adj value: {sensor["linear_adj"]}')
            logging.info(f'New scalar_adj value: {sensor["scalar_adj"]}')

        if input('Do you want to write out these values (y/n)? ') == 'y':
            save_config(sensors, config)

    data_logger.reset()


if __name__ == '__main__':
    main()
