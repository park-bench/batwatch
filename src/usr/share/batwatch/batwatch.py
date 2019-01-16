# Copyright 2018-2019 Joel Allen Luellwitz and Emily Frost
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

"""Handles battery change status monitoring and e-mail notifications for the battery
monitor.
"""

__all__ = ['BatWatch']
__author__ = 'Joel Luellwitz, Emily Frost, and Brittney Scaccia'
__version__ = '0.8'

import logging
import random
import time
from pydbus import SystemBus
import gpgmailmessage

UPOWER_BUS_NAME = 'org.freedesktop.UPower'
UPOWER_DEVICE_STATE_CHARGING = 1
UPOWER_DEVICE_STATE_FULLY_CHARGED = 4

# These constants are integers instead of strings because they need to be compared to
#   determine "favorable" changes.
NO_BATTERY, DISCHARGING, CHARGING, FULLY_CHARGED = range(4)

# This list is built with insert instead of statically so that we only need to maintain
#   the order in one place.
CHARGE_STATUS_LIST = []
CHARGE_STATUS_LIST.insert(NO_BATTERY, "No Battery")
CHARGE_STATUS_LIST.insert(DISCHARGING, "Discharging")
CHARGE_STATUS_LIST.insert(CHARGING, "Charging")
CHARGE_STATUS_LIST.insert(FULLY_CHARGED, "Fully Charged")


class CompositeStatus(object):
    """Stores state information for multiple batteries in an easily comparable object."""
    def __init__(self, battery_count, charge_status):
        """Constructor.

        battery_count: The number of batteries in the system.
        charge_status: The overall charging status of the system.
        """
        self.battery_count = battery_count
        self.charge_status = charge_status

    def __str__(self):
        english_representation = '0 batteries'

        if self.charge_status != NO_BATTERY:

            battery_word = 'batteries'
            if self.battery_count == 1:
                battery_word = 'battery'

            english_status = CHARGE_STATUS_LIST[self.battery_count]
            english_representation = '%s %s %s' % (
                self.battery_count, battery_word, english_status)

        return english_representation

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self == other


class BatWatch(object):
    """Monitors the status of the system battery and notifies designated recipient(s) of
    changes via gpgmailer encrypted e-mail.
    """

    def __init__(self, config):
        """Constructor.

        config: Dictionary containing BatWatch configuration details.
        """
        self.logger = logging.getLogger(__name__)
        self.system_bus = SystemBus()
        self.upower_bus = SystemBus().get(UPOWER_BUS_NAME)
        self.config = config

    def start_monitoring(self):
        """Continuously monitor the status of all batteries attached to the current system,
        and queue a status e-mail if any of those batteries' state changes.
        """
        self.logger.info("Monitoring the system's power state.")

        # Arbitrarily initialize the current status and detect any deviations.
        prior_status = self._get_composite_status()

        initialization_email = []
        if prior_status.charge_status == DISCHARGING:
            message = 'This system was discharging when Batwatch was initialized.'
            self.logger.warning(message)
            initialization_email.append(message)

        if prior_status.battery_count < self.config['minimum_batteries']:
            message = 'This system has fewer batteries than the configured minimum.'
            self.logger.warning(message)
            initialization_email.append(message)

        if initialization_email:
            self._send_email(initialization_email)

        while True:
            current_status = self._get_composite_status()
            if prior_status != current_status:
                if prior_status.battery_count > current_status.battery_count \
                    or prior_status.charge_status > current_status.charge_status:
                    self.logger.warning('Battery state changed from %s to %s.',
                                        prior_status, current_status)
                else:
                    self.logger.info('Battery state changed from %s to %s.', prior_status,
                                     current_status)

                email_text = "Batwatch detected a change in your device's battery status:" \
                    "\n\nThe previous status was %s. The new status is %s." % (
                        prior_status, current_status)
                self._send_email(email_text)
                prior_status = current_status
            else:
                self.logger.trace('No changes in battery status.')

            # Delay for a random amount of time to make BatWatch harder to fingerprint.
            delay = random.uniform(0, self.config['average_delay'])
            time.sleep(delay)

    def _get_composite_status(self):
        """Get status information about batteries connected to the device Batwatch is running
        on, including the charge status. For descriptions of the charge statuses, refer to
        the included README.

        returns: CompositeStatus describing the count and overall charge status of the
            batteries.
        """

        device_names = self.upower_bus.EnumerateDevices()

        batteries = []
        for device_name in device_names:
            device = self.system_bus.get(UPOWER_BUS_NAME, device_name)
            # A device is considered a power supply if it powers the whole system.
            #   https://upower.freedesktop.org/docs/Device.html#Device:PowerSupply

            if device.PowerSupply:
                batteries.append(device)

        charge_status = FULLY_CHARGED

        if not batteries:
            charge_status = NO_BATTERY

        else:
            for battery in batteries:
                if battery.State == UPOWER_DEVICE_STATE_CHARGING:
                    charge_status = CHARGING
                elif battery.State == UPOWER_DEVICE_STATE_FULLY_CHARGED:
                    pass
                else:
                    charge_status = DISCHARGING
                    break

        return CompositeStatus(len(batteries), charge_status)

    def _send_email(self, body_text):
        """Sends an e-mail.

        body_text: The text for the e-mail to be sent.
        """

        email = gpgmailmessage.GpgMailMessage()

        # Get subject from configuration or else leave blank for gpgmailer default.
        if self.config['email_subject']:
            email.set_subject(self.config['email_subject'])

        email.set_body(body_text)
        email.queue_for_sending()
