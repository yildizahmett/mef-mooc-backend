from flask import Blueprint, request
from flask_bcrypt import generate_password_hash
from flask_jwt_extended import create_access_token, get_jwt
import random
import string
from mef_mooc.scripts.auth import admin_auth
from mef_mooc.scripts.models import db
from mef_mooc.scripts.util import SEMESTERS, create_random_password, student_invite_mail_queue, send_mail_queue
from mef_mooc.scripts.constants import FRONTEND_URL
from mef_mooc.config import ADMIN_USERNAME, ADMIN_PASSWORD, JWT_ACCESS_TOKEN_EXPIRES
from mef_mooc.scripts.extensions import jwt_redis_blocklist

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

@admin_app.route("/logout", methods=['POST'])
@admin_auth()
def admin_logout():
    try:
        jti = get_jwt()['jti']
        jwt_redis_blocklist.set(jti, '', JWT_ACCESS_TOKEN_EXPIRES)
        return {"message": "Successfully logged out"}, 200
    except Exception as e:
        print(e)
        return {"message": "Something went wrong"}, 500

@admin_app.route("/invite-students", methods=['POST'])
@admin_auth()
def invite_students():
    try:
        data = request.get_json()
        students = data['students']
        student_mail_list = list()

        for student in students:
            email = student['email']
            password = create_random_password()
            student_no = student['student_no']
            name = student['name']
            surname = student['surname']
            department_id = student['department_id']

            student = db.fetch_one("SELECT * FROM student WHERE email = %s", (email,))
            if student:
                send_mail_queue(email, "MEF MOOC Invitation", f"You have been invited to MEF MOOC.\n{FRONTEND_URL}\n\nYou can login with your email and password.")

            hashed_password = generate_password_hash(password).decode('utf-8')
            try:
                db.execute("INSERT INTO student (email, password, student_no, name, surname, department_id) VALUES (%s, %s, %s, %s, %s, %s)", (email, hashed_password, student_no, name, surname, department_id))
                student_mail_list.append({
                    'email': email,
                    'password': password,
                })
            except Exception as e:
                print(e)

        student_invite_mail_queue(student_mail_list)
        return {"message": "Students invited"}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

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

        send_mail_queue(email, "MEF MOOC Coordinator Account", f"You have been invited to MEF MOOC as a coordinator.\n{FRONTEND_URL}\n\nYou can login with your email and password.\nYour password is {password}")

        return {"message": f"Coordinator added successfully."}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500
    
@admin_app.route("/change-profile/student/<int:student_id>", methods=['POST'])
@admin_auth()
def change_student_profile(student_id):
    try:
        data = request.get_json()
        student = db.fetch_one("SELECT * FROM student WHERE id = %s LIMIT 1", (student_id,))
        if not student:
            return {"message": "Student not found"}, 404

        name = data['name']
        surname = data['surname']
        email = data['email']
        student_no = data['student_no']
        department_id = data['department_id']

        db.execute("UPDATE student SET name = %s, surname = %s, email = %s, student_no = %s, department_id = %s WHERE id = %s", (name, surname, email, student_no, department_id, student_id))

        return {"message": "Student updated"}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500
    
@admin_app.route("/change-profile/coordinator/<int:coordinator_id>", methods=['POST'])
@admin_auth()
def change_coordinator_profile(coordinator_id):
    try:
        data = request.get_json()
        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s LIMIT 1", (coordinator_id,))
        if not coordinator:
            return {"message": "Coordinator not found"}, 404

        name = data['name']
        surname = data['surname']
        email = data['email']

        db.execute("UPDATE coordinator SET name = %s, surname = %s, email = %s WHERE id = %s", (name, surname, email, coordinator_id))

        return {"message": "Coordinator updated"}, 200
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
        departments = db.fetch("""SELECT department.id, department.code, department.name, coordinator.name as coordinator_name, coordinator.surname as coordinator_surname 
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
        code = data['code']

        department = db.fetch_one("SELECT * FROM department WHERE name = %s LIMIT 1", (name,))
        if department:
            return {"message": "Department already exists"}, 400

        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s and is_active = False LIMIT 1", (coordinator_id,))
        if not coordinator:
            return {"message": "Coordinator not found"}, 404

        db.execute("UPDATE coordinator SET is_active = True WHERE id = %s", (coordinator_id,))
        db.execute("INSERT INTO department (name, coordinator_id, code) VALUES (%s, %s)", (name, coordinator_id, code,))

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
    
@admin_app.route("/students", methods=['GET'])
@admin_auth()
def get_students():
    try:
        try:
            data = request.get_json()
            student_no = data['student_no']
        except:
            student_no = ""

        students = db.fetch(f"""
                            SELECT student.id, student.name, student.surname, student.email, student.student_no, department.name as department_name 
                            FROM student 
                            LEFT JOIN department ON student.department_id = department.id
                            WHERE student.student_no like '%%{student_no}%%'
                            """, (student_no,))
        return {"students": students}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@admin_app.route("/student/<int:student_id>", methods=['GET'])
@admin_auth()
def get_student(student_id):
    try:
        student = db.fetch_one("""
                            SELECT student.id, student.name, student.surname, student.email, student.student_no, department.name as department_name 
                            FROM student 
                            LEFT JOIN department ON student.department_id = department.id
                            WHERE student.id = %s LIMIT 1
                            """, (student_id,))
        if not student:
            return {"message": "Student not found"}, 404
        
        return {"student": student}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500
    
@admin_app.route("/coordinator/<int:coordinator_id>", methods=['GET'])
@admin_auth()
def get_coordinator(coordinator_id):
    try:
        coordinator = db.fetch_one("""
                            SELECT coordinator.id, coordinator.name, coordinator.surname, coordinator.email, department.name as department_name 
                            FROM coordinator 
                            LEFT JOIN department ON coordinator.id = department.coordinator_id
                            WHERE coordinator.id = %s LIMIT 1
                            """, (coordinator_id,))
        if not coordinator:
            return {"message": "Coordinator not found"}, 404
        
        return {"coordinator": coordinator}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@admin_app.route("/moocs", methods=['GET'])
@admin_auth()
def get_moocs():
    try:
        moocs = db.fetch("""
                        SELECT mooc.id, mooc.name, mooc.url, mooc.average_hours, is_active 
                        FROM mooc
                        """)
        return {"moocs": moocs}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@admin_app.route("/add-moocs", methods=['POST'])
@admin_auth()
def add_moocs():
    try:
        data = request.get_json()
        moocs = data['moocs']

        incorrect_moocs = []

        query = "INSERT INTO mooc (name, url, average_hours) VALUES "
        mooc_check_count = 0
        for mooc in moocs:
            mooc_check = db.fetch_one("SELECT * FROM mooc WHERE name = %s LIMIT 1", (mooc['name'],))
            if mooc_check:
                mooc_check_count += 1
                continue

            if not mooc['name'] or not mooc['url'] or not mooc['average_hours']:
                incorrect_moocs.append(mooc['name'])
                continue
            
            query += f"('{mooc['name']}', '{mooc['url']}', {mooc['average_hours']}),"

        if mooc_check_count == len(moocs):
            return {"message": "All moocs already exists"}, 400
        
        query = query[:-1]
        db.execute(query)

        if incorrect_moocs:
            report = "Following moocs are not added because of missing data: "
            for mooc in incorrect_moocs:
                report += mooc + ", "
            report = report[:-2]
            return {"message": "MOOC added successfully", "report": report}, 200

        return {"message": "MOOC added successfully"}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500
    
@admin_app.route("/mooc/<int:mooc_id>", methods=['GET'])
@admin_auth()
def get_mooc(mooc_id):
    try:
        mooc = db.fetch_one("""
                            SELECT mooc.id, mooc.name, mooc.url, mooc.average_hours 
                            FROM mooc
                            WHERE mooc.id = %s LIMIT 1
                            """, (mooc_id,))
        if not mooc:
            return {"message": "MOOC not found"}, 404
        
        return {"mooc": mooc}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@admin_app.route("/mooc/<int:mooc_id>/update", methods=['POST'])
@admin_auth()
def update_mooc(mooc_id):
    try:
        data = request.get_json()

        name = data['name']
        url = data['url']
        average_hours = data['average_hours']

        mooc = db.fetch_one("SELECT * FROM mooc WHERE id = %s LIMIT 1", (mooc_id,))
        if not mooc:
            return {"message": "MOOC not found"}, 404
        
        db.execute("UPDATE mooc SET name = %s, url = %s, average_hours = %s WHERE id = %s", (name, url, average_hours, mooc_id))

        return {"message": "MOOC updated successfully"}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500


@admin_app.route("/mooc/<int:mooc_id>/change-status", methods=['POST'])
@admin_auth()
def delete_mooc(mooc_id):
    try:
        mooc = db.fetch_one("SELECT * FROM mooc WHERE id = %s LIMIT 1", (mooc_id,))
        if not mooc:
            return {"message": "MOOC not found"}, 404
        
        if mooc['is_active'] == True:
            db.execute("UPDATE mooc SET is_active = False WHERE id = %s", (mooc_id,))
        elif mooc['is_active'] == False:
            db.execute("UPDATE mooc SET is_active = True WHERE id = %s", (mooc_id,))
        else:
            return {"message": "An error occured"}, 500

        return {"message": "MOOC status changed successfully"}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500
    
@admin_app.route("/semesters", methods=['GET'])
@admin_auth()
def get_semesters():
    try:
        semesters = db.fetch("""
                        SELECT m.id, m.course_code, m.name, m.semester, m.credits, m.created_at, m.is_active, 
                               SUM(CASE WHEN e.is_pass IS True THEN 1 ELSE 0 END) as number_of_passed_students, 
                               d.name as department
                        FROM mefcourse m
                        LEFT JOIN enrollment e ON e.course_id = m.id
                        INNER JOIN department d ON d.id = m.department_id
                        GROUP BY m.id, d.name
                        """)
        return {"semesters": semesters}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@admin_app.route("/semester-report/<semester>", methods=['GET'])
@admin_auth()
def get_semester_report(semester):
    try:
        if semester not in SEMESTERS:
            return {"message": "Semester not found"}, 404
        
        semester_report = db.fetch("""
                        SELECT s.id as student_id, e.id as enrollment_id, d.code as department, m.name as moocs, bd.certificate_url, CONCAT(s.name, ' ', s.surname) as student_name, b.comment
                        FROM student s
                        INNER JOIN department d ON d.id = s.department_id
                        INNER JOIN enrollment e ON s.id = e.student_id
                        INNER JOIN mefcourse c ON c.id = e.course_id
                        INNER JOIN bundle b ON e.id = b.enrollment_id
                        INNER JOIN bundle_detail bd ON b.id = bd.bundle_id
                        INNER JOIN mooc m ON bd.mooc_id = m.id
                        WHERE b.status = 'Accepted Certificates' and c.semester = %s
                        """, (semester,))
        
        return {"semester_report": semester_report}, 200
    
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500