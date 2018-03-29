#!/usr/bin/env python

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
import sys

import psutil
import time
import power


def secs2hours(secs):
    mm, ss = divmod(secs, 60)
    hh, mm = divmod(mm, 60)
    return "%d:%02d:%02d" % (hh, mm, ss)


def print_status(status):
    if status:
        print("The battery is plugged in.")
    else:
        print("The battery is NOT plugged in.")


if not hasattr(psutil, "sensors_battery"):
    sys.exit("platform not supported")
batt = psutil.sensors_battery()
if batt is None:
    sys.exit("no battery is installed")

plugged_in = batt.power_plugged
print_status(plugged_in)

while True:
    time.sleep(1)
    # change = psutil.sensors_battery().power_plugged
    # if change != plugged_in:
    #     plugged_in = change
    #     print_status(plugged_in)

    print(power.PowerManagement.is_ac_online('/sys/class/power_supply/AC'))
    print(power.PowerManagement.get_battery_state('/sys/class/power_supply/BAT0'))

    # print("charge:     %s%%" % round(batt.percent, 2))
    # if batt.power_plugged:
    #     print("status:     %s" % (
    #         "charging" if batt.percent < 100 else "fully charged"))
    #     print("plugged in: yes")
    # else:
    #     print("left:       %s" % secs2hours(batt.secsleft))
    #     print("status:     %s" % "discharging")
    #     print("plugged in: no")
