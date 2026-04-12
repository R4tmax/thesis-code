import subprocess
import requests
import re


def get_gh_token():
    try:
        result = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except Exception:
        print("❌ Error: Could not retrieve token from 'gh' CLI.")
        return None


# ==========================================
# CONFIGURATION
# ==========================================
OWNER = "R4tmax"  # Extracted from your CLI output
REPO = "thesis-code"  # Extracted from your CLI output
TOKEN = get_gh_token()
CI_WORKFLOW = "CI Orchestrator"
CD_WORKFLOW = "CD Orchestrator"
RUN_LIMIT = 5  # Number of pairs to graph

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}


def get_workflow_id(workflow_name):
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/actions/workflows"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    for wf in response.json().get("workflows", []):
        if wf["name"] == workflow_name:
            return wf["id"]
    return None


def get_successful_runs(wf_id, limit=30):
    # Fetch a slightly larger pool to ensure we find matches
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/actions/workflows/{wf_id}/runs"
    params = {"status": "success", "per_page": limit}
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json().get("workflow_runs", [])


def get_jobs(run_id):
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/actions/runs/{run_id}/jobs"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json().get("jobs", [])


def clean_job_name(raw_name):
    """Simplifies the job name for the Gantt chart."""
    clean = raw_name.split('/')[-1]
    clean = clean.replace("(dev)", "").strip()
    return clean


def main():
    if not TOKEN: return

    print("Fetching Workflow IDs...")
    ci_id = get_workflow_id(CI_WORKFLOW)
    cd_id = get_workflow_id(CD_WORKFLOW)

    if not ci_id or not cd_id:
        print("❌ Error: Could not find workflow IDs. Check OWNER and REPO names.")
        return

    print("Fetching Runs...")
    ci_runs = get_successful_runs(ci_id)
    cd_runs = get_successful_runs(cd_id)

    pairs_found = 0

    for ci_run in ci_runs:
        if pairs_found >= RUN_LIMIT:
            break

        branch = ci_run["head_branch"]
        matching_cd_run = None

        # Look for the CI branch name inside the CD's display_title (Commit message)
        for cd_run in cd_runs:
            title = cd_run.get("display_title", "")
            if branch in title:
                matching_cd_run = cd_run
                break

        if not matching_cd_run:
            continue

        pairs_found += 1

        print(f"\n{'=' * 70}")
        print(f" 📊 COMPOSITE PIPELINE (Branch: {branch})")
        print(f" CI Run: {ci_run['id']} | CD Run: {matching_cd_run['id']}")
        print(f"{'=' * 70}")

        ci_jobs = get_jobs(ci_run["id"])
        cd_jobs = get_jobs(matching_cd_run["id"])

        mermaid_lines = []

        # --- PROCESS CI JOBS ---
        mermaid_lines.append(f"    section {CI_WORKFLOW}")
        for job in ci_jobs:
            if job.get("conclusion") == "skipped" or not job.get("started_at"): continue
            name = clean_job_name(job["name"])
            safe_id = "ci_" + re.sub(r'[^a-zA-Z0-9]', '', name)
            mermaid_lines.append(f"    {name} : {safe_id}, {job['started_at']}, {job['completed_at']}")

        # --- PROCESS CD JOBS ---
        mermaid_lines.append(f"    section {CD_WORKFLOW}")
        for job in cd_jobs:
            if job.get("conclusion") == "skipped" or not job.get("started_at"): continue
            name = clean_job_name(job["name"])
            safe_id = "cd_" + re.sub(r'[^a-zA-Z0-9]', '', name)
            mermaid_lines.append(f"    {name} : {safe_id}, {job['started_at']}, {job['completed_at']}")

        # --- OUTPUT COMPOSITE MERMAID ---
        print("\n```mermaid")
        print("gantt")
        print(f"    title Full Deployment Lifecycle ({branch})")
        print("    dateFormat  YYYY-MM-DDTHH:mm:ssZ")
        print("    axisFormat  %H:%M:%S")
        for line in mermaid_lines:
            print(line)
        print("```\n")


if __name__ == "__main__":
    main()