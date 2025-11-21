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
            device_name = re.sub(r'[^a-zA-Z0-9_-]', '', device_name)

            if not device_name:
                device_name = "Device"

            # Add UDID
            device_name = f"{device_name}_{device.udid}"
            mount_point = self.mount_base_dir / device_name

            # Check if mount point exists
            if mount_point.exists():
                if self.is_mounted(str(mount_point)):
                    logger.info("Device already mounted at: %s", mount_point)
                    return True, str(mount_point), None

                # Directory exists but not mounted (stale mount)
                logger.warning("Stale mount detected, cleaning up: %s", mount_point)
                self.unmount_device(str(mount_point), force=True)

                try:
                    mount_point.rmdir()
                    logger.info("Cleaned up stale mount point")
                except OSError as e:
                    logger.error("Failed to remove stale mount point: %s", e)
                    return False, None, "Failed to clean stale mount point"

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

    def unmount_device(self, mount_point, force=False):
        """
        Unmount device.
        Returns success status, error message
        """
        try:
            logger.info(f"Unmounting {Path(mount_point).name}")

            # Sync pending writes to device
            try:
                subprocess.run(['sync'], timeout=5, check=False)
            except Exception:
                pass

            # Try graceful unmount first
            result = subprocess.run(
                ['fusermount', '-u', str(mount_point)],
                capture_output=True,
                text=True,
                timeout=15,
                check=False
            )

            if result.returncode == 0:
                logger.info("Unmount successful (graceful)")
                try:
                    Path(mount_point).rmdir()
                except OSError:
                    pass
                return True, None

            # Graceful failed - check if busy (unless force=True)
            if not force:
                error_msg = result.stderr.strip() if result.stderr else "Unmount failed"

                # Check if device is busy
                if "busy" in error_msg.lower() or "target is busy" in error_msg.lower():
                    logger.warning(f"Device is busy: {error_msg}")
                    return False, "Device is busy. Close all files and try again."

            # Force unmount
            logger.warning("Graceful unmount failed, forcing...")
            result = subprocess.run(
                ['fusermount', '-uz', str(mount_point)],
                capture_output=True,
                text=True,
                timeout=15,
                check=False
            )

            if result.returncode == 0:
                logger.info("Unmount successful (forced)")
                try:
                    Path(mount_point).rmdir()
                except OSError:
                    pass
                return True, None
            else:
                error_msg = result.stderr.strip() if result.stderr else "Unmount failed"
                logger.error(f"Force unmount failed: {error_msg}")
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

    def cleanup_stale_mounts(self):
        """
        Unmount any stale mounts from previous sessions.
        """
        if not self.mount_base_dir.exists():
            return

        try:
            # Use os.listdir instead of iterdir to avoid stat calls
            mount_dirs = os.listdir(self.mount_base_dir)
        except OSError:
            return

        for mount_name in mount_dirs:
            mount_path = self.mount_base_dir / mount_name

            try:
                result = subprocess.run(
                    ['fusermount', '-uz', str(mount_path)],
                    timeout=1,
                    capture_output=True,
                    check=False
                )

                if result.returncode == 0:
                    logger.info(f"Unmounted stale mount: {mount_name}")

                try:
                    os.rmdir(mount_path)
                    logger.debug(f"Removed mount directory: {mount_name}")
                except OSError:
                    pass

            except subprocess.TimeoutExpired:
                logger.warning(f"Timeout unmounting {mount_name}")
            except Exception as e:
                logger.warning(f"Error cleaning up {mount_name}: {e}")
