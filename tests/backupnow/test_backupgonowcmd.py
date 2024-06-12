import os
import shutil
import sys
import unittest

TEST_SUB_DIR = os.path.dirname(os.path.realpath(__file__))

TEST_DATA_DIR = os.path.join(TEST_SUB_DIR, "data")

if __name__ == "__main__":
    TESTS_DIR = os.path.dirname(TEST_SUB_DIR)
    REPO_DIR = os.path.dirname(TESTS_DIR)
    sys.path.insert(0, REPO_DIR)

from backupnow import (
    getRelPaths,
    echo0,
)

from backupnow.rsync import (
    RSync,
)


class TestBackupGoNowCmd(unittest.TestCase):
    src = os.path.join(TEST_DATA_DIR, "source1")

    def __init__(self, *args, **kwargs):
        # super(TestBackupGoNowCmd).__init__()
        unittest.TestCase.__init__(self, *args, **kwargs)
        # self.src = TestBackupGoNowCmd.src
        self.source1_subtree = [
            "sub folder 1",
            os.path.join("sub folder 1", "some other text file.txt"),
            "image-from-rawpixel-id-2258263-jpeg.jpg",
            "some file with text.txt",
        ]

    def changed(self, progress, message=None, error=None):
        msg = ""
        if progress:
            msg += "\r"+str(round(progress*100))+"%"
        if message:
            echo0("message=\"{}\"".format(message))
        if error:
            echo0("error=\"{}\"".format(error))
        echo0(msg)

    def test_existing_destination(self):
        src = os.path.join(TEST_DATA_DIR, "source1")
        dst = os.path.join(TEST_DATA_DIR, "destination-exists")
        if os.path.isdir(dst):
            echo0("Removing old \"{}\"".format(dst))
            shutil.rmtree(dst)
        os.mkdir(dst)
        TestBackupGoNowCmd.set_args(src, dst)
        rsync = RSync()
        rsync.changed = self.changed
        code = rsync.run(src, dst)
        if code != 0:
            raise RuntimeError("rsync failed with code {}".format(code))
        self.assertSameNames(src, dst)

    def test_new_destination(self):
        src = self.src
        dst = os.path.join(TEST_DATA_DIR, "destination-new")
        if os.path.isdir(dst):
            echo0("Removing old \"{}\"".format(dst))
            shutil.rmtree(dst)
        TestBackupGoNowCmd.set_args(src, dst)
        rsync = RSync()
        rsync.changed = self.changed
        code = rsync.run(src, dst)
        if code != 0:
            raise RuntimeError("rsync failed with code {}".format(code))
        self.assertSameNames(src, dst)

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

    def assertSameNames(self, src, dst):
        self.assertEqual(
            getRelPaths(src),
            getRelPaths(dst)
        )

    @classmethod
    def set_args(cls, src, dst):
        if len(sys.argv) < 2:
            sys.argv.append(src)
        else:
            sys.argv[1] = src
        if len(sys.argv) < 3:
            sys.argv.append(dst)
        else:
            sys.argv[2] = dst
        if len(sys.argv) > 3:
            del sys.argv[3:]
        echo0("Using args: {}".format(sys.argv[1:]))


if __name__ == "__main__":
    unittest.main()

    # testcase = TestBackupGoNowCmd()
    # testcase.test_existing_destination()

    # src = os.path.join(TEST_DATA_DIR, "source1")
    # dst = os.path.join(TEST_DATA_DIR, "destination-exists")
    # if os.path.isdir(dst):
    #     echo0("Removing old \"{}\"".format(dst))
    #     shutil.rmtree(dst)
    # os.mkdir(dst)
    # TestBackupGoNowCmd.set_args(src, dst)
    # rsync = RSync()

    # def changed(self, progress, message=None, error=None):
    #     msg = ""
    #     if progress:
    #         msg += "\r"+str(round(progress*100))+"%"
    #     if message:
    #         echo0("message=\"{}\"".format(message))
    #     if error:
    #         echo0("error=\"{}\"".format(error))
    #     echo0(msg)

    # rsync.changed = changed
    # code = rsync.run(src, dst)
