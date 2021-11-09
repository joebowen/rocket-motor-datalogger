import logging

from common.gpio import GPIO
from common.comms import Comms


class LaunchControl:
    def __init__(self, remoteid, display=None, relays=None, buttons=None):
        self.current_state = 'safe'
        self.filling = False
        self.dumping = False

        message_types = {
            'ready': self.receive_ready,
            'safe': self.receive_safe,
            'launch': self.receive_launch,
            'post-launch': self.receive_post_launch,
            'fill-relay-on': self.receive_fill_relay_on,
            'fill-relay-off': self.receive_fill_relay_off,
            'dump-relay-on': self.receive_dump_relay_on,
            'dump-relay-off': self.receive_dump_relay_off,
            'start-cameras': self.receive_start_cameras,
            'stop-cameras': self.receive_stop_cameras
        }

        self.gpio = GPIO(relays=relays, buttons=buttons)
        self.gpio.all_relays_off()

        self.display = display
        self.comms = Comms(message_types, remoteid=remoteid, display=display)


    def send_start_cameras(self):
        logging.info(f'Starting Cameras.')
        message_ids = [self.comms.send_message(command='start-cameras')]

        # while not self.comms.wait_for_ack(message_ids, timeout=1):
        #     logging.info('Waiting for cameras to start...')
        #     message_ids.append(self.comms.send_message(command='start-cameras'))

        return True

    def send_ready(self):
        logging.info(f'Sending Ready Command')
        message_ids = [self.comms.send_message(command='ready')]

        while not self.comms.wait_for_ack(message_ids, timeout=60):
            message_ids.append(self.comms.send_message(command='ready'))

            if not self.gpio.is_button_on('ready'):
                self.send_safe()
                return False

        return True

    def send_stop_cameras(self):
        logging.info(f'Sending stop cameras command.')
        self.comms.send_message(command='stop-cameras')

    def send_safe(self):
        logging.info(f'Sending safe command.')
        message_ids = [self.comms.send_message(command='safe')]

        while not self.comms.wait_for_ack(message_ids, timeout=60):
            logging.info('Waiting for safe...')
            message_ids.append(self.comms.send_message(command='safe'))

        logging.info('Safe...')
        self.display.add_message('SAFE')
        self.current_state = 'safe'

    def send_launch(self):
        logging.info('Sending Launch command!')
        message_ids = [self.comms.send_message(command='launch')]

        while not self.comms.wait_for_ack(message_ids, timeout=60):
            logging.info('Waiting for launch...')
            message_ids.append(self.comms.send_message(command='launch'))

            if not self.gpio.is_button_on('ready'):
                self.send_safe()
                return False

        return True

    def send_post_launch(self):
        logging.info('Sending Post Launch command.')
        message_ids = [self.comms.send_message(command='post-launch')]

        while not self.comms.wait_for_ack(message_ids, timeout=60):
            logging.info('Waiting for post launch...')
            message_ids.append(self.comms.send_message(command='post-launch'))

            if not self.gpio.is_button_on('ready'):
                self.send_safe()
                return False

        return True

    def receive_ready(self, args):
        logging.info('Received ready signal')
        self.current_state = 'ready'
        self.gpio.relay_on('warn_lights')

    def receive_safe(self, args):
        logging.info('Received safe signal')
        self.current_state = 'safe'
        self.gpio.all_relays_off()

    def receive_launch(self, args):
        logging.info('Received launch signal')
        if self.current_state == 'ready':
            self.current_state = 'ignition'
            self.gpio.relay_off('fill_solenoid')
            self.gpio.relay_off('dump_solenoid')
            self.gpio.relay_on('ignition')

    def receive_post_launch(self, args):
        logging.info('Received post launch signal')
        if self.current_state == 'ignition':
            self.gpio.relay_off('ignition')
            self.current_state = 'post-ignition'

    def send_fill_on(self):
        logging.info('Sending Fill Relay On signal')
        self.comms.send_message(command='fill-relay-on')

    def send_fill_off(self):
        logging.info('Sending Fill Relay Off signal')
        self.comms.send_message(command='fill-relay-off')

    def send_dump_on(self):
        logging.info('Sending Dump Relay On signal')
        self.comms.send_message(command='dump-relay-on')

    def send_dump_off(self):
        logging.info('Sending Dump Relay Off signal')
        self.comms.send_message(command='dump-relay-off')

    def receive_fill_relay_on(self, args):
        logging.info('Received fill relay on signal')

        self.gpio.relay_on('fill_solenoid')

    def receive_fill_relay_off(self, args):
        logging.info('Received fill relay off signal')

        self.gpio.relay_off('fill_solenoid')

    def receive_dump_relay_on(self, args):
        logging.info('Received dump relay on signal')

        self.gpio.relay_on('dump_solenoid')

    def receive_dump_relay_off(self, args):
        logging.info('Received dump relay off signal')

        self.gpio.relay_off('dump_solenoid')

    def receive_start_cameras(self, args):
        logging.info('Received start cameras signal')
        self.current_state = 'start-cameras'

    def receive_stop_cameras(self, args):
        logging.info('Received stop cameras signal')
        self.current_state = 'stop-cameras'
