"""
Things here are analogous to the moreplatform submodule of
https://github.com/Hierosoft/hierosoft.git (or other submodules for
off-topic functions such as startswith_any) so if hierosoft becomes
required by backupnow, eliminate this (bnplatform) submodule from
backupnow.
"""
from __future__ import print_function
import os
import platform
import subprocess
from typing import Callable
import psutil
import sys

from backupnow.bnlogging import emit_cast


ALPHABET_LOWER = "abcdefghijklmnopqrstuvwxyz"
ALPHABET_UPPER = ALPHABET_LOWER.upper()
ALPHABETICAL = ALPHABET_UPPER + ALPHABET_LOWER


def _listdrives():
    results = []
    if sys.version_info.major >= 3 and sys.version_info.minor >= 12:
        return os.listdrives()
    # if platform.system() == "Windows":
    #     for letter in ALPHABET_UPPER:
    #         drive_path = letter + ":\\"  # mimic Python3.12+ os.listdrives()
    #         if os.path.exists(drive_path):
    #             results.append(drive_path)

    for partition in psutil.disk_partitions(all=False):
        # print("Device: {}".format(partition.device))  # such as C:\
        # print("Mount point: {}".format(partition.mountpoint))  # such as C:\
        # print("File system type: {}".format(partition.fstype))  # eg NTFS
        results.append(partition.mountpoint)

    return results


def get_volume_info(path, shell_run=None):
    # type: (str, Callable|None) -> dict[str, str|int|None]
    # 2026-01-05
    # https://grok.com/share/c2hhcmQtMg_dd839dc5-ce00-43e9-b657-655bf66be306
    """Get information about the volume containing the given path.

    On Windows, uses win32api.GetVolumeInformation() when available.
    On Unix-like systems (Linux, macOS), uses os.statvfs() and external
    commands to gather equivalent data where possible.

    Args:
        path (str): Any path on the volume to query.
        shell_run (Callable): Alternate command run function such as for
            testing (See tests folder). Defaults to subprocess.run.

    Returns:
        dict: Volume information with the following keys:

        - 'name' (str): Volume label if available, otherwise a fallback
          basename.
        - 'serial_number' (int/long or None): Volume serial number
          (Windows only).
        - 'max_component_length' (int): Maximum filename component length.
        - 'sys_flags' (int): Filesystem-specific flags.
        - 'filesystem' (str): Filesystem type name.
        - 'free_bytes' (int/long or None): Bytes free on the volume
          (None if unavailable).

    Raises:
        OSError: If the path does not exist.
        ImportError: On Windows if pywin32 is not installed.
    """
    if not os.path.exists(path):
        raise OSError("Path does not exist: {}".format(path))

    root_path = os.path.abspath(path)
    if not root_path.endswith(os.sep):
        root_path += os.sep

    system = platform.system()

    if system == "Windows" or not hasattr(os, 'statvfs'):
        # ^ `or not hasattr` is necessary since environment variables
        #   are not set correctly in VSCode on Windows for some reason.
        try:
            import win32api  # type: ignore
            (vol_name, serial, max_comp, flags,
             fs_name) = win32api.GetVolumeInformation(root_path)

            # Get free space using GetDiskFreeSpaceEx (pywin32)
            try:
                import win32file  # type: ignore
                (_, free_bytes, total_bytes) = win32file.GetDiskFreeSpaceEx(
                    root_path)
            except Exception:
                free_bytes = None

            return {
                'name': (vol_name or
                         os.path.basename(os.path.dirname(root_path)) or ''),
                'serial_number': serial,
                'max_component_length': max_comp,
                'sys_flags': flags,
                'filesystem': fs_name,
                'free_bytes': free_bytes,
            }
        except ImportError:
            raise ImportError(
                "pywin32 is required on Windows for full functionality")

    # Non-Windows: Linux / macOS
    st = os.statvfs(root_path)
    max_comp = st.f_namemax
    flags = st.f_flag
    free_bytes = st.f_frsize * st.f_bavail  # block size * free blocks

    fs_type = None  # type: str|None
    vol_name = None  # type: str|None
    mount_point = None  # type: str|None

    try:
        # df -T gives filesystem type reliably
        df_out = subprocess.check_output(
            ["df", "-T", root_path], stderr=subprocess.STDOUT)
        lines = df_out.splitlines()
        parts = lines[-1].split()
        fs_type = parts[1]
        device = parts[0]
        mount_point = parts[-1]

        # Try blkid for volume label (Linux)
        try:
            if shell_run is None:
                shell_run = subprocess.check_output
            label_out = shell_run(
                ["blkid", "-o", "value", "-s", "LABEL", device],
                stderr=subprocess.DEVNULL)
            label = label_out.strip()
            if label:
                vol_name = label.decode('utf-8') if isinstance(label, bytes) else label
        except (subprocess.CalledProcessError, OSError):
            pass

        # macOS: diskutil info
        if system == "Darwin" and vol_name is None:
            try:
                if shell_run is None:
                    shell_run = subprocess.check_output
                info_out = shell_run(
                    ["diskutil", "info", device])
                for line in info_out.splitlines():
                    if line.startswith(b"Volume Name:") or \
                            b"Volume Name:" in line:
                        vol_name = line.split(b":", 1)[1].strip()
                        if sys.version_info.major >= 3:
                            if isinstance(vol_name, bytes):
                                vol_name = vol_name.decode('utf-8')
                        break
            except (subprocess.CalledProcessError, OSError):
                pass
    except Exception:
        fs_type = "unknown"

    # Fallback name if nothing better found
    if mount_point:
        clean_mp = mount_point.rstrip(os.sep)
        name = vol_name or os.path.basename(os.path.dirname(clean_mp)) or ''
    else:
        name = vol_name or ''

    return {
        'name': name,
        'serial_number': None,
        'max_component_length': max_comp,
        'sys_flags': flags,
        'filesystem': fs_type or "unknown",
        'free_bytes': free_bytes,
    }


def listdrives(exclude_drives=[]):
    if not isinstance(exclude_drives, list):
        raise TypeError(
            'You must provide drive letters to exclude'
            ' in the form of a startswith list, such as ["A", "C"],'
            ' ["A:" & "C:"] or ["/sys", "/lib", "/usr/lib"] but got {}'
            .format(emit_cast(exclude_drives)))
    results = []
    if platform.system() == "Windows":
        # Convert exclusions to uppercase (non-destructively: make new list)
        tmp = exclude_drives
        exclude_drives = []
        for i in range(len(tmp)):
            exclude_drives.append(tmp[i].upper())

    for drive in _listdrives():
        if platform.system() == "Windows":
            # Convert drive to upper to make check case-insensitive
            #   (No need for case_insensitive since made each exclude upper)
            if startswith_any(drive.upper(), exclude_drives):
                continue
        else:
            if startswith_any(drive, exclude_drives):
                continue
        results.append(drive)

    return results


def startswith_any(haystack, needles, case_insensitive=False):
    for exclude in needles:
        if case_insensitive:
            if haystack.upper().startswith(exclude.upper()):
                return True
        else:
            if haystack.startswith(exclude):
                return True
    return False
