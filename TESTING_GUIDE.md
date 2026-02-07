# Testing Guide for Agentic Self-Annealing System

## Quick Test (You Already Have Failed Executions!)

Your test suite shows you have **3 failed executions** ready to test with! Here's how:

### Step 1: Run the Test Suite
```bash
python test_agentic_healer.py
```

This verifies:
- ✅ n8n connection is working
- ✅ Can fetch executions
- ✅ System is ready

### Step 2: Start the Agentic Healer
```bash
python start_agentic_healer.py
```

The healer will:
- Start monitoring immediately
- Detect your existing failed executions
- Attempt to heal them automatically
- Show real-time output

### Step 3: Watch It Work

You should see output like:
```
============================================================
   🤖 Agentic Self-Annealing System for n8n
   Monitoring for workflow failures...
   Check interval: 30 seconds
============================================================

🔍 Detected failure: [Workflow Name] (Execution: 305...)
   Error: [Error message from n8n]
   🤖 Agentic healing in progress...
   ✅ [Healing result]
```

### Step 4: Check Results

**View the heal log:**
```bash
# On Windows PowerShell
Get-Content .tmp\heal_log.json | ConvertFrom-Json | Format-List

# Or just open the file
notepad .tmp\heal_log.json
```

**Verify in n8n:**
- Open n8n UI
- Check if workflows were fixed
- Try re-executing the workflows

---

## Creating Test Failures

If you want to test with new failures, here are some options:

### Test 1: Syntax Error (Auto-Fixable)
1. Create a new workflow in n8n
2. Add a **Code** node
3. Add this JavaScript with a syntax error:
   ```javascript
   const data = {name: "test"];  // Missing closing brace
   ```
4. Save and execute
5. The agentic healer should automatically fix it!

### Test 2: Connection Error (Auto-Retry)
1. Create a workflow with an **HTTP Request** node
2. Set URL to `http://invalid-url-that-does-not-exist.com`
3. Execute the workflow
4. The healer will automatically retry the execution

### Test 3: Authentication Error (Explained)
1. Create a workflow with an API call
2. Use invalid/expired credentials
3. Execute the workflow
4. The healer will provide step-by-step fix instructions

---

## What to Look For

### Successful Auto-Fix
- ✅ Status: "resolved"
- ✅ Message shows what was fixed
- ✅ Workflow is actually fixed in n8n
- ✅ Entry in `.tmp/heal_log.json`

### Explained Errors
- ⚠️ Status: "explained"
- ⚠️ Message provides manual fix steps
- ⚠️ Entry logged for learning

### Monitoring
- System checks every 30 seconds
- Only processes new failures (tracks processed executions)
- Logs all attempts for analysis

---

## Troubleshooting

### Healer Not Detecting Failures
- Check that executions are actually **failed** (not just warnings)
- Verify n8n API is accessible
- Check `.env` has correct `N8N_API_URL` and `N8N_API_KEY`

### No Healing Attempts
- Review `.tmp/heal_log.json` to see what's happening
- Check console output for error messages
- Verify the execution actually failed in n8n

### Import Errors
- Make sure you're in the project root directory
- Run: `pip install requests python-dotenv`
- Verify `execution/api.py` exists

---

## Next Steps After Testing

1. **Review the logs**: Analyze `.tmp/heal_log.json` to see patterns
2. **Improve patterns**: Update `directives/self_annealing.md` with new error patterns
3. **Customize interval**: Edit `MONITOR_INTERVAL` in `execution/agentic_healer.py`
4. **Add new healing strategies**: Extend the `heal_execution()` function

---

## Quick Reference

```bash
# Test the system
python test_agentic_healer.py

# Start the agentic healer
python start_agentic_healer.py

# View heal log (PowerShell)
Get-Content .tmp\heal_log.json

# View heal log (Python)
python -c "import json; print(json.dumps(json.load(open('.tmp/heal_log.json')), indent=2))"
```

