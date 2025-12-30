import copy
import sys

from collections import OrderedDict
from logging import getLogger
from typing import Callable, Dict, Literal, Mapping

from backupnow import formatted_ex
from backupnow.bncore import NOT_ON_DESTINATION
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

    def setField(self, key, value):
        widget = self.widgets[key]
        if isinstance(widget, (tk.Label, ttk.Label)):
            widget['text'] = value
        else:
            NotImplementedError(
                "Setting a(n) {} field value is not implemented"
                .format(type(widget).__name__))


class JobTk(BNJob):  # (ttk.Frame):
    """One Job which manages its operations.
    Args:
        parent (tk.Widget): Any container.
        parent_row (int): Row in the container to use (affects self.row
            on adding row(s) during construction).
        run_fn (Callable): The function which should run when "Run" is
            pressed. The caller must keep track of what job is selected and
            call job.run() during this function.
        show (bool, optional): Whether to show this job (add widgets).
            Defaults to True.
    """
    # def __init__(self, *args, **kwargs):
    # ttk.Frame.__init__(self, *args, **kwargs)
    columns = {
        'enabled': 0,
        'name': 1,  # handled by parent for job, by JobTk for operation
        'progress': 2,
        'ran': 3,
        'run': 4,
        'message': 5,
    }

    def __init__(self, parent, parent_row, run_fn, show=True):
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
        container.columnconfigure(5, weight=0)
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
                                         command=run_fn)
        self.widgets['progress'] = ttk.Progressbar(container)
        self.widgets['message'] = ttk.Label(container)
        self.header_rows = 1
        if show:
            self.showHeader()
        self.op_groups = {}  # type: dict[int, OperationInfo]

    def setOpMessage(self, key, message):
        """Set message for a specific operation

        Args:
            key (Union[int,str]): Same key used for add_operation.
            message (str): Any text.
        """
        self.op_groups[key].setField('message', message)

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
        self.widgets['message'].grid(
            column=self.columns['message'],
            row=self.header_rows,
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

    def run_all(self, destination, **kwargs):
        """See _run_all."""
        def default_status_cb(d):
            print("[run_all default_status_cb] {}".format(d))
        if 'status_cb' not in kwargs:
            kwargs['status_cb'] = default_status_cb
        try:
            return self._run_all(destination, **kwargs)
        except Exception as ex:
            kwargs['status_cb']({
                'error': formatted_ex(ex),
            })
            raise

    def _run_all(self, destination, require_subdirectory=True,
                 event_template=None, status_cb=None):
        # type: (str, bool, dict, Callable) -> dict
        """Run every operation in the job. See _run_operation
        for args not listed here and other fields in dict sent to
        status_cb.

        Args:
            status_cb (Callable): Callback function that accepts a
            dictionary with keys such as:
            - 'source_errors' (dict): Key is operations[i]['source']
              string (or int index if job is missing a 'source'),
              where operations[i] is each operation in the
              'operations' key of this job's metadata.
            - and keys in _run_operation documentation.
        """
        if event_template is None:
            event = {'done': False}  # type: dict
        else:
            event = copy.deepcopy(event_template)  # type: dict

        def default_status_cb(d):
            print("[run_all default_status_cb] {}".format(d))
        if status_cb is None:
            status_cb = default_status_cb
        # event['message'] = "Checking settings..."
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
        if not self.meta['operations']:
            raise TypeError(
                "'operations' is an empty list in in job name={} but got {}"
                .format(repr(self.name), emit_cast(self.meta['operations'])))
        op_count = len(self.meta['operations'])
        event['message'] = ("Running {} operation(s)...".format(op_count))
        status_cb(event)
        del event['message']
        event['done'] = False
        event['operations_total'] = op_count
        event['source_errors'] = OrderedDict()
        for idx, operation in enumerate(self.meta['operations']):
            event.update({
                # 'message': "Running operation {}/{}...".format(
                #     idx+1, op_count),
                'message': None,
                'ratio': float(idx)/float(op_count),
                'operations_done': idx,
            })
            print("[_run_all] {}".format(event['message']))
            status_cb(event)
            source = operation.get('source')
            if not source:
                source = idx
            try:
                if 'error' in event:
                    del event['error']
                op_results = self._run_operation(
                    operation,
                    destination,
                    event_template=event,
                    require_subdirectory=require_subdirectory,
                    status_cb=status_cb,
                )  # See superclass
                op_error = op_results.get('error')
                if op_error:
                    event['source_errors'][source] = op_error
                elif op_results['missing_dst_folders']:
                    event['source_errors'][source] = NOT_ON_DESTINATION
            except Exception as ex:
                event['source_errors'][source] = formatted_ex(ex)
        event.update({
            'message': "operation {}/{}...".format(op_count, op_count),
            'ratio': 1.0,
            'done': True,
        })
        status_cb(event)
        return event  # also return it, in case of synchronous operation

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
        if 'message' not in group.widgets:
            group.widgets['message'] = ttk.Label(container)
        group.widgets['message'].grid(column=self.columns['message'],
                                      row=self.row)
        self.row += 1

    def showOperations(self):
        for key in self.op_groups:
            self.showOperation(key)
