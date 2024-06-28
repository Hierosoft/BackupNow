import json
import os

from logging import getLogger

logger = getLogger(__name__)


class Settings(dict):

    def __init__(self):
        dict.__init__(self)

    def load(self, path=None):
        if not path:
            if not self.path:
                raise ValueError("The path was not set.")
            path = self.path
        else:
            self.path = path
        if not os.path.isfile(path):
            logger.warning("[Settings load] There is no {}".format(path))
            return False
        logger.info("Loading {}".format(os.path.realpath(path)))
        with open(path, 'r') as stream:
            meta = json.load(stream)
            # Overlay (keep default values if not in file)
            for k, v in meta.items():
                self[k] = v

    def save(self):
        with open(self.path, 'w') as stream:
            json.dump(self, stream, sort_keys=True, indent=2)


settings = Settings()
