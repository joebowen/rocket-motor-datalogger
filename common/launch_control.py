import time

from common.gpio import GPIO
from common.comms import Comms


class LaunchControl:
    def __init__(self, remoteid, display=None):
        self.gpio = GPIO()
        self.gpio.all_relays_off()
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

        self.display = display
        self.comms = Comms(message_types, remoteid=remoteid, display=display)

    def wait_for_start_cameras(self):
        print('Waiting for the start-cameras command to be sent.')
        while self.current_state != 'start-cameras':
            time.sleep(0.1)

        return True

    def wait_for_stop_cameras(self):
        print('Waiting for the stop-cameras command to be sent.')
        while self.current_state != 'stop-cameras':
            time.sleep(0.1)

        return True

    def wait_for_ready(self):
        print('Waiting for the ready command to be sent.')
        while self.current_state != 'ready':
            time.sleep(0.01)

    def wait_for_safe(self):
        print('Waiting for the safe command to be sent.')
        while self.current_state != 'safe':
            time.sleep(0.01)
    
    def remote_wait_for_ready(self):
        print(f'Waiting for the ready switch to be turned on.')
        self.gpio.wait_for_button('ready')

        self.send_start_cameras()
        is_ready = self.send_ready()

        if is_ready:
            print('Ready...')
            self.display.add_message('READY')
            self.current_state = 'ready'

        return is_ready

    def send_start_cameras(self):
        self.comms.send_message(command='start-cameras')

        return True

    def send_ready(self):
        message_ids = [self.comms.send_message(command='ready')]

        while not self.comms.wait_for_ack(message_ids, timeout=1):
            message_ids.append(self.comms.send_message(command='ready'))

            if not self.gpio.is_button_on('ready'):
                self.send_safe()
                return False

        return True

    def remote_wait_for_safe(self):
        print(f'Waiting for the ready switch to be turned off.')
        self.gpio.wait_for_button_release('ready')

        self.send_safe()

    def send_safe(self):
        message_id = self.comms.send_message(command='safe')
        self.comms.send_message(command='stop-cameras')

        # while not self.comms.wait_for_ack(message_id, timeout=10):
        #     message_id = self.comms.send_message(command='safe')

        print('Safe...')
        self.display.add_message('SAFE')
        self.current_state = 'safe'

    def wait_for_launch(self, timeout=45):
        print(f'Waiting for the launch switch to be pushed.')
        while not self.gpio.is_button_on('launch'):
            if not self.gpio.is_button_on('ready'):
                self.send_safe()
                return False

            if not self.filling and self.gpio.is_button_on('fill'):
                self.filling = True
                self.send_fill_on()

            if self.filling and not self.gpio.is_button_on('fill'):
                self.filling = False
                self.send_fill_off()

            if not self.dumping and self.gpio.is_button_on('dump'):
                self.dumping = True
                self.send_dump_on()

            if self.dumping and not self.gpio.is_button_on('dump'):
                self.dumping = False
                self.send_dump_off()

        is_launch = self.send_launch()

        if is_launch:
            print('Launch...')
            self.display.add_message('LAUNCH')
            self.current_state = 'launch'

            while self.gpio.is_button_on('launch'):
                if not self.gpio.is_button_on('ready'):
                    self.send_safe()
                    return False

            self.send_post_launch()

        return is_launch

    def send_launch(self):
        message_id = self.comms.send_message(command='launch')

        while not self.comms.wait_for_ack(message_id):
            if not self.gpio.is_button_on('ready'):
                self.send_safe()
                return False

        return True

    def send_post_launch(self):
        message_id = self.comms.send_message(command='post-launch')

        while not self.comms.wait_for_ack(message_id):
            if not self.gpio.is_button_on('ready'):
                self.send_safe()
                return False

        return True

    def receive_ready(self, args=None):
        print('Received ready signal')
        self.current_state = 'ready'
        self.gpio.relay_on('warn_lights')

    def receive_safe(self, args=None):
        print('Received safe signal')
        self.current_state = 'safe'
        self.gpio.all_relays_off()

    def receive_launch(self, args=None):
        print('Received launch signal')
        if self.current_state == 'ready':
            self.current_state = 'ignition'
            self.gpio.relay_off('fill_solenoid')
            self.gpio.relay_off('dump_solenoid')
            self.gpio.relay_on('ignition')

    def receive_post_launch(self, args=None):
        print('Received post launch signal')
        if self.current_state == 'ignition':
            self.gpio.relay_off('ignition')
            self.current_state = 'post-ignition'

    def send_fill_on(self):
        self.comms.send_message(command='fill-relay-on')

    def send_fill_off(self):
        self.comms.send_message(command='fill-relay-off')

    def send_dump_on(self):
        self.comms.send_message(command='dump-relay-on')

    def send_dump_off(self):
        self.comms.send_message(command='dump-relay-off')

    def receive_fill_relay_on(self, args=None):
        print('Received fill relay on signal')

        self.gpio.relay_on('fill_solenoid')

    def receive_fill_relay_off(self, args=None):
        print('Received fill relay off signal')

        self.gpio.relay_off('fill_solenoid')

    def receive_dump_relay_on(self, args=None):
        print('Received dump relay on signal')

        self.gpio.relay_on('dump_solenoid')

    def receive_dump_relay_off(self, args=None):
        print('Received dump relay off signal')

        self.gpio.relay_off('dump_solenoid')

    def receive_start_cameras(self, args=None):
        print('Received start cameras signal')
        self.current_state = 'start-cameras'

    def receive_stop_cameras(self, args=None):
        print('Received stop cameras signal')
        self.current_state = 'stop-cameras'