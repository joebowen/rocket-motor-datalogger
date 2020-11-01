import time
import logging

from libraries.comms import Comms


class LaunchControl:
    def __init__(self, remoteid):
        self.current_state = 'safe'

        message_types = {
            'ready': self.receive_ready,
            'safe': self.receive_safe,
            'launch': self.receive_launch,
            'post-launch': self.receive_post_launch,
            'fill-relay-on': self.receive_fill_relay_on,
            'fill-relay-off': self.receive_fill_relay_off,
            'dump-relay-on': self.receive_dump_relay_on,
            'dump-relay-off': self.receive_dump_relay_off
        }

        if not remoteid:
            remoteid = int(input("Enter the remote id shown on the launch controller: "))

        self.comms = Comms(message_types, remoteid=remoteid)

    def wait_for_ready(self):
        logging.info('Waiting for the ready command to be sent.')
        while self.current_state != 'ready':
            time.sleep(0.1)

        return True

    def wait_for_safe(self):
        logging.info('Waiting for the safe command to be sent.')
        while self.current_state != 'safe':
            time.sleep(0.1)

        return True

    def receive_ready(self, args=None):
        logging.info('Received ready signal')
        self.current_state = 'ready'

    def receive_safe(self, args=None):
        logging.info('Received safe signal')
        self.current_state = 'safe'

    def receive_launch(self, args=None):
        logging.info('Received launch signal')

    def receive_post_launch(self, args=None):
        logging.info('Received post launch signal')

    def receive_fill_relay_on(self, args=None):
        logging.info('Received fill relay on signal')

    def receive_fill_relay_off(self, args=None):
        logging.info('Received fill relay off signal')

    def receive_dump_relay_on(self, args=None):
        logging.info('Received dump relay on signal')

    def receive_dump_relay_off(self, args=None):
        logging.info('Received dump relay off signal')