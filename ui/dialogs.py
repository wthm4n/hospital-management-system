import tkinter as tk
from tkinter import ttk
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import *
from ui.widgets import Btn, FloatEntry, FloatCombo, FloatText


class Modal(tk.Toplevel):
    def __init__(self, parent, title, width=700, height=None):
        super().__init__(parent)
        self.title(title)
        self.configure(bg=C_SURFACE)
        self.resizable(False, False)
        self.grab_set()
        self.result = None
        w = width
        self.geometry(f"{w}x{height}" if height else f"{w}x600")
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        y = parent.winfo_rooty() + 40
        self.geometry(f"+{x}+{y}")
        tk.Frame(self, bg=C_PRIMARY, height=3).pack(fill="x")
        hdr = tk.Frame(self, bg=C_SURFACE, pady=18, padx=24)
        hdr.pack(fill="x")
        tk.Label(hdr, text=title, font=F_HEAD, bg=C_SURFACE, fg=C_WHITE).pack(side="left")
        tk.Button(hdr, text="✕", font=F_BODY, bg=C_SURFACE, fg=C_MUTED,
                  relief="flat", cursor="hand2", bd=0,
                  command=self.destroy).pack(side="right")
        self.body = tk.Frame(self, bg=C_SURFACE, padx=24, pady=10)
        self.body.pack(fill="both", expand=True)
        self.scroll_canvas = None

    def make_scrollable(self):
        canvas = tk.Canvas(self.body, bg=C_SURFACE, highlightthickness=0)
        vs = ttk.Scrollbar(self.body, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vs.set)
        vs.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(canvas, bg=C_SURFACE)
        win   = canvas.create_window((0, 0), window=inner, anchor="nw")
        def on_resize(e):
            canvas.itemconfig(win, width=canvas.winfo_width())
        def on_frame(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.bind("<Configure>", on_resize)
        inner.bind("<Configure>",  on_frame)
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(-1*(e.delta//120), "units"))
        self.scroll_canvas = canvas
        self.body = inner
        return inner

    def footer(self, on_save, save_text="Save", show_cancel=True):
        bar = tk.Frame(self, bg=C_SURFACE2, padx=24, pady=14)
        bar.pack(fill="x", side="bottom")
        if show_cancel:
            Btn(bar, "Cancel", self.destroy, "ghost").pack(side="left")
        Btn(bar, save_text, on_save, "primary").pack(side="right")


class FormBuilder:
    def __init__(self, parent, fields: list, cols=2):
        self.fields   = fields
        self._widgets = {}
        self._build(parent, cols)

    def _build(self, parent, cols):
        outer = tk.Frame(parent, bg=C_SURFACE)
        outer.pack(fill="both", expand=True)
        row_frame = None
        for i, field in enumerate(self.fields):
            if i % cols == 0:
                row_frame = tk.Frame(outer, bg=C_SURFACE)
                row_frame.pack(fill="x", pady=5)
            cell = tk.Frame(row_frame, bg=C_CARD,
                            highlightbackground=C_BORDER, highlightthickness=1)
            cell.pack(side="left", fill="x", expand=True, padx=5, pady=3)
            inner = tk.Frame(cell, bg=C_CARD, padx=14, pady=12)
            inner.pack(fill="both", expand=True)
            name    = field["name"]
            label   = field.get("label", name.replace("_", " ").title())
            ftype   = field.get("type", "entry")
            default = field.get("default", "")
            req     = field.get("required", False)
            span    = field.get("span", 1)
            if span == 2 and row_frame:
                cell.pack_configure(fill="x", expand=True)
                row_frame = tk.Frame(outer, bg=C_SURFACE)
                row_frame.pack(fill="x", pady=5)
                cell.pack_forget()
                cell = tk.Frame(row_frame, bg=C_CARD,
                                highlightbackground=C_BORDER, highlightthickness=1)
                cell.pack(side="left", fill="x", expand=True, padx=5, pady=3)
                inner = tk.Frame(cell, bg=C_CARD, padx=14, pady=12)
                inner.pack(fill="both", expand=True)

            if ftype == "combo":
                w = FloatCombo(inner, label, field.get("values", []),
                               required=req, width=24)
                if default:
                    w.set(default)
                w.pack(fill="x")
                self._widgets[name] = w
            elif ftype == "text":
                w = FloatText(inner, label, height=field.get("height", 3))
                w.set(default)
                w.pack(fill="x")
                self._widgets[name] = w
            else:
                w = FloatEntry(inner, label,
                               placeholder=field.get("placeholder", ""),
                               secret=field.get("secret", False),
                               required=req, width=26)
                w.set(default)
                w.pack(fill="x")
                self._widgets[name] = w

    def get_all(self) -> dict:
        result = {}
        for name, widget in self._widgets.items():
            result[name] = widget.get()
        return result

    def set_all(self, data: dict):
        for name, widget in self._widgets.items():
            if name in data:
                widget.set(data[name])

    def validate_required(self) -> list:
        errors = []
        for field in self.fields:
            if field.get("required") and not self._widgets[field["name"]].get():
                errors.append(field.get("label", field["name"]))
        return errors


def confirm(parent, message, title="Confirm"):
    dialog = Modal(parent, title, width=400, height=200)
    dialog.geometry(f"400x200")
    tk.Label(dialog.body, text=message, font=F_BODY,
             bg=C_SURFACE, fg=C_TEXT, wraplength=340).pack(pady=20)
    result = {"yes": False}
    def yes():
        result["yes"] = True
        dialog.destroy()
    bar = tk.Frame(dialog, bg=C_SURFACE2, padx=20, pady=14)
    bar.pack(fill="x", side="bottom")
    Btn(bar, "Cancel", dialog.destroy, "ghost").pack(side="left")
    Btn(bar, "Confirm", yes, "danger").pack(side="right")
    dialog.wait_window()
    return result["yes"]


def ask_value(parent, prompt, title="Input", input_type="string"):
    dialog = Modal(parent, title, width=380, height=220)
    tk.Label(dialog.body, text=prompt, font=F_BODY,
             bg=C_SURFACE, fg=C_MUTED, wraplength=330).pack(pady=(10, 8), anchor="w")
    var = tk.StringVar()
    inner = tk.Frame(dialog.body, bg=C_SURFACE2,
                     highlightbackground=C_BORDER, highlightthickness=1)
    inner.pack(fill="x")
    entry = tk.Entry(inner, textvariable=var, font=F_BODY, bg=C_SURFACE2,
                     fg=C_TEXT, relief="flat", insertbackground=C_WHITE)
    entry.pack(fill="x", ipady=9, padx=10)
    entry.focus_set()
    result = {"value": None}
    def submit():
        result["value"] = var.get().strip()
        dialog.destroy()
    bar = tk.Frame(dialog, bg=C_SURFACE2, padx=20, pady=14)
    bar.pack(fill="x", side="bottom")
    Btn(bar, "Cancel", dialog.destroy, "ghost").pack(side="left")
    Btn(bar, "OK", submit, "primary").pack(side="right")
    entry.bind("<Return>", lambda e: submit())
    dialog.wait_window()
    return result["value"]


def show_detail(parent, title, rows: list):
    dialog = Modal(parent, title, width=520, height=None)
    for label, value in rows:
        row = tk.Frame(dialog.body, bg=C_SURFACE)
        row.pack(fill="x", pady=3)
        tk.Label(row, text=label + ":", font=F_LABEL, bg=C_SURFACE,
                 fg=C_MUTED, width=20, anchor="e").pack(side="left", padx=(0, 12))
        tk.Label(row, text=str(value) if value else "—", font=F_BODY,
                 bg=C_SURFACE, fg=C_WHITE, anchor="w").pack(side="left")
    Btn(dialog.body, "Close", dialog.destroy, "ghost").pack(pady=16)
    dialog.update_idletasks()
    needed = len(rows) * 34 + 180
    dialog.geometry(f"520x{min(needed, 600)}")
