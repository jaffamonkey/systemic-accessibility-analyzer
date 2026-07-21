import json
import requests
import time
from pathlib import Path

# Path to your root jobs directory
jobs_root = Path("/Users/user/queue/jobs/6")

full_tool_suite = [
    "axe-core", "html-sniffer", "oobee", "lighthouse", "ibm", 
    "uuv", "nu-html-checker", "alfa", "speca11y", "pa11y", "axe-scan"
]

# Find all config files
job_files = sorted(list(jobs_root.glob("**/incoming_job_config.json")))
print(f"Total jobs to process: {len(job_files)}")

for job_json_path in job_files:
    try:
        with open(job_json_path, 'r') as f:
            job_data = json.load(f)
        
        # Override with full tool suite
        job_data["tools"] = full_tool_suite
        
        print(f"--- Processing: {job_data.get('job_name')} ---")
        
        # Trigger the job
        res = requests.post('http://localhost:8001/jobs', json=job_data, timeout=30)
        
        if res.status_code in [200, 201]:
            print(f"Success: {job_data.get('job_name')}")
        else:
            print(f"API Error ({res.status_code}): {res.text}")
            
    except Exception as e:
        print(f"Failed: {job_json_path.parent.name} - {e}")
        
    # Strictly serial: wait before starting the next one
    time.sleep(15)