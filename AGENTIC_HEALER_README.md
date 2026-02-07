# Agentic Self-Annealing System for n8n

## Overview

This is an **agentic workflow** that continuously monitors your n8n instance for workflow failures and automatically attempts to heal them. Unlike reactive systems that require manual triggers, this system operates autonomously in the background.

## Architecture

The system follows the 3-layer architecture:

1. **Layer 1 (Directive)**: `directives/self_annealing.md` - Defines healing patterns and strategies
2. **Layer 2 (Orchestration)**: `execution/agentic_healer.py` - Makes intelligent decisions about when/how to heal
3. **Layer 3 (Execution)**: `execution/api.py` - Contains deterministic healing functions

## Quick Start

### 1. Ensure Environment Variables are Set

Make sure your `.env` file contains:
```
N8N_API_URL=http://localhost:5678
N8N_API_KEY=your_api_key_here
```

### 2. Start the Agentic Healer

```bash
python start_agentic_healer.py
```

Or directly:
```bash
python execution/agentic_healer.py
```

The system will:
- Continuously monitor n8n every 30 seconds
- Automatically detect failed workflow executions
- Attempt to heal errors based on intelligent pattern matching
- Log all attempts to `.tmp/heal_log.json`

## How It Works

### Monitoring Loop

1. **Poll n8n API** every 30 seconds for recent executions
2. **Detect failures** by checking execution status
3. **Fetch error details** from failed executions
4. **Make healing decisions** based on error patterns
5. **Apply fixes** automatically or provide explanations
6. **Log results** for learning and improvement

### Healing Strategies

#### Auto-Fixable Errors (Automatically Resolved)

- **Connection/Network Issues**: Automatically retries the execution
- **Syntax Errors**: Fixes JavaScript code in Code nodes and publishes the workflow
- **Rate Limiting**: Logs recommendation to add Wait nodes

#### Explainable Errors (Provides Step-by-Step Guide)

- **Authentication Errors**: Guides user to update credentials
- **Data Flow Issues**: Explains how to check upstream nodes
- **404 Not Found**: Suggests verifying URLs
- **Configuration Issues**: Provides workflow configuration steps

## Logging & Learning

All healing attempts are logged to `.tmp/heal_log.json` with:
- Execution ID and workflow details
- Error message
- Healing strategy attempted
- Success/failure status
- Timestamp

This log can be analyzed to improve healing patterns over time.

## Example Output

```
============================================================
   🤖 Agentic Self-Annealing System for n8n
   Monitoring for workflow failures...
   Check interval: 30 seconds
============================================================

🔍 Detected failure: My Workflow (Execution: abc123)
   Error: SyntaxError: Unexpected token ']'...
   🤖 Agentic healing in progress...
   ✅ Fixed code in nodes: Code Node 1 (Published to n8n)
```

## Stopping the Healer

Press `Ctrl+C` to stop the agentic healer gracefully.

## Integration with Dashboard

The agentic healer works alongside the web dashboard:
- Dashboard: `http://localhost:3000` (shows recent events)
- API: `http://localhost:8000` (provides healing endpoints)

The agentic healer runs independently and doesn't require the dashboard to be running.

## Troubleshooting

### Healer Not Starting
- Check that `.env` file exists and has correct `N8N_API_URL` and `N8N_API_KEY`
- Verify n8n is accessible at the configured URL
- Check Python dependencies: `pip install requests python-dotenv`

### No Healing Attempts
- Verify n8n has failed executions to process
- Check that executions are actually failing (not just warnings)
- Review `.tmp/heal_log.json` to see what's being processed

### Import Errors
- Make sure you're running from the project root directory
- Verify `execution/api.py` exists and has the required functions

## Next Steps

1. **Customize Monitoring Interval**: Edit `MONITOR_INTERVAL` in `execution/agentic_healer.py`
2. **Add New Healing Patterns**: Update `directives/self_annealing.md` and `execution/agentic_healer.py`
3. **Analyze Logs**: Review `.tmp/heal_log.json` to identify common error patterns
4. **Improve Patterns**: Update healing logic based on log analysis

