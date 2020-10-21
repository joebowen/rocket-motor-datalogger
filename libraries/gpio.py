from gpiozero import LED


class GPIO:
    def __init__(self):
        self.relays = {
            'fill_solenoid': LED(20, active_high=False),
            'dump_solenoid': LED(21, active_high=False),
            'ignition': LED(16, active_high=False),
            'warn_lights': LED(12, active_high=False)
        }

    def relay_off(self, index):
        self.relays[index].on()  # Cause "on" is "off" in this case...

    def relay_on(self, index):
        self.relays[index].off()  # Cause "on" is "off" in this case...

    def all_relays_off(self):
        for name in self.relays.keys():
            self.relay_off(name)
