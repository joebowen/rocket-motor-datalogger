#!/usr/bin/python3

import click
import random
import logging
import time
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
def main(debug):
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)

    remote_id = random.randint(0, 9999)
    print(f'remote id: {remote_id}')

    disp = Display(remote_id)

    lc = LaunchControl(remote_id, disp)

    while True:
        print('Safe...')
        disp.add_message('SAFE')

        lc.wait_for_ready()
        print('Ready...')
        disp.add_message('READY')

        if lc.wait_for_launch():
            print('Launch...')
            disp.add_message('LAUNCH')

        lc.send_safe()


if __name__ == '__main__':
    main()
