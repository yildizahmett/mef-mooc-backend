from flask import Blueprint, request
from flask_bcrypt import generate_password_hash
from flask_jwt_extended import create_access_token
import random
import string
from mef_mooc.scripts.auth import admin_auth
from mef_mooc.scripts.models import db
from mef_mooc.config import ADMIN_USERNAME, ADMIN_PASSWORD

admin_app = Blueprint('admin_app', __name__, url_prefix='/admin')

@admin_app.route("/login", methods=['POST'])
def admin_login():
        data = request.get_json()
        username = data['username']
        password = data['password']

        if username != ADMIN_USERNAME or password != ADMIN_PASSWORD:
            return {"message": "Invalid credentials"}, 401

        token_identity = {
            'type': 'admin',
            'id': 1
        }

        access_token = create_access_token(identity=token_identity)
        return {"access_token": access_token}, 200


@admin_app.route("/add-coordinator", methods=['POST'])
@admin_auth()
def add_coordinator():
    try:
        data = request.get_json()
        name = data['name']
        surname = data['surname']
        email = data['email']
        password = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE email = %s LIMIT 1", (email,))
        if coordinator:
            return {"message": "Coordinator already exists"}, 400

        hashed_password = generate_password_hash(password).decode('utf-8')

        db.execute("INSERT INTO coordinator (name, surname, email, password) VALUES (%s, %s, %s, %s)", (name, surname, email, hashed_password))

        print("Coordinator added successfully. Password: " + password)

        return {"message": f"Coordinator added successfully. Password: {password}"}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@admin_app.route("/coordinators", methods=['GET'])
@admin_auth()
def get_coordinators():
    try:
        coordinators = db.fetch("""
                                SELECT coordinator.id, coordinator.name, coordinator.surname, coordinator.email, department.name as department_name 
                                FROM coordinator 
                                LEFT JOIN department ON coordinator.id = department.coordinator_id
                                """)
        return {"coordinators": coordinators}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@admin_app.route("/coordinators/<int:coordinator_id>/passive", methods=['POST'])
@admin_auth()
def delete_coordinator(coordinator_id):
    try:
        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s LIMIT 1", (coordinator_id,))
        if not coordinator:
            return {"message": "Coordinator not found"}, 404

        department = db.fetch_one("SELECT * FROM department WHERE coordinator_id = %s LIMIT 1", (coordinator_id,))
        if department:
            return {"message": "You cannot delete this coordinator"}, 400

        db.execute("UPDATE coordinator SET is_active = False WHERE id = %s", (coordinator_id,))

        return {"message": "Coordinator deleted successfully"}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@admin_app.route("/departments", methods=['GET'])
@admin_auth()
def get_departments():
    try:
        departments = db.fetch("""SELECT department.id, department.name, coordinator.name as coordinator_name, coordinator.surname as coordinator_surname 
                                  FROM department
                                  INNER JOIN coordinator ON department.coordinator_id = coordinator.id
                                  """)
        return {"departments": departments}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@admin_app.route("/add-department", methods=['POST'])
@admin_auth()
def add_department():
    try:
        data = request.get_json()
        name = data['name']
        coordinator_id = data['coordinator_id']

        department = db.fetch_one("SELECT * FROM department WHERE name = %s LIMIT 1", (name,))
        if department:
            return {"message": "Department already exists"}, 400

        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s and is_active = False LIMIT 1", (coordinator_id,))
        if not coordinator:
            return {"message": "Coordinator not found"}, 404

        db.execute("UPDATE coordinator SET is_active = True WHERE id = %s", (coordinator_id,))
        db.execute("INSERT INTO department (name, coordinator_id) VALUES (%s, %s)", (name, coordinator_id))

        return {"message": "Department added successfully"}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@admin_app.route("/passive-coordinators", methods=['GET'])
@admin_auth()
def get_passive_coordinators():
    try:
        coordinators = db.fetch("SELECT id, CONCAT(name, ' ', surname) as coordinator_name FROM coordinator WHERE is_active = False")
        return {"coordinators": coordinators}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@admin_app.route("/departments/<int:department_id>/change-coordinator", methods=['POST'])
@admin_auth()
def change_coordinator(department_id):
    try:
        data = request.get_json()
        coordinator_id = data['coordinator_id']

        department = db.fetch_one("SELECT * FROM department WHERE id = %s LIMIT 1", (department_id,))
        if not department:
            return {"message": "Department not found"}, 404

        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s and is_active = False LIMIT 1", (coordinator_id,))
        if not coordinator:
            return {"message": "Coordinator not found"}, 404

        if department['coordinator_id']:
            db.execute("UPDATE coordinator SET is_active = False WHERE id = %s", (department['coordinator_id'],))

        db.execute("UPDATE coordinator SET is_active = True WHERE id = %s", (coordinator_id,))
        db.execute("UPDATE department SET coordinator_id = %s WHERE id = %s", (coordinator_id, department_id))
        return {"message": "Coordinator changed successfully"}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500
