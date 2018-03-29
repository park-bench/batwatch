#!/usr/bin/env python2

# Copyright 2015-2018 Joel Allen Luellwitz, Emily Klapp and Brittney Scaccia.
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

import sys
import daemon
from daemon import pidlockfile
import signal
import logging
import batwatch
import traceback


# Signal handler for SIGTERM. Quits when SIGTERM is received.
#
# signal: Object representing the signal thrown.
# stack_frame: Represents the stack frame.
def sig_term_handler(signal, stack_frame):
    logger.info("SIGTERM received. Quitting.")
    sys.exit(0)


pid_file = '/run/batwatch.pid'
logger = logging.getLogger('Batwatch-Daemon')

daemon_context = daemon.DaemonContext(
    working_directory='/',
    pidfile=pidlockfile.PIDLockFile(pid_file),
    umask=0
)

daemon_context.signal_map = {
    signal.SIGTERM: sig_term_handler
}

# daemon_context.files_preserve = [log_file_handle]

logger.info('Daemonizing...')
with daemon_context:
    try:
        logger.debug('Initializing Batwatch.')
        the_watcher = batwatch.Batwatch()
        the_watcher.watch_the_bat()

    except Exception as e:
        logger.critical("Fatal %s: %s\n%s" % (type(e).__name__, e.message, traceback.format_exc()))
        sys.exit(1)
