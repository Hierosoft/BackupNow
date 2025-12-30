from __future__ import print_function
import os
import platform
import re
import subprocess
import sys

from backupnow import ALPHABET_UPPER

share_format_rc = re.compile(r'^\\\\[^\\]+\\[^\\]+$')
backslash_rc = re.compile(r'\\')


def is_share_format(share):
    # type (str) -> bool
    return bool(share_format_rc.match(share))


def find_nth_rc(rc, s, n=1):
    # type (re.Pattern, str, int|None) -> int
    """Starting index of nth match of the compiled regex in the string.

    Args:
        rc (re.Pattern): Compiled regular expression object (re.Pattern) to find.
        s (str): String to search in.
        n (int): Which occurrence to find (1-based index). Defaults to 1 (1st)

    Returns:
        int: The starting index of the nth match, or -1 if fewer than n
            matches exist.

    Raises:
        ValueError: If n is less than 1.
    """
    if n < 1:
        raise ValueError("n must be positive")

    for i, match in enumerate(rc.finditer(s), start=1):
        if i == n:
            return match.start()

    return -1


def get_mounted_share(share, user=None, password=None):
    # type: (str, (str|None), (str|None)) -> str|None
    """Get a mountpoint from a share path

    Args:
        share (str): Share path such as \\\\SERVER\\Share1 (start with 2
            backslashes, one and only one thereafter)
        user (str, optional): User name. Defaults to None.
        password (str, optional): Password. Defaults to None.

    Returns:
        str: Drive path (letter then colon on Windows)
    """
    assert isinstance(share, str)
    assert share.startswith("\\\\")
    assert is_share_format(share), \
        "Expected \\\\{{SERVER}}\\{{Share}} format, got {}".format(share)
    share_lower = share.lower()
    used_drives = list(os.listdrives())
    for drive in used_drives:
        try_path = os.path.realpath(drive)
        if try_path.lower() == share_lower:
            print('[get_mounted_share] {} == {}'
                  .format(repr(try_path), repr(share)))
            return drive
        print('[get_mounted_share] {} != {}'
              .format(repr(try_path), repr(share)))
    if platform.system() == "Windows":
        for letter in reversed(ALPHABET_UPPER[4:]):
            mount_path = letter + ":\\"
            if mount_path in used_drives:
                continue
            drive_path = letter + ":"
            mount_share(drive_path, share,
                        user=user, password=password)
            return drive_path
    return None


def mount_share(drive, share, user=None, password=None):
    # type: (str, str, (str|None), (str|None)) -> None
    if (user is None) != (password is None):
        if password:
            password = "*" * len(password)
        raise ValueError(
            "You must set both user and password (or neither),"
            " but got user={}, password={}"
            .format(user, password)
        )
    if platform.system() == "Windows":
        if not share.startswith("\\\\") or ("\\" not in share[2:]):
            raise ValueError("\\\\server\\share format is required, but got {}"
                             .format(share))
        if ((len(drive) not in (1, 2)) or (drive[1:] not in ("", ":"))
                or (not drive[:1].isalpha())):
            raise ValueError("Expected drive with/without colon, but got {}"
                             .format(drive))
        if len(drive) == 1:
            drive += ":"

        # Disconnect any existing drive first:
        if os.path.isdir(drive):
            if not os.path.realpath(drive).startswith("\\\\"):
                raise ValueError("{} () is not a network drive."
                                 .format(repr(drive),
                                         repr(os.path.realpath(drive))))
            cmd = 'net use {} /del /y'.format(drive)
            print("[mount_share] " + cmd)
            subprocess.call(cmd, shell=True)
            # ^ /y: auto-confirm (prevent hang on waiting to confirm)

        if os.path.isdir(drive):
            raise RuntimeError("Failed to unmap {}".format(drive))

        # Map the network drive
        cmd = 'net use {} {}'.format(drive, share)
        if (user is not None) and (password is not None):
            cmd += " /user:{} {}".format(user, password)
        print(cmd)
        subprocess.call(cmd, shell=True)

        if not os.path.isdir(drive):
            raise RuntimeError("Failed to map {} to {}"
                               .format(drive, share))

    else:
        raise NotImplementedError("mount_share is not implemented for {}"
                                  .format(platform.system()))


def split_share(unc_path):
    assert unc_path.startswith("\\\\")
    while unc_path.endswith("\\"):
        unc_path = unc_path[:-1]
    count = len(backslash_rc.findall(unc_path))
    assert count >= 3
    if count == 3:
        # Entire unc_path is a share, so do not split.
        assert is_share_format(unc_path)
        return (unc_path, "")
    fourth_backslash_idx = find_nth_rc(backslash_rc, unc_path, n=4)
    assert fourth_backslash_idx > -1
    return unc_path[:fourth_backslash_idx], unc_path[fourth_backslash_idx+1:]
