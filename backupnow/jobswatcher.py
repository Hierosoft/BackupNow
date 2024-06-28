import copy

from collections import OrderedDict
from datetime import datetime, UTC
from logging import getLogger

from backupnow.taskmanager import (
    TMTimer,
)

logger = getLogger(__name__)


class JobsWatcher:
    """Manage batch jobs and mark timers complete when done.

    Attributes:
        core (BackupNow): The main process containing .settings['jobs'].
        timer_jobs (dict[dict[list[dict]]]): Job dictionaries list for each timer name.
        timers (dict[TMTimer]): Named timer objects from TaskScheduler.

    Args:
        core (BackupNow): The main process containing .settings['jobs'].
    """
    def __init__(self, core):
        self.core = core
        self.timers = OrderedDict()
        self._clear_jobs()

    # def add_timer(self, name, timer):
    #     self.timers[name] = timer
    def _clear_jobs(self):
        self.done_job_count = 0
        self.timer_jobs = OrderedDict()
        self.timers_done = {}
        self._done = False
        self.error = None
        self._job_names = None

    def start(self):
        self._clear_jobs()
        for name, timer in self.timers.items():
            self._add_timer_jobs(name, timer)
        self._start_jobs_multithreaded()

    def job_names(self):
        return self._job_names

    def run_sync(self):
        self._clear_jobs()
        for name, timer in self.timers.items():
            self._add_timer_jobs(name, timer)
        return self.run_jobs_sync()

    def add_timer(self, name, timer):
        if self._job_names is None:
            self._job_names = []
        self.timers[name] = timer
        for command in timer.commands:
            self._job_names.append(command)

    def _add_timer_jobs(self, name, timer):
        core = self.core
        # self.timer_jobs[name] = []
        # for command in timer.commands:
        #     job = self.core.settings['jobs'].get(command)
        #     if job is not None:
        #         incomplete_job = copy.deepcopy(job)
        #         incomplete_job['status'] = None
        #         self.timer_jobs[name].append(incomplete_job)
        #     else:
        #         logger.error(
        #             "There is no command={} (expected job name)"
        #             .format(command))
        #         self.timer_jobs[name].append({'status': "done"})
        logger.info("Running timer: {}".format(name))
        event = {}
        for index, command in enumerate(timer.commands):
            if command == "*":
                for job_name, job in core.settings['jobs'].items():
                    logger.info(
                        "- command=*={} job={}"
                        .format(job_name, job))
                    self.add_job_if(name, job_name, job)
            else:
                job = core.settings['jobs'].get(command)
                event['task_name'] = name
                event['job_name'] = command
                event['command_index'] = index
                if job:
                    logger.warning("- command={} job={}".format(command, job))
                    self.add_job_if(name, command, job)
                else:
                    e_event = copy.deepcopy(event)
                    e_event['error'] = ("There no job named '{}'"
                                        .format(command))
                    self.progress(e_event)

    def run_jobs_sync(self):
        error = None
        event = {}
        for name, jobdict in self.timer_jobs.items():
            for job_name, jobs in jobdict.items():
                for i, job in enumerate(jobs):
                    event = self.core.run_job_sync(
                        job_name,
                        job,
                        progress_cb=lambda evt, nm=name, jn=job_name, idx=i:
                            self.progress_command(evt, nm, jn, idx)
                    )
                    error = event.get('error')
                    if error:
                        event['task_name'] = name
                        event['job_name'] = job_name
                        event['command_index'] = i
                        break
        event['status'] = "done"
        if error:
            event['error'] = error
            self.progress(event)
            return event
        return event

    def _start_jobs_multithreaded(self):
        for name, jobdict in self.timer_jobs.items():
            for job_name, jobs in jobdict.items():
                for i, job in enumerate(jobs):
                    self.core.start_job(
                        job_name,
                        job,
                        progress_cb=lambda evt, nm=name, jn=job_name, idx=i:
                            self.progress_command(evt, nm, jn, idx)
                    )

    def add_job_if(self, timer_name, job_name, job):
        """Add the job if it is enabled.

        Args:
            timer_name (str): The name of the timer.
            job_name (str): The name of the job in core, as specified as
                a command in the timer.
            job (dict): A job dict (such as usable by core start_job).
                Can either contain 'enabled' boolean or it is enabled by
                default. *Not* added if not enabled.

        Returns:
            bool: If the job was added (not None, not empty, and is
                enabled).
        """
        if not job:
            return False
        enabled = job.get('enabled')
        if enabled is not None:
            logger.info("  enabled: {}".format(enabled))
        else:
            enabled = True
            logger.info(
                "  enabled: {} (default)"
                .format(enabled))
        if enabled:
            self._add_job(timer_name, job_name)
            return True
        return False

    def _add_job(self, timer_name, job_name):
        self.timers_done[timer_name] = False
        if timer_name not in self.timer_jobs:
            self.timer_jobs[timer_name] = OrderedDict()
        if job_name not in self.timer_jobs[timer_name]:
            self.timer_jobs[timer_name][job_name] = []
        # index = len(self.timer_jobs[timer_name][job_name])
        job = self.core.settings['jobs'].get(job_name)
        if job is None:
            job = {}
        else:
            job = copy.deepcopy(job)
        job['status'] = None
        self.timer_jobs[timer_name][job_name].append(job)

    def timers_done_count(self):
        count = 0
        for _, this_done in self.timers_done.items():
            if this_done:
                count += 1
        return count

    def is_done(self):
        return self._done

    def check_total_status(self):
        count = 0
        done_count = 0
        for name, jobdict in self.timer_jobs.items():
            this_done_count = 0
            this_count = 0
            for job_name, jobs in jobdict.items():
                for job in jobs:
                    this_count += 1
                    count += 1
                    if job['status'] == "done":
                        done_count += 1
                        this_done_count += 1
            if this_done_count >= this_count:
                if not self.timers_done[name]:
                    self.timers_done[name] = True
                    logger.info("Finished {}/{} timer(s) (name={})".format(
                        self.timers_done_count(),
                        len(self.timers_done),
                        name,
                    ))
                    now = datetime.now(UTC)
                    self.timers[name].ran = now
                    self.core.save()
                    logger.info("Time ran was saved for {}.".format(name))
        if done_count > self.done_job_count:
            logger.info("Finished {}/{} job(s)".format(done_count, count))
            self.done_job_count = done_count
        if done_count >= count:
            return True
        return False

    def progress(self, event):
        name = event.get('task_name')
        job_name = event.get('job_name')
        index = event.get('command_index')
        error = event.get('error')
        if error:
            self.error = error
            logger.error(error)
        if event.get('status'):
            self.timer_jobs[name][job_name][index]['status'] = \
                event.get('status')
        if event.get('status') == 'done':
            now = datetime.now(UTC)
            logger.info(
                "- now={}".format(now.strftime(TMTimer.dt_fmt)))
            # ^ formerly datetime.utcnow()
            timer = self.timers[name]
            timer.ran = now
            self.core.save()
            logger.warning(
                "Marked {} as ran={}"
                .format(name, now.strftime(TMTimer.dt_fmt)))

            self._done = self.check_total_status()
        # else errors may occur before done, but wait for all (already logged?)

    def progress_command(self, event, name, job_name, index):
        event['task_name'] = name
        event['job_name'] = job_name
        event['command_index'] = index
        self.progress(event)
