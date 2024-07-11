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

## Known Issues
This section only covers issues that have only workarounds and not fixes. View other issues at <https://github.com/Poikilos/BackupNow/issues> before reporting new issues.

From the setproctitle documentation:
> A few environment variables can be used to customize the module behavior:
>
> SPT_NOENV
> Avoid clobbering /proc/PID/environ.
>
> On many platforms, setting the process title will clobber the environ
> memory area. os.environ will work as expected from within the Python
> process, but the content of the file /proc/PID/environ will be
> overwritten. If you require this file not to be broken you can set the
> SPT_NOENV environment variable to any non-empty value: in this case the
> maximum length for the title will be limited to the length of the
> command line.



## Developer notes
### Windows
- The auto-installer (`RSync` constructor) extracts the zip file to `C:\PortableApps\cwRsync`
- If you download more than one version, the auto-installer selects the one with the latest version according to alphabetical sorting starting with "cwrsync_".
- The RSync class will look in the default path (`C:\PortableApps\cwRsync`) unless RSync.RSYNC_DIR is set before an RSync object is created. The "bin" directory must exist under the RSYNC_DIR. The "bin" folder must contain "rsync.exe".
- The `get_pid_path()` file tracks the PID. This is necessary to avoid multiple copies running, since listing processes doesn't help: process name is just python.exe even with both `setprocname` and setting `multiprocessing.current_process().name`

Using rsync from a remote source requires an ssh key

Based on <https://www.ch.cam.ac.uk/computing/sync-cwrsync>:
```
bin\ssh-keygen -q -t rsa -f cwrsync -N ""
```
Move the cwrsync private key file to the folder C:\PortableApps\cwRsync\home\%USERNAME%\.ssh.

> Copy the file cwrsync.pub to the .ssh subdirectory of your Linux login directory on the fileserver. If this directory does not exist create it and the authorized_keys file as follows. Append the cwrsync.pub public key file to the file authorized_keys. From a Linux command line, for example,
```bash
ssh %USERNAME%@<group>-fs
pwd
mkdir .ssh
chmod 700 .ssh
cd .ssh
cat cwrsync.pub >> authorized_keys
```
> Adjust the rsync command in the Windows cwrsync.cmd file to locate the private key file:

```bash
rsync -r -av -e "ssh -i home\%USERNAME%\.ssh\cwrsync" /cygdrive/c/Users/%USERNAME%/Documents/test_file <group>-fs:/data/group/<group>/general/people/%USERNAME%/home
```

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