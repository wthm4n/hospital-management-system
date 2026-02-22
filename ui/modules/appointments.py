import tkinter as tk
from tkinter import ttk, messagebox
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import *
from ui.widgets import Btn, Table, SearchEntry, SectionHeader
from ui.dialogs import Modal, FormBuilder, confirm
from services.services import AppointmentService, PatientService, DoctorService
from utils.helpers import today


class AppointmentModule(tk.Frame):
    def __init__(self, parent, user):
        super().__init__(parent, bg=C_BG)
        self.pack(fill="both", expand=True)
        self.user = user
        self._svc  = AppointmentService()
        self._build()
        self._load()

    def _build(self):
        top = tk.Frame(self, bg=C_BG)
        top.pack(fill="x", pady=(0, 14))
        SectionHeader(top, "Appointment Management", "Book and manage patient appointments").pack(side="left")
        acts = tk.Frame(top, bg=C_BG)
        acts.pack(side="right")
        self._filter_var = tk.StringVar(value="all")
        for label, val in [("All","all"),("Scheduled","scheduled"),("Completed","completed"),("Cancelled","cancelled")]:
            tk.Radiobutton(acts, text=label, variable=self._filter_var, value=val,
                           font=F_SMALL, bg=C_BG, fg=C_MUTED,
                           selectcolor=C_SURFACE2, activebackground=C_BG,
                           command=self._load).pack(side="left", padx=6)
        tk.Frame(acts, bg=C_BORDER, width=1, height=28).pack(side="left", padx=8)
        Btn(acts, "Book Appointment", self._book,     "primary",  icon="＋").pack(side="left", padx=3)
        Btn(acts, "Complete",         self._complete, "success",  icon="✓").pack(side="left", padx=2)
        Btn(acts, "Cancel",           self._cancel,   "danger",   icon="✕").pack(side="left", padx=2)
        Btn(acts, "Add Notes",        self._notes,    "outline",  icon="✎").pack(side="left", padx=2)
        Btn(acts, "Today",            self._today,    "cyan",     icon="◷").pack(side="left", padx=2)

        self._tbl = Table(self,
            ["Appt ID","Patient","Doctor","Date","Time","Reason","Status"],
            {"Appt ID":90,"Patient":150,"Doctor":150,"Date":100,"Time":70,"Reason":200,"Status":90})
        self._tbl.pack(fill="both", expand=True)

    def _load(self):
        self._tbl.clear()
        status = self._filter_var.get()
        for a in self._svc.get_all(status):
            self._tbl.add([
                a.get("aid",""), a.get("patient_name",""), a.get("doctor_name",""),
                a.get("date",""), a.get("time",""), a.get("reason",""), a.get("status","")
            ], tag=a.get("status","scheduled"))

    def _today(self):
        self._filter_var.set("all")
        self._tbl.clear()
        for a in self._svc.get_all("all", today()):
            self._tbl.add([
                a.get("aid",""), a.get("patient_name",""), a.get("doctor_name",""),
                a.get("date",""), a.get("time",""), a.get("reason",""), a.get("status","")
            ], tag=a.get("status","scheduled"))

    def _book(self, _=None):
        patients = PatientService().get_all()
        doctors  = DoctorService().get_all(active_only=True)
        if not patients:
            messagebox.showwarning("No Patients", "Register patients first")
            return
        if not doctors:
            messagebox.showwarning("No Doctors", "Add doctors first")
            return
        pat_opts = [f"{p['pid']} — {p['full_name']}" for p in patients]
        doc_opts = [f"{d['did']} — {d['full_name']} ({d.get('specialization','')})" for d in doctors]
        fields = [
            {"name":"patient",  "label":"Patient",   "type":"combo", "values":pat_opts, "required":True},
            {"name":"doctor",   "label":"Doctor",    "type":"combo", "values":doc_opts, "required":True},
            {"name":"date",     "label":"Date",      "required":True, "default":today(), "placeholder":"YYYY-MM-DD"},
            {"name":"time",     "label":"Time",      "default":"09:00", "placeholder":"HH:MM"},
            {"name":"reason",   "label":"Reason",    "placeholder":"Consultation reason"},
            {"name":"symptoms", "label":"Symptoms",  "type":"text", "height":2},
        ]
        dlg = Modal(self, "Book Appointment", width=700)
        fb  = FormBuilder(dlg.body, fields, cols=2)
        def save():
            data = fb.get_all()
            errs = fb.validate_required()
            if errs:
                messagebox.showerror("Required", ", ".join(errs), parent=dlg)
                return
            pat_id = data["patient"].split(" — ")[0]
            doc_id = data["doctor"].split(" — ")[0]
            p = next((x for x in patients if x["pid"] == pat_id), None)
            d = next((x for x in doctors  if x["did"] == doc_id), None)
            record = {
                "pid": pat_id, "patient_name": p["full_name"] if p else "",
                "did": doc_id, "doctor_name":  d["full_name"] if d else "",
                "date": data["date"], "time": data["time"],
                "reason": data["reason"], "symptoms": data["symptoms"],
            }
            ok, aid = self._svc.book(record, self.user["username"])
            if ok:
                dlg.destroy()
                self._load()
        dlg.footer(save)
        dlg.wait_window()

    def _complete(self, _=None):
        vals = self._tbl.selected()
        if not vals:
            return
        self._svc.update_status(vals[0], "completed")
        self._load()

    def _cancel(self, _=None):
        vals = self._tbl.selected()
        if not vals:
            return
        if confirm(self, f"Cancel appointment {vals[0]}?", "Cancel Appointment"):
            self._svc.update_status(vals[0], "cancelled")
            self._load()

    def _notes(self, _=None):
        vals = self._tbl.selected()
        if not vals:
            return
        dlg  = Modal(self, "Add Notes & Prescription", width=640, height=380)
        fields = [
            {"name":"notes",        "label":"Doctor Notes",    "type":"text", "height":3, "span":2},
            {"name":"prescription", "label":"Prescription",    "type":"text", "height":3, "span":2},
        ]
        fb = FormBuilder(dlg.body, fields, cols=1)
        def save():
            data = fb.get_all()
            self._svc.update_status(vals[0], "completed",
                                    data.get("notes",""), data.get("prescription",""))
            dlg.destroy()
            self._load()
        dlg.footer(save, "Save & Complete")
        dlg.wait_window()
