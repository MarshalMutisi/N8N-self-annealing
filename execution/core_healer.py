import os
import json
import requests
import re
import subprocess
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

# Import AI healing logic
try:
    from execution.ai_healer import consult_gemini_for_fix
except ImportError:
    # Handle direct execution or relative import issues
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from ai_healer import consult_gemini_for_fix

load_dotenv()

N8N_URL = os.getenv("N8N_API_URL")
N8N_KEY = os.getenv("N8N_API_KEY")

def get_workflow(workflow_id: str) -> Optional[Dict]:
    """Fetch full workflow JSON from n8n"""
    url = f"{N8N_URL}/api/v1/workflows/{workflow_id}"
    headers = {"X-N8N-API-KEY": N8N_KEY}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"Error fetching workflow {workflow_id}: {e}")
    return None

def update_workflow(workflow_id: str, workflow_data: Dict) -> Tuple[bool, str]:
    """Update workflow in n8n"""
    url = f"{N8N_URL}/api/v1/workflows/{workflow_id}"
    headers = {"X-N8N-API-KEY": N8N_KEY, "Content-Type": "application/json"}
    try:
        resp = requests.put(url, headers=headers, json=workflow_data, timeout=10)
        if resp.status_code in [200, 201]:
            return True, "Updated successfully"
        return False, f"Failed (Status {resp.status_code}): {resp.text}"
    except Exception as e:
        return False, f"Error updating workflow: {e}"

def publish_workflow(workflow_id: str) -> bool:
    """Explicitly publish/activate workflow"""
    url = f"{N8N_URL}/api/v1/workflows/{workflow_id}/activate"
    headers = {"X-N8N-API-KEY": N8N_KEY}
    try:
        resp = requests.post(url, headers=headers, timeout=10)
        return resp.status_code in [200, 201]
    except:
        return False

def fix_javascript_syntax(code: str) -> Tuple[str, bool]:
    """Attempt to fix common JavaScript syntax errors."""
    original = code
    
    # Fix 1: Remove stray brackets in property names
    code = re.sub(r'\.(\w*)\](\w+)', r'.\1\2', code)
    
    # Fix 2: Remove random brackets in variable names
    code = re.sub(r'(\w+)\](\w+)', r'\1\2', code)
    code = re.sub(r'(\w+)\[(\w+)(?!\])', r'\1\2', code)
    
    # Fix 3: Fix unclosed strings
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
    
    # Fix 5: Fix .ll() typo
    code = code.replace(".ll()", ".all()")
    
    return code, code != original

def deterministic_fix(workflow_id: str, error_msg: str) -> Tuple[bool, str]:
    """Attempt deterministic fixes based on error patterns."""
    error_lower = error_msg.lower()
    
    # 1. JSON / Syntax Errors
    if any(pattern in error_lower for pattern in ["json", "parse", "syntax", "unexpected token", "is not a function", "not defined"]):
        workflow = get_workflow(workflow_id)
        if not workflow:
            return False, "Could not fetch workflow for fixing."
        
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
            update_data = {
                "nodes": nodes,
                "connections": workflow.get('connections', {}),
                "settings": workflow.get('settings', {}),
                "name": workflow.get('name')
            }
            success, msg = update_workflow(workflow_id, update_data)
            if success:
                publish_workflow(workflow_id)
                return True, f"✅ Fixed code in nodes: {', '.join(fixed_nodes)} (Published)"
            else:
                return False, f"Failed to update workflow: {msg}"
    
    # 2. Rate Limiting
    if any(pattern in error_lower for pattern in ["rate limit", "429", "quota exceeded", "too many requests"]):
        return True, "✅ Rate limit detected. RECOMMENDED: Add a 'Wait' node before API calls."

    # 3. Authentication Errors (Explanation only)
    if any(pattern in error_lower for pattern in ["401", "unauthorized", "invalid credentials", "forbidden", "403"]):
        return False, "🔐 Auth Error: Please refresh credentials in n8n settings."

    return False, "No deterministic fix found."

def heal_workflow(workflow_id: str, execution_id: str, error_msg: str) -> Dict:
    """Main entry point for healing a workflow failure."""
    
    # Step 1: Try Deterministic Fixes
    success, message = deterministic_fix(workflow_id, error_msg)
    if success:
        return {"status": "resolved", "message": message}
    
    # Step 2: Try Connection/Network Retry (Special subset of deterministic)
    if any(pattern in error_msg.lower() for pattern in ["connection refused", "timeout", "econnreset", "network error"]):
        retry_url = f"{N8N_URL}/api/v1/executions/{execution_id}/retry"
        headers = {"X-N8N-API-KEY": N8N_KEY}
        try:
            resp = requests.post(retry_url, headers=headers, timeout=10)
            if resp.status_code in [200, 201]:
                return {"status": "resolved", "message": "✅ Auto-Retry triggered for network issue."}
        except:
            pass

    # Step 3: AI Escalation (Gemini)
    print(f"🤖 Escalating to Gemini AI for {workflow_id}...")
    workflow_json = get_workflow(workflow_id)
    if workflow_json:
        ai_success, explanation, fixed_workflow = consult_gemini_for_fix(workflow_json, error_msg)
        if ai_success and fixed_workflow:
            update_data = {
                "nodes": fixed_workflow.get("nodes", workflow_json.get("nodes", [])),
                "connections": fixed_workflow.get("connections", workflow_json.get("connections", {})),
                "settings": fixed_workflow.get("settings", workflow_json.get("settings", {})),
                "name": fixed_workflow.get("name", workflow_json.get("name"))
            }
            update_success, update_msg = update_workflow(workflow_id, update_data)
            if update_success:
                publish_workflow(workflow_id)
                return {"status": "resolved", "message": f"🤖 Gemini AI fixed it: {explanation} (Published)"}
            else:
                return {"status": "explained", "message": f"🤖 AI found fix but failed to apply: {update_msg}"}
        else:
            return {"status": "explained", "message": f"🤖 AI could not fix: {explanation}"}

    return {
        "status": "explained",
        "message": f"🛠️ Manual review required for: {error_msg[:100]}..."
    }
