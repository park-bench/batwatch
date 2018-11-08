#!/usr/bin/env python2

# Copyright 2015-2018 Joel Allen Luellwitz and Emily Klapp
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

"""
Handles battery change status monitoring and e-mail notifications for Batwatch.
"""

__author__ = 'Joel Luellwitz, Emily Klapp, and Brittney Scaccia'
__version__ = '0.8'

import logging
import time
import gpgmailmessage
from pydbus import SystemBus

UPOWER_BUS_NAME = 'org.freedesktop.UPower'
FULLY_CHARGED, CHARGING, DISCHARGING, NO_BATTERY = range(4)
CHARGE_STATUS_DICT = {
    0: 'Fully Charged',
    1: 'Charging',
    2: 'Discharging',
    3: 'No Battery'
}


class CompositeStatus(object):
    """
    Describes battery status information that Batwatch should monitor for changes.
    """

    def __init__(self, battery_count, charge_status):
        self.battery_count = battery_count
        self.charge_status = charge_status

    def __str__(self):
        return str(self.__dict__)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self.__eq__(other)


class Batwatch(object):
    """
    Monitors the status of system battery and notifies designated recipient(s) of changes
    by gpgmailer encrypted email.
    """

    __name__ = 'Batwatch'

    def __init__(self, config):
        """
        Start Batwatch with its configuration, logger, and reference to the UPower bus.

        config: Object containing Batwatch configuration details.
        """
        self.logger = logging.getLogger(self.__name__)
        self.system_bus = SystemBus()
        self.upower_bus = SystemBus().get(UPOWER_BUS_NAME)
        self.config = config

    def watch_the_bat(self):
        """
        Continuously monitor the status of all batteries attached to the device Batwatch is running
        on, and queue a status email to a configured recipient if anything changes.
        """
        self.logger.info('Watching the battery status.')

        # Arbitrarily initialize the current status and detect any deviations.
        current_status = CompositeStatus(1, FULLY_CHARGED)

        while True:
            self.logger.trace('Running the main loop.')
            new_status = self._get_composite_status()
            if current_status != new_status:
                self.logger.warn('A change in the battery status was detected. \nNEW STATUS: {} \nOLD STATUS: {}'
                                 .format(current_status, new_status))
                self._send_status_email(current_status, new_status)
                current_status = new_status
            else:
                self.logger.trace('No changes in battery status.')
            time.sleep(int(self.config['delay']))

    def _get_composite_status(self):
        """
        Get status information about batteries connected to the device Batwatch is running on,
         including the charge status, such that:
        * If any battery is discharging, charge status is Discharging.
          (Assume any status other than Charging or Fully Charged is equivalent to Discharging.)
        * Charge status is Fully Charged only if all batteries are Fully Charged.

        returns: CompositeStatus describing the count and overall charge status of the batteries.
        """

        device_names = self.upower_bus.EnumerateDevices()
        charge_status = FULLY_CHARGED

        batteries = []
        for device_name in device_names:
            device = self.system_bus.get(UPOWER_BUS_NAME, device_name)
            if device.PowerSupply is True and device.Type in (2, 3):  # Type 2 = Battery, Type 3 = UPS
                batteries.append(device)

        if not batteries:
            charge_status = NO_BATTERY

        for battery in batteries:
            if battery.State == 1:
                charge_status = CHARGING
            elif battery.State == 4 and charge_status != CHARGING:
                charge_status = FULLY_CHARGED
            else:
                charge_status = DISCHARGING
                break

        return CompositeStatus(len(batteries), charge_status)

    def _send_status_email(self, current_status, new_status):
        """
        Send an e-mail to the configured gpgmailer recipient when battery state changes.

        current_status: The previous battery CompositeStatus.
        new_status: The updated battery CompositeStatus.
        """

        email = gpgmailmessage.GpgMailMessage()
        # get subject from self.config or else leave blank for gpgmailer default.
        if (self.config['email_subject']):
            email.set_subject(self.config['email_subject'])

        body = self._build_email_body(current_status, new_status)
        email.set_body(body)

        email.queue_for_sending()

    def _build_email_body(self, current_status, new_status):
        """
        Return the text with battery status change information to be sent in the e-mail alert.

        current_status: The previous battery CompositeStatus at beginning of this loop.
        new_status: The updated battery CompositeStatus.
        returns: E-mail body text including previous and updated battery status details.
        """

        body_text = "Batwatch detected a change in your device's battery status:\n\n"

        count_diff = new_status.battery_count - current_status.battery_count
        if count_diff != 0:
            if count_diff < 0:
                body_text += 'A battery was ADDED.'
            elif count_diff > 0:
                body_text += 'A battery was REMOVED.'
            body_text += ' Count of batteries is now {}, was {}.\n\n' \
                .format(new_status.battery_count, current_status.battery_count)

        if new_status.charge_status != current_status.charge_status:
            body_text += 'The battery is now {}. Previously, it was {}.\n\n' \
                .format(CHARGE_STATUS_DICT[new_status.charge_status], CHARGE_STATUS_DICT[current_status.charge_status])

        return body_text
