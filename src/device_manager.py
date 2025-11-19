#!/usr/bin/python3
"""
Device Manager for iPhone/iPad detection.
"""

import subprocess
from logger_config import get_logger

logger = get_logger('device_manager')


def get_friendly_model_name(product_type):
    """
    Convert technical model code to user-friendly name.
    """
    models = {
        # iPhone 11
        "iPhone12,1": "iPhone 11",
        "iPhone12,3": "iPhone 11 Pro",
        "iPhone12,5": "iPhone 11 Pro Max",
        # iPhone 12
        "iPhone13,1": "iPhone 12 mini",
        "iPhone13,2": "iPhone 12",
        "iPhone13,3": "iPhone 12 Pro",
        "iPhone13,4": "iPhone 12 Pro Max",
        # iPhone 13
        "iPhone14,4": "iPhone 13 mini",
        "iPhone14,5": "iPhone 13",
        "iPhone14,2": "iPhone 13 Pro",
        "iPhone14,3": "iPhone 13 Pro Max",
        # iPhone 14
        "iPhone14,7": "iPhone 14",
        "iPhone15,2": "iPhone 14 Pro",
        "iPhone15,3": "iPhone 14 Pro Max",
        # iPhone 15
        "iPhone15,4": "iPhone 15",
        "iPhone15,5": "iPhone 15 Plus",
        "iPhone16,1": "iPhone 15 Pro",
        "iPhone16,2": "iPhone 15 Pro Max",
        # iPhone 16
        "iPhone17,1": "iPhone 16 Pro",
        "iPhone17,2": "iPhone 16 Pro Max",
        "iPhone17,3": "iPhone 16",
        "iPhone17,4": "iPhone 16 Plus",
    }
    return models.get(product_type, product_type)


class Device:

    def __init__(self, udid):
        self.udid = udid                # Unique device identifier
        self.name = None                # Device name
        self.model = None               # Device model (technical)
        self.friendly_model = None      # Device model (user-friendly)
        self.ios_version = None         # iOS version
        self.build_version = None       # iOS build version
        self.storage_total = None       # Total storage (GB)
        self.storage_used = None        # Used storage
        self.storage_available = None   # Available storage
        self.is_trusted = False         # Trust status
        self.serial_number = None       # Serial number
        self.hardware_model = None      # Hardware model
        self.battery_level = None       # Battery level (%)
        self.battery_state = None       # Battery state
        self.wifi_mac = None            # WiFi MAC address
        self.bluetooth_mac = None       # Bluetooth MAC address


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
            device.friendly_model = get_friendly_model_name(device.model)
            device.ios_version = device_data.get('ProductVersion', None)
            device.build_version = device_data.get('BuildVersion', None)
            device.serial_number = device_data.get('SerialNumber', None)
            device.hardware_model = device_data.get('HardwareModel', None)
            device.wifi_mac = device_data.get('WiFiAddress', None)
            device.bluetooth_mac = device_data.get('BluetoothAddress', None)

            # These values are based on libimobiledevice's disk_usage domain
            try:
                disk_result = subprocess.run(
                    [
                        'ideviceinfo', '-u', udid,
                        '-q', 'com.apple.disk_usage'
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False
                )
                if disk_result.returncode == 0:
                    # Parse disk usage data
                    disk_data = {}
                    for line in disk_result.stdout.split('\n'):
                        if ':' in line:
                            key, value = line.split(':', 1)
                            disk_data[key.strip()] = value.strip()

                    # Total capacity
                    total_capacity = disk_data.get('TotalDiskCapacity')
                    if total_capacity:
                        try:
                            total_bytes = int(total_capacity)
                            device.storage_total = total_bytes / (1000**3)
                        except ValueError:
                            pass
                    # Available storage
                    available_capacity = disk_data.get('TotalDataAvailable')
                    if available_capacity:
                        try:
                            available_bytes = int(available_capacity)
                            device.storage_available = available_bytes / (1000**3)
                        except ValueError:
                            pass

                    # Calculate used storage
                    # NOTE: This may show less than iPhone because iPhone
                    # includes system data, cache, and reserved space
                    if device.storage_total and device.storage_available:
                        device.storage_used = device.storage_total - device.storage_available

            except (subprocess.SubprocessError, OSError) as e:
                logger.warning("Could not get disk usage info: %s", e)

            # Get battery info
            try:
                battery_result = subprocess.run(
                    [
                        'ideviceinfo', '-u', udid,
                        '-q', 'com.apple.mobile.battery'
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False
                )
                if battery_result.returncode == 0:
                    # Parse battery data
                    battery_data = {}
                    for line in battery_result.stdout.split('\n'):
                        if ':' in line:
                            key, value = line.split(':', 1)
                            battery_data[key.strip()] = value.strip()

                    # Get battery level
                    battery_capacity = battery_data.get('BatteryCurrentCapacity')
                    if battery_capacity:
                        try:
                            device.battery_level = int(battery_capacity)
                        except ValueError:
                            pass

                    # Get battery state
                    is_charging = battery_data.get('BatteryIsCharging')
                    if is_charging:
                        if is_charging.lower() == "true":
                            device.battery_state = "Charging"
                        elif is_charging.lower() == "false":
                            device.battery_state = "Discharging"

            except (subprocess.SubprocessError, OSError) as e:
                logger.warning("Could not get battery info: %s", e)

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
