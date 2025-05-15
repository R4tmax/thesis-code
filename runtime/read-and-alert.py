import functions_framework
from google.cloud import bigquery
from google.cloud import secretmanager

import requests
import logging
import base64
import json
from email.mime.text import MIMEText
from jinja2 import Template
import yaml

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Configure basic logging
logging.basicConfig(level=logging.INFO)

# ─────────────────────────────────────────────────────────────
# LOAD ALERT DEFINITIONS FROM YAML
# ─────────────────────────────────────────────────────────────

def load_alert_definitions(path="alert_definitions.yaml"):
    """
    Load alert configuration from a YAML file.
    """
    with open(path, "r") as file:
        return yaml.safe_load(file)

# Load all alert definitions at cold start
ALERT_DEFINITIONS = load_alert_definitions()

# ─────────────────────────────────────────────────────────────
# MAIN FUNCTION – CLOUD FUNCTION ENTRY POINT
# ─────────────────────────────────────────────────────────────

@functions_framework.http
def read_and_alert(request):
    """
    Entry point for the Cloud Function.
    Based on 'report_type', it either triggers alerts immediately or sends a summary report.
    """
    try:
        logging.info("Starting alert check process.")
        bq_client = bigquery.Client()

        data = request.get_json()
        report_type = data.get('report_type', 'trigger')  # Default to 'trigger'

        alerts = process_alert_definitions(bq_client, report_type)

        if report_type == 'report':
            send_alert_report(alerts)
        elif report_type == 'trigger':
            send_trigger_alerts(alerts)

        logging.info("Alert check process completed successfully.")
        return ("Alert check completed.", 200)

    except Exception as e:
        logging.exception("Error during alert check.")
        return (f"Error occurred: {str(e)}", 500)

# ─────────────────────────────────────────────────────────────
# PROCESS ALERT DEFINITIONS AND RUN QUERIES
# ─────────────────────────────────────────────────────────────

def process_alert_definitions(bq_client, report_type):
    """
    Evaluate alert conditions based on the report type.
    Returns a list of alerts that exceed the defined threshold.
    """
    alerts = []
    for alert_def in ALERT_DEFINITIONS:
        if not alert_def.get("enabled", True):
            continue

        if alert_def.get("alert_kind", "trigger") == report_type:
            count = run_bq_query(bq_client, alert_def["query"])
            if count > alert_def.get("threshold", 0):
                alert = build_alert(alert_def, count)
                alerts.append(alert)

    return alerts

def run_bq_query(bq_client, query):
    """
    Execute a BigQuery query and return the count from the first row.
    """
    logging.info(f"Running query: {query}")
    result = list(bq_client.query(query).result())
    count = result[0].count if result else 0
    logging.info(f"Query completed. Count: {count}")
    return count

def build_alert(alert_def, count):
    """
    Generate an alert object using the alert definition and actual count.
    """
    message = alert_def["message_template"].replace("{{count}}", str(count))
    return {
        "type": alert_def["type"],
        "message": message,
        "link": alert_def.get("link", ""),
        "recipients": alert_def.get("recipients", []),
        "email_subject": alert_def.get("email_subject", f"Alert: {alert_def['type']}"),
        "alert_kind": alert_def.get("alert_kind", "trigger"),
        "severity": alert_def.get("severity", "info")
    }

# ─────────────────────────────────────────────────────────────
# SEND TRIGGER ALERTS
# ─────────────────────────────────────────────────────────────

def send_trigger_alerts(alerts):
    """
    Send each triggered alert immediately to all recipients.
    """
    for alert in alerts:
        msg = f"{alert['message']}<br><br><a href=\"{alert['link']}\" target=\"_blank\">View Details</a>"
        logging.info(f"Sending email for alert: {alert['type']}")
        send_email(msg, alert['type'], alert['email_subject'], alert['recipients'])
        logging.info(f"Email sent for alert: {alert['type']}")

# ─────────────────────────────────────────────────────────────
# SEND REPORT ALERTS
# ─────────────────────────────────────────────────────────────

def send_alert_report(report_alerts):
    """
    Aggregate alerts by recipient and send a single summary email.
    """
    recipient_alerts_map = {}

    for alert in report_alerts:
        for recipient in alert['recipients']:
            recipient_alerts_map.setdefault(recipient, []).append(alert)

    for recipient, alerts in recipient_alerts_map.items():
        report_message = build_report_message(alerts)
        logging.info(f"Sending report email to {recipient} with {len(alerts)} alerts.")
        send_email(report_message, "Report: Alerts Summary", "Alerts Report", [recipient])
        logging.info(f"Report email sent to {recipient}.")

def build_report_message(report_alerts):
    """
    Build HTML summary for a group of alerts.
    """
    return "<br><br>".join([
        f"{alert['message']}<br><a href=\"{alert['link']}\" target=\"_blank\">View Details</a>"
        for alert in report_alerts
    ])

# ─────────────────────────────────────────────────────────────
# EMAIL SENDING LOGIC
# ─────────────────────────────────────────────────────────────


# Gmail API private account
def send_email(alert_message: str, alert_type: str, subject: str, recipients: list):
    """
    Send an email using Gmail API with an HTML alert message.
    Gmail API credentials are loaded from Secret Manager.
    """
    try:
        client_id = get_secret("Gmail_client_id")
        client_secret = get_secret("Gmail_client_secret")
        refresh_token = get_secret("Gmail_refresh_token")
        sender_email = "email.alerttestbot@gmail.com"

        creds = Credentials(
            None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret
        )
        if not creds.valid or creds.expired:
            creds.refresh(Request())

        service = build('gmail', 'v1', credentials=creds)

        with open("email_template.html", "r") as f:
            html_template = f.read()
        template = Template(html_template)
        rendered_html = template.render(alert_type=alert_type, alert_message=alert_message)

        for recipient in recipients:
            message = MIMEText(rendered_html, "html")
            message["to"] = recipient
            message["from"] = sender_email
            message["subject"] = subject
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

            response = service.users().messages().send(
                userId="me", body={"raw": raw_message}).execute()
            logging.info(f"Email sent to {recipient}, message ID: {response.get('id')}")

    except Exception:
        logging.exception("Failed to send Gmail.")
        raise

"""
# MAILGUN
def send_email(alert_message: str, alert_type: str, subject: str, recipients: list):
    try:
        MAILGUN_API = get_secret("mailgun_api")
        MAILGUN_DOMAIN = get_secret("mailgun_domain")

        with open("email_template.html", "r") as f:
            html_template = f.read()

        template = Template(html_template)
        rendered_html = template.render(alert_type=alert_type, alert_message=alert_message)

        for recipient in recipients:
            response = requests.post(
                f"https://api.eu.mailgun.net/v3/{MAILGUN_DOMAIN}/messages",
                auth=("api", MAILGUN_API),
                data={
                    "from": f"Alert System <alert@{MAILGUN_DOMAIN}>",
                    "to": recipient,
                    "subject": subject,
                    "html": rendered_html
                }
            )
            response.raise_for_status()
            logging.info(f"Email sent to {recipient}")

    except requests.exceptions.RequestException:
        logging.exception("Mailgun API request failed.")
        raise
    except Exception:
        logging.exception("General error while sending email.")
        raise
"""
# ─────────────────────────────────────────────────────────────
# SECRET MANAGER ACCESS
# ─────────────────────────────────────────────────────────────

def get_secret(secret_id: str) -> str:
    """
    Retrieve a secret from Google Secret Manager.
    """
    try:
        name = f"projects/749895389873/secrets/{secret_id}/versions/latest"
        client = secretmanager.SecretManagerServiceClient()
        response = client.access_secret_version(request={"name": name})
        secret = response.payload.data.decode("UTF-8")
        logging.info(f"Secret retrieved successfully: {secret_id}")
        return secret
    except Exception:
        logging.exception(f"Failed to get secret: {secret_id}")
        raise


