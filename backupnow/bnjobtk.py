import sys

from logging import getLogger

if sys.version_info.major >= 3:
    # from tkinter import *
    import tkinter as tk
    from tkinter import ttk
    from tkinter import messagebox
else:
    import Tkinter as tk  # type: ignore
    import ttk  # type: ignore
    import tkMessageBox as messagebox  # noqa:F401 #type:ignore


logger = getLogger(__name__)


class OperationInfo:  # (tk.Frame):
    """Manage one operation of a job.

    Attribs:
        meta (dict): An operation dict from the operations list in
            settings.
    """
    def __init__(self):
        self.meta = None
        self.widgets = {}


class JobTk(ttk.Frame):
    def __init__(self, *args, **kwargs):
        # kwargs['bg'] = "white"
        ttk.Frame.__init__(self, *args, **kwargs)
        # self.name_v = tk.StringVar(self)
        self.columnconfigure(0, weight=3)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=1)
        self.columnconfigure(3, weight=1)
        self.columnconfigure(4, weight=1)
        self.name = None
        self.name_label = ttk.Label(self, anchor=tk.W)
        self.enabled_v = tk.BooleanVar(self)
        self.enabled_cb = ttk.Checkbutton(self, onvalue=True, offvalue=False,
                                          variable=self.enabled_v,
                                          state=tk.DISABLED)
        self.edit_button = ttk.Button(self, text="Edit", state=tk.DISABLED)
        self.run_button = ttk.Button(self, text="Run", state=tk.DISABLED)
        self.progressbar = ttk.Progressbar(self)
        self.enabled_cb.grid(column=0, row=0, sticky=tk.W)
        self.name_label.grid(column=1, row=0, sticky=tk.NSEW)
        # self.edit_button.grid(column=2, row=0)
        self.progressbar.grid(column=2, row=0, sticky=tk.W)
        self.run_button.grid(column=3, row=0, sticky=tk.E)
        self.header_rows = 1
        self.columns = 4
        self.row = self.header_rows
        self.op_groups = {}

    def set_enabled(self, enabled):
        # if state: self.enabled_cb.select()
        # else: self.enabled_cb.deselect()
        state = tk.NORMAL if enabled else tk.DISABLED
        self.enabled_v.set(enabled)
        self.run_button.config(state=state)

    def get_enabled(self):
        # self.enabled_cb.invoke()
        # state = checkbutton.select() == checkbutton.deselect()
        return self.enabled_v.get()

    def add_operation(self, key, operation):
        group = OperationInfo()
        if key in self.op_groups:
            raise KeyError("{} is already in op_groups for the {} job."
                           .format(repr(key), repr(self.name)))
        group.meta = operation
        source = operation.get('source')
        if not source:
            source = "(source not set)"
        group.widgets['source'] = ttk.Label(self, text=source)
        group.widgets['source'].grid(column=0, columnspan=self.columns-2,
                                     row=self.row)
        # self.row += 1
        ran = operation.get('ran')
        if not ran:
            ran = "Last run: Never"
        # NOTE: "ran" is typically handled by tasks, this "ran" is only
        #   for reference
        group.widgets['progress'] = ttk.Progressbar(self)
        group.widgets['progress'].grid(column=self.columns-2, row=self.row)
        group.widgets['ran'] = ttk.Label(self, text=ran)
        group.widgets['ran'].grid(column=self.columns-1, row=self.row)
        self.row += 1
        self.op_groups[key] = group

    def set_name(self, name):
        self.name = name
        self.name_label.config(text=name)

    def set_progress(self, ratio, operation_key=None):
        """Set the progress bar.

        Args:
            ratio (float): From 0 to 1.
            operation_key (str, optional): If present, set the separate
                progress bar for the operation. Defaults to None
                (to use the overall progress bar).
        """
        progressbar = self.progressbar
        if operation_key is not None:
            progressbar = self.op_groups.widgets['progress']

        if not ratio:
            return False
        if ratio < 0:
            logger.warning("ratio={}".format(ratio))
            ratio = 0
        elif ratio > 1.0:
            logger.warning("ratio={}".format(ratio))
            ratio = 1.0
        progressbar['value'] = ratio * progressbar['maximum']
        return True

    def process_event(self, event):
        """Process a backend progress event and display it.

        Args:
            event (dict): Attributes of the event.
                - 'ratio' (float): 0 to 1.
                - 'operation_key' (str, optional): The specific operation if
                  any (See set_progress for details).
        """
        ratio = event.get('ratio')
        if ratio:
            self.set_progress(ratio, operation_key=event.get('operation_key'))
