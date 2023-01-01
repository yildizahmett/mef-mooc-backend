import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import *

class Mail:
    def __init__(self):
        self.server = smtplib.SMTP('smtp.gmail.com', 587)
        self.server.starttls()
        self.server.login(MAIL_USERNAME, MAIL_PASSWORD)

    def send(self, to, subject, content):
        message = MIMEMultipart()
        message['From'] = MAIL_USERNAME
        message['To'] = to
        message['Subject'] = subject
        message.attach(MIMEText(content, 'plain'))
        self.server.sendmail(MAIL_USERNAME, to, message.as_string())

    def __del__(self):
        self.server.quit()



