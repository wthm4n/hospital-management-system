import os

MONGO_URI   = os.environ.get("MONGO_URI",    "mongodb://localhost:27017/")
DB_NAME     = os.environ.get("HMS_DB",        "hms_college")
SQLITE_PATH = os.environ.get("HMS_SQLITE",    "hms.db")
APP_NAME    = "MediCore HMS"
VERSION     = "3.0"

C_BG        = "#0f1117"
C_SURFACE   = "#1a1d2e"
C_SURFACE2  = "#252840"
C_CARD      = "#1e2235"
C_BORDER    = "#2d3154"
C_PRIMARY   = "#6c63ff"
C_PRIMARY_H = "#8b85ff"
C_GREEN     = "#00d68f"
C_RED       = "#ff4d6d"
C_YELLOW    = "#ffd166"
C_CYAN      = "#00b4d8"
C_ORANGE    = "#ff6b35"
C_TEXT      = "#e8eaf6"
C_MUTED     = "#8892b0"
C_WHITE     = "#ffffff"

SIDEBAR_W   = 230

FT          = "Segoe UI"
F_TITLE     = (FT, 22, "bold")
F_HEAD      = (FT, 14, "bold")
F_SUB       = (FT, 11, "bold")
F_BODY      = (FT, 11)
F_SMALL     = (FT, 9)
F_LABEL     = (FT, 10)
F_BTN       = (FT, 10, "bold")
F_MONO      = ("Consolas", 10)

ROLES = ["admin", "doctor", "receptionist", "pharmacist", "nurse", "accountant", "lab_tech"]
