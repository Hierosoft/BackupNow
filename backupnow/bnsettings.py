from collections import OrderedDict
import json
import os

from logging import getLogger

logger = getLogger(__name__)


class Settings(dict):

    def __init__(self):
        dict.__init__(self)
        self.path = None  # type: str|None

    def load(self, path=None):
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

    def save(self, path=None):
        if path:
            self.path = path
        if not self.path:
            raise ValueError("The path for Settings must be set for save.")
        with open(self.path, 'w') as stream:
            json.dump(self, stream, sort_keys=True, indent=2)


settings = Settings()
