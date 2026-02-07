import requests
import os
import json
import time
from dotenv import load_dotenv

load_dotenv()

N8N_URL = os.getenv("N8N_API_URL")
N8N_KEY = os.getenv("N8N_API_KEY")
HEADERS = {"X-N8N-API-KEY": N8N_KEY, "Content-Type": "application/json"}

def create_broken_workflow():
    """Creates a workflow with a deliberate JS syntax error that regex won't catch easily."""
    workflow_json = {
        "name": "AI_HEALER_TEST_BROKEN_" + str(int(time.time())),
        "nodes": [
            {
                "parameters": {},
                "name": "Start",
                "type": "n8n-nodes-base.start",
                "typeVersion": 1,
                "position": [250, 300]
            },
            {
                "parameters": {
                    # Deliberate logic/syntax error that might confuse simple regex
                    # Using a variable that doesn't exist mixed with invalid syntax
                    "jsCode": "const x = 10;\nreturn [{'json': { val: x * undefined_variable_that_crashes }}];" 
                },
                "name": "Broken Code",
                "type": "n8n-nodes-base.code",
                "typeVersion": 1,
                "position": [450, 300]
            }
        ],
        "connections": {
            "Start": {
                "main": [
                    [
                        {
                            "node": "Broken Code",
                            "type": "main",
                            "index": 0
                        }
                    ]
                ]
            }
        },
        "settings": {
            "executionOrder": "v1"
        },
        "active": True
    }
    
    resp = requests.post(f"{N8N_URL}/api/v1/workflows", headers=HEADERS, json=workflow_json)
    if resp.status_code == 200:
        wf = resp.json()
        print(f"✅ Created broken workflow: {wf['name']} (ID: {wf['id']})")
        return wf['id']
    else:
        print(f"❌ Failed to create workflow: {resp.text}")
        return None

def trigger_workflow(workflow_id):
    """Triggers the workflow manually via API."""
    print(f"💥 Triggering workflow {workflow_id} to cause failure...")
    # For manual trigger via API, we often need the webhook or just run it?
    # Actually, activating it and letting it run is one way, but we can also
    # use the /manual-run endpoint if available, or just test webhook.
    # But since it's a "Start" node, we can't easily trigger it externally without a webhook.
    # Let's add a webhook trigger to be safe.
    
    # Actually, simpler: Use the execution engine to run it?
    # The simplest way to trigger a "Start" node workflow is via the UI, but API is limited.
    # Let's update the workflow to have a Webhook trigger.
    
    # ... (Skipping complexity, let's trust the Start node if active? No, Start only runs on UI click)
    # Let's add a Webhook node.
    pass 

# Retrying with Webhook node for easier triggering
def create_broken_webhook_workflow():
    workflow_json = {
        "name": "AI_HEALER_TEST_WEBHOOK_" + str(int(time.time())),
        "nodes": [
            {
                "parameters": {
                    "path": "breakme",
                    "options": {}
                },
                "name": "Webhook",
                "type": "n8n-nodes-base.webhook",
                "typeVersion": 1,
                "position": [100, 300],
                "webhookId": "breakme-" + str(int(time.time()))
            },
            {
                "parameters": {
                    "jsCode": "items[0].json.myVal = nonExistentVar; // This will crash ReferenceError"
                },
                "name": "BrokenNode",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [300, 300]
            }
        ],
        "connections": {
            "Webhook": {
                "main": [
                    [
                        {
                            "node": "BrokenNode",
                            "type": "main",
                            "index": 0
                        }
                    ]
                ]
            }
        },
        "active": True
    }
    
    resp = requests.post(f"{N8N_URL}/api/v1/workflows", headers=HEADERS, json=workflow_json)
    if resp.status_code == 200:
        wf = resp.json()
        # Need to activate it
        requests.post(f"{N8N_URL}/api/v1/workflows/{wf['id']}/activate", headers=HEADERS)
        print(f"✅ Created & Activated broken workflow: {wf['name']} (ID: {wf['id']})")
        
        # Get the webhook URL (Production)
        # Usually http://localhost:5678/webhook/breakme-...
        # We need to find the full path from the node, but n8n structure is standard.
        webhook_path = workflow_json['nodes'][0]['parameters']['path']
        return wf['id'], f"{N8N_URL}/webhook/{webhook_path}"
    else:
        print(f"❌ Failed to create workflow: {resp.text}")
        return None, None

def check_logs_for_fix(workflow_id):
    print("⏳ Waiting for Healer to react (check every 5s)...")
    for i in range(12): # Wait 60 seconds max
        time.sleep(5)
        if os.path.exists(".tmp/heal_log.json"):
            with open(".tmp/heal_log.json", "r") as f:
                logs = json.load(f)
                # Look for our workflow ID
                for entry in reversed(logs):
                    if entry.get('workflow_id') == workflow_id:
                        print(f"🔍 Found log entry: {entry.get('error')}")
                        if entry.get('success'):
                            print(f"✨ SUCCESS! AI Healed the workflow!")
                            print(f"   Message: {entry.get('heal_message')}")
                            return True
                        else:
                            print(f"⚠️  Healer attempted but failed: {entry.get('heal_message')}")
    print("❌ Timed out waiting for healer.")
    return False

if __name__ == "__main__":
    wf_id, webhook_url = create_broken_webhook_workflow()
    if wf_id and webhook_url:
        print(f"🚀 Triggering Webhook: {webhook_url}")
        try:
            requests.get(webhook_url, timeout=5)
        except:
             # Webhooks often timeout if they crash the workflow without response
            print("   (Webhook request sent, likely crashed as expected)")
        
        check_logs_for_fix(wf_id)
