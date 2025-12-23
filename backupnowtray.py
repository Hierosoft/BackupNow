"""
Create a tray icon and run tasks.

os.environ may not work correctly with setproctitle. See readme.md.
"""
from __future__ import print_function

from collections import OrderedDict
import os
import platform
import psutil
import pystray  # See https://pystray.readthedocs.io/en/stable/usage.html
import re
import sys
import threading

from logging import getLogger
from multiprocessing import (
    current_process,
)
from PIL import (
    Image,
    ImageTk,
    ImageDraw,
)

from backupnow.bncore import BackupNow
try:
    from setproctitle import setproctitle
except ImportError:
    def setproctitle(_):
        print("setproctitle is not installed.", file=sys.stderr)
        # TODO: Try multiprocessing library instead (setproctitle
        #   doesn't seem to work on Windows anyway: name is still
        #   "Python" in Task Manager)
        pass

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
    echo0,
    find_resource,
    formatted_ex,
    moreps,
)

from backupnow.bnjobtk import (
    JobTk,
)

from backupnow.bnscrollableframe import (
    VerticalScrolledFrame,
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


class BackupNowFrame(ttk.Frame):  # type: ignore
    my_pid = None
    stay_in_tray = True

    def __init__(self, root):
        # type: (tk.Tk) -> None
        ttk.Frame.__init__(self, root)
        self.jobs = OrderedDict()  # type: OrderedDict[str, JobTk]
        self.root = root
        self.icon = None  # type: Icon
        root.after(0, self._on_form_loading)  # delay iconbitmap
        #  & widget creation until after hiding is complete.
        #  (to prevent flash before withdraw:
        #  https://stackoverflow.com/a/33309424/4541104)
        self.core = BackupNow()  # type: BackupNow
        # root.after(100, self._start)
        self.icon_thread = None
        self.jobPanels = None  # type: OrderedDict[str, JobTk]

    def _on_form_loading(self):
        logger.info("Form is loading...")
        root = self.root  # type: tk.Tk
        # root.wm_iconphoto(False, photo)  # 1st arg is "default" children use
        # See also: icon in pystray Icon constructor.
        # root.title("BackupNow")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)  # Notebook row
        root.rowconfigure(1, weight=0)  # Status label row (fixed height)
        root.iconbitmap(icon_path)  # top left icon
        root.wm_iconbitmap(icon_path)

        outer_row = 0
        self.notebook = ttk.Notebook(root)
        self.notebook.grid(row=outer_row, column=0, sticky=tk.NSEW)
        self.jobs_panel = VerticalScrolledFrame(self.notebook)
        self.notebook.add(self.jobs_panel, text="Jobs")
        self.log_panel = ttk.Frame(self.notebook)
        self.notebook.add(self.log_panel, text="Log")  # returns None
        self._add_log_container(self.log_panel)

        self.status_v = tk.StringVar(self.root)
        self.status_label = ttk.Label(self.root, state="readonly",
                                      textvariable=self.status_v)
        outer_row += 1

        self.destinationPanel = ttk.Frame(root)
        self.destinationDropdown = ttk.Combobox(
            self.destinationPanel,
            # state='readonly',  # only allow select not type
        )
        self.destinationLabel = ttk.Label(
            self.destinationPanel,
            text="Destination:"
        )
        self.destinationLabel.grid(row=0, column=0)
        self.destinationDropdown.grid(row=0, column=1)
        self.destinationPanel.grid(row=outer_row)
        outer_row += 1

        self.status_label.grid(row=outer_row, column=0, sticky=tk.EW)
        self.selected_job_name = None
        self._populating_jobs = 0
        logger.info("Form loaded.")
        self.set_status("Loaded settings...")
        # root.after(0, self._start)  # "withdraw" seems to prevent this :( so:
        self._start()
        self.set_status("Loaded settings.")
        self.updateDriveList()

    def updateDriveList(self):
        self.destinationDropdown.set('')
        self.destinationDropdown['values'] = ()
        self.set_status("Listing drives...")
        drives = []
        if platform.system() == "Windows":
            for drive in os.listdrives():
                if drive.upper().startswith("C:"):
                    continue
                drives.append(drive)
        else:
            for drive in os.listdrives():
                if drive.startswith("/usr"):
                    continue
                drives.append(drive)
        drives.sort()
        self.destinationDropdown['values'] = drives
        self.set_status("Done listing drives.")

    def set_status(self, msg):
        self.status_v.set(msg)

    def _start(self):
        if self.core.enabled:
            raise RuntimeError("BackupNow core was already initialized.")
        logger.info("Starting core...")
        self.core.start()  # Do *not* use tk=self.root: "after" skips if closed
        # ^ Sets self.core.enabled = True
        logger.info("Loading settings...")
        self.core.load()
        if self.core.errors:
            logger.error("[_start] load errors:")
            for error in self.core.errors:
                logger.error("[_start] - {}".format(error))
            del self.core.errors[:]
        logger.info("Saving settings...")
        self.core.save()
        if self.core.errors:
            logger.error("[_start] save errors:")
            for error in self.core.errors:
                logger.error("[_start] - {}".format(error))
            del self.core.errors[:]
        logger.info("Saved settings.")
        try:
            self.show_jobs()
        except Exception as ex:
            msg = "{}: {}".format(type(ex).__name__, ex)
            self.set_status(msg)
            raise

    # def key_of_job_row(self, index):
    #     for key, job in self.jobs.items():
    #         if job.row == index:
    #             return key
    #     return None

    def onJobSelected(self, event):
        job_name = event.widget.get()
        if self._populating_jobs > 0:
            logger.warning("Selected job while populating, so ignored.")
            return
        logger.warning("Selected {}".format(repr(job_name)))
        if self.selected_job_name is not None:
            self.jobs[self.selected_job_name].grid_forget()

        self.jobs[job_name].grid()
        self.selected_job_name = job_name

    def pauseJobSelection(self):
        self._populating_jobs += 1

    def unpauseJobSelection(self):
        self._populating_jobs -= 1

    def show_jobs(self):
        container = self.jobs_panel.interior
        if self.jobs:
            for _, job in self.jobs.items():
                job.grid_forget()
            self.jobs.clear()
        self.jobs_header_rows = 0
        self.jobs_label = ttk.Label(container, text=self.core.settings.path)
        self.jobs_label.grid(row=self.jobs_header_rows, column=0, columnspan=8)
        self.jobs_header_rows += 1
        self.jobs_row = self.jobs_header_rows
        jobs = self.core.settings.get('jobs')
        # There is also "taskmanager": { "timers": { "default_backup"
        if not jobs:
            self.set_status("There are no jobs in the settings file.")
            return
        if not hasattr(jobs, 'items'):
            raise TypeError(
                "File \"{}\": Expected a dict for '{}' but got a {}."
                .format(self.core.settings.path, 'jobs', type(jobs).__name__)
            )
        self.jobsDropdown = jobsDropdown = ttk.Combobox(
            container,
            state='readonly',
            values=list(jobs.keys())
        )
        # ^ 'readonly': no typing, only selecting
        jobsDropdown.grid(column=JobTk.columns['name'],
                          # columnspan=len(self.columns)-2,
                          row=self.jobs_row, sticky=tk.EW)
        jobsDropdown.bind("<<ComboboxSelected>>", self.onJobSelected)
        shown_panel = None
        self.jobPanels = OrderedDict()
        for job_name, job in jobs.items():
            show = False
            # job is a dict containing "operations" key pointing to a list
            # existing_key = self.key_of_job_row(self.jobs_row)
            # if existing_key:
            #     raise IndexError("Row {} was already used for {}."
            #                      .format(self.jobs_row, repr(existing_key)))
            enabled = job.get('enabled')
            if job_name in self.jobs:
                raise KeyError(
                    "Each job must have a unique name, but got {} again."
                    .format(repr(job_name)))
            if enabled:
                if self.selected_job_name is None:
                    self.selected_job_name = job_name
                    self.pauseJobSelection()
                    jobsDropdown.set(job_name)
                    self.unpauseJobSelection()
                    show = True
                    shown_panel = panel
            panel = JobTk(container, self.jobs_row, self.onRunButtonClicked,
                          show=show)
            if show:
                shown_panel = panel
            self.jobs[job_name] = panel
            panel.set_name(job_name)
            panel.set_meta(job)
            # panel.pack(side=tk.TOP, fill=tk.X, expand=True)  # it packs now
            operations = job.get('operations')
            if enabled is None:
                enabled = True
            panel.set_enabled(enabled)
            if enabled and operations:
                if hasattr(operations, 'items'):
                    raise TypeError(
                        "File \"{}\": Expected a list"
                        " for {} but got a {}."
                        .format(self.core.settings.path, 'operations',
                                type(operations).__name__)
                    )
                for key, operation in enumerate(operations):
                    panel.add_operation(key, operation, show=show)
            self.jobPanels[job_name] = panel
        # Only increment at end, since we only show the current one!
        # if shown_panel:
        #     self.jobs_row = shown_panel.row + 1

    def onRunButtonClicked(self):
        try:
            job_name = self.jobsDropdown.get()
            destination = self.destinationDropdown.get()
            self.jobPanels[job_name].run_all(destination)
        except Exception as ex:
            self.set_status(formatted_ex(ex))

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
        if not BackupNowFrame.stay_in_tray:
            self.icon.stop()
            # ^ Stopping the icon allows Ctrl+C which may be desirable for
            #   manual testing.
            self.icon = None

    def _quit(self):
        self.icon.title = "Stopping..."
        # self.root.deiconify()  # if never shown, may be empty
        # self.root.after(0, self._stop_service)
        self._stop_service()

    def _stop_service(self):
        logger.warning("Stopping service...")

        if self.icon:
            self.icon.title = "Stopping service..."
        try:
            self.core.stop_sync()
        except Exception as ex:
            # Core didn't initialize correctly.
            echo0('[_stop_service] {}: {}'
                  .format(type(ex).__name__, ex))
        # Warning, if after is still scheduled,
        # destroy (doing things after destroy?)
        # may cause "Fatal Python error: PyEval_RestoreThread:
        # the function must be called with the GIL held, but the GIL is
        # released (the current Python thread state is NULL)
        # Python runtime state: initialized"
        # - Seems to be prevented by avoiding
        #   "after" in "_quit".
        self.core.disable()
        if self.icon:
            self.icon.title = "Stopping icon..."
            self.icon.stop()
            self.icon = None
        logger.warning("Stopped.")
        if self.root:
            self.root.update_idletasks()  # avoid calls to destroyed widgets
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
        logger.info("Quit to tray...")
        self.root.withdraw()
        # image = Image.open(icon_path)
        # menu = (
        #     pystray.MenuItem('Show', show_window),
        #     pystray.MenuItem('Quit', quit_window),
        # )
        # icon = pystray.Icon("name", image, "title", menu)
        # icon.run()
        if not self.icon:
            self.tray_icon_main()

    def tray_icon_main(self):
        logger.info("Load tray icon...")
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

        # self.icon.run()
        if sys.version_info.major >= 3:
            self.icon_thread = threading.Thread(daemon=True,
                                                target=lambda: self.icon.run())
        else:
            self.icon_thread = threading.Thread(target=lambda: self.icon.run())
        self.icon_thread.start()
        # ^ Now icon.stop() should close the thread according to:
        #   - See https://stackoverflow.com/a/77102240/4541104
        #     - which cites https://github.com/moses-palmer/pystray/issues/94
        logger.info("Loaded tray icon.")


def main():
    sibling_pids = []
    for sibling_pid in moreps.get_pids():
        if psutil.pid_exists(sibling_pid):
            p = psutil.Process(sibling_pid)
            name = p.name()  # such as "nvWmi64.exe"
            # print("p.name={}".format(name))  # just python
            # print("p.exe={}".format(p.exe()))  # just python path
            cmd = p.cmdline()
            # ^ list where first is python path, arg is backupnowtray.py path
            #   - but may not be split correctly. See
            #     <https://github.com/giampaolo/psutil/issues/1179>.
            match = False
            for part in cmd:
                if "backupnow" in part.lower():
                    match = True
            if not match:
                # The stored pid is from before reboot and longer indicates
                #   *this* program is running so remove the pid (lock) file:
                print("Removed stale lock for PID {} (PID now belongs to {})."
                      .format(sibling_pid, p.exe()))
                moreps.remove_pid(sibling_pid)
                continue
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
    theme_path = find_resource('forest-light.tcl')
    if theme_path:
        pass
        # root.tk.call('source', theme_path)
        # ttk.Style().theme_use('forest-light')
        # TODO: fix slowness before committing uncommented.
    root.title("BackupNow")

    frame = BackupNowFrame(root)

    root.protocol('WM_DELETE_WINDOW', frame.quit_to_tray)
    root.withdraw()  # hide immediately after prepared
    root.after(10, frame.quit_to_tray)  # Show icon since window is hidden!
    root.mainloop()
    return 0


if __name__ == "__main__":
    process = current_process()
    process.name = "BackupNow-Tray"
    sys.exit(main())
