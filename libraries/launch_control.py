import time

from libraries.gpio import GPIO
from libraries.comms import Comms


class LaunchControl:
    def __init__(self):
        self.relays = GPIO()
        self.relays.all_relays_off()
        self.current_state = 'safe'

        message_types = {
            'ready': self.ready,
            'safe': self.safe,
            'launch': self.launch
        }

        self.comms = Comms(message_types)

    def wait_for_ready(self):
        print('Waiting for the ready command to be sent.')
        while self.current_state != 'ready':
            time.sleep(0.1)

        self.ready()

    def wait_for_safe(self):
        print('Waiting for the safe command to be sent.')
        while self.current_state != 'safe':
            time.sleep(0.1)

        self.safe()

    def ready(self, args=None):
        print('Received ready signal')
        self.current_state = 'ready'
        self.relays.relay_on('warn_lights')

    def safe(self, args=None):
        print('Received safe signal')
        self.current_state = 'safe'
        self.relays.all_relays_off()

    def launch(self, args=None):
        print('Received launch signal')
        if self.current_state == 'ready':
            self.current_state = 'ignition'
            self.relays.relay_on('ignition')
            time.sleep(30)
            self.relays.relay_off('ignition')
            self.current_state = 'post-ignition'
