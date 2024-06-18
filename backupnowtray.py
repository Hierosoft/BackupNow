"""
Create a tray icon and run tasks.

os.environ may not work correctly with setproctitle. See readme.md.
"""
from __future__ import print_function
from setproctitle import setproctitle

from logging import getLogger
from multiprocessing import (
    current_process,
)
import platform
import pystray  # See https://pystray.readthedocs.io/en/stable/usage.html
import sys

from PIL import (
    Image,
    ImageTk,
    ImageDraw,
)

if sys.version_info.major >= 3:
    # from tkinter import *
    import tkinter as tk
    from tkinter import ttk
else:
    import Tkinter as tk  # type: ignore
    import ttk  # type: ignore

from backupnow import (
    find_resource,
)

icon_path = None
if platform.system() == "Windows":
    icon_path = find_resource("backupnow.ico")
elif platform.system() == "Darwin":
    icon_path = find_resource("backupnow.icns")
else:
    icon_path = find_resource("backupnow.png")

logger = getLogger(__name__)

root = None

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


def generate_menu():
    """Build the menu.

    Args:
        icon (pystray.Icon): The main class for
            BackupNow-Tray.
    """
    return pystray.Menu(
        pystray.MenuItem("Show", after_click),
        pystray.MenuItem("Exit", after_click),
    )


def after_click(this_icon, query):
    global icon
    if str(query) == "Exit":
        this_icon.stop()
        icon = None
    elif str(query) == "Show":
        show()


def show():
    global root
    if root is not None:
        return
    root = tk.Tk()
    root.title("BackupNow")

    root.iconbitmap(icon_path)  # top left icon
    root.wm_iconbitmap(icon_path)
    # root.wm_iconphoto(False, photo)  # 1st arg is "default" (children use it)
    # See also: icon in pystray Icon constructor.

    _ = BackupNowApp(root)
    root.mainloop()
    root = None


class BackupNowApp(ttk.Frame):

    def __init__(self, root):
        ttk.Frame.__init__(self, root)
        self.root = root
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


def main():
    icon = pystray.Icon(
        'BackupNow-Tray',
        # icon=create_image(64, 64, 'black', 'white'),
        icon=load_image(icon_path),
        # menu=generate_menu()
    )
    # ^ Trying to use PhotoImage somehow results in:
    # "AttributeError: 'PhotoImage' object has no attribute
    # '_PhotoImage__photo'"
    # in PIL/ImageTk.py

    icon.title = "BackupNow"

    if pystray.Icon.HAS_MENU:
        # print(
        #     "Pystray supports {} tray icon menus"
        #     .format(platform.system()))
        icon.menu = generate_menu()
    else:
        logger.warning(
            "Pystray does not support {} tray icon menus"
            .format(platform.system()))

    icon.run()
    return 0


if __name__ == "__main__":
    process = current_process()
    process.name = "BackupNow-Tray"
    sys.exit(main())
