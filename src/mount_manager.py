#!/usr/bin/python3
"""
Mount manager for device mounting and unmounting operations.
"""
import subprocess
import os
import re
from pathlib import Path
from logger_config import get_logger

logger = get_logger('mount_manager')


class MountManager:
    def __init__(self):
        self.mount_base_dir = Path(f"/run/user/{os.getuid()}/idevices")
        self.mount_base_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Mount base directory: {self.mount_base_dir}")

    def mount_device(self, device):
        """
        Mount device using ifuse.
        Returns success status, mount point
        """
        try:
            device_name = device.name if device.name else "Device"

            # Remove unsafe characters
            device_name = re.sub(r'[/\\:*?"<>|]', '', device_name)
            device_name = device_name.strip()

            if not device_name:
                device_name = "Device"

            # Add UDID
            device_name = f"{device_name}_{device.udid}"
            mount_point = self.mount_base_dir / device_name

            # Check if mount point exists
            if mount_point.exists():
                if self.is_mounted(str(mount_point)):
                    logger.warning(f"Already mounted: {device_name}")
                    return False, None, "Device already mounted"
                else:
                    # Dir exists but not mounted - try to rm
                    try:
                        mount_point.rmdir()
                    except OSError:
                        logger.warning(f"Mount point exists: {mount_point}")
                        return False, None, "Mount point dir already exists"

            # Create mount point
            mount_point.mkdir(parents=True, exist_ok=True)
            logger.info(f"Mounting {device_name}")

            # Mount using ifuse
            result = subprocess.run(
                ['ifuse', '-u', device.udid, str(mount_point)],
                capture_output=True,
                text=True,
                timeout=15,
                check=False
            )

            if result.returncode == 0:
                logger.info(f"Mount successful: {device_name}")
                return True, str(mount_point), None
            else:
                try:
                    mount_point.rmdir()
                except OSError:
                    pass

                error_msg = result.stderr.strip() if result.stderr else "Mount failed"
                logger.error(f"Mount failed: {error_msg}")
                return False, None, error_msg

        except FileNotFoundError:
            error_msg = "ifuse not found"
            logger.error(error_msg)
            return False, None, error_msg
        except subprocess.TimeoutExpired:
            error_msg = "Mount timed out"
            logger.error(error_msg)
            return False, None, error_msg
        except Exception as e:
            error_msg = f"Mount error: {e}"
            logger.error(error_msg)
            return False, None, error_msg

    def unmount_device(self, mount_point):
        """
        Unmount device.
        Returns success status, error message
        """
        try:
            logger.info(f"Unmounting {Path(mount_point).name}")

            result = subprocess.run(
                ['fusermount', '-u', str(mount_point)],
                capture_output=True,
                text=True,
                timeout=15,
                check=False
            )

            if result.returncode == 0:
                logger.info("Unmount successful")

                # Try to rm dir
                try:
                    Path(mount_point).rmdir()
                except OSError:
                    pass

                return True, None
            else:
                error_msg = result.stderr.strip() if result.stderr else "Unmount failed"
                logger.error(f"Unmount failed: {error_msg}")
                return False, error_msg

        except FileNotFoundError:
            return False, "fusermount not found"
        except subprocess.TimeoutExpired:
            return False, "Unmount timed out"
        except Exception as e:
            logger.error(f"Unmount error: {e}")
            return False, str(e)

    def open_file_manager(self, path):
        """
        Open file manager using xdg-open
        """
        try:
            subprocess.Popen(['xdg-open', path])
            logger.info("File manager opened")
            return True
        except Exception as e:
            logger.error(f"Failed to open file manager: {e}")
            return False

    def is_mounted(self, mount_point):
        """
        Check if mount point is currently mounted
        """
        try:
            result = subprocess.run(
                ['mountpoint', '-q', mount_point],
                timeout=5,
                check=False
            )
            return result.returncode == 0
        except OSError:
            return False
