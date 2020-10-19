import meshtastic
import json
import time

from pubsub import pub


class Comms:
    def __init__(self, message_types, remoteid=None):
        self.message_types = message_types
        self.remoteid = remoteid

        pub.subscribe(self.on_receive, 'meshtastic.receive')
        pub.subscribe(self.on_connection, "meshtastic.connection.established")

        self.connected = False

        self.interface = meshtastic.SerialInterface()

    def wait_till_connected(self):
        while not self.connected:
            time.sleep(1)

        print('Meshtastic comms successfully connected')

    def on_connection(self):
        self.connected = True

    def on_receive(self, packet, interface):  # called when a packet arrives
        print(f'Received: {packet}')

        if 'data' in packet and 'text' in packet['data']:
            self.parse_message(packet['data']['text'])

    def parse_message(self, message):
        message_json = json.loads(message)

        print(f'message_json: {message_json}')

        if message_json['remoteid'] == self.remoteid:
            message_command = message_json['command']

            print(f'message_command: {message_command}')

            if message_command in self.message_types:
                message_args = None
                if 'args' in message_json:
                    message_args = message_json['args']

                print(f'Executing: {self.message_types[message_command]}')

                self.message_types[message_command](message_args)
