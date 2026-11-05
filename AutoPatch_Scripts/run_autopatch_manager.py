"""
Launcher for R1 AutoPatch Script & Cloud Repository Manager
"""

import os
import sys

# Ensure current script directory is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from push_autopatch import AutoPatchManagerApp
import tkinter as tk

if __name__ == "__main__":
    root = tk.Tk()
    app = AutoPatchManagerApp(root)
    root.mainloop()

