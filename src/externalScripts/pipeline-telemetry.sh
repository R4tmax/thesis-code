#!/bin/bash

# Workflows to analyze
WORKFLOWS=("CI Orchestrator" "CD Orchestrator")
LIMIT=5

echo "Fetching GitHub Actions Telemetry..."

for workflow in "${WORKFLOWS[@]}"; do
    echo "================================================================"
    echo " WORKFLOW: $workflow (Latest $LIMIT Successful Runs)"
    echo "================================================================"

    # 1. Get the run IDs for the last 5 successful runs
    run_ids=$(gh run list --workflow "$workflow" --status success --limit "$LIMIT" --json databaseId --jq '.[].databaseId')

    # If no runs are found, skip to the next workflow
    if [[ -z "$run_ids" ]]; then
        echo "No successful runs found for this workflow."
        continue
    fi

    # 2. Iterate through each Run ID
    for run_id in $run_ids; do
        echo "----------------------------------------------------------------"
        echo " Run ID: $run_id"
        echo "----------------------------------------------------------------"
        printf "%-40s | %-15s\n" "JOB NAME" "DURATION (MM:SS)"
        echo "----------------------------------------------------------------"

        # 3. Get job details, extract name and timestamps, and loop through them
        gh run view "$run_id" --json jobs --jq '.jobs[] | "\(.name)\t\(.startedAt)\t\(.completedAt)"' | \
        while IFS=$'\t' read -r name started_at completed_at; do

            # Skip jobs that don't have valid timestamps (e.g., pending or skipped jobs)
            if [[ -z "$started_at" || -z "$completed_at" || "$started_at" == "null" || "$completed_at" == "null" ]]; then
                continue
            fi

            # 4. Convert ISO 8601 timestamps to Epoch seconds (GNU date syntax)
            start_sec=$(date -d "$started_at" +%s 2>/dev/null)
            end_sec=$(date -d "$completed_at" +%s 2>/dev/null)

            # 5. Calculate and format the duration
            if [[ -n "$start_sec" && -n "$end_sec" ]]; then
                duration_sec=$((end_sec - start_sec))

                # Format into Minutes:Seconds
                mins=$((duration_sec / 60))
                secs=$((duration_sec % 60))
                duration_formatted=$(printf "%02d:%02d" $mins $secs)

                printf "%-40s | %-15s\n" "$name" "$duration_formatted"
            fi
        done
        echo "" # Add a blank line between runs for readability
    done
done