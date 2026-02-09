import requests
import json

try:
    print("Fetching events from http://localhost:8000/api/events...")
    resp = requests.get("http://localhost:8000/api/events")
    
    if resp.status_code == 200:
        events = resp.json()
        print(f"Success! Got {len(events)} events.")
        
        # Print the first few to check fields
        for evt in events[:3]:
            print(json.dumps(evt, indent=2))
    else:
        print(f"Failed: {resp.status_code} - {resp.text}")

except Exception as e:
    print(f"Error: {e}")
