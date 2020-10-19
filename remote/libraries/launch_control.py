import time
import random

from remote.libraries.gpio import GPIO
from remote.libraries.comms import Comms


class LaunchControl:
    def __init__(self):
        self.gpio = GPIO()
        self.current_state = 'safe'
        self.receive_safe()

        message_types = {
            'ready': self.receive_ready,
            'safe': self.receive_safe,
            'launch': self.receive_launch
        }

        remoteid = random.randint(0, 100000)

        print(f'remote id: {remoteid}')

        self.comms = Comms(message_types, remoteid=remoteid)

    def wait_for_ready(self):
        print(f'Waiting for the ready switch to be turned on.')
        self.gpio.wait_for_button('ready')

        self.send_ready()

    def send_ready(self):
        self.comms.send_message(command='ready')

    def wait_for_safe(self):
        print(f'Waiting for the ready switch to be turned off.')
        self.gpio.wait_for_button_release('ready')

        self.send_safe()

    def send_safe(self):
        self.comms.send_message(command='safe')

    def wait_for_launch(self):
        print(f'Waiting for the launch switch to be pushed.')
        self.gpio.wait_for_button_release('launch')

        self.send_launch()

    def send_launch(self):
        self.comms.send_message(command='launch')

    def receive_ready(self, args=None):
        print('Received ready signal')

    def receive_safe(self, args=None):
        print('Received safe signal')

    def receive_launch(self, args=None):
        print('Received launch signal')
