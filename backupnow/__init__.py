#!/usr/bin/env python3
'''
This module is part of the BackupNow project
by Jake "Poikilos" Gustafson (c) 2021.
You should have a copy of the license.txt file, otherwise see
<https://github.com/Poikilos/BackupNow/blob/main/license.txt>.
'''
import os
import sys

from datetime import datetime
from logging import getLogger

from backupnow.taskmanager import (
    TaskManager,
    TMTimer,
)
from backupnow.bnsettings import settings

logger = getLogger(__name__)

MODULE_DIR = os.path.dirname(os.path.realpath(__file__))
ASSETS_DIR = os.path.join(MODULE_DIR, "assets")

THEME_ROOT = os.path.join(ASSETS_DIR, "forestttktheme")

SEARCH_DIRS = [
    ASSETS_DIR,
    THEME_ROOT,
    os.path.join(THEME_ROOT, "forest-light"),
    os.path.join(THEME_ROOT, "forest-dark"),
]


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


class BackupNow:
    """Backend for BackupNow (manage operations & scheduling)
    Requires:
    - from backupnow.bnsettings import settings
    """
    def __init__(self):
        self.settings = None
        self.tasker = None
        self.error_cb = None

    def start(self, tk=None):
        """Load settings
        By calling load separately from init, the frontend can handle
        exceptions here & fix an instance.

        Args:
            tk (tkinter.Tk): A tk instance for using & starting timers.
        """
        self.settings = settings
        self.tasker = TaskManager()
        # if "tasks" not in settings  # always in settings even if file blank
        # for task in settings['tasks']:
        self.tasker.from_dicts(settings['tasks'])
        self.tk = tk
        self.busy = False
        self.error = None
        if self.tk:
            self.run_tk_timer()

    def run_tasks(self):
        tmtasks = self.tasker.get_ready_timers(datetime.now())
        if not tmtasks:
            self.show_error("There are no tasks scheduled.")

    def show_error(self, error):
        self.error = error
        if self.error_cb:
            self.error_cb(error)

    def run_tk_timer(self):
        self.tk.after(10000, self.run_tk_timer)
        if self.busy:
            return
        self.busy = True
        self.error = None
        try:
            self.run_tasks()
        except Exception as ex:
            self.error = "{}: {}".format(type(ex).__name__, ex)
        self.busy = False


if __name__ == "__main__":
    print("Oops! You ran the module.", file=sys.stderr)
