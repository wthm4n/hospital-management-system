import hashlib, re, datetime, uuid


def hash_pw(pw: str) -> str:
    salt = "HMS_COLLEGE_2025_SALT"
    return hashlib.sha256((salt + pw + salt).encode()).hexdigest()


def verify_pw(raw: str, hashed: str) -> bool:
    return hash_pw(raw) == hashed


def gen_id(prefix="") -> str:
    return prefix + str(uuid.uuid4()).replace("-","")[:10].upper()


def today() -> str:
    return datetime.date.today().isoformat()


def now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def fmt_currency(val) -> str:
    try:
        return f"${float(val):,.2f}"
    except Exception:
        return "$0.00"


def fmt_date(s: str) -> str:
    try:
        return datetime.datetime.strptime(s, "%Y-%m-%d").strftime("%d %b %Y")
    except Exception:
        return s or "—"


def age_from_dob(dob: str) -> str:
    try:
        d = datetime.datetime.strptime(dob, "%Y-%m-%d")
        delta = datetime.date.today() - d.date()
        return str(delta.days // 365)
    except Exception:
        return "—"


def validate_email(e: str) -> bool:
    return bool(re.match(r"[^@]+@[^@]+\.[^@]+", e or ""))


def validate_phone(p: str) -> bool:
    return bool(re.match(r"^\+?[\d\s\-]{7,15}$", p or ""))


PERMISSIONS = {
    "admin":         ["all"],
    "doctor":        ["patients_view", "patients_edit", "appointments", "admissions", "lab", "prescriptions"],
    "receptionist":  ["patients_view", "patients_add", "appointments", "billing_view"],
    "pharmacist":    ["inventory", "prescriptions_view"],
    "nurse":         ["patients_view", "admissions_view", "lab_view"],
    "accountant":    ["billing", "reports_financial"],
    "lab_tech":      ["lab", "patients_view"],
}


def has_permission(role: str, perm: str) -> bool:
    perms = PERMISSIONS.get(role, [])
    return "all" in perms or perm in perms or any(p.startswith(perm.split("_")[0]) for p in perms)
