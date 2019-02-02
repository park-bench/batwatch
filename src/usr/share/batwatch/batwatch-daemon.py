#!/usr/bin/python2

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

"""Daemonize the Batwatch battery monitor."""

# TODO: Eventually consider running in a chroot or jail. (gpgmailer issue 17)

__author__ = 'Joel Luellwitz, Emily Frost, and Brittney Scaccia'
__version__ = '0.8'

import grp
import logging
import os
import pwd
import signal
import stat
import sys
import traceback
import ConfigParser
import daemon
from lockfile import pidlockfile
from pydbus import SystemBus
import batwatch
import confighelper

# Constants
PROGRAM_NAME = 'batwatch'
CONFIGURATION_PATHNAME = os.path.join('/etc', PROGRAM_NAME, '%s.conf' % PROGRAM_NAME)
SYSTEM_PID_DIR = '/run'
PROGRAM_PID_DIRS = PROGRAM_NAME
PID_FILE = '%s.pid' % PROGRAM_NAME
LOG_DIR = os.path.join('/var/log', PROGRAM_NAME)
LOG_FILE = '%s.log' % PROGRAM_NAME
PROCESS_USERNAME = PROGRAM_NAME
PROCESS_GROUP_NAME = PROGRAM_NAME
PROGRAM_UMASK = 0o027  # -rw-r----- and drwxr-x---


class InitializationException(Exception):
    """Indicates an expected fatal error occurred during program initialization.
    Initialization is implied to mean, before daemonization.
    """


def get_user_and_group_ids():
    """Get user and group information for dropping privileges.

    Returns the user and group IDs that the program should eventually run as.
    """
    try:
        program_user = pwd.getpwnam(PROCESS_USERNAME)
    except KeyError as key_error:
        # TODO: When switching to Python 3, convert to chained exception.
        #   (gpgmailer issue 15)
        print('User %s does not exist.' % PROCESS_USERNAME)
        raise key_error
    try:
        program_group = grp.getgrnam(PROCESS_GROUP_NAME)
    except KeyError as key_error:
        # TODO: When switching to Python 3, convert to chained exception.
        #   (gpgmailer issue 15)
        print('Group %s does not exist.' % PROCESS_GROUP_NAME)
        raise key_error

    return program_user.pw_uid, program_group.gr_gid


def read_configuration_and_create_logger(program_uid, program_gid):
    """Reads the configuration file and creates the application logger. This is done in the
    same function because part of the logger creation is dependent upon reading the
    configuration file.

    program_uid: The system user ID this program should drop to before daemonization.
    program_gid: The system group ID this program should drop to before daemonization.
    Returns the read system config, a confighelper instance, and a logger instance.
    """
    print('Reading %s...' % CONFIGURATION_PATHNAME)

    if not os.path.isfile(CONFIGURATION_PATHNAME):
        raise InitializationException(
            'Configuration file %s does not exist. Quitting.' % CONFIGURATION_PATHNAME)

    config_parser = ConfigParser.SafeConfigParser()
    config_parser.read(CONFIGURATION_PATHNAME)

    # Logging config goes first
    config = {}
    config_helper = confighelper.ConfigHelper()
    config['log_level'] = config_helper.verify_string_exists(config_parser, 'log_level')

    # Create logging directory.  drwxr-x--- batwatch batwatch
    log_mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP
    # TODO: Look into defaulting the logging to the console until the program gets more
    #   bootstrapped. (gpgmailer issue 18)
    print('Creating logging directory %s.' % LOG_DIR)
    if not os.path.isdir(LOG_DIR):
        # Will throw exception if file cannot be created.
        os.makedirs(LOG_DIR, log_mode)
    os.chown(LOG_DIR, program_uid, program_gid)
    os.chmod(LOG_DIR, log_mode)

    # Temporarily drop permission and create the handle to the logger.
    os.setegid(program_gid)
    os.seteuid(program_uid)
    config_helper.configure_logger(os.path.join(LOG_DIR, LOG_FILE), config['log_level'])

    logger = logging.getLogger(__name__)

    logger.info('Verifying non-logging configuration.')
    config['average_delay'] = config_helper.verify_number_within_range(
        config_parser, 'average_delay', lower_bound=0)

    config['email_subject'] = config_helper.get_string_if_exists(
        config_parser, 'email_subject')

    config['minimum_batteries'] = config_helper.verify_number_within_range(
        config_parser, 'minimum_batteries', lower_bound=0)

    return config, config_helper, logger


# TODO: Consider checking ACLs. (gpgmailer issue 22)
def verify_safe_file_permissions():
    """Crashes the application if unsafe file permissions exist on application configuration
    files.
    """
    # The configuration file should be owned by root.
    config_file_stat = os.stat(CONFIGURATION_PATHNAME)
    if config_file_stat.st_uid != 0:
        raise InitializationException(
            'File %s must be owned by root.' % CONFIGURATION_PATHNAME)
    if bool(config_file_stat.st_mode & (stat.S_IROTH | stat.S_IWOTH | stat.S_IXOTH)):
        raise InitializationException(
            "File %s cannot have 'other user' access permissions set."
            % CONFIGURATION_PATHNAME)


def create_directory(system_path, program_dirs, uid, gid, mode):
    """Creates directories if they do not exist and sets the specified ownership and
    permissions.

    system_path: The system path that the directories should be created under. These are
      assumed to already exist. The ownership and permissions on these directories are not
      modified.
    program_dirs: A string representing additional directories that should be created under
      the system path that should take on the following ownership and permissions.
    uid: The system user ID that should own the directory.
    gid: The system group ID that should own be associated with the directory.
    mode: The umask of the directory access permissions.
    """
    logger.info('Creating directory %s.' % os.path.join(system_path, program_dirs))

    path = system_path
    for directory in program_dirs.strip('/').split('/'):
        path = os.path.join(path, directory)
        if not os.path.isdir(path):
            # Will throw exception if file cannot be created.
            os.makedirs(path, mode)
        os.chown(path, uid, gid)
        os.chmod(path, mode)


def drop_permissions_forever(uid, gid):
    """Drops escalated permissions forever to the specified user and group.

    uid: The system user ID to drop to.
    gid: The system group ID to drop to.
    """
    logger.info('Dropping permissions for user %s.' % PROCESS_USERNAME)
    os.initgroups(PROCESS_USERNAME, gid)
    os.setgid(gid)
    os.setuid(uid)


def sig_term_handler(signal, stack_frame):
    """Signal handler for SIGTERM. Kills Tor and quits when SIGTERM is received.

    signal: Object representing the signal thrown.
    stack_frame: Represents the stack frame.
    """
    logger.info('SIGTERM received. Quitting.')
    sys.exit(0)


def setup_daemon_context(log_file_handle, program_uid, program_gid):
    """Creates the daemon context. Specifies daemon permissions, PID file information, and
    signal handler.

    log_file_handle: The file handle to the log file.
    program_uid: The system user ID the daemon should run as.
    program_gid: The system group ID the daemon should run as.
    Returns the daemon context.
    """
    daemon_context = daemon.DaemonContext(
        working_directory='/',
        pidfile=pidlockfile.PIDLockFile(
            os.path.join(SYSTEM_PID_DIR, PROGRAM_PID_DIRS, PID_FILE)),
        umask=PROGRAM_UMASK,
    )

    daemon_context.signal_map = {
        signal.SIGTERM: sig_term_handler,
    }

    daemon_context.files_preserve = [log_file_handle]

    # Set the UID and GID to 'batwatch' user and group.
    daemon_context.uid = program_uid
    daemon_context.gid = program_gid

    return daemon_context


os.umask(PROGRAM_UMASK)
program_uid, program_gid = get_user_and_group_ids()
config, config_helper, logger = read_configuration_and_create_logger(
    program_uid, program_gid)

try:

    verify_safe_file_permissions()

    # Re-establish root permissions to create required directories.
    os.seteuid(os.getuid())
    os.setegid(os.getgid())

    # Non-root users cannot create files in /run, so create a directory that can be written
    #   to. Full access to user only.  drwx------
    create_directory(
        SYSTEM_PID_DIR, PROGRAM_PID_DIRS, program_uid, program_gid,
        stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

    # Configuration has been read and directories setup. Now drop permissions forever.
    drop_permissions_forever(program_uid, program_gid)

    daemon_context = setup_daemon_context(
        config_helper.get_log_file_handle(), program_uid, program_gid)

    with daemon_context:
        logger.info('Initializing BatWatch.')
        batwatch = batwatch.BatWatch(config)
        batwatch.start_monitoring()

except Exception as exception:
    logger.critical('Fatal %s: %s\n%s' % (type(exception).__name__, str(exception),
                                          traceback.format_exc()))
    raise exception
