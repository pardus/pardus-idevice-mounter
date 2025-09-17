#!/usr/bin/python3
"""
Device Manager for iPhone/iPad detection.
"""


class Device:

    def __init__(self, udid):
        self.udid = udid
        self.name = None
        self.model = None
        self.ios_version = None


class DeviceManager:
    """
    Manages iOS device detection and information.
    """

    def __init__(self):
        pass

    def get_connected_devices(self):
        """
        Get list of connected device UDIDs.
        Returns list of UDID strings.
        """
        # TODO: Run idevice_id -l command
        # TODO: Parse output
        # TODO: Return list of UDIDs
        pass

    def get_device_info(self, udid):
        """
        Get device information for given UDID.
        Returns device object with name, model & iOS version.
        """
        # TODO: Run ideviceinfo -u <udid> command
        # TODO: Parse device name, model, iOS version
        # TODO: Return Device object
        pass

    def refresh_devices(self):
        """
        Scan for devices and return list of Device objects.
        Main function that combines everything.
        """
        # TODO: Get UDIDs using get_connected_devices()
        # TODO: For each UDID, get info using get_device_info()
        # TODO: Return list of Device objects
        pass
