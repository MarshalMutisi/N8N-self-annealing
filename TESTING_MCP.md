# Testing the N8N MCP Server

There are two main ways to test your new MCP server:

## 1. Fast Testing (MCP Inspector)
The easiest way to verify the tools are working without setting up a full AI client is to use the official MCP Inspector.

1.  Open a new terminal in your project root (`c:\Users\marsh\Desktop\leads`).
2.  Run the following command:
    ```powershell
    npx @modelcontextprotocol/inspector python execution/mcp_server.py
    ```
3.  This will open a web interface in your browser (usually at `http://localhost:5173`).
4.  You can then click on the **Tools** tab and try calling:
    -   `list_n8n_workflows`: To see your live n8n workflows.
    -   `get_failed_n8n_executions`: To check for recent errors.

---

## 2. Real-World Testing (Claude Desktop)
To see the "AI Power User" experience, you can add the server to your Claude Desktop config.

1.  Open your Claude Desktop config file:
    `%APPDATA%\Claude\claude_desktop_config.json`
2.  Add the following entry under `"mcpServers"`:
    ```json
    {
      "mcpServers": {
        "n8n-healer": {
          "command": "python",
          "args": ["c:/Users/marsh/Desktop/leads/execution/mcp_server.py"],
          "env": {
            "N8N_API_URL": "YOUR_N8N_URL",
            "N8N_API_KEY": "YOUR_N8N_KEY",
            "GEMINI_API_KEY": "YOUR_GEMINI_KEY"
          }
        }
      }
    }
    ```
3.  Restart Claude Desktop.
4.  You should see a small 🔌 icon. You can now ask: *"Show me my N8N workflows and tell me if any are failing."*

---

## 3. Verify the Dashboard (Two-Way Sync)
While the MCP is running, you should also check that the dashboard still works:

1.  Run `python run_workflow.py`.
2.  Go to `http://localhost:3000`.
3.  Ensure the events are loading correctly. Because they share the same `core_healer.py` logic, any fix applied via MCP will show up as "Resolved" on the dashboard!
