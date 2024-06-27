from datetime import datetime, timedelta
from logging import getLogger

logger = getLogger(__name__)

INDEX_OF_DOW = {  # Day number as in strftime("%w")
    "Sunday": 0,
    "Monday": 1,
    "Tuesday": 2,
    "Wednesday": 3,
    "Thursday": 4,
    "Friday": 5,
    "Saturday": 6,
}


class TMTimer:
    """Check if a long-term scheduled event is ready to occur.
    It can be used in any program (since `command` is a string).

    Attributes:
        time (str): Time formatted as time_fmt ("%H:%M").
        day_of_week (int): Day of week where Sunday is 0 (dow_index_fmt
            "%w"). This is required only when span is "weekly".

    Arguments:
        timer (dict): A representation of a timer object.
    """
    time_fmt = "%H:%M"
    date_fmt = "%Y-%m-%d"
    dt_fmt = date_fmt + " " + time_fmt
    # dow_name_fmt = "%A"  # full name of day of week (first letter capital)
    dow_index_fmt = "%w"  # Number of day of week where Sunday is 0.

    def __init__(self, timerdict=None):
        self.time = None
        self.span = None
        self.commands = None
        self.errors = None
        self._base_keys = list(self.__dict__.keys())
        self.day_of_week = None
        self._all_keys = list(self.__dict__.keys())
        self._all_keys.remove("_base_keys")
        # print("keys={}".format(self._base_keys))
        if timerdict:
            if not isinstance(timerdict, dict):
                raise ValueError(
                    "Expected dict for timerdict, got {}"
                    .format(type(timerdict).__name__))
            results = self.from_dict(timerdict)
            errors = results.get('errors')
            if errors:
                self.errors = errors

    def __eq__(self, other):
        return self.to_dict() == other.to_dict()

    def validate_time(self, time):
        if time and (len(time) == 4) and time[1] == ":":
            if not time[2:].isnumeric() or not time[:1].isnumeric():
                raise ValueError("time is not valid: {}".format(time))
            logger.warning("Prepending 0 to {}".format(time))
            time = "0" + time
        if (not time) or (len(time) != 5) or (time[2] != ":"):
            raise ValueError("time is not valid: {}".format(time))
        if not time[3:].isnumeric() or not time[:2].isnumeric():
            raise ValueError("time is not valid: {}".format(time))
        if (int(time[:2]) > 23) or (int(time[3:]) > 59):
            raise ValueError("time is not valid: {}".format(time))
        return time

    @staticmethod
    def move_to_day_of_week(dt, day_of_week, reverse=False):
        """Get the closest date matching the day_of_week.

        Args:
            next_dt (datetime): Any datetime.
            day_of_week (int): A day of the week, 0 to 6 starting at
                Sunday.
            reverse (bool, optional): Whether to search backward.
                Defaults to False.

        Raises:
            ValueError: day_of_week is not a number 0 to 6.
            NotImplementedError: The day of week change was not
                calculated correctly.

        Returns:
            datetime: The datetime closest to next_dt matching day_of_week.
        """
        if day_of_week not in INDEX_OF_DOW.values():
            raise ValueError(
                "day_of_week was {} (expected {})"
                .format(day_of_week, list(INDEX_OF_DOW.values())))
        day_delta = timedelta(days=1)
        loops = 0
        while int(dt.strftime("%w")) != day_of_week:
            loops += 1
            if loops > 6:
                raise NotImplementedError(
                    "Could not convert day of {} to {}"
                    .format(dt.strftime(TMTimer.dt_fmt),
                            day_of_week))
            if reverse:
                dt += day_delta
            else:
                dt -= day_delta
        return dt

    def time_until(self, now=None):
        """Determine how much time passed since the scheduled time.

        Args:
            now (datetime, optional): The current time. Defaults to
                datetime.now().

        Raises:
            ValueError: If self.span is "weekly" but self.day_of_week is
                not 0 to 6.
            RuntimeError: If the date could not be determined based on
                the current date.

        Returns:
            timedelta: Time until the event is scheduled (positive), or
                if scheduled today and is already passed, either is 0 or
                negative.
        """
        if now is None:
            now = datetime.now()
        date_str = now.strftime(TMTimer.date_fmt)
        self.time = self.validate_time(self.time)
        next_dt = datetime.strptime(
            date_str+" "+self.time,
            TMTimer.dt_fmt
        )
        if self.span == "weekly":
            next_dt = TMTimer.move_to_day_of_week(next_dt, self.day_of_week)
        elif self.span == "daily":
            pass
        else:
            raise ValueError("span is not valid: {}".format(self.span))
        return next_dt - now

    def due(self, now=None, ran=None, quiet=True):
        """If the timer is due.
        If the timer never ran, it will only return True if the day of
        week matches if self.span is "weekly". Therefore, to run a
        missed timer from a different day for a new timer that never
        ran, there is not enough information: So if it never ran, either
        assume the timer is ready if you don't want to wait for that
        day, or set ran to a prior day or week (if span is "weekly").

        Args:
            now (datetime): The current time for comparison. Defaults to
                datetime.now().
            ran (datetime): The time the task ran last. You must use the
                value from "now" that was used when you ran the command!
                Otherwise the event may detect it was less than span ago
                and return False. Defaults to None.

        Returns:
            bool: True if the scheduled time is now or before now, but if
                ran is set & is in the same span, result it False.
        """
        # delta = self.time_until(now=now)  # negative if passed
        # return delta.total_seconds() <= 0.0
        # ^ Doesn't really work since may be wrong day...so:
        if now is None:
            now = datetime.now()
        span = self.span
        date_str = now.strftime(TMTimer.date_fmt)
        next_dt = datetime.strptime(
            date_str+" "+self.time,
            TMTimer.dt_fmt
        )
        prev_dt = datetime.strptime(
            date_str+" "+self.time,
            TMTimer.dt_fmt
        )
        if span == "weekly":
            prev_dt = TMTimer.move_to_day_of_week(prev_dt, self.day_of_week,
                                                  reverse=True)
            if ran:
                # delta = self.time_until(now=now)  # negative if passed
                # seconds = int(delta.total_seconds())
                # week_hours = 7 * 24
                # week_minutes = week_hours * 60
                # week_seconds = week_minutes * 60
                # *Must* return early in any nested case because now's
                #   day is used below ( and now.strftime("%w") !=
                #   next_dt.strftime("%w"))!
                # if (seconds * -1) >= week_seconds:
                #     return False
                return ran < prev_dt
                # ^ simple "<" works even if ran same day,
                #   since in that case, if it ran the same
                #   day, it would always be equal or greater
                #   than prev_dt since prev_dt is when it is
                #   scheduled (resulting in False).
            else:
                if int(now.strftime("%w")) != self.day_of_week:
                    # NOTE: ^ False if a day late, so set ran to handle that.
                    return False
                span = "daily"
        if span == "daily":
            # now.strftime(TMTimer.time_fmt)
            if not quiet:
                if next_dt <= now:
                    logger.warning("[due] {} <= {}".format(
                        next_dt.strftime(TMTimer.dt_fmt),
                        now.strftime(TMTimer.dt_fmt),
                    ))
            if ran:
                # seconds = int((now - ran).total_seconds())
                seconds = int((now - ran).total_seconds())
                day_minutes = 24 * 60
                day_seconds = day_minutes * 60
                if seconds >= day_seconds:
                    if not quiet:
                        logger.warning("[due] {}s >= day ({}s)".format(
                            seconds,
                            day_seconds,
                        ))
                    return True
            return next_dt <= now
        else:
            raise ValueError(
                "Unknown time span: {} (expected \"daily\" or \"weekly\")"
                .format(self.span))

    def to_dict(self):
        missing = self.missing()
        if missing:
            raise ValueError("Missing {}".format(missing))
        timerdict = {}
        for key in self.required_keys():
            timerdict[key] = self.__dict__[key]
        return timerdict

    def required_keys(self, timerdict=None, span=None):
        if timerdict is None:
            timerdict = self.__dict__
        if not span:
            span = timerdict.get('span')
        results = list(self._base_keys)
        if span and (span.lower() == "weekly"):
            results.append("day_of_week")
        return results

    def all_keys(self):
        return self._all_keys

    def missing(self, timerdict=None, span=None):
        if timerdict is None:
            timerdict = self.__dict__
        if not span:
            span = timerdict.get('span')
        missing = []
        for key in self.required_keys(timerdict=timerdict, span=span):
            if not timerdict[key]:
                missing.append(key)
        return missing

    def empty(self):
        return len(self.missing()) >= 1

    def from_dict(self, timerdict):
        """Configure this TMTimer using an equivalent timer dict.

        Args:
            timerdict (dict): A dictionary with the required_keys (pass
                'span' to required_keys to get all required keys since
                "weekly" span requires an additional key: 'day_of_week')

        Raises:
            ValueError: Blank timer (None, {}, or other "falsey" value).
            ValueError: Missing any required_keys.
            ValueError: Bay day of week str (not "Sunday" to "Saturday",
                case-insensitive).
            ValueError: Bad day of week int (not 0-6).
            ValueError: If time format is not like %H:%M (must be 0:00
                to 23:59). Example: ValueError: time data '24:00' does
                not match format '%H:%M'.
        """
        if not timerdict:
            raise ValueError("Blank timer={}".format(timerdict))
        if not isinstance(timerdict, dict):
            raise ValueError("Expected dict for TMTimer, got {}"
                             .format(type(timerdict).__name__))
        missing = self.missing(timerdict=timerdict, span=timerdict.get('span'))
        if missing:
            raise ValueError("Missing {} in {}".format(missing, timerdict))
        for key in self.required_keys(span=timerdict.get('span')):
            setattr(self, key, timerdict[key])
        if self.day_of_week:
            if isinstance(self.day_of_week, str):
                dow_index = INDEX_OF_DOW.get(self.day_of_week.title())
                if dow_index is None:
                    raise ValueError(
                        "Bad day_of_week={}. Expected name or number: {}"
                        .format(self.day_of_week, INDEX_OF_DOW)
                    )
                self.day_of_week = dow_index
            elif isinstance(self.day_of_week, int):
                if self.day_of_week not in INDEX_OF_DOW.values():
                    raise ValueError(
                        "Bad day_of_week={}. Expected name or number: {}"
                        .format(self.day_of_week, INDEX_OF_DOW)
                    )
        # Example:
        # then = datetime.strptime("16:00", "%H:%M")
        # datetime.datetime(1900, 1, 1, 16, 0)
        _ = datetime.strptime(self.time, TMTimer.time_fmt)  # ValueError if bad


class TaskManager:
    """Manage generic timers than can be used for any program.
    """
    def __init__(self):
        self.timers = {}
        self.enabled = True

    def to_subdict(self, settings, key="taskmanager"):
        settings[key] = self.to_dict()

    def to_dict(self):
        tmdict = {}
        tmdict['enabled'] = self.enabled
        tmdict['timers'] = {}
        if self.timers is None:
            raise ValueError("Timers were not ready. See from_dict errors.")
        for name, timer in self.timers:
            tmdict['timers'][name] = timer.to_dict()
        return tmdict

    def from_dict(self, tmdict):
        if not isinstance(tmdict, dict):
            raise ValueError("Expected dict for taskmanager, got {}"
                             .format(type(tmdict).__name__))
        results = {'errors': []}
        self.enabled = tmdict.get('enabled')
        if self.enabled not in (True, False):
            logger.warning("'enabled' was not set for taskmanager."
                           " Defaulting to True.")
            self.enabled = True
        if self.timers:
            logger.warning("from_dicts is overwriting timers: {}"
                           .format(self.timers))
        timers = {}
        if tmdict.get('timers'):
            # try:
            for name, timerdict in tmdict['timers'].items():
                timers[name] = TMTimer(timerdict=timerdict)
            # except Exception as ex:
            #     results['errors'].append("{}: {}".format(type(ex).__name__, ex))
        if results['errors']:
            self.timers = None  # error state (triggers exception on to_dict
            #   to prevent erasing corrupt settings)
        else:
            self.timers = timers
        return results

    def get_ready_timers(self, now=None):
        if now is None:
            now = datetime.now()
        results = {}
        for name, timer in self.timers.items():
            if timer.due(now=now):
                results[name] = timer
        return results

    def add_timer_dict(self, name, timerdict):
        if name in self.timers:
            raise KeyError("Already has {}".format(name))
        timer = TMTimer(timerdict=timerdict)
        self.timers[name] = timer

    def add_timer(self, name, timer):
        if not isinstance(timer, TMTimer):
            raise TypeError(
                "Expected TMTimer got {} {}"
                .format(type(timer).__name__, timer))
        if name in self.timers:
            raise KeyError("Already has {}".format(name))
        self.timers[name] = timer


if __name__ == "__main__":
    print("Oops, you ran a module.")
