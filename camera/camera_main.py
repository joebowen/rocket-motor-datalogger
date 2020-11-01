#!/usr/bin/python3

import click
import random
import logging
import time
import sys

from libraries.camera import Camera
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
@click.option('-p', '--prefix', type=str, default='video', help='Filename prefix')
@click.option('-d', '--debug', is_flag=True, help='Turn on debugging')
def main(debug, prefix):
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)

    remote_id = random.randint(0, 9999)
    print(f'remote id: {remote_id}')

    camera = Camera()

    camera.start_preview()

    lc = LaunchControl(remote_id)

    while True:
        if not lc.wait_for_ready():
            continue

        camera.start_recording(filename=f'{prefix}.h264')

        if not lc.wait_for_safe():
            continue

        camera.stop_recording()


if __name__ == '__main__':
    main()
