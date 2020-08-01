#!/usr/bin/python3
import click
import logging

from libraries.datalogging import DataLogger


logging.basicConfig(level=logging.INFO,
                    format='(%(threadName)-9s) %(message)s',)


@click.command()
@click.option('--freq', type=int, default=1000, help='Data Logging Frequency - Default: 1000 Hz')
@click.option('--maxruntime', type=int, default=0, help='Maximum Run Time - Default: 0 (for continuous)')
@click.option('--batch-exp', type=int, default=11, help='Data Read Batch Exponent - Default: 11 (ie. 2^11 records per batch)')
@click.option('--debug', is_flag=True, help='Set for more debugging')
@click.option('--nopdf', is_flag=False, default=True, help='Output PDF Chart')
@click.option('--onetrigger', is_flag=True, help='Only log one event. If not set, it will loop')
@click.option('--realtimegraph', is_flag=True, help='Real time QT5 graph')
@click.option('--calibrate', is_flag=True, help='Use this mode to assist with calibration')
def main(freq, maxruntime, batch_exp, debug, nopdf, onetrigger, realtimegraph, calibrate):
    column_names = [
        'Load Cell',
        'Chamber Pressure',
        'Tank Pressure',
        'Second Temperature',
        'Tank Temperature'
    ]

    if calibrate:
        freq = 200
        realtimegraph = True
        batch_exp = 8
        onetrigger = True
        nopdf = True
        maxruntime = 0

    if debug:
        logging.getLogger().setLevel(logging.DEBUG)

    while True:
        data_logger = DataLogger(freq, column_names, batch_exp, maxruntime, nopdf)

        if realtimegraph:
            # No reason importing QT messes if it's not needed
            from libraries.qt_helper import QTHelper

            QTHelper(data_logger)
            data_logger.output_data()
            data_logger.reset(wait_for_reset=True)
        else:
            data_logger.start()
            data_logger.run()
            data_logger.wait_for_keyboard()
            data_logger.output_data()

        if onetrigger:
            break


if __name__ == '__main__':
    main()
