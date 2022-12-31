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
