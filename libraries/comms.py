import meshtastic
import json
import time
import logging

from pubsub import pub


class Comms:
    def __init__(self, message_types, remoteid=None):
        self.message_types = message_types
        self.remoteid = remoteid

        pub.subscribe(self.on_receive, 'meshtastic.receive')
        pub.subscribe(self.on_connection, "meshtastic.connection.established")

        self.connected = False

        self.interface = meshtastic.SerialInterface()

        self.wait_till_connected()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.interface.close()

    def wait_till_connected(self):
        while not self.connected:
            time.sleep(1)

        logging.info('Meshtastic comms successfully connected')

    def on_connection(self, interface, topic=pub.AUTO_TOPIC):
        self.connected = True

    def on_receive(self, packet, interface):  # called when a packet arrives
        logging.debug(f'Received: {packet}')

        if 'decoded' in packet and 'data' in packet['decoded'] and 'text' in packet['decoded']['data']:
            self.parse_message(packet['decoded']['data']['text'])

    def parse_message(self, message):
        message_json = json.loads(message)

        logging.info(f'message_json: {message_json}')

        if message_json['remoteid'] == self.remoteid:
            message_command = message_json['command']

            logging.debug(f'message_command: {message_command}')

            if message_command in self.message_types:
                message_args = None
                if 'args' in message_json:
                    message_args = message_json['args']

                logging.debug(f'Executing: {self.message_types[message_command]}')

                self.message_types[message_command](message_args)
