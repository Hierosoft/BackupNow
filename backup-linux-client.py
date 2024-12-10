#!/usr/bin/env python3

import git
import os
import shlex
import shutil
import socket
import subprocess
import sys

if sys.version_info.major >= 3:
    from datetime import datetime, timezone
else:
    from datetime import datetime


# Try to import gitpython and install if not available
try:
    from git import Repo, GitCommandError
except ImportError:
    print("gitpython not found. Installing...", file=sys.stderr)
    cmd_parts = ['sudo', '/usr/bin/apt', 'install', '-y', 'python3-git']
    cmd = shlex.join(cmd_parts)
    print("Trying to run:", file=sys.stderr)
    print("    " + cmd, file=sys.stderr)

    # Run the first subprocess to install python3-git and capture the exit code
    process = subprocess.run(cmd_parts)
    code = process.returncode

    # Check if the installation failed
    if code != 0:
        print("Installation failed. Try installing the distro package"
              " python3-git, then try running the script again.", file=sys.stderr)
    else:
        print("Installation successful. Rerunning the script...")
        cmd2_parts = [sys.executable, *sys.argv]

        process2 = subprocess.run(cmd2_parts)
        code2 = process2.returncode
        code = code2

    # Exit with the final exit code
    sys.exit(code)


time_fmt = "%H:%M"
date_fmt = "%Y-%m-%d"
dt_fmt = date_fmt + " " + time_fmt
# TODO: use static time_fmt, date_fmt, and dt_fmt
#   from backupnow.taskmanager.TMTimer


def best_utc_now():
    if sys.version_info.major >= 3:
        return datetime.now(timezone.utc)
    return datetime.utcnow()


def copy_preserve(src, dst):
    if os.path.islink(src):
        linkto = os.readlink(src)
        os.symlink(linkto, dst)
    else:
        shutil.copy(src, dst)


def copy_preserve_cmd(src, dst):
    if os.path.islink(src):
        target = os.readlink(src)
        return 'ln -s "%s" "%s"' % (target, dst)
    return 'cp "%s" "%s"' % (src, dst)


def append_to_file(script_path, line):
    if not line.endswith("\n"):
        line += "\n"
    with open(script_path, 'a') as stream:
        stream.write(line)


def backup_folder(source_path, destination, depth=0):
    """Back up the contents of a folder to the remote server using rsync.

    Args:
        source_path (str): Path to the source folder.
        destination (str): Remote destination path.
        depth (int, optional): Depth of tree where depth of backup job's
            'source' is 0 (Reserved for future use).
    """
    folder_name = os.path.basename(source_path)
    remote_destination = "{}/{}".format(destination, folder_name)

    rsync_command = [
        'rsync', '-av', '--delete', '--exclude', '.venv',
        '--exclude', 'node_modules',
        source_path + '/',  # Copy folder contents, not the folder itself
        remote_destination
    ]
    print(shlex.join(rsync_command))
    try:
        subprocess.run(rsync_command, check=True)
        print("Backup completed for {} to {}.".format(source_path, remote_destination))
    except subprocess.CalledProcessError as e:
        print("Rsync error: {}".format(e))


def backup_file(source_path, destination, depth=0):
    """Back up a single file to the remote server using rsync.

    Args:
        source_path (str): Path to the source file.
        destination (str): Remote destination path.
        depth (int, optional): Depth level of the backup (default: 0).

    Returns:
        int: 0 on success, rsync error code otherwise.
    """
    if not os.path.isfile(source_path):
        raise FileNotFoundError('"{}" is not a file'.format(source_path))

    name = os.path.splitext(source_path)[1]
    if destination.endswith(name):
        print('Warning: "{}" ends with "{}" but destination'
              ' should not be file-like. "/" will be appended!'
              .format(destination, name))

    if not destination.endswith("/"):
        destination = "{}/".format(destination)

    rsync_command = [
        'rsync', '-av',
        source_path,
        destination
    ]

    print(shlex.join(rsync_command))

    try:
        result = subprocess.run(rsync_command, check=False)
        # ^ check=False prevents an exception on nonzero return code
        if result.returncode == 0:
            print("Backup completed for {} to {}."
                  .format(source_path, destination),
                  file=sys.stderr)
            return 0
        else:
            print("Rsync failed with error code {} for {} to {}."
                  .format(result.returncode, source_path, destination),
                  file=sys.stderr)
            return result.returncode
    except subprocess.SubprocessError as e:
        print("Rsync error: {}".format(e), file=sys.stderr)
        return 1


def backup(source, destination, git_depth=None, recursive=True,
           links_to_script=False, depth=0):
    """Back up a folder to the remote server using rsync.
    Rsync is used for recursion, but method is not. Therefore, only each
    direct sub of source (or the file if source is a file) is considered
    for links_to_script or other options.

    Args:
        source (str): Path to the source folder.
        destination (str): Remote destination path. Source name will be
            created under it.
        git_depth (int): Depth of git repos in source.
            For example, if source is git folder with
            repos in it, set git_depth to 1. If there
            don't appear to be pending local changes,
            don't back it up. Defaults to -1 (Do not
            filter by git status).
        recursive (bool): Back up files recursively.
        links_to_script (bool): Skip symlinks and instead append to a
            "restore-links-backupnow.sh" script in the destination (wipe
            the script at the start of the destination if already
            present!). Defaults to False.
        depth (int, optional): Normally leave as 0 (auto depth).
    """
    if git_depth is None:
        git_depth = -1
    link_script_name = "restore-links-backupnow.sh"
    link_script_path = os.path.join(destination, link_script_name)
    name = os.path.split(source)[1]
    dst_full = os.path.join(destination, name)
    script_line_count = 0
    if links_to_script:
        if os.path.isfile(link_script_path):
            os.remove(link_script_path)
    if os.path.islink(source):
        if links_to_script:
            cmd = copy_preserve_cmd(source, dst_full)
            append_to_file(link_script_path, cmd)
            script_line_count += 1
        else:
            copy_preserve(source, dst_full)
    elif os.path.isfile(source):
        print("Backing up file: {}".format(source))
        backup_file(source, destination, depth=depth+1)
    elif os.path.isdir(source):
        for sub in os.listdir(source):
            sub_depth = depth + 1
            sub_path = os.path.join(source, sub)
            dst_sub_full = os.path.join(dst_full, sub)
            if os.path.islink(sub_path):
                if links_to_script:
                    cmd = copy_preserve_cmd(sub_path, dst_sub_full)
                    append_to_file(link_script_path, cmd)
                    script_line_count += 1
                else:
                    copy_preserve(sub_path, dst_sub_full)
            elif os.path.isdir(sub_path):
                if not recursive:
                    continue
                noun = "folder" if (git_depth != sub_depth) else "repo"
                if (noun != "repo") or check_repo(sub_path):
                    print("Backing up {}: {}".format(noun, sub_path))
                    backup_folder(sub_path, os.path.join(destination, sub),
                                  depth=depth+1)
                else:
                    print("No changes to back up for: {}".format(sub_path))
            elif os.path.isfile(sub_path):
                print("Backing up file: {}".format(sub_path))
                if links_to_script:
                    backup_file(sub_path, destination, depth=depth+1)
                # ^ intentionally do not use sub of destination in
                #   the case of a file
            else:
                print('Error: "{}" is neither a file nor a directory.'
                        .format(sub_path))
    if script_line_count:
        dt_utc_str = best_utc_now().format(dt_fmt)
        append_to_file(link_script_path, "# done {}".format(dt_utc_str))

def backup_all(backups, remote_host, slash_remote):
    """Run backups based on provided configurations.

    Args:
        backups (list): Backup configurations.
            - 'source' (str): The directory or file to back up.
            - 'destination' (str): The destination parent for the source
              (See generate_full_src_under_dst).
            - 'generate_full_src_under_dst' (bool, optional): Recreate
              the entire source path on the destination (False for only
              the leaf name of the source path). Defaults to False.
        remote_host (str): Remote host for backups.
        slash_remote (str): Base path on the remote server.

    Returns:
        int: 0 on success.
    """
    for backup_info in backups:
        source = backup_info['source']
        dst_recreate_full_source_path = \
            backup_info.get('generate_full_src_under_dst')
        if dst_recreate_full_source_path:
            destination = os.path.join(slash_remote, source.lstrip("/"))
        else:
            name = os.path.split(source)[1]
            destination = os.path.join(slash_remote, name.lstrip("/"))
        if os.path.isfile(source):
            destination = os.path.dirname(destination)

        if remote_host:
            destination = "{}:{}".format(remote_host, destination)

        backup(source, destination,
               git_depth=backup_info.get('git_depth'),
               recursive=backup_info.get('recursive', True),
               links_to_script=backup_info.get('links_to_script'))

    return 0



def check_repo(repo_path):
    """Check if Git changes don't appear to be on origin.

    Args:
        repo_path (str): Path to the Git repository.

    Returns:
        bool: True if changes don't appear to be on origin.
    """
    if not os.path.isdir(os.path.join(repo_path, ".git")):
        print("\"{}\" is not a git repo.".format(repo_path))
        return True
    try:
        repo = Repo(repo_path)
        if repo.bare:
            return True  # Assume changes aren't on origin

        # Check for unstaged changes
        if repo.is_dirty(untracked_files=True):
            return True

        # Check for unpushed commits
        if repo.remotes:
            remote = repo.remotes[0]  # Use the first remote
            # remote.fetch()  # Fetch the latest commits from remote
            # ^ comment since we only need to know if the local
            #   repo has a diff against whatever it last
            #   downloaded!
            if remote.refs and repo.head.commit != remote.refs[0].commit:
                return True
        # or :
        # # Ensure 'origin' remote exists
        # if 'origin' not in repo.remotes:
        #     return True
        # # Fetch the latest commits from 'origin'
        # origin = repo.remotes['origin']
        # origin.fetch()
        # # Compare local commit with the latest on origin
        # if repo.head.commit != origin.refs[0].commit:
        #     return True

        return False
    except GitCommandError as e:
        print("Backing up non-Git due to Git error: {}".format(e))
        return True
    except git.exc.InvalidGitRepositoryError as e:
        print("Backing up non-Git due to invalid Git repo: {}".format(e))
        return True


def main():
    """Initialize backups and start the backup process.

    Returns:
        int: The result of the backup process.
    """
    computer_name = socket.gethostname()

    default_backups = [
        {
            'source': os.path.expanduser('~/git'),
            'git_depth': 1,
            'recursive': True,
        },
        {
            'source': os.path.expanduser('~/metaprojects'),
            'recursive': True,
        },
        {
            'source': os.path.expanduser('~'),
            'recursive': False,
        },
        {
            'source': os.path.expanduser('~/.local/bin'),
            'recursive': False,
            'links_to_script': True,
        },
    ]
    backups = []
    for backup in default_backups:
        if not os.path.exists(backup['source']):
            continue
        backups.append(backup)

    backupnow_configs_dir = os.path.expanduser("~/.config/backupnow")
    if not os.path.isdir(backupnow_configs_dir):
        os.makedirs(backupnow_configs_dir)




    for i in range(len(backups)):
        backups[i]['generate_full_src_under_dst'] = backups[i]['source']

    remote_host = "birdo"
    slash_remote = "/mnt/big/{}".format(computer_name)

    return backup_all(backups, remote_host, slash_remote)


if __name__ == '__main__':
    import sys
    sys.exit(main())
