import tkinter as tk
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import *
from ui.widgets import Btn, Table, SearchEntry, SectionHeader, Badge
from ui.dialogs import Modal, FormBuilder, confirm, show_detail
from services.services import PatientService
from utils.helpers import age_from_dob, fmt_date


class PatientModule(tk.Frame):
    def __init__(self, parent, user):
        super().__init__(parent, bg=C_BG)
        self.pack(fill="both", expand=True)
        self.user = user
        self._svc = PatientService()
        self._build()
        self._load()

    def _build(self):
        top = tk.Frame(self, bg=C_BG)
        top.pack(fill="x", pady=(0, 14))
        SectionHeader(top, "Patient Management",
                      "Register, search and manage patient records").pack(side="left", fill="y")
        actions = tk.Frame(top, bg=C_BG)
        actions.pack(side="right")
        self._search = SearchEntry(actions, "Search by name, ID or phone...",
                                   on_change=self._load, width=30)
        self._search.pack(side="left", padx=(0,10))
        Btn(actions, "New Patient", self._add, "primary", icon="＋").pack(side="left", padx=4)
        Btn(actions, "View",  self._view,   "ghost",    icon="◎").pack(side="left", padx=2)
        Btn(actions, "Edit",  self._edit,   "outline",  icon="✎").pack(side="left", padx=2)
        Btn(actions, "History", self._history, "cyan", icon="◷").pack(side="left", padx=2)
        Btn(actions, "Refresh", self._load, "ghost", icon="↺").pack(side="left", padx=2)

        self._tbl = Table(self,
            ["Pt. ID", "Full Name", "Age", "Gender", "Blood", "Phone", "Email", "Status"],
            {"Pt. ID":90,"Full Name":180,"Age":55,"Gender":75,"Blood":65,
             "Phone":130,"Email":180,"Status":90})
        self._tbl.pack(fill="both", expand=True)
        self._tbl.on_double(lambda v: self._view(v))

    def _load(self):
        self._tbl.clear()
        q = self._search.get()
        for p in self._svc.get_all(q):
            age = age_from_dob(p.get("dob",""))
            self._tbl.add([
                p.get("pid",""), p.get("full_name",""),
                age, p.get("gender",""), p.get("blood",""),
                p.get("phone",""), p.get("email",""),
                p.get("status","active")
            ], tag=p.get("status","active"))

    def _fields(self, existing=None):
        e = existing or {}
        return [
            {"name":"full_name",  "label":"Full Name",         "required":True, "default":e.get("full_name",""),   "placeholder":"e.g. John Smith"},
            {"name":"dob",        "label":"Date of Birth",     "default":e.get("dob",""),                          "placeholder":"YYYY-MM-DD"},
            {"name":"gender",     "label":"Gender",            "type":"combo", "values":["Male","Female","Other"],  "default":e.get("gender","Male")},
            {"name":"blood",      "label":"Blood Group",       "type":"combo",
             "values":["A+","A-","B+","B-","AB+","AB-","O+","O-","Unknown"],   "default":e.get("blood","Unknown")},
            {"name":"phone",      "label":"Phone",             "required":True, "default":e.get("phone",""),        "placeholder":"+1-555-0000"},
            {"name":"email",      "label":"Email",             "default":e.get("email",""),                         "placeholder":"patient@email.com"},
            {"name":"address",    "label":"Address",           "default":e.get("address",""),                       "placeholder":"Street, City, State"},
            {"name":"emergency_name", "label":"Emergency Contact", "default":e.get("emergency_name",""),            "placeholder":"Name"},
            {"name":"emergency_phone","label":"Emergency Phone",   "default":e.get("emergency_phone",""),           "placeholder":"+1-555-0000"},
            {"name":"allergies",  "label":"Known Allergies",   "default":e.get("allergies",""),                     "placeholder":"e.g. Penicillin, Pollen"},
            {"name":"chronic",    "label":"Chronic Conditions","default":e.get("chronic",""),                       "placeholder":"e.g. Diabetes, Hypertension"},
            {"name":"notes",      "label":"Additional Notes",  "type":"text",   "default":e.get("notes","")},
        ]

    def _add(self, _=None):
        dlg = Modal(self, "Register New Patient", width=740)
        inner = dlg.make_scrollable()
        fb    = FormBuilder(inner, self._fields(), cols=2)
        def save():
            data   = fb.get_all()
            errors = fb.validate_required()
            if errors:
                from tkinter import messagebox
                messagebox.showerror("Required Fields", "Please fill: " + ", ".join(errors), parent=dlg)
                return
            ok, result = self._svc.add(data, self.user["username"])
            if ok:
                dlg.destroy()
                self._load()
                self._toast(f"Patient registered — ID: {result}")
            else:
                from tkinter import messagebox
                messagebox.showerror("Error", result, parent=dlg)
        dlg.footer(save)
        dlg.wait_window()

    def _edit(self, _=None):
        vals = self._tbl.selected()
        if not vals:
            self._toast("Select a patient first", "warn")
            return
        patient = self._svc.get(vals[0])
        if not patient:
            return
        dlg = Modal(self, f"Edit Patient — {patient['full_name']}", width=740)
        inner = dlg.make_scrollable()
        fb    = FormBuilder(inner, self._fields(patient), cols=2)
        def save():
            data = fb.get_all()
            self._svc.update(vals[0], data, self.user["username"])
            dlg.destroy()
            self._load()
            self._toast("Patient updated")
        dlg.footer(save)
        dlg.wait_window()

    def _view(self, vals=None):
        if vals is None:
            vals = self._tbl.selected()
        if not vals:
            self._toast("Select a patient first", "warn")
            return
        p = self._svc.get(vals[0])
        if not p:
            return
        show_detail(self, f"Patient — {p.get('full_name','')}", [
            ("Patient ID",        p.get("pid","")),
            ("Full Name",         p.get("full_name","")),
            ("Date of Birth",     fmt_date(p.get("dob",""))),
            ("Age",               age_from_dob(p.get("dob","")) + " years"),
            ("Gender",            p.get("gender","")),
            ("Blood Group",       p.get("blood","")),
            ("Phone",             p.get("phone","")),
            ("Email",             p.get("email","")),
            ("Address",           p.get("address","")),
            ("Emergency Contact", p.get("emergency_name","")),
            ("Emergency Phone",   p.get("emergency_phone","")),
            ("Allergies",         p.get("allergies","")),
            ("Chronic Conditions",p.get("chronic","")),
            ("Notes",             p.get("notes","")),
            ("Status",            p.get("status","").title()),
            ("Registered",        p.get("created_at","")[:10]),
        ])

    def _history(self, _=None):
        vals = self._tbl.selected()
        if not vals:
            self._toast("Select a patient first", "warn")
            return
        from database.connection import db
        pid  = vals[0]
        name = vals[1]
        dlg  = Modal(self, f"History — {name}", width=800, height=550)
        tabs = tk.Frame(dlg.body, bg=C_SURFACE)
        tabs.pack(fill="both", expand=True)
        from tkinter import ttk
        nb = ttk.Notebook(tabs)
        nb.pack(fill="both", expand=True)
        appt_frame = tk.Frame(nb, bg=C_BG)
        nb.add(appt_frame, text="  Appointments  ")
        appt_tbl = Table(appt_frame, ["Date","Doctor","Reason","Status"],
                         {"Date":100,"Doctor":160,"Reason":200,"Status":90})
        appt_tbl.pack(fill="both", expand=True, padx=8, pady=8)
        for a in db.find("appointments", {"pid": pid}):
            appt_tbl.add([a.get("date",""), a.get("doctor_name",""),
                          a.get("reason",""), a.get("status","")], tag=a.get("status","scheduled"))
        adm_frame = tk.Frame(nb, bg=C_BG)
        nb.add(adm_frame, text="  Admissions  ")
        adm_tbl = Table(adm_frame, ["Admitted","Discharged","Ward","Doctor","Diagnosis","Status"],
                        {"Admitted":100,"Discharged":100,"Ward":130,"Doctor":160,"Diagnosis":160,"Status":90})
        adm_tbl.pack(fill="both", expand=True, padx=8, pady=8)
        for a in db.find("admissions", {"pid": pid}):
            adm_tbl.add([a.get("admitted_on",""), a.get("discharged_on",""),
                         a.get("ward_name",""), a.get("doctor_name",""),
                         a.get("diagnosis",""), a.get("status","")], tag=a.get("status","admitted"))
        bill_frame = tk.Frame(nb, bg=C_BG)
        nb.add(bill_frame, text="  Bills  ")
        bill_tbl = Table(bill_frame, ["Bill ID","Total","Paid","Status","Date"],
                         {"Bill ID":100,"Total":100,"Paid":100,"Status":80,"Date":110})
        bill_tbl.pack(fill="both", expand=True, padx=8, pady=8)
        for b in db.find("billing", {"pid": pid}):
            bill_tbl.add([b.get("bid",""), f"${b.get('total',0):.2f}",
                          f"${b.get('paid',0):.2f}", b.get("status",""),
                          b.get("created_at","")[:10]], tag=b.get("status","pending"))
        Btn(dlg.body, "Close", dlg.destroy, "ghost").pack(pady=10)

    def _toast(self, msg, kind="success"):
        colors = {"success": C_GREEN, "warn": C_YELLOW, "error": C_RED}
        color  = colors.get(kind, C_GREEN)
        toast  = tk.Frame(self, bg=C_SURFACE2,
                          highlightbackground=color, highlightthickness=1)
        toast.place(relx=1.0, rely=1.0, anchor="se", x=-20, y=-20)
        tk.Label(toast, text=f"  {msg}  ", font=F_SMALL,
                 bg=C_SURFACE2, fg=color).pack(padx=12, pady=8)
        self.after(2500, toast.destroy)
