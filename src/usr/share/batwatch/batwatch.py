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

class Batwatch:

    logger = logging.getLogger('BATWATCH')

    def __init__(self):
        logger = None

    def watch_the_bat(self):
        logger = None
        bus = SystemBus()
        proxy = bus.get('.UPower', 'devices/battery_BAT0')

        while True:
            print(proxy.State)
            time.sleep(3)