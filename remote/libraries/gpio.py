from gpiozero import LED, Button


class GPIO:
    def __init__(self):
        self.relays = {
            'dump_solenoid': LED(21),
            'ignitor': LED(20),
            'fill_solenoid': LED(16),
            'warn_lights': LED(12)
        }

        self.buttons = {
            'ready': Button(1),
            'launch': Button(2)
        }

    def relay_off(self, relay_name):
        self.relays[relay_name].on()  # Cause "on" is "off" in this case...

    def relay_on(self, relay_name):
        self.relays[relay_name].off()  # Cause "on" is "off" in this case...

    def all_relays_off(self):
        for name in self.relays.keys():
            self.relay_off(name)

    def is_button_on(self, button_name):
        return self.buttons[button_name].is_active()

    def wait_for_button(self, button_name):
        self.buttons[button_name].wait_for_active()
