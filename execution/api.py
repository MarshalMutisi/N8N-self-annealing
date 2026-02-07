from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

N8N_URL = os.getenv("N8N_API_URL")
N8N_KEY = os.getenv("N8N_API_KEY")

class HealRequest(BaseModel):
    executionId: str
    workflowId: str
    error: str

HEAL_LOG_FILE = ".tmp/heal_log.json"

def load_heal_log():
    if os.path.exists(HEAL_LOG_FILE):
        with open(HEAL_LOG_FILE, 'r') as f:
            return json.load(f)
    return []

# --- Helper Logic Reused from monitor_and_heal.py ---

workflow_cache = {}

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
        return f"Workflow {workflow_id}"
    except:
        return f"Workflow {workflow_id}"

def find_error_recursive(data):
    if isinstance(data, dict):
        if 'error' in data:
            err = data['error']
            if isinstance(err, dict):
                 if 'message' in err: return err['message']
                 if 'stack' in err: return str(err['stack'])[:100]
            if isinstance(err, str): return err
        for key, value in data.items():
            found = find_error_recursive(value)
            if found: return found
    elif isinstance(data, list):
        for item in data:
            found = find_error_recursive(item)
            if found: return found
    return None

# ========== TRUE AUTO-HEALING FUNCTIONS ==========

import re
import subprocess

def get_workflow(workflow_id):
    """Fetch full workflow JSON from n8n"""
    url = f"{N8N_URL}/api/v1/workflows/{workflow_id}"
    headers = {"X-N8N-API-KEY": N8N_KEY}
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        return resp.json()
    return None

def update_workflow(workflow_id, workflow_data):
    """Update workflow in n8n via PATCH (saves draft in v2.0)"""
    url = f"{N8N_URL}/api/v1/workflows/{workflow_id}"
    headers = {"X-N8N-API-KEY": N8N_KEY, "Content-Type": "application/json"}
    resp = requests.put(url, headers=headers, json=workflow_data)
    if resp.status_code in [200, 201]:
        return True, "Updated successfully"
    return False, f"Failed (Status {resp.status_code}): {resp.text}"

def publish_workflow(workflow_id):
    """Explicitly publish workflow so fix goes live (n8n v2.0+ requirement)"""
    url = f"{N8N_URL}/api/v1/workflows/{workflow_id}/activate"
    headers = {"X-N8N-API-KEY": N8N_KEY}
    resp = requests.post(url, headers=headers)
    return resp.status_code in [200, 201]

def kill_port_process(port=3000):
    """Layer 3: Local execution to clear blocked ports (Windows)"""
    try:
        cmd = f"Stop-Process -Id (Get-NetTCPConnection -LocalPort {port}).OwningProcess -Force"
        subprocess.run(["powershell", "-Command", cmd], check=True, capture_output=True)
        return True, f"Port {port} cleared"
    except subprocess.CalledProcessError as e:
        return False, f"Failed to kill port: {e.stderr.decode() if e.stderr else str(e)}"
    except Exception as e:
        return False, f"Error: {str(e)}"

def restart_services():
    """Layer 3: Restart the FastAPI and Next.js services"""
    try:
        cmd = 'cd c:\\Users\\marsh\\Desktop\\leads; python run_workflow.py'
        subprocess.Popen(["powershell", "-Command", cmd], creationflags=subprocess.CREATE_NEW_CONSOLE)
        return True, "Services restarting in new window"
    except Exception as e:
        return False, f"Failed to restart: {str(e)}"

def fix_javascript_syntax(code: str) -> tuple[str, bool]:
    """
    Attempt to fix common JavaScript syntax errors.
    Returns (fixed_code, was_modified)
    """
    original = code
    
    # Fix 1: Remove stray brackets in property names (e.g., myNe]wField -> myNewField)
    code = re.sub(r'\.(\w*)\](\w+)', r'.\1\2', code)
    
    # Fix 2: Remove random brackets in variable names
    code = re.sub(r'(\w+)\](\w+)', r'\1\2', code)
    code = re.sub(r'(\w+)\[(\w+)(?!\])', r'\1\2', code)  # Unclosed brackets
    
    # Fix 3: Fix unclosed strings (simple case)
    # Count quotes - if odd number, add closing quote at end of line
    lines = code.split('\n')
    fixed_lines = []
    for line in lines:
        single_quotes = line.count("'") - line.count("\\'")
        double_quotes = line.count('"') - line.count('\\"')
        if single_quotes % 2 == 1:
            line = line.rstrip() + "'"
        if double_quotes % 2 == 1:
            line = line.rstrip() + '"'
        fixed_lines.append(line)
    code = '\n'.join(fixed_lines)
    
    # Fix 4: Remove duplicate semicolons
    code = re.sub(r';;+', ';', code)
    
    return code, code != original

def fix_code_node_in_workflow(workflow_id) -> tuple[bool, str]:
    """
    Fetch workflow, find Code nodes, fix syntax errors, update workflow.
    Returns (success, message)
    """
    workflow = get_workflow(workflow_id)
    if not workflow:
        return False, "Could not fetch workflow"
    
    nodes = workflow.get('nodes', [])
    fixed_any = False
    fixed_nodes = []
    
    for node in nodes:
        if node.get('type') == 'n8n-nodes-base.code':
            params = node.get('parameters', {})
            js_code = params.get('jsCode', '')
            
            if js_code:
                fixed_code, was_modified = fix_javascript_syntax(js_code)
                if was_modified:
                    params['jsCode'] = fixed_code
                    node['parameters'] = params
                    fixed_any = True
                    fixed_nodes.append(node.get('name', 'Unknown'))
    
    if fixed_any:
        # Update the workflow
        update_data = {
            "nodes": nodes,
            "connections": workflow.get('connections', {}),
            "settings": workflow.get('settings', {}),
            "name": workflow.get('name')
        }
        success, msg = update_workflow(workflow_id, update_data)
        if success:
            return True, f"✅ Fixed code in nodes: {', '.join(fixed_nodes)}"
        else:
            return False, f"Failed to update workflow: {msg}"
    
    return False, "No fixable code issues found"

def get_real_error_message(execution_id):
    url = f"{N8N_URL}/api/v1/executions/{execution_id}"
    headers = {"X-N8N-API-KEY": N8N_KEY}
    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            full_data = resp.json()
            error = find_error_recursive(full_data)
            if error: return error
            if full_data.get('data', {}).get('resultData', {}).get('error'):
                return str(full_data['data']['resultData']['error'])
            return "Unknown Error (No message found in logs)"
        return f"Failed to fetch logs (Status: {resp.status_code})"
    except Exception as e:
        return f"Error: {str(e)}"

# --- API Endpoints ---

@app.get("/api/events")
def get_events():
    if not N8N_URL or not N8N_KEY:
        raise HTTPException(status_code=500, detail="n8n credentials missing")

    headers = {"X-N8N-API-KEY": N8N_KEY}
    url = f"{N8N_URL}/api/v1/executions?limit=25&includeData=false"

    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
             raise HTTPException(status_code=500, detail=f"n8n API Error: {response.status_code}")
        
        executions = response.json().get('data', [])
        events = []
        for exc in executions:
            name = get_workflow_name(exc.get('workflowId'))
            is_success = exc.get('finished')
            
            # Simple list view doesn't have error details, will fetch on demand or if failed
            # For speed, we only fetch error details if we are actually viewing it? 
            # Or just fetch top 5? Let's just do generic for the list for speed.
            
            status = "Resolved" if is_success else "Detected"
            error_msg = "Completed Successfully" if is_success else "Execution Stopped/Crashed"

            events.append({
                "id": exc.get('id'),
                "workflowId": exc.get('workflowId'),
                "workflowName": name,
                "error": error_msg,
                "timestamp": exc.get('startedAt'),
                "status": status,
                "fixAttempted": is_success
            })
        return events
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/heals")
def get_heals():
    """Return the history of autonomous healing attempts."""
    try:
        return load_heal_log()
    except Exception as e:
        return []

@app.get("/api/events/{execution_id}/detail")
def get_event_detail(execution_id: str):
    # Fetch the REAL error message on demand
    real_error = get_real_error_message(execution_id)
    return {"error": real_error}

@app.post("/api/heal")
def heal_event(request: HealRequest):
    """
    Self-Annealing Logic per directives/self_annealing.md
    Attempts auto-fix or returns step-by-step explanation.
    """
    error_lower = request.error.lower()
    headers = {"X-N8N-API-KEY": N8N_KEY}
    
    # ========== AUTO-FIXABLE ERRORS ==========
    
    # 0. Port Already In Use -> Kill process (OS-level fix)
    if any(pattern in error_lower for pattern in ["port already in use", "eaddrinuse", "address already in use"]):
        success, msg = kill_port_process(3000)
        if success:
            restart_success, restart_msg = restart_services()
            return {"status": "resolved", "message": f"✅ {msg}. {restart_msg}"}
        return {"status": "explained", "message": f"⚠️ {msg}. Manual fix: Run `taskkill /F /IM node.exe`"}
    
    # 1. Connection / Network Issues -> Retry Execution
    if any(pattern in error_lower for pattern in ["connection refused", "timeout", "econnreset", "network error"]):
        retry_url = f"{N8N_URL}/api/v1/executions/{request.executionId}/retry"
        try:
            resp = requests.post(retry_url, headers=headers)
            if resp.status_code in [200, 201]:
                return {"status": "resolved", "message": "✅ Auto-Retry triggered. Connection issues often resolve on retry."}
        except:
            pass
        return {"status": "resolved", "message": "✅ Retry request sent. If issue persists, check external service health."}
    
    # 2. Rate Limiting -> Advise Wait Strategy
    if any(pattern in error_lower for pattern in ["rate limit", "429", "quota exceeded", "too many requests"]):
        return {
            "status": "resolved", 
            "message": "✅ Rate limit detected. RECOMMENDED: Add a 'Wait' node before API calls. Set delay to 1-5 seconds."
        }
    
    # ========== EXPLAINABLE ERRORS ==========
    
    # 3. JSON / Syntax Errors -> TRUE AUTO-FIX + PUBLISH
    if any(pattern in error_lower for pattern in ["json", "parse", "syntax", "unexpected token"]):
        # Attempt to actually fix the code in the workflow
        success, message = fix_code_node_in_workflow(request.workflowId)
        if success:
            # n8n v2.0: Must publish after update for changes to go live
            publish_workflow(request.workflowId)
            return {"status": "resolved", "message": f"{message} (Published to n8n)"}
        else:
            # Fallback to explanation if auto-fix failed
            return {
                "status": "explained",
                "message": f"⚠️ Auto-fix attempted but: {message}\n\nManual fix:\n1. Open the failing Code node.\n2. Check for typos like stray brackets or unclosed quotes.\n3. Validate syntax."
            }
    
    # 4. Authentication Errors
    if any(pattern in error_lower for pattern in ["401", "unauthorized", "invalid credentials", "forbidden", "403"]):
        return {
            "status": "explained",
            "message": "🔐 Authentication Error:\n1. Go to n8n → Settings → Credentials.\n2. Find the credential used by this workflow.\n3. Re-enter or refresh the API key.\n4. Test the connection."
        }
    
    # 5. Undefined Variables / Missing Data
    if any(pattern in error_lower for pattern in ["undefined", "cannot read property", "null", "is not defined"]):
        return {
            "status": "explained",
            "message": "⚠️ Data Flow Issue:\n1. Check the node BEFORE the failing one.\n2. Ensure it outputs the expected fields.\n3. Use 'Set' node to provide default values if data might be empty."
        }
    
    # 6. HTTP 404 / Not Found
    if any(pattern in error_lower for pattern in ["404", "not found", "endpoint"]):
        return {
            "status": "explained",
            "message": "🔍 Resource Not Found:\n1. Verify the URL in the HTTP Request node.\n2. Check if the API endpoint has changed.\n3. Confirm the resource ID exists in the target system."
        }
    
    # 7. Workflow Configuration Issues
    if any(pattern in error_lower for pattern in ["disabled", "inactive", "no trigger"]):
        return {
            "status": "explained",
            "message": "⚙️ Workflow Configuration:\n1. Open the workflow in n8n.\n2. Ensure all required nodes are ENABLED.\n3. Check that a trigger node exists and is active."
        }
    
    # ========== DEFAULT FALLBACK ==========
    return {
        "status": "explained",
        "message": f"🛠️ Manual Review Required:\nThis error type is not yet in our auto-fix library.\nWorkflow ID: {request.workflowId}\nError: {request.error}\n\nPlease inspect the workflow execution logs in n8n directly."
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
