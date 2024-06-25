from datetime import datetime
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

    def ready(self, now=None):
        """If the timer is ready.

        Args:
            now (datetime): The current time for comparison. Defaults to
                datetime.now().

        Returns:
            True if the scheduled time is now or before now.
        """
        if now is None:
            now = datetime.now()
        if self.span == "daily":
            # now.strftime(TMTimer.time_fmt)
            date_str = now.strftime(TMTimer.date_fmt)
            next_dt = datetime.strptime(
                date_str+" "+self.time,
                TMTimer.dt_fmt
            )
            if next_dt <= now:
                logger.warning("{} <= {}".format(
                    next_dt.strftime(TMTimer.dt_fmt),
                    now.strftime(TMTimer.dt_fmt),
                ))
            return next_dt <= now
        else:
            raise ValueError(
                "Unknown time span (expected daily): {}"
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
