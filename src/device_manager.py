#!/usr/bin/python3
"""
Device Manager for iPhone/iPad detection.
"""

import subprocess
from logger_config import get_logger

logger = get_logger('device_manager')


class Device:

    def __init__(self, udid):
        self.udid = udid           # Unique device identifier
        self.name = None           # Device name
        self.model = None          # Device model
        self.ios_version = None    # iOS version
        self.storage_total = None  # Total storage (GB)
        self.is_trusted = False    # Trust status
        self.serial_number = None  # Serial number


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
        try:
            # List connected devices
            logger.info("Running idevice_id -l to detect devices")
            result = subprocess.run(
                ['idevice_id', '-l'],
                capture_output=True,
                text=True,
                timeout=5,
                check=False
            )

            if result.returncode != 0:
                logger.warning(
                    "idevice_id failed with code %d: %s",
                    result.returncode, result.stderr
                )
                return []

            # Parse ourput | each line is a UDID
            output_lines = result.stdout.split('\n')
            udids = [line.strip() for line in output_lines if line.strip()]

            logger.info("Found %d connected device(s)", len(udids))
            for udid in udids:
                logger.debug("  - UDID: %s", udid)

            return udids

        except FileNotFoundError:
            logger.error(
                "idevice_id not found. "
                "Please install libimobiledevice-utils"
            )
            return []
        except subprocess.TimeoutExpired:
            logger.error("idevice_id command timed out")
            return []
        except Exception as e:
            logger.error("Error getting connected devices: %s", e)
            return []

    def get_device_info(self, udid):
        """
        Get device information for given UDID.
        Returns device object with name, model & iOS version.
        """
        try:
            # Run ideviceinfo for specific device with udid
            logger.info("Getting device info for UDID: %s", udid)
            result = subprocess.run(
                ['ideviceinfo', '-u', udid],
                capture_output=True,
                text=True,
                timeout=10,
                check=False
            )

            if result.returncode != 0:
                logger.warning("ideviceinfo failed for %s", udid)
                return None

            # Parse output | key: value
            device_data = {}
            for line in result.stdout.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    device_data[key.strip()] = value.strip()

            # Create device object
            device = Device(udid)
            device.name = device_data.get('DeviceName', None)
            device.model = device_data.get('ProductType', None)
            device.ios_version = device_data.get('ProductVersion', None)
            device.serial_number = device_data.get('SerialNumber', None)

            # Get total capacity
            try:
                disk_result = subprocess.run(
                    [
                        'ideviceinfo', '-u', udid,
                        '-q', 'com.apple.disk_usage',
                        '-k', 'TotalDiskCapacity'
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False
                )
                if disk_result.returncode == 0:
                    value_str = disk_result.stdout.strip()
                    try:
                        total_bytes = int(value_str)
                        device.storage_total = total_bytes / (1000**3)
                    except ValueError:
                        logger.warning(
                            "Unexpected TotalDiskCapacity value: %r",
                            value_str
                        )
            except (subprocess.SubprocessError, OSError) as e:
                logger.warning("Could not get disk usage info: %s", e)

            # Check trust status, if device info = 0, device is trusted
            device.is_trusted = True

            total_gb = device.storage_total if device.storage_total else 0

            # Log device info
            logger.info(
                "Device: %s (%s, iOS %s, %.0fGB total, Trusted: %s)",
                device.name or "Unknown",
                device.model or "Unknown",
                device.ios_version or "Unknown",
                total_gb,
                device.is_trusted
            )

            return device

        except FileNotFoundError:
            logger.error("ideviceinfo not found")
            return None

    def refresh_devices(self):
        """
        Scan for devices and return list of Device objects.
        Main function that combines everything.
        """
        logger.info("Starting device refresh scan")

        # Get UDIDs
        udids = self.get_connected_devices()

        if not udids:
            logger.info("No devices connected")
            return []

        # Get info for each device
        devices = []
        for udid in udids:
            device = self.get_device_info(udid)
            if device:
                devices.append(device)
            else:
                logger.warning("Could not get info for %s", udid)

        logger.info("Device refresh complete: %d device(s)", len(devices))
        return devices
