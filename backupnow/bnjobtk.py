from collections import OrderedDict
import sys

from logging import getLogger

from backupnow.bnjob import BNJob
from backupnow.bnlogging import emit_cast

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

    Attributes:
        meta (dict): An operation dict from the operations list in
            settings.
    """
    def __init__(self):
        self.meta = None
        self.widgets = {}


class JobTk(BNJob):  # (ttk.Frame):
    # def __init__(self, *args, **kwargs):
    # ttk.Frame.__init__(self, *args, **kwargs)

    def __init__(self, parent, parent_row):
        self.row = parent_row
        container = parent  # self
        self.container = container
        # self.name_v = tk.StringVar(container)
        container.columnconfigure(0, weight=0)  # 0: fixed size
        container.columnconfigure(1, weight=3)
        container.columnconfigure(2, weight=1)
        container.columnconfigure(3, weight=1)
        container.columnconfigure(4, weight=1)
        self.columns = {
            'enabled': 0,
            'name': 1,
            'progress': 2,
            'ran': 3,
            'run': 4,
        }
        self.name = None
        self.widgets = {}
        self.widgets['name'] = ttk.Label(container, anchor=tk.W)
        self.enabled_v = tk.BooleanVar(container)
        self.widgets['enabled'] = ttk.Checkbutton(
            container,
            onvalue=True,
            offvalue=False,
            variable=self.enabled_v,
            state=tk.DISABLED
        )
        self.widgets['edit'] = ttk.Button(container, text="Edit",
                                          state=tk.DISABLED)
        self.widgets['ran'] = ttk.Label(container, text="Ran:")
        self.widgets['run'] = ttk.Button(container, text="Run",
                                         state=tk.NORMAL,
                                         command=self.run)
        self.widgets['progress'] = ttk.Progressbar(container)
        self.widgets['enabled'].grid(column=self.columns['enabled'],
                                     row=self.row, sticky=tk.W)
        self.widgets['name'].grid(column=self.columns['name'],
                                  row=self.row, sticky=tk.NSEW)
        # self.widgets['edit'].grid(column=2, row=self.row)
        self.progress_kwargs = {'sticky': tk.EW}
        self.widgets['progress'].grid(column=self.columns['progress'],
                                      row=self.row, **self.progress_kwargs)
        self.widgets['ran'].grid(
            column=self.columns['ran'],
            row=self.row,
            # sticky=tk.W,
        )
        self.widgets['run'].grid(
            column=self.columns['run'],
            row=self.row,
            # sticky=tk.W,
        )
        # self.header_rows = 1
        # self.row += self.header_rows
        self.op_groups = {}

    def set_enabled(self, enabled):
        # if state: self.enabled_cb.select()
        # else: self.enabled_cb.deselect()
        state = tk.NORMAL if enabled else tk.DISABLED
        self.enabled_v.set(enabled)
        self.widgets['ran'].config(state=state)

    def get_enabled(self):
        # self.enabled_cb.invoke()
        # state = checkbutton.select() == checkbutton.deselect()
        return self.enabled_v.get()

    def run(self):
        if self.meta.get('enabled') is False:
            raise RuntimeError("Tried to run job name={} but enabled is False."
                               .format(repr(self.name)))
        if self.meta.get('operations') is None:
            raise ValueError('operations is None for job name={}.'
                             .format(repr(self.name)))
        if not isinstance(self.meta['operations'], list):
            raise TypeError(
                "Expected list for 'operations' in job name={} but got {}"
                .format(repr(self.name), emit_cast(self.meta['operations'])))
        for operation in self.meta['operations']:
            self._run_operation(operation)  # See superclass

    def add_operation(self, key, operation):
        container = self.container  # self
        group = OperationInfo()
        if key in self.op_groups:
            raise KeyError("{} is already in op_groups for the {} job."
                           .format(repr(key), repr(self.name)))
        group.meta = operation
        source = operation.get('source')
        if not source:
            source = "(source not set)"
        group.widgets['source'] = ttk.Label(container, text=source)
        group.widgets['source'].grid(column=self.columns['name'],
                                     # columnspan=len(self.columns)-2,
                                     row=self.row, sticky=tk.EW)
        # self.row += 1
        ran = operation.get('ran')
        if not ran:
            ran = "Never"
        # NOTE: "ran" is typically handled by tasks, this "ran" is only
        #   for reference
        group.widgets['progress'] = ttk.Progressbar(container)
        group.widgets['progress'].grid(column=self.columns['progress'],
                                       row=self.row,
                                       **self.progress_kwargs)
        group.widgets['ran'] = ttk.Label(container, text=ran)
        group.widgets['ran'].grid(column=self.columns['ran'], row=self.row)
        self.row += 1
        self.op_groups[key] = group

    def grid_forget(self):
        for group in self.op_groups:
            for _, widget in group.widgets.items():
                widget.grid_forget()
        for _, widget in self.widgets.items():
            widget.grid_forget()

    def set_name(self, name):
        self.name = name
        self.widgets['name'].config(text=name)

    def set_meta(self, meta):
        if not isinstance(meta, (dict, OrderedDict)):
            raise TypeError("Expected dict, got {}"
                            .format(emit_cast(meta)))
        if 'enabled' not in meta:
            logger.warning(
                "JobTk (name={}): 'enabled' not set (default: True)"
                .format(repr(self.name)))
        elif not isinstance(meta['enabled'], bool):
            raise TypeError("Expected job 'enabled' bool, got {}"
                            .format(emit_cast(meta['enabled'])))
        if meta.get('operations') is None:
            logger.warning(
                "JobTk (name={}): 'operations' not set (default: [])"
                .format(repr(self.name)))
            meta['operations'] = []
        elif not isinstance(meta['operations'], list):
            raise TypeError("Expected job 'operations' list, got {}"
                            .format(emit_cast(meta['operations'])))
        self.meta = meta

    def set_progress(self, ratio, operation_key=None):
        """Set the progress bar.

        Args:
            ratio (float): From 0 to 1.
            operation_key (str, optional): If present, set the separate
                progress bar for the operation. Defaults to None
                (to use the overall progress bar).
        """
        progressbar = self.widgets['progress']
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
