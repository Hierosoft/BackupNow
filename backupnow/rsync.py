from __future__ import print_function

import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import zipfile

from logging import getLogger

logger = getLogger(__name__)

if sys.version_info.major >= 3:
    try:
        from tkinter import messagebox
    except ModuleNotFoundError:
        raise Exception("The rsync module requires the python3-tk"
                        " package to be installed such as via:\n"
                        "  sudo apt-get install python3-tk")
else:
    import tkMessageBox as messagebox  # noqa: F401  # type: ignore


def echo0(*args, **kwargs):
    kwargs['file'] = sys.stderr
    print(*args, **kwargs)


def shlex_quote(value):
    """Mimic shlex_quote from six"""
    if platform.system() == "Windows":
        # For some reason shlex uses single quotes in Windows which fails with
        # "The filename, directory name, or volume label syntax is incorrect."
        # so instead add double quotes manually:
        if " " in value:
            return '"' + value + '"'
        else:
            return value
    if hasattr(shlex, 'quote'):
        # requires Python 3.3
        return shlex.quote(value)
    else:
        import pipes
        return pipes.quote(value)


def get_cygwin_path(path):
    """Replace {letter}: with /cygdrive/{letter}

    This uses path required by cygwin programs such as cwRsync.

    To avoid:
    > The source and destination cannot both be remote.
    > rsync error: syntax or usage error (code 1) at main.c(1415) [Receiver=3.3.0]

    Args:
        path (_type_): _description_
    """
    if (len(path) > 1) and (path[1] == ":"):
        path = "/cygdrive/" + path[0].lower() + path[2:].replace("\\", "/")
    return path


if platform.system() == "Windows":
    HOME = os.environ['USERPROFILE']
else:
    HOME = os.environ['HOME']


class RSync:
    _TOTAL_SIZE_FLAG = 'total size is '
    RSYNC_ARCHIVE = None

    @classmethod
    def detect_archive(cls):
        _found_archive = None
        DOWNLOADS = os.path.join(HOME, "Downloads")
        for sub in sorted(os.listdir(DOWNLOADS)):
            if sub.lower().startswith("cwrsync_"):
                # such as "cwrsync_6.3.0_x64_free.zip"
                if _found_archive:
                    echo0('Warning: using newer {} not {}'
                          .format(sub, _found_archive))
                _found_archive = os.path.join(DOWNLOADS, sub)
        return _found_archive

    RSYNC_DIR = "C:\\PortableApps\\cwRsync"
    # TODO: ^ bin subfolder may need to be in PATH! See cwrsync.cmd for example
    # RSYNC_BIN = os.path.join(RSYNC_DIR, "cwrsync.cmd")  # only a template!
    RSYNC_BIN = os.path.join(RSYNC_DIR, "bin", "rsync.exe")

    def __init__(self):
        self.rsync_path = shutil.which("rsync")
        # ^ `which` requires Python 3.3
        #   (Uses os.environ['PATH'], or falls back to os.defpath)
        if not self.rsync_path:
            if platform.system() == "Windows":
                if os.path.isfile(RSync.RSYNC_BIN):
                    self.rsync_path = RSync.RSYNC_BIN
                else:
                    RSync.RSYNC_ARCHIVE = RSync.detect_archive()
                    if not RSync.RSYNC_ARCHIVE:
                        raise RuntimeError(
                            "BackupGoNow RSync requires the rsync command"
                            " in the PATH or custom location {} containing"
                            " {}"
                            " (Set RSync.RSYNC_DIR before using RSync"
                            " constructor to change custom location)."
                            .format(RSync.RSYNC_DIR, RSync.RSYNC_BIN)
                        )

                    with zipfile.ZipFile(RSync.RSYNC_ARCHIVE, 'r') as zip_ref:
                        logger.warning(
                            "Extracting {} to {}..."
                            .format(RSync.RSYNC_ARCHIVE, RSync.RSYNC_DIR))
                        zip_ref.extractall(RSync.RSYNC_DIR)
                    logger.warning("Done extracting.")
                    if os.path.isfile(RSync.RSYNC_BIN):
                        self.rsync_path = RSync.RSYNC_BIN
                    else:
                        logger.error(
                            "Extracting didn't result in {}"
                            .format(RSync.RSYNC_BIN))
            else:
                raise RuntimeError(
                    "BackupGoNow RSync requires the rsync command in the PATH."
                )
        self._reset()

    def _reset(self):
        self.progress = 0.0  # The progress from 0.0 to 1.0
        self.totalSize = sys.float_info.max
        self.error_str = ""

    def changed(self, progress, message=None, error=None):
        echo0("Your program should overload this function."
              " It accepts a value from 0.0 to 1.0, and optionally,"
              " a message and an error:\n"
              "changed({}, message=\"{}\", error=\"{}\")"
              "".format(progress, message, error))

    def run(self, src, dst, exclude_from=None, include_from=None,
            exclude=None, include=None):
        '''Start and monitor a single rsync operation.
        Args:
            dst (str): This is the backup destination. The folder name of src
                (but not the full path) will be added under dst.

        Returns:
            int: 0 if good, otherwise error code (positive is for an
                error code returned by rsync, negative is for internal
                error).
        '''
        src = get_cygwin_path(src)
        dst = get_cygwin_path(dst)

        sep = "/"  # "/"" even on windows due to cwRsync requiring /cygdrive/!
        #   (See get_cygwin_path, which does not use os.path.sep (replaces all)

        cmd = (shlex_quote(self.rsync_path)
               + ' -asz --stats --dry-run ' + src + sep + ' ' + dst)
        # -s: --secluded-args "use the protocol to safely send the args"
        # ^ long arg is "--protect-args" in older versions, so always use -s!
        # ^ must add sep to src so rsync doesn't create extra sub-subfolder!
        echo0('Dry run ({}):'.format(cmd))
        my_env = os.environ.copy()
        RSYNC_BIN_DIR = os.path.dirname(self.rsync_path)
        if platform.system() == "Windows":
            my_env['CWRSYNCHOME'] = os.path.dirname(RSYNC_BIN_DIR)
            working_dir = my_env['CWRSYNCHOME']
            # ^ contains home/%USERNAME%/.ssh (See readme)
            # Based on the following lines from cwrsync's included cwrsync.cmd:
            # SET CWRSYNCHOME=%~dp0
            # REM Make cwRsync home as a part of system PATH to find required DLLs
            # SET PATH=%CWRSYNCHOME%\bin;%PATH%
            my_env["PATH"] = RSYNC_BIN_DIR + os.pathsep + my_env["PATH"]
        else:
            working_dir = RSYNC_BIN_DIR

        # FIXME: ^ Test self.rsync_path with spaces.
        # shell = platform.system() != "Windows"
        shell = True
        proc = subprocess.Popen(
            cmd,
            cwd=working_dir,
            env=my_env,
            shell=shell,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        code = None
        total_files = -1

        # output, err = proc.communicate()
        # ^ "...since communicate closes the stdout and stdin and
        # stderr, you can not read or write after you called
        # communicate" -<https://stackoverflow.com/a/16769956/4541104>
        # Therefore:
        self.error_str = ""
        while True:
            output = None
            error = None
            if proc.stdout:
                output = proc.stdout.readline().decode('utf-8')
            if proc.stderr:
                error = proc.stderr.readline().decode('utf-8')
            # if output is not None:
            #     echo0("dry_run output: '''{}'''"
            #           "".format(output.decode('utf-8')))'
            if error:
                self.error_str += error
                echo0("dry_run error: '''{}'''"
                      "".format(self.error_str))
                if "is not recognized as" in error:
                    raise FileNotFoundError("rsync")
                else:
                    raise NotImplementedError("unknown error: {}".format(error))
                # If rsync was not found, Windows shows (literally 2 lines):
                # 'rsync' is not recognized as an internal or external command,
                # operable program or batch file.

            mn = re.findall(r'Number of files: (\d+)', output)
            if mn:
                total_files = int(mn[0])
                echo0("total_files={}".format(total_files))
            else:
                if output:
                    echo0("Unknown output=\"{}\"".format(output))
                pass
                # echo0("Number of files: not found (mn={}) in output={}"
                #       .format(mn, output))
                # total_files = -1

            code = proc.returncode
            if proc.returncode is None:
                code = proc.poll()
            if code is not None:
                if code != 0:
                    # output, err = proc.communicate()
                    # ^ this would return b'', None
                    echo0("Returning {} after undetected output={}, error={}."
                          .format(code, output, error))
                    return code
                break
            # else:
            #     echo0("There was no return code but output was blank.")
            #     return -3
        # if None, the process hasn't terminated yet.
        del code

        echo0('Number of files: ' + str(total_files))

        cmd = (shlex_quote(self.rsync_path)
               + ' -asvz  --progress ' + src + sep + ' ' + dst)
        # ^ must add sep to src so rsync doesn't create extra sub-subfolder!
        echo0('\n\n========\nLive run ({}):'.format(cmd))

        proc = subprocess.Popen(
            cmd,
            shell=shell,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self._reset()
        while True:
            output = proc.stdout.readline().decode('utf-8')
            error = proc.stderr.readline().decode('utf-8')
            sizeFlagI = -1

            if error:
                self.error_str += error
                if 'skipping non-regular file' in error:
                    pass
                else:
                    self.changed(
                        None,
                        error="{}".format(error.strip())
                    )
                    return -1

            if output is None:
                return -2

            sizeFlagI = output.find(RSync._TOTAL_SIZE_FLAG)
            if sizeFlagI >= 0:
                sizeStartI = sizeFlagI + len(RSync._TOTAL_SIZE_FLAG)
                sizeEndI = output.find(" ", sizeStartI)
                if sizeEndI >= 0:
                    sizeStr = output[sizeStartI:sizeEndI].strip()
                    sizeStr = sizeStr.replace(",", "")
                    self.totalSize = float(int(sizeStr))
                    echo0("self.totalSize: {}"
                          "".format(self.totalSize))
            elif output.startswith("sent"):
                continue
            elif 'to-check' in output:
                m = re.findall(r'to-check=(\d+)/(\d+)', output)
                # progress = \
                #     (100 * (int(m[0][1]) - int(m[0][0]))) / total_files
                self.progress = ((int(m[0][1]) - int(m[0][0]))) / total_files
                self.changed(self.progress)
                # sys.stdout.write('\rDone: ' + str(self.progress) + '%')
                # sys.stdout.flush()
                if int(m[0][0]) == 0:
                    break
            elif 'sending incremental file list' in output:
                self.progress = 0.0
            elif len(output.strip()) == 0:
                code = proc.returncode
                if proc.returncode is None:
                    code = proc.poll()
                if code is not None:
                    if code == 0:
                        # ^ 0 is good
                        return 0
                    else:
                        return code
                else:
                    echo0("There was no return code but output was blank.")
                    break
                # if None, the process hasn't terminated yet.
            else:
                print("unknown output: '''{}'''".format(output))

        return 0
