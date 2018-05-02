#!/usr/bin/env python2

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Show battery information.
$ python scripts/battery.py
charge:     74%
left:       2:11:31
status:     discharging
plugged in: no
"""

from __future__ import print_function

import time

from pydbus import SystemBus
from gi.repository import GLib

bus = SystemBus()
response = bus.get('.UPower', 'devices/battery_BAT0')
# loop = GLib.MainLoop()
# print(response)
# response.Changed.connect(print)
# response.onStateChanged = print
while True:
    print(response.State)
    time.sleep(3)

# print(loop.is_running())
# loop.run()
# response.onChanged(response.State)

# while True:
#     time.sleep(1)
#     change = psutil.sensors_battery().power_plugged
#     if change != plugged_in:
#         plugged_in = change
#         print_status(plugged_in)

    # print("charge:     %s%%" % round(batt.percent, 2))
    # if batt.power_plugged:
    #     print("status:     %s" % (
    #         "charging" if batt.percent < 100 else "fully charged"))
    #     print("plugged in: yes")
    # else:
    #     print("left:       %s" % secs2hours(batt.secsleft))
    #     print("status:     %s" % "discharging")
    #     print("plugged in: no")
