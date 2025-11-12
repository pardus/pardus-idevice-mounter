# pylint: disable=no-member


import os
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
from device_manager import DeviceManager
from logger_config import get_logger
from mount_manager import MountManager

logger = get_logger('main_window')

import locale
from locale import gettext as _
locale.bindtextdomain('pardus-idevice-mounter', '/usr/share/locale')
locale.textdomain('pardus-idevice-mounter')
_ = locale.gettext


class MainWindow(Gtk.Window):
    def __init__(self, application):
        """Initializes the main window."""
        super().__init__(application=application)
        self.builder = Gtk.Builder()
        self.glade_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "../ui/main_window.glade"
        )
        try:
            self.builder.add_from_file(self.glade_file)
        except (FileNotFoundError, GLib.Error) as e:
            logger.error(f"Error loading glade file: {e}")
            return

        self.device_manager = DeviceManager()
        self.mount_manager = MountManager()
        self.mount_manager.cleanup_stale_mounts()

        self.init_widgets()
        self.init_signals()
        self.set_version()

    def init_widgets(self):
        """
        Initializes widgets from the glade file.
        """
        glade_window = self.builder.get_object("main_window")
        if glade_window:
            child = glade_window.get_child()
            if child:
                glade_window.remove(child)
                self.add(child)

        header_bar = self.builder.get_object("header_bar")
        if header_bar:
            parent = header_bar.get_parent()
            if parent:
                parent.remove(header_bar)

            self.set_titlebar(header_bar)
            header_bar.show_all()

        self.status_stack = self.builder.get_object("status_stack")
        if self.status_stack:
            self.status_stack.set_visible_child_name("empty")

        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_title(_("Pardus iDevice Mounter"))
        self.set_default_size(600, 400)

        if glade_window:
            self.set_icon_name(glade_window.get_icon_name())

        self.menu_popover = self.builder.get_object("menu_popover")
        self.list_box = self.builder.get_object("list_box")
        self.device_dialog = self.builder.get_object("device_dialog")
        if self.device_dialog:
            self.device_dialog.set_transient_for(self)
            self.device_dialog.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)

        self.show_all()

    def init_signals(self):
        """
        Initializes signals for the widgets.
        """
        self.builder.connect_signals({
            "on_refresh_button_clicked": self.on_refresh_button_clicked,
            "on_scan_button_clicked": self.on_scan_button_clicked,
            "on_retry_button_clicked": self.on_retry_button_clicked,
            "on_menu_about_button_clicked": self.on_menu_about_button_clicked,
            "on_banner_close_button_clicked": self.on_banner_close_button_clicked
        })

    def set_version(self):
        """
        Sets the application version from the __version__ file.
        """
        try:
            version_file = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "__version__"
            )
            with open(version_file, "r") as f:
                version = f.readline().strip()
                device_dialog = self.builder.get_object("device_dialog")
                if device_dialog:
                    device_dialog.set_version(version)
        except FileNotFoundError:
            pass

    def on_refresh_button_clicked(self, widget):
        """
        Handles the refresh button click event.
        """
        logger.info("Refresh button clicked - Starting device scan")

        if self.status_stack:
            self.status_stack.set_visible_child_name("loading")

        GLib.idle_add(self._scan_devices_idle)

    def on_scan_button_clicked(self, widget):
        """
        Handles the scan button click event.
        """
        logger.info("Scan button clicked")
        if self.status_stack:
            self.status_stack.set_visible_child_name("loading")

        GLib.idle_add(self._scan_devices_idle)

    def on_retry_button_clicked(self, widget):
        """
        Handles the retry button click event.
        """
        logger.info("Retry button clicked - Starting device scan")
        self.on_scan_button_clicked(widget)

    def on_reopen_button_clicked(self, widget):
        """
        Handles the reopen button click event.
        """
        logger.info("Reopen button clicked")

    def on_banner_close_button_clicked(self, widget):
        """
        Handles the banner close button click event.
        """
        banner_revealer = self.builder.get_object("banner_revealer")
        if banner_revealer:
            banner_revealer.set_reveal_child(False)

            GLib.timeout_add(100, self._resize_window_after_banner)

    def on_menu_about_button_clicked(self, widget):
        """
        Shows about & credits parts of the device dialog.
        """
        self.menu_popover.popdown()
        self.device_dialog.run()
        self.device_dialog.hide()

    def _create_device_row(self, device):
        """
        Creates a row for each device.
        Sets device information to the row.
        """
        # TODO: Add device model info (iphone13..)

        logger.info(f"Creating row for device: {device.udid}")

        row = Gtk.ListBoxRow()
        row.device = device
        row.is_mounted = False
        row.mount_point = None

        # Main box
        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        main_box.set_margin_start(8)
        main_box.set_margin_end(8)
        main_box.set_margin_top(6)
        main_box.set_margin_bottom(6)

        # Icon and trustted status dot
        icon_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        icon = Gtk.Image.new_from_icon_name("phone-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
        icon.set_pixel_size(30)

        dot_label = Gtk.Label(label="●")
        if device.is_trusted:
            dot_label.set_markup('<span foreground="green">●</span>')
        else:
            dot_label.set_markup('<span foreground="red">●</span>')

        icon_box.pack_start(icon, False, False, 0)
        icon_box.pack_start(dot_label, False, False, 0)

        # Device information box
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        info_box.set_hexpand(True)

        # Device name
        name_label = Gtk.Label()
        device_name = device.name or device.model or f"{_("Device")}_{device.udid}"
        name_label.set_markup(f'<span weight="bold" size="larger">{device_name}</span>')
        name_label.set_xalign(0)

        # Storage and iOS version
        details_label = Gtk.Label()
        storage_text = f"{device.storage_total:.0f}GB" if device.storage_total else _("Unknown")
        ios_text = device.ios_version or _("Unknown")
        details_label.set_text(f"{storage_text} · iOS {ios_text}")
        details_label.set_xalign(0)

        # Trust status ve UDID
        status_label = Gtk.Label()
        trust_text = _("Trusted") if device.is_trusted else _("Not Trusted")
        udid_short = device.udid[:8] + "..." if len(device.udid) > 8 else device.udid
        status_label.set_markup(f'<span style="italic">{trust_text} · UDID: {udid_short}</span>')
        status_label.set_xalign(0)

        info_box.pack_start(name_label, False, False, 0)
        info_box.pack_start(details_label, False, False, 0)
        info_box.pack_start(status_label, False, False, 0)

        # Right side (Mount and details buttons)
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        mount_button = Gtk.Button(label=_("Mount"))
        mount_button.connect("clicked", self._on_row_mount_toggle, row)
        row.mount_button = mount_button

        details_button = Gtk.Button(label=_("Details"))
        details_button.connect("clicked", self._on_row_details_clicked, device)

        button_box.pack_start(mount_button, False, False, 0)
        button_box.pack_start(details_button, False, False, 0)

        # Merge all boxes
        main_box.pack_start(icon_box, False, False, 0)
        main_box.pack_start(info_box, False, False, 0)
        main_box.pack_start(button_box, False, False, 0)

        row.add(main_box)
        row.show_all()

        return row

    def _on_row_mount_toggle(self, widget, row):
        """
        Mount - unmount jobs
        """
        device = row.device
        device_name = device.name or _("Device")

        if not row.is_mounted:
            # Mount
            logger.info(f"Mounting device: {device.udid}")

            success, mount_point, error_msg = self.mount_manager.mount_device(device)

            if success:
                row.is_mounted = True
                row.mount_point = mount_point
                row.mount_button.set_label("Unmount")
                self._show_banner_message(_(f"{device_name} mounted successfully"))

                # Open file manager
                self.mount_manager.open_file_manager(mount_point)
            else:
                error_msg = error_msg or "Unknown error"
                self._show_banner_message(_(f"Mount failed: {error_msg}"))
                logger.error(f"Mount failed for {device.udid}: {error_msg}")

        else:
            # Unmount
            logger.info(f"Unmounting device: {device.udid}")

            success, error_msg = self.mount_manager.unmount_device(row.mount_point)

            if success:
                row.is_mounted = False
                row.mount_point = None
                row.mount_button.set_label("Mount")
                self._show_banner_message(_(f"{device_name} unmounted successfully"))
            else:
                error_msg = error_msg or "Unknown error"
                self._show_banner_message(_(f"Unmount failed: {error_msg}"))
                logger.error(f"Unmount failed for {device.udid}: {error_msg}")

    def _on_row_details_clicked(self, widget, device):
        """
        Row details button clicked
        """
        logger.info(f"Details clicked for device: {device.udid}")
        device_name = device.name or "Device"
        # TODO: Show details dialog for selectedevice
        # TODO: Add device model, name, storage, iOS version, UUID, trust status, battery level..
        self._show_banner_message(_(f"Details for {device_name}"))

    def _scan_devices_idle(self):
        """
        Scan devices and create a row for each device.
        Switch between pages due to device scan results
        """
        try:
            # Clean up any stale mounts before scanning
            self.mount_manager.cleanup_stale_mounts()

            devices = self.device_manager.refresh_devices()
            logger.info(f"Device scan completed - Found {len(devices)} devices")

            # Del old rows
            for child in self.list_box.get_children():
                self.list_box.remove(child)

            if devices:
                for device in devices:
                    row = self._create_device_row(device)
                    self.list_box.add(row)
                self._show_banner_message(_(f"{len(devices)} device(s) found"))

                if self.status_stack:
                    self.status_stack.set_visible_child_name("success")
            else:
                logger.info("No devices found")
                self._show_banner_message(
                    _("No iPhone/iPad found. Connect via USB and confirm 'Trust'"))

                if self.status_stack:
                    self.status_stack.set_visible_child_name("empty")
        except Exception as e:
            logger.error(f"Device scan error: {e}")
            self._show_banner_message(_("Scan error. Install required tools."))

            if self.status_stack:
                self.status_stack.set_visible_child_name("error")

        return False

    def _show_banner_message(self, message):
        """
        Show a message in the banner.
        """
        banner_label = self.builder.get_object("banner_label")
        banner_revealer = self.builder.get_object("banner_revealer")

        if banner_label and banner_revealer:
            banner_label.set_text(message)
            banner_revealer.set_reveal_child(True)
            logger.debug(f"Banner message: {message}")

    def _resize_window_after_banner(self):
        """
        Resize window to natural size after banner is hidden.
        """
        width, _ = self.get_size()
        self.resize(width, 1)
        return False
