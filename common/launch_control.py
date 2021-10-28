from common.gpio import GPIO
from common.comms import Comms


class LaunchControl:
    def __init__(self, remoteid, display=None, relays=None, buttons=None):
        self.gpio = GPIO(relays=relays, buttons=buttons)
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

    def send_start_cameras(self):
        message_ids = [self.comms.send_message(command='start-cameras')]

        # while not self.comms.wait_for_ack(message_ids, timeout=1):
        #     message_ids.append(self.comms.send_message(command='start-cameras'))

        return True

    def send_ready(self):
        message_ids = [self.comms.send_message(command='ready')]

        while not self.comms.wait_for_ack(message_ids, timeout=1):
            message_ids.append(self.comms.send_message(command='ready'))

            if not self.gpio.is_button_on('ready'):
                self.send_safe()
                return False

        return True

    def send_safe(self):
        message_ids = [self.comms.send_message(command='safe')]
        self.comms.send_message(command='stop-cameras')

        while not self.comms.wait_for_ack(message_ids, timeout=1):
            message_ids.append(self.comms.send_message(command='safe'))

        print('Safe...')
        self.display.add_message('SAFE')
        self.current_state = 'safe'

    def send_launch(self):
        message_id = self.comms.send_message(command='launch')

        while not self.comms.wait_for_ack(message_id, timeout=1):
            if not self.gpio.is_button_on('ready'):
                self.send_safe()
                return False

        return True

    def receive_ready(self, args):
        print('Received ready signal')
        self.current_state = 'ready'
        self.gpio.relay_on('warn_lights')
        
        self.send_ack(args['message_id'], 'ready')

    def receive_safe(self, args):
        print('Received safe signal')
        self.current_state = 'safe'
        self.gpio.all_relays_off()
        
        self.send_ack(args['message_id'], 'safe')

    def receive_launch(self, args):
        print('Received launch signal')
        if self.current_state == 'ready':
            self.current_state = 'ignition'
            self.gpio.relay_off('fill_solenoid')
            self.gpio.relay_off('dump_solenoid')
            self.gpio.relay_on('ignition')
        
        self.send_ack(args['message_id'], 'launch')

    def receive_post_launch(self, args):
        print('Received post launch signal')
        if self.current_state == 'ignition':
            self.gpio.relay_off('ignition')
            self.current_state = 'post-ignition'
        
        self.send_ack(args['message_id'], 'post-ignition')

    def send_fill_on(self):
        self.comms.send_message(command='fill-relay-on')

    def send_fill_off(self):
        self.comms.send_message(command='fill-relay-off')

    def send_dump_on(self):
        self.comms.send_message(command='dump-relay-on')

    def send_dump_off(self):
        self.comms.send_message(command='dump-relay-off')

    def receive_fill_relay_on(self, args):
        print('Received fill relay on signal')

        self.gpio.relay_on('fill_solenoid')
        
        self.send_ack(args['message_id'], 'fill-relay-on')

    def receive_fill_relay_off(self, args):
        print('Received fill relay off signal')

        self.gpio.relay_off('fill_solenoid')

        self.send_ack(args['message_id'], 'fill-relay-off')

    def receive_dump_relay_on(self, args):
        print('Received dump relay on signal')

        self.gpio.relay_on('dump_solenoid')

        self.send_ack(args['message_id'], 'dump-relay-on')

    def receive_dump_relay_off(self, args):
        print('Received dump relay off signal')

        self.gpio.relay_off('dump_solenoid')

        self.send_ack(args['message_id'], 'dump-relay-off')

    def receive_start_cameras(self, args):
        print('Received start cameras signal')
        self.current_state = 'start-cameras'

        self.send_ack(args['message_id'], 'start-cameras')

    def receive_stop_cameras(self, args):
        print('Received stop cameras signal')
        self.current_state = 'stop-cameras'

        self.send_ack(args['message_id'], 'stop-cameras')

    def send_ack(self, message_id, command):
        print(f'Send Ack for {command} : {message_id}')

        args = {
            'message_id': message_id,
            'command': command
        }

        self.comms.send_message(command='ack', args=args)
