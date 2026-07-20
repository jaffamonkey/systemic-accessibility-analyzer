#!/bin/bash

# Define the base directory containing all the job folders
JOBS_DIR="/Users/user/code/github/wcag-tools-test-frameworks/auth_service/jobs"

# Loop through every item in the jobs directory that is a folder
for JOB_PATH in "$JOBS_DIR"/*/; do
    
    # Remove the trailing slash to get a clean path
    JOB_PATH="${JOB_PATH%/}"
    
    # Extract just the folder name (e.g., towerhamlets-2-20260710-213114) for logging
    JOB_NAME=$(basename "$JOB_PATH")

    # Define the specific reports and output directories for this job
    REPORTS_DIR="$JOB_PATH/reports"
    OUTPUT_DIR="$JOB_PATH/analysis-canonical-test"

    echo "=================================================="
    echo "Processing Job: $JOB_NAME"
    
    # Check if the reports directory exists before running the Python script
    if [ -d "$REPORTS_DIR" ]; then
        python3 run_job_analysis.py \
            --reports-dir "$REPORTS_DIR" \
            --output-dir "$OUTPUT_DIR"
            
        echo "✅ Successfully completed: $JOB_NAME"
    else
        echo "⚠️  Skipping: $JOB_NAME (No 'reports' directory found)"
    fi
done

echo "=================================================="
echo "All job analyses complete."