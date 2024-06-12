from __future__ import print_function

import platform
import re
import subprocess
import sys

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


class RSync:
    _TOTAL_SIZE_FLAG = 'total size is '

    def __init__(self):
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

        echo0('Dry run (rsync --dry-run):')

        cmd = 'rsync -az --stats --dry-run ' + src + ' ' + dst
        # shell = platform.system() != "Windows"
        shell = True
        proc = subprocess.Popen(
            cmd,
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

        echo0('Live run (rsync):', file=sys.stderr)

        cmd = 'rsync -avz  --progress ' + src + ' ' + dst
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
