import functions_framework
from google.cloud import bigquery, secretmanager, storage
import requests
import logging
import sys
from jinja2 import Template
import yaml
import os
import re

# ──────────────
# Logging setup
# ──────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(name)s | %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


# ───────────────────────────────────────
# CONFIGURATION LOADING
# ───────────────────────────────────────

def is_valid_alert_definition(alert_def: dict, bq_client: bigquery.Client) -> bool:
    """Validate alert definition for structure, types, email format, and view existence."""
    required_keys = [
        "name", "view", "message_template", "recipients", "email_subject",
        "alert_kind", "link", "enabled", "threshold"
    ]

    for key in required_keys:
        if key not in alert_def:
            logger.warning(f"Validation failed for alert (missing '{key}'): {alert_def.get('name', 'UNKNOWN_ALERT_NAME')}")
            return False

    if not isinstance(alert_def["name"], str):
        logger.warning(f"Validation failed for alert '{alert_def['name']}': 'name' must be a string.")
        return False
    if not isinstance(alert_def["view"], str):
        logger.warning(f"Validation failed for alert '{alert_def['name']}': 'view' must be a string.")
        return False
    if not isinstance(alert_def["message_template"], str):
        logger.warning(f"Validation failed for alert '{alert_def['name']}': 'message_template' must be a string.")
        return False
    if not isinstance(alert_def["recipients"], list):
        logger.warning(f"Validation failed for alert '{alert_def['name']}': 'recipients' must be a list.")
        return False
    if not isinstance(alert_def["email_subject"], str):
        logger.warning(f"Validation failed for alert '{alert_def['name']}': 'email_subject' must be a string.")
        return False
    if not isinstance(alert_def["alert_kind"], str) or alert_def["alert_kind"] not in ["report", "trigger"]:
        logger.warning(f"Validation failed for alert '{alert_def['name']}': 'alert_kind' must be 'report' or 'trigger'.")
        return False
    if not isinstance(alert_def["link"], str):
        logger.warning(f"Validation failed for alert '{alert_def['name']}': 'link' must be a string.")
        return False
    if not isinstance(alert_def["enabled"], bool):
        logger.warning(f"Validation failed for alert '{alert_def['name']}': 'enabled' must be a boolean.")
        return False
    if not isinstance(alert_def["threshold"], (int, float)):
        logger.warning(f"Validation failed for alert '{alert_def['name']}': 'threshold' must be a number.")
        return False

    if not check_view_exists(bq_client, alert_def["view"]):
        logger.warning(f"Validation failed for alert '{alert_def['name']}': 'view' does not exist: {alert_def['view']}.")
        return False

    if not all(is_valid_email(recipient) for recipient in alert_def["recipients"]):
        logger.warning(f"Validation failed for alert '{alert_def['name']}': 'recipients' contains invalid email addresses.")
        return False

    if "link" in alert_def and not is_valid_url(alert_def["link"]):
        logger.warning(f"Validation failed for alert '{alert_def['name']}': 'link' is not a valid URL.")
        return False

    return True

def is_valid_email(email: str) -> bool:
    """Check if the given string is a valid email address."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))

def is_valid_url(url: str) -> bool:
    """Check if the given string is a valid HTTP or HTTPS URL."""
    pattern = r"^(https?://)?[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/[a-zA-Z0-9/?=&\-._]*)?$"
    return bool(re.match(pattern, url))

def check_view_exists(bq_client: bigquery.Client, view_name: str) -> bool:
    """Check if a BigQuery view exists."""
    try:
        bq_client.get_table(view_name)
        return True
    except Exception as e:
        if hasattr(e, "code") and e.code == 404:
            return False
        logger.warning(f"Error checking view existence: {e}")
        return False

def load_alert_definitions_from_gcs(bucket_name: str, blob_name: str, bq_client: bigquery.Client) -> list:
    """Load and validate alert definitions from a YAML file stored in GCS."""
    valid_definitions = []
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        yaml_content = blob.download_as_text()
        raw_definitions = yaml.safe_load(yaml_content)

        if not isinstance(raw_definitions, list):
            logger.error("Root of the YAML file is not a list. Expected a list of alert definitions.")
            return []

        for i, alert_def in enumerate(raw_definitions):
            if isinstance(alert_def, dict):
                if is_valid_alert_definition(alert_def, bq_client):
                    valid_definitions.append(alert_def)
                else:
                    logger.warning(f"Skipping invalid alert definition at index {i} in GCS blob '{blob_name}'.")
            else:
                logger.warning(f"Skipping malformed item at index {i} in GCS blob '{blob_name}'. Expected a dictionary.")

        logger.info(f"Successfully loaded {len(valid_definitions)} valid alert definitions from gs://{bucket_name}/{blob_name}.")

        if len(raw_definitions) > len(valid_definitions):
            logger.warning(f"{len(raw_definitions) - len(valid_definitions)} alert definitions were skipped due to validation errors.")

        return valid_definitions

    except yaml.YAMLError as e:
        logger.exception(f"Failed to parse YAML content from GCS blob '{blob_name}'. Check YAML syntax.")
        return []
    except Exception as e:
        logger.exception(f"Failed to load or process alert definitions from GCS bucket '{bucket_name}' blob '{blob_name}'.")
        raise


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
        logger.info(f"Secret '{secret_id}' retrieved successfully.")
        return secret
    except Exception:
        logger.exception(f"Failed to retrieve secret '{secret_id}'.")
        raise


# ───────────────────────────────────────
# BIGQUERY QUERY EXECUTION
# ───────────────────────────────────────

def run_bq_query(bq_client, view_name: str) -> int:
    """Run SELECT COUNT(*) query on the given BigQuery view."""
    try:
        query = f"SELECT COUNT(*) as count FROM `{view_name}`"
        logger.info(f"Executing query on view: {view_name}")
        result = list(bq_client.query(query).result())
        count = getattr(result[0], "count", 0) if result else 0
        logger.info(f"Query result count for '{view_name}': {count}")
        return count
    except Exception:
        logger.exception(f"Failed to execute query on view '{view_name}'")
        raise


# ───────────────────────────────────────
# ALERT PROCESSING
# ───────────────────────────────────────

def build_alert(alert_def: dict, count: int) -> dict:
    """Build alert message and metadata from alert definition."""
    message = alert_def["message_template"].replace("{{count}}", str(count))
    return {
        "name": alert_def["name"],
        "message": message,
        "link": alert_def.get("link", ""),
        "recipients": alert_def.get("recipients", []),
        "email_subject": alert_def.get("email_subject", f"Alert: {alert_def['name']}"),
        "alert_kind": alert_def.get("alert_kind", "trigger")
    }


def process_alert_definitions(alert_definitions,bq_client, alert_type: str) -> list:
    """Filter and evaluate alerts based on alert_type."""
    alerts = []
    for alert_def in alert_definitions:
        if not alert_def.get("enabled", True):
            continue
        if alert_def.get("alert_kind", "trigger") == alert_type:
            try:
                count = run_bq_query(bq_client, alert_def["view"])
                if count > alert_def.get("threshold", 0):
                    logger.info(f"Alert '{alert_def['name']}' triggered with count {count}.")
                    alerts.append(build_alert(alert_def, count))
            except Exception:
                logger.warning(f"Skipping alert '{alert_def['name']}' due to query failure.")
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
    try:
        with open(TEMPLATE_PATHS[template_name], "r", encoding="utf-8") as f:
            template = Template(f.read())
        return template.render(**context)
    except Exception:
        logger.exception(f"Failed to render template '{template_name}'")
        raise


def send_email_mailgun(subject: str, recipients: list, html_body: str):
    """Send email via Mailgun API to multiple recipients."""
    MAILGUN_API = get_secret("mailgun_api")
    MAILGUN_DOMAIN = get_secret("mailgun_domain")

    for recipient in recipients:
        try:
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
            logger.info(f"Email sent to {recipient}")
        except Exception:
            logger.exception(f"Failed to send email to {recipient}")


def send_email(
        name: str,
        subject: str,
        recipients: list,
        alert_message: str = None,
        template_name: str = "single",
        views: list = None,
        link: str = None,
):
    """Prepare context and send email using Mailgun."""
    if template_name == "single":
        context = {
            "name": name,
            "alert_message": alert_message,
            "subject": subject,
            "link": link or "#",
        }
    elif template_name == "report":
        context = {
            "name": name,
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
        logger.info(f"Sending trigger alert email: {alert['name']}")
        send_email(
            alert_message=alert["message"],
            name=alert["name"],
            subject=alert["email_subject"],
            recipients=alert["recipients"],
            template_name="single",
            link=alert["link"],
        )


def build_report_message(alerts: list) -> dict:
    """Build aggregated alert views for report email template."""
    views = [
        {"name": a["name"], "alert_message": a["message"], "link": a["link"]}
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
        logger.info(f"Sending report email to {recipient} with {len(alerts)} alerts.")
        send_email(
            name="Summary Report",
            subject="Summary Report Behavio",
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
        logger.info("Starting alert check process")
        bq_client = bigquery.Client()

        data = request.get_json(force=True) or {}
        report_type = data.get("report_type", "trigger")

        gcs_bucket_name = os.environ.get("GCS_BUCKET_NAME")
        gcs_blob_name = os.environ.get("GCS_BLOB_NAME")
        alert_definitions = load_alert_definitions_from_gcs(gcs_bucket_name, gcs_blob_name, bq_client)
        if not alert_definitions:
            logger.error("No valid alert definitions loaded. Exiting.")
            return "No valid alert definitions loaded.", 500

        alerts = process_alert_definitions(alert_definitions, bq_client, report_type)

        if report_type == "report":
            send_alert_report(alerts)
        elif report_type == "trigger":
            send_trigger_alerts(alerts)
        else:
            logger.warning(f"Unknown report_type '{report_type}', no alerts sent.")

        logger.info("Alert check process completed successfully.")
        return "Alert check completed.", 200

    except Exception as e:
        logger.exception("Error during alert check process")
        return f"Error occurred: {e}", 500
