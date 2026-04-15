import subprocess
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime


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
OWNER = "R4tmax"
REPO = "thesis-code"
TOKEN = get_gh_token()
CI_WORKFLOW = "CI Orchestrator"
CD_WORKFLOW = "CD Orchestrator"
RUN_LIMIT = 1  # Let's just generate the absolute latest composite run

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
    clean = raw_name.split('/')[-1]
    return clean.replace("(dev)", "").strip()


def main():
    if not TOKEN: return

    print("Fetching Workflow IDs...")
    ci_id = get_workflow_id(CI_WORKFLOW)
    cd_id = get_workflow_id(CD_WORKFLOW)

    if not ci_id or not cd_id:
        print("❌ Error: Could not find workflows.")
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

        for cd_run in cd_runs:
            if branch in cd_run.get("display_title", ""):
                matching_cd_run = cd_run
                break

        if not matching_cd_run:
            continue

        pairs_found += 1

        print(f"\nProcessing Composite Pipeline for branch: {branch}...")

        ci_jobs = get_jobs(ci_run["id"])
        cd_jobs = get_jobs(matching_cd_run["id"])

        plot_data = []

        # Process CI Jobs
        for job in ci_jobs:
            if job.get("conclusion") == "skipped" or not job.get("started_at"): continue

            # Calculate duration for the hover text
            fmt = "%Y-%m-%dT%H:%M:%SZ"
            t_start = datetime.strptime(job['started_at'], fmt)
            t_end = datetime.strptime(job['completed_at'], fmt)
            duration_sec = int((t_end - t_start).total_seconds())

            plot_data.append(dict(
                Task=f"[CI] {clean_job_name(job['name'])}",
                Start=job['started_at'],
                Finish=job['completed_at'],
                Stage="1. CI Pipeline",
                Duration=f"{duration_sec} seconds"
            ))

        # Process CD Jobs
        for job in cd_jobs:
            if job.get("conclusion") == "skipped" or not job.get("started_at"): continue

            fmt = "%Y-%m-%dT%H:%M:%SZ"
            t_start = datetime.strptime(job['started_at'], fmt)
            t_end = datetime.strptime(job['completed_at'], fmt)
            duration_sec = int((t_end - t_start).total_seconds())

            plot_data.append(dict(
                Task=f"[CD] {clean_job_name(job['name'])}",
                Start=job['started_at'],
                Finish=job['completed_at'],
                Stage="2. CD Pipeline",
                Duration=f"{duration_sec} seconds"
            ))

        # --- BUILD THE PLOTLY GRAPH ---
        df = pd.DataFrame(plot_data)

        # Sort so the earliest jobs appear at the top of the graph
        df = df.sort_values(by="Start")

        fig = px.timeline(
            df,
            x_start="Start",
            x_end="Finish",
            y="Task",
            color="Stage",
            title=f"Full Deployment Lifecycle: {branch} (Runs {ci_run['id']} -> {matching_cd_run['id']})",
            hover_data=["Duration"],
            color_discrete_sequence=["#2ca02c", "#1f77b4"]  # Green for CI, Blue for CD
        )

        # Invert the Y-axis so the first task is at the top
        fig.update_yaxes(autorange="reversed")

        # Make the layout cleaner for an academic paper
        fig.update_layout(
            font=dict(family="Arial", size=12),
            showlegend=True,
            title_x=0.5  # Center the title
        )

        # Save to an interactive HTML file
        filename = f"pipeline_timeline_{branch}.html"
        fig.write_html(filename)
        print(f"✅ Success! Open '{filename}' in your web browser.")


if __name__ == "__main__":
    main()