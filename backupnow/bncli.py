from __future__ import print_function

import argparse
import logging
import os
import sys
import time

from logging import getLogger

if __name__ == "__main__":
    MODULE_DIR = os.path.dirname(os.path.realpath(__file__))
    REPO_DIR = os.path.dirname(MODULE_DIR)
    sys.path.insert(0, REPO_DIR)

from backupnow import best_utc_now
from backupnow.bncore import BackupNow
from backupnow.taskmanager import (
    TMTimer,
)
from backupnow.jobswatcher import JobsWatcher

logger = getLogger(__name__)
# logger.setLevel(INFO)  # does nothing since there are no handlers.
#   (See basicConfig call in verbose case in main instead).
del logging


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
    enable_multithreading = False
    logger.info("args={}".format(args))
    # prefix = "[main] "
    core = BackupNow()  # type: BackupNow|None
    results = core.start()
    errors = results.get('errors')
    if errors:
        logger.error("BackupNow start errors:")
        for error in errors:
            logger.error("- {}".format(error))
    now = best_utc_now()
    logger.info("now_utc={}".format(now.strftime(TMTimer.dt_fmt)))
    # ^ main itself is too frequent--Don't use warning or higher importance.
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
                        .format(repr(args.backup_name)))
        if args.backup_name:
            timers = matching_timers
    else:
        logger.info("No timers are ready.")
        # ^ This will happen a lot.
    watcher = JobsWatcher(core)

    error = None
    if not timers:  # may be filtered by --backup-name arg
        return 0
    for name, timer in timers.items():
        watcher.add_timer(name, timer)
    if enable_multithreading:
        watcher.start()
        logger.warning("[main] Waiting for jobs to complete...")
        while not watcher.is_done():
            # watcher should set "ran" for when timer ran on its start time.
            time.sleep(1)
        error = watcher.error
    else:
        job_names = watcher.job_names()
        logger.warning("[main] Running {}...".format(job_names))
        event = watcher.run_sync()
        error = event.get('error')
    core.save()
    logger.info("[main] saved \"{}\"".format(core.settings.path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
