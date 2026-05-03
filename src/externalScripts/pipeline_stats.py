import subprocess
import requests
import pandas as pd
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
RUN_LIMIT = 999

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


def get_successful_runs(wf_id, limit=50):
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


def calc_duration(start_str, end_str):
    """Parses ISO 8601 strings and returns duration in seconds."""
    if not start_str or not end_str: return None
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    t_start = datetime.strptime(start_str, fmt)
    t_end = datetime.strptime(end_str, fmt)
    return int((t_end - t_start).total_seconds())


def format_seconds(seconds):
    """Helper to convert seconds back to MM:SS for readable printing."""
    if pd.isna(seconds): return "00:00"
    mins, secs = divmod(int(seconds), 60)
    return f"{mins:02d}:{secs:02d}"


def main():
    if not TOKEN: return

    print("Fetching Workflow IDs...")
    ci_id = get_workflow_id(CI_WORKFLOW)
    cd_id = get_workflow_id(CD_WORKFLOW)

    if not ci_id or not cd_id:
        print("❌ Error: Could not find workflows.")
        return

    print(f"Fetching Recent Successful Runs (Scanning up to {RUN_LIMIT} pairs)...")
    ci_runs = get_successful_runs(ci_id)
    cd_runs = get_successful_runs(cd_id)

    pairs_found = 0
    pipeline_data = []
    job_data = []

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

        ci_duration = calc_duration(ci_run["created_at"], ci_run["updated_at"])
        cd_duration = calc_duration(matching_cd_run["created_at"], matching_cd_run["updated_at"])

        pipeline_data.append({
            "Pair ID": pairs_found,
            "Branch": branch,
            "CI Duration (sec)": ci_duration,
            "CD Duration (sec)": cd_duration,
            "Total Pipeline Wall-Clock (sec)": ci_duration + cd_duration
        })

        for job in get_jobs(ci_run["id"]):
            if job.get("conclusion") == "skipped" or not job.get("started_at"): continue
            job_data.append({
                "Job Name": f"[CI] {clean_job_name(job['name'])}",
                "Duration (sec)": calc_duration(job["started_at"], job["completed_at"])
            })

        for job in get_jobs(matching_cd_run["id"]):
            if job.get("conclusion") == "skipped" or not job.get("started_at"): continue
            job_data.append({
                "Job Name": f"[CD] {clean_job_name(job['name'])}",
                "Duration (sec)": calc_duration(job["started_at"], job["completed_at"])
            })

    if not pipeline_data:
        print("No paired runs found.")
        return

    df_pipeline = pd.DataFrame(pipeline_data)
    df_jobs = pd.DataFrame(job_data)

    quantiles_to_calc = [0.25, 0.50, 0.75, 0.90]

    print("\n===========================================================================")
    print(f" 📊 MACRO LEVEL: PIPELINE EXECUTION STATISTICS (N={pairs_found} paired runs)")
    print("===========================================================================")
    pipe_stats = df_pipeline[["CI Duration (sec)", "CD Duration (sec)", "Total Pipeline Wall-Clock (sec)"]].describe(
        percentiles=quantiles_to_calc)

    pipe_stats_formatted = pipe_stats.apply(lambda x: x.map(format_seconds))
    pipe_stats_formatted.loc['count'] = pipe_stats.loc['count'].astype(int).astype(str)
    print(pipe_stats_formatted)

    print("\n===========================================================================")
    print(" 🔬 MICRO LEVEL: INDIVIDUAL JOB STATISTICS")
    print("===========================================================================")
    job_grouped = df_jobs.groupby("Job Name")["Duration (sec)"].describe(percentiles=quantiles_to_calc)

    job_grouped = job_grouped.sort_values(by="mean", ascending=False)

    job_grouped_formatted = job_grouped.apply(lambda x: x.map(format_seconds) if x.name != 'count' else x)
    job_grouped_formatted['count'] = job_grouped['count'].astype(int).astype(str)

    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 200)
    print(job_grouped_formatted)
    print("\n*Note: '50%' represents the Median execution time. '90%' represents the P90 SLA metric.*")


if __name__ == "__main__":
    main()