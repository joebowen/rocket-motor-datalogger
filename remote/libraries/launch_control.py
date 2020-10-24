from libraries.gpio import GPIO
from libraries.comms import Comms


class LaunchControl:
    def __init__(self, remoteid, display):
        self.gpio = GPIO()
        self.receive_safe()

        message_types = {
            'ready': self.receive_ready,
            'safe': self.receive_safe,
            'launch': self.receive_launch
        }

        self.display = display
        self.comms = Comms(message_types, remoteid=remoteid, display=display)

    def wait_for_ready(self):
        print(f'Waiting for the ready switch to be turned on.')
        self.gpio.wait_for_button('ready')

        self.send_ready()

        print('Ready...')
        self.display.add_message('READY')

    def send_ready(self):
        message_id = self.comms.send_message(command='ready')

        while not self.comms.wait_for_ack(message_id):
            if not self.gpio.is_button_on('ready'):
                return False

        return True

    def wait_for_safe(self):
        print(f'Waiting for the ready switch to be turned off.')
        self.gpio.wait_for_button_release('ready')

        self.send_safe()

    def send_safe(self):
        self.comms.send_message(command='safe')
        print('Safe...')
        self.display.add_message('SAFE')

    def wait_for_launch(self):
        print(f'Waiting for the launch switch to be pushed.')
        while not self.gpio.is_button_on('launch'):
            if not self.gpio.is_button_on('ready'):
                return False

        self.send_launch()

        self.gpio.wait_for_button_release('launch')

        print('Launch...')
        self.display.add_message('LAUNCH')

    def send_launch(self):
        message_id = self.comms.send_message(command='launch')

        while not self.comms.wait_for_ack(message_id):
            if not self.gpio.is_button_on('ready'):
                return False

    def receive_ready(self, args=None):
        print('Received ready signal')

    def receive_safe(self, args=None):
        print('Received safe signal')

    def receive_launch(self, args=None):
        print('Received launch signal')
