#!/usr/bin/env python3
"""
Manage an rsync operation.
"""

import sys
from backupnow.rsync import RSync

if sys.version_info.major >= 3:
    from tkinter import messagebox
else:
    import tkMessageBox as messagebox  # type: ignore


def changed(self, progress, message=None, error=None):
    print("changed({}, message=\"{}\", error=\"{}\")"
          "".format(progress, message, error))


def main():
    try:
        in_folder = sys.argv[1]
        out_folder = sys.argv[2]
    except IndexError:
        clause = ", but there were none."
        if len(sys.argv) > 1:
            clause = ", but there was only {}".format(sys.argv[1:])
        messagebox.showerror(
            "Error",
            "There must be both a source and a destination parameter"+clause
        )
        return 1

    rsync = RSync()
    result = rsync.run(in_folder, out_folder)
    if result:
        print("rsync completed without any errors.")
    else:
        print("rsync failed.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
