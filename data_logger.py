#! /usr/bin/python3
#
# Copyright (c) 2019 Warren J. Jasper <wjasper@ncsu.edu>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

import time
import fcntl
import os
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from usb_20x import *


def main():
    usb20x = usb_204()

    nchan = 1  # Number of channels to measure
    frequency = 100  # Hz
    runtime = 10  # seconds

    if frequency < 100:
        options = usb20x.IMMEDIATE_TRANSFER_MODE
    else:
        options = 0x0

    channels = 0
    for i in range(nchan):
        channels |= (0x1 << i)

    usb20x.AInScanStop()
    usb20x.AInScanClearFIFO()
    usb20x.AInScanStart(0, frequency, channels, options, 0, 0)
    flag = fcntl.fcntl(sys.stdin, fcntl.F_GETFL)
    fcntl.fcntl(sys.stdin, fcntl.F_SETFL, flag | os.O_NONBLOCK)

    start_time = time.time()

    data = pd.DataFrame(columns=['voltage'])

    while start_time > time.time() - runtime:
        raw_data = usb20x.AInScanRead(128)
        if raw_data:
            for raw_data_point in raw_data:
                voltage = usb20x.volts(raw_data_point)

                timestamp = time.time()
                tempDF = pd.DataFrame([voltage], columns=['voltage'], index=[timestamp - start_time])

                data = pd.concat([data, tempDF])

    fcntl.fcntl(sys.stdin, fcntl.F_SETFL, flag)
    usb20x.AInScanStop()

    timestamp = time.time()

    data.to_csv(f'output_data/test-{timestamp}.csv')

    voltage_plot = data['voltage'].plot()
    plt.xlabel('Seconds')
    plt.ylabel('Voltage')
    plt.title('Load Cell Test')
    fig = voltage_plot.get_figure()

    fig.savefig(f'output_data/test-{timestamp}.jpg')


if __name__ == "__main__":
    main()
