"""
AI_Activities_in_Progress_GUI.py
Location: C:\\Users\\yerbr\\startup

Simple GUI for managing AI lifecycle activities:
 - Start AI Brain
 - Pause AI Brain
 - Resume AI Brain
 - Safely Stop AI Brain

References:
 (1) GUI Folder: C:\\Users\\yerbr\\startup
 (2) AI Activities Module: C:\\Users\\yerbr\\AI_Algorithms\\public_mirror\\AI_Activities_in_Progress.py

This interface connects to your existing AI_Activities_Start_Safely_Stop.py module.
"""

import tkinter as tk
from tkinter import messagebox
from urllib.request import urlopen
from io import BytesIO
from PIL import Image, ImageTk
import AI_Activities_Start_Safely_Stop as brain
from find_site_logo import find_site_logo

# ------------------------------------------------------------
# FUNCTION STUBS (connect these to your real logic)
# ------------------------------------------------------------
def start_ai_brain():
    brain.start_brain()
    messagebox.showinfo("AI Status", "AI Brain started successfully.")

def pause_ai_brain():
    brain.pause_brain()
    messagebox.showwarning("AI Status", "AI Brain paused.")

def resume_ai_brain():
    brain.resume_brain()
    messagebox.showinfo("AI Status", "AI Brain resumed.")

def stop_ai_brain_safely():
    brain.stop_brain_safely()
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
    
    logo_url = find_site_logo("https://glowinggoldenglobe.com")
    try:
        logo_url = "https://glowinggoldenglobe.com/favicon.ico"
        with urlopen(logo_url) as response:
            logo_img = Image.open(BytesIO(response.read())).resize((64, 64))
            logo = ImageTk.PhotoImage(logo_img)
            tk.Label(window, image=logo, bg="#1e1e2f").pack(pady=6)
            window.iconphoto(False, logo)
    except Exception as e:
        print(f"Logo load failed: {e}")

    # Header logo (PNG)
    logo_path = r"C:\Users\yerbr\startup\glowinggoldenglobe_logo_resized.png"
    try:
        logo_img = Image.open(logo_path)
        # Preserve aspect ratio
        base_width = 128
        w_percent = base_width / float(logo_img.size[0])
        h_size = int(float(logo_img.size[1]) * w_percent)
        logo_img = logo_img.resize((base_width, h_size), Image.LANCZOS)
        logo = ImageTk.PhotoImage(logo_img)
        tk.Label(window, image=logo, bg="#1e1e2f").pack(pady=6)
    except Exception as e:
        print(f"Header logo load failed: {e}")

    # Title‑bar icon
    icon_path = r"C:\Users\yerbr\startup\glowinggoldenglobe_icon.ico"
    window.iconbitmap(icon_path)

    # Header
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
        "bg": "#2e2e3f",
        "fg": "#ffffff",
        "activebackground": "#00ffff"
    }

    tk.Button(window, text="Start AI Brain", command=start_ai_brain, **button_style).pack(pady=6)
    tk.Button(window, text="Pause AI Brain", command=pause_ai_brain, **button_style).pack(pady=6)
    tk.Button(window, text="Resume AI Brain", command=resume_ai_brain, **button_style).pack(pady=6)
    tk.Button(window, text="Stop AI Brain Safely", command=stop_ai_brain_safely, **button_style).pack(pady=6)

    # Footer references (table layout, no borders)
    footer_frame = tk.Frame(window, bg="#1e1e2f")
    footer_frame.pack(pady=14)

    tk.Label(
        footer_frame,
        text="References:",
        font=("Segoe UI", 10, "bold"),
        fg="#00ffff",
        bg="#1e1e2f",
        anchor="w"
    ).grid(row=0, column=0, sticky="w", padx=10)

    tk.Label(
        footer_frame,
        text="GUI Folder: C:\\Users\\yerbr\\startup",
        font=("Segoe UI", 9),
        fg="#aaaaaa",
        bg="#1e1e2f",
        anchor="w"
    ).grid(row=1, column=0, sticky="w", padx=10)

    tk.Label(
        footer_frame,
        text="AI Module: C:\\Users\\yerbr\\AI_Algorithms\\public_mirror\\AI_Activities_in_Progress.py",
        font=("Segoe UI", 9),
        fg="#aaaaaa",
        bg="#1e1e2f",
        anchor="w"
    ).grid(row=2, column=0, sticky="w", padx=10)

    window.mainloop()


if __name__ == "__main__":
    launch_gui()
