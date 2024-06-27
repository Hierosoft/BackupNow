import json
import os
import socket

from logging import getLogger

from backupnow.bnsysdirs import (
    get_sysdir_sub,
)

logger = getLogger(__name__)


class Settings(dict):
    default_backup_name = "default_backup"

    def __init__(self):
        dict.__init__(self)
        self["comment"] = ("detecting folder *and* file prevents copying to"
                           " another mount of the source!!")
        self["comment2"] = ("Drives configured by BackupGoNow (not BackupNow)"
                            " contain .BackupGoNow-settings.txt")
        self['comment3'] = ("In this program, all timers should be"
                            " \"enabled\", but *jobs* may or may not be.")
        self["jobs"] = {}
        self["timers"] = {}

    def _add_default_timerdict(self):
        self._add_timerdict(
            Settings.default_backup_name,
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
        if "timers" not in self:
            self["timers"] = {}
        self["timers"][key] = timerdict

    def load(self, path=None):
        if not path:
            if not self.path:
                raise ValueError("The path was not set.")
            path = self.path
        else:
            self.path = path
        if not os.path.isfile(path):
            return False
        logger.warning("Loading {}".format(os.path.realpath(path)))
        with open(path, 'r') as stream:
            meta = json.load(stream)
            # Overlay (keep default values if not in file)
            for k, v in meta.items():
                self[k] = v

    def save(self):
        with open(self.path, 'w') as stream:
            json.dump(self, stream, sort_keys=True, indent=2)


settings_path = get_sysdir_sub('LOCALAPPDATA', "settings.json")
settings = Settings()
settings._add_default_timerdict()
settings.path = settings_path  # preferred, changed if try_file found
try_files = {
    "backupnow-{}.json".format(socket.gethostname()),
    "backupnow.json",
    settings_path,
}
for try_file in try_files:
    if os.path.isfile(try_file):
        settings.load(try_file)
        break
