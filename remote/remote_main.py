#!/usr/bin/python3

import click
import logging

from remote.libraries.launch_control import LaunchControl


@click.command()
@click.option('-d', '--debug', is_flag=True, help='Turn on debugging')
def main(debug):
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)

    lc = LaunchControl()


if __name__ == '__main__':
    main()
