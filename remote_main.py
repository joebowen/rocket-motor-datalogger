#!/usr/bin/python3

import click
import random
import logging
import sys

from gpiozero import Button

from remote.libraries.display import Display
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


def wait_for_safe(lc):
    print(f'Waiting for the ready switch to be turned off.')
    lc.gpio.wait_for_button_release('ready')

    lc.send_safe()


def wait_for_ready(lc):
    print(f'Waiting for the ready switch to be turned on.')
    lc.gpio.wait_for_button('ready')

    lc.send_start_cameras()
    is_ready = lc.send_ready()

    if is_ready:
        print('Ready...')
        lc.display.add_message('READY')
        lc.current_state = 'ready'

    return is_ready


def wait_for_launch(lc, timeout=45):
    print(f'Waiting for the launch switch to be pushed.')
    while not lc.gpio.is_button_on('launch'):
        if not lc.gpio.is_button_on('ready'):
            lc.send_safe()
            return False

        if not lc.filling and lc.gpio.is_button_on('fill'):
            lc.filling = True
            lc.send_fill_on()

        if lc.filling and not lc.gpio.is_button_on('fill'):
            lc.filling = False
            lc.send_fill_off()

        if not lc.dumping and lc.gpio.is_button_on('dump'):
            lc.dumping = True
            lc.send_dump_on()

        if lc.dumping and not lc.gpio.is_button_on('dump'):
            lc.dumping = False
            lc.send_dump_off()

    is_launch = lc.send_launch()

    if is_launch:
        print('Launch...')
        lc.display.add_message('LAUNCH')
        lc.current_state = 'launch'

        while lc.gpio.is_button_on('launch'):
            if not lc.gpio.is_button_on('ready'):
                lc.send_safe()
                return False

        lc.send_post_launch()

    return is_launch


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

    buttons = {
        'ready': Button(2),
        'launch': Button(3),
        'fill': Button(5),
        'dump': Button(6)
    }

    lc = LaunchControl(remoteid, display=disp, buttons=buttons)

    disp.add_message('MAKE\nSAFE')
    wait_for_safe(lc)

    while True:
        if not wait_for_ready(lc):
            continue

        if not wait_for_launch(lc):
            continue


if __name__ == '__main__':
    main()
