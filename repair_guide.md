# n8n Self-Healing System - Repair Guide

## Quick Start
```powershell
cd c:\Users\marsh\Desktop\leads
python run_workflow.py
```
Dashboard: [http://localhost:3000](http://localhost:3000)

---

## Auto-Fixed Errors (Click "HEAL" = Done)

| Error Type | What Happens | PowerShell Executed |
|------------|--------------|---------------------|
| **Port Already In Use** | Kills process, restarts services | `Stop-Process -Id (Get-NetTCPConnection -LocalPort 3000).OwningProcess -Force` |
| **Connection Timeout** | Retries via n8n API | n8n: `POST /executions/{id}/retry` |
| **Syntax Error in Code** | Fixes code, updates + publishes workflow | n8n: `PATCH` + `POST /activate` |
| **Rate Limit / 429** | Recommends Wait node | (Explanation only) |

---

## Explained Errors (Click "HEAL" = Step-by-Step Guide)

| Error Type | Manual Fix Steps |
|------------|------------------|
| **401 / Unauthorized** | Settings → Credentials → Refresh API key |
| **Undefined / null** | Check upstream node output, add Set node |
| **404 Not Found** | Verify URL in HTTP Request node |
| **Disabled Node** | Enable required nodes in workflow editor |

---

## DEO Framework Integration

### Layer 1 (Directive)
- This file (`repair_guide.md`)
- `directives/self_annealing.md`

### Layer 2 (Orchestration)
- n8n AI Agent reads this guide and decides fix strategy

### Layer 3 (Execution)
- `execution/api.py` executes PowerShell commands
- Updates n8n workflows via API
- Publishes changes (n8n v2.0 requirement)

---

## n8n v2.0 Critical Notes
- `PATCH /workflows/{id}` only saves draft
- Must call `POST /workflows/{id}/activate` to publish
- This is handled automatically by the heal system

---

## Troubleshooting

### Dashboard Not Loading
```powershell
taskkill /F /IM node.exe /IM python.exe
python run_workflow.py
```

### n8n API Errors
Check `.env` file:
```
N8N_API_URL=http://localhost:5678
N8N_API_KEY=your_key_here
```
