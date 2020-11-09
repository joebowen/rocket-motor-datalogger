import meshtastic
import json
import time
import logging

from pubsub import pub


class Comms:
    def __init__(self, message_types, remoteid=None, display=None):
        self.message_types = message_types
        self.remoteid = remoteid
        self.display = display

        pub.subscribe(self.on_receive, 'meshtastic.receive')
        pub.subscribe(self.on_connection, "meshtastic.connection.established")

        self.connected = False
        self.success_ids = []

        self.interface = meshtastic.SerialInterface()

        self.wait_till_connected()

        self.interface.setOwner(long_name='Remote', short_name='R')

    def set_config(self):

        self.interface.radioConfig.preferences.is_low_power = False
        self.interface.radioConfig.preferences.is_router = True

        self.interface.radioConfig.channel_settings.modem_config = 1

        self.interface.radioConfig.preferences.position_broadcast_secs = 900
        self.interface.radioConfig.preferences.send_owner_interval = 4
        self.interface.radioConfig.preferences.wait_bluetooth_secs = 120
        self.interface.radioConfig.preferences.screen_on_secs = 300
        self.interface.radioConfig.preferences.phone_timeout_secs = 900
        self.interface.radioConfig.preferences.phone_sds_timeout_sec = 7200
        self.interface.radioConfig.preferences.mesh_sds_timeout_secs = 7200
        self.interface.radioConfig.preferences.sds_secs = 31536000
        self.interface.radioConfig.preferences.ls_secs = 3600

        self.interface.writeConfig()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.interface.close()

    def wait_till_connected(self):
        while not self.connected:
            time.sleep(0.01)

        logging.info('Meshtastic comms successfully connected')

    def on_connection(self, interface, topic=pub.AUTO_TOPIC):
        self.connected = True

    def wait_for_ack(self, message_id, timeout=1):
        message = [
            '.',
            '..',
            '...'
        ]

        start_time = time.time()

        count = 0
        while message_id not in self.success_ids:
            time.sleep(0.01)

            count += 1
            if count % 2000:
                if self.display:
                    self.display.add_message(message[count % 3])

            if time.time() > start_time + timeout:
                return False

        return True

    def on_receive(self, packet, interface):  # called when a packet arrives
        logging.debug(f'Received: {packet}')

        if 'decoded' in packet and 'successId' in packet['decoded']:
            self.success_ids.append(packet['decoded']['successId'])

        if 'decoded' in packet and 'data' in packet['decoded'] and 'text' in packet['decoded']['data']:
            self.parse_message(packet['decoded']['data']['text'])

    def send_message(self, command, args=None):
        message = {
            'remoteid': self.remoteid,
            'command': command
        }

        if args:
            message['args'] = args

        message_id = self.interface.sendText(
            text=json.dumps(message),
            wantAck=True,
            wantResponse=True
        ).id

        return message_id

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
