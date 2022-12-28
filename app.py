from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt, verify_jwt_in_request
from flask_bcrypt import Bcrypt
from flask_cors import CORS
import functools
from models import Database

app = Flask(__name__)
app.config.from_pyfile('config.py')
CORS(app)

jwt = JWTManager(app)
bcrypt = Bcrypt(app)

db = Database()

def student_auth():
    def wrapper(f):
        @functools.wraps(f)
        def decorator(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            print(claims)
            if claims['sub']['type'] != 'student':
                return {"message": "Invalid token [From Decorator]"}, 403
            return f(*args, **kwargs)
        return decorator
    return wrapper

def coordinator_auth():
    def wrapper(f):
        @functools.wraps(f)
        def decorator(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            if claims['sub']['type'] != 'coordinator':
                return {"message": "Invalid token [From Decorator]"}, 403
            return f(*args, **kwargs)
        return decorator
    return wrapper

def admin_auth():
    def wrapper(f):
        @functools.wraps(f)
        def decorator(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            if claims['sub']['type'] != 'admin':
                return {"message": "Invalid token [From Decorator]"}, 403
            return f(*args, **kwargs)
        return decorator
    return wrapper

@app.route("/student/login", methods=['POST'])
def student_login():

        data = request.get_json()
        student_no = data['student_no']
        password = data['password']

        student = db.fetch_one("SELECT * FROM student WHERE student_no = %s LIMIT 1", (student_no,))
        if not student:
            return {"message": "Invalid credentials"}, 401

        if not bcrypt.check_password_hash(student['password'], password):
            return {"message": "Invalid credentials"}, 401

        print(student)
        token_identity = {
            'type': 'student',
            'id': student['id']
        }

        access_token = create_access_token(identity=token_identity)
        return {"access_token": access_token}, 200


@app.route("/student/create-bundle", methods=['GET'])
@student_auth()
def create_bundle():
    return "Selamlar"

if __name__ == "__main__":
    app.run(debug=True)
