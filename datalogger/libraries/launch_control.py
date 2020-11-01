import time

from libraries.gpio import GPIO
from libraries.comms import Comms


class LaunchControl:
    def __init__(self, remoteid=None):
        self.relays = GPIO()
        self.relays.all_relays_off()
        self.current_state = 'safe'

        message_types = {
            'ready': self.ready,
            'safe': self.safe,
            'launch': self.launch,
            'post-launch': self.post_launch,
            'fill-relay-on': self.fill_relay_on,
            'fill-relay-off': self.fill_relay_off,
            'dump-relay-on': self.dump_relay_on,
            'dump-relay-off': self.dump_relay_off
        }

        if not remoteid:
            remoteid = int(input("Enter the remote id shown on the launch controller: "))

        self.comms = Comms(message_types, remoteid)

    def wait_for_ready(self):
        print('Waiting for the ready command to be sent.')
        while self.current_state != 'ready':
            time.sleep(0.01)

        self.ready()

    def wait_for_safe(self):
        print('Waiting for the safe command to be sent.')
        while self.current_state != 'safe':
            time.sleep(0.01)

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
            self.comms.send_message(command='post-launch')

    def post_launch(self, args=None):
        print('Received post launch signal')

    def fill_relay_on(self, args=None):
        print('Received fill relay on signal')

        self.relays.relay_on('fill_solenoid')

    def fill_relay_off(self, args=None):
        print('Received fill relay off signal')

        self.relays.relay_off('fill_solenoid')

    def dump_relay_on(self, args=None):
        print('Received dump relay on signal')

        self.relays.relay_on('dump_solenoid')

    def dump_relay_off(self, args=None):
        print('Received dump relay off signal')

        self.relays.relay_off('dump_solenoid')
