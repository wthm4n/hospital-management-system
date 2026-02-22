import tkinter as tk
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import *
from ui.widgets import Btn, Table, SearchEntry, SectionHeader
from ui.dialogs import Modal, FormBuilder, confirm, show_detail
from services.services import DoctorService
from utils.helpers import fmt_currency


class DoctorModule(tk.Frame):
    def __init__(self, parent, user):
        super().__init__(parent, bg=C_BG)
        self.pack(fill="both", expand=True)
        self.user = user
        self._svc  = DoctorService()
        self._build()
        self._load()

    def _build(self):
        top = tk.Frame(self, bg=C_BG)
        top.pack(fill="x", pady=(0, 14))
        SectionHeader(top, "Doctor Management", "Staff directory and schedule management").pack(side="left")
        acts = tk.Frame(top, bg=C_BG)
        acts.pack(side="right")
        self._search = SearchEntry(acts, "Search doctors...", on_change=self._load)
        self._search.pack(side="left", padx=(0, 10))
        Btn(acts, "Add Doctor", self._add,     "primary",  icon="＋").pack(side="left", padx=3)
        Btn(acts, "Edit",       self._edit,    "outline",  icon="✎").pack(side="left", padx=2)
        Btn(acts, "View",       self._view,    "ghost",    icon="◎").pack(side="left", padx=2)
        Btn(acts, "Refresh",    self._load,    "ghost",    icon="↺").pack(side="left", padx=2)

        self._tbl = Table(self,
            ["Doc ID", "Full Name", "Specialization", "Qualification", "Phone", "Fee", "Schedule", "Status"],
            {"Doc ID":80,"Full Name":170,"Specialization":140,"Qualification":120,"Phone":130,"Fee":80,"Schedule":150,"Status":90})
        self._tbl.pack(fill="both", expand=True)
        self._tbl.on_double(lambda v: self._view(v))

    def _load(self):
        self._tbl.clear()
        q = self._search.get().lower()
        for d in self._svc.get_all():
            if q and q not in d.get("full_name","").lower() and q not in d.get("specialization","").lower():
                continue
            self._tbl.add([
                d.get("did",""), d.get("full_name",""), d.get("specialization",""),
                d.get("qualification",""), d.get("phone",""),
                fmt_currency(d.get("fee",0)), d.get("schedule",""),
                d.get("status","active")
            ], tag=d.get("status","active"))

    def _fields(self, e=None):
        e = e or {}
        return [
            {"name":"full_name",     "label":"Full Name",          "required":True, "default":e.get("full_name",""),  "placeholder":"Dr. First Last"},
            {"name":"specialization","label":"Specialization",      "required":True, "default":e.get("specialization",""), "placeholder":"e.g. Cardiology"},
            {"name":"qualification", "label":"Qualification",       "default":e.get("qualification",""), "placeholder":"e.g. MD FACC"},
            {"name":"phone",         "label":"Phone",               "default":e.get("phone",""),  "placeholder":"+1-555-0000"},
            {"name":"email",         "label":"Email",               "default":e.get("email",""),  "placeholder":"doctor@hospital.com"},
            {"name":"fee",           "label":"Consultation Fee ($)", "default":str(e.get("fee","0")), "placeholder":"e.g. 200"},
            {"name":"schedule",      "label":"Schedule",            "default":e.get("schedule",""), "placeholder":"Mon-Fri 9AM-5PM"},
            {"name":"status",        "label":"Status",              "type":"combo",
             "values":["active","on_leave","inactive"],             "default":e.get("status","active")},
        ]

    def _add(self, _=None):
        dlg = Modal(self, "Add Doctor", width=720)
        fb  = FormBuilder(dlg.body, self._fields())
        def save():
            data = fb.get_all()
            errs = fb.validate_required()
            if errs:
                from tkinter import messagebox
                messagebox.showerror("Required", ", ".join(errs), parent=dlg)
                return
            try: data["fee"] = float(data.get("fee","0") or 0)
            except: data["fee"] = 0.0
            ok, _ = self._svc.add(data)
            if ok:
                dlg.destroy()
                self._load()
        dlg.footer(save)
        dlg.wait_window()

    def _edit(self, _=None):
        vals = self._tbl.selected()
        if not vals:
            return
        doc  = self._svc.get(vals[0])
        if not doc:
            return
        dlg = Modal(self, f"Edit — {doc['full_name']}", width=720)
        fb  = FormBuilder(dlg.body, self._fields(doc))
        def save():
            data = fb.get_all()
            try: data["fee"] = float(data.get("fee","0") or 0)
            except: data["fee"] = 0.0
            self._svc.update(vals[0], data)
            dlg.destroy()
            self._load()
        dlg.footer(save)
        dlg.wait_window()

    def _view(self, vals=None):
        if vals is None:
            vals = self._tbl.selected()
        if not vals:
            return
        d = self._svc.get(vals[0])
        if not d:
            return
        show_detail(self, f"Doctor — {d.get('full_name','')}", [
            ("Doctor ID",      d.get("did","")),
            ("Full Name",      d.get("full_name","")),
            ("Specialization", d.get("specialization","")),
            ("Qualification",  d.get("qualification","")),
            ("Phone",          d.get("phone","")),
            ("Email",          d.get("email","")),
            ("Consultation Fee", fmt_currency(d.get("fee",0))),
            ("Schedule",       d.get("schedule","")),
            ("Status",         d.get("status","").title()),
            ("Added",          d.get("created_at","")[:10]),
        ])
