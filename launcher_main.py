#!/usr/bin/python3

import click
import logging
import sys

from gpiozero import LED

from common.launch_control import LaunchControl


class StreamToLogger(object):
    """ Fake file-like stream object that redirects writes to a logger instance.
    """

    def __init__(self, logger, log_level=logging.INFO):
        self.logger = logger
        self.log_level = log_level
        self.linebuf = ''

    def write(self, buf):
        for line in buf.rstrip().splitlines():
            self.logger.log(self.log_level, line.rstrip())

    def flush(self):
        pass


logging.basicConfig(level=logging.INFO, format='(%(threadName)-9s) %(message)s', )

stdout_logger = logging.getLogger('STDOUT')
sl = StreamToLogger(stdout_logger, logging.INFO)
sys.stdout = sl


@click.command()
@click.option('-r', '--remoteid', type=int, default=None, help='Remote ID')
@click.option('-d', '--debug', is_flag=True, help='Turn on debugging')
def main(remoteid, debug):
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)

    relays = {
        'fill_solenoid': LED(19, active_high=False),
        'dump_solenoid': LED(13, active_high=False),
        'ignition': LED(6, active_high=False),
        'warn_lights': LED(26, active_high=False)
    }

    lc = LaunchControl(remoteid, relays=relays)

    while True:
        lc.wait_for_ready()

        lc.wait_for_safe()


if __name__ == '__main__':
    main()
