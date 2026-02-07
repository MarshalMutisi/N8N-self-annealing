"""
Test script for the agentic self-annealing system.
This script helps verify that the system is working correctly.
"""

import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

N8N_URL = os.getenv("N8N_API_URL")
N8N_KEY = os.getenv("N8N_API_KEY")


def test_n8n_connection():
    """Test if we can connect to n8n API."""
    print("=" * 60)
    print("Testing n8n Connection...")
    print("=" * 60)
    
    if not N8N_URL or not N8N_KEY:
        print("[FAIL] ERROR: N8N_API_URL or N8N_API_KEY not set in .env")
        return False
    
    headers = {"X-N8N-API-KEY": N8N_KEY}
    url = f"{N8N_URL}/api/v1/workflows"
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            workflows = resp.json().get('data', [])
            print(f"[OK] Connected to n8n successfully!")
            print(f"   Found {len(workflows)} workflows")
            return True
        else:
            print(f"[FAIL] Failed to connect. Status: {resp.status_code}")
            print(f"   Response: {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"[FAIL] Connection error: {str(e)}")
        return False


def test_fetch_executions():
    """Test if we can fetch executions."""
    print("\n" + "=" * 60)
    print("Testing Execution Fetching...")
    print("=" * 60)
    
    headers = {"X-N8N-API-KEY": N8N_KEY}
    url = f"{N8N_URL}/api/v1/executions?limit=5&includeData=false"
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            executions = resp.json().get('data', [])
            print(f"[OK] Successfully fetched {len(executions)} recent executions")
            
            if executions:
                print("\n   Recent executions:")
                for exc in executions[:3]:
                    status = "[OK] Success" if exc.get('finished') else "[FAIL] Failed"
                    print(f"   - {status}: Execution {exc.get('id')[:8]}... (Workflow: {exc.get('workflowId')[:8]}...)")
            else:
                print("   [INFO] No executions found. Run some workflows in n8n first.")
            
            return True
        else:
            print(f"[FAIL] Failed to fetch executions. Status: {resp.status_code}")
            return False
    except Exception as e:
        print(f"[FAIL] Error: {str(e)}")
        return False


def test_heal_log():
    """Test if heal log file exists and is readable."""
    print("\n" + "=" * 60)
    print("Testing Heal Log...")
    print("=" * 60)
    
    log_file = ".tmp/heal_log.json"
    
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r') as f:
                log = json.load(f)
            print(f"[OK] Heal log exists with {len(log)} entries")
            if log:
                print("\n   Recent healing attempts:")
                for entry in log[-3:]:
                    status = "[OK]" if entry.get('success') else "[WARN]"
                    print(f"   {status} {entry.get('workflow_name', 'Unknown')} - {entry.get('heal_status', 'unknown')}")
            return True
        except Exception as e:
            print(f"[WARN] Log file exists but couldn't read: {str(e)}")
            return False
    else:
        print("[INFO] Heal log doesn't exist yet (will be created on first healing attempt)")
        return True


def test_imports():
    """Test if all required modules can be imported."""
    print("\n" + "=" * 60)
    print("Testing Imports...")
    print("=" * 60)
    
    try:
        import execution.agentic_healer
        print("[OK] agentic_healer module imports successfully")
        
        # Test if key functions exist
        from execution.agentic_healer import monitor_and_heal, heal_execution
        print("[OK] Key functions are accessible")
        
        return True
    except ImportError as e:
        print(f"[FAIL] Import error: {str(e)}")
        return False
    except Exception as e:
        print(f"[FAIL] Error: {str(e)}")
        return False


def show_testing_instructions():
    """Show instructions for manual testing."""
    print("\n" + "=" * 60)
    print("Manual Testing Instructions")
    print("=" * 60)
    print("""
To test the agentic healer with real failures:

1. START THE AGENTIC HEALER:
   python start_agentic_healer.py
   
   (Keep this running in one terminal)

2. CREATE A FAILED WORKFLOW IN N8N:
   
   Option A - Syntax Error (Auto-fixable):
   - Create a new workflow in n8n
   - Add a "Code" node
   - Add JavaScript with a syntax error, e.g.:
     const data = {name: "test"];  // Missing closing brace
   - Save and execute the workflow
   
   Option B - Connection Error (Auto-retry):
   - Create a workflow with an HTTP Request node
   - Point it to an invalid URL or unreachable service
   - Execute the workflow
   
   Option C - Authentication Error (Explained):
   - Create a workflow with an API call
   - Use invalid/expired credentials
   - Execute the workflow

3. WATCH THE AGENTIC HEALER:
   - The healer checks every 30 seconds
   - You should see output like:
     [DETECTED] Failure: My Workflow (Execution: abc123)
     Error: SyntaxError: Unexpected token...
     [HEALING] Agentic healing in progress...
     [OK] Fixed code in nodes: Code Node 1 (Published to n8n)

4. CHECK THE LOGS:
   - View .tmp/heal_log.json to see all healing attempts
   - Check n8n to verify workflows were actually fixed

5. VERIFY IN N8N:
   - Open the workflow in n8n
   - Check if syntax errors were fixed
   - Check if the workflow was republished
   - Try executing again to see if it works
""")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("   Agentic Self-Annealing System - Test Suite")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("n8n Connection", test_n8n_connection()))
    results.append(("Execution Fetching", test_fetch_executions()))
    results.append(("Heal Log", test_heal_log()))
    results.append(("Module Imports", test_imports()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"   {status}: {test_name}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n[OK] All tests passed! System is ready to use.")
        print("\nNext step: Start the agentic healer with:")
        print("   python start_agentic_healer.py")
    else:
        print("\n[WARN] Some tests failed. Please fix the issues above.")
    
    # Show manual testing instructions
    show_testing_instructions()


if __name__ == "__main__":
    main()

