#!/usr/bin/python3

import click
import logging
import time
import sys

from libraries.gopro import GoPro
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
@click.option('-r', '--remoteid', type=int, default=None, help='Remote ID')
@click.option('--nopreview', is_flag=True, help='Turn off the preview window')
def main(prefix, debug, remoteid, nopreview):
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)

    lc = LaunchControl(remoteid)

    camera = Camera()
    gopro = GoPro()

    while True:
        if not nopreview:
            camera.start_preview()

        if not lc.wait_for_ready():
            continue

        camera.start_recording(filename=f'{prefix}-{int(time.time())}.h264')
        gopro.start_recording()

        if not lc.wait_for_safe():
            continue

        if not nopreview:
            camera.stop_preview()

        camera.stop_recording()
        gopro.stop_recording()


if __name__ == '__main__':
    main()
