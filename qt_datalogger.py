#!/usr/bin/python3
import click
import logging

from libraries.datalogging import DataLogger


logging.basicConfig(level=logging.INFO,
                    format='(%(threadName)-9s) %(message)s',)

@click.command()
@click.option('--freq', type=int, default=1000, help='Data Logging Frequency - Default: 1000 Hz')
@click.option('--maxruntime', type=int, default=0, help='Maximum Run Time - Default: 0 (for continuous)')
@click.option('--batch-exp', type=int, default=10, help='Data Read Batch Exponent - Default: 13 (ie. 2^13 records per batch)')
@click.option('--debug', is_flag=True, help='Set for more debugging')
@click.option('--pdf', is_flag=True, help='Output PDF Chart')
@click.option('--continuous', is_flag=True, help='Continue after "exit"')
@click.option('--headless', type=bool, default=True, help='Set False for real time QT5 graph - Default: True')
def main(freq, maxruntime, debug, headless, pdf, continuous, batch_exp=13):
    column_names = [
        'Load Cell',
        'Chamber Pressure',
        'Tank Pressure',
        'Second Temperature',
        'Tank Temperature'
    ]

    if debug:
        logging.getLogger().setLevel(logging.DEBUG)

    while True:
        data_logger = DataLogger(freq, column_names, batch_exp, maxruntime, pdf)

        if headless:
            data_logger.start()
            data_logger.run()
            data_logger.output_data()
        else:
            # No reason importing QT messes if it's not needed
            from libraries.qt_helper import QTHelper

            QTHelper(data_logger, debug)

        if not continuous:
            break


if __name__ == '__main__':
    main()
