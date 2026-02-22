import os
import json
import requests
from typing import Any, Dict, List, Optional
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

# Import shared core healer
try:
    from execution.core_healer import heal_workflow, get_workflow
except ImportError:
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from core_healer import heal_workflow, get_workflow

load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("N8N Healer")

N8N_URL = os.getenv("N8N_API_URL")
N8N_KEY = os.getenv("N8N_API_KEY")
HEADERS = {"X-N8N-API-KEY": N8N_KEY}

@mcp.tool()
def list_n8n_workflows() -> str:
    """
    List all n8n workflows with their current status.
    Returns a formatted string containing workflow names and IDs.
    """
    url = f"{N8N_URL}/api/v1/workflows"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            workflows = resp.json().get("data", [])
            output = ["### N8N Workflows", ""]
            for wf in workflows:
                status = "🟢 Active" if wf.get("active") else "⚪ Inactive"
                output.append(f"- **{wf.get('name')}** (ID: `{wf.get('id')}`) {status}")
            return "\n".join(output)
        return f"Error fetching workflows: Status {resp.status_code}"
    except Exception as e:
        return f"Exception: {str(e)}"

@mcp.tool()
def get_failed_n8n_executions(limit: int = 10) -> str:
    """
    Get the most recent failed N8N executions.
    """
    url = f"{N8N_URL}/api/v1/executions?limit={limit}&includeData=false"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            executions = resp.json().get("data", [])
            failed = [e for e in executions if not e.get("finished", False)]
            
            if not failed:
                return "No failed executions detected in the last few runs."
                
            output = ["### Detected Failures", ""]
            for exc in failed:
                output.append(f"- **Execution ID:** `{exc.get('id')}`")
                output.append(f"  - **Workflow ID:** `{exc.get('workflowId')}`")
                output.append(f"  - **Started:** {exc.get('startedAt')}")
                output.append("")
            return "\n".join(output)
        return f"Error fetching executions: Status {resp.status_code}"
    except Exception as e:
        return f"Exception: {str(e)}"

@mcp.tool()
def fix_n8n_workflow(workflow_id: str, execution_id: str, error_message: str) -> str:
    """
    Triggers the self-healing logic for a specific failed workflow.
    It will attempt deterministic fixes first, then escalate to AI (Gemini).
    """
    try:
        result = heal_workflow(workflow_id, execution_id, error_message)
        status_emoji = "✅" if result["status"] == "resolved" else "🔍"
        return f"{status_emoji} **Heal Status:** {result['status'].upper()}\n\n**Result:** {result['message']}"
    except Exception as e:
        return f"❌ Error during healing process: {str(e)}"

@mcp.tool()
def get_workflow_details(workflow_id: str) -> str:
    """
    Returns the full JSON structure of an n8n workflow for analysis.
    """
    workflow = get_workflow(workflow_id)
    if workflow:
        return json.dumps(workflow, indent=2)
    return f"Could not find workflow with ID: {workflow_id}"

if __name__ == "__main__":
    # In FastMCP, run() handles stdio by default when called as a script
    mcp.run()
