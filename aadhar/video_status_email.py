import smtplib
import logging

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from aadhar.log import log_data
from config import VID_SENDER_EMAIL, VID_SENDER_PASSWORD, VID_SMTP_PORT, VID_SMTP_SERVER


def send_email(subject, to_email, html_body):
    smtp_server = VID_SMTP_SERVER
    smtp_port = VID_SMTP_PORT
    sender_email = VID_SENDER_EMAIL
    sender_password =  VID_SENDER_PASSWORD

    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = to_email

    if html_body:
        msg.attach(MIMEText(html_body, 'html'))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, to_email, msg.as_string())
        log_data(
            message='Email sent successfully',
            event_type='def send_email',
            log_level=logging.INFO,
            additional_context={'to_email': to_email, 'subject': subject}
        )
        return 'Email sent successfully'

    except Exception as e:
        log_data(message=f'Error sending email: {e}',event_type='def send_email',
            log_level=logging.ERROR,
            additional_context={'to_email': to_email, 'subject': subject}
        )
        return f'Error sending email: {e}'
