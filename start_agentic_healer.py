"""
Quick start script for the agentic self-annealing system.
This runs the agentic healer in a separate process.
"""

import subprocess
import sys
import os

def main():
    print("=" * 60)
    print("   🤖 Starting Agentic Self-Annealing System for n8n")
    print("=" * 60)
    print("\nThe agentic healer will:")
    print("  • Continuously monitor n8n for workflow failures")
    print("  • Automatically detect and heal errors")
    print("  • Log all attempts to .tmp/heal_log.json")
    print("\nPress Ctrl+C to stop.\n")
    
    # Run the agentic healer
    script_path = os.path.join("execution", "agentic_healer.py")
    subprocess.run([sys.executable, script_path])

if __name__ == "__main__":
    main()

