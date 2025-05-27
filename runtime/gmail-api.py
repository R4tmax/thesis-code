def send_email(subject: str, recipients: list, html_body: str):
    """
    Send an email using Gmail API with an HTML message body.
    Gmail API credentials are loaded from Secret Manager.
    """
    try:
        client_id = get_secret("Gmail_client_id")
        client_secret = get_secret("Gmail_client_secret")
        refresh_token = get_secret("Gmail_refresh_token")
        sender_email = "email.alerttestbot@gmail.com"

        creds = Credentials(
            None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret
        )
        if not creds.valid or creds.expired:
            creds.refresh(Request())

        service = build('gmail', 'v1', credentials=creds)

        for recipient in recipients:
            message = MIMEText(html_body, "html")
            message["to"] = recipient
            message["from"] = sender_email
            message["subject"] = subject
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

            response = service.users().messages().send(
                userId="me", body={"raw": raw_message}).execute()
            logging.info(f"Email sent to {recipient}, message ID: {response.get('id')}")

    except Exception:
        logging.exception("Failed to send Gmail.")
        raise
