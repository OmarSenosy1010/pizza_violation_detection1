"""
run_all.py
Orchestrates the workflow: ROI selection, then launches detection and storage services in separate windows.
"""
import subprocess
import time
import sys
import os

# Script paths
ROI_SCRIPT       = "C:/Users/Omar/Desktop/pizza_violation_detection1/detection_service/roi_selector.py"
DETECTION_SCRIPT = "C:/Users/Omar/Desktop/pizza_violation_detection1/detection_service/detection.py"
STORAGE_SCRIPT   = "C:/Users/Omar/Desktop/pizza_violation_detection1/detection_service/storage_db.py"

def run_script(script_path, wait=True):
    """
    Runs a Python script. If wait=True, waits for it to finish (used for ROI selection).
    If wait=False, runs it in a new console window (used for services).
    """
    if wait:
        subprocess.run([sys.executable, script_path], check=True)
    else:
        subprocess.Popen([sys.executable, script_path],
                         creationflags=subprocess.CREATE_NEW_CONSOLE)

def main():
    """
    Main workflow: select ROIs, then launch detection and storage services.
    """
    print("🔷 Step 1: Select ROIs manually...")
    run_script(ROI_SCRIPT, wait=True)

    print("✅ ROIs saved.\n🔷 Step 2: Launching detection and storage services...")
    time.sleep(1)

    # Launch detection & storage in separate windows
    run_script(DETECTION_SCRIPT, wait=False)
    time.sleep(1)  # Small delay between scripts
    run_script(STORAGE_SCRIPT, wait=False)

    print("✅ All services started successfully.")
    print("📺 Open your frontend or check logs in terminals.")

if __name__ == "__main__":
    main()
