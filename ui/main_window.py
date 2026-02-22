import tkinter as tk
from tkinter import messagebox
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import *
from ui.widgets import Btn, apply_theme
from database.connection import db


class MainWindow:
    def __init__(self, user: dict):
        self.user    = user
        self.role    = user.get("role", "receptionist")
        self.root    = tk.Tk()
        self.root.title(f"{APP_NAME} — {user.get('full_name', 'User')}")
        self.root.configure(bg=C_BG)
        self.root.state("zoomed")
        apply_theme()
        self._active_nav = None
        self._content    = None
        self._build()
        self._navigate("Dashboard")
        self.root.mainloop()

    def _build(self):
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self._build_main()

    def _build_sidebar(self):
        sb = tk.Frame(self.root, bg=C_SURFACE, width=SIDEBAR_W)
        sb.grid(row=0, column=0, sticky="nsew")
        sb.grid_propagate(False)
        logo = tk.Frame(sb, bg=C_SURFACE, pady=22)
        logo.pack(fill="x")
        box = tk.Frame(logo, bg=C_PRIMARY, padx=10, pady=8)
        box.pack()
        tk.Label(box, text="＋ MediCore", font=("Segoe UI", 13, "bold"),
                 bg=C_PRIMARY, fg=C_WHITE).pack()
        tk.Label(sb, text=f"v{VERSION}", font=F_SMALL,
                 bg=C_SURFACE, fg=C_MUTED).pack()
        tk.Frame(sb, bg=C_BORDER, height=1).pack(fill="x", padx=14, pady=8)
        user_card = tk.Frame(sb, bg=C_SURFACE2, padx=12, pady=10)
        user_card.pack(fill="x", padx=12, pady=(0, 10))
        initials = "".join(w[0].upper() for w in self.user.get("full_name","U U").split()[:2])
        circle   = tk.Frame(user_card, bg=C_PRIMARY, width=38, height=38)
        circle.pack(side="left")
        circle.pack_propagate(False)
        tk.Label(circle, text=initials, font=F_SUB, bg=C_PRIMARY, fg=C_WHITE).pack(expand=True)
        info = tk.Frame(user_card, bg=C_SURFACE2, padx=8)
        info.pack(side="left", fill="both", expand=True)
        name = self.user.get("full_name", "User")
        tk.Label(info, text=name[:18], font=F_LABEL, bg=C_SURFACE2, fg=C_WHITE).pack(anchor="w")
        tk.Label(info, text=self.role.replace("_"," ").title(), font=F_SMALL,
                 bg=C_SURFACE2, fg=C_MUTED).pack(anchor="w")
        tk.Frame(sb, bg=C_BORDER, height=1).pack(fill="x", padx=14, pady=(4, 10))
        nav_items = [
            ("Dashboard",    "⬡",  "all"),
            ("Patients",     "⬟",  "all"),
            ("Doctors",      "⬟",  "all"),
            ("Appointments", "⬡",  "all"),
            ("Admissions",   "⬟",  "all"),
            ("Lab Tests",    "⬟",  "all"),
            ("Inventory",    "⬡",  "all"),
            ("Billing",      "⬟",  "all"),
            ("Wards",        "⬟",  "all"),
            ("Users",        "⬟",  "admin"),
            ("Audit Log",    "⬟",  "admin"),
            ("Reports",      "⬡",  "all"),
        ]
        self._nav_btns = {}
        tk.Label(sb, text="NAVIGATION", font=("Segoe UI", 8, "bold"),
                 bg=C_SURFACE, fg=C_MUTED).pack(anchor="w", padx=18, pady=(0,4))
        NAV_ICONS = {
            "Dashboard":    "◈",
            "Patients":     "◉",
            "Doctors":      "◎",
            "Appointments": "◷",
            "Admissions":   "⊞",
            "Lab Tests":    "⊕",
            "Inventory":    "⊟",
            "Billing":      "⊙",
            "Wards":        "⊠",
            "Users":        "⊛",
            "Audit Log":    "◈",
            "Reports":      "◈",
        }
        for label, _, access in nav_items:
            if access != "all" and self.role != access:
                continue
            icon  = NAV_ICONS.get(label, "◆")
            btn   = tk.Button(sb, text=f"  {icon}  {label}",
                              font=F_BODY, bg=C_SURFACE, fg=C_MUTED,
                              relief="flat", anchor="w", padx=14, pady=9,
                              cursor="hand2", bd=0,
                              activebackground=C_SURFACE2, activeforeground=C_WHITE,
                              command=lambda l=label: self._navigate(l))
            btn.pack(fill="x")
            self._nav_btns[label] = btn
        bottom = tk.Frame(sb, bg=C_SURFACE)
        bottom.pack(side="bottom", fill="x", pady=10, padx=12)
        Btn(bottom, "Logout", self._logout, "ghost").pack(fill="x")

    def _build_main(self):
        right = tk.Frame(self.root, bg=C_BG)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)
        self._topbar = tk.Frame(right, bg=C_SURFACE, pady=0)
        self._topbar.grid(row=0, column=0, sticky="ew")
        self._topbar_left  = tk.Frame(self._topbar, bg=C_SURFACE, padx=24, pady=14)
        self._topbar_left.pack(side="left", fill="y")
        self._topbar_right = tk.Frame(self._topbar, bg=C_SURFACE, padx=20, pady=14)
        self._topbar_right.pack(side="right", fill="y")
        self._page_title = tk.Label(self._topbar_left, text="Dashboard",
                                    font=F_HEAD, bg=C_SURFACE, fg=C_WHITE)
        self._page_title.pack(side="left")
        from utils.helpers import today
        tk.Label(self._topbar_right, text=f"📅  {today()}",
                 font=F_LABEL, bg=C_SURFACE, fg=C_MUTED).pack(side="right")
        self._content_outer = tk.Frame(right, bg=C_BG)
        self._content_outer.grid(row=1, column=0, sticky="nsew")
        self._content_outer.grid_rowconfigure(0, weight=1)
        self._content_outer.grid_columnconfigure(0, weight=1)
        self._content = tk.Frame(self._content_outer, bg=C_BG)
        self._content.grid(row=0, column=0, sticky="nsew", padx=24, pady=18)
        self._content.grid_rowconfigure(0, weight=1)
        self._content.grid_columnconfigure(0, weight=1)

    def _navigate(self, label: str):
        for l, btn in self._nav_btns.items():
            if l == label:
                btn.config(bg=C_PRIMARY, fg=C_WHITE)
            else:
                btn.config(bg=C_SURFACE, fg=C_MUTED)
        self._page_title.config(text=label)
        for w in self._content.winfo_children():
            w.destroy()
        self._active_nav = label
        self._load_module(label)

    def _load_module(self, name: str):
        from ui.modules.dashboard    import DashboardModule
        from ui.modules.patients     import PatientModule
        from ui.modules.doctors      import DoctorModule
        from ui.modules.appointments import AppointmentModule
        from ui.modules.admissions   import AdmissionModule
        from ui.modules.inventory    import InventoryModule
        from ui.modules.billing      import BillingModule
        from ui.modules.wards        import WardModule
        from ui.modules.users        import UserModule
        from ui.modules.lab          import LabModule
        from ui.modules.reports      import ReportsModule
        from ui.modules.audit        import AuditModule
        modules = {
            "Dashboard":    DashboardModule,
            "Patients":     PatientModule,
            "Doctors":      DoctorModule,
            "Appointments": AppointmentModule,
            "Admissions":   AdmissionModule,
            "Lab Tests":    LabModule,
            "Inventory":    InventoryModule,
            "Billing":      BillingModule,
            "Wards":        WardModule,
            "Users":        UserModule,
            "Audit Log":    AuditModule,
            "Reports":      ReportsModule,
        }
        cls = modules.get(name)
        if cls:
            cls(self._content, self.user)

    def _logout(self):
        from ui.dialogs import confirm
        if confirm(self.root, "Are you sure you want to logout?", "Logout"):
            db.close()
            self.root.destroy()
            from ui.login_window import LoginWindow
            LoginWindow()
