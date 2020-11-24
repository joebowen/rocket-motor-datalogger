from adafruit_servokit import ServoKit


class Gimbal:
    def __init__(self, pitch_servo=14, yaw_servo=15):
        self.kit = ServoKit(channels=16)

        self.pitch_servo = pitch_servo
        self.yaw_servo = yaw_servo

        self.go_home()

    def go_home(self):
        self.kit.servo[self.pitch_servo].angle = 0
        self.kit.servo[self.yaw_servo].angle = 90

    def pitch_up(self, percentage=100):
        value = int(percentage/100 * 90) + 90

        self.kit.servo[self.pitch_servo].angle = value

    def pitch_down(self, percentage=100):
        value = 90 - int(percentage / 100 * 90)

        self.kit.servo[self.pitch_servo].angle = value

    def yaw_to_angle(self, angle=90):
        self.kit.servo[self.yaw_servo].angle = angle
