#!/usr/bin/env bash
cd /Users/user/code/systemic-accessibility-analyzer/analyzer || exit 1
source analysis1/bin/activate
export ANALYSIS_JOBS_BASE_DIR="./jobs"
python -m uvicorn app.main:app --reload --port 8000