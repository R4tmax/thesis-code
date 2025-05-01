import functions_framework
import os
from google.cloud import bigquery
import requests

@functions_framework.http
def check_and_send_alert(request):
    project_id = os.environ['GCP_PROJECT']
    dataset = 'alerts_tmp'
    table = 'missing_sales_alert'

    client = bigquery.Client(project=project_id)
    query = f"""
        SELECT alert_message FROM `{project_id}.{dataset}.{table}`
        WHERE DATE(_PARTITIONTIME) = CURRENT_DATE()
        LIMIT 1
    """
    result = client.query(query).result()
    rows = list(result)

    if rows:
        alert_message = rows[0]['alert_message']
        send_email(alert_message)

    return 'Checked alerts', 200

def send_email(message):
    MAILGUN_DOMAIN = os.environ['MAILGUN_DOMAIN']
    MAILGUN_API_KEY = os.environ['MAILGUN_API_KEY']
    response = requests.post(
        f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages",
        auth=("api", MAILGUN_API_KEY),
        data={
            "from": f"alerts@{MAILGUN_DOMAIN}",
            "to": ["team@yourdomain.com"],
            "subject": "BigQuery Alert 🚨",
            "text": message
        }
    )
    response.raise_for_status()
