import tkinter as tk
from tkinter import ttk
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import *
from ui.widgets import StatCard, Table, MiniChart, DonutChart, SectionHeader
from services.services import ReportService
from database.connection import db
from utils.helpers import today, fmt_currency


class DashboardModule(tk.Frame):
    def __init__(self, parent, user):
        super().__init__(parent, bg=C_BG)
        self.pack(fill="both", expand=True)
        self.user = user
        self._build()

    def _build(self):
        svc = ReportService()
        s   = svc.summary()
        fin = svc.financial()

        canvas = tk.Canvas(self, bg=C_BG, highlightthickness=0)
        vs     = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vs.set)
        vs.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(canvas, bg=C_BG)
        win   = canvas.create_window((0,0), window=inner, anchor="nw")
        def _resize(e):
            canvas.itemconfig(win, width=canvas.winfo_width())
        def _scroll(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.bind("<Configure>", _resize)
        inner.bind("<Configure>", _scroll)
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(-1*(e.delta//120), "units"))

        greet_row = tk.Frame(inner, bg=C_BG)
        greet_row.pack(fill="x", pady=(0, 18))
        name = self.user.get("full_name", "User")
        tk.Label(greet_row, text=f"Welcome back, {name} 👋",
                 font=F_HEAD, bg=C_BG, fg=C_WHITE).pack(side="left")
        tk.Label(greet_row, text="Live Hospital Overview",
                 font=F_SMALL, bg=C_BG, fg=C_MUTED).pack(side="right")

        stat_cards = [
            ("Total Patients",      s["patients_active"],      C_PRIMARY,  "◉", f"{s['patients_total']} registered"),
            ("Today's Appointments",s["appointments_today"],   C_CYAN,     "◷", "Scheduled today"),
            ("Currently Admitted",  s["admitted_now"],         C_GREEN,    "⊞", "Active admissions"),
            ("Active Doctors",      s["doctors_active"],       C_YELLOW,   "◎", "On staff"),
            ("Pending Bills",       s["pending_bills"],        C_RED,      "⊙", fmt_currency(fin["outstanding"]) + " outstanding"),
            ("Lab Pending",         s["lab_pending"],          C_ORANGE,   "⊕", "Awaiting results"),
        ]
        grid = tk.Frame(inner, bg=C_BG)
        grid.pack(fill="x", pady=(0, 20))
        for i, (title, val, color, icon, sub) in enumerate(stat_cards):
            card = StatCard(grid, title, val, sub, color, icon)
            card.grid(row=0, column=i, padx=6, sticky="nsew")
            grid.grid_columnconfigure(i, weight=1)

        fin_cards = [
            ("Total Revenue",  fmt_currency(fin["total_revenue"]),  C_GREEN,  "◆"),
            ("Collected",      fmt_currency(fin["collected"]),      C_PRIMARY,"◆"),
            ("Outstanding",    fmt_currency(fin["outstanding"]),    C_RED,    "◆"),
        ]
        fin_row = tk.Frame(inner, bg=C_BG)
        fin_row.pack(fill="x", pady=(0, 22))
        for i, (title, val, color, icon) in enumerate(fin_cards):
            card = StatCard(fin_row, title, val, "", color, icon)
            card.grid(row=0, column=i, padx=6, sticky="nsew")
            fin_row.grid_columnconfigure(i, weight=1)

        mid = tk.Frame(inner, bg=C_BG)
        mid.pack(fill="both", expand=True, pady=(0, 20))
        mid.grid_columnconfigure(0, weight=3)
        mid.grid_columnconfigure(1, weight=2)

        appt_card = tk.Frame(mid, bg=C_CARD,
                             highlightbackground=C_BORDER, highlightthickness=1)
        appt_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        appt_inner = tk.Frame(appt_card, bg=C_CARD, padx=14, pady=14)
        appt_inner.pack(fill="both", expand=True)
        tk.Label(appt_inner, text="Recent Appointments", font=F_SUB,
                 bg=C_CARD, fg=C_WHITE).pack(anchor="w", pady=(0, 10))
        tbl = Table(appt_inner, ["Patient", "Doctor", "Date", "Time", "Status"],
                    {"Patient":150,"Doctor":150,"Date":100,"Time":80,"Status":90})
        tbl.pack(fill="both", expand=True)
        appts = db.find("appointments", sort="created_at", limit=10)
        for a in appts:
            tbl.add([a.get("patient_name",""), a.get("doctor_name",""),
                     a.get("date",""), a.get("time",""), a.get("status","")],
                    tag=a.get("status","scheduled"))

        right_col = tk.Frame(mid, bg=C_BG)
        right_col.grid(row=0, column=1, sticky="nsew")

        low_card = tk.Frame(right_col, bg=C_CARD,
                            highlightbackground=C_BORDER, highlightthickness=1)
        low_card.pack(fill="x", pady=(0, 8))
        low_inner = tk.Frame(low_card, bg=C_CARD, padx=14, pady=14)
        low_inner.pack(fill="both", expand=True)
        tk.Label(low_inner, text="⚠  Low Inventory", font=F_SUB,
                 bg=C_CARD, fg=C_YELLOW).pack(anchor="w", pady=(0, 8))
        alerts = ReportService().inventory_alerts()[:6]
        if alerts:
            for item in alerts:
                qty    = int(item.get("quantity",0))
                rl     = int(item.get("reorder_level",10))
                color  = C_RED if qty == 0 else C_YELLOW
                status = "OUT" if qty == 0 else f"{qty} left"
                row = tk.Frame(low_inner, bg=C_SURFACE2)
                row.pack(fill="x", pady=2)
                tk.Label(row, text=f"  {item.get('name','')[:22]}", font=F_SMALL,
                         bg=C_SURFACE2, fg=C_TEXT).pack(side="left", ipady=5)
                tk.Label(row, text=f"{status}  ", font=F_SMALL,
                         bg=C_SURFACE2, fg=color).pack(side="right", ipady=5)
        else:
            tk.Label(low_inner, text="✓  All stock levels OK",
                     font=F_SMALL, bg=C_CARD, fg=C_GREEN).pack(anchor="w")

        blood_data = {}
        for bg_val in ["A+","A-","B+","B-","AB+","AB-","O+","O-"]:
            cnt = db.count("patients", {"blood": bg_val})
            if cnt > 0:
                blood_data[bg_val] = cnt

        chart_card = tk.Frame(right_col, bg=C_CARD,
                              highlightbackground=C_BORDER, highlightthickness=1)
        chart_card.pack(fill="both", expand=True)
        chart_inner = tk.Frame(chart_card, bg=C_CARD, padx=14, pady=14)
        chart_inner.pack(fill="both", expand=True)
        tk.Label(chart_inner, text="Blood Group Distribution", font=F_SUB,
                 bg=C_CARD, fg=C_WHITE).pack(anchor="w", pady=(0, 6))
        DonutChart(chart_inner, blood_data if blood_data else {"No data": 1},
                   height=200, width=300).pack(fill="both", expand=True)

        appt_status = {
            "Scheduled": db.count("appointments", {"status": "scheduled"}),
            "Completed": db.count("appointments", {"status": "completed"}),
            "Cancelled": db.count("appointments", {"status": "cancelled"}),
        }
        bottom_row = tk.Frame(inner, bg=C_BG)
        bottom_row.pack(fill="x", pady=(0, 20))
        bottom_row.grid_columnconfigure(0, weight=1)
        bottom_row.grid_columnconfigure(1, weight=1)

        appt_chart_card = tk.Frame(bottom_row, bg=C_CARD,
                                   highlightbackground=C_BORDER, highlightthickness=1)
        appt_chart_card.grid(row=0, column=0, padx=(0,8), sticky="nsew")
        appt_chart_inner = tk.Frame(appt_chart_card, bg=C_CARD, padx=14, pady=14)
        appt_chart_inner.pack(fill="both", expand=True)
        tk.Label(appt_chart_inner, text="Appointment Status", font=F_SUB,
                 bg=C_CARD, fg=C_WHITE).pack(anchor="w", pady=(0,6))
        MiniChart(appt_chart_inner, appt_status, C_PRIMARY,
                  height=160).pack(fill="both", expand=True)

        ward_data = {}
        for w in db.find("wards"):
            ward_data[w.get("name","")[:10]] = int(w.get("occupied",0))
        ward_chart_card = tk.Frame(bottom_row, bg=C_CARD,
                                   highlightbackground=C_BORDER, highlightthickness=1)
        ward_chart_card.grid(row=0, column=1, padx=(8,0), sticky="nsew")
        ward_inner = tk.Frame(ward_chart_card, bg=C_CARD, padx=14, pady=14)
        ward_inner.pack(fill="both", expand=True)
        tk.Label(ward_inner, text="Ward Occupancy", font=F_SUB,
                 bg=C_CARD, fg=C_WHITE).pack(anchor="w", pady=(0,6))
        MiniChart(ward_inner, ward_data if ward_data else {"No data": 0}, C_GREEN,
                  height=160).pack(fill="both", expand=True)
