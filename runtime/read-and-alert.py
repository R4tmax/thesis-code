import functions_framework
import os
from google.cloud import bigquery
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

@functions_framework.http
def check_and_send_alert(request):
    project_id = os.environ['GCP_PROJECT']
    dataset = 'alerts_tmp'
    table = 'missing_sales_alert'

    client = bigquery.Client(project=project_id)
    query = f"""
        SELECT alert_message FROM `{project_id}.{dataset}.{table}`
        WHERE DATE(_PARTITIONTIME) = CURRENT_DATE() OR TRUE
        LIMIT 1
    """
    result = client.query(query).result()

    rows = list(result)
    if rows:
        alert_message = rows[0]['alert_message']
        send_email(alert_message)

    return 'Checked alerts', 200

def send_email(message):
    sg = SendGridAPIClient(os.environ['SENDGRID_API_KEY'])
    email = Mail(
        from_email='alerts@yourdomain.com',
        to_emails='team@yourdomain.com',
        subject='BigQuery Alert 🚨',
        plain_text_content=message
    )
    sg.send(email)
