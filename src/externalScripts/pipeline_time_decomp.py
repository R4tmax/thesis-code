import requests
import re
from datetime import datetime
import subprocess

def get_gh_token():
    """Dynamically extracts the authentication token from the gh CLI."""
    try:
        # Runs `gh auth token` and captures the output
        result = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None
    except FileNotFoundError:
        print("❌ Error: The 'gh' CLI tool is not installed or not in PATH.")
        return None

OWNER = "R4tmax"
REPO = "thesis-code"
TOKEN = get_gh_token()
WORKFLOWS_TO_TRACK = ["CI Orchestrator", "CD Orchestrator"]
RUN_LIMIT = 5

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}


def get_workflow_id(workflow_name):
    """Fetches the internal GitHub ID for a workflow based on its display name."""
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/actions/workflows"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()

    for wf in response.json().get("workflows", []):
        if wf["name"] == workflow_name:
            return wf["id"]
    return None


def main():
    if not TOKEN:
        print("❌ Error: GITHUB_TOKEN environment variable is not set.")
        return

    for workflow_name in WORKFLOWS_TO_TRACK:
        print(f"\n{'=' * 65}")
        print(f" 📊 WORKFLOW: {workflow_name}")
        print(f"{'=' * 65}")

        wf_id = get_workflow_id(workflow_name)
        if not wf_id:
            print(f"⚠️ Could not find workflow named '{workflow_name}'. Check the exact name in your YAML.")
            continue

        # 1. Fetch the latest successful runs
        runs_url = f"https://api.github.com/repos/{OWNER}/{REPO}/actions/workflows/{wf_id}/runs"
        params = {"status": "success", "per_page": RUN_LIMIT}
        runs_resp = requests.get(runs_url, headers=HEADERS, params=params)
        runs_resp.raise_for_status()
        runs = runs_resp.json().get("workflow_runs", [])

        if not runs:
            print("No successful runs found.")
            continue

        # 2. Iterate through each run
        for run in runs:
            run_id = run["id"]
            run_date = run["created_at"]

            print(f"\n{'-' * 65}\n Run ID: {run_id} | Triggered: {run_date}\n{'-' * 65}")
            print(f"{'JOB NAME':<45} | {'DURATION'}")
            print(f"{'-' * 65}")

            # 3. Fetch jobs for this specific run
            jobs_url = f"https://api.github.com/repos/{OWNER}/{REPO}/actions/runs/{run_id}/jobs"
            jobs_resp = requests.get(jobs_url, headers=HEADERS)
            jobs_resp.raise_for_status()
            jobs = jobs_resp.json().get("jobs", [])

            mermaid_tasks = []

            # 4. Process each job
            for job in jobs:
                # Explicitly ignore skipped jobs (e.g., jobs for other environments)
                if job.get("conclusion") == "skipped":
                    continue

                started_at = job.get("started_at")
                completed_at = job.get("completed_at")

                # Ignore jobs that haven't properly started/finished
                if not started_at or not completed_at:
                    continue

                # Time Math using precise datetime parsing
                fmt = "%Y-%m-%dT%H:%M:%SZ"
                t_start = datetime.strptime(started_at, fmt)
                t_end = datetime.strptime(completed_at, fmt)
                duration_sec = int((t_end - t_start).total_seconds())

                mins, secs = divmod(duration_sec, 60)
                duration_str = f"{mins:02d}:{secs:02d}"

                print(f"{job['name']:<45} | {duration_str}")

                # Format data for Mermaid.js
                # We strip special chars to create a safe, unique ID for the Mermaid engine
                safe_id = "job_" + re.sub(r'[^a-zA-Z0-9]', '', job['name'])
                mermaid_tasks.append(f"    {job['name']} : {safe_id}, {started_at}, {completed_at}")

            # 5. Output the Graph Data
            if mermaid_tasks:
                print("\nVisual Graph (Copy into a Markdown file/editor to render):")
                print("```mermaid")
                print("gantt")
                print(f"    title Pipeline Execution Flow (Run {run_id})")
                print("    dateFormat  YYYY-MM-DDTHH:mm:ssZ")
                print("    axisFormat  %H:%M:%S")
                print("    section Jobs")
                for task in mermaid_tasks:
                    print(task)
                print("```\n")


if __name__ == "__main__":
    main()