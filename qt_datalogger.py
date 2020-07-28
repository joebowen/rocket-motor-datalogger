#!/usr/bin/python3

import click

from libraries.datalogging import DataLogger


@click.command()
@click.option('--freq', type=int, default=1000, help='Data Logging Frequency - Default: 1000 Hz')
@click.option('--maxruntime', type=int, default=0, help='Maximum Run Time - Default: 0 (for continuous)')
@click.option('--batch-exp', type=int, default=10, help='Data Read Batch Exponent - Default: 10 (ie. 2^10 records per batch)')
@click.option('--debug', is_flag=True, help='Set for more debugging')
@click.option('--headless', type=bool, default=True, help='Set False for real time QT5 graph - Default: True')
def main(freq, maxruntime, debug, headless, batch_exp=10):
    column_names = [
        'Load Cell',
        'Chamber Pressure',
        'Tank Pressure',
        'Second Temperature',
        'Tank Temperature'
    ]

    data_logger = DataLogger(freq, column_names, batch_exp, debug, maxruntime)

    if headless:
        data_logger.start()
        data_logger.run()
        data_logger.output_data()
    else:
        # No reason importing QT messes if it's not needed
        from libraries.qt_helper import QTHelper

        QTHelper(data_logger, debug)


if __name__ == '__main__':
    main()
