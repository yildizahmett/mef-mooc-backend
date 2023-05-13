import pika
import sys
import os
import time
from mef_mooc.config import RABBITMQ_HOST
from mef_mooc.scripts.mail_sender import send_mail

def main():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()

    channel.queue_declare(queue='mail_sending')

    def callback_mail(ch, method, properties, body):
        print(" [x] Received %r" % body)
        try:
            mail = eval(body.decode())
            
            email = mail['email']
            subject = mail['subject']
            body = mail['body']
            send_mail(subject, body, email)
        except Exception as e:
            print(e)
            pass
        time.sleep(1)

    channel.basic_consume(queue='mail_sending', on_message_callback=callback_mail, auto_ack=True)
    channel.start_consuming()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)