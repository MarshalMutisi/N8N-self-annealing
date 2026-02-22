from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import requests
import json
from dotenv import load_dotenv
from execution.ai_healer import consult_gemini_for_fix

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

# --- Shared Logic from core_healer ---
from execution.core_healer import heal_workflow, get_workflow, get_workflow as get_workflow_detail

workflow_cache = {}

def get_workflow_name(workflow_id):
    if workflow_id in workflow_cache:
        return workflow_cache[workflow_id]
    
    workflow = get_workflow(workflow_id)
    if workflow:
        name = workflow.get('name', f"Workflow {workflow_id}")
        workflow_cache[workflow_id] = name
        return name
    return f"Workflow {workflow_id}"

def find_error_recursive(data):
    # This is still needed locally for scanning execution logs in get_events
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

def get_real_error_message(execution_id):
    url = f"{N8N_URL}/api/v1/executions/{execution_id}?includeData=true"
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
            exec_id = exc.get('id')
            
            # Check explicit status if available, fallback to finished bool
            n8n_status = exc.get('status', 'unknown')
            is_finished = exc.get('finished', False)
            
            # Default values
            status = "Detected"
            error_msg = "Unknown Error"
            fix_attempted = False

            if n8n_status == 'success' or (n8n_status == 'unknown' and is_finished):
                status = "Resolved"
                error_msg = "Completed Successfully"
                fix_attempted = True
            elif n8n_status in ['running', 'waiting']:
                status = "Running"
                error_msg = "Execution in progress..."
            else:
                status = "Detected"
                try:
                    error_msg = get_real_error_message(exec_id)
                except:
                    error_msg = "Execution Stopped/Crashed (Could not fetch details)"

            events.append({
                "id": exec_id,
                "workflowId": exc.get('workflowId'),
                "workflowName": name,
                "error": error_msg,
                "timestamp": exc.get('startedAt'),
                "status": status,
                "fixAttempted": fix_attempted
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
    Refactored to use shared core_healer logic.
    """
    try:
        result = heal_workflow(request.workflowId, request.executionId, request.error)
        return result
    except Exception as e:
        return {"status": "explained", "message": f"Error during healing: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
