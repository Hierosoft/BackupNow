#!/usr/bin/env python3
'''
This module is part of the BackupNow project
by Jake "Poikilos" Gustafson (c) 2021.
You should have a copy of the license.txt file, otherwise see
<https://github.com/Poikilos/BackupNow/blob/main/license.txt>.
'''
import os
import socket
import sys

from datetime import datetime
from logging import getLogger

from backupnow.taskmanager import (
    TaskManager,
    # TMTimer,
)
from backupnow.bnsettings import settings
from backupnow.bnsysdirs import (
    get_sysdir_sub,
)

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

    Attributes:
        error_cb (function): The code that creates BackupNow can set
            this to a function that accepts a dict such as `{'error':
            error}`.
    """
    default_backup_name = "default_backup"

    def __init__(self):
        self.settings = None
        self.tm = None
        self.error_cb = None
        self.job = None
        self.ratio = None
        self.busy = 0
        self.errors = []

    @property
    def jobs(self):
        return settings['jobs']

    def save(self):
        self.serialize_timers()
        self.settings.save()

    def load(self):
        self.settings.load()
        results = self.deserialize_timers()
        errors = results.get('errors')
        if errors:
            for error in errors:
                self.errors.append(error)

    def deserialize_timers(self, event_template=None):
        if event_template is not None:
            results = event_template
            if 'errors' not in results:
                results['errors'] = []
        else:
            results = {'errors': []}

        tmdict = self.settings.get('taskmanager')
        if tmdict:
            if not isinstance(tmdict, dict):
                raise TypeError("Expected dict for taskmanager, got {}"
                                .format(type(tmdict).__name__))
            self.tm = TaskManager()
            return self.tm.from_dict(tmdict)
        return results  # no "error" (tmdict is blank though)

    def serialize_timers(self):
        self.settings['taskmanager'] = self.tm.to_dict()

    def validate_operation(self, opdict):
        results = {}
        errors = []
        if 'source' not in opdict:
            errors.append("missing 'source'")

        if errors:
            results['errors'] = errors
        return results

    def validate_jobs(self, event_template=None):
        if event_template is not None:
            results = event_template
            if 'errors' not in results:
                results['errors'] = []
        else:
            results = {'errors': []}
        jobs = settings.get('jobs')
        if not jobs:
            return results
        for name, job in jobs.items():
            if not name:
                results['errors'].append("There is a blank job name.")
            if 'operations' not in job:
                results['errors'].append("Job '{}' has no operations."
                                         .format(name))
                continue
            for i, operation in enumerate(job['operations']):
                op_results = self.validate_operation(operation)
                op_errors = op_results.get('errors')
                if op_errors:
                    for op_error in op_errors:
                        results['errors'].append("operation {} {}"
                                                 .format(i+1, op_error))
        return results

    def start(self, tk=None):
        """Load settings
        By calling load separately from init, the frontend can handle
        exceptions here & fix an instance.

        Args:
            tk (tkinter.Tk): A tk instance for using & starting timers.
        """
        self.settings = settings  # self.tm is set by deserialize_timers

        settings_path = get_sysdir_sub('LOCALAPPDATA', "settings.json")
        # settings._add_default_timerdict()
        # ^ preferred, changed if try_file found
        try_files = {
            "backupnow-{}.json".format(socket.gethostname()),
            "backupnow.json",
            settings_path,
        }
        for try_file in try_files:
            if os.path.isfile(try_file):
                settings.load(try_file)
                # ^ sets settings.path
                break
        echo0("Using {}".format(settings_path))

        settings["comment"] = ("detecting folder *and* file prevents copying"
                               " to another mount of the source!!")
        settings["comment2"] = ("Drives configured by BackupGoNow"
                                " (not BackupNow) contain"
                                " .BackupGoNow-settings.txt")
        settings['comment3'] = ("In this program, all timers should be"
                                " \"enabled\", but *jobs* may or may not be.")
        if 'jobs' not in settings:
            settings['jobs'] = {}
        add_default = False
        if 'taskmanager' not in settings:
            add_default = True
            settings['taskmanager'] = {
                'timers': {}
            }
        if add_default:  # if not settings['taskmanager'].get('tasks'):
            self._add_default_timerdict()
        self.deserialize_timers()

        results = {'errors': []}
        if "jobs" in settings:
            results = self.validate_jobs(event_template=results)
        else:
            logger.warning("No 'jobs' found in {}.".format(settings.path))
        if "taskmanager" in settings:
            results = self.deserialize_timers(event_template=results)
        else:
            logger.warning("No 'taskmanager' found in {}."
                           .format(settings.path))
            self.tm = TaskManager()
        self.tk = tk
        self.busy = False
        if self.tk:
            logger.warning("tk timer will only run when the window is open"
                           " (`withdraw` prevents `after`)!")
            self.run_tk_timer()
        else:
            logger.warning("There is no tk timer, "
                           "so you must keep running run_tasks manually.")
        return results

    def _add_default_timerdict(self):
        self._add_timerdict(
            BackupNow.default_backup_name,
            self.default_timerdict(),
        )

    def default_timerdict(self):
        return {
            "time": "12:00",  # TODO: 16:00
            "span": "daily",
            "commands": ["*"],
        }

    def _add_timerdict(self, key, timerdict):
        """This is private since you should use taskmanager instead
        and use taskmanager.to_subdict(settings, "timers")
        """
        if 'taskmanager' not in self.settings:
            self.settings['taskmanager'] = {}
        if 'timers' not in self.settings['taskmanager']:
            self.settings['taskmanager']['timers'] = {}
        self.settings['taskmanager']['timers'][key] = timerdict

    def stop_sync(self):
        """Stop synchronously
        (wait until threads are cancelled before return)
        """
        return True

    def run_tasks(self):
        tmtasks = self.tm.get_ready_timers(datetime.now())
        if not tmtasks:
            self.show_error("There are no tasks scheduled.")

    def show_error(self, error):
        self.error = error
        if self.error_cb:
            self.error_cb(error)

    def run_tk_timer(self):
        self.tk.after(10000, self.run_tk_timer)
        if self.busy:
            logger.warning("tk timer event: busy")
            return
        else:
            logger.warning("tk timer event: run_tasks...")
        self.busy = True
        self.error = None
        # try:
        self.run_tasks()
        # except Exception as ex:
        #     self.error = "{}: {}".format(type(ex).__name__, ex)
        self.busy = False


def main():
    # echo0("Starting CLI")
    echo0("Oops! You ran the module.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
