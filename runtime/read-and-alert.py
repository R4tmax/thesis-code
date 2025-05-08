import functions_framework
from google.cloud import bigquery
import requests
import logging
from jinja2 import Template
import os
from google.cloud import secretmanager

# ─────────────────────────────────────────────────────────────
# ALERT DEFINITIONS – easily extensible list of alert types
# ─────────────────────────────────────────────────────────────

ALERT_DEFINITIONS = [
    {
        "type": "Unpaid Invoices",
        "query": "SELECT COUNT(*) as count FROM `dataproject-458415.dwh_develop.mv_unpaid_invoices`",
        "message_template": "Found {{count}} unpaid invoices.",
        "link": "https://docs.google.com/spreadsheets/d/1RRNcQdD2aAUcmeMbUz0JJgrJutjiGd1ynl2XXVkNecE/edit?usp=sharing"
    },
    {
        "type": "High-Value Invoices",
        "query": "SELECT COUNT(*) as count FROM `dataproject-458415.dwh_develop.mv_high_value_invoices`",
        "message_template": "Found {{count}} invoices with value above 10,000.",
        "link": "https://docs.google.com/spreadsheets/d/16Mvclc4aWVr-HJZaqrtDgXfwrWCv6EisSYxBdEjIS8E/edit?usp=sharing"
    }
]

# ─────────────────────────────────────────────────────────────
# MAIN FUNCTION
# ─────────────────────────────────────────────────────────────

@functions_framework.http
def read_and_alert(request):
    """
    Google Cloud Function entry point.
    Checks BigQuery views for specific alert conditions
    and sends email notifications if issues are found.
    """
    try:
        bq_client = bigquery.Client()
        alerts = []

        for alert_def in ALERT_DEFINITIONS:
            result = list(bq_client.query(alert_def["query"]).result())
            count = result[0].count if result else 0

            if count > 0:
                message = alert_def["message_template"].replace("{{count}}", str(count))
                alerts.append({
                    "type": alert_def["type"],
                    "message": message,
                    "link": alert_def["link"]
                })

        # Send email notifications for all found alerts
        for alert in alerts:
            msg = (
                f"{alert['message']}<br><br>"
                f"<a href=\"{alert['link']}\" target=\"_blank\">View in Google Sheets</a>"
            )
            send_email(msg, alert['type'])

        return ("Alert check completed.", 200)

    except Exception as e:
        logging.exception("Error during alert check.")
        return (f"Error occurred: {str(e)}", 500)

# ─────────────────────────────────────────────────────────────
# SECRET MANAGER HELPER
# ─────────────────────────────────────────────────────────────

def get_secret(secret_id: str) -> str:
    """
    Retrieve a secret value from Google Secret Manager.
    """
    try:
        name = f"projects/749895389873/secrets/{secret_id}/versions/latest"
        client = secretmanager.SecretManagerServiceClient()
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        logging.exception(f"Failed to get secret: {secret_id}")
        raise

# ─────────────────────────────────────────────────────────────
# SEND EMAIL FUNCTION
# ─────────────────────────────────────────────────────────────

def send_email(alert_message: str, alert_type: str = "Invoice Alert"):
    """
    Send an alert email via Mailgun using data from Secret Manager.
    """
    try:
        MAILGUN_API = get_secret("mailgun_api")
        MAILGUN_DOMAIN = get_secret("mailgun_domain")
        RECIPIENT = get_secret("recipient")

        # Load HTML email template
        with open("email_template.html", "r") as f:
            html_template = f.read()

        # Render HTML email content
        template = Template(html_template)
        rendered_html = template.render(alert_type=alert_type, alert_message=alert_message)

        # Send email via Mailgun
        response = requests.post(
            f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages",
            auth=("api", MAILGUN_API),
            data={
                "from": f"Alert System <alert@{MAILGUN_DOMAIN}>",
                "to": RECIPIENT,
                "subject": f"⚠️ {alert_type} Detected!",
                "html": rendered_html
            }
        )
        response.raise_for_status()
        logging.info("Alert email sent successfully.")

    except requests.exceptions.RequestException:
        logging.exception("Mailgun API request failed.")
        raise

    except Exception:
        logging.exception("General error while sending email.")
        raise