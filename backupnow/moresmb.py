import os
import platform
import subprocess


def mount_share(drive, share, user=None, password=None):
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
        if (len(drive) not in (1, 2)) or (drive[1:] not in ("", ":")):
            raise ValueError("Expected drive with/without colon, but got {}"
                             .format(drive))
        if len(drive) == 1:
            drive += ":"

        # Disconnect any existing drive first:
        if os.path.isdir(drive):
            subprocess.call('net use {} /del /y'.format(drive), shell=True)
            # ^ /y: auto-confirm (prevent hang on waiting to confirm)

        if os.path.isdir(drive):
            raise RuntimeError("Failed to unmap {}".format(drive))

        # Map the network drive
        cmd = 'net use {} {}'.format(drive, share)
        if (user is not None) and (password is not None):
            cmd += " /user:{} {}".format(user, password)
        subprocess.call(cmd, shell=True)

        if not os.path.isdir(drive):
            raise RuntimeError("Failed to map {} to {}"
                               .format(drive, share))

    else:
        raise NotImplementedError("mount_share is not implemented for {}"
                                  .format(platform.system()))
