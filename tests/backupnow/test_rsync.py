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

from backupnow import (  # noqa: E402
    getRelPaths,
    echo0,
)

from backupnow.rsync import (  # noqa: E402
    RSync,
    get_cygwin_path,
)

from tests.backupnow.test_backupgonowcmd import (  # noqa: E402, E501
    TestBackupGoNowCmd,
)


class TestRSync(unittest.TestCase):
    src = os.path.join(TEST_DATA_DIR, "source1")

    def __init__(self, *args, **kwargs):
        # super(TestBackupGoNowCmd).__init__()
        unittest.TestCase.__init__(self, *args, **kwargs)
        # self.src = TestBackupGoNowCmd.src
        self.source1_subtree = TestBackupGoNowCmd.source1_subtree

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

    def changed(self, progress, message=None, error=None):
        msg = ""
        if progress:
            msg += "\r"+str(round(progress*100))+"%"
        if message:
            echo0("message=\"{}\"".format(message))
        if error:
            echo0("error=\"{}\"".format(error))
        echo0(msg)

    def test_get_cygwin_path(self):
        self.assertEqual(
            get_cygwin_path("C:\\PortableApps"),
            "/cygdrive/c/PortableApps",
        )
        self.assertEqual(
            get_cygwin_path("D:\\Videos\\Projects"),
            "/cygdrive/d/Videos/Projects",
        )

    def test_existing_destination(self):
        src = os.path.join(TEST_DATA_DIR, "source1")
        dst = os.path.join(TEST_DATA_DIR, "destination-exists")
        if os.path.isdir(dst):
            echo0("Removing old \"{}\"".format(dst))
            shutil.rmtree(dst)
        os.mkdir(dst)
        # self.set_args(src, dst)
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
        # self.set_args(src, dst)
        rsync = RSync()
        rsync.changed = self.changed
        code = rsync.run(src, dst)
        if code != 0:
            raise RuntimeError("rsync failed with code {}".format(code))
        self.assertSameNames(src, dst)


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
    # self.set_args(src, dst)
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
