#!/usr/bin/python3

import click

from libraries.datalogging import DataLogger


@click.command()
@click.option('--freq', type=int, default=1000, help='Data Logging Frequency - Default: 1000 Hz')
@click.option('--debug', is_flag=True, help='Set for more debugging')
@click.option('--headless', type=bool, default=True, help='Set False for real time QT5 graph - Default: True')
def main(freq, debug, headless):
    column_names = [
        'Load Cell',
        'Chamber Pressure',
        'Tank Pressure',
        'Second Temperature',
        'Tank Temperature'
    ]

    data_logger = DataLogger(freq, column_names, debug)

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
