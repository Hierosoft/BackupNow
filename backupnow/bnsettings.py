from collections import OrderedDict
import json
import os

from logging import getLogger
import shutil

logger = getLogger(__name__)


class Settings(dict):

    def __init__(self):
        dict.__init__(self)
        self.path = None  # type: str|None

    def load(self, path=None):
        # type: (str|None) -> bool
        if not path:
            if not self.path:
                raise ValueError("The path for Settings must be set for load.")
            path = self.path
        else:
            self.path = path
        if not os.path.isfile(path):
            logger.warning("[Settings load] There is no {}".format(path))
            return False
        logger.info("Loading {}".format(os.path.realpath(path)))
        with open(path, 'r') as stream:
            meta = json.load(stream, object_pairs_hook=OrderedDict)
            # Overlay (keep default values if not in file)
            for k, v in meta.items():
                self[k] = v
        return True

    def save(self, path=None):
        if path:
            self.path = path
        if not self.path:
            raise ValueError("The path for Settings must be set for save.")
        tmp_path = self.path + ".tmp"
        with open(tmp_path, 'w') as stream:
            json.dump(self, stream, sort_keys=True, indent=2)
        moved_path = None
        if os.path.isfile(self.path):
            moved_path = self.path + ".old"
            shutil.move(self.path, moved_path)
            # ^ Move it before deleting it, in case only file not dir is
            #   writeable (which would cause move(tmp_path, self.path)
            #   to fail).
        shutil.move(tmp_path, self.path)
        if moved_path:
            os.remove(moved_path)
