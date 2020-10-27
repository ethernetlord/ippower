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



import libippower
import sys
import time
from gi import require_version as gi_require_version
gi_require_version('Gtk', '3.0')
from gi.repository import Gtk


class CONSTS:
    PRINT_ACPI_CALL_DEBUG_MSGS = False


class FatalErrorDialogViewer:
    _DIALOG_TITLE = "Fatal IPPower error"
    _EXIT_CODE = 119

    def __init__(self, main_window):
        self._main_window = main_window

    def view(self, content):
        dialog = Gtk.MessageDialog(transient_for=self._main_window, message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.OK, text=self._DIALOG_TITLE + "\n")
        dialog.format_secondary_markup(content)

        dialog.run()
        dialog.destroy()

        sys.exit(self._EXIT_CODE)

    def view_library_get_error(self, what, exception):
        self.view("<big>Failed to obtain the current {}!</big>\n\nError message: <b>{}</b>".format(what, str(exception)))

    def view_library_set_error(self, what, exception):
        self.view("<big>Failed to update the {}!</big>\n\nError message: <b>{}</b>".format(what, str(exception)))

    def view_library_access_error(self, exception):
        self.view("<big>A fatal access error has occurred!</big>\n\nError message: <b>{}</b>\nError description: <b>{}</b>".format(str(exception), exception.get_description()))


class PowerController:
    _TIMESTAMP_FORMAT = "%H:%M:%S"

    def __init__(self, main_window, perfmode_combo, rapidcharge_switch, batconserv_switch, last_refrershed_label, last_changed_label):
        self._fatal_error_dialog_viewer = FatalErrorDialogViewer(main_window)
        self._currently_refreshed = False

        self._perfmode_combo = perfmode_combo
        self._rapidcharge_switch = rapidcharge_switch
        self._batconserv_switch = batconserv_switch
        self._last_refrershed_label = last_refrershed_label
        self._last_changed_label = last_changed_label

        try:
            self._ippower = libippower.IPPower(show_debug_msgs=CONSTS.PRINT_ACPI_CALL_DEBUG_MSGS)
        except libippower.IPPowerAccessError as e:
            self._fatal_error_dialog_viewer.view_library_access_error(e)


    def refresh(self, refresh_perfmode=True, refresh_rapidcharge=True, refresh_batconserv=True):
        self._currently_refreshed = True

        if refresh_perfmode:
            try:
                perfmode = self._ippower.get_perfmode()
            except libippower.IPPowerError as e:
                self._fatal_error_dialog_viewer.view_library_get_error("performance mode", e)

            if perfmode == libippower.IPPower.IP_PERFMODE_INTELLIGENT:
                self._perfmode_combo.set_active(0)
            elif perfmode == libippower.IPPower.IP_PERFMODE_PERFORMANCE:
                self._perfmode_combo.set_active(1)
            else:
                self._perfmode_combo.set_active(2)

        if refresh_rapidcharge:
            try:
                rapidcharge = self._ippower.get_rapidcharge()
            except libippower.IPPowerError as e:
                self._fatal_error_dialog_viewer.view_library_get_error("rapid charge status", e)
            self._rapidcharge_switch.set_active(rapidcharge == libippower.IPPower.IP_RAPIDCHARGE_ON)

        if refresh_batconserv:
            try:
                batconserv = self._ippower.get_batconserv()
            except libippower.IPPowerError as e:
                self._fatal_error_dialog_viewer.view_library_get_error("battery conservation status", e)
            self._batconserv_switch.set_active(batconserv == libippower.IPPower.IP_BATCONSERV_ON)

        self._update_last_refreshed_label()
        self._currently_refreshed = False

    def _update_last_refreshed_label(self):
        timestamp = time.strftime(self._TIMESTAMP_FORMAT)
        self._last_refrershed_label.set_markup("<i>Last refreshed: {}</i>".format(timestamp))

    def _update_last_changed_label(self):
        timestamp = time.strftime(self._TIMESTAMP_FORMAT)
        self._last_changed_label.set_markup("<i>Last changed: {}</i>".format(timestamp))

    def perfmode_changed(self, combobox):
        if self._currently_refreshed:
            return

        perfmode_idx = self._perfmode_combo.get_active()

        try:
            if perfmode_idx == 0:
                self._ippower.set_perfmode(libippower.IPPower.IP_PERFMODE_INTELLIGENT)
            elif perfmode_idx == 1:
                self._ippower.set_perfmode(libippower.IPPower.IP_PERFMODE_PERFORMANCE)
            else:
                self._ippower.set_perfmode(libippower.IPPower.IP_PERFMODE_BATTERYSAVE)
        except libippower.IPPowerError as e:
            self._fatal_error_dialog_viewer.view_library_set_error("performance mode", e)

        self._update_last_changed_label()
        self.refresh(refresh_perfmode=False)

    def rapidcharge_changed(self, event, switch):
        if self._currently_refreshed:
            return

        rapidcharge_on = self._rapidcharge_switch.get_active()

        try:
            self._ippower.set_rapidcharge(libippower.IPPower.IP_RAPIDCHARGE_ON if rapidcharge_on else libippower.IPPower.IP_RAPIDCHARGE_OFF)
        except libippower.IPPowerError as e:
            self._fatal_error_dialog_viewer.view_library_set_error("rapid charge status", e)

        self._update_last_changed_label()
        self.refresh(refresh_rapidcharge=False)

    def batconserv_changed(self, event, switch):
        if self._currently_refreshed:
            return

        batconserv_on = self._batconserv_switch.get_active()

        try:
            self._ippower.set_batconserv(libippower.IPPower.IP_BATCONSERV_ON if batconserv_on else libippower.IPPower.IP_BATCONSERV_OFF)
        except libippower.IPPowerError as e:
            self._fatal_error_dialog_viewer.view_library_set_error("battery conservation status", e)

        self._update_last_changed_label()
        self.refresh(refresh_batconserv=False)


class MainWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="IPPower", resizable=False)
        self.connect("delete-event", Gtk.main_quit)
        self.set_border_width(15)

        self._initialize_headerbar()
        self._initialize_widgets()

        self._status_updater = PowerController(self, self._perfmode_combo, self._rapidcharge_switch, self._batconserv_switch, self._last_refrershed_label, self._last_changed_label)
        self._perfmode_combo.connect("changed", self._status_updater.perfmode_changed)
        self._rapidcharge_switch.connect("state-set", self._status_updater.rapidcharge_changed)
        self._batconserv_switch.connect("state-set", self._status_updater.batconserv_changed)
        self._refresh_btn.connect("clicked", self._status_updater.refresh)
        self._status_updater.refresh()

    def _initialize_headerbar(self):
        headerbar = Gtk.HeaderBar(show_close_button=True, title="IPPower")
        self.set_titlebar(headerbar)

        self._refresh_btn = Gtk.Button(label="Refresh")
        headerbar.pack_start(self._refresh_btn)

    def _initialize_widgets(self):
        box = Gtk.Box(spacing=10, orientation=Gtk.Orientation.VERTICAL)
        self.add(box)

        grid = Gtk.Grid(row_spacing=10, column_spacing=30)
        box.pack_start(grid, expand=True, fill=True, padding=0)

        # control - performance mode
        perfmode_label = Gtk.Label()
        perfmode_label.set_markup("<big><b>System performance mode</b></big>")
        grid.add(perfmode_label)

        perfmode_combo_renderer = Gtk.CellRendererText()
        perfmode_combo_liststore = Gtk.ListStore(str)
        for item in ("Intelligent cooling", "Extreme performance", "Battery saving"):
            perfmode_combo_liststore.append([item])

        self._perfmode_combo = Gtk.ComboBox(model=perfmode_combo_liststore, expand=False, halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        self._perfmode_combo.pack_start(perfmode_combo_renderer, True)
        self._perfmode_combo.add_attribute(perfmode_combo_renderer, "text", 0)
        grid.attach_next_to(self._perfmode_combo, perfmode_label, Gtk.PositionType.BOTTOM, 1, 1)

        # control - rapid charge
        rapidcharge_label = Gtk.Label()
        rapidcharge_label.set_markup("<big><b>Rapid charge</b></big>")
        grid.attach_next_to(rapidcharge_label, perfmode_label, Gtk.PositionType.RIGHT, 1, 1)

        self._rapidcharge_switch = Gtk.Switch(expand=False, halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)

        grid.attach_next_to(self._rapidcharge_switch, rapidcharge_label, Gtk.PositionType.BOTTOM, 1, 1)

        # control - battery conservation
        batconserv_label = Gtk.Label()
        batconserv_label.set_markup("<big><b>Battery conservation</b></big>")
        grid.attach_next_to(batconserv_label, rapidcharge_label, Gtk.PositionType.RIGHT, 1, 1)

        self._batconserv_switch = Gtk.Switch(expand=False, halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        grid.attach_next_to(self._batconserv_switch, batconserv_label, Gtk.PositionType.BOTTOM, 1, 1)

        # separator between control and info window parts
        box.pack_start(Gtk.HSeparator(margin_top=10, margin_bottom=10), expand=True, fill=True, padding=0)

        # info - autoapply notice
        box.pack_start(Gtk.Label(label="Changes are always applied automatically."), expand=True, fill=True, padding=0)

        # info - timestamp labels
        timestamps_box = Gtk.Box(spacing=10, orientation=Gtk.Orientation.HORIZONTAL)
        box.pack_start(timestamps_box, expand=True, fill=True, padding=0)

        self._last_refrershed_label = Gtk.Label()
        self._last_refrershed_label.set_markup("<i>Last refreshed: (never)</i>")
        timestamps_box.pack_start(self._last_refrershed_label, expand=True, fill=True, padding=0)

        self._last_changed_label = Gtk.Label()
        self._last_changed_label.set_markup("<i>Last changed: (never)</i>")
        timestamps_box.pack_start(self._last_changed_label, expand=True, fill=True, padding=0)


def print_gpl_notice():
    print("IPPower  Copyright (C) 2020  EthernetLord")
    print("Licensed under GNU GPLv3.")
    print()
    print("This program comes with ABSOLUTELY NO WARRANTY.")
    print("This is free software, and you are welcome to redistribute it under certain conditions.")
    print()


def main():
    print_gpl_notice()

    window = MainWindow()
    window.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
