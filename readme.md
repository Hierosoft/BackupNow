# BackupNow
Do a graphical backup based on ~/exclude.txt then ~/include.txt (using rsync which excludes or includes based on the first command switch, so --exclude-from is used first).

rsync_with_progress.py is based on ronnymajani's July 4, 2021 comment on aerickson's 2011 version: <https://gist.github.com/aerickson/1283442> which is based on [Get total rsync progress using Python](https://libbits.wordpress.com/2011/04/09/get-total-rsync-progress-using-python/) by yegorich April 9, 2011.


## Related Projects
- rsyncprogress: only accepts piped input
  - rsyncprogress is based on [rsyncprogress.py](https://gist.github.com/JohannesBuchner/4d61eb5a42aeaad6ce90) (`wget https://gist.github.com/JohannesBuchner/4d61eb5a42aeaad6ce90/raw/4bdecaabd3242931a79a9eeb55b4616916e054f9/rsyncprogress.py`) by JohannesBuchner
  - A comment suggests using the progressbar-latest package to fulfill the progressbar dependency.


## Requirements
You must install rsync (BackupNow checks for it in the system PATH) using your operating system. For example, on Linux find the package using the "Software" application. See "Windows Requirements" for Windows instructions.

### Windows Requirements
- cwRsync
  - Go to <https://itefix.net/cwrsync>
  - Click "Free Rsync Client" tab
  - Click "Download" tab
  - Download the latest version for your CPU (usually 64-bit) such as <https://itefix.net/dl/free-software/cwrsync_6.3.0_x64_free.zip> (but choose the latest version to ensure you have the latest updates) and save it to your Downloads folder (automatically used usually if using Chrome/Firefox/etc.) so BackupNow can find it to automatically install it for you.


## Developer notes
### Windows
- The auto-installer (`RSync` constructor) extracts the zip file to `C:\PortableApps\cwRsync`
- If you download more than one version, the auto-installer selects the one with the latest version according to alphabetical sorting starting with "cwrsync_".
- The RSync class will look in the default path (`C:\PortableApps\cwRsync`) unless RSync.RSYNC_DIR is set before an RSync object is created. The "bin" directory must exist under the RSYNC_DIR. The "bin" folder must contain "rsync.exe".

### Tests
All tests can be discovered by pytest. From the directory (Leave out `--user` if you have activated a venv):
```bash
python3 -m pip install --user pytest
pytest
```
or on Windows, to avoid launching a GUI installer for Microsoft Python, do not call python3 but instead enable the **"py" launcher option** in the installer from [python.org](https://python.org) then:
```batch
py -3 -m pip install --user pytest
py -3 -m pytest
```