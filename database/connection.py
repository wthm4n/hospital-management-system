import sqlite3, json, uuid, os
from typing import Optional
from config import MONGO_URI, DB_NAME, SQLITE_PATH

try:
    from pymongo import MongoClient
    MONGO_OK = True
except ImportError:
    MONGO_OK = False


def gen_id(prefix=""):
    return prefix + str(uuid.uuid4()).replace("-","")[:10].upper()


class DB:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self.mongo = False
        self._client = None
        self._db = None
        self._sq = None
        if MONGO_OK:
            try:
                self._client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=1500)
                self._client.admin.command("ping")
                self._db = self._client[DB_NAME]
                self.mongo = True
                self._mongo_indexes()
                return
            except Exception:
                pass
        self._sqlite_setup()

    def _mongo_indexes(self):
        self._db.users.create_index("username", unique=True)
        self._db.patients.create_index("pid", unique=True)
        self._db.doctors.create_index("did", unique=True)
        self._db.appointments.create_index("aid", unique=True)
        self._db.billing.create_index("bid", unique=True)
        self._db.inventory.create_index("iid", unique=True)
        self._db.wards.create_index("wid", unique=True)
        self._db.admissions.create_index("admid", unique=True)
        self._db.audit_log.create_index([("ts", -1)])

    def _sqlite_setup(self):
        self._sq = sqlite3.connect(SQLITE_PATH, check_same_thread=False)
        self._sq.row_factory = sqlite3.Row
        self._sq.executescript("""
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS users(
    id TEXT PRIMARY KEY, username TEXT UNIQUE, password TEXT,
    role TEXT, full_name TEXT, email TEXT, phone TEXT,
    is_active INTEGER DEFAULT 1, last_login TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS patients(
    id TEXT PRIMARY KEY, pid TEXT UNIQUE, full_name TEXT,
    dob TEXT, gender TEXT, blood TEXT, phone TEXT, email TEXT,
    address TEXT, emergency_name TEXT, emergency_phone TEXT,
    allergies TEXT, chronic TEXT, notes TEXT,
    status TEXT DEFAULT 'active', created_at TEXT);
CREATE TABLE IF NOT EXISTS doctors(
    id TEXT PRIMARY KEY, did TEXT UNIQUE, full_name TEXT,
    specialization TEXT, qualification TEXT, phone TEXT, email TEXT,
    schedule TEXT, fee REAL DEFAULT 0,
    status TEXT DEFAULT 'active', created_at TEXT);
CREATE TABLE IF NOT EXISTS appointments(
    id TEXT PRIMARY KEY, aid TEXT UNIQUE, pid TEXT, patient_name TEXT,
    did TEXT, doctor_name TEXT, date TEXT, time TEXT, reason TEXT,
    symptoms TEXT, status TEXT DEFAULT 'scheduled', notes TEXT,
    prescription TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS billing(
    id TEXT PRIMARY KEY, bid TEXT UNIQUE, pid TEXT, patient_name TEXT,
    items TEXT, subtotal REAL, tax REAL, discount REAL, total REAL,
    paid REAL DEFAULT 0, payment_mode TEXT,
    status TEXT DEFAULT 'pending', created_at TEXT);
CREATE TABLE IF NOT EXISTS inventory(
    id TEXT PRIMARY KEY, iid TEXT UNIQUE, name TEXT, category TEXT,
    quantity INTEGER DEFAULT 0, unit TEXT, unit_price REAL,
    supplier TEXT, reorder_level INTEGER DEFAULT 10,
    batch TEXT, expiry TEXT, location TEXT,
    created_at TEXT);
CREATE TABLE IF NOT EXISTS wards(
    id TEXT PRIMARY KEY, wid TEXT UNIQUE, name TEXT, ward_type TEXT,
    total_beds INTEGER, occupied INTEGER DEFAULT 0,
    floor TEXT, charge_per_day REAL DEFAULT 0, created_at TEXT);
CREATE TABLE IF NOT EXISTS admissions(
    id TEXT PRIMARY KEY, admid TEXT UNIQUE, pid TEXT, patient_name TEXT,
    did TEXT, doctor_name TEXT, wid TEXT, ward_name TEXT,
    bed TEXT, diagnosis TEXT, admitted_on TEXT, discharged_on TEXT,
    daily_rate REAL DEFAULT 0, total_days INTEGER DEFAULT 0,
    status TEXT DEFAULT 'admitted', notes TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS audit_log(
    id TEXT PRIMARY KEY, user TEXT, action TEXT,
    module TEXT, detail TEXT, ts TEXT);
CREATE TABLE IF NOT EXISTS lab_tests(
    id TEXT PRIMARY KEY, ltid TEXT UNIQUE, pid TEXT, patient_name TEXT,
    did TEXT, doctor_name TEXT, test_name TEXT,
    status TEXT DEFAULT 'pending', result TEXT,
    ordered_on TEXT, completed_on TEXT, created_at TEXT);
""")
        self._sq.commit()

    def insert(self, col, data):
        try:
            if "id" not in data:
                data["id"] = gen_id()
            if self.mongo:
                self._db[col].insert_one(data)
            else:
                self._sq_insert(col, data)
            return True
        except Exception as e:
            print(f"[DB insert] {col}: {e}")
            return False

    def find(self, col, q=None, sort=None, limit=0):
        try:
            if self.mongo:
                cur = self._db[col].find(q or {})
                if sort:
                    cur = cur.sort(sort, -1)
                if limit:
                    cur = cur.limit(limit)
                return [self._m2d(d) for d in cur]
            else:
                return self._sq_find(col, q, sort, limit)
        except Exception as e:
            print(f"[DB find] {col}: {e}")
            return []

    def find_one(self, col, q):
        try:
            if self.mongo:
                return self._m2d(self._db[col].find_one(q))
            r = self._sq_find(col, q)
            return r[0] if r else None
        except Exception as e:
            print(f"[DB find_one] {col}: {e}")
            return None

    def update(self, col, q, data):
        try:
            if self.mongo:
                self._db[col].update_one(q, {"$set": data})
            else:
                self._sq_update(col, q, data)
            return True
        except Exception as e:
            print(f"[DB update] {col}: {e}")
            return False

    def delete(self, col, q):
        try:
            if self.mongo:
                self._db[col].delete_one(q)
            else:
                self._sq_delete(col, q)
            return True
        except Exception as e:
            print(f"[DB delete] {col}: {e}")
            return False

    def count(self, col, q=None):
        try:
            if self.mongo:
                return self._db[col].count_documents(q or {})
            return len(self._sq_find(col, q))
        except Exception:
            return 0

    def _m2d(self, doc):
        if doc is None:
            return None
        d = dict(doc)
        if "_id" in d:
            d["_id"] = str(d["_id"])
        return d

    def _sq_insert(self, table, data):
        c = self._sq.cursor()
        vals = []
        for v in data.values():
            vals.append(json.dumps(v) if isinstance(v, (dict, list)) else v)
        cols = ", ".join(data.keys())
        ph   = ", ".join(["?" for _ in data])
        c.execute(f"INSERT INTO {table} ({cols}) VALUES ({ph})", vals)
        self._sq.commit()

    def _sq_find(self, table, q=None, sort=None, limit=0):
        c = self._sq.cursor()
        where, vals = self._where(q)
        order = f" ORDER BY {sort} DESC" if sort else " ORDER BY rowid DESC"
        lim   = f" LIMIT {limit}" if limit else ""
        c.execute(f"SELECT * FROM {table}{where}{order}{lim}", vals)
        result = []
        for row in c.fetchall():
            d = dict(row)
            for k, v in d.items():
                if isinstance(v, str) and v and v[0] in "{[":
                    try:
                        d[k] = json.loads(v)
                    except Exception:
                        pass
            result.append(d)
        return result

    def _sq_update(self, table, q, data):
        c = self._sq.cursor()
        sets, svals = [], []
        for k, v in data.items():
            sets.append(f"{k}=?")
            svals.append(json.dumps(v) if isinstance(v, (dict, list)) else v)
        where, wvals = self._where(q)
        c.execute(f"UPDATE {table} SET {', '.join(sets)}{where}", svals + wvals)
        self._sq.commit()

    def _sq_delete(self, table, q):
        c  = self._sq.cursor()
        where, vals = self._where(q)
        c.execute(f"DELETE FROM {table}{where}", vals)
        self._sq.commit()

    def _where(self, q):
        if not q:
            return "", []
        parts, vals = [], []
        for k, v in q.items():
            parts.append(f"{k}=?")
            vals.append(v)
        return " WHERE " + " AND ".join(parts), vals

    def close(self):
        if self._client:
            self._client.close()
        if self._sq:
            self._sq.close()


db = DB()
