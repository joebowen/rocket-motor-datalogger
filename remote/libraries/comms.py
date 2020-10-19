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

    def on_connection(self, interface, topic=pub.AUTO_TOPIC):
        self.connected = True

    def on_receive(self, packet, interface):  # called when a packet arrives
        print(f'Received: {packet}')

        if 'data' in packet and 'text' in packet['data']:
            self.parse_message(packet['data']['text'])

    def send_message(self, command, args=None):
        message = {
            'remoteid': self.remoteid,
            'command': command
        }

        if args:
            message['args'] = args

        self.interface.sendText(
            text=json.dumps(message),
            wantAck=True
        )

    def parse_message(self, message):
        message_json = json.loads(message)

        if message_json['remoteid'] == self.remoteid:
            message_command = message_json['command']

            if message_command in self.message_types:
                message_args = None
                if 'args' in message_json:
                    message_args = message_json['args']

                self.message_types[message_command](message_args)
