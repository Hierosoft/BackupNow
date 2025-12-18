import os
import sys

TEST_SUB_DIR = os.path.dirname(os.path.realpath(__file__))

TEST_DATA_DIR = os.path.join(TEST_SUB_DIR, "data")

if __name__ == "__main__":
    TESTS_DIR = os.path.dirname(TEST_SUB_DIR)
    REPO_DIR = os.path.dirname(TESTS_DIR)
    sys.path.insert(0, REPO_DIR)

from backupnow.moresmb import (  # noqa: E402
    is_share_format,  # regex check for \\server\share format
)

import pytest


@pytest.mark.parametrize(
    "path, expected",
    [
        # Valid cases
        (r"\\SERVER\share", True),
        (r"\\abc\def", True),
        (r"\\a\b", True),  # Minimal lengths
        (r"\\server.domain\share-name", True),  # Dots and hyphens
        (r"\\SERVER123\share_with_spaces ok", True),  # Spaces and numbers

        # Invalid cases
        (r"\\SERVER", False),  # Missing share
        (r"\\SERVER\\", False),  # Empty share
        (r"\\\SERVER\share", False),  # Extra initial backslash
        (r"\\SERVER\\share", False),  # Extra middle backslash
        (r"\\SERVER\share\\", False),  # Extra trailing backslash
        (r"\SERVER\share", False),  # Single initial backslash
        (r"SERVER\share", False),  # No initial backslashes
        (r"\\SER\\VER\share", False),  # Backslash in server name
        (r"\\SERVER\sha\\re", False),  # Backslash in share name
        (r"", False),  # Empty string
        (r"\\", False),  # Just backslashes, no server/share
        (r"\\SERVER\share\extra", False),  # Extra path after share
    ],
)


def test_is_share_format(path, expected):
    assert is_share_format(path) == expected
