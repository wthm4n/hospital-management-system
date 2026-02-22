import tkinter as tk
from tkinter import messagebox
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import *
from ui.widgets import Btn, Table, SearchEntry, SectionHeader, StatCard, MiniChart, DonutChart
from ui.dialogs import Modal, FormBuilder, confirm, show_detail
from services.services import (AdmissionService, PatientService, DoctorService,
                                WardService, InventoryService, ReportService)
from utils.helpers import fmt_currency, today
from database.connection import db


class AdmissionModule(tk.Frame):
    def __init__(self, parent, user):
        super().__init__(parent, bg=C_BG)
        self.pack(fill="both", expand=True)
        self.user = user
        self._svc  = AdmissionService()
        self._build()
        self._load()

    def _build(self):
        top = tk.Frame(self, bg=C_BG)
        top.pack(fill="x", pady=(0, 14))
        SectionHeader(top, "Hospital Admissions", "Admit patients and manage ward assignments").pack(side="left")
        acts = tk.Frame(top, bg=C_BG)
        acts.pack(side="right")
        self._filter = tk.StringVar(value="all")
        for label, val in [("All","all"),("Admitted","admitted"),("Discharged","discharged")]:
            tk.Radiobutton(acts, text=label, variable=self._filter, value=val,
                           font=F_SMALL, bg=C_BG, fg=C_MUTED,
                           selectcolor=C_SURFACE2, activebackground=C_BG,
                           command=self._load).pack(side="left", padx=5)
        tk.Frame(acts, bg=C_BORDER, width=1, height=28).pack(side="left", padx=8)
        Btn(acts, "Admit Patient", self._admit,     "primary",  icon="＋").pack(side="left", padx=3)
        Btn(acts, "Discharge",     self._discharge, "success",  icon="✓").pack(side="left", padx=2)
        Btn(acts, "View",          self._view,      "ghost",    icon="◎").pack(side="left", padx=2)
        self._tbl = Table(self,
            ["Adm ID","Patient","Doctor","Ward","Bed","Admitted","Discharged","Days","Diagnosis","Status"],
            {"Adm ID":90,"Patient":150,"Doctor":150,"Ward":120,"Bed":60,
             "Admitted":100,"Discharged":100,"Days":55,"Diagnosis":170,"Status":90})
        self._tbl.pack(fill="both", expand=True)

    def _load(self):
        self._tbl.clear()
        for a in self._svc.get_all(self._filter.get()):
            self._tbl.add([
                a.get("admid",""), a.get("patient_name",""), a.get("doctor_name",""),
                a.get("ward_name",""), a.get("bed",""),
                a.get("admitted_on",""), a.get("discharged_on",""),
                a.get("total_days",""), a.get("diagnosis",""), a.get("status","")
            ], tag=a.get("status","admitted"))

    def _admit(self, _=None):
        patients = PatientService().get_all()
        doctors  = DoctorService().get_all(active_only=True)
        wards    = WardService().get_available()
        if not patients or not doctors:
            messagebox.showwarning("Missing Data", "Add patients and doctors first")
            return
        if not wards:
            messagebox.showwarning("No Beds", "No available beds in any ward")
            return
        pat_opts  = [f"{p['pid']} — {p['full_name']}" for p in patients]
        doc_opts  = [f"{d['did']} — {d['full_name']}" for d in doctors]
        ward_opts = [f"{w['wid']} — {w['name']} ({int(w.get('total_beds',0))-int(w.get('occupied',0))} beds free)" for w in wards]
        fields = [
            {"name":"patient",   "label":"Patient",   "type":"combo", "values":pat_opts, "required":True},
            {"name":"doctor",    "label":"Doctor",    "type":"combo", "values":doc_opts, "required":True},
            {"name":"ward",      "label":"Ward",      "type":"combo", "values":ward_opts,"required":True},
            {"name":"bed",       "label":"Bed Number","default":"",   "placeholder":"e.g. 4A"},
            {"name":"diagnosis", "label":"Diagnosis", "placeholder":"Primary diagnosis"},
            {"name":"date",      "label":"Admission Date","default":today(), "placeholder":"YYYY-MM-DD"},
            {"name":"notes",     "label":"Notes",     "type":"text"},
        ]
        dlg = Modal(self, "Admit Patient", width=720)
        fb  = FormBuilder(dlg.body, fields, cols=2)
        def save():
            data = fb.get_all()
            errs = fb.validate_required()
            if errs:
                messagebox.showerror("Required", ", ".join(errs), parent=dlg)
                return
            pat_id  = data["patient"].split(" — ")[0]
            doc_id  = data["doctor"].split(" — ")[0]
            wid     = data["ward"].split(" — ")[0]
            patient = next((p for p in patients if p["pid"] == pat_id), None)
            doctor  = next((d for d in doctors  if d["did"] == doc_id), None)
            ward    = next((w for w in wards    if w["wid"] == wid), None)
            record  = {
                "pid": pat_id, "patient_name": patient["full_name"] if patient else "",
                "did": doc_id, "doctor_name":  doctor["full_name"]  if doctor  else "",
                "wid": wid,    "ward_name":    ward["name"]          if ward    else "",
                "bed": data["bed"], "diagnosis": data["diagnosis"],
                "admitted_on": data["date"], "daily_rate": ward.get("charge_per_day",0) if ward else 0,
                "notes": data["notes"],
            }
            ok, _ = self._svc.admit(record, self.user["username"])
            if ok:
                dlg.destroy()
                self._load()
        dlg.footer(save, "Admit Patient")
        dlg.wait_window()

    def _discharge(self, _=None):
        vals = self._tbl.selected()
        if not vals:
            return
        if confirm(self, f"Discharge patient {vals[1]}?", "Discharge"):
            ok = self._svc.discharge(vals[0], self.user["username"])
            if ok:
                self._load()
            else:
                messagebox.showinfo("Info", "Patient is already discharged")

    def _view(self, _=None):
        vals = self._tbl.selected()
        if not vals:
            return
        a = db.find_one("admissions", {"admid": vals[0]})
        if not a:
            return
        show_detail(self, f"Admission — {a.get('admid','')}", [
            ("Admission ID",   a.get("admid","")),
            ("Patient",        a.get("patient_name","")),
            ("Doctor",         a.get("doctor_name","")),
            ("Ward",           a.get("ward_name","")),
            ("Bed",            a.get("bed","")),
            ("Diagnosis",      a.get("diagnosis","")),
            ("Admitted On",    a.get("admitted_on","")),
            ("Discharged On",  a.get("discharged_on","—")),
            ("Total Days",     a.get("total_days","—")),
            ("Daily Rate",     fmt_currency(a.get("daily_rate",0))),
            ("Est. Charge",    fmt_currency(float(a.get("daily_rate",0)) * max(1, int(a.get("total_days",1) or 1)))),
            ("Notes",          a.get("notes","—")),
            ("Status",         a.get("status","").title()),
        ])


class InventoryModule(tk.Frame):
    def __init__(self, parent, user):
        super().__init__(parent, bg=C_BG)
        self.pack(fill="both", expand=True)
        self.user = user
        self._svc  = InventoryService()
        self._build()
        self._load()

    def _build(self):
        top = tk.Frame(self, bg=C_BG)
        top.pack(fill="x", pady=(0, 14))
        SectionHeader(top, "Pharmacy & Inventory", "Medicine and supply stock management").pack(side="left")
        acts = tk.Frame(top, bg=C_BG)
        acts.pack(side="right")
        self._low_only = tk.BooleanVar(value=False)
        tk.Checkbutton(acts, text="Low stock only", variable=self._low_only,
                       font=F_SMALL, bg=C_BG, fg=C_YELLOW,
                       selectcolor=C_SURFACE2, activebackground=C_BG,
                       command=self._load).pack(side="left", padx=6)
        self._search = SearchEntry(acts, "Search items...", on_change=self._load)
        self._search.pack(side="left", padx=(4, 10))
        Btn(acts, "Add Item",  self._add,     "primary",  icon="＋").pack(side="left", padx=3)
        Btn(acts, "Restock",   self._restock, "success",  icon="↑").pack(side="left", padx=2)
        Btn(acts, "Dispense",  self._dispense,"warning",  icon="↓").pack(side="left", padx=2)
        Btn(acts, "Edit",      self._edit,    "outline",  icon="✎").pack(side="left", padx=2)
        Btn(acts, "Delete",    self._delete,  "danger",   icon="✕").pack(side="left", padx=2)
        self._tbl = Table(self,
            ["Item ID","Name","Category","Qty","Unit","Unit Price","Value","Supplier","Reorder","Expiry","Location"],
            {"Item ID":80,"Name":180,"Category":110,"Qty":60,"Unit":70,"Unit Price":80,
             "Value":80,"Supplier":120,"Reorder":70,"Expiry":100,"Location":110})
        self._tbl.pack(fill="both", expand=True)

    def _load(self):
        self._tbl.clear()
        q = self._search.get().lower()
        for item in self._svc.get_all(low_only=self._low_only.get()):
            if q and q not in item.get("name","").lower() and q not in item.get("category","").lower():
                continue
            qty   = int(item.get("quantity",0))
            rl    = int(item.get("reorder_level",10))
            val   = qty * float(item.get("unit_price",0))
            tag   = "critical" if qty == 0 else ("low" if qty <= rl else "")
            self._tbl.add([
                item.get("iid",""), item.get("name",""), item.get("category",""),
                qty, item.get("unit",""), fmt_currency(item.get("unit_price",0)),
                fmt_currency(val), item.get("supplier",""), rl,
                item.get("expiry",""), item.get("location","")
            ], tag=tag)

    def _fields(self, e=None):
        e = e or {}
        return [
            {"name":"name",          "label":"Item Name",      "required":True, "default":e.get("name",""),       "placeholder":"e.g. Paracetamol 500mg"},
            {"name":"category",      "label":"Category",       "type":"combo",
             "values":["Medicine","PPE","IV Fluids","Wound Care","Equipment","Surgical","Lab Supplies","Other"],
             "default":e.get("category","Medicine")},
            {"name":"quantity",      "label":"Initial Quantity","default":str(e.get("quantity","0")), "placeholder":"0"},
            {"name":"unit",          "label":"Unit",            "default":e.get("unit",""), "placeholder":"tablets / bags / pieces"},
            {"name":"unit_price",    "label":"Unit Price ($)",  "default":str(e.get("unit_price","0")), "placeholder":"0.00"},
            {"name":"supplier",      "label":"Supplier",        "default":e.get("supplier",""), "placeholder":"Supplier name"},
            {"name":"reorder_level", "label":"Reorder Level",   "default":str(e.get("reorder_level","10")), "placeholder":"10"},
            {"name":"batch",         "label":"Batch No.",       "default":e.get("batch",""),    "placeholder":"BATCH-001"},
            {"name":"expiry",        "label":"Expiry Date",     "default":e.get("expiry",""),   "placeholder":"YYYY-MM-DD"},
            {"name":"location",      "label":"Storage Location","default":e.get("location","Pharmacy Store"), "placeholder":"Pharmacy Store"},
        ]

    def _add(self, _=None):
        dlg = Modal(self, "Add Inventory Item", width=720)
        fb  = FormBuilder(dlg.body, self._fields())
        def save():
            data = fb.get_all()
            errs = fb.validate_required()
            if errs:
                messagebox.showerror("Required", ", ".join(errs), parent=dlg)
                return
            try:
                data["quantity"]      = int(data.get("quantity","0") or 0)
                data["unit_price"]    = float(data.get("unit_price","0") or 0)
                data["reorder_level"] = int(data.get("reorder_level","10") or 10)
            except ValueError:
                pass
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
        item = db.find_one("inventory", {"iid": vals[0]})
        if not item:
            return
        dlg = Modal(self, f"Edit — {item['name']}", width=720)
        fb  = FormBuilder(dlg.body, self._fields(item))
        def save():
            data = fb.get_all()
            try:
                data["quantity"]      = int(data.get("quantity","0") or 0)
                data["unit_price"]    = float(data.get("unit_price","0") or 0)
                data["reorder_level"] = int(data.get("reorder_level","10") or 10)
            except ValueError:
                pass
            self._svc.update(vals[0], data)
            dlg.destroy()
            self._load()
        dlg.footer(save)
        dlg.wait_window()

    def _restock(self, _=None):
        vals = self._tbl.selected()
        if not vals:
            return
        from ui.dialogs import ask_value
        amt = ask_value(self, f"How many units to add for:\n{vals[1]}?", "Restock Item")
        if amt:
            try:
                qty = int(amt)
                if qty > 0:
                    self._svc.restock(vals[0], qty, self.user["username"])
                    self._load()
            except ValueError:
                messagebox.showerror("Invalid", "Enter a valid number")

    def _dispense(self, _=None):
        vals = self._tbl.selected()
        if not vals:
            return
        from ui.dialogs import ask_value
        amt = ask_value(self, f"How many units to dispense from:\n{vals[1]}?", "Dispense Item")
        if amt:
            try:
                qty = int(amt)
                if qty > 0:
                    ok, msg = self._svc.dispense(vals[0], qty, self.user["username"])
                    if ok:
                        self._load()
                    else:
                        messagebox.showerror("Cannot Dispense", msg)
            except ValueError:
                messagebox.showerror("Invalid", "Enter a valid number")

    def _delete(self, _=None):
        vals = self._tbl.selected()
        if not vals:
            return
        if confirm(self, f"Delete {vals[1]} from inventory?", "Delete Item"):
            self._svc.delete(vals[0])
            self._load()


class WardModule(tk.Frame):
    def __init__(self, parent, user):
        super().__init__(parent, bg=C_BG)
        self.pack(fill="both", expand=True)
        self.user = user
        self._svc  = WardService()
        self._build()
        self._load()

    def _build(self):
        top = tk.Frame(self, bg=C_BG)
        top.pack(fill="x", pady=(0, 14))
        SectionHeader(top, "Ward Management", "Hospital wards, beds and occupancy").pack(side="left")
        acts = tk.Frame(top, bg=C_BG)
        acts.pack(side="right")
        Btn(acts, "Add Ward", self._add,  "primary", icon="＋").pack(side="left", padx=3)
        Btn(acts, "Edit",     self._edit, "outline", icon="✎").pack(side="left", padx=2)
        Btn(acts, "Refresh",  self._load, "ghost",   icon="↺").pack(side="left", padx=2)
        self._tbl = Table(self,
            ["Ward ID","Name","Type","Total Beds","Occupied","Available","Floor","Rate/Day"],
            {"Ward ID":80,"Name":160,"Type":120,"Total Beds":90,"Occupied":80,"Available":80,"Floor":80,"Rate/Day":90})
        self._tbl.pack(fill="both", expand=True)

    def _load(self):
        self._tbl.clear()
        for w in self._svc.get_all():
            total = int(w.get("total_beds",0))
            occ   = int(w.get("occupied",0))
            avail = total - occ
            tag   = "critical" if avail == 0 else ("active" if avail > 3 else "low")
            self._tbl.add([
                w.get("wid",""), w.get("name",""), w.get("ward_type",""),
                total, occ, avail, w.get("floor",""),
                fmt_currency(w.get("charge_per_day",0))
            ], tag=tag)

    def _fields(self, e=None):
        e = e or {}
        return [
            {"name":"name",           "label":"Ward Name",      "required":True, "default":e.get("name",""),      "placeholder":"e.g. General Ward A"},
            {"name":"ward_type",      "label":"Type",           "type":"combo",
             "values":["General","Intensive Care","Pediatrics","Surgical","Maternity","Oncology","Orthopedics","Neurology"],
             "default":e.get("ward_type","General")},
            {"name":"total_beds",     "label":"Total Beds",     "default":str(e.get("total_beds","10")), "placeholder":"10"},
            {"name":"floor",          "label":"Floor",          "default":e.get("floor","Ground"), "placeholder":"Ground"},
            {"name":"charge_per_day", "label":"Charge Per Day ($)","default":str(e.get("charge_per_day","0")), "placeholder":"0"},
        ]

    def _add(self, _=None):
        dlg = Modal(self, "Add Ward", width=640)
        fb  = FormBuilder(dlg.body, self._fields())
        def save():
            data = fb.get_all()
            errs = fb.validate_required()
            if errs:
                messagebox.showerror("Required", ", ".join(errs), parent=dlg)
                return
            try:
                data["total_beds"]     = int(data.get("total_beds","10") or 10)
                data["charge_per_day"] = float(data.get("charge_per_day","0") or 0)
            except ValueError:
                pass
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
        ward = db.find_one("wards", {"wid": vals[0]})
        if not ward:
            return
        dlg = Modal(self, f"Edit — {ward['name']}", width=640)
        fb  = FormBuilder(dlg.body, self._fields(ward))
        def save():
            data = fb.get_all()
            try:
                data["total_beds"]     = int(data.get("total_beds","10") or 10)
                data["charge_per_day"] = float(data.get("charge_per_day","0") or 0)
            except ValueError:
                pass
            self._svc.update(vals[0], data)
            dlg.destroy()
            self._load()
        dlg.footer(save)
        dlg.wait_window()


class UserModule(tk.Frame):
    def __init__(self, parent, user):
        super().__init__(parent, bg=C_BG)
        self.pack(fill="both", expand=True)
        self.user = user
        self._build()
        self._load()

    def _build(self):
        top = tk.Frame(self, bg=C_BG)
        top.pack(fill="x", pady=(0, 14))
        SectionHeader(top, "User Management", "System accounts and role assignments").pack(side="left")
        acts = tk.Frame(top, bg=C_BG)
        acts.pack(side="right")
        Btn(acts, "Add User",       self._add,       "primary", icon="＋").pack(side="left", padx=3)
        Btn(acts, "Reset Password", self._reset_pwd, "warning", icon="🔑").pack(side="left", padx=2)
        Btn(acts, "Toggle Active",  self._toggle,    "outline", icon="⊙").pack(side="left", padx=2)
        Btn(acts, "Delete",         self._delete,    "danger",  icon="✕").pack(side="left", padx=2)
        self._tbl = Table(self,
            ["Username","Full Name","Role","Email","Phone","Active","Last Login","Created"],
            {"Username":110,"Full Name":160,"Role":110,"Email":180,"Phone":120,
             "Active":70,"Last Login":130,"Created":100})
        self._tbl.pack(fill="both", expand=True)

    def _load(self):
        self._tbl.clear()
        for u in db.find("users", sort="created_at"):
            self._tbl.add([
                u.get("username",""), u.get("full_name",""),
                u.get("role","").replace("_"," ").title(),
                u.get("email",""), u.get("phone",""),
                "Yes" if u.get("is_active",1) else "No",
                u.get("last_login","—"), u.get("created_at","")[:10]
            ], tag="active" if u.get("is_active",1) else "inactive")

    def _add(self, _=None):
        from utils.helpers import hash_pw, now
        fields = [
            {"name":"username",  "label":"Username",   "required":True,  "placeholder":"e.g. jsmith"},
            {"name":"password",  "label":"Password",   "required":True,  "secret":True, "placeholder":"Min 6 chars"},
            {"name":"full_name", "label":"Full Name",  "placeholder":"First Last"},
            {"name":"role",      "label":"Role",       "type":"combo",
             "values":["admin","doctor","receptionist","pharmacist","nurse","accountant","lab_tech"]},
            {"name":"email",     "label":"Email",      "placeholder":"user@hospital.com"},
            {"name":"phone",     "label":"Phone",      "placeholder":"+1-555-0000"},
        ]
        dlg = Modal(self, "Add User", width=680)
        fb  = FormBuilder(dlg.body, fields, cols=2)
        def save():
            data = fb.get_all()
            errs = fb.validate_required()
            if errs:
                messagebox.showerror("Required", ", ".join(errs), parent=dlg)
                return
            if len(data.get("password","")) < 6:
                messagebox.showerror("Password", "Password must be at least 6 characters", parent=dlg)
                return
            if db.find_one("users", {"username": data["username"]}):
                messagebox.showerror("Error", "Username already exists", parent=dlg)
                return
            data["password"]   = hash_pw(data["password"])
            data["is_active"]  = 1
            data["created_at"] = now()
            db.insert("users", data)
            dlg.destroy()
            self._load()
        dlg.footer(save)
        dlg.wait_window()

    def _reset_pwd(self, _=None):
        vals = self._tbl.selected()
        if not vals:
            return
        from ui.dialogs import ask_value
        from utils.helpers import hash_pw
        new_pw = ask_value(self, f"New password for '{vals[0]}':", "Reset Password")
        if new_pw:
            if len(new_pw) < 6:
                messagebox.showerror("Error", "Password must be at least 6 characters")
                return
            db.update("users", {"username": vals[0]}, {"password": hash_pw(new_pw)})

    def _toggle(self, _=None):
        vals = self._tbl.selected()
        if not vals or vals[0] == "admin":
            return
        user = db.find_one("users", {"username": vals[0]})
        if not user:
            return
        new_state = 0 if user.get("is_active", 1) else 1
        db.update("users", {"username": vals[0]}, {"is_active": new_state})
        self._load()

    def _delete(self, _=None):
        vals = self._tbl.selected()
        if not vals:
            return
        if vals[0] == "admin":
            messagebox.showerror("Error", "Cannot delete the admin account")
            return
        if confirm(self, f"Delete user '{vals[0]}'? This cannot be undone.", "Delete User"):
            db.delete("users", {"username": vals[0]})
            self._load()


class LabModule(tk.Frame):
    def __init__(self, parent, user):
        super().__init__(parent, bg=C_BG)
        self.pack(fill="both", expand=True)
        self.user = user
        from services.services import LabService
        self._svc  = LabService()
        self._build()
        self._load()

    def _build(self):
        top = tk.Frame(self, bg=C_BG)
        top.pack(fill="x", pady=(0, 14))
        SectionHeader(top, "Lab Tests", "Order and track laboratory tests").pack(side="left")
        acts = tk.Frame(top, bg=C_BG)
        acts.pack(side="right")
        self._filter = tk.StringVar(value="all")
        for label, val in [("All","all"),("Pending","pending"),("Completed","completed")]:
            tk.Radiobutton(acts, text=label, variable=self._filter, value=val,
                           font=F_SMALL, bg=C_BG, fg=C_MUTED,
                           selectcolor=C_SURFACE2, activebackground=C_BG,
                           command=self._load).pack(side="left", padx=5)
        tk.Frame(acts, bg=C_BORDER, width=1, height=28).pack(side="left", padx=8)
        Btn(acts, "Order Test",   self._order,    "primary", icon="＋").pack(side="left", padx=3)
        Btn(acts, "Enter Result", self._complete, "success", icon="✓").pack(side="left", padx=2)
        self._tbl = Table(self,
            ["Test ID","Patient","Doctor","Test Name","Ordered On","Completed","Status","Result"],
            {"Test ID":90,"Patient":150,"Doctor":150,"Test Name":180,"Ordered On":110,
             "Completed":110,"Status":90,"Result":220})
        self._tbl.pack(fill="both", expand=True)

    def _load(self):
        self._tbl.clear()
        for t in self._svc.get_all(self._filter.get()):
            self._tbl.add([
                t.get("ltid",""), t.get("patient_name",""), t.get("doctor_name",""),
                t.get("test_name",""), t.get("ordered_on",""),
                t.get("completed_on",""), t.get("status",""),
                t.get("result","—")
            ], tag=t.get("status","pending"))

    def _order(self, _=None):
        patients = PatientService().get_all()
        doctors  = DoctorService().get_all(active_only=True)
        if not patients or not doctors:
            messagebox.showwarning("Missing Data", "Add patients and doctors first")
            return
        pat_opts = [f"{p['pid']} — {p['full_name']}" for p in patients]
        doc_opts = [f"{d['did']} — {d['full_name']}" for d in doctors]
        fields = [
            {"name":"patient",   "label":"Patient",   "type":"combo", "values":pat_opts, "required":True},
            {"name":"doctor",    "label":"Ordered By", "type":"combo", "values":doc_opts, "required":True},
            {"name":"test_name", "label":"Test Name",  "required":True, "placeholder":"e.g. CBC, Blood Sugar, X-Ray"},
            {"name":"ordered_on","label":"Ordered On", "default":today(), "placeholder":"YYYY-MM-DD"},
        ]
        dlg = Modal(self, "Order Lab Test", width=660)
        fb  = FormBuilder(dlg.body, fields, cols=2)
        def save():
            data = fb.get_all()
            errs = fb.validate_required()
            if errs:
                messagebox.showerror("Required", ", ".join(errs), parent=dlg)
                return
            pat_id  = data["patient"].split(" — ")[0]
            doc_id  = data["doctor"].split(" — ")[0]
            patient = next((p for p in patients if p["pid"] == pat_id), None)
            doctor  = next((d for d in doctors  if d["did"] == doc_id), None)
            record  = {
                "pid": pat_id, "patient_name": patient["full_name"] if patient else "",
                "did": doc_id, "doctor_name":  doctor["full_name"]  if doctor  else "",
                "test_name": data["test_name"], "ordered_on": data["ordered_on"],
            }
            ok, _ = self._svc.order(record, self.user["username"])
            if ok:
                dlg.destroy()
                self._load()
        dlg.footer(save, "Order Test")
        dlg.wait_window()

    def _complete(self, _=None):
        vals = self._tbl.selected()
        if not vals:
            return
        from ui.dialogs import ask_value
        result = ask_value(self, f"Enter result for:\n{vals[3]}", "Enter Test Result")
        if result:
            self._svc.complete(vals[0], result)
            self._load()


class ReportsModule(tk.Frame):
    def __init__(self, parent, user):
        super().__init__(parent, bg=C_BG)
        self.pack(fill="both", expand=True)
        self.user = user
        self._build()

    def _build(self):
        from tkinter import ttk
        SectionHeader(self, "Reports & Analytics", "System-wide statistics and insights").pack(fill="x", pady=(0,14))
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self._overview_tab(nb)
        self._financial_tab(nb)
        self._inventory_tab(nb)
        self._doctor_tab(nb)

    def _overview_tab(self, nb):
        frame = tk.Frame(nb, bg=C_BG)
        nb.add(frame, text="  Overview  ")
        svc = ReportService()
        s   = svc.summary()
        stat_data = [
            ("Total Patients",   s["patients_total"],     C_PRIMARY, "◉", f"{s['patients_active']} active"),
            ("Appointments",     s["appointments_all"],   C_CYAN,    "◷", f"{s['appointments_today']} today"),
            ("Currently Admitted",s["admitted_now"],      C_GREEN,   "⊞", "In wards"),
            ("Active Doctors",   s["doctors_active"],     C_YELLOW,  "◎", "On staff"),
            ("Inventory Items",  s["inventory_items"],    C_ORANGE,  "⊟", f"{len(svc.inventory_alerts())} alerts"),
            ("Lab Pending",      s["lab_pending"],        C_RED,     "⊕", "Awaiting result"),
        ]
        grid = tk.Frame(frame, bg=C_BG)
        grid.pack(fill="x", pady=14)
        for i, (title, val, color, icon, sub) in enumerate(stat_data):
            StatCard(grid, title, val, sub, color, icon).grid(row=0, column=i, padx=6, sticky="nsew")
            grid.grid_columnconfigure(i, weight=1)
        charts = tk.Frame(frame, bg=C_BG)
        charts.pack(fill="both", expand=True, pady=10)
        charts.grid_columnconfigure(0, weight=1)
        charts.grid_columnconfigure(1, weight=1)
        appt_status = {
            "Scheduled": db.count("appointments", {"status":"scheduled"}),
            "Completed": db.count("appointments", {"status":"completed"}),
            "Cancelled": db.count("appointments", {"status":"cancelled"}),
        }
        c1 = tk.Frame(charts, bg=C_CARD, highlightbackground=C_BORDER, highlightthickness=1)
        c1.grid(row=0, column=0, padx=(0,8), sticky="nsew")
        i1 = tk.Frame(c1, bg=C_CARD, padx=14, pady=14)
        i1.pack(fill="both", expand=True)
        tk.Label(i1, text="Appointment Status", font=F_SUB, bg=C_CARD, fg=C_WHITE).pack(anchor="w")
        DonutChart(i1, appt_status, height=220).pack(fill="both", expand=True)
        blood_data = {g: db.count("patients", {"blood": g})
                      for g in ["A+","A-","B+","B-","AB+","AB-","O+","O-"]}
        blood_data = {k: v for k,v in blood_data.items() if v > 0}
        c2 = tk.Frame(charts, bg=C_CARD, highlightbackground=C_BORDER, highlightthickness=1)
        c2.grid(row=0, column=1, padx=(8,0), sticky="nsew")
        i2 = tk.Frame(c2, bg=C_CARD, padx=14, pady=14)
        i2.pack(fill="both", expand=True)
        tk.Label(i2, text="Blood Group Distribution", font=F_SUB, bg=C_CARD, fg=C_WHITE).pack(anchor="w")
        DonutChart(i2, blood_data if blood_data else {"No data":1}, height=220).pack(fill="both", expand=True)

    def _financial_tab(self, nb):
        frame = tk.Frame(nb, bg=C_BG)
        nb.add(frame, text="  Financial  ")
        fin = ReportService().financial()
        stat_data = [
            ("Total Revenue",  fmt_currency(fin["total_revenue"]), C_GREEN,   "◆", f"{fin['total_bills']} invoices"),
            ("Collected",      fmt_currency(fin["collected"]),     C_PRIMARY, "◆", "Paid amount"),
            ("Outstanding",    fmt_currency(fin["outstanding"]),   C_RED,     "◆", "Unpaid balance"),
            ("Paid Invoices",  str(fin["paid_bills"]),             C_GREEN,   "⊙", "Fully settled"),
            ("Pending",        str(fin["pending_bills"]),          C_YELLOW,  "⊙", "Awaiting payment"),
            ("Partial",        str(fin["partial_bills"]),          C_CYAN,    "⊙", "Partially paid"),
        ]
        grid = tk.Frame(frame, bg=C_BG)
        grid.pack(fill="x", pady=14)
        for i, (title, val, color, icon, sub) in enumerate(stat_data):
            StatCard(grid, title, val, sub, color, icon).grid(row=0, column=i, padx=6, sticky="nsew")
            grid.grid_columnconfigure(i, weight=1)
        bill_frame = tk.Frame(frame, bg=C_CARD,
                              highlightbackground=C_BORDER, highlightthickness=1)
        bill_frame.pack(fill="both", expand=True, pady=10)
        inner = tk.Frame(bill_frame, bg=C_CARD, padx=14, pady=14)
        inner.pack(fill="both", expand=True)
        tk.Label(inner, text="Recent Billing Activity", font=F_SUB, bg=C_CARD, fg=C_WHITE).pack(anchor="w", pady=(0,8))
        tbl = Table(inner, ["Bill ID","Patient","Total","Paid","Balance","Mode","Status","Date"],
                    {"Bill ID":90,"Patient":150,"Total":90,"Paid":90,"Balance":90,"Mode":90,"Status":80,"Date":100})
        tbl.pack(fill="both", expand=True)
        for b in db.find("billing", sort="created_at", limit=20):
            total   = float(b.get("total",0))
            paid    = float(b.get("paid",0))
            tbl.add([b.get("bid",""), b.get("patient_name",""),
                     fmt_currency(total), fmt_currency(paid),
                     fmt_currency(total-paid), b.get("payment_mode","—"),
                     b.get("status",""), b.get("created_at","")[:10]],
                    tag=b.get("status","pending"))

    def _inventory_tab(self, nb):
        frame = tk.Frame(nb, bg=C_BG)
        nb.add(frame, text="  Inventory  ")
        items    = db.find("inventory")
        total_v  = sum(float(i.get("quantity",0)) * float(i.get("unit_price",0)) for i in items)
        out      = sum(1 for i in items if int(i.get("quantity",0)) == 0)
        low      = sum(1 for i in items if 0 < int(i.get("quantity",0)) <= int(i.get("reorder_level",10)))
        stat_data = [
            ("Total Items",      str(len(items)),      C_PRIMARY, "◆", "In inventory"),
            ("Inventory Value",  fmt_currency(total_v),C_GREEN,   "◆", "Current stock value"),
            ("Out of Stock",     str(out),             C_RED,     "◆", "Need restocking"),
            ("Low Stock",        str(low),             C_YELLOW,  "◆", "Below reorder level"),
        ]
        grid = tk.Frame(frame, bg=C_BG)
        grid.pack(fill="x", pady=14)
        for i, (title, val, color, icon, sub) in enumerate(stat_data):
            StatCard(grid, title, val, sub, color, icon).grid(row=0, column=i, padx=6, sticky="nsew")
            grid.grid_columnconfigure(i, weight=1)
        alert_frame = tk.Frame(frame, bg=C_CARD,
                               highlightbackground=C_BORDER, highlightthickness=1)
        alert_frame.pack(fill="both", expand=True, pady=10)
        inner = tk.Frame(alert_frame, bg=C_CARD, padx=14, pady=14)
        inner.pack(fill="both", expand=True)
        tk.Label(inner, text="⚠  Stock Alerts", font=F_SUB, bg=C_CARD, fg=C_YELLOW).pack(anchor="w", pady=(0,8))
        tbl = Table(inner, ["Name","Category","Stock","Reorder Level","Unit Price","Value","Expiry","Status"],
                    {"Name":180,"Category":110,"Stock":70,"Reorder Level":100,"Unit Price":80,"Value":80,"Expiry":100,"Status":90})
        tbl.pack(fill="both", expand=True)
        for item in ReportService().inventory_alerts():
            qty   = int(item.get("quantity",0))
            rl    = int(item.get("reorder_level",10))
            val   = qty * float(item.get("unit_price",0))
            tag   = "critical" if qty == 0 else "low"
            status= "OUT OF STOCK" if qty == 0 else "LOW STOCK"
            tbl.add([item.get("name",""), item.get("category",""),
                     qty, rl, fmt_currency(item.get("unit_price",0)),
                     fmt_currency(val), item.get("expiry","—"), status], tag=tag)

    def _doctor_tab(self, nb):
        frame = tk.Frame(nb, bg=C_BG)
        nb.add(frame, text="  Doctor Workload  ")
        card = tk.Frame(frame, bg=C_CARD, highlightbackground=C_BORDER, highlightthickness=1)
        card.pack(fill="both", expand=True, pady=14)
        inner = tk.Frame(card, bg=C_CARD, padx=14, pady=14)
        inner.pack(fill="both", expand=True)
        tk.Label(inner, text="Doctor Appointment Summary", font=F_SUB, bg=C_CARD, fg=C_WHITE).pack(anchor="w", pady=(0,8))
        tbl = Table(inner, ["Doctor","Specialization","Total","Scheduled","Completed","Cancelled","Completion %"],
                    {"Doctor":170,"Specialization":140,"Total":70,"Scheduled":80,"Completed":90,"Cancelled":80,"Completion %":100})
        tbl.pack(fill="both", expand=True)
        appts   = db.find("appointments")
        for doc in db.find("doctors"):
            did   = doc["did"]
            da    = [a for a in appts if a.get("did") == did]
            total = len(da)
            comp  = sum(1 for a in da if a.get("status") == "completed")
            sch   = sum(1 for a in da if a.get("status") == "scheduled")
            cncl  = sum(1 for a in da if a.get("status") == "cancelled")
            pct   = f"{(comp/total*100):.0f}%" if total > 0 else "—"
            tbl.add([doc.get("full_name",""), doc.get("specialization",""),
                     total, sch, comp, cncl, pct])
        doc_data = {d.get("full_name","")[:12]: db.count("appointments", {"did": d["did"]})
                    for d in db.find("doctors")}
        chart_card = tk.Frame(frame, bg=C_CARD,
                              highlightbackground=C_BORDER, highlightthickness=1)
        chart_card.pack(fill="x", pady=(0,14))
        ci = tk.Frame(chart_card, bg=C_CARD, padx=14, pady=14)
        ci.pack(fill="both", expand=True)
        tk.Label(ci, text="Appointments by Doctor", font=F_SUB, bg=C_CARD, fg=C_WHITE).pack(anchor="w")
        MiniChart(ci, doc_data, C_CYAN, height=140).pack(fill="both", expand=True)


class AuditModule(tk.Frame):
    def __init__(self, parent, user):
        super().__init__(parent, bg=C_BG)
        self.pack(fill="both", expand=True)
        self.user = user
        self._build()
        self._load()

    def _build(self):
        top = tk.Frame(self, bg=C_BG)
        top.pack(fill="x", pady=(0, 14))
        SectionHeader(top, "Audit Log", "System activity and change tracking").pack(side="left")
        acts = tk.Frame(top, bg=C_BG)
        acts.pack(side="right")
        Btn(acts, "Refresh", self._load, "ghost", icon="↺").pack(side="left")
        self._tbl = Table(self,
            ["User","Action","Module","Detail","Timestamp"],
            {"User":110,"Action":110,"Module":100,"Detail":360,"Timestamp":140})
        self._tbl.pack(fill="both", expand=True)

    def _load(self):
        self._tbl.clear()
        for entry in ReportService().audit_log(100):
            action = entry.get("action","")
            tag    = ("active" if action in ["LOGIN","ADD","ADMIT"]
                      else "danger" if action in ["DELETE","DEACTIVATE"]
                      else "")
            self._tbl.add([
                entry.get("user",""), entry.get("action",""),
                entry.get("module",""), entry.get("detail",""),
                entry.get("ts","")
            ], tag=tag)
