#!/usr/bin/env bash

# -----------------------------------------------------------------------------
# Tool Runner Setup Script
# Iterates through the tool_runner directories and installs dependencies.
# -----------------------------------------------------------------------------

# Exit immediately if a command exits with a non-zero status
set -e

echo "🚀 Starting mass installation for tool_runner..."

# Iterate through all directories in the current folder
for dir in */; do
    # Strip the trailing slash to get the exact directory name
    tool="${dir%/}"

    echo "----------------------------------------"
    echo "📦 Processing: $tool"
    echo "----------------------------------------"

    # Navigate into the tool directory
    cd "$tool" || { echo "❌ Failed to enter $tool"; exit 1; }

    # Apply the specific installation rules based on the folder name
    case "$tool" in
        axe-scan)
            echo "⚙️  Action: Global install for axe-scan"
            npm install -g axe-scan
            ;;
        
        pa11y_runner_axe | pa11y_runner_htmlcs)
            echo "⚙️  Action: npm install only"
            npm install
            ;;
            
        *)
            echo "⚙️  Action: npm install && npx playwright install chromium"
            npm install
            # Using npx ensures it uses the locally installed playwright package
            npx playwright install chromium
            ;;
    esac

    # Navigate back to the parent directory for the next loop iteration
    cd ..
done

echo "----------------------------------------"
echo "✅ All tools installed successfully!"