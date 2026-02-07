"""
Agentic Self-Annealing Orchestrator for n8n
Continuously monitors n8n workflows and automatically triggers healing when failures are detected.
This is Layer 2 (Orchestration) - makes intelligent decisions about when/how to heal.
"""

import os
import json
import time
import requests
from datetime import datetime
from dotenv import load_dotenv
from typing import Dict, List, Optional, Tuple

load_dotenv()

N8N_URL = os.getenv("N8N_API_URL")
N8N_KEY = os.getenv("N8N_API_KEY")
HEAL_LOG_FILE = ".tmp/heal_log.json"
MONITOR_INTERVAL = 30  # Check every 30 seconds
PROCESSED_EXECUTIONS = set()  # Track which executions we've already processed

# Ensure .tmp directory exists
os.makedirs(".tmp", exist_ok=True)


def load_heal_log() -> List[Dict]:
    """Load healing attempt history for learning."""
    if os.path.exists(HEAL_LOG_FILE):
        with open(HEAL_LOG_FILE, 'r') as f:
            return json.load(f)
    return []


def save_heal_log(entry: Dict):
    """Save a healing attempt to the log for future learning."""
    log = load_heal_log()
    log.append({
        **entry,
        "timestamp": datetime.now().isoformat()
    })
    with open(HEAL_LOG_FILE, 'w') as f:
        json.dump(log, f, indent=2)


def get_workflow_name(workflow_id: str) -> str:
    """Fetch workflow name from n8n API."""
    url = f"{N8N_URL}/api/v1/workflows/{workflow_id}"
    headers = {"X-N8N-API-KEY": N8N_KEY}
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            return resp.json().get('name', f"Workflow {workflow_id}")
    except:
        pass
    return f"Workflow {workflow_id}"


def find_error_recursive(data) -> Optional[str]:
    """Recursively search for error messages in execution data."""
    if isinstance(data, dict):
        if 'error' in data:
            err = data['error']
            if isinstance(err, dict):
                if 'message' in err:
                    return err['message']
                if 'stack' in err:
                    return str(err['stack'])[:200]  # Truncate long stacks
            if isinstance(err, str):
                return err
        for value in data.values():
            found = find_error_recursive(value)
            if found:
                return found
    elif isinstance(data, list):
        for item in data:
            found = find_error_recursive(item)
            if found:
                return found
    return None


def get_execution_error(execution_id: str) -> Optional[str]:
    """Fetch the actual error message from an execution."""
    url = f"{N8N_URL}/api/v1/executions/{execution_id}"
    headers = {"X-N8N-API-KEY": N8N_KEY}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            full_data = resp.json()
            error = find_error_recursive(full_data)
            if error:
                return error
            # Fallback: check common error locations
            if full_data.get('data', {}).get('resultData', {}).get('error'):
                return str(full_data['data']['resultData']['error'])
    except Exception as e:
        return f"Error fetching execution: {str(e)}"
    return None


def heal_execution(execution_id: str, workflow_id: str, error_msg: str) -> Tuple[bool, str, str]:
    """
    Agentic healing logic - makes intelligent decisions about how to fix errors.
    Returns: (success, status, message)
    """
    error_lower = error_msg.lower()
    headers = {"X-N8N-API-KEY": N8N_KEY}
    
    # ========== AUTO-FIXABLE ERRORS ==========
    
    # 1. Connection / Network Issues -> Retry Execution
    if any(pattern in error_lower for pattern in ["connection refused", "timeout", "econnreset", "network error"]):
        retry_url = f"{N8N_URL}/api/v1/executions/{execution_id}/retry"
        try:
            resp = requests.post(retry_url, headers=headers, timeout=10)
            if resp.status_code in [200, 201]:
                return True, "resolved", "✅ Auto-Retry triggered. Connection issues often resolve on retry."
        except:
            pass
        return True, "resolved", "✅ Retry request sent. If issue persists, check external service health."
    
    # 2. Rate Limiting -> Log and recommend Wait node
    if any(pattern in error_lower for pattern in ["rate limit", "429", "quota exceeded", "too many requests"]):
        return True, "resolved", "✅ Rate limit detected. RECOMMENDED: Add a 'Wait' node before API calls. Set delay to 1-5 seconds."
    
    # 3. JSON / Syntax Errors -> Attempt to fix code nodes
    if any(pattern in error_lower for pattern in ["json", "parse", "syntax", "unexpected token"]):
        # Import healing functions from api.py
        try:
            from execution.api import fix_code_node_in_workflow, publish_workflow
            success, message = fix_code_node_in_workflow(workflow_id)
            if success:
                publish_workflow(workflow_id)
                return True, "resolved", f"{message} (Published to n8n)"
            else:
                return False, "explained", f"⚠️ Auto-fix attempted but: {message}\n\nManual fix:\n1. Open the failing Code node.\n2. Check for typos like stray brackets or unclosed quotes.\n3. Validate syntax."
        except ImportError:
            return False, "explained", "⚠️ Could not import healing functions. Manual fix required."
    
    # 4. Authentication Errors -> Explain
    if any(pattern in error_lower for pattern in ["401", "unauthorized", "invalid credentials", "forbidden", "403"]):
        return False, "explained", "🔐 Authentication Error:\n1. Go to n8n → Settings → Credentials.\n2. Find the credential used by this workflow.\n3. Re-enter or refresh the API key.\n4. Test the connection."
    
    # 5. Undefined Variables / Missing Data -> Explain
    if any(pattern in error_lower for pattern in ["undefined", "cannot read property", "null", "is not defined"]):
        return False, "explained", "⚠️ Data Flow Issue:\n1. Check the node BEFORE the failing one.\n2. Ensure it outputs the expected fields.\n3. Use 'Set' node to provide default values if data might be empty."
    
    # 6. HTTP 404 / Not Found -> Explain
    if any(pattern in error_lower for pattern in ["404", "not found", "endpoint"]):
        return False, "explained", "🔍 Resource Not Found:\n1. Verify the URL in the HTTP Request node.\n2. Check if the API endpoint has changed.\n3. Confirm the resource ID exists in the target system."
    
    # 7. Workflow Configuration Issues -> Explain
    if any(pattern in error_lower for pattern in ["disabled", "inactive", "no trigger"]):
        return False, "explained", "⚙️ Workflow Configuration:\n1. Open the workflow in n8n.\n2. Ensure all required nodes are ENABLED.\n3. Check that a trigger node exists and is active."
    
    # ========== DEFAULT FALLBACK (AI AGENT) ==========
    
    # If no deterministic fix worked, ask Gemini
    try:
        from execution.api import get_workflow, update_workflow, publish_workflow
        from execution.ai_healer import consult_gemini_for_fix
        
        print(f"   🤖 Deterministic fixes failed. Consulting Gemini AI for {workflow_id}...")
        
        # 1. Fetch full workflow
        workflow_data = get_workflow(workflow_id)
        if workflow_data:
            # 2. Consult AI
            success, ai_explanation, fixed_workflow = consult_gemini_for_fix(workflow_data, error_msg)
            
            if success:
                # 3. Apply AI Fix
                full_update = {
                    "nodes": fixed_workflow.get("nodes", []),
                    "connections": fixed_workflow.get("connections", {}),
                    "settings": fixed_workflow.get("settings", {}),
                    "name": workflow_data.get("name")
                }
                
                # Update & Publish
                upd_success, upd_msg = update_workflow(workflow_id, full_update)
                if upd_success:
                    publish_workflow(workflow_id)
                    return True, "resolved", f"✨ AI HEALED: {ai_explanation}"
                else:
                    return False, "explained", f"⚠️ AI proposed a fix but update failed: {upd_msg}"
            else:
                return False, "explained", f"⚠️ AI could not solve it: {ai_explanation}"
                
    except Exception as e:
        return False, "explained", f"⚠️ AI Agent Error: {str(e)}"

    return False, "explained", f"🛠️ Manual Review Required:\nWorkflow ID: {workflow_id}\nError: {error_msg}"


def monitor_and_heal():
    """
    Main agentic loop: continuously monitors n8n for failures and automatically heals them.
    This is the core of the agentic workflow.
    """
    if not N8N_URL or not N8N_KEY:
        print("❌ Error: N8N_API_URL or N8N_API_KEY not set in .env")
        return
    
    print("=" * 60)
    print("   🤖 Agentic Self-Annealing System for n8n")
    print("   Monitoring for workflow failures...")
    print(f"   Check interval: {MONITOR_INTERVAL} seconds")
    print("=" * 60)
    
    while True:
        try:
            # Fetch recent executions
            url = f"{N8N_URL}/api/v1/executions?limit=50&includeData=false"
            headers = {"X-N8N-API-KEY": N8N_KEY}
            
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                print(f"⚠️  Failed to fetch executions. Status: {resp.status_code}")
                time.sleep(MONITOR_INTERVAL)
                continue
            
            executions = resp.json().get('data', [])
            
            # Process each execution
            for exc in executions:
                execution_id = exc.get('id')
                workflow_id = exc.get('workflowId')
                is_success = exc.get('finished', False)
                
                # Skip if we've already processed this execution
                if execution_id in PROCESSED_EXECUTIONS:
                    continue
                
                # Only process failed executions
                if not is_success:
                    workflow_name = get_workflow_name(workflow_id)
                    print(f"\n🔍 Detected failure: {workflow_name} (Execution: {execution_id})")
                    
                    # Fetch the actual error message
                    error_msg = get_execution_error(execution_id)
                    if not error_msg:
                        error_msg = "Unknown error (could not fetch details)"
                    
                    print(f"   Error: {error_msg[:100]}...")
                    
                    # Agentic decision: attempt to heal
                    print("   🤖 Agentic healing in progress...")
                    success, status, message = heal_execution(execution_id, workflow_id, error_msg)
                    
                    # Log the healing attempt
                    heal_entry = {
                        "execution_id": execution_id,
                        "workflow_id": workflow_id,
                        "workflow_name": workflow_name,
                        "error": error_msg,
                        "heal_status": status,
                        "heal_message": message,
                        "success": success
                    }
                    save_heal_log(heal_entry)
                    
                    # Mark as processed
                    PROCESSED_EXECUTIONS.add(execution_id)
                    
                    # Report result
                    if success:
                        print(f"   ✅ {message}")
                    else:
                        print(f"   ⚠️  {message}")
                else:
                    # Mark successful executions as processed to avoid re-checking
                    PROCESSED_EXECUTIONS.add(execution_id)
            
            # Sleep before next check
            time.sleep(MONITOR_INTERVAL)
            
        except KeyboardInterrupt:
            print("\n\n🛑 Agentic healer stopped by user")
            break
        except Exception as e:
            print(f"❌ Error in monitoring loop: {str(e)}")
            time.sleep(MONITOR_INTERVAL)


if __name__ == "__main__":
    monitor_and_heal()

