import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURATION ---
GITLAB_API_TOKEN = "glpat-hxi5ndQVkHsNjcg4CahK"
GITLAB_PROJECT_ID = "69058284"  # e.g., 123456
GITLAB_API_URL = f"https://gitlab.com/api/v4/projects/{GITLAB_PROJECT_ID}/issues"

GOOGLE_SHEET_NAME = "Null Hypothesis time report"
#CREDENTIALS_FILE = r"C:\Users\kadle\Codes\dp_automateddwh\.secrets\dataproject-458415-9925d2283dfa.json" #windows
CREDENTIALS_FILE = "../.secrets/dataproject-458415-d3113f2be44e.json" #linux

# --- SETUP GOOGLE SHEETS ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
client = gspread.authorize(creds)
sheet = client.open(GOOGLE_SHEET_NAME).sheet1  # First tab

# --- FETCH ISSUES WITH TIME LOGS FROM GITLAB ---
headers = {"Private-Token": GITLAB_API_TOKEN}
params = {"per_page": 100}
response = requests.get(GITLAB_API_URL, headers=headers, params=params)
issues = response.json()

# --- FETCH CURRENT SHEET DATA BEFORE CLEARING ---
existing_data = sheet.get_all_records()
existing_times = {str(row["Issue ID"]): row["Time Spent (h)"] for row in existing_data}

# --- CLEAR AND RESET HEADERS ---
sheet.clear()
sheet.append_row(["Issue ID", "Title", "Time Spent (h)", "Assignee"])

# --- TRACK CHANGES ---
updated_issues = []

# --- PROCESS AND WRITE TO SHEET ---
for issue in issues:
    issue_id = str(issue["iid"])
    title = issue["title"]
    spent_h = round(issue["time_stats"]["total_time_spent"] / 3600, 2)
    assignee = issue["assignee"]["name"] if issue.get("assignee") else "Unassigned"

    # Check if this issue existed and has increased time
    old_time = float(existing_times.get(issue_id, 0))
    if spent_h > old_time:
        updated_issues.append((issue_id, title, old_time, spent_h))

    # Append to sheet
    sheet.append_row([
        issue_id,
        title,
        spent_h,
        assignee
    ])

# --- REPORT CHANGES ---
if updated_issues:
    print("\n🕒 Time updates found:")
    for issue_id, title, old, new in updated_issues:
        diff = round(new - old, 2)
        print(f"• Issue #{issue_id} '{title}': +{diff}h (was {old}h, now {new}h)")
else:
    print("No new time entries found.")

print("✅ Time logs exported to Google Sheet.")
