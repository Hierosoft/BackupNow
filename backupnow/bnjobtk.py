import sys

from collections import OrderedDict
from logging import getLogger
from typing import Dict, Literal, Mapping

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
        self.meta = None  # type: dict[str, str]
        self.widgets = {}  # type dict[str, tk.Widget]


class JobTk(BNJob):  # (ttk.Frame):
    # def __init__(self, *args, **kwargs):
    # ttk.Frame.__init__(self, *args, **kwargs)
    columns = {
        'enabled': 0,
        'name': 1,  # handled by parent for job, by JobTk for operation
        'progress': 2,
        'ran': 3,
        'run': 4,
    }

    def __init__(self, parent, parent_row, show=True):
        assert parent_row is not None
        self.row = parent_row
        self.first_row = self.row  # type: int
        container = parent  # self
        self.container = container
        # self.name_v = tk.StringVar(container)
        container.columnconfigure(0, weight=0)  # 0: fixed size
        container.columnconfigure(1, weight=3)
        container.columnconfigure(2, weight=1)
        container.columnconfigure(3, weight=1)
        container.columnconfigure(4, weight=1)
        self.name = None
        self.widgets = {}  # type: dict[str, ttk.Label|ttk.Checkbutton|ttk.Label|ttk.Progressbar|ttk.Combobox]
        # self.widgets['name'] = ttk.Label(container, anchor=tk.W)
        # self.widgets['name'] = ttk.Combobox(container)
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
        self.header_rows = 1
        if show:
            self.showHeader()
        self.op_groups = {}  # type: dict[int, OperationInfo]

    def showHeader(self):
        self.widgets['enabled'].grid(column=self.columns['enabled'],
                                     row=self.row, sticky=tk.W)
        # self.widgets['edit'].grid(column=2, row=self.row)
        self.progress_kwargs = {'sticky': tk.EW}  # type: dict[str, str]
        self.widgets['progress'].grid(column=self.columns['progress'],
                                      row=self.row, **self.progress_kwargs) # type: ignore
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
        self.row += self.header_rows

    def set_enabled(self, enabled):
        # if state: self.enabled_cb.select()
        # else: self.enabled_cb.deselect()
        state = tk.NORMAL if enabled else tk.DISABLED
        self.enabled_v.set(enabled)
        self.widgets['ran'].config(state=state) # type: ignore

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

    def add_operation(self, key, operation, show=True):
        # type: (int, dict[str, str], bool) -> None
        container = self.container  # self
        group = OperationInfo()
        if key in self.op_groups:
            raise KeyError("{} is already in op_groups for the {} job."
                           .format(repr(key), repr(self.name)))
        group.meta = operation
        if not show:
            return
        self.op_groups[key] = group
        self.showOperation(key)

    def hideOperations(self):
        for key in self.op_groups:
            self.hideOperation(key)

    def hideOperation(self, key):
        if self.row <= self.first_row + 1:
            raise ValueError(
                "Tried to hide operation after first row {} but row is {}"
                .format(self.first_row, self.row))
        group = self.op_groups[key]  # type: OperationInfo
        for widget in group.widgets.items():
            widget.grid_forget()
        self.row -= 1

    def grid(self):
        self.showHeader()
        self.showOperations()

    def grid_forget(self):
        for group in self.op_groups.values():
            for _, widget in group.widgets.items():
                widget.grid_forget()
            self.row -= 1
        self.hideHeader()

    def hideHeader(self):
        if self.row != self.first_row + 1:
            raise ValueError(
                "Tried to hide first row {} but row is {}"
                .format(self.first_row, self.row))
        for _, widget in self.widgets.items():
            widget.grid_forget()
        self.row -= self.header_rows

    def set_name(self, name):
        self.name = name
        # See parent instead (jobsDropdown) for:
        # if isinstance(self.widgets['name'], ttk.Combobox):
        #     self.widgets['name'].set(name)  # type: ignore
        # else:
        #     self.widgets['name'].config(text=name)  # type: ignore

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
            progressbar = self.op_groups[operation_key].widgets['progress']

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

    def showOperation(self, key):
        container = self.container
        group = self.op_groups[key]
        operation = group.meta
        source = operation.get('source')
        if not source:
            source = "(source not set)"
        ran = operation.get('ran')
        if not ran:
            ran = "Never"
        # NOTE: "ran" is typically handled by tasks, so this "ran" is
        #   only for reference
        if 'source' not in group.widgets:
            group.widgets['source'] = ttk.Label(container, text=source)
        group.widgets['source'].grid(column=self.columns['name'],
                                     # columnspan=len(self.columns)-2,
                                     row=self.row, sticky=tk.EW)
        if 'progress' not in group.widgets:
            group.widgets['progress'] = ttk.Progressbar(container)
        group.widgets['progress'].grid(column=self.columns['progress'],
                                       row=self.row,
                                       **self.progress_kwargs)  # type: ignore
        if 'ran' not in group.widgets:
            group.widgets['ran'] = ttk.Label(container, text=ran)
        group.widgets['ran'].grid(column=self.columns['ran'], row=self.row)
        self.row += 1

    def showOperations(self):
        for key in self.op_groups:
            self.showOperation(key)
