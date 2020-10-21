from gpiozero import LED, Button


class GPIO:
    def __init__(self):
        self.relays = {
            'ready_led': LED(5),
            'launch_led': LED(6)
        }

        self.buttons = {
            'ready': Button(2),
            'launch': Button(3)
        }

    def relay_off(self, relay_name):
        self.relays[relay_name].off()

    def relay_on(self, relay_name):
        self.relays[relay_name].on()

    def all_relays_off(self):
        for name in self.relays.keys():
            self.relay_off(name)

    def is_button_on(self, button_name):
        return self.buttons[button_name].is_active

    def wait_for_button(self, button_name):
        self.buttons[button_name].wait_for_active()

    def wait_for_button_release(self, button_name):
        self.buttons[button_name].wait_for_inactive()
