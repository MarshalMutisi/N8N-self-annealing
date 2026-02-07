# Directive: n8n Agentic Self-Annealing System

## Goal
Continuously monitor n8n workflows for failures and automatically heal them using an agentic workflow pattern. The system operates in three layers:

1. **Layer 1 (Directive)**: This document defines the healing patterns and strategies
2. **Layer 2 (Orchestration)**: `execution/agentic_healer.py` - Makes intelligent decisions about when/how to heal
3. **Layer 3 (Execution)**: `execution/api.py` - Contains deterministic healing functions

## Agentic Workflow

The system runs as a continuous monitoring loop that:
1. Polls n8n API every 30 seconds for recent executions
2. Detects failed executions automatically
3. Fetches detailed error messages
4. Makes intelligent healing decisions based on error patterns
5. Automatically applies fixes or provides explanations
6. Logs all attempts to `.tmp/heal_log.json` for learning

## Auto-Fixable Errors (Execution Layer Handles)

| Error Pattern | Action | n8n API Call |
|---------------|--------|--------------|
| `connection refused`, `timeout`, `ECONNRESET` | Retry execution | `POST /executions/{id}/retry` |
| `rate limit`, `429`, `quota exceeded` | Log recommendation | (Explanation only) |
| `JSON parse`, `syntax error` | Fix code nodes + publish | `PATCH /workflows/{id}` + `POST /workflows/{id}/activate` |
| Node is `disabled` but required | Enable the node | `PATCH /workflows/{id}` |
| Missing webhook path | Generate default path | `PATCH /workflows/{id}` |

## Explainable Errors (Orchestration Layer Generates Guide)

| Error Pattern | Explanation Template |
|---------------|---------------------|
| `401 Unauthorized`, `invalid credentials` | "Your API key has expired or is incorrect. Go to Settings → Credentials → Update the key." |
| `undefined variable`, `cannot read property` | "A previous node didn't return the expected data. Check the output of the upstream node." |
| `HTTP 404`, `not found` | "The API endpoint has changed. Verify the URL in the HTTP Request node." |
| `disabled`, `inactive`, `no trigger` | "Open the workflow in n8n. Ensure all required nodes are ENABLED and a trigger exists." |

## Edge Cases
- If no pattern matches: Return "Manual Review Required. Contact Administrator."
- Log all heal attempts to `.tmp/heal_log.json` for learning.
- Track processed executions to avoid duplicate healing attempts.

## Scripts

### Orchestration Layer (Agentic)
- `execution/agentic_healer.py`: Main agentic loop that monitors and automatically triggers healing
  - Run with: `python execution/agentic_healer.py`
  - Runs continuously, checking every 30 seconds
  - Automatically processes new failures without manual intervention

### Execution Layer (Deterministic)
- `execution/api.py`: Contains `heal_event()` endpoint and healing functions
  - `fix_code_node_in_workflow()`: Fixes JavaScript syntax errors in Code nodes
  - `publish_workflow()`: Publishes workflow changes (n8n v2.0 requirement)
  - `get_real_error_message()`: Fetches detailed error from execution

## Usage

**Start the agentic healer:**
```bash
python execution/agentic_healer.py
```

The system will:
- Continuously monitor n8n for failures
- Automatically attempt to heal detected errors
- Log all attempts for learning
- Report results in real-time

**Manual healing (via API):**
```bash
POST /api/heal
{
  "executionId": "...",
  "workflowId": "...",
  "error": "..."
}
```

## Learning & Improvement

All healing attempts are logged to `.tmp/heal_log.json` with:
- Execution ID and workflow details
- Error message
- Healing strategy attempted
- Success/failure status
- Timestamp

This log can be analyzed to improve healing patterns over time.
