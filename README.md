# batwatch

_batwatch_ monitors a system's batteries and UPS units for state changes and sends encrypted
notification emails of state changes using our gpgmailer daemon.

batwatch is licensed under the GNU GPLv3.

This is software is still in _beta_ and may not be ready for use in a production environment.

Bug fixes are welcome!

## System Power States

batwatch looks at the number of batteries installed on a system and each of those batteries'
charge states to determine the system's overall charge state. The system charge state can be
one of the following:

*   Fully Charged: All batteries are fully charged and not discharging.
*   Charging: At least one battery is charging and no batteries are discharging.
*   Discharging: At least one battery is discharging.
*   No Battery: No batteries are detected.

A notification e-mail will be sent when the number of batteries installed changes or the
overall charge state changes.

## Prerequisites

This software is currently only supported on Ubuntu 18.04.

Currently, the only supported method for installation of this project is building and
installing a Debian package. The rest of these instructions make the following assumptions:

*   You are familiar with using a Linux terminal.
*   You are somewhat familiar with using `debuild`.
*   You are familiar with using `git` and GitHub.
*   `debhelper` and `devscripts` are installed on your build server.
*   You are familiar with GnuPG (for deb signing).

## Parkbench Dependencies

batwatch depends on two other Parkbench packages, which must be installed first:

*   [parkbench-common](https://github.com/park-bench/parkbench-common)
*   [gpgmailer](https://github.com/park-bench/gpgmailer)

## Steps to Build and Install

1.  Clone the repository and checkout the latest release tag. (Do not build against the
    `master` branch. The `master` branch might not be stable.)
2.  Run `debuild` in the project root directory to build the package.
3.  Run `apt install /path/to/package.deb` to install the package. The daemon will attempt to
    start and fail. (This is expected.)
4.  Copy or rename the example configuration file `/etc/batwatch/batwatch.conf.example` to
    `/etc/batwatch/batwatch.conf`. Make any desired configuration changes.
5.  Change the ownership and permissions of the configuration file:
```
chown root:batwatch /etc/batwatch/batwatch.conf
chmod u=rw,g=r,o= /etc/batwatch/batwatch.conf
```
6.  To ease system maintenance, add `batwatch` as a supplemental group to administrative
    users. Doing this will allow these users to view batwatch log files.
7.  Restart the daemon with `systemctl restart batwatch`. If the configuration file is valid,
    named correctly, and has the correct file permissions, the service will start
    successfully.

## Updates

Updates may change configuration file options. If a configuration file already exists, check
that it has all of the required options from the current example file.
