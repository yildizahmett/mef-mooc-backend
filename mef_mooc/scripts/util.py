import pika
import random
import string
from mef_mooc.scripts.constants import FRONTEND_URL

SEMESTERS = ["2022-2023-Fall", "2022-2023-Spring", "2023-2024-Fall", "2023-2024-Spring", "2024-2025-Fall", "2024-2025-Spring"]

BUNDLE_STATUS = {
    'waiting-bundles': 'Waiting Bundle',
    'rejected-bundles': 'Rejected Bundle',
    'waiting-certificates': 'Waiting Certificates',
    'waiting-approval': 'Waiting Approval',
    'rejected-certificates': 'Rejected Certificates',
    'accepted-certificates': 'Accepted Certificates'
}

def create_random_password(number_of_characters=8):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=number_of_characters))

def student_invite_mail_queue(students):
    if not isinstance(students, list):
        raise TypeError("Students must be a list")
    
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    except Exception as e:
        print(e)
        raise e
    
    channel = connection.channel()
    channel.queue_declare(queue='mail_sending')

    for student in students:
        email = student['email']
        password = student['password']
        
        body = {
            'email': email,
            'subject': 'MEF MOOC Invitation',
            'body': f'You have been invited to MEF MOOC.\n{FRONTEND_URL}\n\nYou can login with your email and password.\nYour password is {password}.'
        }

        channel.basic_publish(exchange='', routing_key='mail_sending', body=str(body))
    
    connection.close()

def send_mail_queue(email, subject, body):
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    except Exception as e:
        print(e)
        return
    
    channel = connection.channel()
    channel.queue_declare(queue='mail_sending')

    body = {
        'email': email,
        'subject': subject,
        'body': body
    }

    channel.basic_publish(exchange='', routing_key='mail_sending', body=str(body))
    
    connection.close()

