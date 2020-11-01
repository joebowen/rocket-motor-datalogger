#!/usr/bin/python3

import click
import random
import logging
import sys

from libraries.display import Display
from libraries.launch_control import LaunchControl


class StreamToLogger(object):
    ''' Fake file-like stream object that redirects writes to a logger instance.
    '''

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
@click.option('-d', '--debug', is_flag=True, help='Turn on debugging')
@click.option('-r', '--remoteid', type=int, default=None, help='Remote ID')
def main(debug, remoteid):
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)

    if not remoteid:
        remoteid = random.randint(0, 9999)

    print(f'remote id: {remoteid}')

    disp = Display(remoteid)

    lc = LaunchControl(remoteid, disp)

    disp.add_message('MAKE\nSAFE')
    lc.wait_for_safe()

    while True:
        if not lc.wait_for_ready():
            continue

        if not lc.wait_for_launch():
            continue


if __name__ == '__main__':
    main()
