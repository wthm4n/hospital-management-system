import tkinter as tk
from tkinter import ttk
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import *


def apply_theme():
    style = ttk.Style()
    style.theme_use("clam")
    style.configure(".",
        background=C_BG, foreground=C_TEXT, font=F_BODY,
        troughcolor=C_SURFACE, fieldbackground=C_SURFACE2,
        selectbackground=C_PRIMARY, selectforeground=C_WHITE,
        borderwidth=0, relief="flat")
    style.configure("TNotebook",         background=C_BG,       borderwidth=0)
    style.configure("TNotebook.Tab",     background=C_SURFACE,  foreground=C_MUTED,
                    padding=[18, 9], font=F_BTN, borderwidth=0)
    style.map("TNotebook.Tab",
        background=[("selected", C_PRIMARY)],
        foreground=[("selected", C_WHITE)])
    style.configure("HMS.Treeview",
        background=C_CARD, fieldbackground=C_CARD,
        foreground=C_TEXT, rowheight=32, font=F_BODY,
        borderwidth=0, relief="flat")
    style.configure("HMS.Treeview.Heading",
        background=C_SURFACE2, foreground=C_MUTED,
        font=F_BTN, relief="flat", borderwidth=0)
    style.map("HMS.Treeview",
        background=[("selected", C_PRIMARY)],
        foreground=[("selected", C_WHITE)])
    style.configure("Vertical.TScrollbar",
        background=C_SURFACE2, troughcolor=C_SURFACE,
        arrowcolor=C_MUTED, borderwidth=0, relief="flat")
    style.configure("Horizontal.TScrollbar",
        background=C_SURFACE2, troughcolor=C_SURFACE,
        arrowcolor=C_MUTED, borderwidth=0, relief="flat")
    style.configure("TCombobox",
        fieldbackground=C_SURFACE2, background=C_SURFACE2,
        foreground=C_TEXT, arrowcolor=C_MUTED,
        borderwidth=1, relief="solid")
    style.map("TCombobox",
        fieldbackground=[("readonly", C_SURFACE2)],
        foreground=[("readonly", C_TEXT)])
    style.configure("TEntry",
        fieldbackground=C_SURFACE2, foreground=C_TEXT,
        insertcolor=C_WHITE, borderwidth=1)
    style.configure("TSeparator", background=C_BORDER)


class Btn(tk.Button):
    STYLES = {
        "primary":   (C_PRIMARY,  C_WHITE,  C_PRIMARY_H),
        "success":   (C_GREEN,    "#0a0a0a", "#00b07a"),
        "danger":    (C_RED,      C_WHITE,  "#ff2a4d"),
        "warning":   (C_YELLOW,   "#0a0a0a", "#e6bc00"),
        "ghost":     (C_SURFACE2, C_MUTED,  C_SURFACE),
        "outline":   (C_SURFACE,  C_PRIMARY, C_SURFACE2),
        "cyan":      (C_CYAN,     "#0a0a0a", "#009bb8"),
    }

    def __init__(self, parent, text, cmd=None, style="primary", w=None, h=None, icon="", **kw):
        bg, fg, hover = self.STYLES.get(style, self.STYLES["primary"])
        label = f"{icon}  {text}" if icon else text
        super().__init__(parent, text=label, command=cmd, bg=bg, fg=fg,
                         font=F_BTN, relief="flat", cursor="hand2",
                         activebackground=hover, activeforeground=fg,
                         padx=16, pady=8, bd=0, **kw)
        if w: self.config(width=w)
        if h: self.config(height=h)
        self._bg, self._hover = bg, hover
        self.bind("<Enter>", lambda e: self.config(bg=self._hover))
        self.bind("<Leave>", lambda e: self.config(bg=self._bg))


class Card(tk.Frame):
    def __init__(self, parent, padx=16, pady=16, **kw):
        super().__init__(parent, bg=C_CARD, **kw)
        self._pad = {"padx": padx, "pady": pady}

    def body(self):
        f = tk.Frame(self, bg=C_CARD)
        f.pack(fill="both", expand=True, **self._pad)
        return f


class StatCard(tk.Frame):
    def __init__(self, parent, title, value, subtitle="", color=C_PRIMARY, icon="◆", **kw):
        super().__init__(parent, bg=C_CARD, **kw)
        self.config(padx=20, pady=18)
        top = tk.Frame(self, bg=C_CARD)
        top.pack(fill="x")
        tk.Label(top, text=icon, font=("Segoe UI", 20), bg=C_CARD, fg=color).pack(side="left")
        self._val = tk.Label(self, text=str(value), font=("Segoe UI", 28, "bold"), bg=C_CARD, fg=C_WHITE)
        self._val.pack(anchor="w", pady=(4, 0))
        tk.Label(self, text=title, font=F_LABEL, bg=C_CARD, fg=C_MUTED).pack(anchor="w")
        if subtitle:
            tk.Label(self, text=subtitle, font=F_SMALL, bg=C_CARD, fg=color).pack(anchor="w")
        tk.Frame(self, bg=color, height=3).pack(fill="x", side="bottom")

    def set(self, value):
        self._val.config(text=str(value))


class SearchEntry(tk.Frame):
    def __init__(self, parent, placeholder="Search...", on_change=None, width=28, **kw):
        super().__init__(parent, bg=C_SURFACE2, **kw)
        self.config(highlightbackground=C_BORDER, highlightthickness=1)
        tk.Label(self, text="⌕", font=("Segoe UI", 13), bg=C_SURFACE2, fg=C_MUTED).pack(side="left", padx=(8,2))
        self.var = tk.StringVar()
        self._ph = placeholder
        self.entry = tk.Entry(self, textvariable=self.var, font=F_BODY,
                              bg=C_SURFACE2, fg=C_MUTED, relief="flat",
                              insertbackground=C_WHITE, width=width, bd=0)
        self.entry.pack(side="left", ipady=7, padx=(0, 10))
        self.entry.insert(0, placeholder)
        self.entry.bind("<FocusIn>",  self._focus_in)
        self.entry.bind("<FocusOut>", self._focus_out)
        if on_change:
            self.var.trace_add("write", lambda *a: on_change())

    def _focus_in(self, e):
        if self.var.get() == self._ph:
            self.entry.delete(0, "end")
            self.entry.config(fg=C_TEXT)

    def _focus_out(self, e):
        if not self.var.get():
            self.entry.insert(0, self._ph)
            self.entry.config(fg=C_MUTED)

    def get(self):
        v = self.var.get()
        return "" if v == self._ph else v

    def set(self, v):
        self.var.set(v)
        self.entry.config(fg=C_TEXT if v else C_MUTED)


class FloatEntry(tk.Frame):
    def __init__(self, parent, label, placeholder="", secret=False, width=22, required=False, **kw):
        super().__init__(parent, bg=C_CARD, **kw)
        lbl = label + (" *" if required else "")
        tk.Label(self, text=lbl, font=F_LABEL, bg=C_CARD, fg=C_MUTED).pack(anchor="w", pady=(0,3))
        inner = tk.Frame(self, bg=C_SURFACE2,
                         highlightbackground=C_BORDER, highlightthickness=1)
        inner.pack(fill="x")
        self.var = tk.StringVar()
        self.entry = tk.Entry(inner, textvariable=self.var, font=F_BODY,
                              bg=C_SURFACE2, fg=C_TEXT, relief="flat",
                              insertbackground=C_WHITE, width=width,
                              show="*" if secret else "")
        self.entry.pack(fill="x", ipady=8, padx=10)
        if placeholder:
            self.entry.insert(0, placeholder)
            self.entry.config(fg=C_MUTED)
            self.entry.bind("<FocusIn>",  lambda e: self._clr(placeholder))
            self.entry.bind("<FocusOut>", lambda e: self._rst(placeholder))
        inner.bind("<Button-1>", lambda e: self.entry.focus())
        self._focus_effect(inner)

    def _focus_effect(self, frame):
        self.entry.bind("<FocusIn>",  lambda e: frame.config(highlightbackground=C_PRIMARY))
        self.entry.bind("<FocusOut>", lambda e: frame.config(highlightbackground=C_BORDER))

    def _clr(self, ph):
        if self.var.get() == ph:
            self.entry.delete(0, "end")
            self.entry.config(fg=C_TEXT)

    def _rst(self, ph):
        if not self.var.get():
            self.entry.insert(0, ph)
            self.entry.config(fg=C_MUTED)

    def get(self):
        v = self.var.get()
        return "" if v.startswith(("Enter", "e.g")) else v

    def set(self, v):
        self.var.set(str(v) if v is not None else "")
        self.entry.config(fg=C_TEXT if v else C_MUTED)


class FloatCombo(tk.Frame):
    def __init__(self, parent, label, values, width=21, required=False, **kw):
        super().__init__(parent, bg=C_CARD, **kw)
        lbl = label + (" *" if required else "")
        tk.Label(self, text=lbl, font=F_LABEL, bg=C_CARD, fg=C_MUTED).pack(anchor="w", pady=(0,3))
        self.var = tk.StringVar()
        self.combo = ttk.Combobox(self, textvariable=self.var, values=values,
                                  font=F_BODY, width=width, state="readonly")
        self.combo.pack(fill="x", ipady=5)
        if values:
            self.combo.current(0)

    def get(self):
        return self.var.get()

    def set(self, v):
        self.var.set(v)


class FloatText(tk.Frame):
    def __init__(self, parent, label, height=3, width=36, **kw):
        super().__init__(parent, bg=C_CARD, **kw)
        tk.Label(self, text=label, font=F_LABEL, bg=C_CARD, fg=C_MUTED).pack(anchor="w", pady=(0,3))
        inner = tk.Frame(self, bg=C_SURFACE2,
                         highlightbackground=C_BORDER, highlightthickness=1)
        inner.pack(fill="x")
        self.text = tk.Text(inner, height=height, width=width, font=F_BODY,
                            bg=C_SURFACE2, fg=C_TEXT, relief="flat",
                            insertbackground=C_WHITE, wrap="word", bd=0,
                            padx=10, pady=8)
        self.text.pack(fill="both")
        self.text.bind("<FocusIn>",  lambda e: inner.config(highlightbackground=C_PRIMARY))
        self.text.bind("<FocusOut>", lambda e: inner.config(highlightbackground=C_BORDER))

    def get(self):
        return self.text.get("1.0", "end-1c").strip()

    def set(self, v):
        self.text.delete("1.0", "end")
        if v:
            self.text.insert("1.0", str(v))


class Table(tk.Frame):
    def __init__(self, parent, cols, col_widths=None, **kw):
        super().__init__(parent, bg=C_BG, **kw)
        self.cols = cols
        vs = ttk.Scrollbar(self, orient="vertical")
        hs = ttk.Scrollbar(self, orient="horizontal")
        self.tree = ttk.Treeview(self, columns=cols, show="headings",
                                 style="HMS.Treeview",
                                 yscrollcommand=vs.set, xscrollcommand=hs.set)
        vs.config(command=self.tree.yview)
        hs.config(command=self.tree.xview)
        vs.pack(side="right", fill="y")
        hs.pack(side="bottom", fill="x")
        self.tree.pack(fill="both", expand=True)
        default_w = col_widths or {}
        for col in cols:
            w = default_w.get(col, max(90, len(col) * 9))
            self.tree.heading(col, text=col, anchor="w")
            self.tree.column(col,  width=w, anchor="w", minwidth=60)
        self.tree.tag_configure("alt",       background="#1c1f33")
        self.tree.tag_configure("active",    background="#1a2a1a", foreground=C_GREEN)
        self.tree.tag_configure("inactive",  background="#2a1a1a", foreground=C_RED)
        self.tree.tag_configure("scheduled", background="#1a1f2e", foreground=C_CYAN)
        self.tree.tag_configure("completed", background="#1a2a1a", foreground=C_GREEN)
        self.tree.tag_configure("cancelled", background="#2a1a1a", foreground=C_RED)
        self.tree.tag_configure("pending",   background="#2a2210", foreground=C_YELLOW)
        self.tree.tag_configure("paid",      background="#1a2a1a", foreground=C_GREEN)
        self.tree.tag_configure("partial",   background="#1a1f2e", foreground=C_CYAN)
        self.tree.tag_configure("admitted",  background="#1a2010", foreground=C_GREEN)
        self.tree.tag_configure("discharged",background="#10101a", foreground=C_MUTED)
        self.tree.tag_configure("critical",  background="#2a0a0a", foreground=C_RED)
        self.tree.tag_configure("low",       background="#2a1a00", foreground=C_YELLOW)

    def clear(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    def add(self, values, tag=""):
        tags = (tag,) if tag else ()
        self.tree.insert("", "end", values=values, tags=tags)

    def selected(self):
        sel = self.tree.selection()
        if not sel:
            return None
        return list(self.tree.item(sel[0], "values"))

    def on_select(self, cb):
        self.tree.bind("<<TreeviewSelect>>", lambda e: cb(self.selected()))

    def on_double(self, cb):
        self.tree.bind("<Double-1>", lambda e: cb(self.selected()))


class Badge(tk.Label):
    COLORS = {
        "active":    (C_GREEN,  "#0a1a0a"),
        "inactive":  (C_RED,    "#1a0a0a"),
        "scheduled": (C_CYAN,   "#0a1a1a"),
        "completed": (C_GREEN,  "#0a1a0a"),
        "cancelled": (C_RED,    "#1a0a0a"),
        "pending":   (C_YELLOW, "#1a1500"),
        "paid":      (C_GREEN,  "#0a1a0a"),
        "partial":   (C_CYAN,   "#0a1a1a"),
        "admitted":  (C_GREEN,  "#0a1a0a"),
        "discharged":(C_MUTED,  "#1a1a1a"),
    }

    def __init__(self, parent, status, **kw):
        fg, bg = self.COLORS.get(status.lower(), (C_MUTED, C_SURFACE2))
        super().__init__(parent, text=f"  {status.upper()}  ",
                         font=F_SMALL, fg=fg, bg=bg,
                         padx=6, pady=2, **kw)


class SectionHeader(tk.Frame):
    def __init__(self, parent, title, subtitle="", **kw):
        super().__init__(parent, bg=C_BG, **kw)
        tk.Frame(self, bg=C_PRIMARY, width=4).pack(side="left", fill="y", padx=(0,12))
        right = tk.Frame(self, bg=C_BG)
        right.pack(side="left", fill="both", expand=True)
        tk.Label(right, text=title, font=F_HEAD, bg=C_BG, fg=C_WHITE).pack(anchor="w")
        if subtitle:
            tk.Label(right, text=subtitle, font=F_SMALL, bg=C_BG, fg=C_MUTED).pack(anchor="w")


class Notification(tk.Frame):
    def __init__(self, parent, message, kind="info", **kw):
        colors = {
            "info":    (C_PRIMARY, "#0d1130"),
            "success": (C_GREEN,   "#0a1a0a"),
            "error":   (C_RED,     "#1a0a0a"),
            "warning": (C_YELLOW,  "#1a1500"),
        }
        fg, bg = colors.get(kind, colors["info"])
        super().__init__(parent, bg=bg,
                         highlightbackground=fg, highlightthickness=1, **kw)
        icons = {"info": "ℹ", "success": "✓", "error": "✕", "warning": "⚠"}
        icon  = icons.get(kind, "ℹ")
        tk.Label(self, text=f"  {icon}  {message}  ",
                 font=F_BODY, bg=bg, fg=fg).pack(padx=10, pady=8)


class MiniChart(tk.Canvas):
    def __init__(self, parent, data: dict, color=C_PRIMARY, title="", **kw):
        kw.setdefault("bg", C_CARD)
        kw.setdefault("highlightthickness", 0)
        super().__init__(parent, **kw)
        self._data  = data
        self._color = color
        self._title = title
        self.bind("<Configure>", lambda e: self._draw())

    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 10 or h < 10:
            return
        if self._title:
            self.create_text(10, 8, text=self._title, font=F_SMALL,
                             fill=C_MUTED, anchor="nw")
        if not self._data:
            return
        values = list(self._data.values())
        labels = list(self._data.keys())
        pad_l, pad_r, pad_t, pad_b = 10, 10, 28, 30
        max_v = max(values) if values else 1
        if max_v == 0:
            max_v = 1
        n = len(values)
        bar_area_w = w - pad_l - pad_r
        bar_w = max(4, bar_area_w // n - 4)
        step  = bar_area_w // n
        for i, (val, label) in enumerate(zip(values, labels)):
            x0 = pad_l + i * step + (step - bar_w) // 2
            bar_h = int((val / max_v) * (h - pad_t - pad_b))
            y0 = h - pad_b - bar_h
            y1 = h - pad_b
            self.create_rectangle(x0, y0, x0 + bar_w, y1,
                                  fill=self._color, outline="", width=0)
            self.create_text(x0 + bar_w // 2, h - pad_b + 6,
                             text=str(label)[:4], font=F_SMALL, fill=C_MUTED, anchor="n")
            if val > 0:
                self.create_text(x0 + bar_w // 2, y0 - 4,
                                 text=str(val), font=F_SMALL, fill=C_MUTED, anchor="s")

    def update_data(self, data):
        self._data = data
        self._draw()


class DonutChart(tk.Canvas):
    def __init__(self, parent, data: dict, title="", **kw):
        kw.setdefault("bg", C_CARD)
        kw.setdefault("highlightthickness", 0)
        super().__init__(parent, **kw)
        PALETTE = [C_PRIMARY, C_GREEN, C_RED, C_YELLOW, C_CYAN, C_ORANGE, C_PRIMARY_H]
        self._data    = data
        self._title   = title
        self._palette = PALETTE
        self.bind("<Configure>", lambda e: self._draw())

    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 20 or h < 20:
            return
        if self._title:
            self.create_text(w // 2, 14, text=self._title, font=F_LABEL,
                             fill=C_MUTED, anchor="center")
        total = sum(self._data.values())
        if total == 0:
            self.create_text(w//2, h//2, text="No data", font=F_SMALL, fill=C_MUTED)
            return
        cx, cy = w // 2, h // 2 + 8
        r_outer = min(cx, cy - 20) - 10
        r_inner = r_outer * 0.55
        start = -90
        for i, (label, val) in enumerate(self._data.items()):
            if val == 0:
                continue
            extent = (val / total) * 360
            color  = self._palette[i % len(self._palette)]
            self.create_arc(cx - r_outer, cy - r_outer,
                            cx + r_outer, cy + r_outer,
                            start=start, extent=extent,
                            fill=color, outline=C_CARD, width=2)
            start += extent
        self.create_oval(cx - r_inner, cy - r_inner,
                         cx + r_inner, cy + r_inner,
                         fill=C_CARD, outline="")
        self.create_text(cx, cy - 6, text=str(total), font=("Segoe UI", 14, "bold"),
                         fill=C_WHITE, anchor="center")
        self.create_text(cx, cy + 10, text="total", font=F_SMALL,
                         fill=C_MUTED, anchor="center")
        legend_y = h - 16
        legend_x = 10
        for i, (label, val) in enumerate(self._data.items()):
            color = self._palette[i % len(self._palette)]
            pct   = f"{(val/total*100):.0f}%" if total > 0 else "0%"
            self.create_rectangle(legend_x, legend_y - 8,
                                  legend_x + 10, legend_y + 2,
                                  fill=color, outline="")
            self.create_text(legend_x + 14, legend_y - 3,
                             text=f"{label} ({pct})", font=F_SMALL,
                             fill=C_MUTED, anchor="w")
            legend_x += max(100, len(f"{label} ({pct})") * 7 + 20)
            if legend_x > w - 100:
                legend_x = 10
                legend_y -= 18

    def update_data(self, data):
        self._data = data
        self._draw()
