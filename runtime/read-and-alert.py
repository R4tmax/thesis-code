import functions_framework
from google.cloud import bigquery, secretmanager
import requests
import logging
from jinja2 import Template
import yaml

# ──────────────
# Logging setup
# ──────────────
logging.basicConfig(level=logging.INFO)


# ───────────────────────────────────────
# CONFIGURATION LOADING
# ───────────────────────────────────────

def load_alert_definitions(path="alert_definitions.yaml"):
    """Load alert configuration from YAML."""
    with open(path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


ALERT_DEFINITIONS = load_alert_definitions()


# ───────────────────────────────────────
# SECRET MANAGER UTILITIES
# ───────────────────────────────────────

def get_secret(secret_id: str) -> str:
    """Retrieve secret from Google Secret Manager."""
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/749895389873/secrets/{secret_id}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        secret = response.payload.data.decode("UTF-8")
        logging.info(f"Secret '{secret_id}' retrieved successfully.")
        return secret
    except Exception:
        logging.exception(f"Failed to retrieve secret '{secret_id}'.")
        raise


# ───────────────────────────────────────
# BIGQUERY QUERY EXECUTION
# ───────────────────────────────────────

def run_bq_query(bq_client, query: str) -> int:
    """Run BigQuery query and return the first count result."""
    logging.info(f"Executing query:\n{query}")
    result = list(bq_client.query(query).result())
    count = getattr(result[0], "count", 0) if result else 0
    logging.info(f"Query result count: {count}")
    return count


# ───────────────────────────────────────
# ALERT PROCESSING
# ───────────────────────────────────────

def build_alert(alert_def: dict, count: int) -> dict:
    """Build alert message and metadata from alert definition."""
    message = alert_def["message_template"].replace("{{count}}", str(count))
    return {
        "type": alert_def["type"],
        "message": message,
        "link": alert_def.get("link", ""),
        "recipients": alert_def.get("recipients", []),
        "email_subject": alert_def.get("email_subject", f"Alert: {alert_def['type']}"),
        "alert_kind": alert_def.get("alert_kind", "trigger"),
        "severity": alert_def.get("severity", "info"),
    }


def process_alert_definitions(bq_client, report_type: str) -> list:
    """Filter and evaluate alerts based on report_type."""
    alerts = []
    for alert_def in ALERT_DEFINITIONS:
        if not alert_def.get("enabled", True):
            continue
        if alert_def.get("alert_kind", "trigger") == report_type:
            count = run_bq_query(bq_client, alert_def["query"])
            if count > alert_def.get("threshold", 0):
                alerts.append(build_alert(alert_def, count))
    return alerts


# ───────────────────────────────────────
# EMAIL TEMPLATES AND SENDING
# ───────────────────────────────────────

TEMPLATE_PATHS = {
    "single": "email_trigger.html",
    "report": "email_report.html",
}


def render_email_template(template_name: str, context: dict) -> str:
    """Render email HTML from template and context."""
    if template_name not in TEMPLATE_PATHS:
        raise ValueError(f"Unknown template_name '{template_name}'")
    with open(TEMPLATE_PATHS[template_name], "r", encoding="utf-8") as f:
        template = Template(f.read())
    return template.render(**context)


def send_email_mailgun(subject: str, recipients: list, html_body: str):
    """Send email via Mailgun API to multiple recipients."""
    MAILGUN_API = get_secret("mailgun_api")
    MAILGUN_DOMAIN = get_secret("mailgun_domain")

    for recipient in recipients:
        response = requests.post(
            f"https://api.eu.mailgun.net/v3/{MAILGUN_DOMAIN}/messages",
            auth=("api", MAILGUN_API),
            data={
                "from": f"Alert System <alert@{MAILGUN_DOMAIN}>",
                "to": recipient,
                "subject": subject,
                "html": html_body,
            },
        )
        response.raise_for_status()
        logging.info(f"Email sent to {recipient}")


def send_email(
    alert_message: str,
    alert_type: str,
    subject: str,
    recipients: list,
    template_name: str = "single",
    views: list = None,
    link: str = None,
):
    """Prepare context and send email using Mailgun."""
    if template_name == "single":
        context = {
            "alert_type": alert_type,
            "alert_message": alert_message,
            "subject": subject,
            "link": link or "#",
        }
    elif template_name == "report":
        context = {
            "alert_type": alert_type,
            "subject": subject,
            "views": views or [],
        }
    else:
        raise ValueError(f"Unsupported template_name '{template_name}'")

    html_body = render_email_template(template_name, context)
    send_email_mailgun(subject, recipients, html_body)


# ───────────────────────────────────────
# ALERT SENDING LOGIC
# ───────────────────────────────────────

def send_trigger_alerts(alerts: list):
    """Send immediate emails for each triggered alert."""
    for alert in alerts:
        logging.info(f"Sending trigger alert email: {alert['type']}")
        send_email(
            alert_message=alert["message"],
            alert_type=alert["type"],
            subject=alert["email_subject"],
            recipients=alert["recipients"],
            template_name="single",
            link=alert["link"],
        )


def build_report_message(alerts: list) -> dict:
    """Build aggregated alert views for report email template."""
    views = [
        {"alert_type": a["type"], "alert_message": a["message"], "link": a["link"]}
        for a in alerts
    ]
    return {"views": views}


def send_alert_report(report_alerts: list):
    """Send a summary email report, grouped by recipient."""
    alerts_by_recipient = {}
    for alert in report_alerts:
        for recipient in alert["recipients"]:
            alerts_by_recipient.setdefault(recipient, []).append(alert)

    for recipient, alerts in alerts_by_recipient.items():
        report_context = build_report_message(alerts)
        logging.info(f"Sending report email to {recipient} with {len(alerts)} alerts.")
        send_email(
            alert_message="",  # Not used in report
            alert_type="Summary Report",
            subject="Alerts Report",
            recipients=[recipient],
            template_name="report",
            views=report_context["views"],
        )


# ───────────────────────────────────────
# CLOUD FUNCTION ENTRY POINT
# ───────────────────────────────────────

@functions_framework.http
def read_and_alert(request):
    """Cloud Function entry point."""
    try:
        logging.info("Starting alert check process")
        bq_client = bigquery.Client()

        data = request.get_json(force=True) or {}
        report_type = data.get("report_type", "trigger")

        alerts = process_alert_definitions(bq_client, report_type)

        if report_type == "report":
            send_alert_report(alerts)
        elif report_type == "trigger":
            send_trigger_alerts(alerts)
        else:
            logging.warning(f"Unknown report_type '{report_type}', no alerts sent.")

        logging.info("Alert check process completed successfully.")
        return "Alert check completed.", 200

    except Exception as e:
        logging.exception("Error during alert check process")
        return f"Error occurred: {e}", 500
