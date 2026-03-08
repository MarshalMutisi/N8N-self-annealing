from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Enable CORS for development and Render deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Shared Logic from core_healer ---
from execution.core_healer import heal_workflow, get_workflow


# --- Request Models ---
class ConnectRequest(BaseModel):
    n8nUrl: str
    n8nApiKey: str
    geminiApiKey: Optional[str] = None

class HealRequest(BaseModel):
    executionId: str
    workflowId: str
    error: str
    n8nUrl: str
    n8nApiKey: str
    geminiApiKey: Optional[str] = None

class EventsRequest(BaseModel):
    n8nUrl: str
    n8nApiKey: str

HEAL_LOG_FILE = ".tmp/heal_log.json"

def load_heal_log():
    if os.path.exists(HEAL_LOG_FILE):
        with open(HEAL_LOG_FILE, 'r') as f:
            return json.load(f)
    return []

workflow_cache = {}

def get_workflow_name(workflow_id, n8n_url, n8n_key):
    cache_key = f"{n8n_url}:{workflow_id}"
    if cache_key in workflow_cache:
        return workflow_cache[cache_key]
    
    workflow = get_workflow(workflow_id, n8n_url, n8n_key)
    if workflow:
        name = workflow.get('name', f"Workflow {workflow_id}")
        workflow_cache[cache_key] = name
        return name
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

def get_real_error_message(execution_id, n8n_url, n8n_key):
    url = f"{n8n_url}/api/v1/executions/{execution_id}?includeData=true"
    headers = {"X-N8N-API-KEY": n8n_key}
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

@app.get("/api/health")
def health_check():
    """Health check for Render and uptime monitors."""
    return {"status": "ok", "service": "HEAS - N8N Self-Annealing System"}


@app.post("/api/connect")
def test_connection(req: ConnectRequest):
    """Test if the provided n8n credentials are valid."""
    headers = {"X-N8N-API-KEY": req.n8nApiKey}
    try:
        resp = requests.get(f"{req.n8nUrl}/api/v1/workflows?limit=1", headers=headers, timeout=10)
        if resp.status_code == 200:
            workflows = resp.json().get('data', [])
            return {"status": "connected", "message": f"Connected! Found {len(workflows)}+ workflows."}
        elif resp.status_code == 401:
            raise HTTPException(status_code=401, detail="Invalid API key.")
        else:
            raise HTTPException(status_code=resp.status_code, detail=f"n8n returned status {resp.status_code}")
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=502, detail=f"Could not reach n8n at {req.n8nUrl}. Is the URL correct?")
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Connection to n8n timed out.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/events")
def get_events(req: EventsRequest):
    """Fetch workflow executions from the visitor's n8n instance."""
    headers = {"X-N8N-API-KEY": req.n8nApiKey}
    url = f"{req.n8nUrl}/api/v1/executions?limit=25&includeData=false"

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
             raise HTTPException(status_code=500, detail=f"n8n API Error: {response.status_code}")
        
        executions = response.json().get('data', [])
        events = []
        seen_workflows = set()
        
        for exc in executions:
            workflow_id = exc.get('workflowId')
            
            # Only process the LATEST execution for each workflow
            if workflow_id in seen_workflows:
                continue
            seen_workflows.add(workflow_id)
            
            name = get_workflow_name(workflow_id, req.n8nUrl, req.n8nApiKey)
            exec_id = exc.get('id')
            
            n8n_status = exc.get('status', 'unknown')
            is_finished = exc.get('finished', False)
            
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
                    error_msg = get_real_error_message(exec_id, req.n8nUrl, req.n8nApiKey)
                except:
                    error_msg = "Execution Stopped/Crashed (Could not fetch details)"

            events.append({
                "id": exec_id,
                "workflowId": workflow_id,
                "workflowName": name,
                "error": error_msg,
                "timestamp": exc.get('startedAt'),
                "status": status,
                "fixAttempted": fix_attempted
            })
        return events
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/heals")
def get_heals():
    """Return the history of autonomous healing attempts."""
    try:
        return load_heal_log()
    except Exception as e:
        return []

@app.post("/api/heal")
def heal_event(request: HealRequest):
    """Heal a workflow using the visitor's n8n credentials + visitor's Gemini key."""
    try:
        result = heal_workflow(
            request.workflowId,
            request.executionId,
            request.error,
            request.n8nUrl,
            request.n8nApiKey,
            request.geminiApiKey
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        return {"status": "explained", "message": f"Error during healing: {str(e)}"}


# --- Static File Serving (for Render monolith) ---
# Mount the Next.js static export if it exists (production build)
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static_dashboard")
if os.path.isdir(STATIC_DIR):
    # Serve index.html at root
    @app.get("/")
    async def serve_root():
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))
    
    # Serve static files for everything else
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
