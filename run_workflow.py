import os
import subprocess
import sys
import threading
import time


def start_backend():
    print(">>> Starting FastAPI Backend on Port 8000...")
    # Using 'execution.api:app' assumes running from root
    subprocess.run([sys.executable, "-m", "uvicorn", "execution.api:app", "--host", "0.0.0.0", "--port", "8000", "--reload"])

def start_healer():
    print(">>> Starting Agentic Healer...")
    # Run the healer script as a module or script
    # Run the healer script as a module to ensure imports work
    subprocess.run([sys.executable, "-m", "execution.agentic_healer"])

def start_frontend():
    print(">>> Starting Next.js Frontend on Port 3000...")
    os.chdir("dashboard_next")
    # Windows requires shell=True for npm, typically
    subprocess.run("npm run dev", shell=True)

def main():
    print("="*60)
    print("   n8n HEAS (Healing & Error Analysis System)")
    print("   Architecture: FastAPI (Py) + Next.js (TS) + n8n API + Agentic Healer")
    print("="*60)
    
    # Start Backend in a separate thread
    backend_thread = threading.Thread(target=start_backend)
    backend_thread.daemon = True
    backend_thread.start()

    # Start Healer in a separate thread
    healer_thread = threading.Thread(target=start_healer)
    healer_thread.daemon = True
    healer_thread.start()
    
    time.sleep(2) # Give backend a moment
    
    # Start Frontend in main thread (or separate, but let's block on one)
    start_frontend()

if __name__ == "__main__":
    main()
