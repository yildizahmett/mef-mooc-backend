from dotenv import load_dotenv, find_dotenv
from os import getenv

try:
    load_dotenv(find_dotenv('../.env'))
except:
    exit('Could not load .env file')

FLASK_HOST = getenv('FLASK_HOST')
FLASK_PORT = getenv('FLASK_PORT')

DATABASE_HOST = getenv('DATABASE_HOST')
DATABASE_NAME = getenv('DATABASE_NAME')
DATABASE_USER = getenv('DATABASE_USER')
DATABASE_PASSWORD = getenv('DATABASE_PASSWORD')
DATABASE_PORT = getenv('DATABASE_PORT')

ADMIN_USERNAME = getenv('ADMIN_USERNAME')
ADMIN_PASSWORD = getenv('ADMIN_PASSWORD')

JWT_ACCESS_TOKEN_EXPIRES = int(getenv('JWT_ACCESS_TOKEN_EXPIRES'))
JWT_SECRET_KEY = getenv('JWT_SECRET_KEY')

SMTP_SERVER = getenv('SMTP_SERVER')
SMTP_PORT = getenv('SMTP_PORT')
SMTP_USERNAME = getenv('SMTP_USERNAME')
SMTP_PASSWORD = getenv('SMTP_PASSWORD')

RABBITMQ_HOST = getenv('RABBITMQ_HOST')

REDIS_HOST = getenv('REDIS_HOST')
REDIS_PORT = int(getenv('REDIS_PORT'))
REDIS_DB = int(getenv('REDIS_DB'))


