import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import hashlib
import os
import json
import sqlite3
import datetime
import re
import uuid
from typing import Optional

try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure, DuplicateKeyError
    MONGO_AVAILABLE = True
except ImportError:
    MONGO_AVAILABLE = False

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.environ.get("HMS_DB_NAME", "hospital_management")
SQLITE_PATH = os.environ.get("HMS_SQLITE_PATH", "hms_local.db")

APP_TITLE = "MediCore Hospital Management System"
PRIMARY   = "#1a73e8"
SECONDARY = "#34a853"
DANGER    = "#ea4335"
WARNING   = "#fbbc04"
BG        = "#f8f9fa"
CARD_BG   = "#ffffff"
TEXT      = "#202124"
MUTED     = "#5f6368"
SIDEBAR   = "#1e2a3a"
SIDEBAR_T = "#ffffff"
SIDEBAR_H = "#2d3f55"

FONT_TITLE  = ("Segoe UI", 20, "bold")
FONT_HEAD   = ("Segoe UI", 13, "bold")
FONT_BODY   = ("Segoe UI", 11)
FONT_SMALL  = ("Segoe UI", 9)
FONT_BTN    = ("Segoe UI", 10, "bold")
FONT_LABEL  = ("Segoe UI", 10)

def hash_password(pw: str) -> str:
    salt = "HMS_SALT_2024"
    return hashlib.sha256((pw + salt).encode()).hexdigest()

def generate_id(prefix: str = "") -> str:
    return prefix + str(uuid.uuid4()).replace("-", "")[:12].upper()

def today_str() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d")

def now_str() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def validate_email(email: str) -> bool:
    return bool(re.match(r"[^@]+@[^@]+\.[^@]+", email))

def validate_phone(phone: str) -> bool:
    return bool(re.match(r"^\+?[\d\s\-]{7,15}$", phone))


class DatabaseManager:
    """Handles all database operations — tries MongoDB first, falls back to SQLite"""

    def __init__(self):
        self.using_mongo = False
        self.mongo_client = None
        self.db = None
        self.sqlite_conn = None
        self._connect()

    def _connect(self):
        if MONGO_AVAILABLE:
            try:
                self.mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
                self.mongo_client.admin.command("ping")
                self.db = self.mongo_client[DB_NAME]
                self.using_mongo = True
                self._setup_mongo_indexes()
                return
            except Exception:
                pass
        self._setup_sqlite()

    def _setup_mongo_indexes(self):
        self.db.users.create_index("username", unique=True)
        self.db.patients.create_index("patient_id", unique=True)
        self.db.patients.create_index("email")
        self.db.doctors.create_index("doctor_id", unique=True)
        self.db.appointments.create_index("appointment_id", unique=True)
        self.db.appointments.create_index([("patient_id", 1), ("date", 1)])
        self.db.billing.create_index("bill_id", unique=True)
        self.db.billing.create_index("patient_id")
        self.db.inventory.create_index("item_id", unique=True)
        self.db.wards.create_index("ward_id", unique=True)
        self.db.admissions.create_index("admission_id", unique=True)

    def _setup_sqlite(self):
        self.sqlite_conn = sqlite3.connect(SQLITE_PATH, check_same_thread=False)
        self.sqlite_conn.row_factory = sqlite3.Row
        cur = self.sqlite_conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL,
                full_name TEXT,
                email TEXT,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS patients (
                id TEXT PRIMARY KEY,
                patient_id TEXT UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                dob TEXT,
                gender TEXT,
                blood_group TEXT,
                phone TEXT,
                email TEXT,
                address TEXT,
                emergency_contact TEXT,
                medical_history TEXT,
                allergies TEXT,
                created_at TEXT,
                status TEXT DEFAULT 'active'
            );
            CREATE TABLE IF NOT EXISTS doctors (
                id TEXT PRIMARY KEY,
                doctor_id TEXT UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                specialization TEXT,
                qualification TEXT,
                phone TEXT,
                email TEXT,
                schedule TEXT,
                fee REAL DEFAULT 0,
                status TEXT DEFAULT 'active',
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS appointments (
                id TEXT PRIMARY KEY,
                appointment_id TEXT UNIQUE NOT NULL,
                patient_id TEXT,
                patient_name TEXT,
                doctor_id TEXT,
                doctor_name TEXT,
                date TEXT,
                time TEXT,
                reason TEXT,
                status TEXT DEFAULT 'scheduled',
                notes TEXT,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS billing (
                id TEXT PRIMARY KEY,
                bill_id TEXT UNIQUE NOT NULL,
                patient_id TEXT,
                patient_name TEXT,
                items TEXT,
                subtotal REAL,
                tax REAL,
                discount REAL,
                total REAL,
                paid REAL DEFAULT 0,
                status TEXT DEFAULT 'pending',
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS inventory (
                id TEXT PRIMARY KEY,
                item_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                category TEXT,
                quantity INTEGER DEFAULT 0,
                unit TEXT,
                unit_price REAL,
                supplier TEXT,
                reorder_level INTEGER DEFAULT 10,
                expiry_date TEXT,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS wards (
                id TEXT PRIMARY KEY,
                ward_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                ward_type TEXT,
                total_beds INTEGER,
                occupied_beds INTEGER DEFAULT 0,
                floor TEXT,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS admissions (
                id TEXT PRIMARY KEY,
                admission_id TEXT UNIQUE NOT NULL,
                patient_id TEXT,
                patient_name TEXT,
                doctor_id TEXT,
                doctor_name TEXT,
                ward_id TEXT,
                ward_name TEXT,
                bed_number TEXT,
                admission_date TEXT,
                discharge_date TEXT,
                diagnosis TEXT,
                status TEXT DEFAULT 'admitted',
                created_at TEXT
            );
        """)
        self.sqlite_conn.commit()

    def _mongo_to_dict(self, doc):
        if doc is None:
            return None
        d = dict(doc)
        if "_id" in d:
            d["_id"] = str(d["_id"])
        return d

    def insert(self, collection: str, data: dict) -> bool:
        try:
            if self.using_mongo:
                self.db[collection].insert_one(data)
                return True
            else:
                return self._sqlite_insert(collection, data)
        except Exception as e:
            print(f"Insert error: {e}")
            return False

    def find_all(self, collection: str, query: dict = None, sort_by: str = None) -> list:
        try:
            if self.using_mongo:
                cursor = self.db[collection].find(query or {})
                if sort_by:
                    cursor = cursor.sort(sort_by, -1)
                return [self._mongo_to_dict(d) for d in cursor]
            else:
                return self._sqlite_find_all(collection, query, sort_by)
        except Exception as e:
            print(f"Find error: {e}")
            return []

    def find_one(self, collection: str, query: dict) -> Optional[dict]:
        try:
            if self.using_mongo:
                return self._mongo_to_dict(self.db[collection].find_one(query))
            else:
                results = self._sqlite_find_all(collection, query)
                return results[0] if results else None
        except Exception as e:
            print(f"Find one error: {e}")
            return None

    def update(self, collection: str, query: dict, data: dict) -> bool:
        try:
            if self.using_mongo:
                self.db[collection].update_one(query, {"$set": data})
                return True
            else:
                return self._sqlite_update(collection, query, data)
        except Exception as e:
            print(f"Update error: {e}")
            return False

    def delete(self, collection: str, query: dict) -> bool:
        try:
            if self.using_mongo:
                self.db[collection].delete_one(query)
                return True
            else:
                return self._sqlite_delete(collection, query)
        except Exception as e:
            print(f"Delete error: {e}")
            return False

    def count(self, collection: str, query: dict = None) -> int:
        try:
            if self.using_mongo:
                return self.db[collection].count_documents(query or {})
            else:
                results = self._sqlite_find_all(collection, query)
                return len(results)
        except Exception:
            return 0

    def _sqlite_insert(self, table: str, data: dict) -> bool:
        cur = self.sqlite_conn.cursor()
        data["id"] = data.get("id", generate_id())
        cols = ", ".join(data.keys())
        placeholders = ", ".join(["?" for _ in data])
        vals = []
        for v in data.values():
            if isinstance(v, (dict, list)):
                vals.append(json.dumps(v))
            else:
                vals.append(v)
        cur.execute(f"INSERT INTO {table} ({cols}) VALUES ({placeholders})", vals)
        self.sqlite_conn.commit()
        return True

    def _sqlite_find_all(self, table: str, query: dict = None, sort_by: str = None) -> list:
        cur = self.sqlite_conn.cursor()
        where, vals = self._build_where(query)
        order = f" ORDER BY {sort_by} DESC" if sort_by else " ORDER BY rowid DESC"
        cur.execute(f"SELECT * FROM {table}{where}{order}", vals)
        rows = cur.fetchall()
        result = []
        for row in rows:
            d = dict(row)
            for k, v in d.items():
                if isinstance(v, str) and v.startswith(("{", "[")):
                    try:
                        d[k] = json.loads(v)
                    except Exception:
                        pass
            result.append(d)
        return result

    def _sqlite_update(self, table: str, query: dict, data: dict) -> bool:
        cur = self.sqlite_conn.cursor()
        set_parts = []
        set_vals = []
        for k, v in data.items():
            set_parts.append(f"{k} = ?")
            if isinstance(v, (dict, list)):
                set_vals.append(json.dumps(v))
            else:
                set_vals.append(v)
        where, where_vals = self._build_where(query)
        cur.execute(f"UPDATE {table} SET {', '.join(set_parts)}{where}", set_vals + where_vals)
        self.sqlite_conn.commit()
        return True

    def _sqlite_delete(self, table: str, query: dict) -> bool:
        cur = self.sqlite_conn.cursor()
        where, vals = self._build_where(query)
        cur.execute(f"DELETE FROM {table}{where}", vals)
        self.sqlite_conn.commit()
        return True

    def _build_where(self, query: dict) -> tuple:
        if not query:
            return "", []
        parts = []
        vals = []
        for k, v in query.items():
            parts.append(f"{k} = ?")
            vals.append(v)
        return " WHERE " + " AND ".join(parts), vals

    def close(self):
        if self.mongo_client:
            self.mongo_client.close()
        if self.sqlite_conn:
            self.sqlite_conn.close()


db = DatabaseManager()


def seed_admin():
    existing = db.find_one("users", {"username": "admin"})
    if not existing:
        db.insert("users", {
            "username": "admin",
            "password": hash_password("admin123"),
            "role": "admin",
            "full_name": "System Administrator",
            "email": "admin@hospital.com",
            "created_at": now_str()
        })

def seed_sample_data():
    if db.count("doctors") == 0:
        doctors = [
            {"doctor_id": "DOC001", "full_name": "Dr. Sarah Mitchell", "specialization": "Cardiology",
             "qualification": "MD, FACC", "phone": "+1-555-0101", "email": "s.mitchell@hospital.com",
             "fee": 200.0, "status": "active", "schedule": "Mon-Fri 9AM-5PM", "created_at": now_str()},
            {"doctor_id": "DOC002", "full_name": "Dr. James Chen", "specialization": "Neurology",
             "qualification": "MD, PhD", "phone": "+1-555-0102", "email": "j.chen@hospital.com",
             "fee": 220.0, "status": "active", "schedule": "Mon-Thu 10AM-6PM", "created_at": now_str()},
            {"doctor_id": "DOC003", "full_name": "Dr. Emily Rodriguez", "specialization": "Pediatrics",
             "qualification": "MD, FAAP", "phone": "+1-555-0103", "email": "e.rodriguez@hospital.com",
             "fee": 150.0, "status": "active", "schedule": "Tue-Sat 8AM-4PM", "created_at": now_str()},
            {"doctor_id": "DOC004", "full_name": "Dr. Robert Kim", "specialization": "Orthopedics",
             "qualification": "MD, FAAOS", "phone": "+1-555-0104", "email": "r.kim@hospital.com",
             "fee": 180.0, "status": "active", "schedule": "Mon-Fri 8AM-3PM", "created_at": now_str()},
        ]
        for d in doctors:
            db.insert("doctors", d)

    if db.count("wards") == 0:
        wards = [
            {"ward_id": "W001", "name": "General Ward A", "ward_type": "General", "total_beds": 20,
             "occupied_beds": 0, "floor": "Ground", "created_at": now_str()},
            {"ward_id": "W002", "name": "ICU", "ward_type": "Intensive Care", "total_beds": 10,
             "occupied_beds": 0, "floor": "1st", "created_at": now_str()},
            {"ward_id": "W003", "name": "Pediatric Ward", "ward_type": "Pediatrics", "total_beds": 15,
             "occupied_beds": 0, "floor": "2nd", "created_at": now_str()},
            {"ward_id": "W004", "name": "Surgical Ward", "ward_type": "Surgical", "total_beds": 12,
             "occupied_beds": 0, "floor": "3rd", "created_at": now_str()},
        ]
        for w in wards:
            db.insert("wards", w)

    if db.count("inventory") == 0:
        items = [
            {"item_id": "INV001", "name": "Paracetamol 500mg", "category": "Medicine", "quantity": 500,
             "unit": "tablets", "unit_price": 0.10, "supplier": "PharmaCo", "reorder_level": 100,
             "expiry_date": "2026-06-30", "created_at": now_str()},
            {"item_id": "INV002", "name": "Surgical Gloves (M)", "category": "PPE", "quantity": 200,
             "unit": "pairs", "unit_price": 0.50, "supplier": "MedSupply", "reorder_level": 50,
             "expiry_date": "2027-12-31", "created_at": now_str()},
            {"item_id": "INV003", "name": "IV Saline 500ml", "category": "IV Fluids", "quantity": 80,
             "unit": "bags", "unit_price": 3.00, "supplier": "FluidMed", "reorder_level": 20,
             "expiry_date": "2025-12-31", "created_at": now_str()},
            {"item_id": "INV004", "name": "Bandages (Roll)", "category": "Wound Care", "quantity": 150,
             "unit": "rolls", "unit_price": 1.25, "supplier": "MedSupply", "reorder_level": 30,
             "expiry_date": "2028-01-01", "created_at": now_str()},
        ]
        for item in items:
            db.insert("inventory", item)


class StyledButton(tk.Button):
    def __init__(self, parent, text, command=None, style="primary", width=None, **kwargs):
        colors = {
            "primary":   (PRIMARY,   "#ffffff"),
            "success":   (SECONDARY, "#ffffff"),
            "danger":    (DANGER,    "#ffffff"),
            "warning":   (WARNING,   "#202124"),
            "secondary": ("#e8eaed", "#202124"),
            "ghost":     (CARD_BG,   PRIMARY),
        }
        bg, fg = colors.get(style, colors["primary"])
        super().__init__(parent, text=text, command=command,
                         bg=bg, fg=fg, font=FONT_BTN,
                         relief="flat", cursor="hand2",
                         padx=14, pady=7, bd=0,
                         activebackground=bg, activeforeground=fg,
                         **kwargs)
        if width:
            self.config(width=width)
        self.bind("<Enter>", lambda e: self.config(bg=self._darken(bg)))
        self.bind("<Leave>", lambda e: self.config(bg=bg))

    def _darken(self, hex_color):
        try:
            r = int(hex_color[1:3], 16)
            g = int(hex_color[3:5], 16)
            b = int(hex_color[5:7], 16)
            return f"#{max(r-20,0):02x}{max(g-20,0):02x}{max(b-20,0):02x}"
        except Exception:
            return hex_color


class LabeledEntry(tk.Frame):
    def __init__(self, parent, label, placeholder="", secret=False, width=25, **kwargs):
        super().__init__(parent, bg=CARD_BG, **kwargs)
        tk.Label(self, text=label, font=FONT_LABEL, bg=CARD_BG, fg=MUTED).pack(anchor="w")
        show = "*" if secret else ""
        self.var = tk.StringVar()
        self.entry = tk.Entry(self, textvariable=self.var, font=FONT_BODY,
                              relief="solid", bd=1, width=width, show=show,
                              bg="#f1f3f4", fg=TEXT, insertbackground=TEXT)
        self.entry.pack(fill="x", ipady=5)
        if placeholder:
            self.entry.insert(0, placeholder)
            self.entry.config(fg=MUTED)
            self.entry.bind("<FocusIn>", lambda e: self._clear_ph(placeholder))
            self.entry.bind("<FocusOut>", lambda e: self._restore_ph(placeholder))

    def _clear_ph(self, ph):
        if self.var.get() == ph:
            self.entry.delete(0, "end")
            self.entry.config(fg=TEXT)

    def _restore_ph(self, ph):
        if not self.var.get():
            self.entry.insert(0, ph)
            self.entry.config(fg=MUTED)

    def get(self) -> str:
        return self.var.get()

    def set(self, value: str):
        self.var.set(value)


class LabeledCombo(tk.Frame):
    def __init__(self, parent, label, values, width=23, **kwargs):
        super().__init__(parent, bg=CARD_BG, **kwargs)
        tk.Label(self, text=label, font=FONT_LABEL, bg=CARD_BG, fg=MUTED).pack(anchor="w")
        self.var = tk.StringVar()
        self.combo = ttk.Combobox(self, textvariable=self.var, values=values,
                                  font=FONT_BODY, width=width, state="readonly")
        self.combo.pack(fill="x")
        if values:
            self.combo.current(0)

    def get(self) -> str:
        return self.var.get()

    def set(self, value: str):
        self.var.set(value)


class DataTable(tk.Frame):
    def __init__(self, parent, columns: list, **kwargs):
        super().__init__(parent, **kwargs)
        self.columns = columns
        style = ttk.Style()
        style.configure("HMS.Treeview", rowheight=28, font=FONT_BODY, background=CARD_BG,
                         fieldbackground=CARD_BG, foreground=TEXT)
        style.configure("HMS.Treeview.Heading", font=FONT_BTN, background="#e8eaed", foreground=TEXT,
                         relief="flat")
        style.map("HMS.Treeview", background=[("selected", PRIMARY)], foreground=[("selected", "#fff")])
        self.tree = ttk.Treeview(self, columns=columns, show="headings", style="HMS.Treeview")
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=max(100, len(col) * 10), anchor="w")
        scroll_y = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        scroll_x = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        scroll_y.pack(side="right", fill="y")
        scroll_x.pack(side="bottom", fill="x")
        self.tree.pack(fill="both", expand=True)

    def clear(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    def insert_row(self, values: list, tag=""):
        self.tree.insert("", "end", values=values, tags=(tag,) if tag else ())

    def color_tag(self, tag: str, bg: str, fg: str = TEXT):
        self.tree.tag_configure(tag, background=bg, foreground=fg)

    def selected_values(self) -> Optional[list]:
        sel = self.tree.selection()
        if not sel:
            return None
        return list(self.tree.item(sel[0], "values"))


class StatCard(tk.Frame):
    def __init__(self, parent, title: str, value: str, color: str = PRIMARY, icon: str = "●", **kwargs):
        super().__init__(parent, bg=CARD_BG, relief="flat", bd=0, **kwargs)
        self.config(padx=20, pady=15)
        tk.Label(self, text=icon, font=("Segoe UI", 22), bg=CARD_BG, fg=color).pack(anchor="w")
        self.value_lbl = tk.Label(self, text=value, font=("Segoe UI", 26, "bold"), bg=CARD_BG, fg=TEXT)
        self.value_lbl.pack(anchor="w")
        tk.Label(self, text=title, font=FONT_SMALL, bg=CARD_BG, fg=MUTED).pack(anchor="w")
        tk.Frame(self, height=3, bg=color).pack(fill="x", side="bottom")

    def update_value(self, value: str):
        self.value_lbl.config(text=value)


class LoginWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"{APP_TITLE} — Login")
        self.root.geometry("440x520")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)
        self.root.eval("tk::PlaceWindow . center")
        self._build()
        self.root.mainloop()

    def _build(self):
        tk.Frame(self.root, bg=PRIMARY, height=8).pack(fill="x")
        container = tk.Frame(self.root, bg=CARD_BG, padx=50, pady=40)
        container.pack(fill="both", expand=True, padx=30, pady=30)
        tk.Label(container, text="🏥", font=("Segoe UI", 40), bg=CARD_BG, fg=PRIMARY).pack()
        tk.Label(container, text="MediCore HMS", font=FONT_TITLE, bg=CARD_BG, fg=TEXT).pack()
        tk.Label(container, text="Hospital Management System", font=FONT_SMALL, bg=CARD_BG, fg=MUTED).pack(pady=(0, 25))
        self.username_field = LabeledEntry(container, "Username", width=28)
        self.username_field.pack(fill="x", pady=5)
        self.password_field = LabeledEntry(container, "Password", secret=True, width=28)
        self.password_field.pack(fill="x", pady=5)
        self.role_field = LabeledCombo(container, "Role", ["Admin", "Doctor", "Receptionist", "Pharmacist"], width=26)
        self.role_field.pack(fill="x", pady=5)
        tk.Frame(container, bg=CARD_BG, height=10).pack()
        StyledButton(container, "LOGIN", command=self._login, style="primary", width=28).pack(fill="x", pady=5)
        db_label = "MongoDB" if db.using_mongo else "SQLite (Local)"
        tk.Label(container, text=f"Connected: {db_label}", font=FONT_SMALL, bg=CARD_BG, fg=MUTED).pack(pady=10)
        tk.Label(container, text="Default credentials: admin / admin123", font=FONT_SMALL, bg=CARD_BG, fg=MUTED).pack()
        self.root.bind("<Return>", lambda e: self._login())

    def _login(self):
        username = self.username_field.get().strip()
        password = self.password_field.get().strip()
        if not username or not password:
            messagebox.showerror("Login Error", "Please enter username and password")
            return
        user = db.find_one("users", {"username": username, "password": hash_password(password)})
        if not user:
            messagebox.showerror("Login Failed", "Invalid credentials. Please try again.")
            return
        self.root.destroy()
        MainApplication(user)


class MainApplication:
    def __init__(self, current_user: dict):
        self.current_user = current_user
        self.root = tk.Tk()
        self.root.title(f"{APP_TITLE} — {current_user.get('full_name', 'User')}")
        self.root.geometry("1280x780")
        self.root.configure(bg=BG)
        self.root.state("zoomed")
        self.active_module = None
        self.content_frame = None
        self._build_layout()
        self._show_dashboard()
        self.root.mainloop()

    def _build_layout(self):
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        right = tk.Frame(self.root, bg=BG)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)
        self._build_topbar(right)
        self.content_frame = tk.Frame(right, bg=BG)
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)

    def _build_sidebar(self):
        sidebar = tk.Frame(self.root, bg=SIDEBAR, width=220)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        logo_frame = tk.Frame(sidebar, bg=SIDEBAR, pady=20)
        logo_frame.pack(fill="x")
        tk.Label(logo_frame, text="🏥 MediCore", font=("Segoe UI", 14, "bold"),
                 bg=SIDEBAR, fg=SIDEBAR_T).pack()
        tk.Label(logo_frame, text="HMS v2.0", font=FONT_SMALL, bg=SIDEBAR, fg="#8899aa").pack()
        ttk.Separator(sidebar, orient="horizontal").pack(fill="x", padx=10)
        nav_items = [
            ("🏠", "Dashboard",    self._show_dashboard),
            ("👥", "Patients",     self._show_patients),
            ("🩺", "Doctors",      self._show_doctors),
            ("📅", "Appointments", self._show_appointments),
            ("🏥", "Admissions",   self._show_admissions),
            ("💊", "Inventory",    self._show_inventory),
            ("💰", "Billing",      self._show_billing),
            ("🏢", "Wards",        self._show_wards),
            ("👤", "Users",        self._show_users),
            ("📊", "Reports",      self._show_reports),
        ]
        self.nav_buttons = {}
        for icon, label, cmd in nav_items:
            btn = tk.Button(sidebar, text=f"  {icon}  {label}", font=FONT_BODY,
                            bg=SIDEBAR, fg=SIDEBAR_T, relief="flat", anchor="w",
                            padx=10, pady=10, cursor="hand2", bd=0,
                            activebackground=SIDEBAR_H, activeforeground=SIDEBAR_T,
                            command=lambda c=cmd, l=label: self._nav_click(c, l))
            btn.pack(fill="x")
            self.nav_buttons[label] = btn
        ttk.Separator(sidebar, orient="horizontal").pack(fill="x", padx=10, side="bottom", pady=5)
        tk.Label(sidebar, text=f"👤 {self.current_user.get('full_name', 'User')[:18]}",
                 font=FONT_SMALL, bg=SIDEBAR, fg="#8899aa").pack(side="bottom", pady=2)
        StyledButton(sidebar, "⏻  Logout", command=self._logout,
                     style="danger").pack(side="bottom", fill="x", padx=10, pady=5)

    def _build_topbar(self, parent):
        bar = tk.Frame(parent, bg=CARD_BG, pady=12, padx=20)
        bar.grid(row=0, column=0, sticky="ew")
        self.page_title_var = tk.StringVar(value="Dashboard")
        tk.Label(bar, textvariable=self.page_title_var, font=FONT_HEAD,
                 bg=CARD_BG, fg=TEXT).pack(side="left")
        tk.Label(bar, text=f"Role: {self.current_user.get('role', '').title()}  |  {today_str()}",
                 font=FONT_SMALL, bg=CARD_BG, fg=MUTED).pack(side="right")

    def _nav_click(self, cmd, label):
        for l, b in self.nav_buttons.items():
            b.config(bg=SIDEBAR if l != label else SIDEBAR_H)
        self.page_title_var.set(label)
        cmd()

    def _clear_content(self):
        for w in self.content_frame.winfo_children():
            w.destroy()

    def _logout(self):
        if messagebox.askyesno("Logout", "Are you sure you want to logout?"):
            db.close()
            self.root.destroy()
            LoginWindow()

    def _show_dashboard(self):
        self._clear_content()
        frame = tk.Frame(self.content_frame, bg=BG)
        frame.pack(fill="both", expand=True)
        tk.Label(frame, text="Welcome back, " + self.current_user.get("full_name", "User"),
                 font=FONT_HEAD, bg=BG, fg=TEXT).pack(anchor="w", pady=(0, 15))
        cards_frame = tk.Frame(frame, bg=BG)
        cards_frame.pack(fill="x")
        stats = [
            ("Total Patients",     db.count("patients"),                       PRIMARY,  "👥"),
            ("Appointments Today", db.count("appointments", {"date": today_str()}), SECONDARY, "📅"),
            ("Active Admissions",  db.count("admissions", {"status": "admitted"}), WARNING,   "🏥"),
            ("Doctors on Staff",   db.count("doctors",     {"status": "active"}),  "#9c27b0", "🩺"),
            ("Pending Bills",      db.count("billing",     {"status": "pending"}), DANGER,    "💰"),
            ("Inventory Items",    db.count("inventory"),                          "#00bcd4", "💊"),
        ]
        for i, (title, val, color, icon) in enumerate(stats):
            card = StatCard(cards_frame, title, str(val), color, icon)
            card.grid(row=0, column=i, padx=8, pady=5, sticky="nsew")
            cards_frame.grid_columnconfigure(i, weight=1)
        mid = tk.Frame(frame, bg=BG)
        mid.pack(fill="both", expand=True, pady=15)
        mid.grid_columnconfigure(0, weight=1)
        mid.grid_columnconfigure(1, weight=1)
        recent_appt = tk.LabelFrame(mid, text=" Recent Appointments ", font=FONT_LABEL,
                                    bg=CARD_BG, fg=MUTED, bd=1, relief="solid")
        recent_appt.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=5)
        tbl = DataTable(recent_appt, ["Patient", "Doctor", "Date", "Time", "Status"])
        tbl.pack(fill="both", expand=True, padx=10, pady=10) 
        tbl.color_tag("scheduled", "#e8f5e9", SECONDARY)
        tbl.color_tag("completed", "#e3f2fd", PRIMARY)
        tbl.color_tag("cancelled", "#ffebee", DANGER)
        appts = db.find_all("appointments", sort_by="created_at")[:8]
        for a in appts:
            tbl.insert_row([a.get("patient_name", ""), a.get("doctor_name", ""),
                            a.get("date", ""), a.get("time", ""),
                            a.get("status", "").title()], tag=a.get("status", ""))
        low_inv = tk.LabelFrame(mid, text=" Low Inventory Alert ", font=FONT_LABEL,
                                bg=CARD_BG, fg=MUTED, bd=1, relief="solid")
        low_inv.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=5)
        inv_tbl = DataTable(low_inv, ["Item", "Qty", "Reorder Level", "Status"])
        inv_tbl.pack(fill="both", expand=True, padx=10, pady=10)
        inv_tbl.color_tag("critical", "#ffebee", DANGER)
        inv_tbl.color_tag("low", "#fff8e1", "#e65100")
        all_inv = db.find_all("inventory")
        for item in all_inv:
            qty = int(item.get("quantity", 0))
            rl  = int(item.get("reorder_level", 10))
            if qty <= rl:
                tag    = "critical" if qty == 0 else "low"
                status = "OUT OF STOCK" if qty == 0 else "LOW STOCK"
                inv_tbl.insert_row([item.get("name", ""), qty, rl, status], tag=tag)

    def _show_patients(self):
        self._clear_content()
        PatientModule(self.content_frame)

    def _show_doctors(self):
        self._clear_content()
        DoctorModule(self.content_frame)

    def _show_appointments(self):
        self._clear_content()
        AppointmentModule(self.content_frame)

    def _show_admissions(self):
        self._clear_content()
        AdmissionModule(self.content_frame)

    def _show_inventory(self):
        self._clear_content()
        InventoryModule(self.content_frame)

    def _show_billing(self):
        self._clear_content()
        BillingModule(self.content_frame)

    def _show_wards(self):
        self._clear_content()
        WardModule(self.content_frame)

    def _show_users(self):
        self._clear_content()
        if self.current_user.get("role") != "admin":
            tk.Label(self.content_frame, text="⛔ Access Denied — Admin only",
                     font=FONT_HEAD, bg=BG, fg=DANGER).pack(pady=50)
            return
        UserModule(self.content_frame)

    def _show_reports(self):
        self._clear_content()
        ReportsModule(self.content_frame)


class BaseModule(tk.Frame):
    def __init__(self, parent, title: str, **kwargs):
        super().__init__(parent, bg=BG, **kwargs)
        self.pack(fill="both", expand=True)
        self._build_toolbar(title)

    def _build_toolbar(self, title: str):
        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x", pady=(0, 10))
        tk.Label(bar, text=title, font=FONT_HEAD, bg=BG, fg=TEXT).pack(side="left")
        self.toolbar_right = tk.Frame(bar, bg=BG)
        self.toolbar_right.pack(side="right")

    def _add_toolbar_btn(self, text: str, cmd, style="primary"):
        StyledButton(self.toolbar_right, text, command=cmd, style=style).pack(side="left", padx=3)

    def _search_bar(self, parent, var: tk.StringVar, placeholder="Search...", cmd=None):
        frame = tk.Frame(parent, bg=CARD_BG, relief="solid", bd=1)
        frame.pack(side="left", padx=(0, 8))
        tk.Label(frame, text="🔍", font=FONT_BODY, bg=CARD_BG, fg=MUTED).pack(side="left", padx=5)
        entry = tk.Entry(frame, textvariable=var, font=FONT_BODY, relief="flat",
                         bg=CARD_BG, fg=TEXT, width=22)
        entry.pack(side="left", ipady=4)
        entry.insert(0, placeholder)
        entry.config(fg=MUTED)
        entry.bind("<FocusIn>", lambda e: entry.delete(0, "end") or entry.config(fg=TEXT) if entry.get() == placeholder else None)
        if cmd:
            entry.bind("<KeyRelease>", lambda e: cmd())
        return entry


def make_form_dialog(parent, title: str, fields: list) -> Optional[dict]:
    """Shows a modal dialog form and returns entered values or None if cancelled"""
    dialog = tk.Toplevel(parent)
    dialog.title(title)
    dialog.resizable(False, False)
    dialog.configure(bg=CARD_BG)
    dialog.grab_set()
    tk.Label(dialog, text=title, font=FONT_HEAD, bg=CARD_BG, fg=TEXT, pady=10).pack()
    ttk.Separator(dialog, orient="horizontal").pack(fill="x")
    form_frame = tk.Frame(dialog, bg=CARD_BG, padx=30, pady=20)
    form_frame.pack()
    widgets = {}
    row_frame = None
    for i, field in enumerate(fields):
        if i % 2 == 0:
            row_frame = tk.Frame(form_frame, bg=CARD_BG)
            row_frame.pack(fill="x", pady=4)
        name  = field.get("name")
        label = field.get("label", name)
        ftype = field.get("type", "entry")
        val   = field.get("default", "")
        cell  = tk.Frame(row_frame, bg=CARD_BG, padx=8)
        cell.pack(side="left", fill="x", expand=True)
        tk.Label(cell, text=label, font=FONT_LABEL, bg=CARD_BG, fg=MUTED).pack(anchor="w")
        if ftype == "combo":
            var = tk.StringVar(value=val)
            w = ttk.Combobox(cell, textvariable=var, values=field.get("values", []),
                             font=FONT_BODY, width=22, state="readonly")
            w.pack(fill="x", ipady=3)
            if val:
                var.set(val)
            elif field.get("values"):
                w.current(0)
            widgets[name] = var
        elif ftype == "text":
            var = tk.StringVar(value=val)
            w = tk.Text(cell, font=FONT_BODY, width=24, height=3,
                        relief="solid", bd=1, bg="#f1f3f4")
            if val:
                w.insert("1.0", val)
            w.pack(fill="x")
            widgets[name] = w
        else:
            secret = field.get("secret", False)
            var = tk.StringVar(value=val)
            w = tk.Entry(cell, textvariable=var, font=FONT_BODY, width=25,
                         relief="solid", bd=1, bg="#f1f3f4", fg=TEXT,
                         show="*" if secret else "")
            w.pack(fill="x", ipady=5)
            widgets[name] = var

    result = {"submitted": False, "data": {}}

    def on_submit():
        data = {}
        for name, widget in widgets.items():
            if isinstance(widget, tk.Text):
                data[name] = widget.get("1.0", "end-1c").strip()
            else:
                data[name] = widget.get().strip()
        result["submitted"] = True
        result["data"] = data
        dialog.destroy()

    ttk.Separator(dialog, orient="horizontal").pack(fill="x")
    btn_frame = tk.Frame(dialog, bg=CARD_BG, padx=20, pady=15)
    btn_frame.pack()
    StyledButton(btn_frame, "Cancel", command=dialog.destroy, style="secondary").pack(side="left", padx=5)
    StyledButton(btn_frame, "Save",   command=on_submit,     style="primary").pack(side="left", padx=5)
    dialog.wait_window()
    if result["submitted"]:
        return result["data"]
    return None


class PatientModule(BaseModule):
    def __init__(self, parent):
        super().__init__(parent, "Patient Management")
        self._add_toolbar_btn("➕ New Patient", self._add_patient)
        self._add_toolbar_btn("✏️ Edit", self._edit_patient, "secondary")
        self._add_toolbar_btn("🗑 Delete", self._delete_patient, "danger")
        self._add_toolbar_btn("🔄 Refresh", self._load, "ghost")
        self.search_var = tk.StringVar()
        self._search_bar(self.toolbar_right, self.search_var, "Search patients...", self._load)
        self.table = DataTable(self, ["Patient ID", "Full Name", "DOB", "Gender", "Blood Group",
                                      "Phone", "Email", "Status"])
        self.table.pack(fill="both", expand=True)
        self._load()

    def _load(self):
        self.table.clear()
        patients = db.find_all("patients", sort_by="created_at")
        q = self.search_var.get().strip().lower()
        for p in patients:
            name = p.get("full_name", "")
            pid  = p.get("patient_id", "")
            if q and q not in name.lower() and q not in pid.lower():
                continue
            self.table.insert_row([
                p.get("patient_id", ""), p.get("full_name", ""),
                p.get("dob", ""), p.get("gender", ""), p.get("blood_group", ""),
                p.get("phone", ""), p.get("email", ""), p.get("status", "").title()
            ], tag=p.get("status", "active"))
        self.table.color_tag("active",   CARD_BG, TEXT)
        self.table.color_tag("inactive", "#f5f5f5", MUTED)

    def _form_fields(self, existing=None):
        e = existing or {}
        return [
            {"name": "full_name",         "label": "Full Name *",          "default": e.get("full_name", "")},
            {"name": "dob",               "label": "Date of Birth",         "default": e.get("dob", "")},
            {"name": "gender",            "label": "Gender",     "type": "combo",
             "values": ["Male", "Female", "Other"],              "default": e.get("gender", "Male")},
            {"name": "blood_group",       "label": "Blood Group", "type": "combo",
             "values": ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"],
             "default": e.get("blood_group", "A+")},
            {"name": "phone",             "label": "Phone *",              "default": e.get("phone", "")},
            {"name": "email",             "label": "Email",                "default": e.get("email", "")},
            {"name": "address",           "label": "Address",              "default": e.get("address", "")},
            {"name": "emergency_contact", "label": "Emergency Contact",    "default": e.get("emergency_contact", "")},
            {"name": "allergies",         "label": "Allergies",            "default": e.get("allergies", "")},
            {"name": "medical_history",   "label": "Medical History", "type": "text",
             "default": e.get("medical_history", "")},
            {"name": "status", "label": "Status", "type": "combo",
             "values": ["active", "inactive"], "default": e.get("status", "active")},
        ]

    def _add_patient(self):
        data = make_form_dialog(self, "Add New Patient", self._form_fields())
        if not data:
            return
        if not data.get("full_name"):
            messagebox.showerror("Validation", "Full name is required")
            return
        data["patient_id"] = generate_id("PAT")
        data["created_at"] = now_str()
        if db.insert("patients", data):
            messagebox.showinfo("Success", f"Patient added with ID: {data['patient_id']}")
            self._load()

    def _edit_patient(self):
        vals = self.table.selected_values()
        if not vals:
            messagebox.showwarning("Select", "Please select a patient to edit")
            return
        patient = db.find_one("patients", {"patient_id": vals[0]})
        if not patient:
            return
        data = make_form_dialog(self, "Edit Patient", self._form_fields(patient))
        if not data:
            return
        db.update("patients", {"patient_id": vals[0]}, data)
        messagebox.showinfo("Success", "Patient updated successfully")
        self._load()

    def _delete_patient(self):
        vals = self.table.selected_values()
        if not vals:
            messagebox.showwarning("Select", "Please select a patient to delete")
            return
        if messagebox.askyesno("Confirm Delete", f"Delete patient {vals[1]}?"):
            db.update("patients", {"patient_id": vals[0]}, {"status": "inactive"})
            messagebox.showinfo("Success", "Patient marked as inactive")
            self._load()


class DoctorModule(BaseModule):
    def __init__(self, parent):
        super().__init__(parent, "Doctor Management")
        self._add_toolbar_btn("➕ Add Doctor", self._add_doctor)
        self._add_toolbar_btn("✏️ Edit", self._edit_doctor, "secondary")
        self._add_toolbar_btn("🔄 Refresh", self._load, "ghost")
        self.table = DataTable(self, ["Doctor ID", "Full Name", "Specialization",
                                      "Qualification", "Phone", "Email", "Fee", "Status"])
        self.table.pack(fill="both", expand=True)
        self._load()

    def _load(self):
        self.table.clear()
        for d in db.find_all("doctors", sort_by="created_at"):
            self.table.insert_row([
                d.get("doctor_id", ""), d.get("full_name", ""), d.get("specialization", ""),
                d.get("qualification", ""), d.get("phone", ""), d.get("email", ""),
                f"${d.get('fee', 0):.2f}", d.get("status", "").title()
            ])

    def _fields(self, e=None):
        e = e or {}
        return [
            {"name": "full_name",       "label": "Full Name *",       "default": e.get("full_name", "")},
            {"name": "specialization",  "label": "Specialization *",  "default": e.get("specialization", "")},
            {"name": "qualification",   "label": "Qualification",     "default": e.get("qualification", "")},
            {"name": "phone",           "label": "Phone",             "default": e.get("phone", "")},
            {"name": "email",           "label": "Email",             "default": e.get("email", "")},
            {"name": "fee",             "label": "Consultation Fee",  "default": str(e.get("fee", ""))},
            {"name": "schedule",        "label": "Schedule",          "default": e.get("schedule", "")},
            {"name": "status",          "label": "Status", "type": "combo",
             "values": ["active", "on_leave", "inactive"],            "default": e.get("status", "active")},
        ]

    def _add_doctor(self):
        data = make_form_dialog(self, "Add Doctor", self._fields())
        if not data:
            return
        try:
            data["fee"] = float(data.get("fee", 0) or 0)
        except ValueError:
            data["fee"] = 0.0
        data["doctor_id"] = generate_id("DOC")
        data["created_at"] = now_str()
        db.insert("doctors", data)
        messagebox.showinfo("Success", "Doctor added successfully")
        self._load()

    def _edit_doctor(self):
        vals = self.table.selected_values()
        if not vals:
            messagebox.showwarning("Select", "Please select a doctor")
            return
        doc = db.find_one("doctors", {"doctor_id": vals[0]})
        if not doc:
            return
        data = make_form_dialog(self, "Edit Doctor", self._fields(doc))
        if not data:
            return
        try:
            data["fee"] = float(data.get("fee", 0) or 0)
        except ValueError:
            data["fee"] = 0.0
        db.update("doctors", {"doctor_id": vals[0]}, data)
        messagebox.showinfo("Success", "Doctor updated")
        self._load()


class AppointmentModule(BaseModule):
    def __init__(self, parent):
        super().__init__(parent, "Appointment Management")
        self._add_toolbar_btn("➕ Book Appointment", self._add_appointment)
        self._add_toolbar_btn("✅ Mark Complete", self._complete, "success")
        self._add_toolbar_btn("❌ Cancel", self._cancel, "danger")
        self._add_toolbar_btn("🔄 Refresh", self._load, "ghost")
        filter_frame = tk.Frame(self.toolbar_right, bg=BG)
        filter_frame.pack(side="left", padx=5)
        tk.Label(filter_frame, text="Filter:", font=FONT_SMALL, bg=BG, fg=MUTED).pack(side="left")
        self.filter_var = tk.StringVar(value="All")
        ttk.Combobox(filter_frame, textvariable=self.filter_var,
                     values=["All", "scheduled", "completed", "cancelled"],
                     width=12, state="readonly").pack(side="left", padx=3)
        StyledButton(filter_frame, "Go", command=self._load, style="ghost").pack(side="left")
        self.table = DataTable(self, ["Appt ID", "Patient", "Doctor", "Date",
                                      "Time", "Reason", "Status"])
        self.table.pack(fill="both", expand=True)
        self.table.color_tag("scheduled", "#e8f5e9", "#1b5e20")
        self.table.color_tag("completed", "#e3f2fd", "#0d47a1")
        self.table.color_tag("cancelled", "#ffebee", "#b71c1c")
        self._load()

    def _load(self):
        self.table.clear()
        flt = self.filter_var.get()
        query = {} if flt == "All" else {"status": flt}
        for a in db.find_all("appointments", query, sort_by="created_at"):
            self.table.insert_row([
                a.get("appointment_id", ""), a.get("patient_name", ""),
                a.get("doctor_name", ""), a.get("date", ""), a.get("time", ""),
                a.get("reason", ""), a.get("status", "")
            ], tag=a.get("status", "scheduled"))

    def _add_appointment(self):
        patients = db.find_all("patients", {"status": "active"})
        doctors  = db.find_all("doctors",  {"status": "active"})
        if not patients:
            messagebox.showwarning("No Patients", "Please add patients first")
            return
        if not doctors:
            messagebox.showwarning("No Doctors", "Please add doctors first")
            return
        pat_names = [f"{p['patient_id']} - {p['full_name']}" for p in patients]
        doc_names = [f"{d['doctor_id']} - {d['full_name']} ({d.get('specialization','')})" for d in doctors]
        fields = [
            {"name": "patient",   "label": "Patient *",  "type": "combo", "values": pat_names},
            {"name": "doctor",    "label": "Doctor *",   "type": "combo", "values": doc_names},
            {"name": "date",      "label": "Date (YYYY-MM-DD)", "default": today_str()},
            {"name": "time",      "label": "Time (HH:MM)",      "default": "09:00"},
            {"name": "reason",    "label": "Reason",     "default": ""},
            {"name": "notes",     "label": "Notes",      "default": ""},
        ]
        data = make_form_dialog(self, "Book Appointment", fields)
        if not data:
            return
        pat_id   = data["patient"].split(" - ")[0]
        doc_id   = data["doctor"].split(" - ")[0]
        patient  = db.find_one("patients", {"patient_id": pat_id})
        doctor   = db.find_one("doctors",  {"doctor_id": doc_id})
        record = {
            "appointment_id": generate_id("APT"),
            "patient_id":     pat_id,
            "patient_name":   patient["full_name"],
            "doctor_id":      doc_id,
            "doctor_name":    doctor["full_name"],
            "date":           data.get("date", today_str()),
            "time":           data.get("time", ""),
            "reason":         data.get("reason", ""),
            "notes":          data.get("notes", ""),
            "status":         "scheduled",
            "created_at":     now_str(),
        }
        db.insert("appointments", record)
        messagebox.showinfo("Success", f"Appointment booked: {record['appointment_id']}")
        self._load()

    def _complete(self):
        vals = self.table.selected_values()
        if not vals:
            messagebox.showwarning("Select", "Please select an appointment")
            return
        db.update("appointments", {"appointment_id": vals[0]}, {"status": "completed"})
        self._load()

    def _cancel(self):
        vals = self.table.selected_values()
        if not vals:
            messagebox.showwarning("Select", "Please select an appointment")
            return
        if messagebox.askyesno("Confirm", "Cancel this appointment?"):
            db.update("appointments", {"appointment_id": vals[0]}, {"status": "cancelled"})
            self._load()


class AdmissionModule(BaseModule):
    def __init__(self, parent):
        super().__init__(parent, "Hospital Admissions")
        self._add_toolbar_btn("➕ Admit Patient", self._admit)
        self._add_toolbar_btn("🏠 Discharge", self._discharge, "success")
        self._add_toolbar_btn("🔄 Refresh", self._load, "ghost")
        self.table = DataTable(self, ["Adm ID", "Patient", "Doctor", "Ward",
                                      "Bed", "Admitted", "Discharged", "Diagnosis", "Status"])
        self.table.pack(fill="both", expand=True)
        self.table.color_tag("admitted",   "#e8f5e9", "#1b5e20")
        self.table.color_tag("discharged", "#e3f2fd", "#0d47a1")
        self._load()

    def _load(self):
        self.table.clear()
        for a in db.find_all("admissions", sort_by="created_at"):
            self.table.insert_row([
                a.get("admission_id", ""), a.get("patient_name", ""),
                a.get("doctor_name", ""), a.get("ward_name", ""),
                a.get("bed_number", ""), a.get("admission_date", ""),
                a.get("discharge_date", ""), a.get("diagnosis", ""),
                a.get("status", "")
            ], tag=a.get("status", "admitted"))

    def _admit(self):
        patients = db.find_all("patients", {"status": "active"})
        doctors  = db.find_all("doctors",  {"status": "active"})
        wards    = db.find_all("wards")
        if not patients or not doctors or not wards:
            messagebox.showwarning("Missing Data", "Please ensure patients, doctors, and wards exist")
            return
        available_wards = [w for w in wards if int(w.get("occupied_beds", 0)) < int(w.get("total_beds", 0))]
        if not available_wards:
            messagebox.showwarning("No Beds", "No available beds in any ward")
            return
        pat_opts  = [f"{p['patient_id']} - {p['full_name']}" for p in patients]
        doc_opts  = [f"{d['doctor_id']} - {d['full_name']}" for d in doctors]
        ward_opts = [f"{w['ward_id']} - {w['name']} ({int(w.get('total_beds',0))-int(w.get('occupied_beds',0))} free)" for w in available_wards]
        fields = [
            {"name": "patient",   "label": "Patient",   "type": "combo", "values": pat_opts},
            {"name": "doctor",    "label": "Doctor",    "type": "combo", "values": doc_opts},
            {"name": "ward",      "label": "Ward",      "type": "combo", "values": ward_opts},
            {"name": "bed",       "label": "Bed Number", "default": ""},
            {"name": "diagnosis", "label": "Diagnosis",  "default": ""},
            {"name": "date",      "label": "Admission Date", "default": today_str()},
        ]
        data = make_form_dialog(self, "Admit Patient", fields)
        if not data:
            return
        pat_id  = data["patient"].split(" - ")[0]
        doc_id  = data["doctor"].split(" - ")[0]
        ward_id = data["ward"].split(" - ")[0]
        patient = db.find_one("patients", {"patient_id": pat_id})
        doctor  = db.find_one("doctors",  {"doctor_id": doc_id})
        ward    = db.find_one("wards",    {"ward_id": ward_id})
        record = {
            "admission_id":   generate_id("ADM"),
            "patient_id":     pat_id,
            "patient_name":   patient["full_name"],
            "doctor_id":      doc_id,
            "doctor_name":    doctor["full_name"],
            "ward_id":        ward_id,
            "ward_name":      ward["name"],
            "bed_number":     data.get("bed", ""),
            "admission_date": data.get("date", today_str()),
            "discharge_date": "",
            "diagnosis":      data.get("diagnosis", ""),
            "status":         "admitted",
            "created_at":     now_str(),
        }
        db.insert("admissions", record)
        new_occ = int(ward.get("occupied_beds", 0)) + 1
        db.update("wards", {"ward_id": ward_id}, {"occupied_beds": new_occ})
        messagebox.showinfo("Success", f"Patient admitted: {record['admission_id']}")
        self._load()

    def _discharge(self):
        vals = self.table.selected_values()
        if not vals:
            messagebox.showwarning("Select", "Please select an admission")
            return
        adm = db.find_one("admissions", {"admission_id": vals[0]})
        if adm and adm.get("status") == "admitted":
            db.update("admissions", {"admission_id": vals[0]},
                      {"status": "discharged", "discharge_date": today_str()})
            ward = db.find_one("wards", {"ward_id": adm.get("ward_id", "")})
            if ward:
                new_occ = max(0, int(ward.get("occupied_beds", 0)) - 1)
                db.update("wards", {"ward_id": adm["ward_id"]}, {"occupied_beds": new_occ})
            messagebox.showinfo("Discharged", "Patient discharged successfully")
            self._load()
        else:
            messagebox.showinfo("Info", "Patient is already discharged")


class InventoryModule(BaseModule):
    def __init__(self, parent):
        super().__init__(parent, "Pharmacy & Inventory")
        self._add_toolbar_btn("➕ Add Item",    self._add_item)
        self._add_toolbar_btn("📦 Restock",    self._restock, "success")
        self._add_toolbar_btn("✏️ Edit",       self._edit,    "secondary")
        self._add_toolbar_btn("🗑 Delete",     self._delete,  "danger")
        self._add_toolbar_btn("🔄 Refresh",   self._load,    "ghost")
        self.table = DataTable(self, ["Item ID", "Name", "Category", "Qty",
                                      "Unit", "Unit Price", "Supplier", "Reorder Lvl", "Expiry"])
        self.table.pack(fill="both", expand=True)
        self.table.color_tag("critical", "#ffebee", DANGER)
        self.table.color_tag("low",      "#fff8e1", "#e65100")
        self._load()

    def _load(self):
        self.table.clear()
        for item in db.find_all("inventory", sort_by="created_at"):
            qty = int(item.get("quantity", 0))
            rl  = int(item.get("reorder_level", 10))
            tag = "critical" if qty == 0 else ("low" if qty <= rl else "")
            self.table.insert_row([
                item.get("item_id", ""), item.get("name", ""),
                item.get("category", ""), qty, item.get("unit", ""),
                f"${item.get('unit_price', 0):.2f}", item.get("supplier", ""),
                rl, item.get("expiry_date", "")
            ], tag=tag)

    def _fields(self, e=None):
        e = e or {}
        return [
            {"name": "name",          "label": "Item Name *",      "default": e.get("name", "")},
            {"name": "category",      "label": "Category", "type": "combo",
             "values": ["Medicine", "PPE", "IV Fluids", "Wound Care",
                        "Equipment", "Surgical", "Lab Supplies", "Other"],
             "default": e.get("category", "Medicine")},
            {"name": "quantity",      "label": "Quantity",         "default": str(e.get("quantity", "0"))},
            {"name": "unit",          "label": "Unit",             "default": e.get("unit", "")},
            {"name": "unit_price",    "label": "Unit Price ($)",   "default": str(e.get("unit_price", "0"))},
            {"name": "supplier",      "label": "Supplier",         "default": e.get("supplier", "")},
            {"name": "reorder_level", "label": "Reorder Level",    "default": str(e.get("reorder_level", "10"))},
            {"name": "expiry_date",   "label": "Expiry (YYYY-MM-DD)", "default": e.get("expiry_date", "")},
        ]

    def _add_item(self):
        data = make_form_dialog(self, "Add Inventory Item", self._fields())
        if not data:
            return
        try:
            data["quantity"]      = int(data.get("quantity", 0) or 0)
            data["unit_price"]    = float(data.get("unit_price", 0) or 0)
            data["reorder_level"] = int(data.get("reorder_level", 10) or 10)
        except ValueError:
            data["quantity"] = 0; data["unit_price"] = 0.0; data["reorder_level"] = 10
        data["item_id"]    = generate_id("INV")
        data["created_at"] = now_str()
        db.insert("inventory", data)
        messagebox.showinfo("Success", "Item added successfully")
        self._load()

    def _edit(self):
        vals = self.table.selected_values()
        if not vals:
            messagebox.showwarning("Select", "Please select an item")
            return
        item = db.find_one("inventory", {"item_id": vals[0]})
        if not item:
            return
        data = make_form_dialog(self, "Edit Item", self._fields(item))
        if not data:
            return
        try:
            data["quantity"]      = int(data.get("quantity", 0) or 0)
            data["unit_price"]    = float(data.get("unit_price", 0) or 0)
            data["reorder_level"] = int(data.get("reorder_level", 10) or 10)
        except ValueError:
            pass
        db.update("inventory", {"item_id": vals[0]}, data)
        messagebox.showinfo("Success", "Item updated")
        self._load()

    def _restock(self):
        vals = self.table.selected_values()
        if not vals:
            messagebox.showwarning("Select", "Please select an item to restock")
            return
        item = db.find_one("inventory", {"item_id": vals[0]})
        if not item:
            return
        amt = simpledialog.askinteger("Restock", f"How many {item.get('unit','units')} to add?",
                                      minvalue=1, maxvalue=99999)
        if amt:
            new_qty = int(item.get("quantity", 0)) + amt
            db.update("inventory", {"item_id": vals[0]}, {"quantity": new_qty})
            messagebox.showinfo("Success", f"Restocked. New quantity: {new_qty}")
            self._load()

    def _delete(self):
        vals = self.table.selected_values()
        if not vals:
            messagebox.showwarning("Select", "Please select an item")
            return
        if messagebox.askyesno("Confirm Delete", f"Delete {vals[1]}?"):
            db.delete("inventory", {"item_id": vals[0]})
            self._load()


class BillingModule(BaseModule):
    def __init__(self, parent):
        super().__init__(parent, "Billing & Payments")
        self._add_toolbar_btn("➕ New Bill", self._create_bill)
        self._add_toolbar_btn("💳 Record Payment", self._payment, "success")
        self._add_toolbar_btn("📄 View Details",   self._view_details, "secondary")
        self._add_toolbar_btn("🔄 Refresh",       self._load, "ghost")
        self.table = DataTable(self, ["Bill ID", "Patient", "Subtotal",
                                      "Tax", "Discount", "Total", "Paid", "Balance", "Status"])
        self.table.pack(fill="both", expand=True)
        self.table.color_tag("paid",      "#e8f5e9", "#1b5e20")
        self.table.color_tag("pending",   "#fff8e1", "#e65100")
        self.table.color_tag("partial",   "#e3f2fd", "#0d47a1")
        self._load()

    def _load(self):
        self.table.clear()
        for b in db.find_all("billing", sort_by="created_at"):
            total   = float(b.get("total", 0))
            paid    = float(b.get("paid", 0))
            balance = total - paid
            self.table.insert_row([
                b.get("bill_id", ""), b.get("patient_name", ""),
                f"${b.get('subtotal', 0):.2f}", f"${b.get('tax', 0):.2f}",
                f"${b.get('discount', 0):.2f}", f"${total:.2f}",
                f"${paid:.2f}", f"${balance:.2f}", b.get("status", "").title()
            ], tag=b.get("status", "pending"))

    def _create_bill(self):
        patients = db.find_all("patients", {"status": "active"})
        if not patients:
            messagebox.showwarning("No Patients", "Please add patients first")
            return
        pat_opts = [f"{p['patient_id']} - {p['full_name']}" for p in patients]
        fields = [
            {"name": "patient",   "label": "Patient",   "type": "combo", "values": pat_opts},
            {"name": "items",     "label": "Items (name:price, separated by ;)",
             "default": "Consultation:150;Lab Test:80"},
            {"name": "discount",  "label": "Discount ($)", "default": "0"},
            {"name": "tax_rate",  "label": "Tax Rate (%)", "default": "10"},
        ]
        data = make_form_dialog(self, "Create Bill", fields)
        if not data:
            return
        pat_id  = data["patient"].split(" - ")[0]
        patient = db.find_one("patients", {"patient_id": pat_id})
        items_raw = data.get("items", "")
        items = []
        subtotal = 0.0
        for part in items_raw.split(";"):
            part = part.strip()
            if ":" in part:
                name, price_str = part.rsplit(":", 1)
                try:
                    price = float(price_str.strip())
                    items.append({"name": name.strip(), "price": price})
                    subtotal += price
                except ValueError:
                    pass
        try:
            discount = float(data.get("discount", 0) or 0)
            tax_rate = float(data.get("tax_rate", 10) or 10)
        except ValueError:
            discount = 0.0; tax_rate = 10.0
        tax   = (subtotal - discount) * (tax_rate / 100)
        total = subtotal - discount + tax
        record = {
            "bill_id":      generate_id("BILL"),
            "patient_id":   pat_id,
            "patient_name": patient["full_name"],
            "items":        items,
            "subtotal":     round(subtotal, 2),
            "tax":          round(tax, 2),
            "discount":     round(discount, 2),
            "total":        round(total, 2),
            "paid":         0.0,
            "status":       "pending",
            "created_at":   now_str(),
        }
        db.insert("billing", record)
        messagebox.showinfo("Success", f"Bill created: {record['bill_id']} | Total: ${total:.2f}")
        self._load()

    def _payment(self):
        vals = self.table.selected_values()
        if not vals:
            messagebox.showwarning("Select", "Please select a bill")
            return
        bill = db.find_one("billing", {"bill_id": vals[0]})
        if not bill:
            return
        total   = float(bill.get("total", 0))
        paid    = float(bill.get("paid", 0))
        balance = total - paid
        if balance <= 0:
            messagebox.showinfo("Paid", "This bill is already fully paid")
            return
        amt = simpledialog.askfloat("Payment", f"Balance: ${balance:.2f}\nEnter payment amount:",
                                    minvalue=0.01, maxvalue=balance)
        if amt:
            new_paid = paid + amt
            status   = "paid" if new_paid >= total else "partial"
            db.update("billing", {"bill_id": vals[0]},
                      {"paid": round(new_paid, 2), "status": status})
            messagebox.showinfo("Payment Recorded",
                                f"Received: ${amt:.2f}\nTotal Paid: ${new_paid:.2f}\nStatus: {status.title()}")
            self._load()

    def _view_details(self):
        vals = self.table.selected_values()
        if not vals:
            messagebox.showwarning("Select", "Please select a bill")
            return
        bill = db.find_one("billing", {"bill_id": vals[0]})
        if not bill:
            return
        detail = tk.Toplevel(self)
        detail.title(f"Bill Details — {bill['bill_id']}")
        detail.configure(bg=CARD_BG)
        detail.geometry("400x500")
        detail.grab_set()
        tk.Label(detail, text=f"Bill: {bill['bill_id']}", font=FONT_HEAD, bg=CARD_BG).pack(pady=10)
        tk.Label(detail, text=f"Patient: {bill.get('patient_name','')}", font=FONT_BODY, bg=CARD_BG).pack()
        tk.Label(detail, text=f"Date: {bill.get('created_at','')}", font=FONT_SMALL, bg=CARD_BG, fg=MUTED).pack()
        ttk.Separator(detail, orient="horizontal").pack(fill="x", padx=20, pady=10)
        items = bill.get("items", [])
        if isinstance(items, str):
            try:
                items = json.loads(items)
            except Exception:
                items = []
        for item in items:
            name  = item.get("name", "Item")
            price = float(item.get("price", 0))
            tk.Label(detail, text=f"  {name}  .........  ${price:.2f}",
                     font=FONT_BODY, bg=CARD_BG, anchor="w").pack(fill="x", padx=30)
        ttk.Separator(detail, orient="horizontal").pack(fill="x", padx=20, pady=8)
        for label, key in [("Subtotal", "subtotal"), ("Discount", "discount"), ("Tax", "tax"), ("TOTAL", "total")]:
            val  = float(bill.get(key, 0))
            bold = "bold" if label == "TOTAL" else ""
            tk.Label(detail, text=f"  {label}:  ${val:.2f}",
                     font=("Segoe UI", 11, bold), bg=CARD_BG).pack(anchor="e", padx=30)
        paid    = float(bill.get("paid", 0))
        balance = float(bill.get("total", 0)) - paid
        tk.Label(detail, text=f"  Paid: ${paid:.2f}  |  Balance: ${balance:.2f}",
                 font=FONT_SMALL, bg=CARD_BG, fg=MUTED).pack(pady=5)
        StyledButton(detail, "Close", command=detail.destroy, style="secondary").pack(pady=10)


class WardModule(BaseModule):
    def __init__(self, parent):
        super().__init__(parent, "Ward Management")
        self._add_toolbar_btn("➕ Add Ward", self._add_ward)
        self._add_toolbar_btn("✏️ Edit",    self._edit,    "secondary")
        self._add_toolbar_btn("🔄 Refresh", self._load,   "ghost")
        self.table = DataTable(self, ["Ward ID", "Name", "Type", "Total Beds",
                                      "Occupied", "Available", "Floor"])
        self.table.pack(fill="both", expand=True)
        self.table.color_tag("full",  "#ffebee", DANGER)
        self.table.color_tag("avail", "#e8f5e9", SECONDARY)
        self._load()

    def _load(self):
        self.table.clear()
        for w in db.find_all("wards", sort_by="created_at"):
            total   = int(w.get("total_beds", 0))
            occ     = int(w.get("occupied_beds", 0))
            avail   = total - occ
            tag     = "full" if avail == 0 else "avail"
            self.table.insert_row([
                w.get("ward_id", ""), w.get("name", ""), w.get("ward_type", ""),
                total, occ, avail, w.get("floor", "")
            ], tag=tag)

    def _fields(self, e=None):
        e = e or {}
        return [
            {"name": "name",       "label": "Ward Name *", "default": e.get("name", "")},
            {"name": "ward_type",  "label": "Type", "type": "combo",
             "values": ["General", "Intensive Care", "Pediatrics", "Surgical",
                        "Maternity", "Oncology", "Orthopedics", "Neurology"],
             "default": e.get("ward_type", "General")},
            {"name": "total_beds", "label": "Total Beds",  "default": str(e.get("total_beds", "10"))},
            {"name": "floor",      "label": "Floor",       "default": e.get("floor", "Ground")},
        ]

    def _add_ward(self):
        data = make_form_dialog(self, "Add Ward", self._fields())
        if not data:
            return
        try:
            data["total_beds"] = int(data.get("total_beds", 10) or 10)
        except ValueError:
            data["total_beds"] = 10
        data["occupied_beds"] = 0
        data["ward_id"]       = generate_id("WRD")
        data["created_at"]    = now_str()
        db.insert("wards", data)
        messagebox.showinfo("Success", "Ward added")
        self._load()

    def _edit(self):
        vals = self.table.selected_values()
        if not vals:
            messagebox.showwarning("Select", "Please select a ward")
            return
        ward = db.find_one("wards", {"ward_id": vals[0]})
        if not ward:
            return
        data = make_form_dialog(self, "Edit Ward", self._fields(ward))
        if not data:
            return
        try:
            data["total_beds"] = int(data.get("total_beds", 10) or 10)
        except ValueError:
            data["total_beds"] = 10
        db.update("wards", {"ward_id": vals[0]}, data)
        self._load()


class UserModule(BaseModule):
    def __init__(self, parent):
        super().__init__(parent, "User Management")
        self._add_toolbar_btn("➕ Add User",    self._add_user)
        self._add_toolbar_btn("🔑 Reset Pwd",  self._reset_pwd, "warning")
        self._add_toolbar_btn("🗑 Delete",     self._delete,    "danger")
        self._add_toolbar_btn("🔄 Refresh",   self._load,      "ghost")
        self.table = DataTable(self, ["Username", "Full Name", "Role", "Email", "Created"])
        self.table.pack(fill="both", expand=True)
        self._load()

    def _load(self):
        self.table.clear()
        for u in db.find_all("users", sort_by="created_at"):
            self.table.insert_row([
                u.get("username", ""), u.get("full_name", ""),
                u.get("role", "").title(), u.get("email", ""),
                u.get("created_at", "")[:10]
            ])

    def _add_user(self):
        fields = [
            {"name": "username",  "label": "Username *",  "default": ""},
            {"name": "password",  "label": "Password *",  "secret": True},
            {"name": "full_name", "label": "Full Name",   "default": ""},
            {"name": "email",     "label": "Email",       "default": ""},
            {"name": "role",      "label": "Role",  "type": "combo",
             "values": ["admin", "doctor", "receptionist", "pharmacist", "nurse"]},
        ]
        data = make_form_dialog(self, "Add User", fields)
        if not data:
            return
        if not data.get("username") or not data.get("password"):
            messagebox.showerror("Validation", "Username and password are required")
            return
        existing = db.find_one("users", {"username": data["username"]})
        if existing:
            messagebox.showerror("Error", "Username already exists")
            return
        data["password"]   = hash_password(data["password"])
        data["created_at"] = now_str()
        db.insert("users", data)
        messagebox.showinfo("Success", "User created successfully")
        self._load()

    def _reset_pwd(self):
        vals = self.table.selected_values()
        if not vals:
            messagebox.showwarning("Select", "Please select a user")
            return
        new_pwd = simpledialog.askstring("Reset Password",
                                         f"Enter new password for {vals[0]}:", show="*")
        if new_pwd and len(new_pwd) >= 6:
            db.update("users", {"username": vals[0]}, {"password": hash_password(new_pwd)})
            messagebox.showinfo("Success", "Password reset successfully")
        elif new_pwd:
            messagebox.showerror("Error", "Password must be at least 6 characters")

    def _delete(self):
        vals = self.table.selected_values()
        if not vals:
            messagebox.showwarning("Select", "Please select a user")
            return
        if vals[0] == "admin":
            messagebox.showerror("Error", "Cannot delete the admin account")
            return
        if messagebox.askyesno("Confirm", f"Delete user '{vals[0]}'?"):
            db.delete("users", {"username": vals[0]})
            self._load()


class ReportsModule(BaseModule):
    def __init__(self, parent):
        super().__init__(parent, "Reports & Analytics")
        tabs = ttk.Notebook(self)
        tabs.pack(fill="both", expand=True)
        self._patient_tab(tabs)
        self._financial_tab(tabs)
        self._inventory_tab(tabs)
        self._appointment_tab(tabs)

    def _patient_tab(self, nb):
        frame = tk.Frame(nb, bg=BG)
        nb.add(frame, text="  Patient Stats  ")
        stats_frame = tk.Frame(frame, bg=BG)
        stats_frame.pack(fill="x", padx=20, pady=20)
        total        = db.count("patients")
        active       = db.count("patients", {"status": "active"})
        inactive     = db.count("patients", {"status": "inactive"})
        admitted     = db.count("admissions", {"status": "admitted"})
        discharged   = db.count("admissions", {"status": "discharged"})
        stat_data = [
            ("Total Registered",   total,     PRIMARY,  "👥"),
            ("Active Patients",    active,    SECONDARY,"✅"),
            ("Inactive Patients",  inactive,  MUTED,    "🚫"),
            ("Currently Admitted", admitted,  WARNING,  "🏥"),
            ("Total Discharged",   discharged,PRIMARY,  "🏠"),
        ]
        for i, (title, val, color, icon) in enumerate(stat_data):
            StatCard(stats_frame, title, str(val), color, icon).grid(row=0, column=i, padx=6, sticky="nsew")
            stats_frame.grid_columnconfigure(i, weight=1)
        blood_frame = tk.LabelFrame(frame, text=" Blood Group Distribution ",
                                    font=FONT_LABEL, bg=CARD_BG, bd=1, relief="solid")
        blood_frame.pack(fill="x", padx=20, pady=10)
        groups = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
        patients = db.find_all("patients")
        counts = {g: sum(1 for p in patients if p.get("blood_group") == g) for g in groups}
        for i, (g, cnt) in enumerate(counts.items()):
            cell = tk.Frame(blood_frame, bg=CARD_BG, padx=10, pady=8)
            cell.grid(row=0, column=i, sticky="nsew", padx=2)
            blood_frame.grid_columnconfigure(i, weight=1)
            tk.Label(cell, text=g, font=FONT_HEAD, bg=CARD_BG, fg=PRIMARY).pack()
            tk.Label(cell, text=str(cnt), font=("Segoe UI", 18, "bold"), bg=CARD_BG, fg=TEXT).pack()

    def _financial_tab(self, nb):
        frame = tk.Frame(nb, bg=BG)
        nb.add(frame, text="  Financial  ")
        bills    = db.find_all("billing")
        total_r  = sum(float(b.get("total", 0)) for b in bills)
        total_p  = sum(float(b.get("paid",  0)) for b in bills)
        total_b  = total_r - total_p
        pending  = sum(1 for b in bills if b.get("status") == "pending")
        paid_cnt = sum(1 for b in bills if b.get("status") == "paid")
        partial  = sum(1 for b in bills if b.get("status") == "partial")
        stats_frame = tk.Frame(frame, bg=BG)
        stats_frame.pack(fill="x", padx=20, pady=20)
        stat_data = [
            ("Total Revenue",   f"${total_r:.0f}", PRIMARY,  "💵"),
            ("Total Collected", f"${total_p:.0f}", SECONDARY, "✅"),
            ("Outstanding",     f"${total_b:.0f}", DANGER,    "⚠️"),
            ("Pending Bills",   str(pending),       WARNING,   "⏳"),
            ("Paid Bills",      str(paid_cnt),      SECONDARY, "✔"),
            ("Partial Bills",   str(partial),       PRIMARY,   "½"),
        ]
        for i, (title, val, color, icon) in enumerate(stat_data):
            StatCard(stats_frame, title, val, color, icon).grid(row=0, column=i, padx=6, sticky="nsew")
            stats_frame.grid_columnconfigure(i, weight=1)
        tbl_frame = tk.LabelFrame(frame, text=" Recent Bills ", font=FONT_LABEL,
                                  bg=CARD_BG, bd=1, relief="solid")
        tbl_frame.pack(fill="both", expand=True, padx=20, pady=10)
        tbl = DataTable(tbl_frame, ["Bill ID", "Patient", "Total", "Paid", "Balance", "Status"])
        tbl.pack(fill="both", expand=True, padx=5, pady=5)
        tbl.color_tag("paid",    "#e8f5e9", SECONDARY)
        tbl.color_tag("pending", "#fff8e1", "#e65100")
        tbl.color_tag("partial", "#e3f2fd", PRIMARY)
        for b in bills[:20]:
            total   = float(b.get("total", 0))
            paid    = float(b.get("paid",  0))
            balance = total - paid
            tbl.insert_row([b.get("bill_id", ""), b.get("patient_name", ""),
                            f"${total:.2f}", f"${paid:.2f}",
                            f"${balance:.2f}", b.get("status", "").title()],
                           tag=b.get("status", "pending"))

    def _inventory_tab(self, nb):
        frame = tk.Frame(nb, bg=BG)
        nb.add(frame, text="  Inventory  ")
        inv = db.find_all("inventory")
        total_items = len(inv)
        out_of_stock = sum(1 for i in inv if int(i.get("quantity", 0)) == 0)
        low_stock    = sum(1 for i in inv if 0 < int(i.get("quantity", 0)) <= int(i.get("reorder_level", 10)))
        total_value  = sum(float(i.get("quantity", 0)) * float(i.get("unit_price", 0)) for i in inv)
        stats_frame = tk.Frame(frame, bg=BG)
        stats_frame.pack(fill="x", padx=20, pady=20)
        stat_data = [
            ("Total Items",     str(total_items),     PRIMARY,  "📦"),
            ("Out of Stock",    str(out_of_stock),    DANGER,   "🚫"),
            ("Low Stock",       str(low_stock),       WARNING,  "⚠️"),
            ("Inventory Value", f"${total_value:.0f}", SECONDARY,"💰"),
        ]
        for i, (title, val, color, icon) in enumerate(stat_data):
            StatCard(stats_frame, title, val, color, icon).grid(row=0, column=i, padx=6, sticky="nsew")
            stats_frame.grid_columnconfigure(i, weight=1)
        tbl_frame = tk.LabelFrame(frame, text=" Items Needing Attention ", font=FONT_LABEL,
                                  bg=CARD_BG, bd=1, relief="solid")
        tbl_frame.pack(fill="both", expand=True, padx=20, pady=10)
        tbl = DataTable(tbl_frame, ["Item", "Category", "Qty", "Reorder Lvl", "Value", "Status"])
        tbl.pack(fill="both", expand=True, padx=5, pady=5)
        tbl.color_tag("critical", "#ffebee", DANGER)
        tbl.color_tag("low",      "#fff8e1", "#e65100")
        for item in inv:
            qty = int(item.get("quantity", 0))
            rl  = int(item.get("reorder_level", 10))
            if qty <= rl:
                tag    = "critical" if qty == 0 else "low"
                status = "OUT OF STOCK" if qty == 0 else "LOW STOCK"
                value  = qty * float(item.get("unit_price", 0))
                tbl.insert_row([item.get("name", ""), item.get("category", ""),
                                qty, rl, f"${value:.2f}", status], tag=tag)

    def _appointment_tab(self, nb):
        frame = tk.Frame(nb, bg=BG)
        nb.add(frame, text="  Appointments  ")
        appts      = db.find_all("appointments")
        total      = len(appts)
        scheduled  = sum(1 for a in appts if a.get("status") == "scheduled")
        completed  = sum(1 for a in appts if a.get("status") == "completed")
        cancelled  = sum(1 for a in appts if a.get("status") == "cancelled")
        today_cnt  = sum(1 for a in appts if a.get("date") == today_str())
        stats_frame = tk.Frame(frame, bg=BG)
        stats_frame.pack(fill="x", padx=20, pady=20)
        stat_data = [
            ("Total",     str(total),     PRIMARY,  "📋"),
            ("Scheduled", str(scheduled), SECONDARY,"📅"),
            ("Completed", str(completed), PRIMARY,  "✅"),
            ("Cancelled", str(cancelled), DANGER,   "❌"),
            ("Today",     str(today_cnt), WARNING,  "🗓"),
        ]
        for i, (title, val, color, icon) in enumerate(stat_data):
            StatCard(stats_frame, title, val, color, icon).grid(row=0, column=i, padx=6, sticky="nsew")
            stats_frame.grid_columnconfigure(i, weight=1)
        tbl_frame = tk.LabelFrame(frame, text=" Doctor Workload ", font=FONT_LABEL,
                                  bg=CARD_BG, bd=1, relief="solid")
        tbl_frame.pack(fill="both", expand=True, padx=20, pady=10)
        tbl = DataTable(tbl_frame, ["Doctor", "Specialization", "Total Appts", "Completed", "Scheduled"])
        tbl.pack(fill="both", expand=True, padx=5, pady=5)
        doctors = db.find_all("doctors")
        for doc in doctors:
            did    = doc["doctor_id"]
            d_appts = [a for a in appts if a.get("doctor_id") == did]
            d_comp  = sum(1 for a in d_appts if a.get("status") == "completed")
            d_sch   = sum(1 for a in d_appts if a.get("status") == "scheduled")
            tbl.insert_row([doc.get("full_name", ""), doc.get("specialization", ""),
                            len(d_appts), d_comp, d_sch])


if __name__ == "__main__":
    seed_admin()
    seed_sample_data()
    LoginWindow()