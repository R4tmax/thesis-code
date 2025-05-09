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
    """
    Loads alert definitions from a YAML file.

    Args:
        path (str): Path to the YAML file.

    Returns:
        list: List of alert definitions as dictionaries.
    """
    with open(path, "r") as file:
        return yaml.safe_load(file)

ALERT_DEFINITIONS = load_alert_definitions()

# ─────────────────────────────────────────────────────────────
# MAIN FUNCTION (CLOUD FUNCTION ENTRY POINT)
# ─────────────────────────────────────────────────────────────

@functions_framework.http
def read_and_alert(request):
    """
    Entry point for the Cloud Function.
    Executes alert processing based on request payload (trigger or report mode).

    Args:
        request (flask.Request): HTTP request object.

    Returns:
        tuple: HTTP response message and status code.
    """
    try:
        logging.info("Starting alert check process.")
        bq_client = bigquery.Client()

        data = request.get_json()
        report_type = data.get('report_type', 'trigger')  # Default to 'trigger' if not provided

        alerts, report_alerts = process_alert_definitions(bq_client)

        if report_type == 'report':
            send_alert_report(report_alerts)
        elif report_type == 'trigger':
            send_trigger_alerts(alerts)

        logging.info("Alert check process completed successfully.")
        return ("Alert check completed.", 200)

    except Exception as e:
        logging.exception("Error during alert check.")
        return (f"Error occurred: {str(e)}", 500)

# ─────────────────────────────────────────────────────────────
# PROCESS ALERT DEFINITIONS
# ─────────────────────────────────────────────────────────────

def process_alert_definitions(bq_client):
    """
    Processes all alert definitions, executes queries, and classifies alerts.

    Args:
        bq_client (bigquery.Client): BigQuery client instance.

    Returns:
        tuple: Lists of trigger alerts and report alerts.
    """
    alerts = []
    report_alerts = []

    for alert_def in ALERT_DEFINITIONS:
        if not alert_def.get("enabled", True):
            continue

        count = run_bq_query(bq_client, alert_def["query"])

        if count > alert_def.get("threshold", 0):
            alert = build_alert(alert_def, count)
            if alert_def.get("alert_kind", "trigger") == "trigger":
                alerts.append(alert)
            else:
                report_alerts.append(alert)

    return alerts, report_alerts

def run_bq_query(bq_client, query):
    """
    Executes a BigQuery query and returns the count result.

    Args:
        bq_client (bigquery.Client): BigQuery client.
        query (str): SQL query string.

    Returns:
        int: Count result from the query.
    """
    logging.info(f"Running query: {query}")
    result = list(bq_client.query(query).result())
    count = result[0].count if result else 0
    logging.info(f"Query completed. Count: {count}")
    return count

def build_alert(alert_def, count):
    """
    Builds an alert object based on definition and query result.

    Args:
        alert_def (dict): Alert definition.
        count (int): Result count from query.

    Returns:
        dict: Alert data structure.
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
# SEND ALERTS
# ─────────────────────────────────────────────────────────────

def send_alert_report(report_alerts):
    """
    Sends a summary email containing all report-type alerts.

    Args:
        report_alerts (list): List of report-type alerts.
    """
    if report_alerts:
        report_message = build_report_message(report_alerts)
        recipients = get_report_recipients(report_alerts)
        logging.info("Sending report email for all alerts.")
        send_email(report_message, "Report: Alerts Summary", "All Alerts Report", recipients)
        logging.info("Report email sent.")

def build_report_message(report_alerts):
    """
    Builds an HTML report message for all alerts.

    Args:
        report_alerts (list): List of report alerts.

    Returns:
        str: HTML formatted report message.
    """
    return "<br><br>".join([f"{alert['message']}<br><a href=\"{alert['link']}\" target=\"_blank\">View Details</a>" for alert in report_alerts])

def get_report_recipients(report_alerts):
    """
    Gathers all recipients from the report alerts.

    Args:
        report_alerts (list): List of report alerts.

    Returns:
        list: Combined list of email recipients.
    """
    return [recipient for alert in report_alerts for recipient in alert['recipients']]

def send_trigger_alerts(alerts):
    """
    Sends emails for each individual trigger-type alert.

    Args:
        alerts (list): List of trigger alerts.
    """
    for alert in alerts:
        msg = f"{alert['message']}<br><br><a href=\"{alert['link']}\" target=\"_blank\">View Details</a>"
        logging.info(f"Sending email for alert: {alert['type']}")
        send_email(msg, alert['type'], alert['email_subject'], alert['recipients'])
        logging.info(f"Email sent for alert: {alert['type']}")

# ─────────────────────────────────────────────────────────────
# SEND EMAIL FUNCTION
# ─────────────────────────────────────────────────────────────

def send_email(alert_message: str, alert_type: str, subject: str, recipients: list):
    """
    Sends an HTML email via the Mailgun API.

    Args:
        alert_message (str): Email body content.
        alert_type (str): Type of the alert.
        subject (str): Subject of the email.
        recipients (list): List of email recipients.
    """
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

# ─────────────────────────────────────────────────────────────
# SECRET MANAGER HELPER
# ─────────────────────────────────────────────────────────────

def get_secret(secret_id: str) -> str:
    """
    Retrieves a secret value from Google Secret Manager.

    Args:
        secret_id (str): The secret ID to retrieve.

    Returns:
        str: The secret value as a string.
    """
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
