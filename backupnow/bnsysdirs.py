import os
import platform

from logging import getLogger

logger = getLogger(__name__)
LUID = "backupnow"  # Locally-unique id (by "Unix project name" convention)

sysdirs = {}  # type: dict[str, str]
if platform.system() == "Windows":
    sysdirs['HOME'] = os.environ['USERPROFILE']
    sysdirs['APPDATA'] = os.environ['APPDATA']
    sysdirs['LOCALAPPDATA'] = os.environ['LOCALAPPDATA']
else:
    self = sysdirs  # See also Constants in hierosoft/sysdirs.py
    sysdirs['HOME'] = os.environ['HOME']
    if platform.system() == "Darwin":
        # macOS
        sysdirs['APPDATA']
        self['APPDATA'] = os.path.join(
            self['HOME'],
            ".config"
        )  # .net Core-like
        self['LOCALAPPDATA'] = os.path.join(self['HOME'], ".local",
                                            "share")  # .net Core-like
        self['CACHES'] = os.path.join(self['HOME'], "Library",
                                      "Caches")  # .net Core-like
    else:
        # Linux or other using XDG standards is assumed in this case
        self['APPDATA'] = os.path.join(self['HOME'], ".config")
        self['LOCALAPPDATA'] = os.path.join(self['HOME'], ".local",
                                            "share")  # .net-like
        self['CACHES'] = os.path.join(self['HOME'], ".cache")
    del self


def get_sysdir_sub(key, leaf=None, luid=LUID):
    """Get a path specific to the program (luid) under a system folder.
    The subfolder specific to the luid, but not the leaf under that,
    will be created if the subfolder does not exist.

    Args:
        key (str): The name of the system directory such as "APPDATA",
            "LOCALAPPDATA", or "CACHES".
        leaf (str, optional): Set if you want a subdirectory. Defaults to None.

    Returns:
        str: Either this modules's unique subfolder under the specified
            key system directory, or the deeper leaf path under that if
            leaf is specified.
    """
    my_system_sub = os.path.join(sysdirs[key], luid)
    if not os.path.isdir(my_system_sub):
        os.makedirs(my_system_sub)
    if not leaf:
        logger.info("No leaf was specified for {}."
                    .format(my_system_sub))
        return my_system_sub
    return os.path.join(my_system_sub, leaf)


def local_data_path(leaf=None, luid=LUID):
    """Get a persistent local path (specific to computer not just user)
    The local app data path subfolder specific to the luid, but not the
    leaf under that, will be created if it does not exist.

    Args:
        leaf (str, optional): Set if you want a subdirectory. Defaults to None.

    Returns:
        str: Either this modules's unique subfolder under the OS' local
            app data, or the deeper leaf path under that if leaf is
            specified.
    """
    return get_sysdir_sub('LOCALAPPDATA', leaf=leaf, luid=luid)


def cache_path(leaf=None, luid=LUID):
    """Get a cache path.
    The cache subfolder specific to the luid, but not the leaf under
    that, will be created if it does not exist.

    Args:
        sub (str, optional): Set if you want a subdirectory. Defaults to None.

    Returns:
        str: Either this modules's unique subfolder under OS's cache
            folder, or the deeper leaf path under that if leaf is
            specified.
    """
    return get_sysdir_sub('CACHES', leaf=leaf, luid=luid)
