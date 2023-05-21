from flask import Blueprint, request
from flask_jwt_extended import create_access_token, get_jwt
from flask_bcrypt import check_password_hash, generate_password_hash
from mef_mooc.scripts.util import SEMESTERS, BUNDLE_STATUS, create_random_password, send_mail_queue
from mef_mooc.scripts.auth import coordinator_auth
from mef_mooc.scripts.models import db
from mef_mooc.scripts.extensions import jwt_redis_blocklist
from mef_mooc.config import JWT_ACCESS_TOKEN_EXPIRES

coordinator_app = Blueprint('coordinator_app', __name__, url_prefix='/coordinator')

@coordinator_app.route("/login", methods=['POST'])
def coordinator_login():
    try:
        data = request.get_json()
        email = data['email']
        password = data['password']

        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE email = %s and is_active = True LIMIT 1", (email,))
        if not coordinator:
            return {"message": "Invalid credentials or coordinator disabled"}, 401

        if not check_password_hash(coordinator['password'], password):
            return {"message": "Invalid credentials or coordinator disabled"}, 401

        token_identity = {
            'type': 'coordinator',
            'id': coordinator['id']
        }

        access_token = create_access_token(identity=token_identity)
        return {"access_token": access_token, "coordinator_name": coordinator["name"] + " " + coordinator["surname"]}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500
    
@coordinator_app.route("/logout", methods=['POST'])
@coordinator_auth()
def coordinator_logout():
    try:
        jti = get_jwt()['jti']
        jwt_redis_blocklist.set(jti, "", JWT_ACCESS_TOKEN_EXPIRES)
        return {"message": "Logged out successfully"}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500
    
@coordinator_app.route("/forgot-password", methods=['POST'])
def coordinator_forgot_password():
    try:
        data = request.get_json()
        email = data['email']

        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE email = %s and is_active = True LIMIT 1", (email,))
        if not coordinator:
            return {"message": "Invalid credentials or coordinator disabled"}, 401

        password = create_random_password()
        hashed_password = generate_password_hash(password).decode('utf-8')

        db.execute("UPDATE coordinator SET password = %s WHERE id = %s", (hashed_password, coordinator['id']))

        send_mail_queue(
            email,
            "MEF MOOC Şifre Sıfırlama",
            "MEF MOOC şifreniz başarıyla sıfırlandı.\nYeni şifreniz: " + password
        )

        return {"message": "Password reset successfully"}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500
    
@coordinator_app.route("/change-password", methods=['POST'])
@coordinator_auth()
def coordinator_change_password():
    try:
        data = request.get_json()
        old_password = data['old_password']
        new_password = data['new_password']

        coordinator_id = get_jwt()['sub']['id']
        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s and is_active = True LIMIT 1", (coordinator_id,))
        if not coordinator:
            return {"message": "Coordinator not found or coordinator disabled"}, 404

        if not check_password_hash(coordinator['password'], old_password):
            return {"message": "Invalid credentials"}, 401

        hashed_password = generate_password_hash(new_password).decode('utf-8')
        db.execute("UPDATE coordinator SET password = %s WHERE id = %s", (hashed_password, coordinator['id']))

        return {"message": "Password changed successfully"}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500
    
@coordinator_app.route("/profile", methods=['GET'])
@coordinator_auth()
def coordinator_profile():
    try:
        coordinator_id = get_jwt()['sub']['id']
        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s and is_active = True LIMIT 1", (coordinator_id,))

        if not coordinator:
            return {"message": "Coordinator not found or coordinator disabled"}, 404
        
        department = db.fetch_one("SELECT * FROM department WHERE coordinator_id = %s LIMIT 1", (coordinator['id'],))
        if not department:
            return {"message": "Department not found"}, 404
        
        coordinator['department'] = department["name"]

        # REMOVE PASSWORD
        del coordinator['password']

        return {"coordinator": coordinator}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@coordinator_app.route("/possible-semesters", methods=['GET'])
@coordinator_auth()
def coordinator_possible_semesters():
    try:
        coordinator_id = get_jwt()['sub']['id']
        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s and is_active = True LIMIT 1", (coordinator_id,))

        if not coordinator:
            return {"message": "Coordinator not found or coordinator disabled"}, 404

        return {"semesters": SEMESTERS}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

# Current course informations
@coordinator_app.route("/course/<int:course_id>/info", methods=['GET'])
@coordinator_auth()
def coordinator_course_info(course_id):
    try:
        coordinator_id = get_jwt()['sub']['id']
        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s and is_active = True LIMIT 1", (coordinator_id,))

        if not coordinator:
            return {"message": "Coordinator not found or coordinator disabled"}, 404

        course = db.fetch_one("SELECT * FROM MEFcourse WHERE id = %s LIMIT 1", (course_id,))
        if not course:
            return {"message": "Course not found"}, 404

        department = db.fetch_one("SELECT * FROM department WHERE id = %s LIMIT 1", (course['department_id'],))
        if not department:
            return {"message": "Department not found"}, 404

        if department['coordinator_id'] != coordinator['id']:
            return {"message": "You are not allowed to see this course"}, 403

        return {"course": course}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@coordinator_app.route("/add-course", methods=['POST'])
@coordinator_auth()
def coordinator_add_course():
    try:
        coordinator_id = get_jwt()['sub']['id']
        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s and is_active = True LIMIT 1", (coordinator_id,))

        if not coordinator:
            return {"message": "Coordinator not found or coordinator disabled"}, 404

        department = db.fetch_one("SELECT * FROM department WHERE coordinator_id = %s LIMIT 1", (coordinator['id'],))
        if not department:
            return {"message": "Department not found or department disabled"}, 404
        
        if department['coordinator_id'] != coordinator['id']:
            return {"message": "You are not allowed to add course to this department"}, 403

        data = request.get_json()
        course_code = data['course_code']
        name = data['name']
        type = data['type']
        semester = data['semester']
        credits = data['credits']

        course = db.fetch_one("SELECT * FROM MEFcourse WHERE course_code = %s and semester = %s and name = %s and department_id = %s LIMIT 1", (course_code, semester, name,department['id'],))
        if course:
            return {"message": "Course already exists"}, 400

        db.execute("INSERT INTO MEFcourse (course_code, name, type, semester, credits, department_id, coordinator_id) VALUES (%s, %s, %s, %s, %s, %s, %s)", 
                    (course_code, name, type, semester, credits, department['id'], coordinator_id))

        return {"message": "Course added successfully"}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@coordinator_app.route("/course/<int:course_id>/passive", methods=['POST'])
@coordinator_auth()
def coordinator_passive_course(course_id):
    try:
        coordinator_id = get_jwt()['sub']['id']
        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s and is_active = True LIMIT 1", (coordinator_id,))

        if not coordinator:
            return {"message": "Coordinator not found or coordinator disabled"}, 404

        course = db.fetch_one("SELECT * FROM MEFcourse WHERE id = %s and is_active = True LIMIT 1", (course_id,))
        if not course:
            return {"message": "Course not found"}, 404

        department = db.fetch_one("SELECT * FROM department WHERE coordinator_id = %s LIMIT 1", (coordinator['id'],))
        if not department:
            return {"message": "Department not found or department disabled"}, 404

        if course['department_id'] != department['id']:
            return {"message": "You cannot view this course"}, 400

        db.execute("UPDATE MEFcourse SET is_active = False WHERE id = %s", (course_id,))

        return {"message": "Course passived successfully"}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@coordinator_app.route("/active-courses", methods=['GET'])
@coordinator_auth()
def coordinator_active_courses():
    try:
        coordinator_id = get_jwt()['sub']['id']
        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s and is_active = True LIMIT 1", (coordinator_id,))

        if not coordinator:
            return {"message": "Coordinator not found or coordinator disabled"}, 404

        department = db.fetch_one("SELECT * FROM department WHERE coordinator_id = %s LIMIT 1", (coordinator['id'],))
        if not department:
            return {"message": "Department not found or department disabled"}, 404

        if department['coordinator_id'] != coordinator['id']:
            return {"message": "You are not allowed to see this course"}, 403

        courses = db.fetch("SELECT * FROM MEFcourse WHERE department_id = %s and is_active = True", (department['id'],))
        return {"courses": courses}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@coordinator_app.route("/inactive-courses", methods=['GET'])
@coordinator_auth()
def coordinator_inactive_courses():
    try:
        coordinator_id = get_jwt()['sub']['id']
        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s and is_active = True LIMIT 1", (coordinator_id,))

        if not coordinator:
            return {"message": "Coordinator not found or coordinator disabled"}, 404

        department = db.fetch_one("SELECT * FROM department WHERE coordinator_id = %s LIMIT 1", (coordinator['id'],))
        if not department:
            return {"message": "Department not found or department disabled"}, 404

        courses = db.fetch("SELECT * FROM MEFcourse WHERE department_id = %s and is_active = False", (department['id'],))
        return {"courses": courses}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@coordinator_app.route("/course/<int:course_id>/waiting-students", methods=['GET'])
@coordinator_auth()
def coordinator_waiting_students(course_id):
    try:
        coordinator_id = get_jwt()['sub']['id']
        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s and is_active = True LIMIT 1", (coordinator_id,))

        if not coordinator:
            return {"message": "Coordinator not found or coordinator disabled"}, 404

        course = db.fetch_one("SELECT * FROM MEFcourse WHERE id = %s LIMIT 1", (course_id,))
        if not course:
            return {"message": "Course not found"}, 404

        department = db.fetch_one("SELECT * FROM department WHERE coordinator_id = %s LIMIT 1", (coordinator_id,))

        if course['department_id'] != department['id']:
            return {"message": "You cannot view this course"}, 400

        students = db.fetch("""
                            SELECT a.id as student_id, a.name, a.surname, a.email, a.student_no, 
                            e.pass_date, m.id as course_id, m.course_code, m.name as course_name, m.credits, m.semester,
                            m.is_active as is_course_active, e.is_pass as is_passed_course, e.is_waiting as is_waiting_enrollment
                            FROM (SELECT student.id, student.name, 
                                student.surname, student.email, student.student_no, enrollment.is_waiting
                            FROM student
                            INNER JOIN enrollment ON student.id = enrollment.student_id
                            WHERE enrollment.course_id = %s and enrollment.is_waiting = True) a
                            LEFT JOIN enrollment e ON e.student_id = a.id
                            LEFT JOIN mefcourse m ON e.course_id = m.id and m.id != %s
        """, (course_id, course_id,))
        return {"students": students}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500
    
@coordinator_app.route("/course/<int:course_id>/waiting-students/accept", methods=['POST'])
@coordinator_auth()
def coordinator_accept_waiting_students(course_id):
    try:
        coordinator_id = get_jwt()['sub']['id']
        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s and is_active = True LIMIT 1", (coordinator_id,))

        if not coordinator:
            return {"message": "Coordinator not found or coordinator disabled"}, 404

        course = db.fetch_one("SELECT * FROM MEFcourse WHERE id = %s LIMIT 1", (course_id,))
        if not course:
            return {"message": "Course not found"}, 404

        department = db.fetch_one("SELECT * FROM department WHERE coordinator_id = %s LIMIT 1", (coordinator_id,))

        if course['department_id'] != department['id']:
            return {"message": "You cannot view this course"}, 400

        data = request.get_json()
        student_id = data['student_id']

        student = db.fetch_one("SELECT * FROM student WHERE id = %s LIMIT 1", (student_id,))
        if not student:
            return {"message": "Student not found"}, 404

        is_waiting_enrollment = db.fetch_one("SELECT * FROM enrollment WHERE student_id = %s and course_id = %s and is_waiting = True LIMIT 1", (student_id, course_id))
        if not is_waiting_enrollment:
            return {"message": "Student is not waiting for this course"}, 400
        
        db.execute("UPDATE enrollment SET is_waiting = False WHERE student_id = %s and course_id = %s", (student_id, course_id))
        return {"message": "Student accepted"}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500
    
@coordinator_app.route("/course/<int:course_id>/waiting-students/reject", methods=['POST'])
@coordinator_auth()
def coordinator_reject_waiting_students(course_id):
    try:
        coordinator_id = get_jwt()['sub']['id']
        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s and is_active = True LIMIT 1", (coordinator_id,))

        if not coordinator:
            return {"message": "Coordinator not found or coordinator disabled"}, 404

        course = db.fetch_one("SELECT * FROM MEFcourse WHERE id = %s LIMIT 1", (course_id,))
        if not course:
            return {"message": "Course not found"}, 404

        department = db.fetch_one("SELECT * FROM department WHERE coordinator_id = %s LIMIT 1", (coordinator_id,))

        if course['department_id'] != department['id']:
            return {"message": "You cannot view this course"}, 400

        data = request.get_json()
        student_id = data['student_id']
        coordinator_message = data['message']

        student = db.fetch_one("SELECT * FROM student WHERE id = %s LIMIT 1", (student_id,))
        if not student:
            return {"message": "Student not found"}, 404

        is_waiting_enrollment = db.fetch_one("SELECT * FROM enrollment WHERE student_id = %s and course_id = %s and is_waiting = True LIMIT 1", (student_id, course_id))
        if not is_waiting_enrollment:
            return {"message": "Student is not waiting for this course"}, 400
        
        db.execute("DELETE FROM enrollment WHERE student_id = %s and course_id = %s", (student_id, course_id))

        try:
            send_mail_queue(student['email'], "Course Enrollment", 
                            f"Your enrollment request for {course['name']} has been rejected by MOOC Coordinator.\n\nCoordinator Message: {coordinator_message}")
        except:
            pass
        
        return {"message": "Student rejected"}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@coordinator_app.route("/course/<int:course_id>/students", methods=['GET'])
@coordinator_auth()
def coordinator_course(course_id):
    try:
        coordinator_id = get_jwt()['sub']['id']
        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s and is_active = True LIMIT 1", (coordinator_id,))

        if not coordinator:
            return {"message": "Coordinator not found or coordinator disabled"}, 404

        course = db.fetch_one("SELECT * FROM MEFcourse WHERE id = %s LIMIT 1", (course_id,))
        if not course:
            return {"message": "Course not found"}, 404

        department = db.fetch_one("SELECT * FROM department WHERE coordinator_id = %s LIMIT 1", (coordinator_id,))

        if course['department_id'] != department['id']:
            return {"message": "You cannot view this course"}, 400

        students = db.fetch("""
                            SELECT student.id, student.name, student.surname, student.email, student.student_no, enrollment.created_at as enroll_date
                            FROM student
                            INNER JOIN enrollment ON student.id = enrollment.student_id
                            WHERE enrollment.course_id = %s and enrollment.is_waiting = False
        """, (course_id,))

        return {"students": students}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

# @coordinator_app.route("/course/<int:course_id>/<status>", methods=['GET'])
# @coordinator_auth()
# def coordinator_course_all_reports(course_id, status):
#     try:
#         coordinator_id = get_jwt()['sub']['id']
#         coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s and is_active = True LIMIT 1", (coordinator_id,))

#         if not coordinator:
#             return {"message": "Coordinator not found or coordinator disabled"}, 404

#         course = db.fetch_one("SELECT * FROM MEFcourse WHERE id = %s LIMIT 1", (course_id,))
#         if not course:
#             return {"message": "Course not found"}, 404

#         department = db.fetch_one("SELECT * FROM department WHERE coordinator_id = %s LIMIT 1", (coordinator_id,))

#         if course['department_id'] != department['id']:
#             return {"message": "You cannot view this course"}, 400

#         hashed_status = BUNDLE_STATUS.get(status)

#         if not hashed_status:
#             return {"message": "Status not found"}, 404

#         # TODO: Get total bundle hours
#         bundles = db.fetch("""
#                             SELECT s.id as student_id, s.name as student_name, s.surname as student_surname, s.email as student_email, 
#                                    s.student_no, b.id as bundle_id, b.created_at as bundle_created_at, m.name as mooc_name, e.pass_date,
#                                    m.url as mooc_url, bd.certificate_url, CONCAT(c.name, ' ', c.surname) as coordinator_name, b.comment
#                             FROM student s
#                             INNER JOIN enrollment e ON s.id = e.student_id
#                             INNER JOIN bundle b ON e.id = b.enrollment_id
#                             INNER JOIN bundle_detail bd ON b.id = bd.bundle_id
#                             INNER JOIN mooc m ON bd.mooc_id = m.id
#                             LEFT JOIN coordinator c ON b.coordinator_id = c.id
#                             WHERE b.status = %s and e.course_id = %s
#                             ORDER BY b.created_at DESC
#         """, (hashed_status, course_id,))

#         return {"bundles": bundles, "is_active": course["is_active"]}, 200
#     except Exception as e:
#         print(e)
#         return {"message": "An error occured"}, 500

@coordinator_app.route("/moocs", methods=['GET'])
@coordinator_auth()
def coordinator_moocs():
    try:
        coordinator_id = get_jwt()['sub']['id']
        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s and is_active = True LIMIT 1", (coordinator_id,))

        if not coordinator:
            return {"message": "Coordinator not found or coordinator disabled"}, 404

        moocs = db.fetch("SELECT id, average_hours, name, url FROM mooc WHERE is_active = True")

        return {"moocs": moocs}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@coordinator_app.route("/course/<int:course_id>/bundle/<int:bundle_id>", methods=['GET'])
@coordinator_auth()
def coordinator_course_bundle(course_id, bundle_id):
    try:
        coordinator_id = get_jwt()['sub']['id']
        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s and is_active = True LIMIT 1", (coordinator_id,))

        if not coordinator:
            return {"message": "Coordinator not found or coordinator disabled"}, 404

        course = db.fetch_one("SELECT * FROM MEFcourse WHERE id = %s LIMIT 1", (course_id,))
        if not course:
            return {"message": "Course not found"}, 404

        department = db.fetch_one("SELECT * FROM department WHERE coordinator_id = %s LIMIT 1", (coordinator_id,))

        if course['department_id'] != department['id']:
            return {"message": "You cannot view this course"}, 400

        bundle = db.fetch("""
                            SELECT s.id as student_id, s.name as student_name, s.surname as student_surname, s.email as student_email, 
                                   s.student_no, b.id as bundle_id, m.name as mooc_name, m.id as mooc_id, b.comment,
                                   m.url as mooc_url, bd.certificate_url, bd.id as bundle_detail_id
                            FROM student s
                            INNER JOIN enrollment e ON s.id = e.student_id
                            INNER JOIN bundle b ON e.id = b.enrollment_id
                            INNER JOIN bundle_detail bd ON b.id = bd.bundle_id
                            INNER JOIN mooc m ON bd.mooc_id = m.id
                            WHERE b.id = %s and e.course_id = %s
                            ORDER BY b.created_at DESC
        """, (bundle_id, course_id,))

        return {"bundle": bundle}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500
    
@coordinator_app.route("/course/<int:course_id>/bundle/<int:bundle_id>/bundle-detail/<int:bundle_detail_id>/update-mooc", methods=['POST'])
@coordinator_auth()
def coordinator_update_mooc(course_id, bundle_id, bundle_detail_id):
    try:
        coordinator_id = get_jwt()['sub']['id']
        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s and is_active = True LIMIT 1", (coordinator_id,))

        if not coordinator:
            return {"message": "Coordinator not found or coordinator disabled"}, 404

        course = db.fetch_one("SELECT * FROM MEFcourse WHERE id = %s LIMIT 1", (course_id,))
        if not course:
            return {"message": "Course not found"}, 404
        
        bundle = db.fetch_one("SELECT * FROM bundle WHERE id = %s LIMIT 1", (bundle_id,))
        if not bundle:
            return {"message": "Bundle not found"}, 404
        
        bundle_detail = db.fetch_one("SELECT * FROM bundle_detail WHERE id = %s and bundle_id = %s LIMIT 1", (bundle_detail_id, bundle_id,))
        if not bundle_detail:
            return {"message": "Bundle detail not found"}, 404

        department = db.fetch_one("SELECT * FROM department WHERE coordinator_id = %s LIMIT 1", (coordinator_id,))

        if course['department_id'] != department['id']:
            return {"message": "You cannot view this course"}, 400

        data = request.get_json()
        mooc_id = data["mooc_id"]

        mooc = db.fetch_one("SELECT * FROM mooc WHERE id = %s LIMIT 1", (mooc_id,))
        if not mooc:
            return {"message": "Mooc not found"}, 404
        
        db.execute("UPDATE bundle_detail SET mooc_id = %s WHERE id = %s", (mooc_id, bundle_detail_id,))

        return {"message": "Mooc updated"}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@coordinator_app.route("/course/<int:course_id>/bundle/<int:bundle_id>/bundle-detail/<int:bundle_detail_id>/update-certificate", methods=['POST'])
@coordinator_auth()
def coordinator_update_certificate(course_id, bundle_id, bundle_detail_id):
    try:
        coordinator_id = get_jwt()['sub']['id']
        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s and is_active = True LIMIT 1", (coordinator_id,))

        if not coordinator:
            return {"message": "Coordinator not found or coordinator disabled"}, 404

        course = db.fetch_one("SELECT * FROM MEFcourse WHERE id = %s LIMIT 1", (course_id,))
        if not course:
            return {"message": "Course not found"}, 404
        
        bundle = db.fetch_one("SELECT * FROM bundle WHERE id = %s LIMIT 1", (bundle_id,))
        if not bundle:
            return {"message": "Bundle not found"}, 404
        
        bundle_detail = db.fetch_one("SELECT * FROM bundle_detail WHERE id = %s and bundle_id = %s LIMIT 1", (bundle_detail_id, bundle_id,))
        if not bundle_detail:
            return {"message": "Bundle detail not found"}, 404

        department = db.fetch_one("SELECT * FROM department WHERE coordinator_id = %s LIMIT 1", (coordinator_id,))

        if course['department_id'] != department['id']:
            return {"message": "You cannot view this course"}, 400

        data = request.get_json()
        certificate_url = data["certificate_url"]

        db.execute("UPDATE bundle_detail SET certificate_url = %s WHERE id = %s", (certificate_url, bundle_detail_id,))

        return {"message": "Certificate updated"}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500
    
@coordinator_app.route("/course/<int:course_id>/bundle/<int:bundle_id>/bundle-detail/<int:bundle_detail_id>/delete-mooc", methods=['POST'])
@coordinator_auth()
def coordinator_delete_mooc(course_id, bundle_id, bundle_detail_id):
    try:
        coordinator_id = get_jwt()['sub']['id']
        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s and is_active = True LIMIT 1", (coordinator_id,))

        if not coordinator:
            return {"message": "Coordinator not found or coordinator disabled"}, 404

        course = db.fetch_one("SELECT * FROM MEFcourse WHERE id = %s LIMIT 1", (course_id,))
        if not course:
            return {"message": "Course not found"}, 404
        
        bundle = db.fetch_one("SELECT * FROM bundle WHERE id = %s LIMIT 1", (bundle_id,))
        if not bundle:
            return {"message": "Bundle not found"}, 404
        
        bundle_detail = db.fetch_one("SELECT * FROM bundle_detail WHERE id = %s and bundle_id = %s LIMIT 1", (bundle_detail_id, bundle_id,))
        if not bundle_detail:
            return {"message": "Bundle detail not found"}, 404

        department = db.fetch_one("SELECT * FROM department WHERE coordinator_id = %s LIMIT 1", (coordinator_id,))

        if course['department_id'] != department['id']:
            return {"message": "You cannot view this course"}, 400
        
        number_of_mooc = db.fetch_one("SELECT COUNT(*) FROM bundle_detail WHERE bundle_id = %s", (bundle_id,))['count']
        if number_of_mooc == 1:
            return {"message": "You cannot delete the last mooc in a bundle"}, 400

        db.execute("DELETE FROM bundle_detail WHERE id = %s", (bundle_detail_id,))

        return {"message": "Mooc deleted"}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500
    
@coordinator_app.route("/course/<int:course_id>/bundle/<int:bundle_id>/add-mooc", methods=['POST'])
@coordinator_auth()
def coordinator_add_mooc(course_id, bundle_id):
    try:
        coordinator_id = get_jwt()['sub']['id']
        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s and is_active = True LIMIT 1", (coordinator_id,))

        if not coordinator:
            return {"message": "Coordinator not found or coordinator disabled"}, 404

        course = db.fetch_one("SELECT * FROM MEFcourse WHERE id = %s LIMIT 1", (course_id,))
        if not course:
            return {"message": "Course not found"}, 404
        
        bundle = db.fetch_one("SELECT * FROM bundle WHERE id = %s LIMIT 1", (bundle_id,))
        if not bundle:
            return {"message": "Bundle not found"}, 404

        department = db.fetch_one("SELECT * FROM department WHERE coordinator_id = %s LIMIT 1", (coordinator_id,))

        if course['department_id'] != department['id']:
            return {"message": "You cannot view this course"}, 400
        
        data = request.get_json()
        mooc_id = data["mooc_id"]

        mooc = db.fetch_one("SELECT * FROM mooc WHERE id = %s LIMIT 1", (mooc_id,))
        if not mooc:
            return {"message": "Mooc not found"}, 404

        all_moocs = db.fetch("SELECT * FROM bundle_detail WHERE bundle_id = %s", (bundle_id,))
        for mooc in all_moocs:
            if mooc['mooc_id'] == mooc_id:
                return {"message": "Mooc already in bundle"}, 400
        
        db.execute("INSERT INTO bundle_detail (bundle_id, mooc_id) VALUES (%s, %s)", (bundle_id, mooc_id,))

        return {"message": "Mooc added"}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500
    
@coordinator_app.route("/course/<int:course_id>/bundle/<int:bundle_id>/update-comment", methods=['POST'])
@coordinator_auth()
def coordinator_update_comment(course_id, bundle_id):
    try:
        coordinator_id = get_jwt()['sub']['id']
        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s and is_active = True LIMIT 1", (coordinator_id,))

        if not coordinator:
            return {"message": "Coordinator not found or coordinator disabled"}, 404

        course = db.fetch_one("SELECT * FROM MEFcourse WHERE id = %s LIMIT 1", (course_id,))
        if not course:
            return {"message": "Course not found"}, 404
        
        bundle = db.fetch_one("SELECT * FROM bundle WHERE id = %s LIMIT 1", (bundle_id,))
        if not bundle:
            return {"message": "Bundle not found"}, 404

        department = db.fetch_one("SELECT * FROM department WHERE coordinator_id = %s LIMIT 1", (coordinator_id,))

        if course['department_id'] != department['id']:
            return {"message": "You cannot view this course"}, 400
        
        data = request.get_json()
        comment = data["comment"]

        db.execute("UPDATE bundle SET comment = %s WHERE id = %s", (comment, bundle_id,))

        return {"message": "Comment updated"}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@coordinator_app.route("/course/<int:course_id>/bundle/<int:bundle_id>/approve-bundle", methods=['POST'])
@coordinator_auth()
def coordinator_approve_bundle(course_id, bundle_id):
    try:
        coordinator_id = get_jwt()['sub']['id']
        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s and is_active = True LIMIT 1", (coordinator_id,))

        if not coordinator:
            return {"message": "Coordinator not found or coordinator disabled"}, 404

        course = db.fetch_one("SELECT * FROM MEFcourse WHERE id = %s LIMIT 1", (course_id,))
        if not course:
            return {"message": "Course not found"}, 404

        department = db.fetch_one("SELECT * FROM department WHERE coordinator_id = %s LIMIT 1", (coordinator_id,))

        if course['department_id'] != department['id']:
            return {"message": "You cannot view this course"}, 400

        bundle = db.fetch_one("SELECT * FROM bundle WHERE id = %s LIMIT 1", (bundle_id,))
        if not bundle:
            return {"message": "Bundle not found"}, 404

        if bundle['status'] != BUNDLE_STATUS['waiting-bundles']:
            return {"message": "Bundle is not waiting for approval"}, 400

        enrollment = db.fetch_one("SELECT * FROM enrollment WHERE id = %s LIMIT 1", (bundle['enrollment_id'],))
        if not enrollment:
            return {"message": "Enrollment not found"}, 404

        student = db.fetch_one("SELECT * FROM student WHERE id = %s LIMIT 1", (enrollment['student_id'],))
        if not student:
            return {"message": "Student not found"}, 404

        db.execute("UPDATE bundle SET status = %s, coordinator_id = %s, bundle_date = NOW() WHERE id = %s", (BUNDLE_STATUS['waiting-certificates'], coordinator["id"], bundle_id))
        send_mail_queue(student['email'], "Bundle Approved", f"Your bundle for {course['name']} has been approved. You can start your courses.")
        return {"message": "Bundle approved"}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@coordinator_app.route("/course/<int:course_id>/bundle/<int:bundle_id>/reject-bundle", methods=['POST'])
@coordinator_auth()
def coordinator_reject_bundle(course_id, bundle_id):
    try:
        coordinator_id = get_jwt()['sub']['id']
        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s and is_active = True LIMIT 1", (coordinator_id,))

        if not coordinator:
            return {"message": "Coordinator not found or coordinator disabled"}, 404

        course = db.fetch_one("SELECT * FROM MEFcourse WHERE id = %s LIMIT 1", (course_id,))
        if not course:
            return {"message": "Course not found"}, 404

        department = db.fetch_one("SELECT * FROM department WHERE coordinator_id = %s LIMIT 1", (coordinator_id,))

        if course['department_id'] != department['id']:
            return {"message": "You cannot view this course"}, 400

        bundle = db.fetch_one("SELECT * FROM bundle WHERE id = %s LIMIT 1", (bundle_id,))
        if not bundle:
            return {"message": "Bundle not found"}, 404

        if bundle['status'] != BUNDLE_STATUS['waiting-bundles']:
            return {"message": "Bundle is not waiting for approval"}, 400
        
        enrollment = db.fetch_one("SELECT * FROM enrollment WHERE id = %s LIMIT 1", (bundle["enrollment_id"],))
        if not enrollment:
            return {"message": "Enrollment not found"}, 404

        student = db.fetch_one("SELECT * FROM student WHERE id = %s LIMIT 1", (enrollment["student_id"],))

        data = request.get_json()
        reason = data["reason"]

        db.execute("UPDATE bundle SET status = %s, coordinator_id = %s, bundle_date = NOW(), reject_status_comment = %s WHERE id = %s", (BUNDLE_STATUS['rejected-bundles'], coordinator["id"], reason, bundle_id))
        send_mail_queue(student["email"], "Bundle Rejected", f"Your bundle for {course['name']} has been rejected.\nReason: " + reason)
        return {"message": "Bundle rejected"}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@coordinator_app.route("/course/<int:course_id>/bundle/<int:bundle_id>/approve-certificate", methods=['POST'])
@coordinator_auth()
def coordinator_approve_certificate(course_id, bundle_id):
    try:
        coordinator_id = get_jwt()['sub']['id']
        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s and is_active = True LIMIT 1", (coordinator_id,))

        if not coordinator:
            return {"message": "Coordinator not found or coordinator disabled"}, 404

        course = db.fetch_one("SELECT * FROM MEFcourse WHERE id = %s LIMIT 1", (course_id,))
        if not course:
            return {"message": "Course not found"}, 404

        department = db.fetch_one("SELECT * FROM department WHERE coordinator_id = %s LIMIT 1", (coordinator_id,))

        if course['department_id'] != department['id']:
            return {"message": "You cannot view this course"}, 400

        bundle = db.fetch_one("SELECT * FROM bundle WHERE id = %s LIMIT 1", (bundle_id,))
        if not bundle:
            return {"message": "Bundle not found"}, 404

        if bundle['status'] != BUNDLE_STATUS['waiting-approval']:
            return {"message": "Bundle is not waiting for certificate approval"}, 400

        enrollment = db.fetch_one("SELECT * FROM enrollment WHERE id = %s LIMIT 1", (bundle['enrollment_id'],))
        if not enrollment:
            return {"message": "Enrollment not found"}, 404
        
        student = db.fetch_one("SELECT * FROM student WHERE id = %s LIMIT 1", (enrollment['student_id'],))
        if not student:
            return {"message": "Student not found"}, 404
        
        db.execute("UPDATE enrollment SET is_pass = True, pass_date = NOW() WHERE id = %s", (enrollment['id'],))
        db.execute("UPDATE bundle SET status = %s, certificate_coordinator = %s, certificate_date = NOW() WHERE id = %s", (BUNDLE_STATUS['accepted-certificates'], coordinator_id, bundle_id))
        send_mail_queue(student['email'], "Course Completition", f"""Your certificates has been approved. You completed the {course["name"]} course succesfully.""")
        return {"message": "Certificate approved"}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@coordinator_app.route("/course/<int:course_id>/bundle/<int:bundle_id>/reject-certificate", methods=['POST'])
@coordinator_auth()
def coordinator_reject_certificate(course_id, bundle_id):
    try:
        coordinator_id = get_jwt()['sub']['id']
        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s and is_active = True LIMIT 1", (coordinator_id,))

        if not coordinator:
            return {"message": "Coordinator not found or coordinator disabled"}, 404

        course = db.fetch_one("SELECT * FROM MEFcourse WHERE id = %s LIMIT 1", (course_id,))
        if not course:
            return {"message": "Course not found"}, 404

        department = db.fetch_one("SELECT * FROM department WHERE coordinator_id = %s LIMIT 1", (coordinator_id,))

        if course['department_id'] != department['id']:
            return {"message": "You cannot view this course"}, 400

        bundle = db.fetch_one("SELECT * FROM bundle WHERE id = %s LIMIT 1", (bundle_id,))
        if not bundle:
            return {"message": "Bundle not found"}, 404

        if bundle['status'] != BUNDLE_STATUS['waiting-approval']:
            return {"message": "Bundle is not waiting for certificate approval"}, 400

        data = request.get_json()
        reason = data['reason']

        enrollment = db.fetch_one("SELECT * FROM enrollment WHERE id = %s LIMIT 1", (bundle['enrollment_id'],))
        if not enrollment:
            return {"message": "Enrollment not found"}, 404
        
        student = db.fetch_one("SELECT * FROM student WHERE id = %s LIMIT 1", (enrollment['student_id'],))
        if not student:
            return {"message": "Student not found"}, 404
        
        db.execute("UPDATE bundle SET status = %s, certificate_coordinator = %s, certificate_date = NOW(), reject_status_comment = %s WHERE id = %s", (BUNDLE_STATUS['rejected-certificates'], coordinator_id, reason, bundle_id))

        # Create copy of bundle with the status of waiting certificates and bundle details
        db.execute("""INSERT INTO bundle (created_at, coordinator_id, enrollment_id, status, bundle_date, complete_date)
                      SELECT created_at, coordinator_id, enrollment_id, %s, bundle_date, complete_date
                      FROM bundle WHERE id = %s"""
                   ,(BUNDLE_STATUS["waiting-certificates"], bundle['id'],))
                
        # Get the new bundle id
        new_bundle = db.fetch_one("SELECT * FROM bundle WHERE enrollment_id = %s AND status = %s LIMIT 1", (bundle['enrollment_id'], BUNDLE_STATUS['waiting-certificates']))

        bundle_details = db.fetch("SELECT * FROM bundle_detail WHERE bundle_id = %s", (bundle['id'],))
        for bundle_detail in bundle_details:
            db.execute("INSERT INTO bundle_detail (bundle_id, mooc_id) SELECT %s, mooc_id FROM bundle_detail WHERE id = %s", (new_bundle['id'], bundle_detail['id'],))

        send_mail_queue(student['email'], "Course Completition", f"""Your certificates for {course["name"]} has been rejected. Please check your certificate URLs.\nReason: {reason}""")
        return {"message": "Certificate rejected"}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500
    
@coordinator_app.route("/course/<int:course_id>/waiting-bundles", methods=['GET'])
@coordinator_auth()
def coordinator_course_waiting_bundles(course_id):
    try:
        coordinator_id = get_jwt()['sub']['id']
        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s and is_active = True LIMIT 1", (coordinator_id,))

        if not coordinator:
            return {"message": "Coordinator not found or coordinator disabled"}, 404

        course = db.fetch_one("SELECT * FROM MEFcourse WHERE id = %s LIMIT 1", (course_id,))
        if not course:
            return {"message": "Course not found"}, 404

        department = db.fetch_one("SELECT * FROM department WHERE coordinator_id = %s LIMIT 1", (coordinator_id,))

        if course['department_id'] != department['id']:
            return {"message": "You cannot view this course"}, 400

        hashed_status = BUNDLE_STATUS.get("waiting-bundles")

        if not hashed_status:
            return {"message": "Status not found"}, 404

        # TODO: Get total bundle hours
        bundles = db.fetch("""
                            SELECT s.id as student_id, s.name as student_name, s.surname as student_surname, s.email as student_email, 
                                   s.student_no, b.id as bundle_id, b.created_at as bundle_created_at, m.name as mooc_name, m.url as mooc_url, m.average_hours
                            FROM student s
                            INNER JOIN enrollment e ON s.id = e.student_id
                            INNER JOIN bundle b ON e.id = b.enrollment_id
                            INNER JOIN bundle_detail bd ON b.id = bd.bundle_id
                            INNER JOIN mooc m ON bd.mooc_id = m.id
                            LEFT JOIN coordinator c ON b.coordinator_id = c.id
                            WHERE b.status = %s and e.course_id = %s
                            ORDER BY b.created_at DESC
        """, (hashed_status, course_id,))

        return {"bundles": bundles, "is_active": course["is_active"]}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500
    
@coordinator_app.route("/course/<int:course_id>/rejected-bundles", methods=['GET'])
@coordinator_auth()
def coordinator_course_rejected_bundles(course_id):
    try:
        coordinator_id = get_jwt()['sub']['id']
        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s and is_active = True LIMIT 1", (coordinator_id,))

        if not coordinator:
            return {"message": "Coordinator not found or coordinator disabled"}, 404

        course = db.fetch_one("SELECT * FROM MEFcourse WHERE id = %s LIMIT 1", (course_id,))
        if not course:
            return {"message": "Course not found"}, 404

        department = db.fetch_one("SELECT * FROM department WHERE coordinator_id = %s LIMIT 1", (coordinator_id,))

        if course['department_id'] != department['id']:
            return {"message": "You cannot view this course"}, 400

        hashed_status = BUNDLE_STATUS.get("rejected-bundles")

        if not hashed_status:
            return {"message": "Status not found"}, 404

        # TODO: Get total bundle hours
        bundles = db.fetch("""
                            SELECT s.id as student_id, s.name as student_name, s.surname as student_surname, s.email as student_email, 
                                   s.student_no, b.id as bundle_id, b.bundle_date as bundle_created_at, m.name as mooc_name,
                                   m.url as mooc_url, CONCAT(c.name, ' ', c.surname) as coordinator_name, b.reject_status_comment
                            FROM student s
                            INNER JOIN enrollment e ON s.id = e.student_id
                            INNER JOIN bundle b ON e.id = b.enrollment_id
                            INNER JOIN bundle_detail bd ON b.id = bd.bundle_id
                            INNER JOIN mooc m ON bd.mooc_id = m.id
                            LEFT JOIN coordinator c ON b.coordinator_id = c.id
                            WHERE b.status = %s and e.course_id = %s
                            ORDER BY b.created_at DESC
        """, (hashed_status, course_id,))

        return {"bundles": bundles, "is_active": course["is_active"]}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@coordinator_app.route("/course/<int:course_id>/waiting-certificates", methods=['GET'])
@coordinator_auth()
def coordinator_course_waiting_certificates(course_id):
    try:
        coordinator_id = get_jwt()['sub']['id']
        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s and is_active = True LIMIT 1", (coordinator_id,))

        if not coordinator:
            return {"message": "Coordinator not found or coordinator disabled"}, 404

        course = db.fetch_one("SELECT * FROM MEFcourse WHERE id = %s LIMIT 1", (course_id,))
        if not course:
            return {"message": "Course not found"}, 404

        department = db.fetch_one("SELECT * FROM department WHERE coordinator_id = %s LIMIT 1", (coordinator_id,))

        if course['department_id'] != department['id']:
            return {"message": "You cannot view this course"}, 400

        hashed_status = BUNDLE_STATUS.get("waiting-certificates")

        if not hashed_status:
            return {"message": "Status not found"}, 404

        # TODO: Get total bundle hours
        bundles = db.fetch("""
                            SELECT s.id as student_id, s.name as student_name, s.surname as student_surname, s.email as student_email, 
                                   s.student_no, b.id as bundle_id, b.bundle_date as bundle_created_at, m.name as mooc_name,
                                   m.url as mooc_url, bd.certificate_url, CONCAT(c.name, ' ', c.surname) as coordinator_name, b.created_at as student_bundle_create_date
                            FROM student s
                            INNER JOIN enrollment e ON s.id = e.student_id
                            INNER JOIN bundle b ON e.id = b.enrollment_id
                            INNER JOIN bundle_detail bd ON b.id = bd.bundle_id
                            INNER JOIN mooc m ON bd.mooc_id = m.id
                            LEFT JOIN coordinator c ON b.coordinator_id = c.id
                            WHERE b.status = %s and e.course_id = %s
                            ORDER BY b.created_at DESC
        """, (hashed_status, course_id,))

        return {"bundles": bundles, "is_active": course["is_active"]}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500
    
@coordinator_app.route("/course/<int:course_id>/waiting-approval", methods=['GET'])
@coordinator_auth()
def coordinator_course_waiting_approval(course_id):
    try:
        coordinator_id = get_jwt()['sub']['id']
        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s and is_active = True LIMIT 1", (coordinator_id,))

        if not coordinator:
            return {"message": "Coordinator not found or coordinator disabled"}, 404

        course = db.fetch_one("SELECT * FROM MEFcourse WHERE id = %s LIMIT 1", (course_id,))
        if not course:
            return {"message": "Course not found"}, 404

        department = db.fetch_one("SELECT * FROM department WHERE coordinator_id = %s LIMIT 1", (coordinator_id,))

        if course['department_id'] != department['id']:
            return {"message": "You cannot view this course"}, 400

        hashed_status = BUNDLE_STATUS.get("waiting-approval")

        if not hashed_status:
            return {"message": "Status not found"}, 404

        # TODO: Get total bundle hours
        bundles = db.fetch("""
                            SELECT s.id as student_id, s.name as student_name, s.surname as student_surname, s.email as student_email, 
                                   s.student_no, b.id as bundle_id, b.complete_date, m.name as mooc_name, b.bundle_date, b.created_at as student_bundle_create_date,  
                                   m.url as mooc_url, bd.certificate_url, b.comment, CONCAT(c.name, ' ', c.surname) as bundle_coordinator
                            FROM student s
                            INNER JOIN enrollment e ON s.id = e.student_id
                            INNER JOIN bundle b ON e.id = b.enrollment_id
                            INNER JOIN bundle_detail bd ON b.id = bd.bundle_id
                            INNER JOIN mooc m ON bd.mooc_id = m.id
                            LEFT JOIN coordinator c ON b.coordinator_id = c.id
                            WHERE b.status = %s and e.course_id = %s
                            ORDER BY b.created_at DESC
        """, (hashed_status, course_id,))

        return {"bundles": bundles, "is_active": course["is_active"]}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500
    
@coordinator_app.route("/course/<int:course_id>/rejected-certificates", methods=['GET'])
@coordinator_auth()
def coordinator_course_rejected_certificates(course_id):
    try:
        coordinator_id = get_jwt()['sub']['id']
        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s and is_active = True LIMIT 1", (coordinator_id,))

        if not coordinator:
            return {"message": "Coordinator not found or coordinator disabled"}, 404

        course = db.fetch_one("SELECT * FROM MEFcourse WHERE id = %s LIMIT 1", (course_id,))
        if not course:
            return {"message": "Course not found"}, 404

        department = db.fetch_one("SELECT * FROM department WHERE coordinator_id = %s LIMIT 1", (coordinator_id,))

        if course['department_id'] != department['id']:
            return {"message": "You cannot view this course"}, 400

        hashed_status = BUNDLE_STATUS.get("rejected-certificates")

        if not hashed_status:
            return {"message": "Status not found"}, 404

        # TODO: Get total bundle hours
        bundles = db.fetch("""
                            SELECT s.id as student_id, s.name as student_name, s.surname as student_surname, s.email as student_email, 
                                   s.student_no, b.id as bundle_id, b.certificate_date as bundle_created_at, m.name as mooc_name, b.comment,
                                   m.url as mooc_url, bd.certificate_url, CONCAT(c.name, ' ', c.surname) as coordinator_name, b.reject_status_comment
                            FROM student s
                            INNER JOIN enrollment e ON s.id = e.student_id
                            INNER JOIN bundle b ON e.id = b.enrollment_id
                            INNER JOIN bundle_detail bd ON b.id = bd.bundle_id
                            INNER JOIN mooc m ON bd.mooc_id = m.id
                            LEFT JOIN coordinator c ON b.certificate_coordinator = c.id
                            WHERE b.status = %s and e.course_id = %s
                            ORDER BY b.created_at DESC
        """, (hashed_status, course_id,))

        return {"bundles": bundles, "is_active": course["is_active"]}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500
    
@coordinator_app.route("/course/<int:course_id>/accepted-certificates", methods=['GET'])
@coordinator_auth()
def coordinator_course_accepted_certificates(course_id):
    try:
        coordinator_id = get_jwt()['sub']['id']
        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE id = %s and is_active = True LIMIT 1", (coordinator_id,))

        if not coordinator:
            return {"message": "Coordinator not found or coordinator disabled"}, 404

        course = db.fetch_one("SELECT * FROM MEFcourse WHERE id = %s LIMIT 1", (course_id,))
        if not course:
            return {"message": "Course not found"}, 404

        department = db.fetch_one("SELECT * FROM department WHERE coordinator_id = %s LIMIT 1", (coordinator_id,))

        if course['department_id'] != department['id']:
            return {"message": "You cannot view this course"}, 400

        hashed_status = BUNDLE_STATUS.get("accepted-certificates")

        if not hashed_status:
            return {"message": "Status not found"}, 404

        # TODO: Get total bundle hours
        bundles = db.fetch("""
                            SELECT s.id as student_id, s.name as student_name, s.surname as student_surname, s.email as student_email, 
                                s.student_no, b.id as bundle_id, b.certificate_date, b.bundle_date, m.name as mooc_name, e.pass_date,
                                m.url as mooc_url, bd.certificate_url, CONCAT(c.name, ' ', c.surname) as certificate_coordinator, b.comment,
                                CONCAT(cb.name, ' ', cb.surname) as bundle_coordinator, b.complete_date as student_complete_date, b.created_at as student_bundle_create_date
                            FROM student s
                            INNER JOIN enrollment e ON s.id = e.student_id
                            INNER JOIN bundle b ON e.id = b.enrollment_id
                            INNER JOIN bundle_detail bd ON b.id = bd.bundle_id
                            INNER JOIN mooc m ON bd.mooc_id = m.id
                            LEFT JOIN coordinator c ON b.certificate_coordinator = c.id
                            LEFT JOIN coordinator cb ON b.coordinator_id = cb.id
                            WHERE b.status = %s and e.course_id = %s
                            ORDER BY b.created_at DESC
        """, (hashed_status, course_id,))

        return {"bundles": bundles, "is_active": course["is_active"]}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500