import meshtastic
from pubsub import pub


class Comms:
    def __init__(self):
        pub.subscribe(self.onReceive, "meshtastic.receive")
        pub.subscribe(self.onConnection, "meshtastic.connection.established")

        self.interface = meshtastic.SerialInterface()

    def onReceive(self, packet, interface):  # called when a packet arrives
        print(f"Received: {packet}")

    def onConnection(self, interface, topic=pub.AUTO_TOPIC):  # called when we (re)connect to the radio
        # defaults to broadcast, specify a destination ID if you wish
        self.interface.sendText("hello mesh")
