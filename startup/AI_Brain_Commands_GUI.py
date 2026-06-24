"""
AI_Activities_in_Progress_GUI.py
Location: C:/Users/yerbr/startup

Purpose:
Provides a graphical interface for controlling and monitoring AI Brain lifecycle events.
Includes:
 - Header image and icon
 - References text
 - Live output streaming from AI Brain, Metrics, Dashboard, and Monitor terminals
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
    get_live_status,
    start_metrics,
    start_dashboard,
    start_monitor
)

# ------------------------------------------------------------
# CONTROL FUNCTIONS
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
            logo = ImageTk.PhotoImage(logo_img)
            tk.Label(window, image=logo, bg="#1e1e2f").pack(pady=6)
            window.iconphoto(False, logo)
    except Exception as e:
        print(f"Logo load failed: {e}")

    # Header image (slightly wider, keep height constant)
    logo_path = r"C:\Users\yerbr\startup\glowinggoldenglobe_logo_resized.png"
    try:
        logo_img = Image.open(logo_path)
        original_width, original_height = logo_img.size
        new_width = int(original_width * 1.3)  # widen by 30% for natural proportions
        logo_img = logo_img.resize((new_width, original_height), Image.LANCZOS)
        logo = ImageTk.PhotoImage(logo_img)
        tk.Label(window, image=logo, bg="#1e1e2f").pack(pady=6)
        window.logo_ref = logo
    except Exception as e:
        print(f"Header logo load failed: {e}")

    # Title‑bar icon (.ico)
    icon_path = r"C:\Users\yerbr\startup\glowinggoldenglobe_icon.ico"
    try:
        window.iconbitmap(icon_path)
    except Exception as e:
        print(f"Icon load failed: {e}")

    # Header text
    tk.Label(
        window,
        text="AI Activities Control Panel",
        font=("Segoe UI", 15, "bold"),
        fg="#00ffff",
        bg="#1e1e2f"
    ).pack(pady=8)

    # Buttons
    button_style = {
        "width": 26,
        "font": ("Segoe UI", 11),
    }

    tk.Button(window, text="Start AI Brain", command=lambda: start_ai_brain(ai_status), **button_style).pack(pady=4)
    tk.Button(window, text="Pause AI Brain", command=lambda: pause_ai_brain(ai_status), **button_style).pack(pady=4)
    tk.Button(window, text="Resume AI Brain", command=lambda: resume_ai_brain(ai_status), **button_style).pack(pady=4)
    tk.Button(window, text="Safely Stop AI Brain", command=lambda: stop_ai_brain_safely(ai_status), **button_style).pack(pady=4)
    tk.Button(window, text="Start Metrics Terminal", command=start_metrics, **button_style).pack(pady=4)
    tk.Button(window, text="Start Dashboard Terminal", command=start_dashboard, **button_style).pack(pady=4)
    tk.Button(window, text="Start Monitor Terminal", command=start_monitor, **button_style).pack(pady=4)

    # Live output box
    output_box = tk.Text(window, height=10, width=60, bg="#0f0f1a", fg="#00ff99", font=("Consolas", 10))
    output_box.pack(pady=10)

    ai_status = tk.StringVar(value="Idle")
    tk.Label(window, textvariable=ai_status, font=("Consolas", 12, "bold"), bg="#1e1e2f", fg="white").pack(pady=5)

    def update_live_output():
        """Continuously fetch live output from all AI terminals."""
        while True:
            status = get_live_status()
            if status:
                output_box.insert(tk.END, status + "\n")
                output_box.see(tk.END)
                if "Paused" in status:
                    ai_status.set("Paused")
                elif "Simulating" in status or "Running" in status:
                    ai_status.set("Simulating")
                elif "Stopped" in status:
                    ai_status.set("Stopped")
            time.sleep(1)

    threading.Thread(target=update_live_output, daemon=True).start()

    # --------------------------------------------------------
    # REFERENCES TABLE (original style, no borders)
    # --------------------------------------------------------
    references_frame = tk.Frame(window, bg="#1e1e2f")
    references_frame.pack(pady=10)

    tk.Label(
        references_frame,
        text="References",
        font=("Segoe UI", 12, "bold"),
        fg="#00ffff",
        bg="#1e1e2f"
    ).grid(row=0, column=0, columnspan=2, pady=(0, 6))

    tk.Label(
        references_frame,
        text="(1) GUI Folder:",
        font=("Segoe UI", 10),
        fg="#aaaaaa",
        bg="#1e1e2f",
        anchor="w"
    ).grid(row=1, column=0, sticky="w", padx=(10, 5))
    tk.Label(
        references_frame,
        text="C:/Users/yerbr/startup",
        font=("Segoe UI", 10),
        fg="#ffffff",
        bg="#1e1e2f",
        anchor="w"
    ).grid(row=1, column=1, sticky="w")

    tk.Label(
        references_frame,
        text="(2) AI Activities Module:",
        font=("Segoe UI", 10),
        fg="#aaaaaa",
        bg="#1e1e2f",
        anchor="w"
    ).grid(row=2, column=0, sticky="w", padx=(10, 5))
    tk.Label(
        references_frame,
        text="AI_Activities_Start_Safely_Stop.py",
        font=("Segoe UI", 10),
        fg="#ffffff",
        bg="#1e1e2f",
        anchor="w"
    ).grid(row=2, column=1, sticky="w")

    window.mainloop()

# ------------------------------------------------------------
# MAIN ENTRY POINT
# ------------------------------------------------------------
if __name__ == "__main__":
    launch_gui()
