# tests/test_bnplatform.py

import os
import platform
import subprocess
import sys
import pytest
from backupnow.bnplatform import get_volume_info, listdrives

# Control whether subprocess.check_output returns bytes (True) or str (False)
# In Python 3 we test both modes to ensure compatibility with real subprocess
utf8 = False


def current_str_type(value):
    """Return value as bytes if utf8=True, else as str."""
    if utf8:
        return value.encode("utf-8")
    return value


def dummy_shell_run(cmd, stderr=None):
    """Simulate subprocess.check_output for testing.

    Returns realistic multiline output for df, blkid, and diskutil commands.
    Respects global utf8 flag: returns bytes when utf8=True, str otherwise.
    """
    cmd_str = " ".join(cmd)

    if "df -T" in cmd_str:
        output = """Filesystem     Type     1024-blocks    Used Available Capacity Mounted on
/dev/disk1s1   apfs         976773168 800000000  150000000    85%    /
""".strip()
    elif "blkid" in cmd_str and "-s LABEL" in cmd_str:
        output = "MyRootVolume\n"
    elif "diskutil info" in cmd_str:
        output = """   Device Identifier:        disk1s1
   Device Node:              /dev/disk1s1
   Whole:                    No
   Part of Whole:            disk1
   Volume Name:              Macintosh HD
   Mounted:                  Yes
   Mount Point:              /
""".strip()
    else:
        raise subprocess.CalledProcessError(
            1, cmd, output=current_str_type("not found")
        )

    if utf8:
        return output.encode('utf-8') + b'\n'
    return output + '\n'


@pytest.fixture
def temp_path(tmpdir):
    """A path to a volume that exists."""
    # p = tmpdir.mkdir("testvol").join("file.txt")
    # p.write("test")
    # return str(p)
    for drive in listdrives():
        return drive


@pytest.mark.parametrize("utf8", [False, True])
def test_get_volume_info_linux_with_label(temp_path, utf8):
    """Test successful volume label detection via blkid (Linux-like)."""
    # Use parametrization only in Python 3
    if sys.version_info.major < 3 and utf8:
        pytest.skip("bytes mode only tested on Python 3")

    info = get_volume_info(temp_path, shell_run=dummy_shell_run)
    assert isinstance(info, dict)

    if platform.system() == "Linux":
        assert info['name'] == 'MyRootVolume'
        assert info['serial_number'] is None
        assert info['max_component_length'] > 0
        assert info['sys_flags'] >= 0
        assert info['filesystem'] == 'apfs'
    assert info['free_bytes'] > 0


@pytest.mark.parametrize("utf8", [False, True])
def test_get_volume_info_linux_fallback_name(temp_path, utf8):
    """Test fallback name when blkid provides no label."""

    if sys.version_info.major < 3 and utf8:
        pytest.skip("bytes mode only tested on Python 3")

    def no_label_run(cmd, stderr=None):
        cmd_str = " ".join(cmd)
        if "blkid" in cmd_str:
            raise subprocess.CalledProcessError(2, cmd)
        return dummy_shell_run(cmd, stderr)

    info = get_volume_info(temp_path, shell_run=no_label_run)
    assert isinstance(info, dict)

    if platform.system() == "Darwin":
        assert info['name'] == ''
        assert info['filesystem'] == 'apfs'
    assert info['free_bytes'] > 0


@pytest.mark.parametrize("utf8", [False, True])
def test_get_volume_info_macos_with_diskutil(temp_path, utf8):
    """Test macOS volume name extraction via diskutil."""

    if sys.version_info.major < 3 and utf8:
        pytest.skip("bytes mode only tested on Python 3")

    info = get_volume_info(temp_path, shell_run=dummy_shell_run)
    assert isinstance(info, dict)
    if platform.system() == "Darwin":
        assert info['name'] == 'Macintosh HD'
        assert info['filesystem'] == 'apfs'
    assert info['free_bytes'] > 0


@pytest.mark.parametrize("utf8", [False, True])
def test_get_volume_info_df_failure_graceful(temp_path, utf8):
    """Test graceful degradation when df command fails."""

    if sys.version_info.major < 3 and utf8:
        pytest.skip("bytes mode only tested on Python 3")

    def failing_df(cmd, stderr=None):
        if "df -T" in " ".join(cmd):
            raise Exception("df failed")
        return dummy_shell_run(cmd, stderr)

    if platform.system() != "Windows":
        info = get_volume_info(temp_path, shell_run=failing_df)
        assert isinstance(info, dict)
        # The df command is only used if *not* Windows.
        assert info['filesystem'] == 'unknown'
        assert info['free_bytes'] > 0
        assert info['name'] == ''


def test_get_volume_info_path_not_exist():
    """Verify OSError is raised for non-existent path."""
    with pytest.raises(OSError):
        get_volume_info("/non/existent/path/123")
        # assert isinstance(info, dict)


@pytest.mark.parametrize("utf8", [False, True])
def test_get_volume_info_on_all_drives(monkeypatch, utf8):
    """Test get_volume_info on every drive returned by listdrives().

    Uses real drives from listdrives() — no temporary files created.
    Skips bytes mode on Python 2.
    """

    if sys.version_info.major < 3 and utf8:
        pytest.skip("bytes mode only tested on Python 3")

    # Patch the shell_run inside the function to our dummy
    monkeypatch.setattr(
        'backupnow.bnplatform.subprocess.check_output',
        dummy_shell_run
    )

    drives = listdrives()
    assert isinstance(drives, list)
    assert len(drives) > 0, "listdrives() returned no drives"

    for drive in drives:
        # Ensure drive path ends with separator
        test_path = drive
        if not test_path.endswith(os.sep):
            test_path += os.sep

        # On some systems, certain drives may not support statvfs or external cmds
        # But our function should either succeed or gracefully handle issues
        info = get_volume_info(test_path, shell_run=dummy_shell_run)
        assert isinstance(info, dict)

        # Basic sanity checks — these should always hold
        assert isinstance(info['name'], str)
        assert isinstance(info['max_component_length'], int)
        assert info['max_component_length'] > 0
        assert isinstance(info['sys_flags'], int)
        assert isinstance(info['filesystem'], str)
        assert isinstance(info['free_bytes'], (int, type(None)))
        if info['free_bytes'] is not None:
            assert info['free_bytes'] >= 0
