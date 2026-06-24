"""
AI_Activities_Start_Safely_Stop.py
Location: C:\Users\verbr\startup

Handles safe start, pause, resume, and stop operations for AI Brain.
Now includes live output streaming for GUI monitoring.
"""

import subprocess
import threading
import queue
import os
import signal

AI_BRAIN_PROCESS = None
AI_BRAIN_QUEUE = queue.Queue()
AI_BRAIN_PATH = os.path.join(os.path.dirname(__file__), "AI_Brain.py")

def _capture_output():
    """Continuously read AI Brain output and push to queue."""
    global AI_BRAIN_PROCESS
    for line in AI_BRAIN_PROCESS.stdout:
        AI_BRAIN_QUEUE.put(line.strip())

def start_brain():
    """Start AI Brain process and begin capturing live output."""
    global AI_BRAIN_PROCESS
    if AI_BRAIN_PROCESS is None or AI_BRAIN_PROCESS.poll() is not None:
        AI_BRAIN_PROCESS = subprocess.Popen(
            ["python", AI_BRAIN_PATH],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        threading.Thread(target=_capture_output, daemon=True).start()

def pause_brain():
    """Pause AI Brain simulation."""
    global AI_BRAIN_PROCESS
    if AI_BRAIN_PROCESS:
        AI_BRAIN_PROCESS.send_signal(signal.SIGSTOP)

def resume_brain():
    """Resume AI Brain simulation."""
    global AI_BRAIN_PROCESS
    if AI_BRAIN_PROCESS:
        AI_BRAIN_PROCESS.send_signal(signal.SIGCONT)

def stop_brain_safely():
    """Safely stop AI Brain process."""
    global AI_BRAIN_PROCESS
    if AI_BRAIN_PROCESS:
        AI_BRAIN_PROCESS.terminate()
        AI_BRAIN_PROCESS.wait(timeout=5)
        AI_BRAIN_PROCESS = None

def get_live_status():
    """Return latest live output line from AI Brain."""
    try:
        return AI_BRAIN_QUEUE.get_nowait()
    except queue.Empty:
        return None
