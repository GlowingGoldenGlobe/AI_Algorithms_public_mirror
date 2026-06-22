"""
AI_Brain_Commands_GUI.py
Simple GUI with four buttons:
 - Start AI Brain
 - Pause AI Brain
 - Resume AI Brain
 - Safely Stop AI Brain

This GUI calls function stubs that you can connect to your
existing AI_Brain_Commands_Start_Safely_Stop.py module.
"""
# AI_Brain_Commands_GUI.py
import tkinter as tk
from tkinter import messagebox
import AI_Brain_Commands_Start_Safely_Stop as brain

# ---------------------------------------------------------
# FUNCTION STUBS (connect these to your real logic)
# ---------------------------------------------------------
def create_gui():
    window = tk.Tk()
    window.title("AI Brain Control Panel")
    window.geometry("300x250")

    tk.Label(window, text="AI Brain Lifecycle Control", font=("Arial", 14, "bold")).pack(pady=10)

    tk.Button(window, text="Start Brain", width=20, command=brain.start_brain).pack(pady=5)
    tk.Button(window, text="Pause Brain", width=20, command=brain.pause_brain).pack(pady=5)
    tk.Button(window, text="Resume Brain", width=20, command=brain.resume_brain).pack(pady=5)
    tk.Button(window, text="Stop Brain Safely", width=20, command=brain.stop_brain_safely).pack(pady=5)

    window.mainloop()

def start_ai_brain():
    brain.start_brain()

def pause_ai_brain():
    brain.pause_brain()

def resume_ai_brain():
    brain.resume_brain()

def stop_ai_brain_safely():
    brain.stop_brain_safely()

# ---------------------------------------------------------
# GUI WINDOW
# ---------------------------------------------------------

def launch_gui():
    window = tk.Tk()
    window.title("AI Brain Command Panel")
    window.geometry("320x260")

    tk.Label(
        window,
        text="AI Brain Command Module",
        font=("Arial", 14)
    ).pack(pady=12)

    tk.Button(
        window,
        text="Start AI Brain",
        width=28,
        command=start_ai_brain
    ).pack(pady=6)

    tk.Button(
        window,
        text="Pause AI Brain",
        width=28,
        command=pause_ai_brain
    ).pack(pady=6)

    tk.Button(
        window,
        text="Resume AI Brain",
        width=28,
        command=resume_ai_brain
    ).pack(pady=6)

    tk.Button(
        window,
        text="Safely Stop AI Brain",
        width=28,
        command=stop_ai_brain_safely
    ).pack(pady=6)

    window.mainloop()


# ---------------------------------------------------------
# MAIN ENTRY
# ---------------------------------------------------------
 
if __name__ == "__main__":
    create_gui()
