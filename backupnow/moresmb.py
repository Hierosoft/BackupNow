from __future__ import print_function
import os
import platform
import subprocess
import sys


def get_mounted_share(share, user=None, password=None):
    """Get a mountpoint from a share path

    Args:
        share (_type_): _description_
        user (_type_, optional): _description_. Defaults to None.
        password (_type_, optional): _description_. Defaults to None.

    Returns:
        str: Drive path (letter then colon on Windows)
    """
    for drive in os.listdrives():
        try_path = os.path.realpath(drive)
        if try_path == share:
            print('[get_mounted_share] {} == {}'.format(repr(try_path), repr(share)))
            return drive
        print('[get_mounted_share] {} != {}'.format(repr(try_path), repr(share)))
    return None


def mount_share(drive, share, user=None, password=None):
    # type: (str, str, str, str) -> None
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
            cmd = '[mount_share] net use {} /del /y'.format(drive)
            print(cmd)
            subprocess.call(cmd, shell=True)
            # ^ /y: auto-confirm (prevent hang on waiting to confirm)

        if os.path.isdir(drive):
            raise RuntimeError("Failed to unmap {}".format(drive))

        # Map the network drive
        cmd = '[mount_share] net use {} {}'.format(drive, share)
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
