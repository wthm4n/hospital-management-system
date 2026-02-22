import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.login_window import LoginWindow

if __name__ == "__main__":
    LoginWindow()
