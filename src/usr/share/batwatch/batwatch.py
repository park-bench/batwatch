# Copyright 2018 Joel Allen Luellwitz and Emily Frost
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

__all__ = ['BatWatch', 'CompositeStatus']
__author__ = 'Joel Luellwitz, Emily Frost, and Brittney Scaccia'
__version__ = '0.8'

import logging
import time
from pydbus import SystemBus
import gpgmailmessage

UPOWER_BUS_NAME = 'org.freedesktop.UPower'
# TODO: Rework this to be less redundant.
FULLY_CHARGED, CHARGING, DISCHARGING, NO_BATTERY = range(4)
CHARGE_STATUS_DICT = {
    0: 'Fully Charged',
    1: 'Charging',
    2: 'Discharging',
    3: 'No Battery'
}


class CompositeStatus(object):
    """Stores state information for multiple batteries in an easily comparable object."""
    # TODO: Override __gt__ and __lt__ to determine "favorable" changes.

    def __init__(self, battery_count, charge_status):
        # TODO: Add inline comments explaining what these values are and how they work.
        self.battery_count = battery_count
        self.charge_status = charge_status

    def __str__(self):
        return str(self.__dict__)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self.__eq__(other)


class BatWatch(object):
    """Monitors the status of the system battery and notifies designated recipient(s) of
    changes via gpgmailer encrypted email.
    """

    def __init__(self, config):
        self.logger = logging.getLogger(__name__)
        self.system_bus = SystemBus()
        self.upower_bus = SystemBus().get(UPOWER_BUS_NAME)
        self.config = config

    def start_monitoring(self):
        """Continuously monitor the status of all batteries attached to the current system,
        and queue a status email if any of those batteries' state changes.
        """
        self.logger.info('Monitoring the system\'s power state.')

        # Arbitrarily initialize the current status and detect any deviations.
        prior_status = CompositeStatus(1, FULLY_CHARGED)

        # TODO: Don't arbitrarily initialize a status. Get the actual status and send an
        #   email if the state is discharging.

        # TODO: Check for favorable state changes and log them differently from
        #   unfavorable ones.

        while True:
            current_status = self._get_composite_status()
            if prior_status != current_status:
                self.logger.warning('Battery state changed from %s to %s.', prior_status,
                                    current_status)
                self._send_status_email(prior_status, current_status)
                prior_status = current_status
            else:
                self.logger.trace('No changes in battery status.')
            time.sleep(self.config['delay'])

    def _get_composite_status(self):
        # TODO: Move the composite status state description to the readme.
        """Get status information about batteries connected to the device Batwatch is running
            on, including the charge status, such that:
            * If any battery is discharging, charge status is Discharging.
              (Assume any status other than Charging or Fully Charged is equivalent to
               Discharging.)
            * Charge status is Fully Charged only if all batteries are Fully Charged.

        returns: CompositeStatus describing the count and overall charge status of the
            batteries.
        """

        device_names = self.upower_bus.EnumerateDevices()
        charge_status = FULLY_CHARGED

        batteries = []
        for device_name in device_names:
            device = self.system_bus.get(UPOWER_BUS_NAME, device_name)
            # We only care about device types 2 and 3, which are batteries and UPSes,
            #   respectively. The full list can be found here:
            #   https://upower.freedesktop.org/docs/Device.html#Device:Type

            # A device is considered a power supply if it powers the whole system.
            if device.PowerSupply is True and device.Type in (2, 3):
                batteries.append(device)

        if not batteries:
            charge_status = NO_BATTERY

        else:
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
        """Send an e-mail to the configured gpgmailer recipient when battery state changes.

        current_status: The previous battery CompositeStatus.
        new_status: The updated battery CompositeStatus.
        """

        email = gpgmailmessage.GpgMailMessage()
        # Get subject from configuration or else leave blank for gpgmailer default.
        if self.config['email_subject']:
            email.set_subject(self.config['email_subject'])

        body = self._build_email_body(current_status, new_status)
        email.set_body(body)

        email.queue_for_sending()

    def _build_email_body(self, current_status, new_status):
        """Creates an e-mail body with the battery status change information.

        current_status: The previous battery CompositeStatus.
        new_status: The updated battery CompositeStatus.

        Returns a string intended to be an e-mail body.
        """

        body_text = 'Batwatch detected a change in your device\'s battery status:\n\n'

        count_diff = new_status.battery_count - current_status.battery_count
        if count_diff != 0:
            if count_diff < 0:
                body_text += 'Batteries were added.'
            elif count_diff > 0:
                body_text += 'Batteries were removed.'
            body_text += ' Count of batteries is now %s, was %s.\n\n' % (
                new_status.battery_count, current_status.battery_count)

        if new_status.charge_status != current_status.charge_status:
            body_text += 'The battery is now %s. Previously, it was %s.\n\n' % (
                CHARGE_STATUS_DICT[new_status.charge_status],
                CHARGE_STATUS_DICT[current_status.charge_status])

        return body_text
