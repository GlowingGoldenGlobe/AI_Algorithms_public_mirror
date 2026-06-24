"""
AI_Activities_in_Progress_GUI.py
Location: C:/Users/yerbr/startup

Simple GUI for managing AI lifecycle activities:
 - Start AI Brain
 - Pause AI Brain
 - Resume AI Brain
 - Safely Stop AI Brain

References:
(1) GUI Folder: C:/Users/yerbr/startup
(2) AI Activities Module:
    C:/Users/yerbr/AI_Algorithms_public_mirror/AI_Activities_in_Progress.py

This interface connects to your existing AI_Activities_Start_Safely_Stop.py module.
"""

import tkinter as tk
from tkinter import messagebox
from urllib.request import urlopen
from io import BytesIO
from PIL import Image, ImageTk
import threading
import time

from AI_Activities_Start_Safely_Stop import (
    start_brain,
    pause_brain,
    resume_brain,
    stop_brain_safely,
    get_live_status
)

# ------------------------------------------------------------
# GUI WINDOW
# ------------------------------------------------------------
def launch_gui():
    window = tk.Tk()
    window.title("AI Activities in Progress")
    window.geometry("480x380")
    window.configure(bg="#1e1e2f")

    # Load logo AFTER window creation
    try:
        logo_url = "https://glowinggoldenglobe.com/favicon.ico"
        with urlopen(logo_url) as response:
            logo_img = Image.open(BytesIO(response.read())).resize((64, 64))
            logo_photo = ImageTk.PhotoImage(logo_img)
            tk.Label(window, image=logo_photo, bg="#1e1e2f").pack(pady=6)
    except Exception:
        tk.Label(window, text="Glowing Golden Globe", bg="#1e1e2f", fg="white").pack(pady=6)

    # Header text
    tk.Label(
        window,
        text="AI Activities Control Panel",
        font=("Consolas", 14, "bold"),
        bg="#1e1e2f",
        fg="#00ff99"
    ).pack(pady=5)

    # Status label
    ai_status = tk.StringVar(value="Idle")
    status_label = tk.Label(window, textvariable=ai_status, font=("Consolas", 12, "bold"), bg="#1e1e2f", fg="white")
    status_label.pack(pady=10)

    # Buttons
    tk.Button(window, text="Start AI Brain", command=lambda: start_ai_brain(ai_status), width=25).pack(pady=5)
    tk.Button(window, text="Pause AI Brain", command=lambda: pause_ai_brain(ai_status), width=25).pack(pady=5)
    tk.Button(window, text="Resume AI Brain", command=lambda: resume_ai_brain(ai_status), width=25).pack(pady=5)
    tk.Button(window, text="Safely Stop AI Brain", command=lambda: stop_ai_brain_safely(ai_status), width=25).pack(pady=5)

    # Live output box
    output_box = tk.Text(window, height=10, width=60, bg="#0f0f1a", fg="#00ff99", font=("Consolas", 10))
    output_box.pack(pady=10)

    def update_live_output():
        """Continuously fetch live output from AI Brain."""
        while True:
            status = get_live_status()
            if status:
                output_box.insert(tk.END, status + "\n")
                output_box.see(tk.END)
                if "Paused" in status:
                    ai_status.set("Paused")
                elif "Simulating" in status:
                    ai_status.set("Simulating")
                elif "Stopped" in status:
                    ai_status.set("Stopped")
            time.sleep(1)

    threading.Thread(target=update_live_output, daemon=True).start()
    window.mainloop()

# ------------------------------------------------------------
# FUNCTION STUBS
# ------------------------------------------------------------
def start_ai_brain(ai_status):
    start_brain()
    ai_status.set("Simulating")
    messagebox.showinfo("AI Status", "AI Brain started successfully.")

def pause_ai_brain(ai_status):
    pause_brain()
    ai_status.set("Paused")
    messagebox.showwarning("AI Status", "AI Brain paused.")

def resume_ai_brain(ai_status):
    resume_brain()
    ai_status.set("Simulating")
    messagebox.showinfo("AI Status", "AI Brain resumed.")

def stop_ai_brain_safely(ai_status):
    stop_brain_safely()
    ai_status.set("Stopped")
    messagebox.showinfo("AI Status", "AI Brain stopped safely.")

# ------------------------------------------------------------
# MAIN ENTRY POINT
# ------------------------------------------------------------
if __name__ == "__main__":
    launch_gui()
