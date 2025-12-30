from __future__ import print_function
import os
import sched
import socket
import sys
import threading
import time

import logging
from logging import getLogger
from typing import Callable

from backupnow.bnsettings import Settings

if __name__ == "__main__":
    MODULE_DIR = os.path.dirname(os.path.realpath(__file__))
    REPO_DIR = os.path.dirname(MODULE_DIR)
    sys.path.insert(0, REPO_DIR)

from backupnow import best_utc_now
from backupnow.taskmanager import (
    TaskManager,
)
from backupnow.bnsysdirs import (
    get_sysdir_sub,
)

logger = getLogger(__name__)
# logger.setLevel(INFO)  # does nothing since there are no handlers.
#   (See basicConfig call in verbose case in main instead).
del logging

NOT_ON_DESTINATION = "Not on destination."


class BackupNow:
    """Backend for BackupNow (manage operations & scheduling)

    Attributes:
        error_cb (function): The code that creates BackupNow can set
            this to a function that accepts a dict such as `{'error':
            error}`.
    """
    default_backup_name = "default_backup"
    default_settings_path = get_sysdir_sub('LOCALAPPDATA', "settings.json")
    TIMER_JOB_NAME = "timer"

    def __init__(self):
        self.settings = Settings()  # type: Settings
        self.tm = TaskManager()  # type: TaskManager
        self.enabled = False  # type: bool
        self.error_cb = None  # type: Callable
        # self.job = None
        self.ratio = None
        self.busy = 0
        self.errors = []  # type: list[str]
        self.threads = {}  # type: dict[str, threading.Thread]
        self.scheduler = sched.scheduler(time.time, time.sleep)
        self.run_level = 1

    @property
    def jobs(self):
        return self.settings['jobs']

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
            self.tm = TaskManager()  # type: TaskManager
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
        jobs = self.settings.get('jobs')
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
        # self.settings = settings  # type: Settings
        # self.tm is set by deserialize_timers

        # settings._add_default_timerdict()
        # ^ preferred, changed if try_file found
        try_files = [
            "backupnow-{}.json".format(socket.gethostname()),
            "backupnow.json",
            BackupNow.default_settings_path,
        ]
        for try_file in try_files:
            if os.path.isfile(try_file):
                self.settings.load(try_file)
                # ^ sets settings.path
                break
        if self.settings.path:
            logger.warning("Using {}".format(self.settings.path))
        else:
            self.settings.path = BackupNow.default_settings_path
            logger.warning("Defaulting to (new) {}".format(self.settings.path))

        settings = self.settings
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

        # tm is set by serialize_timers or deserialize_timers:
        logger.info("[BackupNow start] tm={}".format(self.tm.to_dict()))
        self.tk = tk
        self.busy = False
        if self.tk:
            logger.warning(
                "tk timer will only run when the window is open"
                " (`withdraw` prevents `after`)!")
            self.run_tk_timer()
        else:
            # logger.debug(
            #     "There is no tk timer, "
            #     "so you must keep running run_tasks manually.")
            self.run_timer()
        self.enabled = True
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

    def disable(self):
        self.enabled = False

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
        self.run_level = 0
        # TODO: Respect run_level to allow canceling jobs.
        wait_time = 1
        max_wait_time = 20
        while self.threads:
            keys = list(self.threads.keys())
            alive_keys = []
            for key in keys:
                if not self.threads[key].is_alive():
                    logger.warning(
                        "Warning: stop_sync is removing orphaned thread {}"
                        .format(key))
                    del self.threads[key]
                else:
                    alive_keys.append(key)
            if self.threads:
                logger.warning(
                    "Waiting {}s for {}"
                    .format(wait_time, alive_keys))
                time.sleep(wait_time)
                wait_time += 2
                if wait_time > max_wait_time:
                    wait_time = max_wait_time
        return True

    def start_job(self, job_name, job, progress_cb=None):
        if not progress_cb:
            raise ValueError("Set the progress_cb to a method.")
        thread = None
        event = {}
        if job_name in self.threads:
            thread = self.threads[job_name]
            if not thread or not thread.is_alive():
                logger.warning("Discarding orphaned thread name={}"
                               .format(job_name))
                del self.threads[job_name]
                thread = None
        if thread is not None:
            event = {
                'error': "{} is already running.".format(job_name),
                'done': True,  # Since this instance is done
            }
            return event
        thread = threading.Thread(
            target=self.run_job_sync,
            args=(job_name, job),
            kwargs={'progress_cb': progress_cb},
        )
        self.threads[job_name] = thread
        thread.start()
        return event

    def run_job_sync(self, job_name, job, progress_cb=print):
        # type (str, BNJob, Callable) -> dict
        event = {}
        logger.warning("[_run_job] job={}".format(job))
        time.sleep(1)  # FIXME: for debug only
        logger.warning("[_run_job] done {}".format(job_name))
        event['done'] = True
        progress_cb(event)
        return event

    def run_tasks(self):
        tmtasks = self.tm.get_ready_timers(best_utc_now())
        # ^ formerly datetime.utcnow()
        if not tmtasks:
            self.show_error("There are no tasks scheduled.")

    def show_error(self, error):
        self.error = error
        if self.error_cb:
            self.error_cb(error)

    def run_timer_sync(self, job_name=None):
        """Run the timer.

        Args:
            job_name (str, optional): Set this to
                BackupNow.TIMER_JOB_NAME if running as a thread in
                self.threads. When the loop terminates, the entry in
                self.threads will be deleted. Defaults to None.
        """
        while self.run_level > 0:
            # NOTE: There is also schedule (from pypi,
            #   as opposed to Python's scheduler) used as follows:
            #   schedule.every(10).seconds.do(run_threaded, job)
            self.on_timer()
        if job_name:
            if job_name in self.threads:
                del self.threads[job_name]

    def run_timer(self):
        job_name = BackupNow.TIMER_JOB_NAME
        thread = None
        if job_name in self.threads:
            thread = self.threads[job_name]
            if not thread or not thread.is_alive():
                logger.warning("Discarding orphaned thread name={}"
                               .format(job_name))
                del self.threads[job_name]
                thread = None
        if thread is not None:
            event = {
                'error': "{} is already running.".format(job_name),
                'done': True,  # Since this instance is done
            }
            return event
        thread = threading.Thread(
            target=self.run_timer_sync,
            # args=(job_name, job),
            kwargs={'job_name': job_name},
        )

    def run_tk_timer(self):
        raise DeprecationWarning(
            "This method is useless since the Tk window must be open"
            " for timer events to run.")
        # self.tk.after(10000, self.run_tk_timer)
        # self.on_timer()

    def on_timer(self):
        if self.busy:
            logger.warning("on_timer: busy")
            return
        else:
            logger.warning("on_timer: run_tasks...")
        self.busy = True
        self.error = None
        # try:
        self.run_tasks()
        # except Exception as ex:
        #     self.error = "{}: {}".format(type(ex).__name__, ex)
        self.busy = False

