import json

with open('semesters.json') as f:
    semesters = json.load(f)

DATABASE_HOST = 'localhost'
DATABASE_NAME = 'mefmooc'
DATABASE_USER = 'postgres'
DATABASE_PASSWORD = 'Ay2945349*'
JWT_SECRET_KEY='secret'
ADMIN_USERNAME='admin'
ADMIN_PASSWORD='admin'
JWT_ACCESS_TOKEN_EXPIRES=7200
SEMESTERS = semesters["semesters"]

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = "mefmooc@gmail.com"
SMTP_PASSWORD = "mrrbkesncfatjovp"

RABBITMQ_HOST = 'localhost'

BUNDLE_STATUS = {
    'waiting-bundles': 'Waiting Bundle',
    'rejected-bundles': 'Rejected Bundle',
    'waiting-certificates': 'Waiting Certificates',
    'waiting-approval': 'Waiting Approval',
    'rejected-certificates': 'Rejected Certificates',
    'accepted-certificates': 'Accepted Certificates'
}