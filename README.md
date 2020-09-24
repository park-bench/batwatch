# batwatch

_batwatch_ monitors a system's batteries and UPS units for state changes and sends
notifications via _gpgmailer_.

batwatch is licensed under the GNU GPLv3.

Bug fixes are welcome!

## System Power States

_batwatch_ looks at the number of batteries installed on a system and each of those
batteries' charge states to determine the system's overall state to be one of the following.

* Fully Charged: All batteries are fully charged and not discharging.
* Charging: At least one battery is charging and no batteries are discharging.
* Discharging: At least one battery is discharging.
* No Battery: No batteries have been detected.

A notification e-mail will be sent when the number of batteries installed changes or the
overall charge state changes.

## Prerequisites

This software is currently only supported on Ubuntu 18.04 and may not be ready for use in a production environment.

The only current method of installation for our software is building and installing your own debian package. We make the following assumptions:

*    You are already familiar with using a Linux terminal.
*    You are already somewhat familiar with using debuild.
*    `debhelper` and `devscripts` are installed on your build server.

## Parkbench Dependencies

_batwatch_ depends two other packages in the Parkbench project, which must be installed
first:

* [_parkbench-common_](https://github.com/park-bench/parkbench-common)
* [_gpgmailer_](https://github.com/park-bench/gpgmailer)

## Steps to Build and Install

1. Clone the latest release tag. (Do not clone the master branch. `master` may not be stable.)
2. Use `debuild` from the project root directory to build the package.
3. Use `dpkg -i` to install the package.
4. Use `apt-get -f install` to resolve any missing dependencies.

## Post-Install configuration

There is a configuration file at `/etc/batwatch/batwatch.conf.example` that needs to be
copied to `/etc/batwatch/batwatch.conf`. The file's ownership and permissions also need to
be changed:

```
chown root:batwatch /etc/batwatch/batwatch.conf
chmod u=rw,g=r,o= /etc/batwatch/batwatch.conf
```

## Updates

Updates may change configuration file options, so if you have a configuration
file already, check that it has all of the required options in the current
example file.
