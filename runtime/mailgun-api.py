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