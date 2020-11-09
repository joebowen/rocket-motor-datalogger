import time
import threading
import queue

from libraries.gpio import GPIO
from libraries.comms import Comms

# exit_flag = queue.Queue(1)


# class FillingThread(threading.Thread):
#     def __init__(self, launch_control, group=None, target=None, name=None, args=(), kwargs=None, verbose=None, daemon=True):
#         super(FillingThread, self).__init__()
#         self.target = target
#         self.name = name
#         self.launch_control = launch_control
#
#     def run(self):
#         while exit_flag.empty():
#             self.launch_control.comms.send_message(command='tank_pressure', args='test')
#             time.sleep(1)


class LaunchControl:
    def __init__(self, remoteid=None):
        self.relays = GPIO()
        self.relays.all_relays_off()
        self.current_state = 'safe'
        self.filling = None

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

        if not remoteid:
            remoteid = int(input("Enter the remote id shown on the launch controller: "))

        self.comms = Comms(message_types, remoteid)

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
        self.relays.relay_on('warn_lights')

    def receive_safe(self, args=None):
        print('Received safe signal')
        self.current_state = 'safe'
        self.relays.all_relays_off()

    def receive_launch(self, args=None):
        print('Received launch signal')
        if self.current_state == 'ready':
            self.current_state = 'ignition'
            self.relays.relay_off('fill_solenoid')
            self.relays.relay_off('dump_solenoid')
            self.relays.relay_on('ignition')

    def receive_post_launch(self, args=None):
        print('Received post launch signal')
        if self.current_state == 'ignition':
            self.relays.relay_off('ignition')
            self.current_state = 'post-ignition'
            self.comms.send_message(command='post-launch')

    def receive_fill_relay_on(self, args=None):
        print('Received fill relay on signal')

        self.relays.relay_on('fill_solenoid')

        # self.filling = FillingThread(
        #     name='filling',
        #     daemon=True,
        #     launch_control=self
        # )
        #
        # self.filling.start()

    def receive_fill_relay_off(self, args=None):
        print('Received fill relay off signal')

        self.relays.relay_off('fill_solenoid')

        # self.filling.terminate()

    def receive_dump_relay_on(self, args=None):
        print('Received dump relay on signal')

        self.relays.relay_on('dump_solenoid')

    def receive_dump_relay_off(self, args=None):
        print('Received dump relay off signal')

        self.relays.relay_off('dump_solenoid')

    def receive_start_cameras(self, args=None):
        print('Received start cameras signal')

    def receive_stop_cameras(self, args=None):
        print('Received stop cameras signal')
