import pika
import random
import string
from mef_mooc.scripts.constants import FRONTEND_URL

SEMESTERS = ["2022-2023-Fall", "2022-2023-Spring", "2022-2023-Summer", "2023-2024-Fall", 
             "2023-2024-Spring", "2023-2024-Summer", "2024-2025-Fall", "2024-2025-Spring", 
             "2024-2025-Summer", "2025-2026-Fall", "2025-2026-Spring", "2025-2026-Summer",
             "2026-2027-Fall", "2026-2027-Spring", "2026-2027-Summer", "2027-2028-Fall",
             "2027-2028-Spring", "2027-2028-Summer", "2028-2029-Fall", "2028-2029-Spring",
             "2028-2029-Summer", "2029-2030-Fall", "2029-2030-Spring", "2029-2030-Summer",
             "2030-2031-Fall", "2030-2031-Spring", "2030-2031-Summer", "2031-2032-Fall",
             "2031-2032-Spring", "2031-2032-Summer", "2032-2033-Fall", "2032-2033-Spring",
             "2032-2033-Summer", "2033-2034-Fall", "2033-2034-Spring", "2033-2034-Summer",
             "2034-2035-Fall", "2034-2035-Spring", "2034-2035-Summer", "2035-2036-Fall",
             "2035-2036-Spring", "2035-2036-Summer", "2036-2037-Fall", "2036-2037-Spring",
             "2036-2037-Summer", "2037-2038-Fall", "2037-2038-Spring", "2037-2038-Summer"]

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

def db_exec_queue(query, params=()):
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    except Exception as e:
        print(e)
        return
    
    channel = connection.channel()
    channel.queue_declare(queue='db_exec')

    body = {
        'query': query,
        'params': params
    }

    channel.basic_publish(exchange='', routing_key='db_exec', body=str(body))
    
    connection.close()

