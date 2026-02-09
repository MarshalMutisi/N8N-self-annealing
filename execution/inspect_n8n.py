import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

N8N_URL = os.getenv("N8N_API_URL")
N8N_KEY = os.getenv("N8N_API_KEY")

headers = {"X-N8N-API-KEY": N8N_KEY}
# Fetch list
url = f"{N8N_URL}/api/v1/executions?limit=1&includeData=false"
resp = requests.get(url, headers=headers)
if resp.status_code == 200:
    data = resp.json()
    execs = data.get('data', [])
    if execs:
        first = execs[0]
        print("Execution Summary:")
        print(json.dumps(first, indent=2))
        
        # Fetch details
        print("\nFetching details...")
        id = first['id']
        url_detail = f"{N8N_URL}/api/v1/executions/{id}"
        resp_detail = requests.get(url_detail, headers=headers)
        if resp_detail.status_code == 200:
            full_json = resp_detail.json()
            # Write to file for inspection
            with open("execution_dump.json", "w") as f:
                json.dump(full_json, f, indent=2)
            print("Dumped execution details to execution_dump.json")
        else:
            print("Failed to fetch details")
    else:
        print("No executions found")
else:
    print(f"Error fetching list: {resp.status_code}")
