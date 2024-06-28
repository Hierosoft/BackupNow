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
        root.after(0, self._on_form_loading)  # delay iconbitmap
        #  & widget creation until after hiding is complete.
        #  (to prevent flash before withdraw:
        #  https://stackoverflow.com/a/33309424/4541104)
        self.core = None
        # root.after(100, self._start)

    def _on_form_loading(self):
        logger.warning("Form is loading...")
        root = self.root
        # root.wm_iconphoto(False, photo)  # 1st arg is "default" children use
        # See also: icon in pystray Icon constructor.
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        # root.title("BackupNow")
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        self.log_panel = ttk.Frame(self.notebook)
        self.notebook.add(self.log_panel, text="Log")  # returns None
        self._add_log_container(self.log_panel)
        root.iconbitmap(icon_path)  # top left icon
        root.wm_iconbitmap(icon_path)
        logger.warning("Form loaded.")
        # root.after(0, self._start)  # "withdraw" seems to prevent this :( so:
        self._start()

    def _start(self):
        if self.core:
            raise RuntimeError("BackupNow core was already initialized.")
        logger.warning("Starting core...")
        self.core = BackupNow()
        self.core.start()  # Do *not* use tk=self.root: "after" skips if closed
        logger.warning("Loading settings...")
        self.core.load()
        if self.core.errors:
            logger.error("[_start] load errors:")
            for error in self.core.errors:
                logger.error("[_start] - {}".format(error))
            self.core.errors = []
        logger.warning("Saving settings...")
        self.core.save()
        if self.core.errors:
            logger.error("[_start] save errors:")
            for error in self.core.errors:
                logger.error("[_start] - {}".format(error))
            self.core.errors = []
        logger.warning("Saved settings.")

    def _add_log_container(self, container):
        # container.padding = "3 3 12 12"
        # container.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))
        container.columnconfigure(0, weight=1)
        container.rowconfigure(0, weight=1)

        self.log_text = tk.Text(container)
        self.log_text.grid(column=0, row=0, sticky=tk.NSEW)

        # for child in container.winfo_children():
        #     child.grid_configure(padx=5, pady=5)

    def _generate_menu(self):
        # default arg is associated with left-click (double on Windows)
        return pystray.Menu(
            pystray.MenuItem("Show", self._after_click, default=True),
            pystray.MenuItem("Exit", self._after_click),
        )

    def _after_click(self, _, query):
        """Handle a pystray icon menu click event.

        Args:
            _ (pystray.Icon): The icon.
            query (str): The menu item string determining the action to
                take.
        """
        # type(query) is pystray._base.MenuItem
        # query.: checked, default, enabled, radio, submenu, text, visible
        if str(query) == "Exit":
            self._quit()
        elif str(query) == "Show":
            self._show()
            self.core.save()
        else:
            logger.error(
                "Unknown icon click query=\"{}\""
                .format(query))

    def _show(self):
        self.root.deiconify()
        # self.root.after(0, self.root.deiconify)
        # ^ "after" doesn't seem to run after "withdraw" (?)
        self.icon.stop()
        # ^ Stopping the icon allows Ctrl+C which may be desirable for
        #   manual testing.

    def _quit(self):
        self.icon.title = "Stopping..."
        # self.root.deiconify()  # if never shown, may be empty
        # self.root.after(0, self._stop_service)
        self._stop_service()

    def _stop_service(self):
        logger.warning("Stopping service...")
        self.icon.title = "Stopping service..."
        self.core.stop_sync()
        # Warning, if after is still scheduled,
        # destroy (doing things after destroy?)
        # may cause "Fatal Python error: PyEval_RestoreThread:
        # the function must be called with the GIL held, but the GIL is
        # released (the current Python thread state is NULL)
        # Python runtime state: initialized"
        # - Seems to be prevented by avoiding
        #   "after" in "_quit".
        self.core = None
        self.icon.title = "Stopping icon..."
        self.icon.stop()
        self.icon = None
        logger.warning("Stopped.")
        self.root.destroy()
        self.root = None
        moreps.remove_pid(BackupNowFrame.my_pid)

    def quit(self):
        """Quit instead of minimizing to tray.
        If the OS does not support tray icon menus, this is called
        instead of quit_to_tray when the window is closed to provide a
        way to quit.
        """
        self._quit()

    def quit_to_tray(self):
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
        self.icon.menu = self._generate_menu()  # ensure default if no HAS_MENU
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
            self.root.protocol('WM_DELETE_WINDOW', self.quit)

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

    root.protocol('WM_DELETE_WINDOW', frame.quit_to_tray)
    root.withdraw()  # hide immediately after prepared
    root.after(1, frame.quit_to_tray)  # Show icon since window is hidden!
    root.mainloop()
    return 0


if __name__ == "__main__":
    process = current_process()
    process.name = "BackupNow-Tray"
    sys.exit(main())
