#!/usr/bin/python3

import time
from adafruit_servokit import ServoKit

kit = ServoKit(channels=16)

kit.servo[14].angle = 0
kit.servo[15].angle = 90
time.sleep(5)
while True:
    kit.servo[15].angle = 90
    time.sleep(3)
    kit.servo[15].angle = 110
    time.sleep(3)
    kit.servo[15].angle = 70
    time.sleep(3)
    kit.servo[14].angle = 0
    time.sleep(1)
    kit.servo[14].angle = 180
    time.sleep(.5)
    kit.servo[14].angle = 180
    time.sleep(3)
    kit.servo[14].angle = 0
    time.sleep(3)