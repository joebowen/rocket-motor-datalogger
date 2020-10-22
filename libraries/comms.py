import meshtastic
import json
import time
import logging

from pubsub import pub


class Comms:
    def __init__(self, message_types):
        self.message_types = message_types

        pub.subscribe(self.on_receive, 'meshtastic.receive')
        pub.subscribe(self.on_connection, "meshtastic.connection.established")

        self.connected = False
        self.success_ids = []

        self.interface = meshtastic.SerialInterface(devPath='/dev/ttyUSB0')

        self.wait_till_connected()

        self.interface.radioConfig.preferences.is_low_power = False
        self.interface.radioConfig.preferences.is_router = True
        self.interface.radioConfig.preferences.min_wake_secs = 1
        self.interface.radioConfig.channel_settings.modem_config = 3
        self.interface.writeConfig()

        self.remoteid = int(input("Enter the remote id shown on the launch controller: "))

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.interface.close()

    def wait_till_connected(self):
        while not self.connected:
            time.sleep(1)

        logging.info('Meshtastic comms successfully connected')

    def on_connection(self, interface, topic=pub.AUTO_TOPIC):
        self.connected = True

    def wait_for_ack(self, message_id):
        while message_id not in self.success_ids:
            time.sleep(0.001)

    def on_receive(self, packet, interface):  # called when a packet arrives
        logging.debug(f'Received: {packet}')

        if 'decoded' in packet and 'successId' in packet['decoded']:
            self.success_ids.append(packet['decoded']['successId'])

        if 'decoded' in packet and 'data' in packet['decoded'] and 'text' in packet['decoded']['data']:
            self.parse_message(packet['decoded']['data']['text'])

    def parse_message(self, message):
        try:
            message_json = json.loads(message)
        except json.decoder.JSONDecodeError:
            return False

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
