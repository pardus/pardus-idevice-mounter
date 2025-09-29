# pylint: disable=no-member


import os
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
from device_manager import DeviceManager
# Import logging system
from logger_config import get_logger

# Get logger for this module
logger = get_logger('main_window')


class MainWindow(Gtk.Window):
    def __init__(self, application):
        """Initializes the main window."""
        super().__init__(application=application)
        self.builder = Gtk.Builder()
        glade_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "../ui/main_window.glade"
        )
        try:
            self.builder.add_from_file(glade_file)
        except (FileNotFoundError, GLib.Error) as e:
            logger.error(f"Error loading glade file: {e}")
            return

        self.device_manager = DeviceManager()

        self.init_widgets()
        self.init_signals()
        self.set_version()

        status_stack = self.builder.get_object("status_stack")
        if status_stack:
            status_stack.set_visible_child_name("empty")

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

        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_title("Pardus iDevice Mounter")
        self.set_default_size(600, 400)

        if glade_window:
            self.set_icon_name(glade_window.get_icon_name())

        self.menu_popover = self.builder.get_object("menu_popover")
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
            "on_mount_button_clicked": self.on_mount_button_clicked,
            "on_unmount_button_clicked": self.on_unmount_button_clicked,
            "on_row_primary_button_clicked": self.on_row_primary_button_clicked,
            "on_row_details_button_clicked": self.on_row_details_button_clicked,
            "on_retry_button_clicked": self.on_retry_button_clicked,
            "on_reopen_button_clicked": self.on_reopen_button_clicked,
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
        status_stack = self.builder.get_object("status_stack")
        if status_stack:
            status_stack.set_visible_child_name("loading")

        GLib.idle_add(self._scan_devices_idle)

    def on_mount_button_clicked(self, widget):
        """
        Handles the mount button click event.
        """
        logger.info("Mount button clicked")

    def on_unmount_button_clicked(self, widget):
        """
        Handles the unmount button click event.
        """
        logger.info("Unmount button clicked")

    def on_row_primary_button_clicked(self, widget):
        """
        Handles the row primary button click event.
        """
        logger.info("Row primary button clicked")

    def on_row_details_button_clicked(self, widget):
        """
        Handles the row details button click event.
        """
        logger.info("Row details button clicked")

    def on_retry_button_clicked(self, widget):
        """
        Handles the retry button click event.
        """
        logger.info("Retry button clicked")

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

    def on_scan_button_clicked(self, widget):
        """
        Handles the scan button click event.
        """
        logger.info("Scan button clicked - Starting device scan")
        status_stack = self.builder.get_object("status_stack")
        if status_stack:
            status_stack.set_visible_child_name("loading")

        # Use GLib idle callback for device scanning
        GLib.idle_add(self._scan_devices_idle)

    def on_menu_about_button_clicked(self, widget):
        """
        Shows about & credits parts of the device dialog.
        """
        self.menu_popover.popdown()
        self.device_dialog.run()
        self.device_dialog.hide()

    def _scan_devices_idle(self):
        """
        Scan devices from device manager. Shows msgs due to device scanning.
        Returns False after 5 seconds.
        """
        try:
            devices = self.device_manager.refresh_devices()
            logger.info(f"Device scan completed - Found {len(devices)} devices")

            if devices:
                logger.info("Found devices:")
                for device in devices:
                    device_name = device.name or device.model or f"Device_{device.udid[:8]}"
                    logger.info(f"  - {device_name} (UDID: {device.udid})")
                self._show_banner_message(f"{len(devices)} device(s) found")
            else:
                logger.info("No devices found")
                self._show_banner_message(
                    "No iPhone/iPad found. Connect via USB and confirm 'Trust'"
                    )

            # Return to empty state after 5 seconds
            GLib.timeout_add_seconds(5, self._back_to_empty)

        except Exception as e:
            logger.error(f"Device scan error: {e}")
            self._show_banner_message("Scan error. Install required tools.")
            self._back_to_empty()

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
            logger.debug(f"Banner message displayed: {message}")

    def _resize_window_after_banner(self):
        """
        Resize window to natural size after banner is hidden.
        """
        width, _ = self.get_size()
        self.resize(width, 1)
        return False

    def _back_to_empty(self):
        """
        Sets the status stack to the empty view.
        """
        status_stack = self.builder.get_object("status_stack")
        if status_stack:
            status_stack.set_visible_child_name("empty")
        return False
