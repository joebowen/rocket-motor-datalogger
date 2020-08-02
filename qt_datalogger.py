#!/usr/bin/python3
import click
import logging
import json

from libraries.datalogging import DataLogger


logging.basicConfig(level=logging.INFO,
                    format='(%(threadName)-9s) %(message)s',)


def load_config(config_file='sensors.json'):
    with open(config_file) as config_file:
        config = json.load(config_file)

        for sensor_id, sensor in config.items():
            if sensor['sensor_type'] == 'loadcell':
                sensor['formula'] = lambda v: v
            if sensor['sensor_type'] == 'temp':
                sensor['formula'] = lambda v, opamp_mul: ((v / opamp_mul) - 1.25) / 0.005
            if sensor['sensor_type'] == 'pressure':
                sensor['formula'] = lambda v, max_psi, opamp_mul: (v / opamp_mul / 4) * max_psi
            else:
                Exception('Unknown sensor type')

        return config


def save_config(sensors, config_file='sensors.json'):
    for sensor_id, sensor in sensors.items():
        del (sensor['formula'])

    with open(config_file, mode='w') as config_file:
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
@click.option('--scaling_cal', type=str, default=None, help='Use this mode to auto calibrate the channels and determine the appropriate linear_adj and scalar_adj')
@click.option('--config', type=str, default='sensors.json', help='Config file')
def main(freq, maxruntime, batch_exp, debug, nopdf, onetrigger, realtimegraph, opamp_cal, scaling_cal, config):
    sensors = load_config(config)

    if scaling_cal:
        input('Please turn on the unit (both red and green switches) and press enter...')
        freq = 200
        realtimegraph = False
        batch_exp = 8
        onetrigger = True
        nopdf = True
        maxruntime = 0.25


    if opamp_cal:
        freq = 200
        realtimegraph = True
        batch_exp = 8
        onetrigger = True
        nopdf = True
        maxruntime = 0

    if debug:
        logging.getLogger().setLevel(logging.DEBUG)

    while True:
        data_logger = DataLogger(freq, sensors, batch_exp, maxruntime, nopdf)

        if realtimegraph:
            # No reason importing QT messes if it's not needed
            from libraries.qt_helper import QTHelper

            QTHelper(data_logger)
            data_logger.output_data()
        else:
            data_logger.start()
            data_logger.run()
            data_logger.wait_for_keyboard()
            data_logger.output_data()

        if onetrigger:
            break

    if scaling_cal:
        test_data = data_logger.get_data()
        if sensors[scaling_cal]['sensor_type'] == 'loadcell':
            loadcell_max_lbs = float(input("Enter the calibration mass (lbs): "))
            sensors[scaling_cal]['max'] = loadcell_max_lbs * 4.448222

            mean_no_load = test_data[sensors[scaling_cal]['sensor_name']].mean()
            sensors[scaling_cal]['linear_adj'] = -mean_no_load

            input("Place the test mass on the load cell and press enter.")

            data_logger.start()
            data_logger.run()
            data_logger.wait_for_keyboard()
            data_logger.output_data()

            mean_load = test_data[sensors[scaling_cal]['sensor_name']].mean()
            sensors[scaling_cal]['scalar_adj'] = sensors[scaling_cal]['max'] / (mean_load - mean_no_load)

        if sensors[scaling_cal]['sensor_type'] == 'temp':
            mean_measured_temp = test_data[sensors[scaling_cal]['sensor_name']].mean()

            current_temp_F = float(input("Enter the current sensor temp (F): "))
            current_temp_C = (current_temp_F - 32) * (5/9)

            sensors[scaling_cal]['linear_adj'] = current_temp_C - mean_measured_temp
            sensors[scaling_cal]['scalar_adj'] = 1

        if sensors[scaling_cal]['sensor_type'] == 'pressure':
            mean_measured_pressure = test_data[sensors[scaling_cal]['sensor_name']].mean()

            current_pressure = 0
            sensors[scaling_cal]['linear_adj'] = current_pressure - mean_measured_pressure
            sensors[scaling_cal]['scalar_adj'] = 1

        logging.info(f'New linear_adj value: {sensors[scaling_cal]["linear_adj"]}')
        logging.info(f'New scalar_adj value: {sensors[scaling_cal]["scalar_adj"]}')
        if input('Do you want to write out these values (y/n)? ') == 'y':
            save_config(sensors, config)

    data_logger.reset(wait_for_reset=True)


if __name__ == '__main__':
    main()
