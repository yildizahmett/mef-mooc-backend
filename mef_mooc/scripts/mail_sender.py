import smtplib
from email.mime.text import MIMEText
from mef_mooc.config import SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD

def send_mail(subject, message, receiver_mail):
    smtp_server = SMTP_SERVER
    smtp_port = SMTP_PORT
    username = SMTP_USERNAME
    password = SMTP_PASSWORD
    server = smtplib.SMTP(smtp_server, smtp_port)
    server.starttls()
    server.login(username, password)

    # Create the email message
    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = username
    msg['To'] = receiver_mail

    server.sendmail(username, msg["To"], msg.as_string())
    server.quit()

    return True
