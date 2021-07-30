# BackupNow
Do a graphical backup based on ~/exclude.txt then ~/include.txt (using rsync which excludes or includes based on the first command switch, so --exclude-from is used first).

rsync_with_progress.py is based on ronnymajani's July 4, 2021 comment on aerickson's 2011 version: <https://gist.github.com/aerickson/1283442> which is based on [Get total rsync progress using Python](https://libbits.wordpress.com/2011/04/09/get-total-rsync-progress-using-python/) by yegorich April 9, 2011.

## Related Projects
- rsyncprogress: only accepts piped input
  - rsyncprogress is based on [rsyncprogress.py](https://gist.github.com/JohannesBuchner/4d61eb5a42aeaad6ce90) (`wget https://gist.github.com/JohannesBuchner/4d61eb5a42aeaad6ce90/raw/4bdecaabd3242931a79a9eeb55b4616916e054f9/rsyncprogress.py`) by JohannesBuchner
  - A comment suggests using the progressbar-latest package to fulfill the progressbar dependency.
