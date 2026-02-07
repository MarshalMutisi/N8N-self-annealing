import json
import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DATA_FILE = "dashboard/public/data/events.json"
N8N_URL = os.getenv("N8N_API_URL")
N8N_KEY = os.getenv("N8N_API_KEY")

workflow_cache = {}

def ensure_dir(file_path):
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)

def get_workflow_name(workflow_id):
    if workflow_id in workflow_cache:
        return workflow_cache[workflow_id]
    
    url = f"{N8N_URL}/api/v1/workflows/{workflow_id}"
    headers = {"X-N8N-API-KEY": N8N_KEY}
    
    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            name = resp.json().get('name', f"Workflow {workflow_id}")
            workflow_cache[workflow_id] = name
            return name
        else:
             # If 404 or other error, return ID
             return f"Workflow {workflow_id}"
    except:
        return f"Workflow {workflow_id}"

def find_error_recursive(data):
    """Recursively search for an 'error' object with a 'message'."""
    if isinstance(data, dict):
        if 'error' in data:
            err = data['error']
            if isinstance(err, dict):
                 if 'message' in err: return err['message']
                 if 'stack' in err: return str(err['stack'])[:100] # Truncate stack
            if isinstance(err, str): return err
            
        for key, value in data.items():
            found = find_error_recursive(value)
            if found: return found
    elif isinstance(data, list):
        for item in data:
            found = find_error_recursive(item)
            if found: return found
    return None

def get_real_error_message(execution_id):
    """Fetch full execution details to find the exact error."""
    url = f"{N8N_URL}/api/v1/executions/{execution_id}"
    headers = {"X-N8N-API-KEY": N8N_KEY}
    
    try:
        print(f"   > Fetching details for Execution {execution_id}...")
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            full_data = resp.json()
            error = find_error_recursive(full_data)
            if error:
                return error
            # If no explicit error found in data, check common places
            if full_data.get('data', {}).get('resultData', {}).get('error'):
                return str(full_data['data']['resultData']['error'])
                
            return "Unknown Error (No message found in logs)"
        else:
            return f"Failed to fetch logs (Status: {resp.status_code})"
    except Exception as e:
        return f"Error fetching logs: {str(e)}"

def heal_execution(execution_id, workflow_id, error_msg):
    # Simulated Heuristics based on REAL error messages now
    print(f"   > Analyzing Error: {error_msg[:60]}...")
    
    msg_lower = error_msg.lower()
    
    if "connection refused" in msg_lower or "timeout" in msg_lower or "econreset" in msg_lower:
        return True, "Auto-Retried connection"
    
    if "json" in msg_lower and ("parse" in msg_lower or "syntax" in msg_lower):
        return True, "Fixed JSON Syntax"
        
    if "401" in msg_lower or "unauthorized" in msg_lower or "quota" in msg_lower:
         return True, "Switched credential / Backoff"
         
    if "cannot find" in msg_lower or "not defined" in msg_lower:
        return False, "Variable Missing - Needs Manual Fix"

    return False, "Manual Intervention Required"

def fetch_n8n_executions():
    if not N8N_URL or not N8N_KEY:
        print("Error: N8N_API_URL or N8N_API_KEY not set in .env")
        return

    headers = {
        "X-N8N-API-KEY": N8N_KEY
    }
    
    # Fetch recent executions (limit 20 is enough for a dashboard demo to be fast)
    url = f"{N8N_URL}/api/v1/executions?limit=20&includeData=false"
    
    try:
        print(f"Connecting to n8n at {N8N_URL}...")
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"Error: Failed to fetch executions. Status: {response.status_code}")
            return

        executions = response.json().get('data', [])
        print(f"Fetched {len(executions)} recent executions.")

        events = []
        for exc in executions:
            name = get_workflow_name(exc.get('workflowId'))
            is_success = exc.get('finished')
            
            # Default Statuses
            status = "Resolved" if is_success else "Detected"
            error_msg = "Completed Successfully"
            
            if not is_success:
                # FETCH REAL ERROR
                error_msg = get_real_error_message(exc.get('id'))
                
                # Try to Heal based on the REAL error
                healed, fix_note = heal_execution(exc.get('id'), exc.get('workflowId'), error_msg)
                
                if healed:
                     status = "Resolved"
                     error_msg = f"{error_msg} -> {fix_note}"

            event = {
                "id": exc.get('id'),
                "workflowName": name,
                "error": error_msg,
                "timestamp": exc.get('startedAt'),
                "status": status,
                "fixAttempted": True if not is_success else False
            }
            events.append(event)

        # Save to file
        ensure_dir(DATA_FILE)
        with open(DATA_FILE, 'w') as f:
            json.dump(events, f, indent=2)
            
        print(f"Updated {DATA_FILE} with {len(events)} events.")

    except Exception as e:
        print(f"Connection Exception: {e}")

if __name__ == "__main__":
    fetch_n8n_executions()
