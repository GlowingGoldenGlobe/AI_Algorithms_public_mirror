# ============================================================
#    █████╗ ██╗         █████╗  ██████╗██╗████████╗
#   ██╔══██╗██║        ██╔══██╗██╔════╝██║╚══██╔══╝
#   ███████║██║        ███████║██║     ██║   ██║   
#   ██╔══██║██║        ██╔══██║██║     ██║   ██║   
#   ██║  ██║███████╗   ██║  ██║╚██████╗██║   ██║   
#   ╚═╝  ╚═╝╚══════╝   ╚═╝  ╚═╝ ╚═════╝╚═╝   ╚═╝   
# ------------------------------------------------------------
#                 AI Activities in Progress
# ------------------------------------------------------------

import os
import json
import subprocess
import time
from colorama import Fore, Style, init

init(autoreset=True)

CONFIG_FILE = "config.json"


def log_info(msg: str):
    print(Fore.CYAN + "[INFO] " + Style.RESET_ALL + msg)


def log_warning(msg: str):
    print(Fore.YELLOW + "[WARNING] " + Style.RESET_ALL + msg)


def log_error(msg: str):
    print(Fore.RED + "[ERROR] " + Style.RESET_ALL + msg)


def load_config():
    """Load configuration from JSON file."""
    if not os.path.exists(CONFIG_FILE):
        log_error(f"Missing configuration file: {CONFIG_FILE}")
        return None

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def check_process_running(process_name: str) -> bool:
    """Check if a process is running and display progress."""
    log_info(f"Checking if '{process_name}' is running...")

    for i in range(5):
        progress_bar = f"[{'=' * (i + 1)}{' ' * (4 - i)}] {((i + 1) * 20)}%"
        print(Fore.MAGENTA + f"Progress: {progress_bar}" + Style.RESET_ALL)
        time.sleep(0.2)

    result = subprocess.run(["tasklist"], capture_output=True, text=True)
    return process_name.lower() in result.stdout.lower()


def terminate_process(pid: int):
    """Terminate a process by PID."""
    try:
        os.kill(pid, 9)
        log_warning(f"Terminated process with PID {pid}")
    except Exception as e:
        log_error(f"Failed to terminate PID {pid}: {e}")


def main():
    config = load_config()
    if not config:
        return

    process_name = config.get("process_name", "python.exe")

    if check_process_running(process_name):
        log_info(f"Process '{process_name}' is active.")
    else:
        log_warning(f"Process '{process_name}' not found.")


if __name__ == "__main__":
    main()
