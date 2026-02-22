import tkinter as tk
from tkinter import messagebox
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import *
from ui.widgets import Btn, Table, SectionHeader
from ui.dialogs import Modal, FormBuilder, confirm
from services.services import BillingService, PatientService
from utils.helpers import fmt_currency, today


class BillingModule(tk.Frame):
    def __init__(self, parent, user):
        super().__init__(parent, bg=C_BG)
        self.pack(fill="both", expand=True)
        self.user = user
        self._svc  = BillingService()
        self._build()
        self._load()

    def _build(self):
        top = tk.Frame(self, bg=C_BG)
        top.pack(fill="x", pady=(0, 14))
        SectionHeader(top, "Billing & Payments", "Invoice management and payment tracking").pack(side="left")
        acts = tk.Frame(top, bg=C_BG)
        acts.pack(side="right")
        self._filter = tk.StringVar(value="all")
        for label, val in [("All","all"),("Pending","pending"),("Partial","partial"),("Paid","paid")]:
            tk.Radiobutton(acts, text=label, variable=self._filter, value=val,
                           font=F_SMALL, bg=C_BG, fg=C_MUTED,
                           selectcolor=C_SURFACE2, activebackground=C_BG,
                           command=self._load).pack(side="left", padx=5)
        tk.Frame(acts, bg=C_BORDER, width=1, height=28).pack(side="left", padx=8)
        Btn(acts, "New Invoice",    self._create,  "primary",  icon="＋").pack(side="left", padx=3)
        Btn(acts, "Record Payment", self._payment, "success",  icon="$").pack(side="left", padx=2)
        Btn(acts, "View Invoice",   self._view,    "ghost",    icon="◎").pack(side="left", padx=2)

        self._tbl = Table(self,
            ["Bill ID","Patient","Subtotal","Discount","Tax","Total","Paid","Balance","Mode","Status"],
            {"Bill ID":90,"Patient":150,"Subtotal":90,"Discount":80,"Tax":70,
             "Total":90,"Paid":90,"Balance":90,"Mode":90,"Status":80})
        self._tbl.pack(fill="both", expand=True)

    def _load(self):
        self._tbl.clear()
        for b in self._svc.get_all(self._filter.get()):
            total   = float(b.get("total",0))
            paid    = float(b.get("paid",0))
            balance = total - paid
            self._tbl.add([
                b.get("bid",""), b.get("patient_name",""),
                fmt_currency(b.get("subtotal",0)), fmt_currency(b.get("discount",0)),
                fmt_currency(b.get("tax",0)),      fmt_currency(total),
                fmt_currency(paid),                fmt_currency(balance),
                b.get("payment_mode","—"),         b.get("status","pending")
            ], tag=b.get("status","pending"))

    def _create(self, _=None):
        patients = PatientService().get_all()
        if not patients:
            messagebox.showwarning("No Patients", "Register patients first")
            return
        pat_opts = [f"{p['pid']} — {p['full_name']}" for p in patients]
        dlg   = Modal(self, "Create Invoice", width=760, height=580)
        inner = dlg.make_scrollable()
        tk.Label(inner, text="Patient & Billing Details", font=F_SUB,
                 bg=C_SURFACE, fg=C_MUTED).pack(anchor="w", pady=(0,10))
        top_fields = [
            {"name":"patient",   "label":"Patient",         "type":"combo", "values":pat_opts, "required":True},
            {"name":"discount",  "label":"Discount ($)",    "default":"0",  "placeholder":"0.00"},
            {"name":"tax_rate",  "label":"Tax Rate (%)",    "default":"10", "placeholder":"10"},
            {"name":"payment_mode","label":"Payment Mode",  "type":"combo",
             "values":["Cash","Card","Insurance","Bank Transfer","Other"], "default":"Cash"},
        ]
        fb_top = FormBuilder(inner, top_fields, cols=2)
        tk.Label(inner, text="Billing Items (one per line: Description : Amount)",
                 font=F_LABEL, bg=C_SURFACE, fg=C_MUTED).pack(anchor="w", pady=(14,4))
        items_box = tk.Frame(inner, bg=C_SURFACE2,
                             highlightbackground=C_BORDER, highlightthickness=1)
        items_box.pack(fill="x")
        items_text = tk.Text(items_box, height=7, font=F_MONO, bg=C_SURFACE2,
                             fg=C_TEXT, relief="flat", insertbackground=C_WHITE,
                             padx=12, pady=10)
        items_text.pack(fill="x")
        items_text.insert("1.0",
            "Consultation : 150\nLab Tests : 80\nMedication : 45")

        def save():
            top_data = fb_top.get_all()
            errs = fb_top.validate_required()
            if errs:
                messagebox.showerror("Required", ", ".join(errs), parent=dlg)
                return
            raw      = items_text.get("1.0","end-1c").strip()
            items    = []
            subtotal = 0.0
            for line in raw.split("\n"):
                line = line.strip()
                if ":" in line:
                    name, price_str = line.rsplit(":", 1)
                    try:
                        price = float(price_str.strip())
                        items.append({"name": name.strip(), "price": price})
                        subtotal += price
                    except ValueError:
                        pass
            if not items:
                messagebox.showerror("Error", "Add at least one billing item", parent=dlg)
                return
            try:
                discount = float(top_data.get("discount","0") or 0)
                tax_rate = float(top_data.get("tax_rate","10") or 10)
            except ValueError:
                discount, tax_rate = 0.0, 10.0
            taxable = max(0, subtotal - discount)
            tax   = taxable * (tax_rate / 100)
            total = taxable + tax
            pat_id  = top_data["patient"].split(" — ")[0]
            patient = next((p for p in patients if p["pid"] == pat_id), None)
            record = {
                "pid": pat_id, "patient_name": patient["full_name"] if patient else "",
                "items": items, "subtotal": round(subtotal, 2),
                "discount": round(discount, 2), "tax": round(tax, 2),
                "total": round(total, 2), "payment_mode": top_data.get("payment_mode","Cash"),
            }
            ok, bid = self._svc.create(record, self.user["username"])
            if ok:
                dlg.destroy()
                self._load()
        dlg.footer(save, "Create Invoice")
        dlg.wait_window()

    def _payment(self, _=None):
        vals = self._tbl.selected()
        if not vals:
            return
        bill = self._svc.get(vals[0])
        if not bill:
            return
        total   = float(bill.get("total",0))
        paid    = float(bill.get("paid",0))
        balance = total - paid
        if balance <= 0:
            messagebox.showinfo("Already Paid", "This invoice is fully paid")
            return
        dlg    = Modal(self, f"Record Payment — {vals[0]}", width=440, height=340)
        fields = [
            {"name":"amount", "label":f"Amount (Balance: {fmt_currency(balance)})", "required":True,
             "default":f"{balance:.2f}", "placeholder":"0.00"},
            {"name":"mode",   "label":"Payment Mode", "type":"combo",
             "values":["Cash","Card","Insurance","Bank Transfer","Other"], "default":"Cash"},
        ]
        fb = FormBuilder(dlg.body, fields, cols=1)
        def save():
            data = fb.get_all()
            try:
                amount = float(data.get("amount","0") or 0)
            except ValueError:
                messagebox.showerror("Invalid", "Enter a valid amount", parent=dlg)
                return
            if amount <= 0 or amount > balance:
                messagebox.showerror("Invalid", f"Amount must be between $0.01 and {fmt_currency(balance)}", parent=dlg)
                return
            ok, msg = self._svc.record_payment(vals[0], amount, data.get("mode","Cash"),
                                               self.user["username"])
            if ok:
                dlg.destroy()
                self._load()
        dlg.footer(save, "Record Payment")
        dlg.wait_window()

    def _view(self, _=None):
        vals = self._tbl.selected()
        if not vals:
            return
        bill = self._svc.get(vals[0])
        if not bill:
            return
        dlg = Modal(self, f"Invoice — {bill.get('bid','')}", width=520, height=560)
        b   = dlg.body
        header = tk.Frame(b, bg=C_SURFACE)
        header.pack(fill="x", pady=(0,14))
        tk.Label(header, text="INVOICE", font=("Segoe UI", 18, "bold"),
                 bg=C_SURFACE, fg=C_PRIMARY).pack(side="left")
        tk.Label(header, text=bill.get("bid",""), font=F_MONO,
                 bg=C_SURFACE, fg=C_MUTED).pack(side="right", pady=8)
        info_rows = [
            ("Patient",  bill.get("patient_name","")),
            ("Date",     bill.get("created_at","")[:10]),
            ("Mode",     bill.get("payment_mode","—")),
        ]
        for label, val in info_rows:
            row = tk.Frame(b, bg=C_SURFACE)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=label+":", font=F_LABEL, bg=C_SURFACE,
                     fg=C_MUTED, width=12, anchor="w").pack(side="left")
            tk.Label(row, text=val, font=F_BODY, bg=C_SURFACE, fg=C_TEXT).pack(side="left")
        tk.Frame(b, bg=C_BORDER, height=1).pack(fill="x", pady=12)
        tk.Label(b, text="Items", font=F_SUB, bg=C_SURFACE, fg=C_MUTED).pack(anchor="w", pady=(0,6))
        items = bill.get("items", [])
        if isinstance(items, str):
            try: items = json.loads(items)
            except: items = []
        for item in items:
            row = tk.Frame(b, bg=C_SURFACE2)
            row.pack(fill="x", pady=1)
            tk.Label(row, text=f"  {item.get('name','Item')}", font=F_BODY,
                     bg=C_SURFACE2, fg=C_TEXT, anchor="w").pack(side="left", fill="x", expand=True, ipady=6)
            tk.Label(row, text=f"  {fmt_currency(item.get('price',0))}  ", font=F_MONO,
                     bg=C_SURFACE2, fg=C_GREEN).pack(side="right", ipady=6)
        tk.Frame(b, bg=C_BORDER, height=1).pack(fill="x", pady=10)
        totals = [
            ("Subtotal",  fmt_currency(bill.get("subtotal",0)), C_MUTED),
            ("Discount",  f"- {fmt_currency(bill.get('discount',0))}", C_YELLOW),
            ("Tax",       fmt_currency(bill.get("tax",0)), C_MUTED),
            ("TOTAL",     fmt_currency(bill.get("total",0)), C_WHITE),
            ("Paid",      fmt_currency(bill.get("paid",0)), C_GREEN),
            ("Balance",   fmt_currency(float(bill.get("total",0)) - float(bill.get("paid",0))), C_RED),
        ]
        for label, val, color in totals:
            row = tk.Frame(b, bg=C_SURFACE)
            row.pack(fill="x", pady=1)
            font = F_SUB if label == "TOTAL" else F_LABEL
            tk.Label(row, text=label, font=font, bg=C_SURFACE,
                     fg=C_MUTED if label != "TOTAL" else C_WHITE).pack(side="left")
            tk.Label(row, text=val, font=font, bg=C_SURFACE, fg=color).pack(side="right")
        Btn(dlg.body, "Close", dlg.destroy, "ghost").pack(pady=14)
