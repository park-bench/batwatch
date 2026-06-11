#!/usr/bin/python3

# Copyright 2018-2026 Joel Allen Luellwitz and Emily Frost
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

"""Daemonize the Batwatch battery monitor."""

# TODO: Eventually consider running in a chroot or jail. (gpgmailer issue 17)

__author__ = 'Joel Luellwitz, Emily Frost, and Brittney Scaccia'
__version__ = '0.9'

import logging
import os
import pwd
import sdnotify
import stat
import traceback
import configparser
import batwatch
from parkbenchcommon import confighelper

# Constants
PROGRAM_NAME = 'batwatch'
CONFIGURATION_PATHNAME = f'/etc/{PROGRAM_NAME}/{PROGRAM_NAME}.conf'
PROCESS_USERNAME = PROGRAM_NAME


class InitializationException(Exception):
    """Indicates an expected fatal error occurred during program initialization.
    Initialization is implied to mean, before daemonization.
    """


def read_configuration():
    """Reads and validates the configuration file. Supported configuration options are
    returned as a dictonary.

    Return (dict): The read system configuration.
    """
    logger = logging.getLogger(__name__)

    logger.info(f'Reading {CONFIGURATION_PATHNAME}...')
    config_parser = configparser.ConfigParser()
    config_parser.read(CONFIGURATION_PATHNAME)

    logger.info('Validating batwatch configuration.')

    config = {}
    config_helper = confighelper.ConfigHelper()
    config['log_level'] = config_helper.verify_log_level(config_parser)

    config['main_loop_max_delay'] = config_helper.verify_number_within_range(
        config_parser, 'main_loop_max_delay', lower_bound=0, upper_bound=301)
    config['email_subject'] = config_helper.get_string_if_exists(
        config_parser, 'email_subject')

    config['minimum_batteries'] = config_helper.verify_integer_within_range(
        config_parser, 'minimum_batteries', lower_bound=0)

    return config


def get_user_id():
    """Return (int): The user ID that the program runs as."""

    try:
        program_user = pwd.getpwnam(PROCESS_USERNAME)
    except KeyError as key_error:
        message = f'User {PROCESS_USERNAME} does not exist.'
        raise InitializationException(message) from key_error

    return program_user.pw_uid


# TODO: Consider checking ACLs. (gpgmailer issue 22)
def verify_safe_file_permissions():
    """Crashes the application if unsafe file permissions exist on application configuration
    files.
    """
    if not os.path.isfile(CONFIGURATION_PATHNAME):
        raise InitializationException(
            f'Configuration file {CONFIGURATION_PATHNAME} does not exist. Quitting.')

    # The configuration file should be owned by batwatch.
    config_file_stat = os.stat(CONFIGURATION_PATHNAME)
    if config_file_stat.st_uid != get_user_id():
        raise InitializationException(
            f'File {CONFIGURATION_PATHNAME} must be owned by {PROCESS_USERNAME}.')
    if bool(config_file_stat.st_mode & stat.S_IWGRP):
        raise InitializationException(
            f'File {CONFIGURATION_PATHNAME} cannot be writable via the group access '
            'permission.')
    if bool(config_file_stat.st_mode & (stat.S_IROTH | stat.S_IWOTH | stat.S_IXOTH)):
        raise InitializationException(
            "File {CONFIGURATION_PATHNAME} cannot have 'other user' access permissions set.")


def start():
    """The parent function for the entire program. It loads and verifies configuration,
    initializes the main program class, and calls its entry function.
    """
    confighelper.ConfigHelper.configure_logger()
    logger = logging.getLogger(__name__)

    try:
        verify_safe_file_permissions()
        config = read_configuration()
        logger.setLevel(config['log_level'])

        logger.debug('Initializing BatWatch.')
        batwatcher = batwatch.BatWatch(config)
        sdnotify.SystemdNotifier().notify('READY=1')
        batwatcher.start_monitoring()

    except Exception as exception:
        logger.critical(
            f'Fatal {type(exception).__name__}: {str(exception)}\n{traceback.format_exc()}')
        raise exception


if __name__ == '__main__':
    start()
