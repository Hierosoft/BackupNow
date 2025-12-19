#!/usr/bin/env python3
'''
Mount a volume by name using gio.

based on:

> Quick and dirty implementation of mounting a local volume using Gio.
> For people who were scratching their heads like me.
>
> Code below based on infos from:
> http://stackoverflow.com/questions/5709454/gio-check-if-volume-is-mounted
> http://stackoverflow.com/questions/1991206/accessing-samba-shares-with-gio-in-python/2051628#2051628

-oktayacikalin <https://gist.github.com/oktayacikalin/7065927>
'''
from __future__ import print_function
import platform
import sys

if platform.system() == "Windows":
    raise SystemError("The mount submodule is not compatible with Windows.")

from gi.repository import Gio, GObject  # type: ignore


# VOLUME_NAME = 'TrekStor'
# VOLUME_UUID = '3d9d84c9-460d-4047-8e6f-1013df72acd0'


def error(msg):
    sys.stderr.write("{}\n".format(msg))


def mount_done_cb(obj, res, user_data):
    # print(obj, res, user_data)
    # obj.mount_enclosing_volume_finish(res)
    obj.mount_finish(res)
    # print('done.')
    # print(1, obj.get_name(), obj.get_uuid(), obj.get_mount(), obj.get_drive())
    # print(2, obj.get_mount().get_uuid())
    # print(3, obj.get_mount().get_default_location().get_path())
    print(4, obj.get_mount().get_root().get_path())
    # print(5, obj.get_mount().get_volume())
    # print(6, obj.get_mount().get_drive())
    user_data.quit()


def mount(volume_name):
    mo = Gio.MountOperation()
    mo.set_anonymous(True)

    vm = Gio.VolumeMonitor.get()
    # print(dir(vm))
    # print(vm.get_mount_for_uuid(VOLUME_UUID))
    # print(vm.get_volume_for_uuid(VOLUME_UUID))
    loop = GObject.MainLoop()
    found = False
    for v in vm.get_volumes():
        name = v.get_name()
        if name == volume_name:
            mount = v.get_mount()
            print(name, v.get_uuid(), v.get_mount(), v.get_drive())
            if not mount:
                v.mount(0, mo, None, mount_done_cb, loop)
                # print(name, v.get_uuid(), v.get_mount(), v.get_drive())
                found = True

    if found:
        loop.run()


def main():
    if len(sys.argv) < 2:
        error("You must enter a volume name as the first argument.")
        exit(1)
    mount(sys.argv[1])


if __name__ == '__main__':
    main()
