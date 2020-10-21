from gpiozero import LED, Button


class GPIO:
    def __init__(self):
        self.relays = {
            'fill_solenoid': LED(20, active_high=False),
            'dump_solenoid': LED(21, active_high=False),
            'ignition': LED(16, active_high=False),
            'warn_lights': LED(12, active_high=False)
        }

        self.buttons = {
            'ready': Button(1),
            'launch': Button(2)
        }

    def relay_off(self, relay_name):
        self.relays[relay_name].off()

    def relay_on(self, relay_name):
        self.relays[relay_name].on()

    def all_relays_off(self):
        for name in self.relays.keys():
            self.relay_off(name)

    def is_button_on(self, button_name):
        return self.buttons[button_name].is_active()

    def wait_for_button(self, button_name):
        self.buttons[button_name].wait_for_active()

    def wait_for_button_release(self, button_name):
        self.buttons[button_name].wait_for_inactive()
