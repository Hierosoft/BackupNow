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
