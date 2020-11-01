import time

from libraries.comms import Comms


class LaunchControl:
    def __init__(self, remoteid):
        self.receive_safe()
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

        self.comms = Comms(message_types, remoteid=remoteid, display=display)

    def wait_for_ready(self):
        print('Waiting for the ready command to be sent.')
        while self.current_state != 'ready':
            time.sleep(0.01)

    def wait_for_safe(self):
        print('Waiting for the safe command to be sent.')
        while self.current_state != 'safe':
            time.sleep(0.01)

    def receive_ready(self, args=None):
        print('Received ready signal')
        self.current_state = 'ready'

    def receive_safe(self, args=None):
        print('Received safe signal')
        self.current_state = 'safe'

    def receive_launch(self, args=None):
        print('Received launch signal')

    def receive_post_launch(self, args=None):
        print('Received post launch signal')

    def receive_fill_relay_on(self, args=None):
        print('Received fill relay on signal')

    def receive_fill_relay_off(self, args=None):
        print('Received fill relay off signal')

    def receive_dump_relay_on(self, args=None):
        print('Received dump relay on signal')

    def receive_dump_relay_off(self, args=None):
        print('Received dump relay off signal')
