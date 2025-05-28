import base64
import json
from email.mime.text import MIMEText
from google.oauth2 import service_account
from googleapiclient.discovery import build


def send_email_gmail_sa(subject: str, recipients: list, html_body: str):
    """
    Send an email using Gmail API via service account with domain-wide delegation.
    """
    try:
        service_account_info_str = get_secret("service-account-info")
        service_account_info = json.loads(service_account_info_str)

        delegated_user = get_secret("delegated-user-email")

        creds = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=["https://www.googleapis.com/auth/gmail.send"]
        ).with_subject(delegated_user)

        service = build('gmail', 'v1', credentials=creds)

        for recipient in recipients:
            message = MIMEText(html_body, "html")
            message["to"] = recipient
            message["from"] = delegated_user
            message["subject"] = subject
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

            response = service.users().messages().send(
                userId="me", body={"raw": raw_message}).execute()
            logger.info(f"Email sent to {recipient}, message ID: {response.get('id')}")

    except Exception:
        logger.exception("Failed to send Gmail via service account.")
        raise
