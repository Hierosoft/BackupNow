"""Store and use additional metadata on running processes beyond psutil.
"""
from collections import OrderedDict
import json
import os

from logging import getLogger

from backupnow.bnsysdirs import (
    local_data_path,
    LUID,
)

logger = getLogger(__name__)


def pids_path():
    # get_sysdir_sub('LOCALAPPDATA', leaf="processes.json", luid=LUID)
    return local_data_path("processes.json")


def add_pid(pid, luid=LUID):
    data = {}
    path = pids_path()
    if os.path.isfile(path):
        with open(path, 'r') as stream:
            data = json.load(stream, object_pairs_hook=OrderedDict)
    if data.get("programs") is None:
        data['programs'] = {}
    if data['programs'].get(luid) is None:
        data['programs'][luid] = {}
    if data['programs'][luid].get('processes') is None:
        data['programs'][luid]['processes'] = []
    if pid in data['programs'][luid]['processes']:
        logger.warning("PID {} was already added.")
        return False
    data['programs'][luid]['processes'].append({
        'pid': pid,
    })
    with open(path, 'w') as stream:
        json.dump(data, stream)
    return True


def remove_pid(pid, luid=LUID):
    data = {}
    path = pids_path()
    if os.path.isfile(path):
        with open(path, 'r') as stream:
            data = json.load(stream, object_pairs_hook=OrderedDict)
    if data.get("programs") is None:
        return False
    if data['programs'].get(luid) is None:
        return False
    if data['programs'][luid].get('processes') is None:
        return False
    index = -1
    for i, process in enumerate(data['programs'][luid]['processes']):
        if process.get('pid') == pid:
            index = i
    if index < 0:
        return False
    del data['programs'][luid]['processes'][index]
    with open(path, 'w') as stream:
        json.dump(data, stream)
    return True


def get_process_info(pid, luid=LUID):
    data = {}
    path = pids_path()
    if os.path.isfile(path):
        with open(path, 'r') as stream:
            data = json.load(stream, object_pairs_hook=OrderedDict)
    if data.get("programs") is None:
        return False
    if data['programs'].get(luid) is None:
        return False
    if data['programs'][luid].get('processes') is None:
        return False
    for process in data['programs'][luid]['processes']:
        if process.get('pid') == pid:
            return process
    return None


def get_pids(luid=LUID):
    data = {}
    results = []
    path = pids_path()
    if os.path.isfile(path):
        with open(path, 'r') as stream:
            data = json.load(stream, object_pairs_hook=OrderedDict)
    if data.get("programs") is None:
        return []
    if data['programs'].get(luid) is None:
        return []
    if data['programs'][luid].get('processes') is None:
        return []
    for process in data['programs'][luid]['processes']:
        if process.get('pid'):  # If any pid for this luid
            results.append(process['pid'])
    return results


def has_process_info(pid, luid=LUID):
    return get_process_info(pid, luid=luid) is not None
