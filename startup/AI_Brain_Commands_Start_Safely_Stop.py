"""
module_commands.py
Automated command events for AI Brain lifecycle control.
Provides: start, safe stop, pause, resume.
Includes a minimal GUI interface with one button per action.
"""

import subprocess
import os
import signal
import threading
import tkinter as tk
from tkinter import messagebox

# ---------------------------------------------------------
# INTERNAL STATE
# ---------------------------------------------------------

AI_BRAIN_PROCESS = None
AI_BRAIN_PAUSED = False
AI_BRAIN_PATH = "run_eval.py"   # Adjust if needed


# ---------------------------------------------------------
# COMMAND FUNCTIONS
# ---------------------------------------------------------

def start_brain():
    global AI_BRAIN_PROCESS

    if AI_BRAIN_PROCESS is not None:
        messagebox.showinfo("AI Brain", "AI Brain is already running.")
        return

    try:
        AI_BRAIN_PROCESS = subprocess.Popen(
            ["python", AI_BRAIN_PATH],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        messagebox.showinfo("AI Brain", "AI Brain started.")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to start AI Brain:\n{e}")


def stop_brain_safely():
    global AI_BRAIN_PROCESS

    if AI_BRAIN_PROCESS is None:
        messagebox.showinfo("AI Brain", "AI Brain is not running.")
        return

    try:
        AI_BRAIN_PROCESS.terminate()
        AI_BRAIN_PROCESS.wait(timeout=5)
        AI_BRAIN_PROCESS = None
        messagebox.showinfo("AI Brain", "AI Brain stopped safely.")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to stop AI Brain safely:\n{e}")


def pause_brain():
    global AI_BRAIN_PROCESS, AI_BRAIN_PAUSED

    if AI_BRAIN_PROCESS is None:
        messagebox.showinfo("AI Brain", "AI Brain is not running.")
        return

    if AI_BRAIN_PAUSED:
        messagebox.showinfo("AI Brain", "AI Brain is already paused.")
        return

    try:
        os.kill(AI_BRAIN_PROCESS.pid, signal.SIGSTOP)
        AI_BRAIN_PAUSED = True
        messagebox.showinfo("AI Brain", "AI Brain paused.")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to pause AI Brain:\n{e}")


def resume_brain():
    global AI_BRAIN_PROCESS, AI_BRAIN_PAUSED

    if AI_BRAIN_PROCESS is None:
        messagebox.showinfo("AI Brain", "AI Brain is not running.")
        return

    if not AI_BRAIN_PAUSED:
        messagebox.showinfo("AI Brain", "AI Brain is not paused.")
        return

    try:
        os.kill(AI_BRAIN_PROCESS.pid, signal.SIGCONT)
        AI_BRAIN_PAUSED = False
        messagebox.showinfo("AI Brain", "AI Brain resumed.")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to resume AI Brain:\n{e}")


# ---------------------------------------------------------
# GUI INTERFACE
# ---------------------------------------------------------

def launch_gui():
    window = tk.Tk()
    window.title("AI Brain Control Panel")
    window.geometry("300x260")

    tk.Label(window, text="AI Brain Command Module", font=("Arial", 14)).pack(pady=10)

    tk.Button(window, text="Start AI Brain", width=25, command=start_brain).pack(pady=5)
    tk.Button(window, text="Pause AI Brain", width=25, command=pause_brain).pack(pady=5)
    tk.Button(window, text="Resume AI Brain", width=25, command=resume_brain).pack(pady=5)
    tk.Button(window, text="Safely Stop AI Brain", width=25, command=stop_brain_safely).pack(pady=5)

    window.mainloop()


# ---------------------------------------------------------
# MAIN ENTRY (optional)
# ---------------------------------------------------------

if __name__ == "__main__":
    launch_gui()
