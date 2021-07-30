import subprocess
import re
import sys

try:
    try:
        import tkMessageBox as messagebox
    except ModuleNotFoundError:
        # Python 3
        try:
            from tkinter import messagebox
        except ModuleNotFoundError:
            raise Exception("You must install the python3-tk package"
                            " such as via:\n"
                            "  sudo apt-get install python3-tk")
            exit(1)
    except NameError as ex:
    if "ModuleNotFoundError" in str(ex):
        # There is no ModuleNotFoundError in Python 2, so trying to
        # use it will raise a NameError.
        raise Exception("You are using Python 2"
                        " but this program requires Python 3.")
    else:
        raise ex
class Rsync:
    def __init__(self):
        pass
    
    def run(src, dst, exclude_from=None, include_from=None,
            exclude_from=None):
        print('Dry run:')

        try:
            in_folder = sys.argv[1]
            out_folder = sys.argv[2]
        except IndexError:
            clause = ", but there were none."
            if len(sys.argv) > 1:
                clause = ", but there was only {}".format(sys.argv[1:])
            messagebox.showerror("Error", ("There must be both a source and"
                                           " a destination parameter"+clause))
            exit(1)


        cmd = 'rsync -az --stats --dry-run ' + in_folder + ' ' + out_folder

        proc = subprocess.Popen(cmd,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )

        output, err = proc.communicate()

        mn = re.findall(r'Number of files: (\d+)', output.decode('utf-8'))
        total_files = int(mn[0])

        print('Number of files: ' + str(total_files))

        print('Real rsync:')

        cmd = 'rsync -avz  --progress ' + in_folder + ' ' + out_folder
        proc = subprocess.Popen(cmd,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )

        while True:
            output = proc.stdout.readline().decode('utf-8')
            if 'to-check' in output:
                m = re.findall(r'to-check=(\d+)/(\d+)', output)
                progress = (100 * (int(m[0][1]) - int(m[0][0]))) / total_files
                sys.stdout.write('\rDone: ' + str(progress) + '%')
                sys.stdout.flush()
                if int(m[0][0]) == 0:
                    break

        print('\rFinished')
