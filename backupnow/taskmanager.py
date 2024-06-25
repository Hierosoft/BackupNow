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
        self._base_keys = list(self.__dict__.keys())
        self.day_of_week = None
        self._all_keys = list(self.__dict__.keys())
        self._all_keys.remove("_base_keys")
        # print("keys={}".format(self._base_keys))
        if timerdict:
            self.from_dict(timerdict)

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
            if self.day_of_week not in INDEX_OF_DOW.values():
                raise ValueError("day_of_week was {} (expected {})"
                                 .format(self.day_of_week,
                                         list(INDEX_OF_DOW.values())))
            day_delta = timedelta(days=1)
            loops = 0
            while int(next_dt.strftime("%w")) != self.day_of_week:
                loops += 1
                if loops > 6:
                    raise RuntimeError(
                        "Could not convert day of {} to {}"
                        .format(next_dt.strftime(TMTimer.dt_fmt),
                                self.day_of_week))
                next_dt += day_delta
        elif self.span == "daily":
            pass
        else:
            raise ValueError("span is not valid: {}".format(self.span))
        return next_dt - now

    def ready(self, now=None):
        """If the timer is ready.

        Args:
            now (datetime): The current time for comparison. Defaults to
                datetime.now().

        Returns:
            True if the scheduled time is now or before now.
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
        if span == "weekly":
            if not isinstance(self.day_of_week, int):
                raise TypeError("Expected int for day_of_week but got {}({})"
                                .format(type(self.day_of_week).__name__,
                                        self.day_of_week))
            if int(now.strftime("%w")) != self.day_of_week:
                # ^ *Must* return early because now's day is used below
                #   ( and now.strftime("%w") != next_dt.strftime("%w"))!
                return False
            span = "daily"
        if span == "daily":
            # now.strftime(TMTimer.time_fmt)
            # if next_dt <= now:
            #     logger.warning("{} <= {}".format(
            #         next_dt.strftime(TMTimer.dt_fmt),
            #         now.strftime(TMTimer.dt_fmt),
            #     ))
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
    def __init__(self):
        self.timers = {}

    def to_subdict(self, settings, key):
        for name, timer in self.timers.items():
            settings[key][name] = timer.to_dict()

    def to_dict_tree(self):
        results = {}
        for name, timer in self.timers:
            results[name] = timer.to_dict()
        return results

    def from_dict_tree(self, timerdicts):
        if self.timers:
            logger.warning("from_dicts is overwriting timers: {}"
                           .format(self.timers))
        self.timers = {}
        for name, timerdict in timerdicts.items():
            self.timers[name] = TMTimer(timerdict=timerdict)

    def get_ready_timers(self, now=None):
        if now is None:
            now = datetime.now()
        results = {}
        for name, timer in self.timers.items():
            if timer.ready(now=now):
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
