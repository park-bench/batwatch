#!/usr/bin/env python2

# Copyright 2015-2018 Joel Allen Luellwitz, Emily Klapp and Brittney
# Scaccia.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
import time
from pydbus import SystemBus

UPOWER_BUS_NAME = 'org.freedesktop.UPower'

class Batwatch:

    def __init__(self):
        self.logger = logging.getLogger('BATWATCH')

    def watch_the_bat(self):
        self.logger.info('Hi, I\'m watching the bat')

        # Get the initial composite status
        # in an endless loop:
        # 1) get a new composite status
        # 2) compare it to the old one
        # 3) if they're different, do stuff like send an email with the old and new values.
        # 4) save the new composite status as the old one

        bus = SystemBus()
        current_status = get_composite_status(bus)

        self.logger.debug(current_status)
        self.logger.debug(current_status.__dict__)

        while True:
            new_status = get_composite_status(bus)
            if current_status != new_status:
                # send mail
                current_status = new_status
            print(current_status.__dict__)
            print(new_status.__dict__)
            self.logger.debug(current_status.__dict__)
            self.logger.debug(new_status.__dict__)
            time.sleep(5)


def get_composite_status(bus):

    upower = bus.get(UPOWER_BUS_NAME)
    device_names = upower.EnumerateDevices()
    charge_status = ChargeStatus.Fully_Charged

    batteries = []
    for device in device_names:
        this_device = bus.get(UPOWER_BUS_NAME, device)
        if this_device.PowerSupply is True and this_device.Type in (2, 3):  # Type 2 = Battery, Type 3 = UPS
            batteries.append(this_device)

    if not batteries:
        charge_status = ChargeStatus.No_Battery

    # If any battery is discharging, overall status is Discharging.
    for battery in batteries:
        if battery.State not in (1, 4):  # State 1 = Charging, State 4 = Fully Charged
            charge_status = ChargeStatus.Discharging

    # If the overall status is not Discharging, then if any battery is charging, overall status is Charging.
    if charge_status is not ChargeStatus.Discharging:
        for battery in batteries:
            if battery.State == 1:
                charge_status = ChargeStatus.Charging

    return CompositeStatus(len(batteries), charge_status)


class ChargeStatus:
    Fully_Charged, Charging, Discharging, No_Battery = range(4)


class CompositeStatus:

    def __init__(self, num_batteries, charge_status):
        self.num_batteries = num_batteries
        self.charge_status = charge_status

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self.__eq__(other)


batwatch = Batwatch()
batwatch.watch_the_bat()
