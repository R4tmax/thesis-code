import functions_framework
from google.cloud import bigquery
import requests
import logging
from jinja2 import Template

# URLs to Google Sheets dashboards linked to specific invoice views
UNPAID_SHEET_URL = ""
HIGH_VALUE_SHEET_URL = ""

@functions_framework.http
def read_and_alert(request):
    """
    Google Cloud Function entrypoint.
    Checks BigQuery views for specific alert conditions (e.g., unpaid or high-value invoices)
    and sends email alerts if issues are found.
    """
    try:
        # Initialize BigQuery client
        bq_client = bigquery.Client()

        alerts = []

        # Query for unpaid invoices
        unpaid_query = "SELECT COUNT(*) as count FROM `dataproject-458415.dwh_develop.mv_unpaid_invoices`"
        unpaid_count = list(bq_client.query(unpaid_query).result())[0].count
        if unpaid_count > 0:
            alerts.append({
                "type": "Nezaplacené faktury",  # Unpaid invoices
                "message": f"Bylo nalezeno {unpaid_count} nezaplacených faktur.",
                "link": UNPAID_SHEET_URL
            })

        # Query for high-value invoices
        high_value_query = "SELECT COUNT(*) as count FROM `dataproject-458415.dwh_develop.mv_high_value_invoices`"
        high_count = list(bq_client.query(high_value_query).result())[0].count
        if high_count > 0:
            alerts.append({
                "type": "Faktury s vysokou hodnotou",  # High-value invoices
                "message": f"Bylo nalezeno {high_count} faktur s hodnotou nad 10 000.",
                "link": HIGH_VALUE_SHEET_URL
            })

        # Send email notifications for all alerts found
        for alert in alerts:
            msg = (
                f"{alert['message']}<br><br>"
                f"<a href=\"{alert['link']}\" target=\"_blank\">Zobrazit v Google Sheets</a>"
            )
            send_email(msg, alert['type'])

        return ("Alert check completed.", 200)

    except Exception as e:
        # Log unexpected exceptions and return error response
        logging.exception("Error during alert check.")
        return (f"Error occurred: {str(e)}", 500)


def send_email(alert_message, alert_type="Invoice Alert"):
    """
    Sends an HTML email using the Mailgun API with the alert message and type.

    Args:
        alert_message (str): The body of the alert message, including a link.
        alert_type (str): The type of alert, used for email subject and header.
    """
    try:
        # In production, these should come from Secret Manager or environment variables
        MAILGUN_API = ""
        MAILGUN_DOMAIN = ""
        RECIPIENT = ""

        # Validate all required credentials
        if not all([MAILGUN_API, MAILGUN_DOMAIN, RECIPIENT]):
            raise ValueError("Missing required environment values: MAILGUN_API, MAILGUN_DOMAIN, RECIPIENT")

        # Load HTML template for the email
        with open("email_template.html", "r") as f:
            html_template = f.read()

        # Render HTML with dynamic content using Jinja2
        template = Template(html_template)
        rendered_html = template.render(alert_type=alert_type, alert_message=alert_message)

        # Send email using Mailgun API
        response = requests.post(
            f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages",
            auth=("api", MAILGUN_API),
            data={
                "from": f"Alert System <alert@{MAILGUN_DOMAIN}>",
                "to": RECIPIENT,
                "subject": f"⚠️ {alert_type} Detekováno!",
                "html": rendered_html
            }
        )
        # Raise error if request failed
        response.raise_for_status()
        logging.info("Alert email sent successfully.")

    except requests.exceptions.RequestException:
        # Handle failed email sending due to network/API issues
        logging.exception("Failed to send alert email.")
        raise

    except Exception as e:
        # Log other types of email-sending errors
        logging.exception("General email sending error.")
        raise
