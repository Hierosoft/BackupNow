"""
Create a tray icon and run tasks.

os.environ may not work correctly with setproctitle. See readme.md.
"""
from __future__ import print_function

import os
import platform
import psutil
import pystray  # See https://pystray.readthedocs.io/en/stable/usage.html
import re
import sys

from logging import getLogger
from multiprocessing import (
    current_process,
)
from PIL import (
    Image,
    ImageTk,
    ImageDraw,
)
from setproctitle import setproctitle


if sys.version_info.major >= 3:
    # from tkinter import *
    import tkinter as tk
    from tkinter import ttk
    from tkinter import messagebox
else:
    import Tkinter as tk  # type: ignore
    import ttk  # type: ignore
    import tkMessageBox as messagebox  # type: ignore

from backupnow import (
    find_resource,
    moreps,
    BackupNow,
)

icon_path = None
if platform.system() == "Windows":
    icon_path = find_resource("backupnow.ico")
elif platform.system() == "Darwin":
    icon_path = find_resource("backupnow.icns")
else:
    icon_path = find_resource("backupnow.png")

logger = getLogger(__name__)

setproctitle("BackupNow-Tray")
"""
Hmm, process title is still "Python" in Windows.
"The setproctitle module allows a process to change its title (as
displayed by system tools such as ps, top or MacOS Activity Monitor)."

So try the multiprocessing library instead.
"""


def create_image(width, height, color1, color2):
    # Generate an image and draw a pattern
    image = Image.new('RGB', (width, height), color1)
    dc = ImageDraw.Draw(image)
    dc.rectangle(
        (width // 2, 0, width, height // 2),
        fill=color2)
    dc.rectangle(
        (0, height // 2, width // 2, height),
        fill=color2)

    return image


def load_photoimage(path):
    ico = Image.open(path)
    return ImageTk.PhotoImage(ico)


def load_image(path):
    return Image.open(path)


class BackupNowFrame(ttk.Frame):
    my_pid = None

    def __init__(self, root):
        ttk.Frame.__init__(self, root)
        self.root = root
        self.icon = None

    def on_form_loading(self):
        root = self.root
        root.iconbitmap(icon_path)  # top left icon
        root.wm_iconbitmap(icon_path)
        # root.wm_iconphoto(False, photo)  # 1st arg is "default" children use
        # See also: icon in pystray Icon constructor.

        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        # root.title("BackupNow")
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        self.log_panel = ttk.Frame(self.notebook)
        self.notebook.add(self.log_panel, text="Tasks")  # returns None
        self.add_log_container(self.log_panel)

    def add_log_container(self, container):
        # container.padding = "3 3 12 12"
        # container.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))
        container.columnconfigure(0, weight=1)
        container.rowconfigure(0, weight=1)

        self.log_text = tk.Text(container)
        self.log_text.grid(column=0, row=0, sticky=tk.NSEW)

        # for child in container.winfo_children():
        #     child.grid_configure(padx=5, pady=5)

    def calculate(self, *args):
        try:
            value = float(self.feet.get())
            self.meters.set(int(0.3048 * value * 10000.0 + 0.5)/10000.0)
        except ValueError:
            pass


    def generate_menu(self):
        # default arg is associated with left-click (double on Windows)
        return pystray.Menu(
            pystray.MenuItem("Show", self.after_click, default=True),
            pystray.MenuItem("Exit", self.after_click),
        )

    def after_click(self, _, query):
        """Handle a pystray icon menu click event.

        Args:
            _ (pystray.Icon): The icon.
            query (str): The menu item string determining the action to
                take.
        """
        # type(query) is pystray._base.MenuItem
        # query.: checked, default, enabled, radio, submenu, text, visible
        if str(query) == "Exit":
            self.quit_window()
        elif str(query) == "Show":
            self.show()
        else:
            logger.error(
                "Unknown icon click query=\"{}\""
                .format(query))

    def show(self):
        self.icon.stop()
        self.root.after(0, self.root.deiconify)

    def quit_window(self):
        self.icon.stop()
        self.icon = None
        self.root.destroy()
        self.root = None
        moreps.remove_pid(BackupNowFrame.my_pid)

    def on_window_closing_quit(self):
        """Quit instead of withdraw.
        If the OS does not support tray icon menus, call this instead of
        withdraw_window on close.
        """
        self.quit_window()

    def on_window_closing(self):
        self.root.withdraw()
        # image = Image.open(icon_path)
        # menu = (
        #     pystray.MenuItem('Show', show_window),
        #     pystray.MenuItem('Quit', quit_window),
        # )
        # icon = pystray.Icon("name", image, "title", menu)
        # icon.run()
        self.icon = pystray.Icon(
            'BackupNow-Tray',
            # icon=create_image(64, 64, 'black', 'white'),
            icon=load_image(icon_path),
            # menu=generate_menu(),

        )
        # ^ Trying to use PhotoImage somehow results in:
        # "AttributeError: 'PhotoImage' object has no attribute
        # '_PhotoImage__photo'"
        # in PIL/ImageTk.py

        self.icon.title = "BackupNow"
        self.icon.menu = self.generate_menu()  # ensures default if no HAS_MENU
        if pystray.Icon.HAS_MENU:
            pass
            # print(
            #     "Pystray supports {} tray icon menus"
            #     .format(platform.system()))
        else:
            logger.warning(
                "Pystray does not support {} tray icon menu."
                " The next time the window closes the program will quit!"
                .format(platform.system()))
            self.root.protocol('WM_DELETE_WINDOW', self.on_window_closing_quit)

        self.icon.run()


def main():
    sibling_pids = []
    for sibling_pid in moreps.get_pids():
        if psutil.pid_exists(sibling_pid):
            # TODO: In case this is a stale PID from before this boot of
            #   the OS (though the PID should never be left in thi list
            #   after this program's exit) maybe see if the
            #   process.name().lower() contains "python" or "backupnow"
            #   before assuming it is running.
            sibling_pids.append(sibling_pid)
        else:
            # The process is not running but must have not removed
            #   itself from the list, so remove it:
            moreps.remove_pid(sibling_pid)
    if sibling_pids:
        if len(sibling_pids) > 1:
            id_msg = "IDs: {}".format(re.sub("[\\[\\]]", "",
                                             str(sibling_pids)))
        else:
            id_msg = "ID: {}".format(sibling_pids[0])
        messagebox.showinfo(
            "BackupNow",
            "The BackupNow tray icon (process {}) is already running."
            .format(id_msg)
        )
        return 2

    # if psutil.pid_exists():
    BackupNowFrame.my_pid = os.getpid()
    moreps.add_pid(BackupNowFrame.my_pid)
    root = tk.Tk()
    root.title("BackupNow")

    frame = BackupNowFrame(root)

    root.protocol('WM_DELETE_WINDOW', frame.on_window_closing)
    root.withdraw()  # hide immediately after prepared
    root.after(1, frame.on_form_loading)  # delay iconbitmap
    #  (to prevent flash before withdraw:
    #  https://stackoverflow.com/a/33309424/4541104)
    root.after(1, frame.on_window_closing)  # Show icon since window is hidden!
    root.mainloop()
    return 0


if __name__ == "__main__":
    process = current_process()
    process.name = "BackupNow-Tray"
    sys.exit(main())
