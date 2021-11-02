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

        self.set_config()

    def set_config(self):
        # logging.info(self.interface.localNode.radioConfig)
        # logging.info(dir(self.interface.localNode.channels))
        self.interface.localNode.radioConfig.preferences.is_low_power = False
        self.interface.localNode.radioConfig.preferences.is_router = False

        self.interface.localNode.radioConfig.channels[0].settings.modem_config = 2

        self.interface.localNode.radioConfig.preferences.position_broadcast_secs = 300
        self.interface.localNode.radioConfig.preferences.gps_attempt_time = 300
        self.interface.localNode.radioConfig.preferences.gps_update_interval = 300
        self.interface.localNode.radioConfig.preferences.send_owner_interval = 10
        self.interface.localNode.radioConfig.preferences.wait_bluetooth_secs = 60
        self.interface.localNode.radioConfig.preferences.screen_on_secs = 900
        self.interface.localNode.radioConfig.preferences.phone_timeout_secs = 900
        self.interface.localNode.radioConfig.preferences.phone_sds_timeout_sec = 7200
        self.interface.localNode.radioConfig.preferences.mesh_sds_timeout_secs = 7200
        self.interface.localNode.radioConfig.preferences.sds_secs = 31536000
        self.interface.localNode.radioConfig.preferences.ls_secs = 3600

        # self.interface.localNode.radioConfig.channel_settings.tx_power = 100

        self.interface.localNode.writeConfig()

        logging.info('Wrote out config')

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.interface.close()

    def wait_till_connected(self):
        while not self.connected:
            time.sleep(1)

        logging.info('Meshtastic comms successfully connected')

    def on_connection(self, interface, topic=pub.AUTO_TOPIC):
        self.connected = True

    def wait_for_ack(self, message_ids, timeout=1):
        message = [
            '.',
            '..',
            '...'
        ]

        start_time = time.time()

        count = 0
        while all(message_id not in self.success_ids for message_id in message_ids):
            time.sleep(1)

            count += 1
            if count % 2000:
                if self.display:
                    self.display.add_message(message[count % 3])

            if time.time() > start_time + timeout:
                return False

        return True

    def on_receive(self, packet, interface):  # called when a packet arrives
        logging.debug(f'Received: {packet}')

        if 'decoded' in packet and 'text' in packet['decoded']:
            logging.info(f'packet: {packet}')
            self.parse_message(packet['decoded']['text'], packet['id'])

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
            wantResponse=False
        ).id

        return message_id

    def parse_message(self, message, message_id):
        try:
            message_json = json.loads(message)
        except json.decoder.JSONDecodeError:
            return False

        logging.info(f'message_json: {message_json}')

        if message_json['remoteid'] == self.remoteid:
            message_command = message_json['command']

            logging.debug(f'message_command: {message_command}')

            if message_command == 'ack':
                logging.info(f'Received Message Ack: {message_json["args"]["message_id"]}')
                self.success_ids.append(message_json['args']['message_id'])

            elif message_command in self.message_types:
                message_args = {
                    'message_id': message_id,
                    'message_command': message_command
                }

                if 'args' in message_json:
                    message_args['args'] = message_json['args']

                logging.debug(f'Executing: {self.message_types[message_command]}')

                self.message_types[message_command](message_args)
