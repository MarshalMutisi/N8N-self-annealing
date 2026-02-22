import subprocess
import json
import sys
import time

def test_mcp_server():
    print("🚀 Starting MCP Server for CLI verification...")
    # Start the server as a subprocess
    process = subprocess.Popen(
        [sys.executable, "execution/mcp_server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=0
    )

    # Initialize message (JSON-RPC)
    init_msg = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "TestClient", "version": "1.0"}
        }
    }

    # Request tools list message
    list_tools_msg = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "listTools",
        "params": {}
    }

    try:
        # Send initialize
        process.stdin.write(json.dumps(init_msg) + "\n")
        time.sleep(1)
        
        # Read initialization response (could be multiple if there are logs)
        while True:
            line = process.stdout.readline()
            if not line: break
            print(f"Server response (init): {line.strip()}")
            if '"id": 1' in line:
                break

        # Send listTools
        process.stdin.write(json.dumps(list_tools_msg) + "\n")
        time.sleep(1)

        # Read tools list response
        while True:
            line = process.stdout.readline()
            if not line: break
            print(f"Server response (tools): {line.strip()}")
            if '"id": 2' in line:
                data = json.loads(line)
                tools = [tool["name"] for tool in data.get("result", {}).get("tools", [])]
                print(f"\n✅ Tools found: {tools}")
                
                expected = ['list_n8n_workflows', 'get_failed_n8n_executions', 'fix_n8n_workflow', 'get_workflow_details']
                missing = [t for t in expected if t not in tools]
                
                if not missing:
                    print("✨ All expected tools are present!")
                else:
                    print(f"❌ Missing tools: {missing}")
                break

    except Exception as e:
        print(f"❌ Verification failed: {e}")
    finally:
        process.terminate()

if __name__ == "__main__":
    test_mcp_server()
