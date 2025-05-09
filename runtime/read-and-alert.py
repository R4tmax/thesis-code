import functions_framework
from google.cloud import bigquery
import requests
import logging
from jinja2 import Template
import os
import yaml
from google.cloud import secretmanager

# Configure basic logging format
logging.basicConfig(level=logging.INFO)

# ─────────────────────────────────────────────────────────────
# LOAD ALERT DEFINITIONS FROM YAML FILE
# ─────────────────────────────────────────────────────────────

def load_alert_definitions(path="alert_definitions.yaml"):
    with open(path, "r") as file:
        return yaml.safe_load(file)

ALERT_DEFINITIONS = load_alert_definitions()

# ─────────────────────────────────────────────────────────────
# MAIN FUNCTION
# ─────────────────────────────────────────────────────────────

@functions_framework.http
def read_and_alert(request):
    try:
        logging.info("Starting alert check process.")
        bq_client = bigquery.Client()
        alerts = []

        for alert_def in ALERT_DEFINITIONS:
            if not alert_def.get("enabled", True):
                continue

            logging.info(f"Running query for alert type: {alert_def['type']}")
            result = list(bq_client.query(alert_def["query"]).result())
            count = result[0].count if result else 0
            logging.info(f"Query completed. Count: {count}")

            threshold = alert_def.get("threshold", 0)
            if count > threshold:
                message = alert_def["message_template"].replace("{{count}}", str(count))
                alerts.append({
                    "type": alert_def["type"],
                    "message": message,
                    "link": alert_def.get("link", ""),
                    "recipients": alert_def.get("recipients", []),
                    "email_subject": alert_def.get("email_subject", f"Alert: {alert_def['type']}"),
                    "alert_kind": alert_def.get("alert_kind", "trigger"),
                    "severity": alert_def.get("severity", "info")
                })
                logging.info(f"Alert triggered for: {alert_def['type']}")

        for alert in alerts:
            msg = (
                f"{alert['message']}<br><br>"
                f"<a href=\"{alert['link']}\" target=\"_blank\">View Details</a>"
            )
            logging.info(f"Sending email for alert: {alert['type']}")
            send_email(msg, alert['type'], alert['email_subject'], alert['recipients'])
            logging.info(f"Email sent for alert: {alert['type']}")

        logging.info("Alert check process completed successfully.")
        return ("Alert check completed.", 200)

    except Exception as e:
        logging.exception("Error during alert check.")
        return (f"Error occurred: {str(e)}", 500)

# ─────────────────────────────────────────────────────────────
# SECRET MANAGER HELPER
# ─────────────────────────────────────────────────────────────

def get_secret(secret_id: str) -> str:
    try:
        name = f"projects/749895389873/secrets/{secret_id}/versions/latest"
        client = secretmanager.SecretManagerServiceClient()
        response = client.access_secret_version(request={"name": name})
        secret = response.payload.data.decode("UTF-8")
        logging.info(f"Secret retrieved successfully: {secret_id}")
        return secret
    except Exception as e:
        logging.exception(f"Failed to get secret: {secret_id}")
        raise

# ─────────────────────────────────────────────────────────────
# SEND EMAIL FUNCTION
# ─────────────────────────────────────────────────────────────

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
                f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages",
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
