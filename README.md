# batwatch

_batwatch_ monitors a system's batteries and UPS units for state changes and sends
notifications via _gpgmailer_.

Also depends on our _confighelper_ library which can be found at
https://github.com/park-bench/confighelper

batwatch is licensed under the GNU GPLv3. All source code commits prior to the public
release are also retroactively licensed under the GNU GPLv3.

Bug fixes are welcome!

## System Power States

_batwatch_ looks at the number of batteries installed on a system and each of those
batteries' charge levels to determine the system's state. If any single battery is
discharging, the entire system is considered to be discharging.

## Prerequisites

This software is currently only supported on Ubuntu 18.04 and may not be ready for use in a production environment.

The only current method of installation for our software is building and installing your own debian package. We make the following assumptions:

*    You are already familiar with using a Linux terminal.
*    You are already somewhat familiar with using debuild.
*    `build-essential` is installed.
*    `devscripts` is installed.

## Parkbench Dependencies

_batwatch_ depends on one other piece of the Parkbench project, which must be installed first:

* [_confighelper_](https://github.com/park-bench/confighelper)

## Steps to Build and Install

1. Clone the latest release tag. (Do not clone the master branch. `master` may not be stable.)
2. Use `debuild` from the project root directory to build the package.
3. Use `dpkg -i` to install the package.
4. Use `apt-get -f install` to resolve any missing dependencies.

## Post-Install configuration

There is a configuration file at `/etc/batwatch/batwatch.conf`, but the daemon will work if
this file is not changed.

## Updates

Updates may change configuration file options, so if you have a configuration
file already, check that it has all of the required options in the current
example file.
