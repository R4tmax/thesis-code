import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURATION ---
GITLAB_API_TOKEN = "glpat-hxi5ndQVkHsNjcg4CahK"
GITLAB_PROJECT_ID = "69058284"  # e.g., 123456
GITLAB_API_URL = f"https://gitlab.com/api/v4/projects/{GITLAB_PROJECT_ID}/issues"

GOOGLE_SHEET_NAME = "Null Hypothesis time report"
CREDENTIALS_FILE = r"C:\Users\kadle\Codes\dp_automateddwh\.secrets\dataproject-458415-9925d2283dfa.json"

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

# --- CLEAR EXISTING SHEET & SET HEADERS ---
sheet.clear()
sheet.append_row(["Issue ID", "Title", "Time Spent (h)", "Assignee"])

# --- PROCESS AND WRITE TO SHEET ---
for issue in issues:
    spent = issue["time_stats"]["total_time_spent"] /3600
    estimate = issue["time_stats"]["time_estimate"]
    assignee = issue["assignee"]["name"] if issue.get("assignee") else "Unassigned"

    sheet.append_row([
        issue["iid"],
        issue["title"],
        spent,
        assignee
    ])

print("✅ Time logs exported to Google Sheet.")
