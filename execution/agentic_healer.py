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
        try:
            with open(HEAL_LOG_FILE, 'r') as f:
                content = f.read().strip()
                if not content:
                    return []
                return json.loads(content)
        except (json.JSONDecodeError, Exception) as e:
            print(f"⚠️ Warning: Failed to load {HEAL_LOG_FILE}: {str(e)}")
            return []
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


# Import shared logic
from execution.core_healer import heal_workflow, get_workflow

def get_workflow_name(workflow_id: str) -> str:
    """Fetch workflow name from n8n API."""
    workflow = get_workflow(workflow_id)
    if workflow:
        return workflow.get('name', f"Workflow {workflow_id}")
    return f"Workflow {workflow_id}"

def get_execution_error(execution_id: str) -> Optional[str]:
    """Fetch the actual error message from an execution."""
    # This is slightly different from api.py's version but uses the same recursive logic
    # To avoid cross-dependency issues, we'll keep the recursive search here or move to core_healer.
    # For now, let's just use the api.py logic which is better.
    # Actually, let's just import find_error_recursive from a helper or keep it here.
    url = f"{N8N_URL}/api/v1/executions/{execution_id}?includeData=true"
    headers = {"X-N8N-API-KEY": N8N_KEY}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            full_data = resp.json()
            # Reuse logic to find error
            from execution.api import find_error_recursive
            return find_error_recursive(full_data)
    except:
        pass
    return "Unknown Error"


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
                    result = heal_workflow(workflow_id, execution_id, error_msg)
                    success = result["status"] == "resolved"
                    status = result["status"]
                    message = result["message"]
                    
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

