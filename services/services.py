import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import db
from utils.helpers import hash_pw, verify_pw, gen_id, now, today


class AuthService:
    def login(self, username: str, password: str):
        user = db.find_one("users", {"username": username.strip()})
        if not user:
            return None, "User not found"
        if not user.get("is_active", 1):
            return None, "Account is disabled"
        if not verify_pw(password, user.get("password", "")):
            return None, "Incorrect password"
        db.update("users", {"username": username}, {"last_login": now()})
        self._audit(username, "LOGIN", "auth", "Logged in")
        return user, "OK"

    def _audit(self, user, action, module, detail):
        db.insert("audit_log", {
            "user": user, "action": action,
            "module": module, "detail": detail, "ts": now()
        })


class PatientService:
    def add(self, data: dict, by: str) -> tuple:
        if not data.get("full_name","").strip():
            return False, "Full name is required"
        data["pid"]        = gen_id("P")
        data["created_at"] = now()
        data["status"]     = "active"
        if db.insert("patients", data):
            db.insert("audit_log", {"user": by, "action": "ADD", "module": "patients",
                                    "detail": f"Added {data['full_name']} ({data['pid']})", "ts": now()})
            return True, data["pid"]
        return False, "Database error"

    def update(self, pid: str, data: dict, by: str) -> bool:
        ok = db.update("patients", {"pid": pid}, data)
        if ok:
            db.insert("audit_log", {"user": by, "action": "EDIT", "module": "patients",
                                    "detail": f"Updated {pid}", "ts": now()})
        return ok

    def deactivate(self, pid: str, by: str) -> bool:
        ok = db.update("patients", {"pid": pid}, {"status": "inactive"})
        if ok:
            db.insert("audit_log", {"user": by, "action": "DEACTIVATE", "module": "patients",
                                    "detail": f"Deactivated {pid}", "ts": now()})
        return ok

    def get_all(self, search=""):
        patients = db.find("patients", sort="created_at")
        if search:
            s = search.lower()
            patients = [p for p in patients
                        if s in p.get("full_name","").lower()
                        or s in p.get("pid","").lower()
                        or s in p.get("phone","").lower()]
        return patients

    def get(self, pid: str):
        return db.find_one("patients", {"pid": pid})


class DoctorService:
    def add(self, data: dict) -> tuple:
        if not data.get("full_name","").strip():
            return False, "Full name is required"
        data["did"]        = gen_id("D")
        data["created_at"] = now()
        if db.insert("doctors", data):
            return True, data["did"]
        return False, "Database error"

    def update(self, did: str, data: dict) -> bool:
        return db.update("doctors", {"did": did}, data)

    def get_all(self, active_only=False):
        q = {"status": "active"} if active_only else None
        return db.find("doctors", q, sort="created_at")

    def get(self, did: str):
        return db.find_one("doctors", {"did": did})


class AppointmentService:
    def book(self, data: dict, by: str) -> tuple:
        data["aid"]        = gen_id("A")
        data["status"]     = "scheduled"
        data["created_at"] = now()
        if db.insert("appointments", data):
            db.insert("audit_log", {"user": by, "action": "BOOK", "module": "appointments",
                                    "detail": f"{data['patient_name']} with {data['doctor_name']} on {data['date']}", "ts": now()})
            return True, data["aid"]
        return False, "Database error"

    def update_status(self, aid: str, status: str, notes="", prescription="") -> bool:
        upd = {"status": status}
        if notes:
            upd["notes"] = notes
        if prescription:
            upd["prescription"] = prescription
        return db.update("appointments", {"aid": aid}, upd)

    def get_all(self, status_filter="all", date_filter=""):
        q = {}
        if status_filter != "all":
            q["status"] = status_filter
        if date_filter:
            q["date"] = date_filter
        return db.find("appointments", q or None, sort="created_at")

    def get_for_patient(self, pid: str):
        return db.find("appointments", {"pid": pid}, sort="created_at")


class BillingService:
    def create(self, data: dict, by: str) -> tuple:
        data["bid"]        = gen_id("B")
        data["paid"]       = 0.0
        data["status"]     = "pending"
        data["created_at"] = now()
        if db.insert("billing", data):
            db.insert("audit_log", {"user": by, "action": "CREATE_BILL", "module": "billing",
                                    "detail": f"Bill {data['bid']} for {data['patient_name']} ${data['total']:.2f}", "ts": now()})
            return True, data["bid"]
        return False, "Database error"

    def record_payment(self, bid: str, amount: float, mode: str, by: str) -> tuple:
        bill = db.find_one("billing", {"bid": bid})
        if not bill:
            return False, "Bill not found"
        new_paid = float(bill.get("paid", 0)) + amount
        total    = float(bill.get("total", 0))
        status   = "paid" if new_paid >= total else "partial"
        db.update("billing", {"bid": bid}, {"paid": round(new_paid, 2),
                                            "status": status,
                                            "payment_mode": mode})
        db.insert("audit_log", {"user": by, "action": "PAYMENT", "module": "billing",
                                "detail": f"${amount:.2f} on {bid} via {mode}", "ts": now()})
        return True, f"Payment recorded. Status: {status.title()}"

    def get_all(self, status_filter="all"):
        q = None if status_filter == "all" else {"status": status_filter}
        return db.find("billing", q, sort="created_at")

    def get(self, bid: str):
        return db.find_one("billing", {"bid": bid})


class InventoryService:
    def add(self, data: dict) -> tuple:
        data["iid"]        = gen_id("I")
        data["created_at"] = now()
        if db.insert("inventory", data):
            return True, data["iid"]
        return False, "Database error"

    def restock(self, iid: str, qty: int, by: str) -> bool:
        item = db.find_one("inventory", {"iid": iid})
        if not item:
            return False
        new_qty = int(item.get("quantity", 0)) + qty
        ok = db.update("inventory", {"iid": iid}, {"quantity": new_qty})
        if ok:
            db.insert("audit_log", {"user": by, "action": "RESTOCK", "module": "inventory",
                                    "detail": f"+{qty} for {item['name']}, new stock: {new_qty}", "ts": now()})
        return ok

    def dispense(self, iid: str, qty: int, by: str) -> tuple:
        item = db.find_one("inventory", {"iid": iid})
        if not item:
            return False, "Item not found"
        current = int(item.get("quantity", 0))
        if current < qty:
            return False, f"Insufficient stock (available: {current})"
        db.update("inventory", {"iid": iid}, {"quantity": current - qty})
        db.insert("audit_log", {"user": by, "action": "DISPENSE", "module": "inventory",
                                "detail": f"-{qty} of {item['name']}", "ts": now()})
        return True, f"Dispensed {qty} {item.get('unit','units')}"

    def get_all(self, low_only=False):
        items = db.find("inventory", sort="name")
        if low_only:
            items = [i for i in items if int(i.get("quantity",0)) <= int(i.get("reorder_level",10))]
        return items

    def update(self, iid: str, data: dict) -> bool:
        return db.update("inventory", {"iid": iid}, data)

    def delete(self, iid: str) -> bool:
        return db.delete("inventory", {"iid": iid})


class WardService:
    def add(self, data: dict) -> tuple:
        data["wid"]        = gen_id("W")
        data["occupied"]   = 0
        data["created_at"] = now()
        if db.insert("wards", data):
            return True, data["wid"]
        return False, "Database error"

    def get_all(self):
        return db.find("wards", sort="created_at")

    def get_available(self):
        wards = db.find("wards")
        return [w for w in wards if int(w.get("total_beds",0)) > int(w.get("occupied",0))]

    def update(self, wid: str, data: dict) -> bool:
        return db.update("wards", {"wid": wid}, data)


class AdmissionService:
    def admit(self, data: dict, by: str) -> tuple:
        data["admid"]      = gen_id("ADM")
        data["status"]     = "admitted"
        data["created_at"] = now()
        if db.insert("admissions", data):
            ward = db.find_one("wards", {"wid": data["wid"]})
            if ward:
                db.update("wards", {"wid": data["wid"]},
                          {"occupied": int(ward.get("occupied",0)) + 1})
            db.insert("audit_log", {"user": by, "action": "ADMIT", "module": "admissions",
                                    "detail": f"Admitted {data['patient_name']}", "ts": now()})
            return True, data["admid"]
        return False, "Database error"

    def discharge(self, admid: str, by: str) -> bool:
        adm = db.find_one("admissions", {"admid": admid})
        if not adm or adm.get("status") != "admitted":
            return False
        import datetime
        admitted  = adm.get("admitted_on", today())
        days      = max(1, (datetime.date.today() - datetime.date.fromisoformat(admitted)).days)
        db.update("admissions", {"admid": admid},
                  {"status": "discharged", "discharged_on": today(), "total_days": days})
        ward = db.find_one("wards", {"wid": adm.get("wid","")})
        if ward:
            db.update("wards", {"wid": adm["wid"]},
                      {"occupied": max(0, int(ward.get("occupied",0)) - 1)})
        db.insert("audit_log", {"user": by, "action": "DISCHARGE", "module": "admissions",
                                "detail": f"Discharged {adm['patient_name']} after {days} days", "ts": now()})
        return True

    def get_all(self, status="all"):
        q = None if status == "all" else {"status": status}
        return db.find("admissions", q, sort="created_at")


class LabService:
    def order(self, data: dict, by: str) -> tuple:
        data["ltid"]       = gen_id("L")
        data["status"]     = "pending"
        data["created_at"] = now()
        if db.insert("lab_tests", data):
            return True, data["ltid"]
        return False, "Database error"

    def complete(self, ltid: str, result: str) -> bool:
        return db.update("lab_tests", {"ltid": ltid},
                         {"status": "completed", "result": result, "completed_on": now()})

    def get_all(self, status="all"):
        q = None if status == "all" else {"status": status}
        return db.find("lab_tests", q, sort="created_at")


class ReportService:
    def summary(self) -> dict:
        from database.connection import db as _db
        return {
            "patients_total":    _db.count("patients"),
            "patients_active":   _db.count("patients", {"status": "active"}),
            "doctors_active":    _db.count("doctors",  {"status": "active"}),
            "appointments_today":_db.count("appointments", {"date": today()}),
            "appointments_all":  _db.count("appointments"),
            "admitted_now":      _db.count("admissions",   {"status": "admitted"}),
            "pending_bills":     _db.count("billing",      {"status": "pending"}),
            "inventory_items":   _db.count("inventory"),
            "lab_pending":       _db.count("lab_tests",    {"status": "pending"}),
        }

    def financial(self) -> dict:
        bills     = db.find("billing")
        total_rev = sum(float(b.get("total",0))    for b in bills)
        collected = sum(float(b.get("paid",0))     for b in bills)
        return {
            "total_revenue":  total_rev,
            "collected":      collected,
            "outstanding":    total_rev - collected,
            "paid_bills":     sum(1 for b in bills if b.get("status") == "paid"),
            "pending_bills":  sum(1 for b in bills if b.get("status") == "pending"),
            "partial_bills":  sum(1 for b in bills if b.get("status") == "partial"),
            "total_bills":    len(bills),
        }

    def inventory_alerts(self) -> list:
        items = db.find("inventory")
        return [i for i in items if int(i.get("quantity",0)) <= int(i.get("reorder_level",10))]

    def audit_log(self, limit=50) -> list:
        return db.find("audit_log", sort="ts", limit=limit) if db.mongo else db.find("audit_log", limit=limit)


def seed():
    from database.connection import db as _db
    if not _db.find_one("users", {"username": "admin"}):
        _db.insert("users", {
            "username": "admin", "password": hash_pw("admin123"),
            "role": "admin", "full_name": "System Administrator",
            "email": "admin@medicore.com", "phone": "", "is_active": 1,
            "created_at": now()
        })
    if _db.count("doctors") == 0:
        docs = [
            ("Dr. Sarah Mitchell",  "Cardiology",    "MD FACC",    "+1-555-0101", 250.0, "Mon-Fri 9-5"),
            ("Dr. James Chen",      "Neurology",     "MD PhD",     "+1-555-0102", 270.0, "Mon-Thu 10-6"),
            ("Dr. Emily Rodriguez", "Pediatrics",    "MD FAAP",    "+1-555-0103", 180.0, "Tue-Sat 8-4"),
            ("Dr. Robert Kim",      "Orthopedics",   "MD FAAOS",   "+1-555-0104", 220.0, "Mon-Fri 8-3"),
            ("Dr. Priya Sharma",    "Oncology",      "MD DM",      "+1-555-0105", 300.0, "Mon-Wed-Fri"),
        ]
        for name, spec, qual, ph, fee, sched in docs:
            _db.insert("doctors", {
                "did": gen_id("D"), "full_name": name, "specialization": spec,
                "qualification": qual, "phone": ph, "email": "",
                "fee": fee, "schedule": sched, "status": "active", "created_at": now()
            })
    if _db.count("wards") == 0:
        wards = [
            ("General Ward A", "General",        20, "Ground", 150),
            ("ICU",            "Intensive Care", 8,  "1st",    800),
            ("Pediatric Ward", "Pediatrics",     15, "2nd",    200),
            ("Surgical Ward",  "Surgical",       12, "3rd",    400),
            ("Maternity Ward", "Maternity",      10, "2nd",    300),
        ]
        for name, wtype, beds, floor, rate in wards:
            _db.insert("wards", {
                "wid": gen_id("W"), "name": name, "ward_type": wtype,
                "total_beds": beds, "occupied": 0, "floor": floor,
                "charge_per_day": rate, "created_at": now()
            })
    if _db.count("inventory") == 0:
        meds = [
            ("Paracetamol 500mg",  "Medicine",  500, "tablets", 0.10, "PharmaPlus",  100, "2026-06-30"),
            ("Amoxicillin 250mg",  "Medicine",  200, "capsules",0.35, "MedDist",      50, "2026-03-31"),
            ("IV Saline 500ml",    "IV Fluids",  80, "bags",    3.00, "FluidMed",     20, "2026-12-31"),
            ("Surgical Gloves M",  "PPE",       300, "pairs",   0.50, "SafeGlove",    60, "2027-01-01"),
            ("Bandages (Roll)",    "Wound Care",150, "rolls",   1.25, "WoundCare Co.",30, "2028-01-01"),
            ("Morphine 10mg",      "Medicine",   45, "vials",  12.00, "PharmaPlus",   15, "2025-11-30"),
            ("Insulin 100IU/ml",   "Medicine",   30, "vials",  25.00, "DiabetaLab",   10, "2025-10-31"),
            ("N95 Respirator",     "PPE",        60, "pieces",  4.50, "SafeGlove",    20, "2027-06-30"),
        ]
        for name, cat, qty, unit, price, supp, rl, exp in meds:
            _db.insert("inventory", {
                "iid": gen_id("I"), "name": name, "category": cat,
                "quantity": qty, "unit": unit, "unit_price": price,
                "supplier": supp, "reorder_level": rl, "expiry": exp,
                "batch": gen_id("BATCH"), "location": "Pharmacy Store", "created_at": now()
            })
