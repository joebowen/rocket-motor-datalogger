#!/usr/bin/python3

import time

from libraries.gimbal import Gimbal


def main():
    gimbal = Gimbal()

    time.sleep(5)
    while True:
        gimbal.yaw_to_angle(angle=110)
        time.sleep(3)
        gimbal.yaw_to_angle(angle=70)
        time.sleep(3)
        gimbal.yaw_to_angle(angle=90)
        time.sleep(3)

        gimbal.pitch_up(percentage=100)
        time.sleep(1)
        gimbal.yaw_to_angle(angle=50)
        time.sleep(4)
        gimbal.pitch_down(percentage=100)
        time.sleep(3)


if __name__ == "__main__":
    main()
