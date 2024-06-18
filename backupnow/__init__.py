#!/usr/bin/env python3
'''
This module is part of the BackupNow project
by Jake "Poikilos" Gustafson (c) 2021.
You should have a copy of the license.txt file, otherwise see
<https://github.com/Poikilos/BackupNow/blob/main/license.txt>.
'''
import os
import platform
import sys

from logging import getLogger

logger = getLogger(__name__)
LUID = "backupnow"  # Locally-unique id (Unix project name convention)

MODULE_DIR = os.path.dirname(os.path.realpath(__file__))
ASSETS_DIR = os.path.join(MODULE_DIR, "assets")

THEME_ROOT = os.path.join(ASSETS_DIR, "forestttktheme")

SEARCH_DIRS = [
    ASSETS_DIR,
    THEME_ROOT,
    os.path.join(THEME_ROOT, "forest-light"),
    os.path.join(THEME_ROOT, "forest-dark"),
]
sysdirs = {}
if platform.system() == "Windows":
    sysdirs['HOME'] = os.environ['USERPROFILE']
    sysdirs['APPDATA'] = os.environ['APPDATA']
    sysdirs['LOCALAPPDATA'] = os.environ['LOCALAPPDATA']
else:
    self = sysdirs  # See also Constants in hierosoft/sysdirs.py
    sysdirs['HOME'] = os.environ['HOME']
    if platform.system() == "Darwin":
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
        # XDG-like
        self['APPDATA'] = os.path.join(self['HOME'], ".config")
        self['LOCALAPPDATA'] = os.path.join(self['HOME'], ".local",
                                            "share")  # .net-like
        self['CACHES'] = os.path.join(self['HOME'], ".cache")


def echo0(*args, **kwargs):
    kwargs['file'] = sys.stderr
    print(*args, **kwargs)


def find_resource(name):
    if os.path.exists(name):
        return os.path.realpath(name)
    for parent in SEARCH_DIRS:
        sub_path = os.path.join(parent, name)
        if os.path.exists(sub_path):
            return sub_path
    return None


def get_sysdir_sub(key, leaf=None, luid=None):
    """Get a path specific to the program (luid) under a system folder.
    The subfolder specific to the luid, but not the leaf under that,
    will be created if the subfolder does not exist.

    Args:
        key (str): The name of the system directory such as "APPATA",
            "LOCALAPPATA", or "CACHES".
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


def getRelPath(root, sub_path):
    if not sub_path.startswith(root):
        raise RuntimeError(
            "Root \"{}\" was lost from sub_path \"{}\""
            .format(root, sub_path))
    return sub_path[len(root)+1:]  # +1 to avoid os.sep (slash)


def getRelPaths(path, sort=True, root=None):
    results = []
    if not path:
        raise ValueError("Path was blank.")
    if root is None:
        root = path

    if sort:
        sorted_subs = sorted(os.listdir(path),  key=lambda s: s.casefold())
        # casefold is more aggressive (will find more characters) than lower()
    else:
        sorted_subs = list(os.listdir(path))

    for sub in sorted_subs:
        sub_path = os.path.join(path, sub)
        if not os.path.isdir(sub_path):
            continue
        sub_rel = getRelPath(root, sub_path)
        results.append(sub_rel)
        results += getRelPaths(sub_path, sort=sort, root=root)

    for sub in sorted_subs:
        sub_path = os.path.join(path, sub)
        if not os.path.isfile(sub_path):
            continue
        sub_rel = getRelPath(root, sub_path)
        results.append(sub_rel)

    return results
