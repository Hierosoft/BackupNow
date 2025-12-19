"""
VerticalScrolledFrame
based on https://stackoverflow.com/a/16198198/4541104
which is based on
https://web.archive.org/web/20170514022131id_/http://tkinter.unpythonic.net/wiki/VerticalScrolledFrame
"""
import sys

if sys.version_info.major >= 3:
    # from tkinter import *
    import tkinter as tk
    from tkinter import ttk
    from tkinter import messagebox
else:
    import Tkinter as tk  # type: ignore
    import ttk  # type: ignore
    import tkMessageBox as messagebox  # noqa:F401 #type:ignore


class VerticalScrolledFrame(ttk.Frame):  # type: ignore
    """A pure Tkinter scrollable frame that actually works!
    * Use the 'interior' attribute to place widgets inside
    * Construct and pack/place/grid normally.
    * This frame only allows vertical scrolling.
    """
    def __init__(self, parent, *args, **kw):
        ttk.Frame.__init__(self, parent, *args, **kw)

        # Create a canvas object and a vertical scrollbar for scrolling it.
        self.vscrollbar = vscrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL)
        self.vscrollbar.pack(fill=tk.Y, side=tk.RIGHT, expand=tk.FALSE)
        self.canvas = canvas = tk.Canvas(self, bd=0, highlightthickness=0,
                                yscrollcommand=self.vscrollbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=tk.TRUE)
        self.vscrollbar.config(command=self.canvas.yview)

        # Reset the view
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)

        # Create a frame inside the canvas which will be scrolled with it.
        self.interior = interior = ttk.Frame(self.canvas)
        interior_id = self.canvas.create_window(0, 0, window=interior,
                                                anchor=tk.NW)

        # Track changes to the canvas and frame width and sync them,
        # also updating the scrollbar.
        def _configure_interior(event):
            # type: (tk.Event) -> None
            # Update the scrollbars to match the size of the inner frame.
            size = (interior.winfo_reqwidth(), interior.winfo_reqheight())
            self.canvas.config(scrollregion=(0, 0, size[0], size[1]))
            if interior.winfo_reqwidth() != self.canvas.winfo_width():
                # Update the canvas's width to fit the inner frame.
                self.canvas.config(width=interior.winfo_reqwidth())
        interior.bind('<Configure>', _configure_interior)

        def _configure_canvas(event):
            if interior.winfo_reqwidth() != self.canvas.winfo_width():
                # Update the inner frame's width to fill the canvas.
                self.canvas.itemconfigure(interior_id, width=self.canvas.winfo_width())
        self.canvas.bind('<Configure>', _configure_canvas)

    def destroy(self):
        """
        Clear bindings/connections to prevent callbacks on destroyed widgets
        """
        if hasattr(self, 'interior') and self.interior.winfo_exists():
            self.interior.unbind('<Configure>')
        if hasattr(self, 'canvas') and self.canvas.winfo_exists():
            self.canvas.unbind('<Configure>')
            self.canvas.configure(yscrollcommand='')
        if hasattr(self, 'vscrollbar') and self.vscrollbar.winfo_exists():
            self.vscrollbar.configure(command='')
        super(VerticalScrolledFrame, self).destroy()


if __name__ == "__main__":

    class SampleApp(tk.Tk):  # type: ignore
        def __init__(self, *args, **kwargs):
            root = self
            tk.Tk.__init__(self, *args, **kwargs)
            self.geometry("600x100+100+100")
            root.title(
                "You ran the wrong file."
                " This is just the bnscrollableframe.py demo.")
            self.frame = VerticalScrolledFrame(root)
            self.frame.pack(fill=tk.BOTH)
            # self.label = ttk.Label(self, text="Shrink window for scrollbar.")
            # self.label.pack()
            buttons = []
            for i in range(10):
                buttons.append(ttk.Button(self.frame.interior,
                                          text="Button " + str(i)))
                buttons[-1].pack()

    app = SampleApp()
    app.mainloop()
