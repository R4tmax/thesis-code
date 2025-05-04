import functions_framework
from google.cloud import bigquery
import requests
import logging


@functions_framework.http
def read_and_alert(request):
    try:
        # Initialize BigQuery client
        bq_client = bigquery.Client()

        # Query to fetch invoice information
        query = """
        SELECT 
            invoice_id, 
            customer_id, 
            customer_name, 
            issue_date, 
            due_date, 
            amount, 
            currency, 
            status, 
            paid_date
        FROM `dataproject-458415.dwh_develop.synth_invoices`
        """

        results = list(bq_client.query(query).result())

        # First alert type: Number of unpaid invoices
        unpaid_invoices = [r for r in results if r.paid_date is None]
        if len(unpaid_invoices) > 10:  # Set your own threshold
            send_email(f"Alert: {len(unpaid_invoices)} unpaid invoices found!")

        # Second alert type: Number of high-value invoices
        high_value_invoices = [r for r in results if r.amount > 10000]
        if len(high_value_invoices) > 5:  # Set your own threshold
            send_email(f"Alert: {len(high_value_invoices)} high-value invoices found!")

        # Third alert type: Total value of unpaid invoices
        unpaid_sum = sum(r.amount for r in unpaid_invoices)
        if unpaid_sum > 100000:  # Set your own threshold
            send_email(f"Alert: Total unpaid invoices amount exceeds 100,000 USD!")

        # Return successful response if everything went fine
        return ("Alert check completed.", 200)

    except Exception as e:
        logging.exception("Error during alert check.")
        return (f"Error occurred: {str(e)}", 500)


def send_email(alert_message):
    """Send an email with the alert message."""
    try:
        # Load credentials from Secret Manager (API key, domain)
        MAILGUN_API = "MAILGUN_API"
        MAILGUN_DOMAIN = "MAILGUN_DOMAIN"
        RECIPIENT = "RECIPIENT"

        # Send the email via Mailgun
        response = requests.post(
            f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages",
            auth=("api", MAILGUN_API),
            data={
                "from": f"Alert System <alert@{MAILGUN_DOMAIN}>",
                "to": RECIPIENT,
                "subject": "Invoice Alert Detected!",
                "text": alert_message
            }
        )
        response.raise_for_status()
        logging.info("Alert email sent successfully.")
    except requests.exceptions.RequestException as e:
        logging.exception("Failed to send alert email.")
        raise
