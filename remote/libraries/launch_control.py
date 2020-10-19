import time
import random

from remote.libraries.gpio import GPIO
from remote.libraries.comms import Comms


class LaunchControl:
    def __init__(self):
        self.gpio = GPIO()
        self.current_state = 'safe'
        self.safe()

        message_types = {
            'ready': self.ready,
            'safe': self.safe,
            'launch': self.launch
        }

        remoteid = random.randint(0, 1000)

        print(f'remote id: {remoteid}')

        self.comms = Comms(message_types, remoteid=remoteid)

    def wait_for_ready(self):
        self.gpio.wait_for_button('ready')

    def wait_for_safe(self):
        if self.comms:
            while self.current_state != 'safe':
                time.sleep(1)

        self.safe()

    def ready(self, args=None):
        self.current_state = 'ready'
        self.relays.relay_on('warn_lights')

    def safe(self, args=None):
        self.current_state = 'safe'
        self.relays.all_relays_off()

    def launch(self, args=None):
        if self.current_state == 'ready':
            self.current_state = 'ignition'
            self.relays.relay_on('ignition')
            time.sleep(30)
            self.relays.relay_off('ignition')
            self.current_state = 'post-ignition'
