"""
Methods used both by __init__ and components that __init__ imports.
"""
import sys

from datetime import datetime

if sys.version_info.major >= 3:
    from datetime import timezone

def best_utc_now():
    if sys.version_info.major >= 3:
        return datetime.now(timezone.utc)  # type:ignore
    return datetime.utcnow()
