#!/bin/bash

# Name of the final combined file
OUTPUT_FILE="collated_inputs.txt"

# Clear the output file if it already exists
> "$OUTPUT_FILE"

# Search specifically inside the jobs folder for input.txt files
find ./jobs -type f -name "urls.txt" | while read -r file; do
    # Extract just the specific review folder name (e.g., accessibilityreview-20260531-115106)
    folder_name=$(basename "$(dirname "$file")")
    
    # Append a clean header to the output file
    echo "=================================================================" >> "$OUTPUT_FILE"
    echo " REVIEW FOLDER: $folder_name" >> "$OUTPUT_FILE"
    echo "=================================================================" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
    
    # Append the content of the input.txt file
    cat "$file" >> "$OUTPUT_FILE"
    
    # Add spacing before the next entry
    echo -e "\n\n" >> "$OUTPUT_FILE"
done

echo "Done! All files collated into '$(pwd)/$OUTPUT_FILE'."
