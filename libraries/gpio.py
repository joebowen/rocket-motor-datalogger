from gpiozero import LED


class GPIO:
    def __init__(self):
        self.relays = {
            'dump_solenoid': LED(21),
            'ignitor': LED(20),
            'fill_solenoid': LED(16),
            'warn_lights': LED(12)
        }

    def relay_off(self, index):
        self.relays[index].on()  # Cause "on" is "off" in this case...

    def relay_on(self, index):
        self.relays[index].off()  # Cause "on" is "off" in this case...

    def all_relays_off(self):
        for name in self.relays.keys():
            self.relay_off(name)
