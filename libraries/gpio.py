from gpiozero import LED


class GPIO:
    def __init__(self):
        self.relays = [
            LED(21),
            LED(20),
            LED(16),
            LED(12)
        ]

    def relay_off(self, index):
        self.relays[index].on()

    def relay_on(self, index):
        self.relays[index].off()
