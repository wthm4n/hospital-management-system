import tkinter as tk
from tkinter import messagebox
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import *
from ui.widgets import Btn, FloatEntry, FloatCombo, apply_theme
from services.services import AuthService, seed
from database.connection import db


class LoginWindow:
    def __init__(self):
        seed()
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} — Login")
        self.root.geometry("520x680")
        self.root.resizable(False, False)
        self.root.configure(bg=C_BG)
        apply_theme()
        self._center()
        self._build()
        self.root.mainloop()

    def _center(self):
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x  = (sw - 520) // 2
        y  = (sh - 680) // 2
        self.root.geometry(f"520x680+{x}+{y}")

    def _build(self):
        tk.Frame(self.root, bg=C_PRIMARY, height=4).pack(fill="x")
        outer = tk.Frame(self.root, bg=C_BG)
        outer.pack(fill="both", expand=True)
        left_bar = tk.Frame(outer, bg=C_SURFACE, width=60)
        left_bar.pack(side="left", fill="y")
        left_bar.pack_propagate(False)
        for color in [C_PRIMARY, C_GREEN, C_CYAN, C_YELLOW]:
            tk.Frame(left_bar, bg=color, height=3).pack(fill="x", pady=1)
        main = tk.Frame(outer, bg=C_BG, padx=50, pady=30)
        main.pack(fill="both", expand=True)
        logo_frame = tk.Frame(main, bg=C_BG)
        logo_frame.pack(pady=(20, 0))
        logo_box = tk.Frame(logo_frame, bg=C_PRIMARY, padx=18, pady=12)
        logo_box.pack()
        tk.Label(logo_box, text="＋", font=("Segoe UI", 30, "bold"),
                 bg=C_PRIMARY, fg=C_WHITE).pack()
        tk.Label(main, text=APP_NAME, font=F_TITLE,
                 bg=C_BG, fg=C_WHITE).pack(pady=(14, 2))
        tk.Label(main, text="Hospital Management System", font=F_LABEL,
                 bg=C_BG, fg=C_MUTED).pack()
        tk.Frame(main, bg=C_BORDER, height=1).pack(fill="x", pady=24)
        card = tk.Frame(main, bg=C_CARD,
                        highlightbackground=C_BORDER, highlightthickness=1)
        card.pack(fill="x")
        inner = tk.Frame(card, bg=C_CARD, padx=30, pady=28)
        inner.pack(fill="both")
        tk.Label(inner, text="Sign in to your account", font=F_SUB,
                 bg=C_CARD, fg=C_MUTED).pack(anchor="w", pady=(0,18))
        self.f_user = FloatEntry(inner, "Username", "Enter username", required=True)
        self.f_user.pack(fill="x", pady=6)
        self.f_pass = FloatEntry(inner, "Password", "Enter password", secret=True, required=True)
        self.f_pass.pack(fill="x", pady=6)
        self.f_role = FloatCombo(inner, "Role", [r.title() for r in [
            "Admin", "Doctor", "Receptionist", "Pharmacist", "Nurse", "Accountant", "Lab Tech"
        ]])
        self.f_role.pack(fill="x", pady=6)
        tk.Frame(inner, bg=C_CARD, height=8).pack()
        Btn(inner, "SIGN IN", self._login, "primary", w=30).pack(fill="x", ipady=4)
        info = tk.Frame(main, bg=C_BG)
        info.pack(fill="x", pady=18)
        db_txt = f"● MongoDB Connected" if db.mongo else "● SQLite (Local Mode)"
        db_clr = C_GREEN if db.mongo else C_YELLOW
        tk.Label(info, text=db_txt, font=F_SMALL, bg=C_BG, fg=db_clr).pack(side="left")
        tk.Label(info, text="Default: admin / admin123", font=F_SMALL,
                 bg=C_BG, fg=C_MUTED).pack(side="right")
        self.root.bind("<Return>", lambda e: self._login())
        self.f_user.entry.focus_set()

    def _login(self):
        u = self.f_user.get().strip()
        p = self.f_pass.get().strip()
        if not u or not p:
            self._show_error("Please enter username and password")
            return
        svc  = AuthService()
        user, msg = svc.login(u, p)
        if not user:
            self._show_error(msg)
            return
        self.root.destroy()
        from ui.main_window import MainWindow
        MainWindow(user)

    def _show_error(self, msg):
        for w in self.root.winfo_children():
            if isinstance(w, tk.Frame) and hasattr(w, '_is_error'):
                w.destroy()
        err = tk.Frame(self.root, bg="#2a0a0a",
                       highlightbackground=C_RED, highlightthickness=1)
        err._is_error = True
        err.pack(fill="x", padx=30, pady=(0, 8))
        tk.Label(err, text=f"  ✕  {msg}  ", font=F_SMALL,
                 bg="#2a0a0a", fg=C_RED).pack(padx=10, pady=8)
        self.root.after(3000, err.destroy)
