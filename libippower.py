#!/usr/bin/python3



# ----- IPPower -----
#
# IPPower - a library & GUI utility for laptop power management
# Copyright (C) 2020  EthernetLord
# https://ethernetlord.eu/ - https://github.com/ethernetlord
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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.



class IPPowerError(Exception):
    pass


class IPPowerValueError(IPPowerError):
    def get_bad_value(self):
        try:
            return self._bad_value
        except AttributeError:
            return None

    def set_bad_value(self, bad_value):
        self._bad_value = bad_value
        return self


class IPPowerAccessError(IPPowerError):
    def get_description(self):
        try:
            return self._description
        except AttributeError:
            return None

    def set_description(self, description):
        self._description = description
        return self


class IPPowerVerificationError(IPPowerError):
    pass


class IPPower:
    LIBRARY_VERSION = 1
    _ACPI_CALL_PATH = "/proc/acpi/call"

    # Values of these constants are taken from the Arch Wiki:
    # https://wiki.archlinux.org/index.php/Lenovo_IdeaPad_5_15are05
    IP_PERFMODE_INTELLIGENT = r'0x000FB001'
    IP_PERFMODE_PERFORMANCE = r'0x0012B001'
    IP_PERFMODE_BATTERYSAVE = r'0x0013B001'
    IP_RAPIDCHARGE_ON = r'0x07'
    IP_RAPIDCHARGE_OFF = r'0x08'
    IP_BATCONSERV_ON = r'0x03'
    IP_BATCONSERV_OFF = r'0x05'

    _ACPI_GET_PERFMODE = r'\_SB.PCI0.LPC0.EC0.SPMO'
    _ACPI_GET_RAPIDCHARGE = r'\_SB.PCI0.LPC0.EC0.QCHO'
    _ACPI_GET_BATCONSERV = r'\_SB.PCI0.LPC0.EC0.BTSM'
    _ACPI_SET_PERFMODE = r'\_SB.PCI0.LPC0.EC0.VPC0.DYTC'
    _ACPI_SET_RAPIDCHARGE = r'\_SB.PCI0.LPC0.EC0.VPC0.SBMC'
    _ACPI_SET_BATCONSERV = r'\_SB.PCI0.LPC0.EC0.VPC0.SBMC'

    def __init__(self, show_debug_msgs=False):
        self._show_debug_msgs = show_debug_msgs

        import os

        if not os.path.exists(self._ACPI_CALL_PATH):
            raise IPPowerAccessError("The ACPI call interface doesn't exist on this system!").set_description('"{}" is missing (install the acpi_call kernel module)'.format(self._ACPI_CALL_PATH))

        if not os.access(self._ACPI_CALL_PATH, os.R_OK | os.W_OK):
            raise IPPowerAccessError("You are not permitted to access the ACPI call interface!").set_description('"{}" isn\'t accessible for reading or writing (try running the program as root)'.format(self._ACPI_CALL_PATH))

    def _debug_msg(self, *args):
        if self._show_debug_msgs:
            import sys
            import time

            print("[{} libippower DEBUG]".format(time.strftime("%Y-%m-%d %H:%M:%S")), *args, file=sys.stderr)

    def _acpi_call_read(self):
        with open(self._ACPI_CALL_PATH) as call_file:
            ret = call_file.read().strip().split("\x00")[0].strip()
            self._debug_msg("Read from ACPI call interface:", ret)
            return ret

    def _acpi_call_write(self, write_data):
        with open(self._ACPI_CALL_PATH, "w") as call_file:
            print(write_data, file=call_file)
            self._debug_msg("Written to ACPI call interface:", write_data)

    def _generic_get(self, acpi_path):
        self._acpi_call_write(acpi_path)
        return self._acpi_call_read()

    def _generic_set(self, acpi_path, value):
        call_value = (acpi_path + " " + value)
        self._acpi_call_write(call_value)

    def get_perfmode(self):
        perfmode = self._generic_get(self._ACPI_GET_PERFMODE)

        if perfmode == "0x0":
            return self.IP_PERFMODE_INTELLIGENT
        if perfmode == "0x1":
            return self.IP_PERFMODE_PERFORMANCE
        if perfmode == "0x2":
            return self.IP_PERFMODE_BATTERYSAVE

        raise IPPowerValueError("An invalid performance mode was returned by the ACPI!").set_bad_value(perfmode)

    def get_rapidcharge(self):
        rapidcharge = self._generic_get(self._ACPI_GET_RAPIDCHARGE)

        if rapidcharge == "0x0":
            return self.IP_RAPIDCHARGE_OFF
        if rapidcharge == "0x1":
            return self.IP_RAPIDCHARGE_ON

        raise IPPowerValueError("An invalid rapid charge status was returned by the ACPI!").set_bad_value(rapidcharge)

    def get_batconserv(self):
        batconserv = self._generic_get(self._ACPI_GET_BATCONSERV)

        if batconserv == "0x0":
            return self.IP_BATCONSERV_OFF
        if batconserv == "0x1":
            return self.IP_BATCONSERV_ON

        raise IPPowerValueError("An invalid battery conservation status was returned by the ACPI!").set_bad_value(batconserv)

    def set_perfmode(self, perfmode):
        if perfmode != self.IP_PERFMODE_INTELLIGENT and perfmode != self.IP_PERFMODE_PERFORMANCE and perfmode != self.IP_PERFMODE_BATTERYSAVE:
            raise IPPowerValueError("An invalid performance mode was provided!").set_bad_value(perfmode)

        self._generic_set(self._ACPI_SET_PERFMODE, perfmode)

        if perfmode != self.get_perfmode():
            raise IPPowerVerificationError("Failed to verify whether the performance mode was set correctly!")

    def set_rapidcharge(self, rapidcharge):
        if rapidcharge != self.IP_RAPIDCHARGE_ON and rapidcharge != self.IP_RAPIDCHARGE_OFF:
            raise IPPowerValueError("An invalid rapid charge status was provided!").set_bad_value(rapidcharge)

        # simulating the behaviour of the Lenovo Vantage software
        if rapidcharge == self.IP_RAPIDCHARGE_ON and self.get_batconserv() != self.IP_BATCONSERV_OFF:
            self.set_batconserv(self.IP_BATCONSERV_OFF)

        self._generic_set(self._ACPI_SET_RAPIDCHARGE, rapidcharge)

        if rapidcharge != self.get_rapidcharge():
            raise IPPowerVerificationError("Failed to verify whether the rapid charge status was set correctly!")

    def set_batconserv(self, batconserv):
        if batconserv != self.IP_BATCONSERV_ON and batconserv != self.IP_BATCONSERV_OFF:
            raise IPPowerValueError("An invalid battery conservation status was provided!").set_bad_value(batconserv)

        # simulating the behaviour of the Lenovo Vantage software
        if batconserv == self.IP_BATCONSERV_ON and self.get_rapidcharge() != self.IP_RAPIDCHARGE_OFF:
            self.set_rapidcharge(self.IP_RAPIDCHARGE_OFF)

        self._generic_set(self._ACPI_SET_BATCONSERV, batconserv)

        if batconserv != self.get_batconserv():
            raise IPPowerVerificationError("Failed to verify whether the battery conservation status was set correctly!")
