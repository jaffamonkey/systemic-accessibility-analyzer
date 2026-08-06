import json
import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Path to the JSON file containing your single list of configs
CONFIG_FILE_PATH = "/Users/user/code/systemic-accessibility-analyzer/batched_jobs/job_batch_00.json"

# The full tool suite to enforce
full_tool_suite = [
    "axe-core", "html-sniffer", "oobee", "lighthouse", "ibm", 
    "uuv", "nu-html-checker", "alfa", "speca11y", "pa11y", "axe-scan"
]

# Adjust how many jobs run concurrently (e.g., 4 at a time is usually a sweet spot)
MAX_CONCURRENT_JOBS = 4

def process_single_job(job_data):
    """Worker function to submit and track a single job concurrently."""
    job_name = job_data.get('job_name')
    job_data["tools"] = full_tool_suite
    
    try:
        print(f"🚀 Launching job: {job_name}")
        res = requests.post('http://localhost:8001/jobs', json=job_data, timeout=30)
        
        if res.status_code not in [200, 201]:
            print(f"❌ Failed to queue {job_name}: HTTP {res.status_code}")
            return job_name, "failed_to_queue"
            
        response_data = res.json()
        job_id = response_data.get("id")
        print(f"✅ Queued successfully: {job_name} (ID: {job_id})")
        
        # Active Polling Loop for this specific job
        status = "queued"
        max_attempts = 120  # 120 checks * 15 seconds = 30 minute absolute max limit
        attempts = 0
        
        while status in ["queued", "running"] and attempts < max_attempts:
            time.sleep(15)  # Check status every 15 seconds
            attempts += 1
            
            try:
                status_res = requests.get(f'http://localhost:8001/jobs/{job_id}', timeout=10)
                if status_res.status_code == 200:
                    status = status_res.json().get("status")
                else:
                    print(f"⚠️ [{job_name}] Error checking status ({status_res.status_code}), retrying...")
            except Exception as poll_err:
                print(f"⚠️ [{job_name}] Network error while polling status: {poll_err}")
                
        if status in ["queued", "running"]:
            print(f"⏱️ ❌ Job {job_name} timed out after 30 minutes!")
            return job_name, "timeout"
        else:
            print(f"🏁 Finished {job_name} with final status: {status}")
            return job_name, status
            
    except Exception as e:
        print(f"❌ Exception processing job '{job_name}': {e}")
        return job_name, "error"

def main():
    try:
        with open(CONFIG_FILE_PATH, 'r') as f:
            jobs_list = json.load(f)
    except FileNotFoundError:
        print(f"Error: Could not find {CONFIG_FILE_PATH}.")
        return
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format in {CONFIG_FILE_PATH} - {e}")
        return

    total_jobs = len(jobs_list)
    print(f"Total jobs to process in parallel: {total_jobs} (Max concurrent workers: {MAX_CONCURRENT_JOBS})")

    # Use a ThreadPoolExecutor to run multiple jobs concurrently
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_JOBS) as executor:
        # Submit all jobs to the pool
        future_to_job = {
            executor.submit(process_single_job, job_data): job_data.get('job_name') 
            for job_data in jobs_list
        }
        
        # As each concurrent job finishes, catch its result
        for future in as_completed(future_to_job):
            j_name = future_to_job[future]
            try:
                name, final_status = future.result()
                print(f"📊 Summary -> Job '{name}' completed with status: {final_status}")
            except Exception as exc:
                print(f"📊 Summary -> Job '{j_name}' generated an exception: {exc}")

    print("\n🎉 All batch jobs processed!")

if __name__ == "__main__":
    main()
