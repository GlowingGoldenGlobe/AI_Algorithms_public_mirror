"""
AI_Activities_Start_Safely_Stop.py
Location: C:/Users/yerbr/startup

Automated command events for AI Brain lifecycle control.
Provides: start, safe stop, pause, resume.
Includes live output streaming for AI Brain, Metrics, Dashboard, and Monitor terminals.
"""

import subprocess
import os
import signal
import threading
import queue
from tkinter import messagebox

# ------------------------------------------------------------
# INTERNAL STATE
# ------------------------------------------------------------
AI_BRAIN_PROCESS = None
AI_METRICS_PROCESS = None
AI_DASHBOARD_PROCESS = None
AI_MONITOR_PROCESS = None
AI_BRAIN_PAUSED = False

LIVE_QUEUE = queue.Queue()

# ------------------------------------------------------------
# OUTPUT CAPTURE
# ------------------------------------------------------------
def _capture_output(process, label):
    """Capture output from any subprocess and tag it for GUI display."""
    for line in process.stdout:
        LIVE_QUEUE.put(f"[{label}] {line.strip()}")

def get_live_status():
    """Return latest line from any active subprocess."""
    try:
        return LIVE_QUEUE.get_nowait()
    except queue.Empty:
        return None

# ------------------------------------------------------------
# MAIN AI BRAIN CONTROL
# ------------------------------------------------------------
def start_brain():
    """Start the main AI Brain process."""
    global AI_BRAIN_PROCESS
    AI_BRAIN_PATH = os.path.join(os.path.dirname(__file__), "AI_Brain.py")

    if AI_BRAIN_PROCESS is not None and AI_BRAIN_PROCESS.poll() is None:
        messagebox.showinfo("AI Brain", "AI Brain is already running.")
        return

    try:
        AI_BRAIN_PROCESS = subprocess.Popen(
            ["python", AI_BRAIN_PATH],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        threading.Thread(target=_capture_output, args=(AI_BRAIN_PROCESS, "Brain"), daemon=True).start()
        messagebox.showinfo("AI Brain", "AI Brain started successfully.")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to start AI Brain:\n{e}")

def stop_brain_safely():
    """Safely stop the AI Brain process."""
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
    """Pause AI Brain simulation."""
    global AI_BRAIN_PROCESS, AI_BRAIN_PAUSED
    if AI_BRAIN_PROCESS is None:
        messagebox.showinfo("AI Brain", "AI Brain is not running.")
        return

    try:
        AI_BRAIN_PROCESS.send_signal(signal.SIGSTOP)
        AI_BRAIN_PAUSED = True
        messagebox.showwarning("AI Brain", "AI Brain paused.")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to pause AI Brain:\n{e}")

def resume_brain():
    """Resume AI Brain simulation."""
    global AI_BRAIN_PROCESS, AI_BRAIN_PAUSED
    if AI_BRAIN_PROCESS is None:
        messagebox.showinfo("AI Brain", "AI Brain is not running.")
        return

    try:
        AI_BRAIN_PROCESS.send_signal(signal.SIGCONT)
        AI_BRAIN_PAUSED = False
        messagebox.showinfo("AI Brain", "AI Brain resumed.")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to resume AI Brain:\n{e}")

# ------------------------------------------------------------
# ADDITIONAL TERMINALS
# ------------------------------------------------------------
def start_metrics():
    """Start AI Brain Metrics terminal."""
    global AI_METRICS_PROCESS
    METRICS_PATH = os.path.join(os.path.dirname(__file__), "AI_Brain_Metrics.py")

    try:
        AI_METRICS_PROCESS = subprocess.Popen(
            ["python", METRICS_PATH],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        threading.Thread(target=_capture_output, args=(AI_METRICS_PROCESS, "Metrics"), daemon=True).start()
        messagebox.showinfo("AI Metrics", "Metrics terminal started successfully.")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to start Metrics terminal:\n{e}")

def start_dashboard():
    """Start AI Brain Dashboard terminal."""
    global AI_DASHBOARD_PROCESS
    DASHBOARD_PATH = os.path.join(os.path.dirname(__file__), "AI_Brain_Dashboard.py")

    try:
        AI_DASHBOARD_PROCESS = subprocess.Popen(
            ["python", DASHBOARD_PATH],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        threading.Thread(target=_capture_output, args=(AI_DASHBOARD_PROCESS, "Dashboard"), daemon=True).start()
        messagebox.showinfo("AI Dashboard", "Dashboard terminal started successfully.")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to start Dashboard terminal:\n{e}")

def start_monitor():
    """Start AI Brain Monitor terminal."""
    global AI_MONITOR_PROCESS
    MONITOR_PATH = os.path.join(os.path.dirname(__file__), "AI_Brain_Monitor.py")

    try:
        AI_MONITOR_PROCESS = subprocess.Popen(
            ["python", MONITOR_PATH],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        threading.Thread(target=_capture_output, args=(AI_MONITOR_PROCESS, "Monitor"), daemon=True).start()
        messagebox.showinfo("AI Monitor", "Monitor terminal started successfully.")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to start Monitor terminal:\n{e}")
