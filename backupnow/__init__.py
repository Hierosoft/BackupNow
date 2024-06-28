#!/usr/bin/env python3
'''
This module is part of the BackupNow project
by Jake "Poikilos" Gustafson (c) 2021.
You should have a copy of the license.txt file, otherwise see
<https://github.com/Poikilos/BackupNow/blob/main/license.txt>.

If using the CLI, run frequently so that scheduled events can be
checked.
'''
import argparse
import os
import socket
import sys

from datetime import datetime, UTC
import logging
from logging import getLogger
from pprint import pformat

if __name__ == "__main__":
    MODULE_DIR = os.path.dirname(os.path.realpath(__file__))
    REPO_DIR = os.path.dirname(MODULE_DIR)
    sys.path.insert(0, REPO_DIR)

from backupnow.taskmanager import (
    TaskManager,
    TMTimer,
)
from backupnow.bnsettings import settings
from backupnow.bnsysdirs import (
    get_sysdir_sub,
)

logger = getLogger(__name__)
# logger.setLevel(INFO)  # does nothing since there are no handlers.
#   (See basicConfig call in verbose case in main instead).
del logging

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
    default_settings_path = get_sysdir_sub('LOCALAPPDATA', "settings.json")

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
            logger.debug("Deserializing timers.")
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

        # settings._add_default_timerdict()
        # ^ preferred, changed if try_file found
        try_files = [
            "backupnow-{}.json".format(socket.gethostname()),
            "backupnow.json",
            BackupNow.default_settings_path,
        ]
        for try_file in try_files:
            if os.path.isfile(try_file):
                settings.load(try_file)
                # ^ sets settings.path
                break
        logger.info("Using {}".format(self.settings.path))

        settings["comment"] = ("detecting folder *and* file prevents copying"
                               " to another mount of the source!!")
        settings["comment2"] = ("Drives configured by BackupGoNow"
                                " (not BackupNow) contain"
                                " .BackupGoNow-settings.txt")
        settings['comment3'] = ("In this program, all timers should be"
                                " \"enabled\", but *jobs* may or may not be.")
        settings['comment4'] = ("All times should be in UTC"
                                " (time strings and timestamps).")
        if 'jobs' not in settings:
            settings['jobs'] = {}
        add_default = False
        if 'taskmanager' in settings:
            if not isinstance(settings['taskmanager'], dict):
                logger.error(
                    "Healing non-dict taskmanager={}({})"
                    .format(
                        type(self.settings.get('taskmanager')).__name__,
                        self.settings.get('taskmanager'),
                    )
                )
                del settings['taskmanager']
        if 'taskmanager' not in settings:
            add_default = True
            settings['taskmanager'] = {
                'timers': {}
            }
        if add_default:  # if not settings['taskmanager'].get('tasks'):
            logger.warning("Adding default timerdict.")
            self._add_default_timerdict()

        results = {'errors': []}
        if 'jobs' in settings:
            results = self.validate_jobs(event_template=results)
        else:
            logger.warning("No 'jobs' found in {}.".format(settings.path))
        if 'taskmanager' in settings:
            results = self.deserialize_timers(event_template=results)
            # ^ Can raise TypeError but type of 'taskmanager' is ensured above
            logger.info(
                "[BackupNow start] taskmanager={}"
                .format(settings['taskmanager']))
        else:
            # should be fixed above, so:
            raise NotImplementedError(
                "No 'taskmanager' found in {}."
                .format(settings.path)
            )

            # self.tm = TaskManager()
        logger.info("[BackupNow start] tm={}".format(self.tm.to_dict()))
        self.tk = tk
        self.busy = False
        if self.tk:
            logger.warning(
                "tk timer will only run when the window is open"
                " (`withdraw` prevents `after`)!")
            self.run_tk_timer()
        else:
            logger.debug(
                "There is no tk timer, "
                "so you must keep running run_tasks manually.")
        return results

    def _add_default_timerdict(self):
        self._add_timerdict(
            BackupNow.default_backup_name,
            BackupNow.default_timerdict(),
        )

    @staticmethod
    def default_timerdict():
        return {
            'time': "12:00",  # TODO: 16:00
            'span': "daily",
            'commands': ["*"],
            'enabled': True,
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
        tmtasks = self.tm.get_ready_timers(datetime.now(UTC))
        # ^ formerly datetime.utcnow()
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
    logger.info("Starting CLI")
    parser = argparse.ArgumentParser(
        prog='BackupNow',
        description=__doc__,
        # epilog='Text at the bottom of help'
    )
    parser.add_argument(
        '-n',
        '--backup-name',
        help=(
            "Only check timer(s) for a single job name in {settings_file}"
            .format(
                settings_file=BackupNow.default_settings_path,
            )
        ),
    )
    parser.add_argument(
        '-v',
        '--verbose',
        action='store_true',
        help="Enable verbose output.",
    )
    parser.add_argument(
        '-V',
        '--debug',
        action='store_true',
        help="Enable verbose info and debug output.",
    )
    # NOTE: --help is automatically generated (See parser.print_help())
    # parser.add_argument('-v', '--verbose', action='store_true')
    args = parser.parse_args()
    if args.verbose:
        import logging
        logging.basicConfig(level=logging.INFO)  # 20 (default is 30)
        del logging
    if args.debug:
        import logging
        logging.basicConfig(level=logging.DEBUG)  # 10 (default is 30)
        del logging
    logger.info("args={}".format(args))
    # prefix = "[main] "
    core = BackupNow()
    results = core.start()
    errors = results.get('errors')
    if errors:
        logger.error("BackupNow start errors:")
        for error in errors:
            logger.error("- {}".format(error))

    now = datetime.now(UTC)
    logger.warning(
        "now={}".format(now.strftime(TMTimer.dt_fmt)))

    timers = core.tm.get_ready_timers()
    if core.tm:
        logger.info("Timers (including non-ready):")
        if core.tm.timers:
            for name, timer in core.tm.timers.items():
                logger.info("{}:".format(name))
                if timer.ran:
                    logger.info(
                        "  ran (UTC): {}"
                        .format(timer.ran.strftime(TMTimer.dt_fmt)))

                logger.info(
                    "  time (UTC): {}"
                    .format(timer.utc_datetime(what_day=now)
                            .strftime(TMTimer.dt_fmt)))
                for k, v in timer.to_dict().items():
                    logger.info("  {}: {}".format(k, v))
        else:
            logger.warning("No timers")
    else:
        logger.error("No taskmanager")
    if timers:
        matching_timers = {}
        for name, timer in timers.items():
            logger.info("timer \"{}\" ready: {}".format(name, timer.to_dict()))
            # ^ {'time': '12:00', 'span': 'daily', 'commands': ['*']}
            if args.backup_name:
                if args.backup_name == name:
                    matching_timers[name] = timer
                    logger.info("- adding {} timer".format(name))
                else:
                    logger.warning(
                        "- skipped (not {})"
                        .format(pformat(args.backup_name)))
        if args.backup_name:
            timers = matching_timers
    else:
        logger.info("No timers are ready.")
        # ^ This will happen a lot.
    if timers:
        for name, timer in timers.items():
            logger.info("Running timer: {}".format(name))
            for command in timer.commands:
                if command == "*":
                    for job_name, job in core.settings['jobs'].items():
                        logger.info(
                            "- command={} job={}"
                            .format(command, job))
                        enabled = job.get('enabled')
                        if enabled is not None:
                            logger.info("  enabled: {}".format(enabled))
                        else:
                            enabled = True
                            logger.info(
                                "  enabled: {} (default)"
                                .format(enabled))
                        if enabled:
                            now = datetime.now(UTC)
                            logger.warning(
                                "- now={}".format(now.strftime(TMTimer.dt_fmt)))
                            # ^ formerly datetime.utcnow()
                            timer.ran = now
                            core.save()
                            logger.warning(
                                "Marked as ran {}"
                                .format(now.strftime(TMTimer.dt_fmt)))
                else:
                    job = core.settings['jobs'].get(command)
                    logger.warning("- command={} job={}".format(command, job))
    core.save()
    logger.info("[main] saved \"{}\"".format(core.settings.path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
