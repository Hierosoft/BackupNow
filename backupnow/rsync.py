from __future__ import print_function
import subprocess
import re
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


class RSync:
    _TOTAL_SIZE_FLAG = 'total size is '

    def __init__(self):
        self._reset()

    def _reset(self):
        self.progress = 0.0  # The progress from 0.0 to 1.0
        self.totalSize = sys.float_info.max

    def changed(self, progress, message=None, error=None):
        print("Your program should overload this function."
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

        print('Dry run:')

        cmd = 'rsync -az --stats --dry-run ' + src + ' ' + dst

        proc = subprocess.Popen(
            cmd,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )

        output, err = proc.communicate()
        # if output is not None:
        #     print("dry_run output: '''{}'''"
        #           "".format(output.decode('utf-8')))
        if err is not None:
            print("dry_run error: '''{}'''"
                  "".format(err.decode('utf-8')))

        mn = re.findall(r'Number of files: (\d+)', output.decode('utf-8'))
        total_files = int(mn[0])

        print('Number of files: ' + str(total_files))

        print('Real rsync:')

        cmd = 'rsync -avz  --progress ' + src + ' ' + dst
        proc = subprocess.Popen(
            cmd,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self._reset()
        while True:
            output = proc.stdout.readline().decode('utf-8')
            error = proc.stderr.readline().decode('utf-8')
            sizeFlagI = -1

            if (error is not None) and (len(error) > 0):
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
                    print("self.totalSize: {}"
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
                    print("There was no return code but output was blank.")
                    break
                # if None, the process hasn't terminated yet.
            else:
                print("unknown output: '''{}'''".format(output))

        return 0
