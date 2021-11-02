#!/usr/bin/python3

import meshtastic
import time

from pubsub import pub


class Comms:
    def __init__(self):
        pub.subscribe(self.on_connection, "meshtastic.connection.established")

        self.connected = False

        self.interface = meshtastic.SerialInterface(devPath='/dev/ttyUSB0')

        self.wait_till_connected()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.interface.close()

    def wait_till_connected(self):
        while not self.connected:
            time.sleep(0.01)

        logging.info('Meshtastic comms successfully connected')

    def on_connection(self, interface, topic=pub.AUTO_TOPIC):
        self.connected = True

    def set_config(self):
        self.interface.localNode.radioConfig.preferences.is_low_power = False
        self.interface.localNode.radioConfig.preferences.is_router = False

        # self.interface.localNode.radioConfig.channel_settings.modem_config = 3

        self.interface.localNode.radioConfig.preferences.position_broadcast_secs = 1
        self.interface.localNode.radioConfig.preferences.gps_attempt_time = 300
        self.interface.localNode.radioConfig.preferences.gps_update_interval = 5
        self.interface.localNode.radioConfig.preferences.send_owner_interval = 1
        self.interface.localNode.radioConfig.preferences.wait_bluetooth_secs = 30
        self.interface.localNode.radioConfig.preferences.screen_on_secs = 300
        self.interface.localNode.radioConfig.preferences.phone_timeout_secs = 30
        self.interface.localNode.radioConfig.preferences.phone_sds_timeout_sec = 7200
        self.interface.localNode.radioConfig.preferences.mesh_sds_timeout_secs = 7200
        self.interface.localNode.radioConfig.preferences.sds_secs = 31536000
        self.interface.localNode.radioConfig.preferences.ls_secs = 3600

        # self.interface.localNode.radioConfig.channel_settings.tx_power = 100

        self.interface.localNode.writeConfig()

        logging.info('Wrote out config')


def main():
    radio = Comms()
    radio.set_config()


if __name__ == '__main__':
    main()
