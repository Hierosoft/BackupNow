import os
import sys
import unittest

TEST_SUB_DIR = os.path.dirname(os.path.realpath(__file__))

TEST_DATA_DIR = os.path.join(TEST_SUB_DIR, "data")

if __name__ == "__main__":
    TESTS_DIR = os.path.dirname(TEST_SUB_DIR)
    REPO_DIR = os.path.dirname(TESTS_DIR)
    sys.path.insert(0, REPO_DIR)

from backupnow import (  # noqa: E402
    getRelPaths,
    echo0,
)


class TestBackupGoNowCmd(unittest.TestCase):
    src = os.path.join(TEST_DATA_DIR, "source1")

    source1_subtree = [  # same in test_rsync.py
        "sub folder 1",
        os.path.join("sub folder 1", "some other text file.txt"),
        "image-from-rawpixel-id-2258263-jpeg.jpg",
        "some file with text.txt",
    ]

    def __init__(self, *args, **kwargs):
        # super(TestBackupGoNowCmd).__init__()
        unittest.TestCase.__init__(self, *args, **kwargs)
        # self.src = TestBackupGoNowCmd.src

    def test_getRelPaths(self):
        src = self.src
        got_subtree = getRelPaths(src)
        try:
            self.assertEqual(
                got_subtree,
                self.source1_subtree
            )
        except AssertionError:
            echo0("expected: {}".format(self.source1_subtree))
            echo0("got: {}".format(got_subtree))
            raise


if __name__ == "__main__":
    unittest.main()
