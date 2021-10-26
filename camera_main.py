#!/usr/bin/python3

import click
import logging
import time
import sys
import os

from camera.libraries.gopro import GoPro
from camera.libraries.camera import Camera
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
@click.option('-p', '--prefix', type=str, default='pi-hq', help='Filename prefix')
@click.option('-d', '--debug', is_flag=True, help='Turn on debugging')
@click.option('-r', '--remoteid', type=int, default=None, help='Remote ID')
@click.option('--nogopro', is_flag=True, help='Do not use a wireless gopro')
@click.option('--nopreview', is_flag=True, help='Turn off the preview window')
def main(prefix, debug, remoteid, nogopro, nopreview):
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)

    lc = LaunchControl(remoteid)

    media_dirs = os.listdir('/media/pi/')
    if media_dirs:
        base_dir = f'/media/pi/{media_dirs[0]}/'
    else:
        base_dir = '/home/pi/Desktop/video/'

    if not os.path.exists(base_dir):
        os.makedirs(base_dir)

    camera = Camera(base_dir)

    if not nogopro:
        gopro = GoPro(base_dir)

    while True:
        if not nopreview:
            camera.start_preview()

        if not lc.wait_for_start_cameras():
            continue

        if not nopreview:
            camera.stop_preview()

        camera.start_recording(filename=f'{prefix}-{int(time.time())}.h264')

        if not nogopro:
            gopro.start_recording()

        if not lc.wait_for_stop_cameras():
            continue

        camera.stop_recording()

        if not nogopro:
            gopro.stop_recording()


if __name__ == '__main__':
    main()
