#!/usr/bin/python3

import click
import logging
import time
import sys

from libraries.launch_control import LaunchControl


@click.command()
@click.option('-d', '--debug', is_flag=True, help='Turn on debugging')
def main(debug):
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)

    lc = LaunchControl()

    input('Press enter when ready...')

    lc.send_ready()

    input('Press enter to launch...')

    lc.send_launch()
    time.sleep(10)
    lc.send_safe()

    sys.exit()


if __name__ == '__main__':
    main()
